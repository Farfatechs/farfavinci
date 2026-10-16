# farfavinci - desinstallation complete (retire aussi l'ancienne version "AutoTexte")
$dossiers = @((Join-Path $env:LOCALAPPDATA "farfavinci"), (Join-Path $env:LOCALAPPDATA "AutoTexteResolve"))
$utility = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"
$bureau = [Environment]::GetFolderPath("Desktop")
$run = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

Write-Host "Arret de l'application et du surveillant..."
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
    Where-Object { $_.CommandLine -like "*\farfavinci\*" -or $_.CommandLine -like "*AutoTexteResolve*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1

Write-Host "Suppression des fichiers..."
foreach ($d in $dossiers) { Remove-Item -Recurse -Force $d -ErrorAction SilentlyContinue }
foreach ($f in "farfavinci.lua", "AutoTexte Pont.lua") {
    Remove-Item -Force (Join-Path $utility $f) -ErrorAction SilentlyContinue
}
foreach ($f in "farfavinci.lnk", "Auto Sous-titres.lnk") {
    Remove-Item -Force (Join-Path $bureau $f) -ErrorAction SilentlyContinue
}
foreach ($k in "farfavinci", "AutoTexteWatcher") {
    Remove-ItemProperty $run $k -ErrorAction SilentlyContinue
}
Remove-Item -Recurse -Force "HKCU:\Software\Classes\autotexte" -ErrorAction SilentlyContinue

Write-Host "Suppression des modeles d'IA telecharges..."
$hf = Join-Path $env:USERPROFILE ".cache\huggingface\hub"
foreach ($m in "models--Systran--faster-whisper-large-v3", "models--Systran--faster-whisper-tiny",
               "models--facebook--sam2.1-hiera-base-plus") {
    Remove-Item -Recurse -Force (Join-Path $hf $m) -ErrorAction SilentlyContinue
}

Write-Host "Desinstallation terminee. (Les masques et sous-titres deja importes dans tes projets DaVinci restent en place.)"
