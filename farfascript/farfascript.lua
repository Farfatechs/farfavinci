--[[
  farfascript - sous-titres automatiques pour DaVinci Resolve (gratuit, 21.x)

  Menu Espace de travail > Scripts > farfascript : démarre ce pont résident et
  ouvre l'application farfascript. L'application lui envoie des demandes par
  fichier (request.lua) et lit les réponses dans Fusion.prefs.
  Principe repris d'AutoSubs (MIT) : le Lua de Resolve gratuit n'a ni io ni
  os.execute, mais loadfile, bmd.* et fusion:SetPrefs fonctionnent.
]]
---@diagnostic disable: undefined-global

local MAILBOX = os.getenv("LOCALAPPDATA") .. "\\farfascript\\bridge"
local REQUEST = MAILBOX .. "\\request.lua"
local NS = "Global.FarfaScript."

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


function commandes.render_audio(req)
    local projet, timeline = contexte()
    local fps = fps_de(timeline)
    local debut = timeline:GetStartFrame()
    local nom = "audio_" .. tostring(os.time())
    local reglages = {
        TargetDir = req.dir,
        CustomName = nom,
        RenderMode = "Single clip",
        ExportVideo = false,
        ExportAudio = true,
        IsExportVideo = false,
        IsExportAudio = true,
        AudioBitDepth = 24,
        AudioSampleRate = 44100,
    }
    local decalage = 0
    if req.range == "inout" then
        -- GetMarkInOut renvoie des images relatives au début de la timeline
        local mio = lire_marques(timeline)
        local m = mio.audio or mio.video or {}
        if m["in"] == nil and m["out"] == nil then
            error("Pose d'abord un point d'entrée (I) et de sortie (O) sur la timeline")
        end
        reglages.MarkIn = (m["in"] or 0) + debut
        reglages.MarkOut = m["out"] and (m["out"] + debut) or timeline:GetEndFrame()
        decalage = (reglages.MarkIn - debut) / fps
    else
        reglages.MarkIn = debut
        reglages.MarkOut = timeline:GetEndFrame()
    end

    -- Le rendu ne démarre que depuis la page Deliver (comme AutoSubs)
    local page_avant = RESOLVE:GetCurrentPage()
    RESOLVE:OpenPage("deliver")

    local function restaurer()
        pcall(function() RESOLVE:OpenPage(page_avant) end)
    end

    local ok, err = pcall(function()
        -- Préréglage stock "Audio Only", sinon WAV direct
        if not projet:LoadRenderPreset("Audio Only") then
            for _, e in ipairs({ { "wav", "LinearPCM" }, { "wav", "lpcm" } }) do
                if projet:SetCurrentRenderFormatAndCodec(e[1], e[2]) then break end
            end
        end
        projet:SetRenderSettings(reglages)
        local job = projet:AddRenderJob()
        if not job or job == "" then error("Impossible de créer le rendu audio") end
        local lance = projet:StartRendering(job)
        if not lance then
            bmd.wait(0.5)
            lance = projet:StartRendering(job)
        end
        if not lance then
            error("DaVinci refuse de lancer le rendu (même après la page Deliver)")
        end
        local t0 = os.time()
        while true do
            local st = projet:GetRenderJobStatus(job) or {}
            local js = tostring(st.JobStatus)
            if js == "Complete" or js == "Failed" or js == "Cancelled" then
                if js ~= "Complete" then error("Rendu audio : " .. js) end
                break
            end
            if os.time() - t0 > 3600 then error("Rendu audio trop long") end
            bmd.wait(0.5)
        end
        projet:DeleteRenderJob(job)
    end)
    restaurer()
    if not ok then error(err, 0) end

    for _, ext in ipairs({ "wav", "mov", "mp4" }) do
        local chemin = req.dir .. "\\" .. nom .. "." .. ext
        if bmd.fileexists(chemin) then
            return { fichier = chemin, decalage = string.format("%.3f", decalage) }
        end
    end
    error("Rendu terminé mais fichier audio introuvable dans " .. req.dir)
