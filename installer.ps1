# farfavinci - installation (sous-titres automatiques + masque IA pour DaVinci Resolve)
# Lancer avec Installer.bat (double-clic) ou :
#   powershell -ExecutionPolicy Bypass -File installer.ps1
$ErrorActionPreference = "Stop"
$src = $PSScriptRoot
$dest = Join-Path $env:LOCALAPPDATA "farfavinci"

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
$avecMasque = $true
if (-not $gpu) {
    Alerte "Aucune carte graphique NVIDIA detectee."
    Alerte "Les sous-titres marcheront sur le processeur (beaucoup plus lent)."
    Alerte "Le masque IA ne sera PAS installe (il exige une carte NVIDIA)."
    $avecMasque = $false
} else {
    Ok "Carte graphique : $gpu"
}

if (-not (Test-Path "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe")) {
    Alerte "DaVinci Resolve introuvable a l'emplacement habituel (installation quand meme)."
} else {
    $ver = (Get-Item "C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe").VersionInfo.ProductVersion
    Ok "DaVinci Resolve $ver"
}

$libre = (Get-PSDrive ($env:LOCALAPPDATA.Substring(0, 1))).Free / 1GB
if ($libre -lt 12) { Alerte ("Espace disque libre : {0:N0} Go (environ 12 Go necessaires)" -f $libre) }

# --- Ancienne version (nommee "AutoTexte") : on la deplace au lieu de tout retelecharger ---
$ancien = Join-Path $env:LOCALAPPDATA "AutoTexteResolve"
if ((Test-Path $ancien) -and -not (Test-Path $dest)) {
    Titre "Mise a jour de l'ancienne version (AutoTexte -> farfavinci)"
    Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
        Where-Object { $_.CommandLine -like "*AutoTexteResolve*" } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep 2
    Move-Item $ancien $dest
    Ok "Installation deplacee vers $dest"
}
Remove-Item -Force (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\AutoTexte Pont.lua") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path ([Environment]::GetFolderPath("Desktop")) "Auto Sous-titres.lnk") -ErrorAction SilentlyContinue
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" "AutoTexteWatcher" -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force $dest | Out-Null

# --- Sous-titres (Whisper) ----------------------------------------------------------
Titre "1/3 Sous-titres : Whisper (environ 2 Go a telecharger)"
if (-not (Test-Path "$dest\venv\Scripts\python.exe")) { py -3.12 -m venv "$dest\venv" }
$py = "$dest\venv\Scripts\python.exe"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install faster-whisper "av==15.1.0" customtkinter pillow nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"
if ($LASTEXITCODE -ne 0) { Stop-Erreur "Echec de l'installation de Whisper (verifie ta connexion Internet)." }
Ok "Whisper installe"

# --- Masque IA (SAM 2) -------------------------------------------------------------
Titre "2/3 Masque IA : PyTorch CUDA + SAM 2 (environ 3 Go a telecharger)"
if ($avecMasque) {
    if (-not (Test-Path "$dest\venv_mask\Scripts\python.exe")) { py -3.12 -m venv "$dest\venv_mask" }
    $pm = "$dest\venv_mask\Scripts\python.exe"
    & $pm -m pip install --upgrade pip --quiet
    & $pm -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
    $env:SAM2_BUILD_CUDA = "0"   # pas besoin de compilateur
    & $pm -m pip install "https://github.com/facebookresearch/sam2/archive/refs/heads/main.zip" "av==15.1.0" pillow huggingface_hub
    if ($LASTEXITCODE -ne 0) {
        Alerte "Echec de l'installation du masque IA : les sous-titres fonctionneront quand meme."
    } else {
        Ok "Masque IA installe"
    }
} else {
    Alerte "Etape ignoree (pas de carte NVIDIA)."
}

# --- Fichiers, pont DaVinci, demarrage --------------------------------------------
Titre "3/3 Application, pont DaVinci et raccourci"
foreach ($f in "transcribe.py", "app.pyw", "bridge.py", "watcher.pyw", "mask.py", "masque_ui.py",
               "icon.ico", "caption-bin.drb", "NOTICE-AutoSubs.txt") {
    Copy-Item (Join-Path $src $f) $dest -Force
}
$scripts = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
New-Item -ItemType Directory -Force $scripts | Out-Null
Copy-Item (Join-Path $src "farfavinci.lua") $scripts -Force
Ok "Pont installe dans DaVinci (Espace de travail > Scripts > farfavinci)"

# Surveillant invisible : ouvre l'application quand le pont DaVinci demarre
$pw = "$dest\venv\Scripts\pythonw.exe"
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" "farfavinci" "`"$pw`" `"$dest\watcher.pyw`""
Start-Process $pw -ArgumentList "`"$dest\watcher.pyw`""
Ok "Ouverture automatique de l'application activee"

$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "farfavinci.lnk"))
$lnk.TargetPath = $pw
$lnk.Arguments = "`"$dest\app.pyw`""
$lnk.WorkingDirectory = $dest
$lnk.IconLocation = "$dest\icon.ico,0"
$lnk.Save()
Ok "Raccourci 'farfavinci' cree sur le bureau"

Titre "Installation terminee"
Write-Host "  1. Ouvre (ou redemarre) DaVinci Resolve"
Write-Host "  2. Espace de travail > Scripts > farfavinci"
Write-Host "  3. L'application s'ouvre toute seule"
Write-Host "  Au premier usage, les modeles d'IA se telechargent (environ 3,5 Go)."
