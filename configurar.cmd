@echo off
rem Liga o painel ao bot bot do painel:  configurar.cmd   ou   configurar.cmd teste
set "UV_PROJECT_ENVIRONMENT=C:\Boletim\.venv"
set "PYTHONUTF8=1"
"%USERPROFILE%\.local\bin\uv.exe" run --project "%~dp0." --python 3.12 python "%~dp0configurar_telegram.py" %1
