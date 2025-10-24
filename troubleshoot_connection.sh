# Raspberry Pi Bağlantı Troubleshooting
# Port yönlendirme ve SSH sorunları için

echo "🔍 Raspberry Pi Connection Troubleshooting"
echo "==========================================="

# 1. Ping test
echo "1️⃣ Ping test:"
ping -c 4 88.235.245.254

# 2. Port kontrolü
echo "2️⃣ Port accessibility test:"
echo "Testing SSH port 22..."
nc -zv 88.235.245.254 22

# 3. Alternative SSH ports test
echo "3️⃣ Testing alternative SSH ports:"
for port in 22 2222 2200 8022; do
    echo "Testing port $port..."
    timeout 5 nc -zv 88.235.245.254 $port 2>/dev/null && echo "✅ Port $port: OPEN" || echo "❌ Port $port: CLOSED"
done

# 4. SSH connection test with verbose
echo "4️⃣ SSH connection test (verbose):"
ssh -v -o ConnectTimeout=10 oktay@88.235.245.254 "echo 'SSH OK'"

# 5. Different SSH methods
echo "5️⃣ Alternative connection methods:"
echo "Method 1: Standard SSH"
echo "ssh oktay@88.235.245.254"
echo ""
echo "Method 2: SSH with specific port"
echo "ssh -p 22 oktay@88.235.245.254"
echo ""
echo "Method 3: SSH with key"
echo "ssh -i ~/.ssh/id_rsa oktay@88.235.245.254"
echo ""
echo "Method 4: SCP direct"
echo "scp -P 22 file.txt oktay@88.235.245.254:/home/oktay/"

# 6. Router/NAT troubleshooting
echo "6️⃣ Network troubleshooting:"
echo "Check if Raspberry Pi is behind NAT/router:"
echo "- Router port forwarding: External port -> 88.235.245.254:22"
echo "- Raspberry Pi local IP might be different"
echo "- Firewall settings on Raspberry Pi"

# 7. Alternative transfer methods
echo "7️⃣ Alternative file transfer methods:"
echo "Method 1: HTTP upload (if web server running)"
echo "curl -X POST -F 'file=@filename' http://88.235.245.254:8080/upload"
echo ""
echo "Method 2: FTP/SFTP"
echo "sftp oktay@88.235.245.254"
echo ""
echo "Method 3: Git repository"
echo "git clone/push method"
echo ""
echo "Method 4: Cloud storage"
echo "Upload to cloud, download on Raspberry Pi"