# Installe Auto Sous-titres : environnement Python + Whisper GPU + application + pont DaVinci
$ErrorActionPreference = "Stop"
$src = $PSScriptRoot
$dest = Join-Path $env:LOCALAPPDATA "AutoTexteResolve"
New-Item -ItemType Directory -Force $dest | Out-Null

Write-Host "1/3 Creation de l'environnement Python..."
if (-not (Test-Path "$dest\venv\Scripts\python.exe")) { py -3.12 -m venv "$dest\venv" }
& "$dest\venv\Scripts\python.exe" -m pip install --upgrade pip
Write-Host "2/3 Installation de Whisper GPU (environ 2 Go)..."
& "$dest\venv\Scripts\python.exe" -m pip install faster-whisper "av==15.1.0" customtkinter pillow nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"

Write-Host "2b/3 Installation du masque IA (PyTorch CUDA + SAM 2, environ 3 Go)..."
if (-not (Test-Path "$dest\venv_mask\Scripts\python.exe")) { py -3.12 -m venv "$dest\venv_mask" }
$pm = "$dest\venv_mask\Scripts\python.exe"
& $pm -m pip install --upgrade pip
& $pm -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
$env:SAM2_BUILD_CUDA = "0"
& $pm -m pip install "git+https://github.com/facebookresearch/sam2.git" "av==15.1.0" pillow huggingface_hub

Write-Host "3/3 Copie de l'application, du pont DaVinci et du raccourci..."
Copy-Item "$src\mask.py" $dest -Force
Copy-Item "$src\masque_ui.py" $dest -Force
Copy-Item "$src\transcribe.py" $dest -Force
Copy-Item "$src\app.pyw" $dest -Force
Copy-Item "$src\bridge.py" $dest -Force
Copy-Item "$src\watcher.pyw" $dest -Force
Copy-Item "$src\icon.ico" $dest -Force
Copy-Item "$src\caption-bin.drb" $dest -Force
Copy-Item "$src\NOTICE-AutoSubs.txt" $dest -Force
$scripts = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
New-Item -ItemType Directory -Force $scripts | Out-Null
Copy-Item "$src\AutoTexte Pont.lua" $scripts -Force

# Surveillant invisible : lance l'application quand le pont DaVinci demarre
$pw = "$dest\venv\Scripts\pythonw.exe"
Set-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" "AutoTexteWatcher" "`"$pw`" `"$dest\watcher.pyw`""
Start-Process $pw -ArgumentList "`"$dest\watcher.pyw`""

$sh = New-Object -ComObject WScript.Shell
$lnk = $sh.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Auto Sous-titres.lnk"))
$lnk.TargetPath = $pw
$lnk.Arguments = "`"$dest\app.pyw`""
$lnk.WorkingDirectory = $dest
$lnk.IconLocation = "$dest\icon.ico,0"
$lnk.Save()
Write-Host "Termine. Utilise le raccourci 'Auto Sous-titres' sur le bureau."
