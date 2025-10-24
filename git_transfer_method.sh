# Git Repository Method - Raspberry Pi File Transfer
# SSH sorunları varsa Git üzerinden dosya transferi

echo "📦 Git Repository File Transfer Method"
echo "====================================="

# 1. Local git repository setup
echo "1️⃣ Setting up local git repository..."

# Git initialize (if not already)
git init

# Add all files
git add .

# Commit changes
git commit -m "Kuvoz project - web interface with DHT11 support"

# Add remote repository (GitHub)
echo "2️⃣ Adding remote repository..."
echo "GitHub repository: https://github.com/oktaycit/Kuvoz.git"

# Check if remote exists
if git remote | grep -q origin; then
    echo "Remote 'origin' already exists"
    git remote set-url origin https://github.com/oktaycit/Kuvoz.git
else
    git remote add origin https://github.com/oktaycit/Kuvoz.git
fi

# Push to repository
echo "3️⃣ Pushing to GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "✅ Files uploaded to GitHub!"
echo ""
echo "📥 On Raspberry Pi, run these commands:"
echo "======================================="
echo "# Connect to Raspberry Pi"
echo "ssh oktay@88.235.245.254"
echo ""
echo "# Clone repository"
echo "cd /home/oktay"
echo "git clone https://github.com/oktaycit/Kuvoz.git kuvoz"
echo "cd kuvoz"
echo ""
echo "# Setup project"
echo "make web-deps-install"
echo "make web-platform-fix-full"
echo ""
echo "💡 Alternative GitHub methods:"
echo "• Download ZIP: https://github.com/oktaycit/Kuvoz/archive/main.zip"
echo "• Use GitHub CLI: gh repo clone oktaycit/Kuvoz"
echo "• Use SSH clone: git clone git@github.com:oktaycit/Kuvoz.git"