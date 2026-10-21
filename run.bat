@echo off
chcp 65001 >nul
title Sistem Data Undangan Pernikahan Digital

echo ================================================================
echo   SISTEM DATA UNDANGAN PERNIKAHAN DIGITAL (PRD V1)
echo   Backend: Python Flask & SQLite ^| Frontend: Tailwind CSS
echo ================================================================
echo.

set PYTHON_CMD=python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set PYTHON_CMD="%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    ) else (
        echo [ERROR] Python tidak ditemukan di sistem!
        echo Silakan pastikan Python 3.10+ telah terinstal.
        pause
        exit /b 1
    )
)

echo [1/3] Menyiapkan database dan aset awal...
%PYTHON_CMD% generate_assets.py
%PYTHON_CMD% database.py

echo.
echo [2/3] Memulai Web Server di http://127.0.0.1:5000 ...
echo Akun Bawaan:
echo - Admin: admin / admin123
echo - Client Demo: rizky_anisa / pass123
echo.
echo [3/3] Membuka browser otomatis dalam 2 detik...
start "" "http://127.0.0.1:5000"

%PYTHON_CMD% app.py

pause
