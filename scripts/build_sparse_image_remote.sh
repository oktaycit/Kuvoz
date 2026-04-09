#!/bin/bash
# Kuvoz için sparse imaj üretim scripti
# Amaç:
# 1. /dev/mmcblk0'dan normal dosyaya sparse destekli ham imaj almak
# 2. İstenirse PiShrink ile imajı daha da küçültmek
# 3. İstenirse xz ile sıkıştırmak
#
# Notlar:
# - Bu yöntem klasik dd ham kopyasına göre daha az fiziksel disk alanı kullanabilir.
# - Gerçek fayda, kaynakta uzun sıfır blokları varsa görülür.
# - En iyi sonuç için önce sistem temizliği ve boş alan sıfırlama yapılabilir.
#
# Kullanım:
#   chmod +x ./scripts/build_sparse_image_remote.sh
#   ./scripts/build_sparse_image_remote.sh
#
# Ortam değişkenleri:
#   HOME_DIR=/home/vet
#   USE_PISHRINK=1
#   COMPRESS_XZ=1

set -euo pipefail

HOME_DIR="${HOME_DIR:-$HOME}"
USE_PISHRINK="${USE_PISHRINK:-1}"
COMPRESS_XZ="${COMPRESS_XZ:-1}"
STAMP="$(date +%Y%m%d_%H%M%S)"
RAW_BASENAME="kuvoz_sparse_${STAMP}.img"
SHRUNK_BASENAME="kuvoz_sparse_${STAMP}_shrunk.img"
XZ_BASENAME="${SHRUNK_BASENAME}.xz"
RAW_IMAGE="${HOME_DIR}/${RAW_BASENAME}"
SHRUNK_IMAGE="${HOME_DIR}/${SHRUNK_BASENAME}"
XZ_IMAGE="${HOME_DIR}/${XZ_BASENAME}"
RAW_SHA="${RAW_IMAGE}.sha256"
SHRUNK_SHA="${SHRUNK_IMAGE}.sha256"
XZ_SHA="${XZ_IMAGE}.sha256"
LOG_FILE="${HOME_DIR}/build_sparse_image_${STAMP}.log"
LOCK_FILE="${HOME_DIR}/build_sparse_image.lock"

exec > >(tee -a "${LOG_FILE}") 2>&1

cleanup() {
    rm -f "${LOCK_FILE}" 2>/dev/null || true
}

trap cleanup EXIT

if [ -f "${LOCK_FILE}" ]; then
    echo "❌ Kilit dosyası bulundu: ${LOCK_FILE}"
    exit 1
fi

touch "${LOCK_FILE}"

echo "🚀 Sparse imaj üretimi başladı"
echo "Log: ${LOG_FILE}"
echo "Ham çıktı: ${RAW_IMAGE}"
echo "USE_PISHRINK=${USE_PISHRINK}"
echo "COMPRESS_XZ=${COMPRESS_XZ}"

echo
echo "1. Ön kontrol"
df -h "${HOME_DIR}"
if [ "${USE_PISHRINK}" = "1" ] && [ ! -x "${HOME_DIR}/pishrink.sh" ]; then
    echo "❌ PiShrink bulunamadı: ${HOME_DIR}/pishrink.sh"
    exit 1
fi

echo
echo "2. Sparse ham imaj alınıyor"
sudo dd if=/dev/mmcblk0 of="${RAW_IMAGE}" bs=4M conv=sparse status=progress
sync
ls -lh "${RAW_IMAGE}"
du -h "${RAW_IMAGE}"
sha256sum "${RAW_IMAGE}" > "${RAW_SHA}"

CURRENT_IMAGE="${RAW_IMAGE}"
CURRENT_SHA="${RAW_SHA}"

if [ "${USE_PISHRINK}" = "1" ]; then
    echo
    echo "3. PiShrink uygulanıyor"
    sudo "${HOME_DIR}/pishrink.sh" -v "${RAW_IMAGE}" "${SHRUNK_IMAGE}"
    sync
    ls -lh "${SHRUNK_IMAGE}"
    du -h "${SHRUNK_IMAGE}"
    sha256sum "${SHRUNK_IMAGE}" > "${SHRUNK_SHA}"
    CURRENT_IMAGE="${SHRUNK_IMAGE}"
    CURRENT_SHA="${SHRUNK_SHA}"
fi

if [ "${COMPRESS_XZ}" = "1" ]; then
    echo
    echo "4. XZ sıkıştırma uygulanıyor"
    xz -T0 -9e -c "${CURRENT_IMAGE}" > "${XZ_IMAGE}"
    sha256sum "${XZ_IMAGE}" > "${XZ_SHA}"
    ls -lh "${XZ_IMAGE}"
    du -h "${XZ_IMAGE}"
    CURRENT_IMAGE="${XZ_IMAGE}"
    CURRENT_SHA="${XZ_SHA}"
fi

echo
echo "5. Sonuç"
echo "FINAL_IMAGE=${CURRENT_IMAGE}"
echo "FINAL_SHA=${CURRENT_SHA}"
ls -lh "${CURRENT_IMAGE}" "${CURRENT_SHA}"
df -h "${HOME_DIR}"

echo
echo "✅ Sparse imaj akışı tamamlandı"
