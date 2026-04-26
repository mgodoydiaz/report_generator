@echo off
REM ============================================================
REM run_supabase_backup.bat - helper para Windows Task Scheduler
REM
REM Invoca scripts/backup_supabase.py usando python.exe nativo de
REM Windows (no requiere conda env activado). El script de Python
REM resuelve sus rutas con Path(__file__).resolve(), por lo que
REM no depende del working directory.
REM
REM Schedule sugerido (lunes y viernes 03:00):
REM   schtasks /Create /TN "RGenerator-Supabase-Backup" ^
REM     /TR "%~dp0run_supabase_backup.bat" ^
REM     /SC WEEKLY /D MON,FRI /ST 03:00 /F
REM
REM Logs van a backups/backup_supabase.log al lado de los .dump.
REM ============================================================

setlocal

set "PYTHON_EXE=C:\Python313\python.exe"
set "SCRIPT=%~dp0backup_supabase.py"
set "LOG_DIR=%~dp0..\backups"
set "LOG=%LOG_DIR%\backup_supabase.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo. >> "%LOG%"
echo === %DATE% %TIME% === >> "%LOG%"
"%PYTHON_EXE%" "%SCRIPT%" %* >> "%LOG%" 2>&1
exit /b %ERRORLEVEL%
