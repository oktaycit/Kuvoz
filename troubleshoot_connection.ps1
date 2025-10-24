# PowerShell Raspberry Pi Connection Troubleshooting

Write-Host "🔍 Raspberry Pi Connection Troubleshooting" -ForegroundColor Green
Write-Host "===========================================" -ForegroundColor Green

$RaspberryIP = "88.235.245.254"
$Username = "oktay"
$Password = "berkay1996"

# 1. Ping test
Write-Host "`n1️⃣ Ping test:" -ForegroundColor Yellow
try {
    $pingResult = Test-Connection -ComputerName $RaspberryIP -Count 4 -Quiet
    if ($pingResult) {
        Write-Host "✅ Ping successful" -ForegroundColor Green
    } else {
        Write-Host "❌ Ping failed - Host unreachable" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Ping error: $_" -ForegroundColor Red
}

# 2. Port test
Write-Host "`n2️⃣ Port accessibility test:" -ForegroundColor Yellow
$ports = @(22, 2222, 2200, 8022, 80, 443, 8080, 5000)
foreach ($port in $ports) {
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $tcpClient.ReceiveTimeout = 3000
        $tcpClient.SendTimeout = 3000
        $result = $tcpClient.ConnectAsync($RaspberryIP, $port).Wait(3000)
        if ($result) {
            Write-Host "✅ Port $port : OPEN" -ForegroundColor Green
        } else {
            Write-Host "❌ Port $port : CLOSED/TIMEOUT" -ForegroundColor Red
        }
        $tcpClient.Close()
    } catch {
        Write-Host "❌ Port $port : ERROR" -ForegroundColor Red
    }
}

# 3. SSH key methods
Write-Host "`n3️⃣ SSH Connection Methods:" -ForegroundColor Yellow
Write-Host "Method 1 (Password):" -ForegroundColor Cyan
Write-Host "ssh $Username@$RaspberryIP" -ForegroundColor White

Write-Host "`nMethod 2 (Specific port):" -ForegroundColor Cyan
Write-Host "ssh -p 22 $Username@$RaspberryIP" -ForegroundColor White

Write-Host "`nMethod 3 (With options):" -ForegroundColor Cyan
Write-Host "ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null $Username@$RaspberryIP" -ForegroundColor White

# 4. Alternative transfer methods
Write-Host "`n4️⃣ Alternative File Transfer Methods:" -ForegroundColor Yellow

Write-Host "`nMethod 1 - WinSCP GUI:" -ForegroundColor Cyan
Write-Host "Host: $RaspberryIP" -ForegroundColor White
Write-Host "Username: $Username" -ForegroundColor White
Write-Host "Password: $Password" -ForegroundColor White
Write-Host "Port: 22" -ForegroundColor White

Write-Host "`nMethod 2 - PuTTY PSCP:" -ForegroundColor Cyan
Write-Host "pscp -r -pw $Password . $Username@$RaspberryIP:/home/oktay/kuvoz/" -ForegroundColor White

Write-Host "`nMethod 3 - Git Repository:" -ForegroundColor Cyan
Write-Host "1. Push to GitHub: git push origin main" -ForegroundColor White
Write-Host "2. On Pi: git clone https://github.com/oktaycit/Kuvoz.git" -ForegroundColor White

Write-Host "`nMethod 4 - Cloud Storage:" -ForegroundColor Cyan
Write-Host "1. Upload to Google Drive/OneDrive" -ForegroundColor White
Write-Host "2. Download on Raspberry Pi" -ForegroundColor White

# 5. Network diagnostics
Write-Host "`n5️⃣ Network Diagnostics:" -ForegroundColor Yellow
Write-Host "Check these possibilities:" -ForegroundColor Cyan
Write-Host "• Router port forwarding (22 -> Raspberry Pi)" -ForegroundColor White
Write-Host "• Raspberry Pi SSH service status" -ForegroundColor White
Write-Host "• Firewall rules on Raspberry Pi" -ForegroundColor White
Write-Host "• ISP blocking SSH port" -ForegroundColor White
Write-Host "• Dynamic IP changed" -ForegroundColor White

# 6. Quick tests
Write-Host "`n6️⃣ Quick Test Commands:" -ForegroundColor Yellow
Write-Host "Test 1: telnet $RaspberryIP 22" -ForegroundColor White
Write-Host "Test 2: nmap -p 22 $RaspberryIP" -ForegroundColor White
Write-Host "Test 3: ssh -vvv $Username@$RaspberryIP" -ForegroundColor White

Write-Host "`n💡 Recommended Actions:" -ForegroundColor Green
Write-Host "1. Try WinSCP GUI application" -ForegroundColor White
Write-Host "2. Check router port forwarding" -ForegroundColor White  
Write-Host "3. Use Git repository method" -ForegroundColor White
Write-Host "4. Contact network administrator" -ForegroundColor White