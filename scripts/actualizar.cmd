@echo off
rem Actualizacion periodica de avisos de venta y de alquiler.
rem La ejecuta la tarea "PrecioEntornoCABA\Actualizar avisos".
cd /d "%~dp0.."
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PY="C:\Users\Usuario\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\python.exe"
if not exist data\local mkdir data\local
echo ===== %date% %time% venta >> data\local\actualizar.log
set INFERENCIA=
if exist data\processed\inferencia\evaluacion.json set INFERENCIA=--modelo data/processed/inferencia
%PY% -m precio_entorno.actualizar --operacion venta --autorizacion-confirmada %INFERENCIA% >> data\local\actualizar.log 2>&1
echo ===== %date% %time% alquiler >> data\local\actualizar.log
if exist data\local\real-alquiler.sqlite3 %PY% -m precio_entorno.actualizar --operacion alquiler --autorizacion-confirmada >> data\local\actualizar.log 2>&1
