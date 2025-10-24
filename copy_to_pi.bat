@echo off
REM Kuvoz Raspberry Pi Copy Script
REM SCP ile dosyaları kopyalama

echo 🚀 Kuvoz Files -> Raspberry Pi
echo ================================

set REMOTE_HOST=oktay@88.235.245.254
set REMOTE_PATH=/home/oktay/kuvoz
set PASSWORD=berkay1996

echo 📡 Target: %REMOTE_HOST%:%REMOTE_PATH%
echo.

REM Ana dosyalar
echo 📄 Copying main files...
scp -o StrictHostKeyChecking=no main2.py main3.py web_server.py kuvoz_backend.py %REMOTE_HOST%:%REMOTE_PATH%/
scp -o StrictHostKeyChecking=no form.kv Makefile %REMOTE_HOST%:%REMOTE_PATH%/
scp -o StrictHostKeyChecking=no *.mk %REMOTE_HOST%:%REMOTE_PATH%/
scp -o StrictHostKeyChecking=no *.md %REMOTE_HOST%:%REMOTE_PATH%/
scp -o StrictHostKeyChecking=no *.py %REMOTE_HOST%:%REMOTE_PATH%/
scp -o StrictHostKeyChecking=no *.sh %REMOTE_HOST%:%REMOTE_PATH%/

REM lib klasörü
echo 📚 Copying lib folder...
scp -r -o StrictHostKeyChecking=no lib/ %REMOTE_HOST%:%REMOTE_PATH%/

REM web klasörü
echo 🌐 Copying web folder...
scp -r -o StrictHostKeyChecking=no web/ %REMOTE_HOST%:%REMOTE_PATH%/

REM systemd klasörü
echo ⚙️ Copying systemd folder...
scp -r -o StrictHostKeyChecking=no systemd/ %REMOTE_HOST%:%REMOTE_PATH%/

REM scripts klasörü
echo 📜 Copying scripts folder...
scp -r -o StrictHostKeyChecking=no scripts/ %REMOTE_HOST%:%REMOTE_PATH%/

REM config klasörü
echo 🔧 Copying config folder...
scp -r -o StrictHostKeyChecking=no config/ %REMOTE_HOST%:%REMOTE_PATH%/

echo.
echo ✅ Copy completed!
echo 🔗 Connect: ssh %REMOTE_HOST%
echo 📁 Project: cd kuvoz
echo 🚀 Setup: make web-deps-install
echo 🌐 Run: make web-platform-fix-full

pause