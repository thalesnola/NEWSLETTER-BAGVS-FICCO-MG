@echo off
rem Liga a edicao de seguranca publica ao canal privado:  configurar_canal.cmd   ou   configurar_canal.cmd teste
set "UV_PROJECT_ENVIRONMENT=C:\Boletim\.venv"
set "PYTHONUTF8=1"
"%USERPROFILE%\.local\bin\uv.exe" run --project "%~dp0." --python 3.12 python "%~dp0configurar_canal.py" %1