end

-- Liste les clips audio de la timeline (plan B : l'application reconstruit
-- l'audio elle-même à partir des fichiers sources, sans passer par le rendu).
function commandes.clips()
    local _, timeline = contexte()
    local fps = fps_de(timeline)
    local debut = timeline:GetStartFrame()
    local res = { fps = tostring(fps) }
    local n = 0
    for piste = 1, timeline:GetTrackCount("audio") do
        for _, it in ipairs(timeline:GetItemListInTrack("audio", piste) or {}) do
            local mpi = it:GetMediaPoolItem()
            local chemin = mpi and mpi:GetClipProperty("File Path") or ""
            if chemin ~= "" then
                local deb = (it:GetStart() - debut) / fps
                local fin = (it:GetEnd() - debut) / fps
                local ok, src = pcall(function() return it:GetLeftOffset() end)
                local src_s = ((ok and tonumber(src)) or 0) / fps
                n = n + 1
                res["clip" .. n] = string.format("%d|%.3f|%.3f|%.3f|%s", piste, deb, fin, src_s, chemin)
            end
        end
    end
    res.nb = tostring(n)
    return res
end

-- Titres animés ------------------------------------------------------------
-- Modèle Fusion "AutoSubs Caption" (projet AutoSubs, licence MIT) importé
-- depuis caption-bin.drb. Un titre par sous-titre, texte + minutage des mots
-- (karaoké) + réglages du style, posés sur la piste vidéo 3 "Sous-titres".

local DRB = os.getenv("LOCALAPPDATA") .. "\\farfascript\\caption-bin.drb"
local NOM_MODELE = "AutoSubs Caption"
local NOM_PISTE = "Sous-titres"

local function est_modele(nom)
    return type(nom) == "string" and nom:sub(1, #NOM_MODELE) == NOM_MODELE
end

local function chercher_modele(dossier)
    for _, clip in ipairs(dossier:GetClipList() or {}) do
        if est_modele(clip:GetClipProperty("Clip Name")) then return clip end
    end
    for _, sous in ipairs(dossier:GetSubFolderList() or {}) do
        local trouve = chercher_modele(sous)
        if trouve then return trouve end
    end
    return nil
end

local function modele(pool)
    local racine = pool:GetRootFolder()
    local clip = chercher_modele(racine)
    if clip then return clip end
    local avant = pool:GetCurrentFolder()
    pool:SetCurrentFolder(racine)
    pool:ImportFolderFromFile(DRB)
    if avant then pool:SetCurrentFolder(avant) end
    clip = chercher_modele(racine)
    if not clip then error("Impossible d'importer le modèle de titres (" .. DRB .. ")") end
    return clip
end

-- Titres animés : toujours sur la piste vidéo 3 (créée si besoin ; la 2 est pour farfamask)
local PISTE_TITRES = 3
local function piste_autotexte(timeline)
    while timeline:GetTrackCount("video") < PISTE_TITRES do
        timeline:AddTrack("video")
    end
    pcall(function() timeline:SetTrackName("video", PISTE_TITRES, NOM_PISTE) end)
    return PISTE_TITRES
end

-- Piste de sous-titres : toujours la n°1, créée si besoin et nommée "Sous-titres"
local function piste_sous_titres(timeline)
    if timeline:GetTrackCount("subtitle") == 0 then
        timeline:AddTrack("subtitle")
    end
    pcall(function() timeline:SetTrackName("subtitle", 1, NOM_PISTE) end)
    return 1
end

function commandes.pistes()
    local _, timeline = contexte()
    local res = {}
    for _, genre in ipairs({ "video", "audio", "subtitle" }) do
        local noms = {}
        for i = 1, timeline:GetTrackCount(genre) do
            noms[#noms + 1] = i .. ":" .. tostring(timeline:GetTrackName(genre, i))
        end
        res[genre] = table.concat(noms, ", ")
    end
    return res
end

local function nb_car(s)
    local _, n = string.gsub(s, "[^\128-\191]", "")
    return n
end

local function minutage_mots(mots, fps, debut_s)
    local res, idx = {}, 0
    for _, m in ipairs(mots or {}) do
        local fin_idx = idx + nb_car(m[3]) - 1
        res[#res + 1] = {
            startIndex = idx,
            endIndex = fin_idx,
            startFrame = math.floor((m[1] - debut_s) * fps),
            endFrame = math.floor((m[2] - debut_s) * fps),
        }
        idx = fin_idx + 1
    end
    return res
end

-- Courbes naturelles ---------------------------------------------------------
-- Le modèle pose des courbes à 3-4 clés assez sèches. On les remplace par des
-- courbes calculées image par image (ressort amorti, accélération/décélération).
-- Espace du KeyStretcher : 0..fin = entrée (temps réel), 100-fin..100 = sortie.

local function ease_out(t) return 1 - (1 - t) ^ 3 end
local function ease_in(t) return t ^ 3 end
-- ressort amorti : 0 -> 1 avec un dépassement d'environ 12 % puis stabilisation
local function ressort(t) return 1 - math.exp(-6 * t) * math.cos(9 * t) end

-- f_entree(t) / f_sortie(u) : valeurs pour t, u dans [0, 1]
local function courbe(fin, mode, repos, f_entree, f_sortie)
    local k = {}
    for i = 0, fin do
        k[i] = { (mode ~= 1) and f_entree(i / fin) or repos }
    end
    for i = 0, fin do
        k[100 - fin + i] = { (mode ~= 0) and f_sortie(i / fin) or repos }
    end
    return k
end

local function spline_de(entree)
    local sortie = entree and entree:GetConnectedOutput()
    local stretcher = sortie and sortie:GetTool()
    if not (stretcher and stretcher.Keyframes) then return nil end
    local so = stretcher.Keyframes:GetConnectedOutput()
    return so and so:GetTool()
end

local function naturaliser(comp, tool, anim)
    if not anim or anim == "Aucune" then return end
    local follower = comp:FindTool("Follower1")
    if not follower then return end
    local cfps = tonumber(comp:GetPrefs("Comp.FrameFormat.Rate")) or 30
    -- au plus 45 : les clés d'entrée (0..fin) et de sortie (100-fin..100) ne se croisent pas
    local fin = math.min(45, math.max(4, math.floor((tool:GetInput("AnimationLength") or 0.3) * cfps + 0.5)))
    local mode = tool:GetInput("AnimationMode") or 2

    -- Opacité (le modèle la branche sur l'AnimationKeyframeStretcher)
    local st = comp:FindTool("AnimationKeyframeStretcher")
    local sp_op = st and st.Keyframes and st.Keyframes:GetConnectedOutput()
    sp_op = sp_op and sp_op:GetTool()
    if sp_op then
        sp_op:SetKeyFrames(courbe(fin, mode, 1,
            function(t) return ease_out(math.min(1, t / 0.6)) end,
            function(u) return 1 - ease_in(u) end), true)
    end

    -- Taille (Pop / Rebond)
    if anim == "Pop" or anim == "Rebond" then
        local f_in
        if anim == "Rebond" then
            f_in = function(t) return 0.5 + 0.5 * ressort(t) end
        else
            f_in = function(t) return 0.8 + 0.2 * ease_out(t) end
        end
        local k = courbe(fin, mode, 1, f_in, function(u) return 1 - 0.08 * ease_in(u) end)
        local prop = (tool:GetInput("AnimationLevel") == 0) and "Line" or "Word"
        for _, axe in ipairs({ "SizeX", "SizeY" }) do
            local sp = spline_de(follower[prop .. axe])
            if sp then sp:SetKeyFrames(k, true) end
        end
    end

    -- Glissement : petit déplacement vertical qui ralentit en arrivant
    if anim == "Glissement" then
        local k = courbe(fin, mode, 0,
            function(t) return -0.035 * (1 - ease_out(t)) end,
            function(u) return -0.035 * ease_in(u) end)
        for i = 1, 3 do
            local entree = follower["Offset" .. i]
            local so = entree and entree:GetConnectedOutput()
            local xy = so and so:GetTool()
            local sp = xy and spline_de(xy.Y)
            if sp then sp:SetKeyFrames(k, true) end
        end
    end
end

function commandes.add_captions(req)
    local projet, timeline = contexte()
    local chunk, err = loadfile(req.data)
    if not chunk then error("Données illisibles : " .. tostring(err)) end
    local data = chunk()
    local pool = projet:GetMediaPool()
    local tpl = modele(pool)
    local fps = fps_de(timeline)
    local tpl_fps = tonumber(tpl:GetClipProperty("FPS")) or fps
    local debut = timeline:GetStartFrame()
    local piste = piste_autotexte(timeline)

    if data.remplacer then
        -- on n'efface que nos titres, jamais les clips de l'utilisateur sur cette piste
        local anciens = {}
        for _, it in ipairs(timeline:GetItemListInTrack("video", piste) or {}) do
            if est_modele(it:GetName()) then anciens[#anciens + 1] = it end
        end
        if #anciens > 0 then timeline:DeleteClips(anciens, false) end
    end

    -- Liste des clips, sans chevauchement (DaVinci refuse sinon)
    local liste, caps, fin_prec = {}, {}, nil
    for _, c in ipairs(data.captions) do
        local rec = debut + math.floor(c.s * fps + 0.5)
        local fin = debut + math.floor(c.e * fps + 0.5)
        if fin_prec and rec < fin_prec then rec = fin_prec end
        if fin > rec then
            local duree = math.max(1, math.floor((fin - rec) / fps * tpl_fps + 0.5))
            liste[#liste + 1] = {
                mediaPoolItem = tpl, mediaType = 1, startFrame = 0, endFrame = duree,
                recordFrame = rec, trackIndex = piste,
            }
            caps[#caps + 1] = c
            fin_prec = fin
        end
    end
    if #liste == 0 then error("Aucun sous-titre à placer") end

    local items = pool:AppendToTimeline(liste) or {}
    local poses, rates, premiere_erreur = 0, 0, nil
    for i = 1, #liste do
        local item = items[i]
        local ok, e = pcall(function()
            if not item then error("titre non placé") end
            local comp = item:GetFusionCompByIndex(1)
            if not comp then error("pas de composition Fusion") end
            local tool = comp:FindTool("AutoSubs")
            local texte = comp:FindTool("Template") or comp:FindToolByID("TextPlus")
            if not tool or not texte then error("modèle incomplet") end
            local cfps = tonumber(comp:GetPrefs("Comp.FrameFormat.Rate")) or tpl_fps
            -- le minutage doit être en place avant le texte (le modèle le lit au changement)
            tool:SetData("WordTiming", minutage_mots(caps[i].w, cfps, caps[i].s))
            texte:SetInput("Text", caps[i].t)
            local cls = comp:FindTool("CharacterLevelStyling1")
            if cls then pcall(cls.SetInput, cls, "Text", caps[i].t) end
            local setter = tool:GetData("SetInputValues")
            if setter and setter ~= "" and data.reglages then
                loadstring(setter)()(comp, tool, data.reglages)
            end
            naturaliser(comp, tool, data.anim)
        end)
        if ok then poses = poses + 1 else
            rates = rates + 1
            premiere_erreur = premiere_erreur or tostring(e)
        end
    end
    return {
        poses = tostring(poses),
        rates = tostring(rates),
        erreur_titre = premiere_erreur or "",
    }
end

-- Diagnostic : liste les clips de la piste de sous-titres
function commandes.inspecter()
    local _, timeline = contexte()
    local fps = fps_de(timeline)
    local debut = timeline:GetStartFrame()
    local res = { pistes = tostring(timeline:GetTrackCount("subtitle")) }
    local n = 0
    for piste = 1, timeline:GetTrackCount("subtitle") do
        for _, it in ipairs(timeline:GetItemListInTrack("subtitle", piste) or {}) do
            n = n + 1
            if n <= 30 then
                res["sub" .. n] = string.format("%d|%.2f|%.2f|%s", piste,
                    (it:GetStart() - debut) / fps, (it:GetEnd() - debut) / fps, tostring(it:GetName()))
            end
        end
    end
    res.total = tostring(n)
    return res
end

-- Diagnostic : ce que DaVinci renvoie pour les points I / O
function commandes.marques()
    local _, timeline = contexte()
    local mio = lire_marques(timeline)
    local res = { debut = tostring(timeline:GetStartFrame()), fin = tostring(timeline:GetEndFrame()) }
    for genre, t in pairs(mio) do
        if type(t) == "table" then
            res[genre] = tostring(t["in"]) .. "-" .. tostring(t["out"])
        end
    end
    return res
end

function commandes.add_srt(req)
    local projet, timeline = contexte()
    local pool = projet:GetMediaPool()
    piste_sous_titres(timeline)
    -- DaVinci ajoute toujours en fin de piste : on vide la piste 1 pour repartir du début
    if req.remplacer == "1" then
        local anciens = timeline:GetItemListInTrack("subtitle", 1) or {}
        if #anciens > 0 then timeline:DeleteClips(anciens, false) end
    end
    local items = pool:ImportMedia({ req.srt })
    if not items or not items[1] then
        error("DaVinci a refusé d'importer le SRT : " .. req.srt)
    end
    local ok = pool:AppendToTimeline({
        { mediaPoolItem = items[1], recordFrame = timeline:GetStartFrame() },
    })
    local n = 0
    local clips = timeline:GetItemListInTrack("subtitle", 1)
    if clips then n = #clips end
    return {
        ajoute = tostring(ok and true or false),
        clips_sous_titres = tostring(n),
    }
end


-- Boucle principale ---------------------------------------------------------

local function repondre(id, resultat)
    local lignes = {}
    for k, v in pairs(resultat) do
        lignes[#lignes + 1] = k .. "=" .. tostring(v):gsub("[\r\n]+", " ")
    end
    ecrire_pref("FSReply", id .. ":" .. base64(table.concat(lignes, "\n")))
end

local function main()
    local jeton = tostring(os.time()) .. " " .. tostring({})
    fusion:SetPrefs(NS .. "Owner", jeton)
    bmd.wait(0.3)
    -- Signal de démarrage : le surveillant (watcher.pyw) lance alors l'application
    -- signal de démarrage : le surveillant (watcher.pyw) ouvre l'application
    ecrire_pref("FSStart", jeton)
    print("[farfascript] Pont démarré. Tu peux utiliser l'application farfascript.")
    local tick = 0
    while true do
        tick = tick + 1
        if tick % 10 == 0 then
            local ok, owner = pcall(fusion.GetPrefs, fusion, NS .. "Owner")
            if ok and owner ~= jeton then
                print("[farfascript] Un autre pont a pris le relais, arrêt.")
                return
            end
        end
        if bmd.fileexists(REQUEST) then
            local chunk = loadfile(REQUEST)
            local ok, req = false, nil
            if chunk then ok, req = pcall(chunk) end
            if ok and type(req) == "table" and req.id and req.id ~= FARFASCRIPT_LAST then
                FARFASCRIPT_LAST = req.id
                ecrire_pref("FSAck", req.id)
                local fn = commandes[req.cmd]
                local reussi, res = pcall(function()
                    if not fn then error("Commande inconnue : " .. tostring(req.cmd)) end
                    return fn(req)
                end)
                if reussi then
                    repondre(req.id, res or {})
                else
                    print("[farfascript] Erreur : " .. tostring(res))
                    repondre(req.id, { erreur = res })
                end
            end
        end
        bmd.wait(0.1)
    end
end

main()