/**
 * Kuvoz Tailscale Remote Access - Standalone JavaScript
 * WebSocket tabanlı Tailscale yönetim sistemi
 */

// Global state
let socket = null;
let authUrl = "";
let statusPollingInterval = null;
let currentShareInfo = null;
let sharingPermissionEnabled = false;

// Translation helper
function t(key) {
  const translations = window.kuvozTranslations || {};
  const keys = key.split('.');
  let value = translations;
  for (const k of keys) {
    value = value?.[k];
  }
  return value || key;
}

// Socket.IO connection
function connectSocket() {
  try {
    const socketUrl = window.location.origin;
    console.log('Tailscale: Connecting to Socket.IO at:', socketUrl);
    
    socket = io(socketUrl, {
      timeout: 5000,
      forceNew: true,
      transports: ['polling', 'websocket']
    });

    socket.on('connect', () => {
      console.log('✅ Tailscale: Socket.IO connected');
      checkTailscaleStatus();
      startStatusPolling();
    });

    socket.on('disconnect', () => {
      console.log('❌ Tailscale: Socket.IO disconnected');
      setTimeout(connectSocket, 3000);
    });

    socket.on('connect_error', (error) => {
      console.error('❌ Tailscale: Connection error:', error);
    });

    // Register event handlers
    registerEventHandlers();
  } catch (error) {
    console.error('❌ Tailscale: Failed to connect socket:', error);
  }
}

// Event handlers
function registerEventHandlers() {
  if (!socket) return;

  // Clear old handlers
  const events = [
    'tailscale_status_response',
    'tailscale_install_progress',
    'tailscale_install_response',
    'tailscale_auth_url',
    'tailscale_connect_response',
    'tailscale_disconnect_response',
    'tailscale_share_response',
    'tailscale_funnel_response',
    'tailscale_funnel_enable_required'
  ];
  
  events.forEach(e => socket.off(e));

  // Status response
  socket.on('tailscale_status_response', (data) => {
    hideLoading();
    setButtonsLoading(false);
    updateStatus(data);
  });

  // Install progress
  socket.on('tailscale_install_progress', (data) => {
    showLoading(data.message);
    setButtonsLoading(true);
  });

  // Install response
  socket.on('tailscale_install_response', (data) => {
    hideLoading();
    setButtonsLoading(false);
    alert((data.success ? '✅ ' : '❌ ') + data.message);
    if (data.success) checkTailscaleStatus();
  });

  // Auth URL (QR code)
  socket.on('tailscale_auth_url', (data) => {
    hideLoading();
    setButtonsLoading(false);
    authUrl = data.url;
    
    if (data.qr_code) {
      showQRCode(data.url, data.qr_code);
    } else {
      console.warn('⚠️ No QR code data, showing URL only');
      alert("QR kod oluşturulamadı. Tarayıcınızda açın:\n" + data.url);
      const link = document.getElementById("authUrlLink");
      if (link) { link.href = data.url; link.textContent = data.url; }
      document.getElementById("qrSection").classList.remove("hidden");
    }
    startStatusPolling();
  });

  // Connect response
  socket.on('tailscale_connect_response', (data) => {
    hideLoading();
    setButtonsLoading(false);
    if (data.success) { 
      alert((data.already_connected ? "ℹ️ " : "✅ ") + data.message); 
      checkTailscaleStatus(); 
    }
  });

  // Disconnect response
  socket.on('tailscale_disconnect_response', (data) => {
    hideLoading();
    setButtonsLoading(false);
    if (data.success) { alert("✅ " + data.message); checkTailscaleStatus(); }
  });

  // Share response
  socket.on('tailscale_share_response', (data) => {
    hideLoading();
    setButtonsLoading(false);
    if (data.success) displayShareInfo(data.share_info);
  });

  // Funnel response
  socket.on('tailscale_funnel_response', (data) => {
    hideLoading();
    setButtonsLoading(false);
    if (data.success) { 
      updateFunnelUI(data); 
      if (data.url) displayFunnelInfo(data.url, data.ssh_command); 
    }
    else alert("❌ " + data.message);
  });

  // Funnel enable required
  socket.on('tailscale_funnel_enable_required', (data) => {
    hideLoading();
    setButtonsLoading(false);
    if (data.enable_url) {
      const msg = "Funnel URL: " + data.enable_url;
      alert(msg); 
      window.open(data.enable_url, "_blank");
    }
  });
}

