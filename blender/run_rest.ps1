# Attend la fin du premier lot puis enchaine les 4 rendus restants.
$log = 'E:\Autres\NOMAD-ONE\blender\renders\render.log'
for ($i = 0; $i -lt 720; $i++) {
  if ((Test-Path $log) -and (Select-String -Path $log -Pattern '=== termine' -Quiet)) { break }
  Start-Sleep -Seconds 20
}
& pwsh -NoProfile -ExecutionPolicy Bypass -File 'E:\Autres\NOMAD-ONE\blender\run_jobs2.ps1'
