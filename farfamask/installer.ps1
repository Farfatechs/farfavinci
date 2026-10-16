# farfamask - installation (masque IA pour DaVinci Resolve gratuit)
# Lancer avec Installer.bat (double-clic) ou :
#   powershell -ExecutionPolicy Bypass -File installer.ps1
$ErrorActionPreference = "Stop"
$src = $PSScriptRoot
$nom = "farfamask"
$dest = Join-Path $env:LOCALAPPDATA $nom
$utility = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
$bureau = [Environment]::GetFolderPath("Desktop")
$run = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

function Titre($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Cyan }
function Ok($t) { Write-Host "  [OK] $t" -ForegroundColor Green }
function Alerte($t) { Write-Host "  [!]  $t" -ForegroundColor Yellow }
function Stop-Erreur($t) { Write-Host "  [X]  $t" -ForegroundColor Red; exit 1 }

# --- Verifications -------------------------------------------------------------
Titre "Verification de la configuration"
try { $v = (& py -3.12 --version) 2>&1 } catch { $v = $null }
if ("$v" -notmatch "Python 3\.12") {
    Stop-Erreur ("Python 3.12 introuvable. Installe-le depuis https://www.python.org/downloads/ " +
                 "(coche 'py launcher' pendant l'installation), puis relance l'installation.")
}
Ok "$v"
$gpu = $null
try { $gpu = (& nvidia-smi --query-gpu=name,memory.total --format=csv,noheader) 2>$null } catch { }
if (-not $gpu) {
    Stop-Erreur "Aucune carte graphique NVIDIA detectee : farfamask a besoin d'une carte NVIDIA (CUDA)."
}
Ok "Carte graphique : $gpu"
$resolve = "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
if (Test-Path $resolve) { Ok ("DaVinci Resolve " + (Get-Item $resolve).VersionInfo.ProductVersion) }
else { Alerte "DaVinci Resolve introuvable a l'emplacement habituel (installation quand meme)." }

# --- Ancienne version commune (farfavinci) : on reprend sa partie -------------------
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like "*\farfavinci\*" -or $_.CommandLine -like "*AutoTexteResolve*" -or
                   $_.CommandLine -like "*\$nom\*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1
New-Item -ItemType Directory -Force $dest | Out-Null
foreach ($ancien in (Join-Path $env:LOCALAPPDATA "farfavinci"), (Join-Path $env:LOCALAPPDATA "AutoTexteResolve")) {
    if ((Test-Path "$ancien\venv_mask") -and -not (Test-Path "$dest\venv")) {
        Move-Item "$ancien\venv_mask" "$dest\venv"
        Ok "Environnement repris de l'ancienne installation ($ancien)"
    }
    if ((Test-Path $ancien) -and -not (Test-Path "$ancien\venv") -and -not (Test-Path "$ancien\venv_mask")) {
        Remove-Item -Recurse -Force $ancien -ErrorAction SilentlyContinue
    }
}
foreach ($f in "farfavinci.lua", "AutoTexte Pont.lua", "farfavinci Sous-titres.lua", "farfavinci Masque IA.lua") {
    Remove-Item -Force (Join-Path $utility $f) -ErrorAction SilentlyContinue
}
foreach ($f in "farfascript.lua", "farfamask.lua") {   # anciens lanceurs de la version commune
    $p = Join-Path $utility $f
    if ((Test-Path $p) -and ((Get-Content $p -Raw) -match "FARFAVINCI_MODE")) { Remove-Item -Force $p }
}
foreach ($f in "farfavinci.lnk", "Auto Sous-titres.lnk") { Remove-Item -Force (Join-Path $bureau $f) -ErrorAction SilentlyContinue }
foreach ($k in "farfavinci", "AutoTexteWatcher") { Remove-ItemProperty $run $k -ErrorAction SilentlyContinue }

# --- PyTorch CUDA + SAM 2 ------------------------------------------------------------
Titre "1/2 PyTorch CUDA + SAM 2 (environ 3 Go a telecharger)"
if (-not (Test-Path "$dest\venv\Scripts\python.exe")) { py -3.12 -m venv "$dest\venv" }
$py = "$dest\venv\Scripts\python.exe"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
if ($LASTEXITCODE -ne 0) { Stop-Erreur "Echec de l'installation de PyTorch (verifie ta connexion Internet)." }
$env:SAM2_BUILD_CUDA = "0"   # pas besoin de compilateur
& $py -m pip install "https://github.com/facebookresearch/sam2/archive/refs/heads/main.zip" "av==15.1.0" pillow huggingface_hub customtkinter
if ($LASTEXITCODE -ne 0) { Stop-Erreur "Echec de l'installation de SAM 2 (verifie ta connexion Internet)." }
Ok "SAM 2 installe"

# --- Application, script DaVinci, demarrage ------------------------------------------
Titre "2/2 Application, script DaVinci et raccourci"
foreach ($f in "app.pyw", "bridge.py", "mask.py", "masque_ui.py", "watcher.pyw", "icon.ico",
               "NOTICE-AutoSubs.txt") {
    Copy-Item (Join-Path $src $f) $dest -Force
}
New-Item -ItemType Directory -Force $utility | Out-Null
Copy-Item (Join-Path $src "$nom.lua") $utility -Force
Ok "Script installe : Espace de travail > Scripts > $nom"

$pw = "$dest\venv\Scripts\pythonw.exe"
Set-ItemProperty $run $nom "`"$pw`" `"$dest\watcher.pyw`""
Start-Process $pw -ArgumentList "`"$dest\watcher.pyw`""
Ok "Ouverture automatique de l'application activee"

$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $bureau "$nom.lnk"))
$lnk.TargetPath = $pw
$lnk.Arguments = "`"$dest\app.pyw`""
$lnk.WorkingDirectory = $dest
$lnk.IconLocation = "$dest\icon.ico,0"
$lnk.Save()
Ok "Raccourci '$nom' cree sur le bureau"

Titre "Installation terminee"
Write-Host "  1. Ouvre (ou redemarre) DaVinci Resolve"
Write-Host "  2. Espace de travail > Scripts > $nom"
Write-Host "  3. L'application $nom s'ouvre toute seule"
Write-Host "  Au premier usage, le modele SAM 2 se telecharge (environ 320 Mo)."
