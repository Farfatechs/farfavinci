# farfascript - desinstallation (ne touche pas a farfamask)
$nom = "farfascript"
$dest = Join-Path $env:LOCALAPPDATA $nom

Write-Host "Arret de l'application et du surveillant..."
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like "*\$nom\*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1

Write-Host "Suppression des fichiers..."
Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\$nom.lua") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path ([Environment]::GetFolderPath("Desktop")) "$nom.lnk") -ErrorAction SilentlyContinue
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" $nom -ErrorAction SilentlyContinue

Write-Host "Suppression du modele Whisper telecharge..."
$hf = Join-Path $env:USERPROFILE ".cache\huggingface\hub"
foreach ($m in "models--Systran--faster-whisper-large-v3", "models--Systran--faster-whisper-tiny") {
    Remove-Item -Recurse -Force (Join-Path $hf $m) -ErrorAction SilentlyContinue
}
Write-Host "Desinstallation de $nom terminee. (Les sous-titres deja crees dans tes projets restent en place.)"