// UI Helper Functions
function getSocket() {
  return socket;
}

function setButtonsLoading(isLoading) {
  const buttons = document.querySelectorAll(".action-buttons button, .btn");
  buttons.forEach((btn) => {
    btn.disabled = isLoading;
    btn.style.opacity = isLoading ? "0.5" : "1";
    btn.style.cursor = isLoading ? "not-allowed" : "pointer";
  });
}

function showLoading(message) {
  const indicator = document.getElementById("loadingIndicator");
  const text = document.getElementById("loadingText");
  if (indicator) indicator.classList.add("active");
  if (text) text.textContent = message || "Yükleniyor...";
}

function hideLoading() {
  const indicator = document.getElementById("loadingIndicator");
  if (indicator) indicator.classList.remove("active");
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).catch(() => {
    const el = document.createElement("textarea");
    el.value = text; 
    document.body.appendChild(el); 
    el.select(); 
    document.execCommand("copy"); 
    document.body.removeChild(el);
  });
}

// Status checking
function checkTailscaleStatus() {
  if (!socket) { 
    console.warn("checkTailscaleStatus: no socket"); 
    return; 
  }
  if (!socket.connected) {
    console.warn("checkTailscaleStatus: not connected, waiting...");
    socket.once("connect", () => checkTailscaleStatus());
    return;
  }
  setButtonsLoading(true);
  showLoading(t("remote.checking_status") || "Durum kontrol ediliyor...");
  socket.emit("tailscale_status");
}

function startStatusPolling() {
  if (statusPollingInterval) clearInterval(statusPollingInterval);
  statusPollingInterval = setInterval(() => {
    const qr = document.getElementById("qrSection");
    if (qr && !qr.classList.contains("hidden")) return;
    const s = getSocket();
    if (s && s.connected) s.emit("tailscale_status");
  }, 5000);
}

function stopStatusPolling() {
  if (statusPollingInterval) { 
    clearInterval(statusPollingInterval); 
    statusPollingInterval = null; 
  }
}

// Action functions
function installTailscale() {
  const sock = getSocket(); 
  if (!sock) return;
  const msg = t("remote.install_confirm") || "Tailscale kurulumu başlatılsın mı?";
  if (confirm(msg)) {
    setButtonsLoading(true);
    showLoading(t("remote.installing") || "Kuruluyor...");
    sock.emit("tailscale_install");
  }
}

function connectTailscale() {
  const sock = getSocket(); 
  if (!sock) return;
  setButtonsLoading(true);
  showLoading(t("remote.connecting_wait") || "Bağlanıyor... (30-60 saniye)");
  sock.emit("tailscale_connect");
  setTimeout(() => {
    if (document.getElementById("loadingIndicator").classList.contains("active"))
      showLoading(t("remote.still_waiting") || "Hala bekleniyor...");
  }, 30000);
}

function disconnectTailscale() {
  const sock = getSocket(); 
  if (!sock) return;
  const msg = t("remote.disconnect_confirm") || "Tailscale bağlantısını kesmek istediğinizden emin misiniz?";
  if (confirm(msg)) {
    setButtonsLoading(true);
    showLoading(t("remote.disconnecting") || "Bağlantı kesiliyor...");
    sock.emit("tailscale_disconnect");
  }
}

function copyAuthUrl() {
  if (authUrl) {
    copyToClipboard(authUrl);
    alert(t("remote.copy_success") || "Link kopyalandı!");
  }
}

