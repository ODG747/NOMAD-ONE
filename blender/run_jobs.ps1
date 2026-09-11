param([string[]]$Jobs = @('turntable','exploded'))
$blender = 'E:\Applis\Blender5.2\blender.exe'
$dir     = 'E:\Autres\NOMAD-ONE\blender'
$log     = Join-Path $dir 'renders\render.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
"=== demarrage $(Get-Date -Format 'HH:mm:ss') : $($Jobs -join ', ') ===" | Out-File -FilePath $log -Encoding utf8
foreach ($j in $Jobs) {
  "--- job $j : debut $(Get-Date -Format 'HH:mm:ss') ---" | Out-File -FilePath $log -Append -Encoding utf8
  & $blender --background --factory-startup --python (Join-Path $dir 'render_jobs.py') -- --job $j 2>&1 |
    Where-Object { $_ -match '\[NOMAD\]|Error|Traceback|Fra:' } |
    Out-File -FilePath $log -Append -Encoding utf8
  "--- job $j : fin $(Get-Date -Format 'HH:mm:ss') (exit $LASTEXITCODE) ---" | Out-File -FilePath $log -Append -Encoding utf8
}
"=== termine $(Get-Date -Format 'HH:mm:ss') ===" | Out-File -FilePath $log -Append -Encoding utf8
