@echo off
rem Boletim diario - chamado pelo Agendador de Tarefas. Argumentos extras repassados (ex.: --vigiar).
set "UV_PROJECT_ENVIRONMENT=C:\Boletim\.venv"
set "PYTHONUTF8=1"
if not exist "C:\Boletim\logs" mkdir "C:\Boletim\logs"
cd /d "C:\Boletim"
"%USERPROFILE%\.local\bin\uv.exe" run --project "%~dp0." --python 3.12 python "%~dp0boletim.py" %* >> "C:\Boletim\logs\agendador.log" 2>&1
