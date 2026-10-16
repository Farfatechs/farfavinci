# farfavinci - desinstallation complete
$dest = Join-Path $env:LOCALAPPDATA "AutoTexteResolve"

Write-Host "Arret de l'application et du surveillant..."
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like "*AutoTexteResolve*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1

Write-Host "Suppression des fichiers..."
Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\AutoTexte Pont.lua") -ErrorAction SilentlyContinue
Remove-Item -Force (Join-Path ([Environment]::GetFolderPath("Desktop")) "Auto Sous-titres.lnk") -ErrorAction SilentlyContinue
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" "AutoTexteWatcher" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "HKCU:\Software\Classes\autotexte" -ErrorAction SilentlyContinue

Write-Host "Suppression des modeles d'IA telecharges..."
$hf = Join-Path $env:USERPROFILE ".cache\huggingface\hub"
foreach ($m in "models--Systran--faster-whisper-large-v3", "models--Systran--faster-whisper-tiny",
               "models--facebook--sam2.1-hiera-base-plus") {
    Remove-Item -Recurse -Force (Join-Path $hf $m) -ErrorAction SilentlyContinue
}

Write-Host "Desinstallation terminee. (Les masques et sous-titres deja importes dans tes projets DaVinci restent en place.)"