// QR Code display
function showQRCode(url, qrCodeData) {
  const qrSection = document.getElementById("qrSection");
  const qrCodeImage = document.getElementById("qrCodeImage");
  const authUrlLink = document.getElementById("authUrlLink");
  
  if (qrCodeImage && qrCodeData) {
    qrCodeImage.src = qrCodeData.startsWith("data:image/")
      ? qrCodeData
      : ("data:image/png;base64," + qrCodeData);
    console.log("✅ QR Code displayed");
  }
  
  if (authUrlLink) { 
    authUrlLink.href = url; 
    authUrlLink.textContent = url; 
  }
  if (qrSection) qrSection.classList.remove("hidden");
}

// Status update
function updateStatus(data) {
  const indicator = document.getElementById("statusIndicator");
  const statusText = document.getElementById("statusText");
  const notInstalled = document.getElementById("notInstalledSection");
  const notConnected = document.getElementById("notConnectedSection");
  const connected = document.getElementById("connectedSection");
  
  [notInstalled, notConnected, connected].forEach(s => s && s.classList.add("hidden"));

  if (!data.installed) {
    if (indicator) indicator.classList.remove("connected");
    if (statusText) statusText.textContent = t("remote.not_installed") || "Kurulu Değil";
    if (notInstalled) notInstalled.classList.remove("hidden");
  } else if (!data.connected) {
    if (indicator) indicator.classList.remove("connected");
    if (statusText) statusText.textContent = t("remote.not_connected") || "Bağlı Değil";
    if (notConnected) notConnected.classList.remove("hidden");
  } else {
    if (indicator) indicator.classList.add("connected");
    if (statusText) statusText.textContent = (t("remote.active_status") || "Aktif") + " ✓";
    if (connected) connected.classList.remove("hidden");
    
    const hostnameEl = document.getElementById("hostname");
    if (hostnameEl) hostnameEl.textContent = data.hostname || "-";
    
    const ipList = document.getElementById("ipList");
    if (ipList) {
      ipList.innerHTML = "";
      if (data.ips && data.ips.length > 0) {
        data.ips.forEach(ip => {
          const div = document.createElement("div");
          div.className = "ip-item";
          const copyLabel = t("remote.copy") || "Kopyala";
          div.innerHTML = `<span><strong>http://${ip}:8000</strong></span><button class="copy-btn" onclick="copyToClipboard('http://${ip}:8000')">${copyLabel}</button>`;
          ipList.appendChild(div);
        });
      } else {
        ipList.innerHTML = `<p>${t("remote.no_ips") || "IP adresi bulunamadı"}</p>`;
      }
    }
    updateSharingUI();
  }
}

// Sharing permission management
const SHARING_PERMISSION_KEY = "kuvoz_sharing_permission";
const SHARING_EXPIRY_KEY = "kuvoz_sharing_expiry";

function checkSharingPermission() {
  const p = localStorage.getItem(SHARING_PERMISSION_KEY);
  const e = localStorage.getItem(SHARING_EXPIRY_KEY);
  if (p === "enabled" && e && Date.now() < parseInt(e)) {
    sharingPermissionEnabled = true;
    return true;
  }
  localStorage.removeItem(SHARING_PERMISSION_KEY);
  localStorage.removeItem(SHARING_EXPIRY_KEY);
  sharingPermissionEnabled = false;
  return false;
}

