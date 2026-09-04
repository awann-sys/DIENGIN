@echo off
setlocal

echo Membuat Task Scheduler: DIENGIN Pipeline 15m
echo.

schtasks /Create /TN "DIENGIN Pipeline 15m" /TR "C:\DIENGIN\run_pipeline.bat" /SC MINUTE /MO 15 /ST 00:00 /F

if errorlevel 1 (
    echo.
    echo GAGAL membuat task.
    exit /b 1
)

echo.
echo SUCCESS - task berhasil dibuat.
echo Cek:
echo schtasks /Query /TN "DIENGIN Pipeline 15m" /V /FO LIST
echo.
echo Tes:
echo schtasks /Run /TN "DIENGIN Pipeline 15m"
exit /b 0
