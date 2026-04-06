#!/bin/bash
# Kuvoz için SD karttan doğrudan USB belleğe imaj üretme akışı
# Amaç:
# 1. Ham imajı cihazın kendi SD kartına değil, doğrudan USB belleğe yazmak
# 2. PiShrink'i USB üzerindeki .img dosyasına uygulamak
# 3. İstenirse aynı USB üzerinde .xz sıkıştırılmış çıktı üretmek
#
# Önemli:
# - Bu akış cihazın iç depolamasını şişirmez.
# - Ama USB bellekte GEÇİCİ olarak tam ham imaj kadar alan gerekir.
# - Yani 16 GB'lık karttan imaj alacaksanız USB belleğin 16 GB+ boş alanı olmalı.
#
# Kullanım:
#   chmod +x ./scripts/build_portable_image_to_usb.sh
#   USB_DEVICE=/dev/sda1 USB_MOUNT=/mnt/usb1 ./scripts/build_portable_image_to_usb.sh

set -euo pipefail

USB_DEVICE="${USB_DEVICE:-/dev/sda1}"
USB_MOUNT="${USB_MOUNT:-/mnt/usb1}"
WORK_DIR="${WORK_DIR:-$USB_MOUNT}"
HOME_DIR="${HOME_DIR:-$HOME}"
STAMP="$(date +%Y%m%d_%H%M%S)"
RAW_BASENAME="kuvoz_sd_${STAMP}.img"
XZ_BASENAME="${RAW_BASENAME}.xz"
RAW_IMAGE="${WORK_DIR}/${RAW_BASENAME}"
RAW_SHA="${RAW_IMAGE}.sha256"
XZ_IMAGE="${WORK_DIR}/${XZ_BASENAME}"
XZ_SHA="${XZ_IMAGE}.sha256"
LOG_FILE="${HOME_DIR}/build_portable_image_to_usb_${STAMP}.log"
LOCK_FILE="${HOME_DIR}/build_portable_image_to_usb.lock"

exec > >(tee -a "${LOG_FILE}") 2>&1

cleanup() {
    rm -f "${LOCK_FILE}" 2>/dev/null || true
    if mountpoint -q "${USB_MOUNT}"; then
        sync || true
        sudo umount "${USB_MOUNT}" || true
    fi
}

trap cleanup EXIT

if [ -f "${LOCK_FILE}" ]; then
    echo "❌ Kilit dosyası bulundu: ${LOCK_FILE}"
    exit 1
fi

touch "${LOCK_FILE}"

if [ ! -x "${HOME_DIR}/pishrink.sh" ]; then
    echo "❌ PiShrink bulunamadı: ${HOME_DIR}/pishrink.sh"
    exit 1
fi

echo "🚀 USB üstünde küçültülmüş imaj üretimi başladı"
echo "Log: ${LOG_FILE}"
echo "USB cihazı: ${USB_DEVICE}"
echo "USB mount: ${USB_MOUNT}"
echo "Çalışma dizini: ${WORK_DIR}"

echo
echo "1. USB bağlanıyor"
sudo mkdir -p "${USB_MOUNT}"
sudo mount -t ntfs-3g "${USB_DEVICE}" "${USB_MOUNT}"
df -h "${USB_MOUNT}"

echo
echo "2. USB temizleniyor"
sudo find "${USB_MOUNT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
sync
df -h "${USB_MOUNT}"

echo
echo "3. Ham imaj doğrudan USB'ye alınıyor"
sudo dd if=/dev/mmcblk0 of="${RAW_IMAGE}" bs=4M status=progress conv=fsync
sync
sha256sum "${RAW_IMAGE}" > "${RAW_SHA}"
ls -lh "${RAW_IMAGE}" "${RAW_SHA}"
df -h "${USB_MOUNT}"

echo
echo "4. PiShrink USB üzerindeki imaja uygulanıyor"
sudo "${HOME_DIR}/pishrink.sh" -v "${RAW_IMAGE}"
sync
sha256sum "${RAW_IMAGE}" > "${RAW_SHA}"
ls -lh "${RAW_IMAGE}" "${RAW_SHA}"
df -h "${USB_MOUNT}"

echo
echo "5. XZ sıkıştırma başlatılıyor"
xz -T0 -9e "${RAW_IMAGE}"
sha256sum "${XZ_IMAGE}" > "${XZ_SHA}"
ls -lh "${XZ_IMAGE}" "${XZ_SHA}"
df -h "${USB_MOUNT}"

echo
echo "6. Checksum doğrulanıyor"
( cd "${WORK_DIR}" && sha256sum -c "${XZ_BASENAME}.sha256" )

echo
echo "✅ USB üstünde küçültülmüş imaj üretimi tamamlandı"
