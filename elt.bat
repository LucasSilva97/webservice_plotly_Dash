@echo off
rem Gera as fontes sinteticas e roda o ELT completo (raw -> dbt -> parquet -> snapshot).
rem Repassa argumentos: elt.bat --manter-fontes
chcp 65001 >nul
cd /d "%~dp0"
".venv\Scripts\python.exe" -m elt %*
