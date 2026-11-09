# Reports load of Blender processes NOT started by our pipeline (pids listed in logs/our_pids.txt).
# Prints: IDLE  |  BUSY cpu_cores=<n> gpu3d=<pct> pids=<list>
param([string]$OursFile)
$ours = @()
if (Test-Path $OursFile) { $ours = Get-Content $OursFile | Where-Object { $_ -match '^\d+$' } }
$f = @(Get-Process blender -ErrorAction SilentlyContinue | Where-Object { $ours -notcontains "$($_.Id)" })
if ($f.Count -eq 0) { 'IDLE'; exit 0 }
$ids = $f | ForEach-Object { $_.Id }
$t0 = @{}; foreach ($p in $f) { $t0[$p.Id] = $p.TotalProcessorTime.TotalSeconds }
Start-Sleep -Seconds 3
$cpu = 0.0
foreach ($p in (Get-Process -Id $ids -ErrorAction SilentlyContinue)) { $cpu += ($p.TotalProcessorTime.TotalSeconds - $t0[$p.Id]) / 3.0 }
$gpu = 0.0
try {
  $s = (Get-Counter '\GPU Engine(*engtype_3D)\Utilization Percentage' -ErrorAction Stop).CounterSamples
  foreach ($x in $s) { foreach ($id in $ids) { if ($x.InstanceName -like "pid_$($id)_*") { $gpu += $x.CookedValue } } }
} catch {}
if ($cpu -gt 2.0 -or $gpu -gt 15) { "BUSY cpu_cores={0:N1} gpu3d={1:N0} pids={2}" -f $cpu, $gpu, ($ids -join ',') } else { "IDLE cpu_cores={0:N1} gpu3d={1:N0} pids={2}" -f $cpu, $gpu, ($ids -join ',') }
