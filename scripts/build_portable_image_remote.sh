#!/bin/bash
# Kuvoz için uzakta çalıştırılan taşınabilir imaj üretim scripti
# Amaç:
# 1. Canlı SD karttan ham imaj almak
# 2. PiShrink ile küçültülmüş bir .img üretmek
# 3. Sonucu xz ile sıkıştırmak
# 4. Sığıyorsa USB belleğe checksum ile kopyalamak
#
# Kullanım:
#   chmod +x ~/build_portable_image_remote.sh
#   nohup ~/build_portable_image_remote.sh > ~/build_portable_image_nohup.log 2>&1 < /dev/null &
#
# Ortam değişkenleri:
#   USB_DEVICE=/dev/sda1
#   USB_MOUNT=/mnt/usb1
#   HOME_DIR=/home/vet

set -euo pipefail

USB_DEVICE="${USB_DEVICE:-/dev/sda1}"
USB_MOUNT="${USB_MOUNT:-/mnt/usb1}"
HOME_DIR="${HOME_DIR:-$HOME}"
STAMP="$(date +%Y%m%d_%H%M%S)"
RAW_BASENAME="kuvoz_sd_${STAMP}.img"
SHRUNK_BASENAME="kuvoz_sd_${STAMP}_shrunk.img"
OUT_BASENAME="${SHRUNK_BASENAME}.xz"
RAW_IMAGE="${HOME_DIR}/${RAW_BASENAME}"
SHRUNK_IMAGE="${HOME_DIR}/${SHRUNK_BASENAME}"
OUT_IMAGE="${HOME_DIR}/${OUT_BASENAME}"
RAW_SHA="${RAW_IMAGE}.sha256"
SHRUNK_SHA="${SHRUNK_IMAGE}.sha256"
OUT_SHA="${OUT_IMAGE}.sha256"
LOG_FILE="${HOME_DIR}/build_portable_image_${STAMP}.log"
LOCK_FILE="${HOME_DIR}/build_portable_image.lock"

exec > >(tee -a "${LOG_FILE}") 2>&1

cleanup() {
    rm -f "${LOCK_FILE}" 2>/dev/null || true
    rm -f /zero.fill 2>/dev/null || true
    sync || true
    if mountpoint -q "${USB_MOUNT}"; then
        sudo umount "${USB_MOUNT}" || true
    fi
}

trap cleanup EXIT

if [ -f "${LOCK_FILE}" ]; then
    echo "❌ Kilit dosyası bulundu: ${LOCK_FILE}"
    echo "Önce eski işi kontrol edin."
    exit 1
fi

touch "${LOCK_FILE}"

echo "🚀 Taşınabilir Kuvoz imaj üretimi başladı"
echo "Log: ${LOG_FILE}"
echo "Çıktı: ${OUT_IMAGE}"
echo "USB cihazı: ${USB_DEVICE}"

echo
echo "1. Ön hazırlık"
rm -f "${HOME_DIR}"/kuvoz_sd_*.img "${HOME_DIR}"/kuvoz_sd_*.img.gz "${HOME_DIR}"/kuvoz_sd_*.img.xz "${HOME_DIR}"/kuvoz_sd_*.sha256 2>/dev/null || true
sudo apt clean
sudo journalctl --vacuum-time=1d >/dev/null || true
sudo rm -rf /tmp/*
if [ ! -x "${HOME_DIR}/pishrink.sh" ]; then
    echo "❌ PiShrink bulunamadı: ${HOME_DIR}/pishrink.sh"
    exit 1
fi
df -h /

echo
echo "2. Boş alan sıfırlanıyor"
sudo dd if=/dev/zero of=/zero.fill bs=64M status=progress || true
sync
sudo rm -f /zero.fill
sync
df -h /

echo
echo "3. Ham imaj üretiliyor"
sudo dd if=/dev/mmcblk0 of="${RAW_IMAGE}" bs=4M status=progress conv=fsync
sha256sum "${RAW_IMAGE}" > "${RAW_SHA}"
ls -lh "${RAW_IMAGE}" "${RAW_SHA}"

echo
echo "4. PiShrink ile küçültülmüş imaj üretiliyor"
sudo "${HOME_DIR}/pishrink.sh" -v "${RAW_IMAGE}" "${SHRUNK_IMAGE}"
sha256sum "${SHRUNK_IMAGE}" > "${SHRUNK_SHA}"
ls -lh "${SHRUNK_IMAGE}" "${SHRUNK_SHA}"

echo
echo "5. XZ ile sıkıştırılıyor"
xz -T0 -9e -c "${SHRUNK_IMAGE}" > "${OUT_IMAGE}"
sha256sum "${OUT_IMAGE}" > "${OUT_SHA}"
ls -lh "${OUT_IMAGE}" "${OUT_SHA}"

echo
echo "6. Geçici büyük dosyalar temizleniyor"
rm -f "${RAW_IMAGE}" "${RAW_SHA}" "${SHRUNK_IMAGE}" "${SHRUNK_SHA}"
sync
df -h /

echo
echo "7. USB kapasitesi kontrol ediliyor"
sudo mkdir -p "${USB_MOUNT}"
sudo mount -t ntfs-3g "${USB_DEVICE}" "${USB_MOUNT}"
df -h "${USB_MOUNT}"
IMAGE_BYTES="$(stat -c %s "${OUT_IMAGE}")"
USB_AVAIL_BYTES="$(df --output=avail -B1 "${USB_MOUNT}" | tail -1 | tr -d ' ')"
echo "IMAGE_BYTES=${IMAGE_BYTES}"
echo "USB_AVAIL_BYTES=${USB_AVAIL_BYTES}"

if [ "${USB_AVAIL_BYTES}" -lt "${IMAGE_BYTES}" ]; then
    echo "❌ İmaj USB'ye sığmıyor. Dosya home dizininde bırakıldı."
    exit 2
fi

echo
echo "8. USB temizlenip dosyalar kopyalanıyor"
sudo find "${USB_MOUNT}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
sync
cp -f "${OUT_IMAGE}" "${USB_MOUNT}/"
cp -f "${OUT_SHA}" "${USB_MOUNT}/"
sync

echo
echo "9. Kopya doğrulanıyor"
ls -lh "${USB_MOUNT}/${OUT_BASENAME}" "${USB_MOUNT}/${OUT_BASENAME}.sha256"
( cd "${USB_MOUNT}" && sha256sum -c "${OUT_BASENAME}.sha256" )
df -h "${USB_MOUNT}"

echo
echo "✅ İşlem tamamlandı"
