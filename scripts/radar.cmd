@echo off
rem Radar de tendencias barriales: notas de los siete dias calendario anteriores.
rem La ejecuta la tarea "PrecioEntornoCABA\Radar de noticias" los lunes a las 9:00 (hora de Buenos Aires).
cd /d "%~dp0.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PY="C:\Users\Usuario\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe"
if not exist data\local mkdir data\local
echo ===== %date% %time% radar >> data\local\radar.log
%PY% -m precio_entorno.radar >> data\local\radar.log 2>&1