function updateSharingUI() {
  const shareStatusInfo = document.getElementById("shareStatusInfo");
  const shareIndicator = document.getElementById("shareIndicator");
  const shareStatusText = document.getElementById("shareStatusText");
  const enableBtn = document.getElementById("enableSharingBtn");
  const disableBtn = document.getElementById("disableSharingBtn");
  const remoteSupportBtn = document.getElementById("remoteSupportBtn");
  
  if (!shareStatusInfo) return;
  shareStatusInfo.classList.remove("hidden");
  
  const isEnabled = checkSharingPermission();
  
  if (isEnabled) {
    if (shareIndicator) shareIndicator.classList.add("sharing-enabled");
    if (shareStatusText) {
      shareStatusText.textContent = (t("remote.on") || "Açık") + " ⚠️";
      shareStatusText.style.color = "#ffa500";
      shareStatusText.style.fontWeight = "bold";
    }
    if (enableBtn) enableBtn.style.display = "none";
    if (disableBtn) disableBtn.style.display = "inline-block";
    if (remoteSupportBtn) remoteSupportBtn.style.display = "inline-block";
  } else {
    if (shareIndicator) shareIndicator.classList.remove("sharing-enabled");
    if (shareStatusText) {
      shareStatusText.textContent = t("remote.off") || "Kapalı";
      shareStatusText.style.color = "";
      shareStatusText.style.fontWeight = "";
    }
    if (enableBtn) enableBtn.style.display = "inline-block";
    if (disableBtn) disableBtn.style.display = "none";
    if (remoteSupportBtn) remoteSupportBtn.style.display = "none";
  }
  checkFunnelStatus();
}

function checkFunnelStatus() {
  const s = getSocket();
  if (s && s.connected) s.emit("tailscale_funnel_status");
}

function updateFunnelUI(data) {
  const enableFunnelBtn = document.getElementById("enableFunnelBtn");
  const disableFunnelBtn = document.getElementById("disableFunnelBtn");
  const funnelInfoSection = document.getElementById("funnelInfoSection");
  
  if (data.enabled) {
    if (enableFunnelBtn) enableFunnelBtn.style.display = "none";
    if (disableFunnelBtn) disableFunnelBtn.style.display = "inline-block";
    if (funnelInfoSection) funnelInfoSection.classList.remove("hidden");
  } else {
    if (enableFunnelBtn) enableFunnelBtn.style.display = "inline-block";
    if (disableFunnelBtn) disableFunnelBtn.style.display = "none";
    if (funnelInfoSection) funnelInfoSection.classList.add("hidden");
  }
}

function displayFunnelInfo(url, sshCommand) {
  const urlBox = document.getElementById("funnelUrlBox");
  const sshBox = document.getElementById("sshCommandBox");
  if (urlBox) urlBox.textContent = url;
  if (sshBox) sshBox.textContent = sshCommand;
}

function enableFunnel() {
  const msg = t("remote.funnel_warning") || "Public erişim açılacak. Emin misiniz?";
  if (!confirm(msg)) return;
  showLoading(t("remote.funnel_enabling") || "Açılıyor...");
  const s = getSocket(); 
  if (s) s.emit("tailscale_funnel_enable");
}

function disableFunnel() {
  const msg = t("remote.funnel_close_confirm") || "Public erişimi kapatmak istiyor musunuz?";
  if (!confirm(msg)) return;
  showLoading(t("remote.funnel_disabling") || "Kapanıyor...");
  const s = getSocket(); 
  if (s) s.emit("tailscale_funnel_disable");
}

function copyFunnelUrl() {
  const urlBox = document.getElementById("funnelUrlBox");
  if (urlBox) { 
    copyToClipboard(urlBox.textContent); 
    alert(t("remote.copy_success") || "URL Kopyalandı"); 
  }
}

function copySshCommand() {
  const sshBox = document.getElementById("sshCommandBox");
  if (sshBox) { 
    copyToClipboard(sshBox.textContent); 
    alert(t("remote.ssh_copy_success") || "SSH komutu kopyalandı"); 
  }
}

// Sharing confirmation modal
function showEnableSharingConfirm() { 
  const m = document.getElementById("sharingConfirmModal"); 
  if (m) m.classList.remove("hidden"); 
}
function closeSharingConfirm() { 
  const m = document.getElementById("sharingConfirmModal"); 
  if (m) m.classList.add("hidden"); 
}

function enableSharing() {
  const cb = document.getElementById("confirmCheckbox");
  if (!cb || !cb.checked) { 
    alert("Lütfen onay kutusunu işaretleyin."); 
    return; 
  }
  const expiry = Date.now() + 24 * 60 * 60 * 1000;
  localStorage.setItem(SHARING_PERMISSION_KEY, "enabled");
  localStorage.setItem(SHARING_EXPIRY_KEY, expiry.toString());
  closeSharingConfirm();
  updateSharingUI();
  alert(t("remote.sharing_enabled_msg") || "Paylaşım izni verildi.");
}

