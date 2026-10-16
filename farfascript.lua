-- farfascript : ouvre la fenêtre des sous-titres automatiques de farfavinci et démarre le pont
-- (le pont commun est installé dans %LOCALAPPDATA%/farfavinci/pont.lua)
---@diagnostic disable: undefined-global
FARFAVINCI_MODE = "soustitres"
local pont, err = loadfile(os.getenv("LOCALAPPDATA") .. "\\farfavinci\\pont.lua")
if not pont then
    print("[farfavinci] Pont introuvable : relance Installer.bat (" .. tostring(err) .. ")")
    return
end
pont()
