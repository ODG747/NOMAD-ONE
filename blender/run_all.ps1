# NOMAD ONE - relance la production des rendus.
# Reprend automatiquement la ou le lot precedent s'est arrete.
#   pwsh -File blender\run_all.ps1
$dir = 'E:\Autres\NOMAD-ONE\blender'
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dir 'run_jobs.ps1')
& pwsh -NoProfile -ExecutionPolicy Bypass -File (Join-Path $dir 'run_jobs2.ps1')
Write-Output 'Rendus termines. Etape suivante : python tools\build_assets.py'
