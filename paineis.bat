@echo off
rem Abre os tres paineis em http://127.0.0.1:8050/ e na rede pelo IP desta maquina (Ctrl+C encerra).
rem So nesta maquina: paineis.bat --host 127.0.0.1
chcp 65001 >nul
cd /d "%~dp0"
".venv\Scripts\python.exe" -m paineis --abrir %*
