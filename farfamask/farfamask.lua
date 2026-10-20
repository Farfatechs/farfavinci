--[[
  farfamask - masque IA pour DaVinci Resolve (gratuit, 21.x)

  Menu Espace de travail > Scripts > farfamask : démarre ce pont résident et
  ouvre l'application farfamask. L'application lui envoie des demandes par
  fichier (request.lua) et lit les réponses dans Fusion.prefs.
  Principe repris d'AutoSubs (MIT) : le Lua de Resolve gratuit n'a ni io ni
  os.execute, mais loadfile, bmd.* et fusion:SetPrefs fonctionnent.
]]
---@diagnostic disable: undefined-global

local MAILBOX = os.getenv("LOCALAPPDATA") .. "\\farfamask\\bridge"
local REQUEST = MAILBOX .. "\\request.lua"
local NS = "Global.FarfaMask."

-- base64 en Lua pur (pas d'opérateurs binaires)
local B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
local function base64(data)
    return ((data:gsub(".", function(x)
        local r, b = "", x:byte()
        for i = 8, 1, -1 do
            r = r .. (b % 2 ^ i - b % 2 ^ (i - 1) >= 1 and "1" or "0")
        end
        return r
    end) .. "0000"):gsub("%d%d%d?%d?%d?%d?", function(x)
        if #x < 6 then return "" end
        local c = 0
        for i = 1, 6 do
            c = c + (x:sub(i, i) == "1" and 2 ^ (6 - i) or 0)
        end
        return B64:sub(c + 1, c + 1)
    end) .. ({ "", "==", "=" })[#data % 3 + 1])
end

local function ecrire_pref(cle, valeur)
    for _ = 1, 5 do
        local ok = pcall(function()
            fusion:SetPrefs(NS .. cle, valeur)
            fusion:SavePrefs()
        end)
        if ok then return end
        bmd.wait(0.05)
    end
end

local RESOLVE = rawget(_G, "resolve") or (rawget(_G, "Resolve") and Resolve())

local function contexte()
    if not RESOLVE then error("Objet DaVinci introuvable") end
    local projet = RESOLVE:GetProjectManager():GetCurrentProject()
    if not projet then error("Aucun projet ouvert") end
    local timeline = projet:GetCurrentTimeline()
    if not timeline then error("Aucune timeline ouverte") end
    return projet, timeline
end

local function fps_de(timeline)
    return tonumber(timeline:GetSetting("timelineFrameRate")) or 25
end

local function lire_marques(timeline)
    local ok, mio = pcall(function() return timeline:GetMarkInOut() end)
    if ok and type(mio) == "table" then return mio end
    return {}
end

-- Commandes -----------------------------------------------------------------

local commandes = {}

function commandes.ping()
    local projet, timeline = contexte()
    return {
        projet = projet:GetName(),
        timeline = timeline:GetName(),
        fps = tostring(fps_de(timeline)),
    }
end


-- Masque IA ------------------------------------------------------------------

local function tc_en_images(tc, fps)
    local h, m, s, f = tostring(tc):match("(%d+):(%d+):(%d+)[:;](%d+)")
    if not h then return nil end
    local nominal = math.floor(fps + 0.5)
    return ((tonumber(h) * 60 + tonumber(m)) * 60 + tonumber(s)) * nominal + tonumber(f)
end

local function fichier_de(item)
    local mpi = item and item:GetMediaPoolItem()
    local chemin = mpi and mpi:GetClipProperty("File Path") or ""
    return chemin ~= "" and chemin or nil, mpi
end

-- Clip vidéo sous la tête de lecture : le plus haut qui a un vrai fichier vidéo.
-- GetCurrentVideoItem renvoie parfois nil (selon la page) ou un titre (piste
-- « Sous-titres » de farfascript) : dans ces cas on parcourt les pistes nous-mêmes.
local function clip_sous_tete(timeline, tete)
    local item = timeline:GetCurrentVideoItem()
    if item and fichier_de(item) then return item end
    if not tete then return nil end
    for piste = timeline:GetTrackCount("video"), 1, -1 do
        if timeline:GetIsTrackEnabled("video", piste) ~= false then
            for _, it in ipairs(timeline:GetItemListInTrack("video", piste) or {}) do
                if it:GetStart() <= tete and tete < it:GetEnd() and fichier_de(it) then
                    return it
                end
            end
        end
    end
    return nil
end

local function piste_de(item)
    local ok, ti = pcall(function() return item:GetTrackTypeAndIndex() end)
    if ok and type(ti) == "table" then return ti[1], tonumber(ti[2]) or 1 end
    return "video", 1
end

local function source_debut(item)
    local ok, src = pcall(function() return item:GetSourceStartFrame() end)
    if not ok or not src then
        ok, src = pcall(function() return item:GetLeftOffset() end)
    end
    return tonumber(src) or 0
end

-- Clips vidéo sélectionnés sur la timeline (DaVinci 21.0.4+), avec un vrai fichier
local function clips_selectionnes(timeline)
    local ok, sel = pcall(function() return timeline:GetSelectedClips() end)
    local res = {}
    if ok and type(sel) == "table" then
        for _, it in pairs(sel) do
            if piste_de(it) == "video" and fichier_de(it) then res[#res + 1] = it end
        end
    end
    return res
end

-- Tous les clips vidéo (pistes actives) qui touchent [debut, fin)
local function clips_entre(timeline, debut, fin)
    local res = {}
    for piste = 1, timeline:GetTrackCount("video") do
        if timeline:GetIsTrackEnabled("video", piste) ~= false then
            for _, it in ipairs(timeline:GetItemListInTrack("video", piste) or {}) do
                if it:GetStart() < fin and debut < it:GetEnd() and fichier_de(it) then
                    res[#res + 1] = it
                end
            end
        end
    end
    return res
end

-- Découpe [debut, fin) en segments : à chaque instant, le clip de la piste la plus
-- haute ; les trous entre clips deviennent des segments sans fichier (images noires).
local function segments_de(items, debut, fin)
    local bornes, vu = { debut, fin }, { [debut] = true, [fin] = true }
    for _, it in ipairs(items) do
        for _, b in ipairs({ it:GetStart(), it:GetEnd() }) do
            if b > debut and b < fin and not vu[b] then
                vu[b] = true
                bornes[#bornes + 1] = b
            end
        end
    end
    table.sort(bornes)
    local segs = {}
    for i = 1, #bornes - 1 do
        local a, b = bornes[i], bornes[i + 1]
        local choix, haut = nil, -1
        for _, it in ipairs(items) do
            local _, p = piste_de(it)
            if it:GetStart() <= a and b <= it:GetEnd() and p > haut then choix, haut = it, p end
        end
        local der = segs[#segs]
        if der and der.item == choix then
            der.fin = b  -- même clip que le segment précédent : on prolonge
        else
            segs[#segs + 1] = { item = choix, debut = a, fin = b }
        end
    end
    return segs
end

function commandes.clip_courant(req)
    local _, timeline = contexte()
    local fps = fps_de(timeline)
    local tete = tc_en_images(timeline:GetCurrentTimecode(), fps)
    local items = clips_selectionnes(timeline)
    local origine = "sélection"
    local marques
    if req.range == "inout" then
        local m = lire_marques(timeline)
        m = m.video or m.audio or {}
        if m["in"] == nil and m["out"] == nil then
            error("Pose d'abord un point d'entrée (I) et de sortie (O) sur la timeline")
        end
        local t0 = timeline:GetStartFrame()
        marques = {
            m["in"] and (m["in"] + t0) or t0,
            m["out"] and (m["out"] + t0 + 1) or timeline:GetEndFrame(),  -- le point O est inclus
        }
    end
    if #items == 0 then
        if marques then
            -- rien de sélectionné : tous les clips entre les points I / O
            items = clips_entre(timeline, marques[1], marques[2])
            origine = "I / O"
        else
            local it = clip_sous_tete(timeline, tete)
            items = it and { it } or {}
            origine = "tête de lecture"
        end
    end
    if #items == 0 then
        error("Aucun clip vidéo : sélectionne un ou plusieurs clips sur la timeline (page Edit)")
    end

    -- Plage traitée : du début du premier clip à la fin du dernier, coupée aux points I / O
    local debut, fin = math.huge, -math.huge
    for _, it in ipairs(items) do
        debut, fin = math.min(debut, it:GetStart()), math.max(fin, it:GetEnd())
    end
    if marques then
        debut, fin = math.max(debut, marques[1]), math.min(fin, marques[2])
        if fin <= debut then
            error("Les points I / O ne recouvrent pas les clips sélectionnés")
        end
    end

    local res = {
        debut = tostring(debut),
        duree = tostring(fin - debut),
        tete = tostring(tete and (tete - debut) or 0),
        nb_clips = tostring(#items),
        origine = origine,
    }
    local segs = segments_de(items, debut, fin)
    res.nb_segments = tostring(#segs)
    for i, s in ipairs(segs) do
        local k = "seg" .. i .. "_"
        res[k .. "duree"] = tostring(s.fin - s.debut)
        if s.item then
            local chemin = fichier_de(s.item)
            local decal = s.debut - s.item:GetStart()
            res[k .. "fichier"] = chemin
            res[k .. "source_debut"] = tostring(math.floor(source_debut(s.item) + decal + 0.5))
            res.nom = res.nom or tostring(s.item:GetName())
        end
    end
    if not res.nom then
        error("Les points I / O tombent dans un trou entre les clips sélectionnés")
    end
    return res
end

local NOM_DETOURAGE = "Détourage"
-- Sujet détouré : toujours sur la piste vidéo 2 (créée si besoin ; la 3 est pour farfascript)
local PISTE_DETOURAGE = 2
local function piste_detourage(timeline)
    while timeline:GetTrackCount("video") < PISTE_DETOURAGE do
        timeline:AddTrack("video")
    end
    pcall(function() timeline:SetTrackName("video", PISTE_DETOURAGE, NOM_DETOURAGE) end)
    return PISTE_DETOURAGE
end

-- Importe détourage + cache dans le bin "Masques IA" et pose le détourage
-- au-dessus du clip d'origine, sur la piste "Détourage"
function commandes.add_mask(req)
    local projet, timeline = contexte()
    local pool = projet:GetMediaPool()
    local racine = pool:GetRootFolder()
    local bin
    for _, sous in ipairs(racine:GetSubFolderList() or {}) do
        if sous:GetName() == "Masques IA" then bin = sous end
    end
    bin = bin or pool:AddSubFolder(racine, "Masques IA")
    local avant = pool:GetCurrentFolder()
    if bin then pool:SetCurrentFolder(bin) end
    local items = pool:ImportMedia({ req.detourage, req.cache }) or {}
    if avant then pool:SetCurrentFolder(avant) end
    if not items[1] then error("Import des masques refusé par DaVinci") end
    local res = { importes = tostring(#items) }
    if req.poser == "1" then
        local piste = piste_detourage(timeline)
        local n = tonumber(req.n)
        local poses = pool:AppendToTimeline({ {
            mediaPoolItem = items[1], mediaType = 1, startFrame = 0, endFrame = n - 1,
            recordFrame = tonumber(req.debut), trackIndex = piste,
        } })
        res.pose = tostring(poses and poses[1] ~= nil)
        res.piste = tostring(piste)
    end
    return res
end

-- Boucle principale ---------------------------------------------------------

local function repondre(id, resultat)
    local lignes = {}
    for k, v in pairs(resultat) do
        lignes[#lignes + 1] = k .. "=" .. tostring(v):gsub("[\r\n]+", " ")
    end
    ecrire_pref("FMReply", id .. ":" .. base64(table.concat(lignes, "\n")))
end

local function main()
    local jeton = tostring(os.time()) .. " " .. tostring({})
    fusion:SetPrefs(NS .. "Owner", jeton)
    bmd.wait(0.3)
    -- Signal de démarrage : le surveillant (watcher.pyw) lance alors l'application
    -- signal de démarrage : le surveillant (watcher.pyw) ouvre l'application
    ecrire_pref("FMStart", jeton)
    print("[farfamask] Pont démarré. Tu peux utiliser l'application farfamask.")
    local tick = 0
    while true do
        tick = tick + 1
        if tick % 10 == 0 then
            local ok, owner = pcall(fusion.GetPrefs, fusion, NS .. "Owner")
            if ok and owner ~= jeton then
                print("[farfamask] Un autre pont a pris le relais, arrêt.")
                return
            end
        end
        if bmd.fileexists(REQUEST) then
            local chunk = loadfile(REQUEST)
            local ok, req = false, nil
            if chunk then ok, req = pcall(chunk) end
            if ok and type(req) == "table" and req.id and req.id ~= FARFAMASK_LAST then
                FARFAMASK_LAST = req.id
                ecrire_pref("FMAck", req.id)
                local fn = commandes[req.cmd]
                local reussi, res = pcall(function()
                    if not fn then error("Commande inconnue : " .. tostring(req.cmd)) end
                    return fn(req)
                end)
                if reussi then
                    repondre(req.id, res or {})
                else
                    print("[farfamask] Erreur : " .. tostring(res))
                    repondre(req.id, { erreur = res })
                end
            end
        end
        bmd.wait(0.1)
    end
end

main()