# Crea o actualiza la tarea semanal del radar de tendencias barriales.
# Lunes a las 9:00. La hora es la del reloj de Windows, que tiene que estar en
# "Argentina Standard Time" (America/Argentina/Buenos_Aires, UTC-3 sin horario de verano).
# Uso: powershell -ExecutionPolicy Bypass -File scripts\programar-radar.ps1

$zona = (Get-TimeZone).Id
if ($zona -ne 'Argentina Standard Time') {
    Write-Warning "El reloj de Windows esta en '$zona'. La tarea correria a las 9:00 de esa zona, no de Buenos Aires."
}

$script = Join-Path $PSScriptRoot 'radar.cmd'
$accion = New-ScheduledTaskAction -Execute $script -WorkingDirectory (Split-Path $PSScriptRoot -Parent)
$disparador = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '09:00'
# Si la computadora estaba apagada el lunes a las 9:00, corre apenas se pueda.
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RunOnlyIfNetworkAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskPath '\PrecioEntornoCABA\' -TaskName 'Radar de noticias' -Action $accion `
    -Trigger $disparador -Settings $opciones -Force `
    -Description 'Radar de tendencias barriales: recolecta notas inmobiliarias de los siete dias anteriores.' |
    Select-Object TaskPath, TaskName, State

Get-ScheduledTaskInfo -TaskPath '\PrecioEntornoCABA\' -TaskName 'Radar de noticias' |
    Select-Object NextRunTime, LastRunTime, LastTaskResult