function disableSharing() {
  const msg = t("remote.sharing_disabled_confirm") || "Paylaşımı kapatmak istiyor musunuz?";
  if (confirm(msg)) {
    localStorage.removeItem(SHARING_PERMISSION_KEY);
    localStorage.removeItem(SHARING_EXPIRY_KEY);
    updateSharingUI();
    const qr = document.getElementById("qrSection");
    if (qr) qr.classList.add("hidden");
    alert(t("remote.sharing_disabled_msg") || "Paylaşım izni kapatıldı.");
  }
}

// Remote support modal
function showRemoteSupport() {
  if (!checkSharingPermission()) {
    alert(t("remote.permission_denied") || "Önce paylaşım izni vermelisiniz.");
    return;
  }
  showLoading(t("remote.creating_link") || "Link oluşturuluyor...");
  const s = getSocket(); 
  if (s) s.emit("tailscale_create_share");
}

function displayShareInfo(shareInfo) {
  currentShareInfo = shareInfo;
  const modal = document.getElementById("remoteSupportModal");
  document.getElementById("shareHostname").textContent = shareInfo.hostname || "-";
  document.getElementById("shareTailscaleIP").textContent = shareInfo.tailscale_ip || "-";
  document.getElementById("shareUrl").textContent = shareInfo.web_url || "-";
  if (modal) modal.classList.remove("hidden");
}

function closeRemoteSupport() {
  const modal = document.getElementById("remoteSupportModal");
  if (modal) modal.classList.add("hidden");
}

function copyShareUrl() {
  if (currentShareInfo) { 
    copyToClipboard(currentShareInfo.web_url); 
    alert(t("remote.copy_success") || "Kopyalandı"); 
  }
}

function copyAllInfo() {
  if (!currentShareInfo) return;
  const text = [
    t("remote.help_subject") || "Kuvoz Uzak Yardım",
    "",
    "Cihaz: " + currentShareInfo.hostname,
    "IP: " + currentShareInfo.tailscale_ip,
    "URL: " + currentShareInfo.web_url,
  ].join("\n");
  copyToClipboard(text);
  alert(t("remote.all_info_copied") || "Tüm bilgiler kopyalandı.");
}

function shareViaEmail() {
  if (!currentShareInfo) return;
  const subject = encodeURIComponent(t("remote.help_subject") || "Kuvoz Uzak Yardım");
  const body = encodeURIComponent("URL: " + currentShareInfo.web_url);
  window.location.href = `mailto:?subject=${subject}&body=${body}`;
}

function shareViaWhatsApp() {
  if (!currentShareInfo) return;
  const text = encodeURIComponent("Kuvoz Uzak Yardım URL: " + currentShareInfo.web_url);
  window.open("https://wa.me/?text=" + text, "_blank");
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  console.log('🔧 Tailscale page initialized');
  
  // Load translations if available
  if (window.kuvozTranslations) {
    applyTranslations();
  }
  
  // Connect to socket
  connectSocket();
  
  // Cleanup on unload
  window.addEventListener("beforeunload", stopStatusPolling);
  
  // Modal click handlers
  document.getElementById("remoteSupportModal")?.addEventListener("click", (e) => {
    if (e.target.id === "remoteSupportModal") closeRemoteSupport();
  });
  
  document.getElementById("sharingConfirmModal")?.addEventListener("click", (e) => {
    if (e.target.id === "sharingConfirmModal") closeSharingConfirm();
  });
});

// Apply translations
function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(element => {
    const key = element.getAttribute('data-i18n');
    const translation = t(key);
    if (element.querySelector('i')) {
      const textNodes = Array.from(element.childNodes).filter(node => node.nodeType === Node.TEXT_NODE);
      if (textNodes.length > 0) {
        textNodes[0].textContent = translation;
      }
    } else {
      element.textContent = translation;
    }
  });
}