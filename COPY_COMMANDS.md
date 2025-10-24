# Kuvoz Raspberry Pi Manual Copy Commands
# Bu komutları PowerShell'de sırasıyla çalıştırın

# 1. Klasör oluştur
ssh oktay@88.235.245.254 "mkdir -p /home/oktay/kuvoz"

# 2. Ana Python dosyaları
scp main2.py main3.py web_server.py kuvoz_backend.py oktay@88.235.245.254:/home/oktay/kuvoz/

# 3. Test dosyaları
scp test_*.py oktay@88.235.245.254:/home/oktay/kuvoz/

# 4. Script dosyaları  
scp *.sh oktay@88.235.245.254:/home/oktay/kuvoz/

# 5. Makefile ve config
scp Makefile *.mk oktay@88.235.245.254:/home/oktay/kuvoz/

# 6. Documentation
scp *.md oktay@88.235.245.254:/home/oktay/kuvoz/

# 7. Kivy form
scp form.kv oktay@88.235.245.254:/home/oktay/kuvoz/

# 8. lib klasörü
scp -r lib oktay@88.235.245.254:/home/oktay/kuvoz/

# 9. web klasörü  
scp -r web oktay@88.235.245.254:/home/oktay/kuvoz/

# 10. systemd klasörü
scp -r systemd oktay@88.235.245.254:/home/oktay/kuvoz/

# 11. scripts klasörü (varsa)
scp -r scripts oktay@88.235.245.254:/home/oktay/kuvoz/

# 12. Permissions ayarla
ssh oktay@88.235.245.254 "cd /home/oktay/kuvoz && chmod +x *.sh *.py"

# 13. Verification
ssh oktay@88.235.245.254 "cd /home/oktay/kuvoz && ls -la"

echo "✅ Copy completed!"
echo "🔗 Connect with: ssh oktay@88.235.245.254"
echo "📁 Go to project: cd kuvoz"  
echo "🚀 Setup: make web-deps-install"
echo "🌐 Run: make web-platform-fix-full"