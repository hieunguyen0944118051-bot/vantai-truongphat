// BẢO MẬT PHIÊN LÂU DÀI & BỀN VỮNG: Lưu trữ trên localStorage & sessionStorage chống mất đăng nhập trên điện thoại
let token = localStorage.getItem('token') || sessionStorage.getItem('token');
let currentUser = JSON.parse(localStorage.getItem('user') || sessionStorage.getItem('user') || 'null');

function getFormattedDate(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const clientToday = new Date();
const todayStr = getFormattedDate(clientToday);
let selectedDate = todayStr; // Tự động lấy ngày thực tế của máy tính hôm nay
let gpsCache = [];
let driversActivityCache = null;
let dailyKmChart = null;
let topRoutesChart = null;
let customerBreakdownChart = null;

const API_BASE = '/api';

function formatVND(val) {
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(val || 0);
}
function formatDateVN(dateStr) {
  if (!dateStr) return '';
  const parts = dateStr.split('-');
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`;
  return dateStr;
}

function getHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token
  };
}

// Sinh động các phím chọn nhanh ngày thực tế (Hôm nay, Hôm qua, -2, -3, -4 ngày)
function renderQuickDateButtons() {
  const desktopContainer = document.getElementById('quickDateButtonsDesktop');
  const mobileContainer = document.getElementById('quickDateButtonsMobile');

  const now = new Date();
  const days = [];
  for (let i = 0; i < 5; i++) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    const dStr = getFormattedDate(d);
    let label = '';
    if (i === 0) label = `Hôm Nay (${d.getDate()}/${d.getMonth() + 1})`;
    else if (i === 1) label = `Hôm Qua (${d.getDate()}/${d.getMonth() + 1})`;
    else label = `${d.getDate()}/${d.getMonth() + 1}`;
    days.push({ dateStr: dStr, label, dayNum: d.getDate() });
  }

  if (desktopContainer) {
    desktopContainer.innerHTML = days.map(d => {
      const isSelected = (d.dateStr === selectedDate);
      const btnClass = isSelected
        ? 'px-3 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shadow-md shadow-blue-500/20 font-mono text-xs transition'
        : 'px-3 py-1.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200/80 font-mono text-xs transition shadow-2xs';
      return `<button onclick="handleDateSelect('${d.dateStr}')" class="${btnClass}">${d.label}</button>`;
    }).join('');
  }

  if (mobileContainer) {
    mobileContainer.innerHTML = days.map(d => {
      const isSelected = (d.dateStr === selectedDate);
      const btnClass = isSelected
        ? 'px-2.5 py-1 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold shrink-0 shadow-xs font-mono text-[11px]'
        : 'px-2.5 py-1 rounded-xl bg-slate-800 text-slate-300 border border-slate-700 shrink-0 font-mono text-[11px]';
      return `<button onclick="handleDateSelect('${d.dateStr}')" class="${btnClass}">${d.label}</button>`;
    }).join('');
  }
}

// Khởi chạy ứng dụng an toàn
async function initApp() {
  if (window.lucide) lucide.createIcons();

  renderQuickDateButtons();

  const dPick = document.getElementById('desktopDatePicker');
  const mPick = document.getElementById('mobileDatePicker');
  if (dPick) dPick.value = selectedDate;
  if (mPick) mPick.value = selectedDate;

  const displayDate = formatDateVN(selectedDate);
  const bannerEl = document.getElementById('dateBannerText');
  if (bannerEl) bannerEl.innerText = `Đang xem ngày: ${displayDate}`;
  const tripsDateEl = document.getElementById('tripsCurrentDateDisplay');
  if (tripsDateEl) tripsDateEl.innerText = displayDate;

  // Khôi phục phiên đăng nhập bền vững
  if (token) {
    // 1. Mở ngay giao diện ứng dụng lập tức (0ms độ trễ)
    showApp();

    // 2. Xác thực ngầm với máy chủ (Silent Background Re-validation)
    fetch(API_BASE + '/auth/me', { headers: getHeaders() })
      .then(async res => {
        if (res.ok) {
          currentUser = await res.json();
          localStorage.setItem('user', JSON.stringify(currentUser));
          sessionStorage.setItem('user', JSON.stringify(currentUser));
        } else if (res.status === 401) {
          // Token thực sự bị vô hiệu hóa
          console.warn('Phiên đăng nhập đã hết hạn trên máy chủ');
          logout();
        }
      })
      .catch(err => {
        // Lỗi kết nối mạng 4G/Wifi chập chờn -> KHÔNG ĐƯỢC LOGOUT
        console.warn('Mạng chập chờn khi xác thực phiên (giữ nguyên phiên đăng nhập):', err);
      });
  } else {
    showLogin();
  }

  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.onsubmit = handleLogin;
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}

// Xử lý đổi ngày xem số liệu & Nhảy về ngày cũ
function handleDateSelect(dateStr) {
  if (!dateStr) return;
  selectedDate = dateStr;
  renderQuickDateButtons();
  
  const dPick = document.getElementById('desktopDatePicker');
  const mPick = document.getElementById('mobileDatePicker');
  if (dPick) dPick.value = dateStr;
  if (mPick) mPick.value = dateStr;

  const displayDate = formatDateVN(dateStr);
  const bannerEl = document.getElementById('dateBannerText');
  if (bannerEl) bannerEl.innerText = `Đang xem ngày: ${displayDate}`;
  const tripsDateEl = document.getElementById('tripsCurrentDateDisplay');
  if (tripsDateEl) tripsDateEl.innerText = displayDate;

  loadDashboard(dateStr);
  loadDailyTripsFromSheets(dateStr);
}

// Xử lý AI Copilot
async function handleAiCommand(e) {
  e.preventDefault();
  const inputEl = document.getElementById('aiCommandInput');
  const cmd = inputEl.value.trim();
  if (!cmd) return;

  const resBox = document.getElementById('aiResponseBox');
  const resText = document.getElementById('aiResponseText');
  resBox.classList.remove('hidden');
  resText.innerText = '⏳ Đang tra cứu...';

  try {
    const res = await fetch(API_BASE + '/assistant/execute', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ command: cmd })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Lỗi xử lý');

    resText.innerText = result.message;
    inputEl.value = '';
    loadDashboard(selectedDate);
  } catch (err) {
    resText.innerText = '❌ Lỗi: ' + err.message;
  }
  if (window.lucide) lucide.createIcons();
}

function fillAiPrompt(text) {
  const inputEl = document.getElementById('aiCommandInput');
  if (inputEl) {
    inputEl.value = text;
    inputEl.focus();
  }
}

// Đăng nhập an toàn đa tầng với 2FA PIN và Tường Lửa
async function handleLogin(e) {
  if (e && e.preventDefault) e.preventDefault();

  const uInput = document.getElementById('loginUsername');
  const pInput = document.getElementById('loginPassword');
  const pinInput = document.getElementById('loginPin');

  const u = (uInput ? uInput.value : '').trim();
  const p = (pInput ? pInput.value : '').trim();
  const pin = (pinInput ? pinInput.value : '').trim();

  const alertBox = document.getElementById('loginAlert');
  const alertText = document.getElementById('loginAlertText');

  const showError = (msg) => {
    if (alertBox) {
      alertBox.classList.remove('hidden');
      alertBox.style.display = 'flex';
    }
    if (alertText) alertText.innerText = msg;
    if (window.innerWidth < 768) {
      setTimeout(() => alert(msg), 50);
    }
  };

  if (!u || !p) {
    showError('Vui lòng nhập đầy đủ tài khoản và mật khẩu!');
    if (!u && uInput) uInput.focus();
    else if (!p && pInput) pInput.focus();
    return false;
  }

  if (!pin) {
    showError('Vui lòng nhập mã PIN bảo mật cấp 2!');
    if (pinInput) pinInput.focus();
    return false;
  }

  const btnLogin = document.getElementById('btnLogin');
  if (btnLogin) {
    btnLogin.disabled = true;
    btnLogin.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Đang xác thực...';
  }

  const formData = new URLSearchParams();
  formData.append('username', u);
  formData.append('password', p);

  try {
    const res = await fetch(API_BASE + '/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Security-PIN': pin
      },
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Tên đăng nhập, mật khẩu hoặc mã PIN không chính xác!');
    }
    token = data.access_token;
    currentUser = data.user;
    
    // Lưu bền vững vào cả localStorage (cho iPhone/Android/PWA) và sessionStorage
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(currentUser));
    sessionStorage.setItem('token', token);
    sessionStorage.setItem('user', JSON.stringify(currentUser));
    
    if (alertBox) {
      alertBox.classList.add('hidden');
      alertBox.style.display = 'none';
    }
    showApp();
  } catch (err) {
    showError(err.message || 'Lỗi kết nối máy chủ!');
  } finally {
    if (btnLogin) {
      btnLogin.disabled = false;
      btnLogin.innerHTML = '<span>Đăng Nhập An Toàn</span><i data-lucide="arrow-right" class="w-4 h-4"></i>';
      if (window.lucide) lucide.createIcons();
    }
  }
  return false;
}

function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('user');
  token = null;
  currentUser = null;
  showLogin();
}

function showLogin() {
  const loginEl = document.getElementById('loginScreen');
  const appEl = document.getElementById('appScreen');
  if (loginEl) {
    loginEl.classList.remove('hidden');
    loginEl.style.display = 'flex';
  }
  if (appEl) {
    appEl.classList.add('hidden');
    appEl.style.display = 'none';
  }
  const uEl = document.getElementById('loginUsername');
  if (uEl) uEl.value = '';
  const pEl = document.getElementById('loginPassword');
  if (pEl) pEl.value = '';
  const pinEl = document.getElementById('loginPin');
  if (pinEl) pinEl.value = '';
}

function showApp() {
  const loginEl = document.getElementById('loginScreen');
  if (loginEl) {
    loginEl.classList.add('hidden');
    loginEl.style.display = 'none';
  }
  const appEl = document.getElementById('appScreen');
  if (appEl) {
    appEl.classList.remove('hidden');
    appEl.style.display = 'flex';
  }

  if (currentUser) {
    const unEl = document.getElementById('userNameDisplay');
    if (unEl) unEl.innerText = currentUser.full_name || currentUser.username || 'Ban Giám Đốc';
    const urEl = document.getElementById('userRoleDisplay');
    if (urEl) urEl.innerText = currentUser.role || 'Quản trị viên';
  }

  loadFleetCatalog().then(() => switchTab('dashboard'));
  startAutoSyncLoop();
}

// Đổi Mật Khẩu
function openChangePasswordModal() {
  const form = document.getElementById('changePasswordForm');
  if (form) form.reset();
  const alertEl = document.getElementById('changePasswordAlert');
  if (alertEl) alertEl.classList.add('hidden');
  document.getElementById('modalChangePassword').classList.remove('hidden');
}

async function handleChangePassword(e) {
  e.preventDefault();
  const oldPass = document.getElementById('oldPasswordInput').value;
  const newPass = document.getElementById('newPasswordInput').value;
  const confirmPass = document.getElementById('confirmPasswordInput').value;
  const alertEl = document.getElementById('changePasswordAlert');

  if (newPass !== confirmPass) {
    alertEl.className = 'p-3 rounded-xl text-xs border bg-red-50 text-red-600 border-red-200 block';
    alertEl.innerText = 'Mật khẩu mới và xác nhận mật khẩu không trùng khớp!';
    return;
  }

  try {
    const res = await fetch(API_BASE + '/auth/change-password', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        old_password: oldPass,
        new_password: newPass,
        confirm_password: confirmPass
      })
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.detail || 'Lỗi đổi mật khẩu');

    alertEl.className = 'p-3 rounded-xl text-xs border bg-emerald-50 text-emerald-700 border-emerald-200 block';
    alertEl.innerText = result.message;
    setTimeout(() => { closeModal('modalChangePassword'); }, 1500);
  } catch (err) {
    alertEl.className = 'p-3 rounded-xl text-xs border bg-red-50 text-red-600 border-red-200 block';
    alertEl.innerText = err.message;
  }
}

// Navigation Tabs
function switchTab(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.nav-btn').forEach(el => {
    el.classList.remove('bg-gradient-to-r', 'from-blue-600', 'via-indigo-600', 'to-blue-700', 'text-white', 'shadow-md', 'shadow-blue-500/25', 'bg-blue-600');
    el.classList.add('text-slate-300', 'hover:bg-slate-800/80', 'hover:text-white');
  });
  document.querySelectorAll('.mobile-nav-btn').forEach(el => {
    el.classList.remove('text-blue-400', 'bg-blue-500/10');
    el.classList.add('text-slate-400');
  });

  const activeNav = document.getElementById('nav-' + tabId);
  if (activeNav) {
    activeNav.classList.remove('text-slate-300', 'hover:bg-slate-800/80');
    activeNav.classList.add('bg-gradient-to-r', 'from-blue-600', 'via-indigo-600', 'to-blue-700', 'text-white', 'shadow-md', 'shadow-blue-500/25');
  }

  const activeMobNav = document.getElementById('mob-' + tabId);
  if (activeMobNav) {
    activeMobNav.classList.remove('text-slate-400');
    activeMobNav.classList.add('text-blue-400', 'bg-blue-500/10');
  }

  const targetTab = document.getElementById('tab-' + tabId);
  if (targetTab) targetTab.classList.remove('hidden');

  const titles = {
    'dashboard': 'Tổng Quan Vận Hành — Lệnh Điều Xe (Google Sheets) & GPS Bình Anh',
    'trips': 'Lệnh Điều Xe & Bảng Kê Hàng Ngày (Google Sheets)',
    'vehicles': 'Đội Xe & Rơ-Moóc',
    'drivers': 'Tài Xế & Hoạt Động Hôm Nay (GPS Bình Anh)',
    'maintenance': 'Bảo Dưỡng — Thay Nhớt Động Cơ (Google Sheets)',
    'gps': 'Giám Sát Xe (GPS Bình Anh)',
    'tires': 'Thay Vỏ & Bạt',
    'barges': 'Đội Sà Lan',
    'xe': 'Xe & Chi Phí — Giấy tờ, Đổ dầu, Bảo dưỡng, Vỏ, Bạt, Công nợ (Google Sheets)',
    'settings': 'Cài Đặt'
  };
  const titleEl = document.getElementById('pageTitle');
  if (titleEl) titleEl.innerText = titles[tabId] || 'Quản Lý Vận Tải';

  if (tabId === 'dashboard') loadDashboard(selectedDate);
  if (tabId === 'trips') loadDailyTripsFromSheets(selectedDate);
  if (tabId === 'vehicles') loadGroupedVehicles();
  if (tabId === 'drivers') loadDriversActivity();
  if (tabId === 'maintenance') loadMaintenance();
  if (tabId === 'gps') loadGpsLive();
  if (tabId === 'tires') loadTires();
  if (tabId === 'barges') loadBarges();
  if (tabId === 'xe') loadXe();
  if (tabId === 'settings') renderSettings();

  setTimeout(() => {
    if (window.lucide) lucide.createIcons();
  }, 100);
}

// 1. DASHBOARD
const dashboardStatsClientCache = {};
let lastDashStats = null;

function renderSettings() {
  const u = document.getElementById('settingsUser');
  if (u && currentUser) u.innerText = `${currentUser.full_name || currentUser.username} (${currentUser.role})`;
  const box = document.getElementById('settingsSources');
  if (!box) return;
  const g = (lastDashStats && lastDashStats.sources && lastDashStats.sources.gps) || {};
  const line = (ok, label, detail) => `<div class="flex justify-between gap-3 p-3 rounded-xl border ${ok ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-200'}"><span class="font-semibold">${label}</span><span class="text-right">${detail}</span></div>`;
  box.innerHTML = [
    line(!!g.configured && !g.last_error, 'GPS Bình Anh', g.configured ? (g.last_error ? 'Lỗi: ' + escHtml(g.last_error) : `tín hiệu mới nhất ${escHtml(g.newest_gps_time || '—')}`) : 'Chưa cấu hình tài khoản trên Render'),
    line(!!(lastDashStats && !lastDashStats.sheet_warning), 'Sheets lệnh điều xe', lastDashStats ? (lastDashStats.sheet_warning ? escHtml(lastDashStats.sheet_warning) : `đọc lúc ${escHtml(lastDashStats.sources.sheets.sync_time || '—')}`) : 'Mở Tổng quan để kiểm tra'),
    line(!!(typeof xeData !== 'undefined' && xeData), 'Sheets xe & chi phí', (typeof xeData !== 'undefined' && xeData) ? `đọc lúc ${escHtml(xeData.source.read_at)}` : 'Chưa đọc'),
    line(!!(typeof xeData !== 'undefined' && xeData && xeData.write_enabled), 'Ghi vào Sheets', (typeof xeData !== 'undefined' && xeData && xeData.write_enabled) ? 'Đang bật' : 'Chưa bật (cần Apps Script — xem HUONG_DAN.md)'),
  ].join('');
}

function renderDashboardStatsUI(stats) {
  if (!stats) return;

  // % Xe hoạt động ngày
  const activePercentEl = document.getElementById('stat-active-percent');
  const activeRatioEl = document.getElementById('stat-active-ratio');
  const barActiveEl = document.getElementById('bar-active-percent');
  const txtRunningEl = document.getElementById('text-running-count');
  const txtOffEl = document.getElementById('text-off-count');

  if (activePercentEl) activePercentEl.innerText = `${stats.active_percent}%`;
  if (activeRatioEl) activeRatioEl.innerText = `(${stats.active_vehicles_count} / ${stats.total_vehicles} Xe)`;
  if (barActiveEl) barActiveEl.style.width = `${stats.active_percent}%`;
  if (txtRunningEl) txtRunningEl.innerText = `${stats.active_vehicles_count} Xe chạy`;
  if (txtOffEl) txtOffEl.innerText = `${stats.off_vehicles_count} Xe nghỉ cả ngày`;

  const dailyKmEl = document.getElementById('stat-daily-km');
  if (dailyKmEl) dailyKmEl.innerText = `${stats.total_daily_km} km`;

  renderSourceStatus(stats);

  // CẢNH BÁO TRANG CHỦ: XE ĐANG CHẠY NHƯNG KHÔNG QUẸT THẺ LÁI XE
  const noCardRunningBox = document.getElementById('dashboardRunningNoCardAlertBox');
  const noCardRunningList = document.getElementById('dashboardRunningNoCardList');
  const noCardRunningBadge = document.getElementById('dashNoCardRunningBadge');
  const noCardRunningCountBadge = document.getElementById('dashNoCardRunningCountBadge');

  const runningNoCardVehicles = (stats.running_no_card_alerts || []).filter(a => a.speed > 0);

  if (runningNoCardVehicles.length > 0) {
    if (noCardRunningBox) noCardRunningBox.classList.remove('hidden');
    if (noCardRunningBadge) noCardRunningBadge.innerText = `${runningNoCardVehicles.length} Xe Đang Chạy`;
    if (noCardRunningCountBadge) noCardRunningCountBadge.innerText = `${runningNoCardVehicles.length} Xe Vi Phạm`;
    if (noCardRunningList) {
      noCardRunningList.innerHTML = runningNoCardVehicles.map(a => `
        <div class="p-3 rounded-xl bg-white border-2 border-rose-200 shadow-sm space-y-1.5 hover:border-rose-400 transition">
          <div class="flex items-center justify-between">
            <span class="font-mono font-black text-rose-700 text-sm tracking-tight">${a.plate_number}</span>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-600 text-white animate-pulse">
              ⚡ ${a.speed} km/h
            </span>
          </div>
          <div class="text-[11px] font-bold text-slate-800 flex items-center justify-between">
            <span>Tài xế: ${a.driver_name || 'Chưa đăng ký'}</span>
            <span class="text-[10px] font-bold text-rose-600">🚨 Chưa quẹt thẻ</span>
          </div>
          <p class="text-[10px] text-slate-500 truncate" title="${a.address}">
            📍 ${a.address || 'Đang di chuyển'}
          </p>
        </div>
      `).join('');
    }
  } else {
    if (noCardRunningBox) noCardRunningBox.classList.add('hidden');
  }

  renderGpsTable(stats.gps_table || []);
  renderDailyKmChart(stats.km_chart_data || []);
  renderTopRoutesChart(stats.top_routes || []);
  renderCustomerBreakdownChart(stats.customer_breakdown || []);

  const activeTextEl = document.getElementById('activePercentText');
  if (activeTextEl) activeTextEl.innerText = `${stats.active_vehicles_count}/${stats.total_vehicles} Xe (${stats.active_percent}%)`;
  const activeSubEl = document.getElementById('activePercentSub');
  if (activeSubEl) activeSubEl.innerText = `${stats.off_vehicles_count} xe nghỉ bãi`;

  if (window.lucide) lucide.createIcons();
}

async function loadDashboard(dateStr) {
  const d = dateStr || selectedDate;
  
  // Hiển thị tức thì 0ms từ cache phiên
  if (dashboardStatsClientCache[d]) {
    renderDashboardStatsUI(dashboardStatsClientCache[d]);
  }

  try {
    const res = await fetch(`${API_BASE}/dashboard/stats?date=${d}`, { headers: getHeaders() });
    if (!res.ok) return;
    const stats = await res.json();
    dashboardStatsClientCache[d] = stats;
    renderDashboardStatsUI(stats);
    lastDashStats = stats;
    if (typeof loadXe === 'function') {
      if (xeData && !xeData.stale_error) renderDashTodo(xeData);
      if (!xeData || Date.now() - (window.__xeLoadedAt || 0) > 180000) { window.__xeLoadedAt = Date.now(); loadXe(); }
    }
  } catch (err) {
    console.error('Error loading dashboard stats', err);
  }
}

// Danh sách xe – tài xế: nạp 1 lần từ /api/vehicles/fleet (nguồn duy nhất: backend/fleet.py)
const XE_BEN_SET = new Set();
const OFFICIAL_DRIVERS_MAP = {};
let FLEET_TOTAL = 0;

async function loadFleetCatalog() {
  try {
    const res = await fetch(API_BASE + '/vehicles/fleet', { headers: getHeaders() });
    if (!res.ok) return;
    const json = await res.json();
    XE_BEN_SET.clear();
    (json.vehicles || []).forEach(v => {
      const clean = v.plate_number.replace(/[-. ]/g, '').toUpperCase();
      if (v.vehicle_type === 'Xe Ben') XE_BEN_SET.add(clean);
      if (v.driver_name) OFFICIAL_DRIVERS_MAP[clean] = v.driver_name;
    });
    FLEET_TOTAL = json.total || 0;
    const benEl = document.getElementById('fleetCountBen');
    if (benEl) benEl.innerText = `${json.total_ben} Ben • ${json.total_thung} Thùng`;
  } catch (err) { console.warn('Không nạp được danh sách xe', err); }
}

function getOfficialDriverName(plate, fallback) {
  if (!plate) return fallback || 'Chưa phân công';
  const clean = plate.replace(/[-. ]/g, '').toUpperCase();
  return OFFICIAL_DRIVERS_MAP[clean] || fallback || 'Chưa phân công';
}

// Nhãn nguồn số liệu + giờ cập nhật (mọi con số phải ghi nguồn)
function sourceTag(text) {
  return `<span class="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-md">${escHtml(text)}</span>`;
}

function gpsTimeBadge(v) {
  if (!v.gps_time) return '<span class="text-[11px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-md">Không có tín hiệu</span>';
  if (v.is_stale) return `<span class="text-[11px] font-bold text-slate-600 bg-slate-100 border border-slate-300 px-2 py-0.5 rounded-md" title="Tín hiệu cũ hơn 30 phút">⚠ ${escHtml(v.gps_time)}</span>`;
  return `<span class="text-[11px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-md">${escHtml(v.gps_time)}</span>`;
}

function renderSourceStatus(stats) {
  const warnEl = document.getElementById('dashSheetWarning');
  if (warnEl) {
    if (stats.sheet_warning) {
      warnEl.classList.remove('hidden');
      warnEl.querySelector('[data-msg]').innerText = stats.sheet_warning;
    } else {
      warnEl.classList.add('hidden');
    }
  }
  const g = (stats.sources && stats.sources.gps) || {};
  const gpsEl = document.getElementById('stat-gps-status');
  const gpsSubEl = document.getElementById('stat-gps-sub');
  if (gpsEl) {
    gpsEl.innerText = g.newest_gps_time || 'Không có';
    gpsEl.className = 'text-lg md:text-xl font-black mt-1.5 font-mono tracking-tight ' + ((g.stale_count || 0) > 0 ? 'text-slate-600' : 'text-emerald-700');
  }
  if (gpsSubEl) {
    let msg = `${g.stale_count || 0}/${g.total || 0} xe tín hiệu cũ > 30 phút`;
    if (!g.configured) msg = 'Chưa cấu hình tài khoản Bình Anh trên máy chủ';
    else if (g.last_error) msg = 'Lỗi kết nối Bình Anh: ' + g.last_error;
    gpsSubEl.innerText = msg;
  }
  const headerGps = document.getElementById('headerGpsStatus');
  if (headerGps) headerGps.innerText = g.newest_gps_time ? `GPS: ${g.newest_gps_time}` : 'GPS: không có tín hiệu';
  const sheetEl = document.getElementById('stat-sheet-time');
  if (sheetEl) sheetEl.innerText = (stats.sources && stats.sources.sheets && stats.sources.sheets.sync_time) ? `Sheets đọc lúc ${stats.sources.sheets.sync_time}` : 'Sheets: chưa đọc được';
}

function formatPlateBadge(plate) {
  if (!plate) return '—';
  const clean = plate.replace(/[-. ]/g, '').toUpperCase();
  const isBen = XE_BEN_SET.has(clean);
  if (isBen) {
    return `<span class="inline-flex items-center font-mono font-black text-amber-900 bg-amber-100/90 border border-amber-300 px-2 py-0.5 rounded-md text-xs shadow-xs tracking-tight" title="Xe Ben">${plate}</span>`;
  } else {
    return `<span class="inline-flex items-center font-mono font-black text-blue-900 bg-blue-100/90 border border-blue-300 px-2 py-0.5 rounded-md text-xs shadow-xs tracking-tight" title="Xe Thùng">${plate}</span>`;
  }
}

function renderGpsTable(items) {
  const tbody = document.getElementById('gpsDayTableBody');
  if (!tbody) return;
  tbody.innerHTML = items.map(v => {
    let cardBadge = '<span class="px-2 py-0.5 rounded text-[11px] text-slate-500 block text-center">Đậu bãi</span>';
    if (v.card_violation === 'running_no_card') {
      cardBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-black bg-rose-100 text-rose-700 border border-rose-300 block text-center">Chưa quẹt thẻ</span>';
    } else if (v.is_card_swiped) {
      cardBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 block text-center">Đã quẹt thẻ</span>';
    } else if (v.daily_km > 0) {
      cardBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-200 block text-center">Chưa quẹt</span>';
    }
    let stateBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-700 border border-slate-200">Đậu bãi / Tắt máy</span>';
    if (v.op_state === 'running') {
      stateBadge = `<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">Đang chạy ${v.speed} km/h</span>`;
    } else if (v.op_state === 'idling') {
      stateBadge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">Dừng nổ máy</span>';
    }
    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td data-label="Số xe" class="py-3 px-4">${formatPlateBadge(v.plate_number)}</td>
        <td data-label="Tài xế" class="py-3 px-4 font-medium text-slate-800">${escHtml(v.driver_name || getOfficialDriverName(v.plate_number))}</td>
        <td data-label="Thẻ lái xe" class="py-3 px-4 text-center">${cardBadge}</td>
        <td data-label="Trạng thái" class="py-3 px-4 space-y-1">
          <div>${stateBadge}</div>
          <div class="text-[11px] text-slate-600 truncate max-w-xs" title="${escHtml(v.address)}">${escHtml(v.address || '—')}</div>
        </td>
        <td data-label="Km hôm nay" class="py-3 px-4 text-right font-mono font-bold text-blue-600">${v.daily_km} km</td>
        <td data-label="Giờ GPS" class="py-3 px-4 text-center">${gpsTimeBadge(v)}</td>
      </tr>`;
  }).join('');
}

function renderDailyKmChart(kmData) {
  const chartEl = document.getElementById('dailyKmChart');
  if (!chartEl) return;
  const ctx = chartEl.getContext('2d');
  if (dailyKmChart) dailyKmChart.destroy();

  dailyKmChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: kmData.map(d => d.plate),
      datasets: [
        {
          label: 'Quãng đường chạy trong ngày (km)',
          data: kmData.map(d => d.km),
          backgroundColor: '#3b82f6',
          borderRadius: 6,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: (v) => v + ' km' }
        }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderTopRoutesChart(routesData) {
  const container = document.getElementById('topRoutesContainer');
  const countBadge = document.getElementById('topRoutesTotalCountBadge');
  if (!container) return;

  if (!routesData || routesData.length === 0) {
    if (countBadge) countBadge.innerText = '0 Tuyến Hoạt Động';
    container.innerHTML = `
      <div class="p-8 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-slate-400 text-xs">
        <i data-lucide="truck" class="w-8 h-8 mx-auto mb-2 text-slate-300"></i>
        <p class="font-bold">Chưa có dữ liệu chuyến xe hôm nay</p>
        <p class="text-[11px] mt-0.5">Tất cả xe đang nghỉ bãi hoặc chưa cập nhật lệnh điều xe</p>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  const totalTrips = routesData.reduce((acc, r) => acc + (r.trips_count || 0), 0);
  if (countBadge) {
    countBadge.innerText = `${routesData.length} Tuyến • ${totalTrips} Chuyến`;
  }

  container.innerHTML = routesData.map((r, index) => {
    const isTop1 = (index === 0);
    const isTop2 = (index === 1);
    const rankBadgeClass = isTop1 
      ? 'bg-amber-500 text-white font-black shadow-xs' 
      : (isTop2 ? 'bg-slate-700 text-white font-black' : 'bg-slate-200 text-slate-700 font-bold');

    const vehiclesList = r.vehicles || [];
    
    const vehiclesHtml = vehiclesList.map(v => {
      const isBen = (v.vehicle_type === 'Xe Ben');
      const plateBadgeClass = isBen
        ? 'bg-blue-50 text-blue-900 border-blue-200 hover:border-blue-400 hover:bg-blue-100'
        : 'bg-emerald-50 text-emerald-900 border-emerald-200 hover:border-emerald-400 hover:bg-emerald-100';

      const typeIcon = isBen ? '🚛' : '🚚';
      const tripCountBadge = v.trips_count > 1 
        ? `<span class="px-1.5 py-0.2 bg-blue-600 text-white rounded-full text-[9px] font-black">${v.trips_count} chuyến</span>`
        : '';

      return `
        <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-xl border ${plateBadgeClass} text-xs transition shadow-2xs group">
          <span class="text-xs shrink-0">${typeIcon}</span>
          <span class="font-mono font-black text-[11px] tracking-tight text-slate-900">${v.plate_number}</span>
          <span class="text-slate-400 text-[10px]">•</span>
          <span class="font-bold text-slate-700 text-[11px] truncate max-w-[120px]">${v.driver_name}</span>
          ${tripCountBadge}
        </div>
      `;
    }).join('');

    return `
      <div class="p-3.5 bg-slate-50/80 hover:bg-slate-100/90 rounded-2xl border border-slate-200/90 space-y-2.5 transition">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-start gap-2.5 min-w-0">
            <span class="w-5 h-5 rounded-lg ${rankBadgeClass} text-[11px] flex items-center justify-center shrink-0 mt-0.5">
              ${index + 1}
            </span>
            <div class="min-w-0">
              <h4 class="font-extrabold text-slate-900 text-xs md:text-sm flex items-center gap-1.5 flex-wrap">
                <span>${r.route}</span>
              </h4>
              <div class="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500 font-medium">
                ${r.customer_name && r.customer_name !== '—' ? `<span class="text-blue-600 font-bold">🏢 Khách hàng: ${r.customer_name}</span>` : ''}
                ${r.cargo_type && r.cargo_type !== '—' ? `<span class="text-slate-600">📦 Hàng: ${r.cargo_type}</span>` : ''}
              </div>
            </div>
          </div>

          <div class="text-right shrink-0">
            <span class="px-2.5 py-1 bg-blue-600 text-white rounded-xl font-black text-xs shadow-xs">
              ⚡ ${r.trips_count} Chuyến
            </span>
            <p class="text-[10px] text-slate-500 font-bold mt-1">${r.vehicles_count} Xe chạy tuyến này</p>
          </div>
        </div>

        <!-- DANH SÁCH XE CHẠY TUYẾN NÀY (BIỂN SỐ XE + TÀI XẾ) -->
        <div class="pt-2 border-t border-slate-200/60">
          <div class="flex items-center gap-1.5 mb-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            <i data-lucide="truck" class="w-3 h-3 text-blue-600"></i>
            <span>Xe & Tài Xế phụ trách (${vehiclesList.length} xe):</span>
          </div>
          <div class="flex flex-wrap gap-1.5">
            ${vehiclesHtml || '<span class="text-xs text-slate-400 italic">Đang cập nhật danh sách xe</span>'}
          </div>
        </div>
      </div>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

function renderCustomerBreakdownChart(customerData) {
  const chartEl = document.getElementById('customerBreakdownChart');
  if (!chartEl) return;
  const ctx = chartEl.getContext('2d');
  if (customerBreakdownChart) customerBreakdownChart.destroy();

  if (!customerData || customerData.length === 0) {
    ctx.clearRect(0, 0, chartEl.width, chartEl.height);
    return;
  }

  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b'];

  customerBreakdownChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: customerData.map(c => `${c.customer} (${c.percent}%)`),
      datasets: [{
        data: customerData.map(c => c.trips),
        backgroundColor: colors.slice(0, customerData.length),
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { boxWidth: 10, font: { size: 11, weight: 'bold' }, padding: 8 }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const item = customerData[context.dataIndex];
              return ` ${item.customer}: ${item.trips} chuyến (${item.percent}%)`;
            }
          }
        }
      },
      cutout: '62%'
    }
  });
}

// CÀI ĐẶT TRANG TÍNH THÁNG 09
// ===== FILE SHEETS THEO THÁNG =====
const SHEET_SRC_LABEL = { manual: 'Link dán tay', known: 'Đã cấu hình', auto: 'Tự tìm thấy' };

function escHtml(v) {
  return String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function showSheetConfigAlert(msg, ok) {
  const el = document.getElementById('sheetConfigAlert');
  if (!el) return;
  el.innerText = msg;
  el.className = ok
    ? 'p-3 rounded-xl text-xs border bg-emerald-50 text-emerald-800 border-emerald-200 block'
    : 'p-3 rounded-xl text-xs border bg-red-50 text-red-800 border-red-200 block';
}

function renderSheetMonthConfig(cfg) {
  const list = document.getElementById('sheetMonthList');
  if (list) {
    list.innerHTML = (cfg.months || []).map(m => {
      const ok = !!m.sheet_id;
      const badge = ok
        ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">✅ ${SHEET_SRC_LABEL[m.source] || 'Có file'}</span>`
        : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">⚠️ Chưa có file</span>`;
      const link = ok ? `<a href="${escHtml(m.url)}" target="_blank" rel="noopener" class="text-blue-700 underline font-mono text-[10px] break-all">Mở file</a>` : '';
      return `<div class="p-3 rounded-xl border ${m.is_current ? 'border-indigo-400 bg-indigo-50/50' : 'border-slate-200'} space-y-2">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <div><b class="text-slate-900">${escHtml(m.label)}</b>${m.is_current ? ' <span class="text-[10px] text-indigo-700 font-bold">(tháng hiện tại)</span>' : ''}
            <div class="text-[10px] text-slate-500 font-mono">${escHtml(m.file_name)}</div></div>
          <div class="flex items-center gap-2">${badge}${link}</div>
        </div>
        <div class="flex gap-2">
          <input type="text" data-month="${escHtml(m.month)}" placeholder="Dán link tay (chỉ khi tên file khác chuẩn)" value="${m.source === 'manual' ? escHtml(m.url) : ''}" class="sheet-month-input flex-1 p-2 bg-white border border-slate-300 rounded-lg font-mono text-[10px] focus:ring-2 focus:ring-indigo-600 focus:outline-none" />
          <button type="button" onclick="saveSheetMonth('${escHtml(m.month)}')" class="px-3 py-1.5 bg-indigo-600 text-white rounded-lg font-bold text-[11px]">Lưu</button>
        </div>
      </div>`;
    }).join('');
  }
  const folderInp = document.getElementById('cfgSheetFolder');
  if (folderInp) folderInp.value = (cfg.folder_ids || []).join(', ');
  const errEl = document.getElementById('sheetDiscoveryErr');
  if (errEl) {
    const errs = cfg.discovery_errors || [];
    errEl.innerText = errs.length ? '❌ Không đọc được thư mục (kiểm tra đã bật chia sẻ link chưa): ' + errs.join(' | ') : '';
    errEl.classList.toggle('hidden', !errs.length);
  }
}

async function postSheetConfig(body) {
  const res = await fetch(API_BASE + '/trips/sheets-config', {
    method: 'POST', headers: getHeaders(), body: JSON.stringify(body)
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.detail || 'Lỗi lưu cấu hình');
  return json;
}

async function afterSheetConfigChange(json) {
  showSheetConfigAlert(`✅ ${json.message}`, true);
  renderSheetMonthConfig(json);
  for (const k in dailyTripsClientCache) delete dailyTripsClientCache[k];
  handleDateSelect(selectedDate);
}

async function openSheetConfigModal() {
  openModal('modalSheetConfig');
  const alertEl = document.getElementById('sheetConfigAlert');
  if (alertEl) alertEl.className = 'hidden';
  try {
    const res = await fetch(API_BASE + '/trips/sheets-config', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi tải cấu hình');
    renderSheetMonthConfig(json);
  } catch (err) {
    showSheetConfigAlert(`❌ Lỗi: ${err.message}`, false);
  }
}

async function saveSheetMonth(month) {
  const inp = document.querySelector(`.sheet-month-input[data-month="${month}"]`);
  try {
    await afterSheetConfigChange(await postSheetConfig({ month, url: inp ? inp.value.trim() : '' }));
  } catch (err) { showSheetConfigAlert(`❌ Lỗi: ${err.message}`, false); }
}

async function saveSheetFolder() {
  const v = document.getElementById('cfgSheetFolder').value.trim();
  try {
    await afterSheetConfigChange(await postSheetConfig({ folder_ids: v, refresh: true }));
  } catch (err) { showSheetConfigAlert(`❌ Lỗi: ${err.message}`, false); }
}

async function refreshSheetDiscovery() {
  try {
    await afterSheetConfigChange(await postSheetConfig({ refresh: true }));
  } catch (err) { showSheetConfigAlert(`❌ Lỗi: ${err.message}`, false); }
}

// Giữ tên hàm cũ để không lỗi nếu còn nơi gọi
async function saveSheetConfig() { return refreshSheetDiscovery(); }

// 3. TAB BẢNG KÊ (LỆNH ĐIỀU XE & BẢNG KÊ THỰC TẾ HÀNG NGÀY)
const dailyTripsClientCache = {};

function renderDailyTripsTable(data) {
  const timeEl = document.getElementById('sheetsSyncTimeText');
  if (timeEl && data.sync_time) timeEl.innerText = data.sync_time;
  
  const countActiveEl = document.getElementById('sheet-count-active');
  if (countActiveEl) countActiveEl.innerText = `${data.active_count} Xe`;
  
  const countOffEl = document.getElementById('sheet-count-off');
  if (countOffEl) countOffEl.innerText = `${data.off_count} Xe`;
  
  const percentActiveEl = document.getElementById('sheet-percent-active');
  if (percentActiveEl) percentActiveEl.innerText = `${data.active_percent}%`;

  const tbody = document.getElementById('dailyTripsTableBody');
  if (!tbody || !data.all_trips) return;

  tbody.innerHTML = data.all_trips.map(t => {
    const isOff = t.status_code === 'driver_off';

    let opBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${t.op_badge_class || 'bg-slate-100 text-slate-700'}">${t.movement_state || '⚪ Xe đậu bãi'}</span>`;
    let liveAddr = t.gps_address || '—';

    if (isOff) {
      opBadge = '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">⚪ Tài xế nghỉ (Nghỉ cả ngày)</span>';
    }

    const typeBadge = t.vehicle_type === 'Xe Ben'
      ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-100 text-orange-800">Xe Ben</span>'
      : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">Xe Thùng</span>';

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td data-label="STT" class="py-3 px-4 text-center font-bold text-slate-500">${t.stt}</td>
        <td data-label="Số xe" class="py-3 px-4 font-mono font-black text-blue-700 text-sm">${escHtml(t.plate_number)}</td>
        <td data-label="Loại" class="py-3 px-4">${typeBadge}</td>
        <td data-label="Tuyến" class="py-3 px-4 font-bold text-slate-800 ${isOff ? 'text-slate-400 font-normal italic' : ''}">${escHtml(t.route)}</td>
        <td data-label="Hàng" class="py-3 px-4 font-medium text-slate-700">${escHtml(t.cargo_type || '—')}</td>
        <td data-label="Chủ hàng" class="py-3 px-4 font-bold text-slate-900">${escHtml(t.customer_name || '—')}</td>
        <td data-label="GPS" class="py-3 px-4 space-y-1">
          <div>${opBadge}</div>
          <div class="text-[11px] text-slate-600 font-medium flex items-center gap-1 truncate max-w-xs" title="${liveAddr}">
            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-red-500 shrink-0"></i>
            <span class="truncate">${liveAddr}</span>
          </div>
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

async function loadDailyTripsFromSheets(dateStr) {
  const d = dateStr || selectedDate;
  
  // Nếu đã có cache trong phiên, hiển thị ngay tức thì 0ms
  if (dailyTripsClientCache[d]) {
    renderDailyTripsTable(dailyTripsClientCache[d]);
  } else {
    const timeEl = document.getElementById('sheetsSyncTimeText');
    if (timeEl) timeEl.innerText = `Đang đồng bộ ngày ${formatDateVN(d)}...`;
  }

  try {
    const res = await fetch(`${API_BASE}/trips/sheets-live?date=${d}`, { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi đọc Trang Tính');

    const data = json.data;
    dailyTripsClientCache[d] = data;
    setSheetMissingBanner(null);
    renderDailyTripsTable(data);
  } catch (err) {
    console.error('Error loading daily trips:', err);
    // Chưa có file tháng / lỗi đọc: xóa bảng, KHÔNG để lại số liệu ngày khác
    delete dailyTripsClientCache[d];
    setSheetMissingBanner(err.message);
    renderDailyTripsTable({ active_count: 0, off_count: 0, active_percent: 0, sync_time: '—', all_trips: [] });
  }
}

function setSheetMissingBanner(msg) {
  const el = document.getElementById('sheetMissingBanner');
  if (!el) return;
  if (!msg) { el.classList.add('hidden'); el.innerHTML = ''; return; }
  el.innerHTML = `⚠️ ${escHtml(msg)}. Tạo file đúng tên chuẩn trong thư mục Drive tự dò, hoặc bấm
    <button onclick="openSheetConfigModal()" class="underline font-black">File Tháng</button> để dán link.`;
  el.classList.remove('hidden');
}

async function syncGoogleSheetsTrips() {
  const icon = document.getElementById('sheetsSyncIcon');
  if (icon) icon.classList.add('animate-spin');

  try {
    const res = await fetch(`${API_BASE}/trips/sync-sheets?date=${selectedDate}`, { method: 'POST', headers: getHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Lỗi đồng bộ');

    alert(`✅ ${data.message}\n• Xe hoạt động: ${data.active_count} xe\n• Tài xế nghỉ cả ngày: ${data.off_count} xe`);
    loadDailyTripsFromSheets(selectedDate);
    loadDashboard(selectedDate);
  } catch (err) {
    alert('Lỗi: ' + err.message);
  } finally {
    if (icon) icon.classList.remove('animate-spin');
  }
}

function exportTripsExcel() {
  window.open(API_BASE + '/trips/export/excel', '_blank');
}

// 4. TAB ĐỘI XE & RƠ-MOÓC (15 XE BEN & 11 XE THÙNG)
let groupedVehiclesClientCache = null;

async function loadGroupedVehicles() {
  if (groupedVehiclesClientCache) {
    renderVehiclesGroup(groupedVehiclesClientCache.ben_vehicles, 'benVehiclesTableBody');
    renderVehiclesGroup(groupedVehiclesClientCache.thung_vehicles, 'thungVehiclesTableBody');
    if (window.lucide) lucide.createIcons();
  }

  try {
    const res = await fetch(API_BASE + '/vehicles/fleet', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi lấy dữ liệu xe');

    json.ben_vehicles = (json.vehicles || []).filter(v => v.vehicle_type === 'Xe Ben');
    json.thung_vehicles = (json.vehicles || []).filter(v => v.vehicle_type !== 'Xe Ben');
    groupedVehiclesClientCache = json;
    renderVehiclesGroup(json.ben_vehicles, 'benVehiclesTableBody');
    renderVehiclesGroup(json.thung_vehicles, 'thungVehiclesTableBody');

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading grouped vehicles:', err);
  }
}

function renderVehiclesGroup(list, tbodyId) {
  const tbody = document.getElementById(tbodyId);
  if (!tbody) return;
  tbody.innerHTML = (list || []).map((v, idx) => `
    <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
      <td class="py-3 px-4 text-center font-bold text-slate-400">${idx + 1}</td>
      <td class="py-3 px-4 font-mono font-black text-blue-700 text-sm">${escHtml(v.plate_number)}</td>
      <td class="py-3 px-4 font-mono font-bold text-slate-800">${escHtml(v.trailer_number || '—')}</td>
      <td class="py-3 px-4 text-slate-800">${escHtml(v.driver_name || 'Chưa phân công')}</td>
    </tr>
  `).join('');
}

// 5. TAB TÀI XẾ
function renderDriversActivityUI(json) {
  if (!json) return;

  // Render cảnh báo xe chạy không quẹt thẻ RFID
  const noCardContainer = document.getElementById('noCardAlertContainer');
  const noCardList = document.getElementById('noCardVehiclesList');
  const runningBadge = document.getElementById('noCardRunningBadge');
  const totalBadge = document.getElementById('noCardTotalBadge');

  if (noCardContainer && json.no_card_alerts) {
    const runningCount = json.no_card_running_count || 0;
    const totalViolations = json.no_card_alerts.length;

    if (totalViolations > 0) {
      noCardContainer.classList.remove('hidden');
      if (runningBadge) runningBadge.innerText = `${runningCount} Xe Đang Chạy`;
      if (totalBadge) totalBadge.innerText = `Tổng vi phạm: ${totalViolations} xe`;

      noCardList.innerHTML = json.no_card_alerts.map(v => {
        const isRunning = (v.violation_type === 'running_no_card');
        return `
          <div class="p-3 rounded-xl border ${isRunning ? 'bg-rose-100/80 border-rose-300' : 'bg-amber-50 border-amber-200'} space-y-1">
            <div class="flex items-center justify-between">
              <span class="font-mono font-black text-slate-900 text-sm">${v.plate_number}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-black ${isRunning ? 'bg-rose-600 text-white animate-pulse' : 'bg-amber-600 text-white'}">
                ${isRunning ? `🚨 Chạy ${v.speed} km/h` : `⚠️ Đã chạy ${v.daily_km} km`}
              </span>
            </div>
            <div class="text-[11px] font-bold text-slate-800">
              Tài xế phụ trách: <span class="text-blue-700">${escHtml(v.driver_assigned)}</span>${v.phone ? ` (${escHtml(v.phone)})` : ''} • GPS ${escHtml(v.gps_time || '—')}
            </div>
            <div class="text-[10px] text-rose-700 font-bold flex items-center gap-1">
              <i data-lucide="alert-triangle" class="w-3 h-3 shrink-0"></i>
              <span>Thẻ RFID: LÁI XE ĐĂNG XUẤT (Chưa quẹt thẻ)</span>
            </div>
            <div class="text-[10px] text-slate-500 truncate" title="${v.address}">
              📍 ${v.address}
            </div>
          </div>
        `;
      }).join('');
    } else {
      noCardContainer.classList.add('hidden');
    }
  }

  renderDetailedDriversTable(json.drivers || []);
  if (window.lucide) lucide.createIcons();
}

async function loadDriversActivity() {
  if (driversActivityCache) {
    renderDriversActivityUI(driversActivityCache);
  }

  try {
    const res = await fetch(API_BASE + '/drivers/activity', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi tài xế');

    driversActivityCache = json;
    renderDriversActivityUI(json);
  } catch (err) {
    console.error('Error loading drivers activity:', err);
  }
}

function filterDriversActivity() {
  const search = document.getElementById('driverSearchInput').value.toLowerCase();
  if (!driversActivityCache) return;
  const filtered = (driversActivityCache.drivers || []).filter(d => 
    d.full_name.toLowerCase().includes(search) || 
    (d.phone && d.phone.includes(search)) ||
    (d.vehicle_plate && d.vehicle_plate.toLowerCase().includes(search))
  );
  renderDetailedDriversTable(filtered);
}

function renderDetailedDriversTable(list) {
  const tbody = document.getElementById('driversDetailedTableBody');
  if (!tbody) return;
  tbody.innerHTML = (list || []).map(d => `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td data-label="Tài xế" class="py-3 px-4">
          <div class="font-bold text-slate-900 text-sm leading-tight">${escHtml(d.full_name)}</div>
          <div class="text-[11px] text-slate-500 font-mono">${escHtml(d.phone || '—')}</div>
        </td>
        <td data-label="Xe" class="py-3 px-4 font-mono font-black text-blue-700 text-sm">${escHtml(d.vehicle_plate)}</td>
        <td data-label="Thẻ lái xe" class="py-3 px-4 text-center">
          ${d.is_card_swiped
            ? '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800">Đã quẹt</span>'
            : '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">Chưa quẹt</span>'}
        </td>
        <td data-label="Km hôm nay" class="py-3 px-4 text-right font-mono font-black text-blue-600 text-sm">${d.daily_km} km</td>
        <td data-label="Trạng thái" class="py-3 px-4 space-y-0.5">
          <div class="font-bold text-[11px] ${d.speed > 0 ? 'text-emerald-700' : 'text-slate-600'}">${d.movement_state}</div>
          <div class="text-[11px] text-slate-500 truncate max-w-xs" title="${escHtml(d.current_address)}">${escHtml(d.current_address || '—')}</div>
        </td>
        <td data-label="Giờ GPS" class="py-3 px-4 text-center">${gpsTimeBadge(d)}</td>
      </tr>`).join('');
}

// 6. TAB BẢO DƯỠNG THAY NHỚT (KHỚP 100% GOOGLE SHEET)
let maintenanceClientCache = null;

function renderMaintenanceUI(list) {
  const tbody = document.getElementById('maintenanceTableBody');
  if (!tbody || !list) return;

  tbody.innerHTML = list.map(m => {
    const rem = (m.remaining_km !== undefined ? m.remaining_km : (m.diff_km !== undefined ? m.diff_km : '—')).toString();
    const statusText = (m.status || m.status_text || 'Thiếu số liệu').toString();
    const isOver = rem.startsWith('-') || statusText.toLowerCase().includes('quá') || statusText.toLowerCase().includes('sắp');

    let statBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-500 border border-slate-200">Thiếu số liệu</span>';
    if (statusText.toLowerCase().includes('còn xa')) {
      statBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-300">🟢 Còn xa</span>';
    } else if (isOver) {
      statBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-100 text-rose-700 border border-rose-300 animate-pulse">🚨 Sắp / Quá hạn</span>';
    } else if (statusText.toLowerCase().includes('gần')) {
      statBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300">⚠️ Gần tới hạn</span>';
    }

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td class="py-3 px-4 text-center font-bold text-slate-400">${m.stt || '—'}</td>
        <td class="py-3 px-4">${formatPlateBadge(m.plate_number)}</td>
        <td class="py-3 px-4 text-right font-bold text-slate-600">${m.norm_km || m.norm || '15.000'}</td>
        <td class="py-3 px-4 text-right font-mono text-slate-800">${m.last_km || '—'}</td>
        <td class="py-3 px-4 text-center text-slate-600">${m.last_date || '—'}</td>
        <td class="py-3 px-4 text-right font-mono font-black text-slate-900">${m.current_km || '—'}</td>
        <td class="py-3 px-4 text-right font-mono text-indigo-600 font-bold">${m.due_km || '—'}</td>
        <td class="py-3 px-4 text-right font-mono font-black ${isOver ? 'text-red-600' : 'text-emerald-600'}">
          ${rem}
        </td>
        <td class="py-3 px-4 text-center">${statBadge}</td>
        <td class="py-3 px-4 text-slate-700 font-bold text-[11px]">${m.notes || ''}</td>
      </tr>
    `;
  }).join('');
  if (window.lucide) lucide.createIcons();
}

async function loadMaintenance() {
  if (maintenanceClientCache) {
    renderMaintenanceUI(maintenanceClientCache);
  }

  try {
    const res = await fetch(API_BASE + '/maintenance/oil', { headers: getHeaders() });
    const list = await res.json();
    if (!res.ok) {
      const tbody = document.getElementById('maintenanceTableBody');
      if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="py-6 text-center text-rose-700 font-bold">${escHtml(list.detail || 'Không đọc được Google Sheets')}</td></tr>`;
      return;
    }
    maintenanceClientCache = list;
    renderMaintenanceUI(list);
  } catch (err) {
    console.error('Error loading maintenance', err);
  }
}

// BẢN ĐỒ GIÁM SÁT HÀNH TRÌNH LEAFLET.JS (REALTIME FLEET MAP)
function focusVehicleOnMap(plate) {}
function fitAllFleetBounds() {}
function handleMapSearch(q) {}
function filterMapMarkers(t) {}

// 7. GPS & TIRES & BARGES
let tiresClientCache = null;
let bargesClientCache = null;

async function loadGpsLive() {
  const timeEl = document.getElementById('gpsLastUpdateTime');
  if (timeEl && gpsCache.length === 0) timeEl.innerText = 'Đang đồng bộ từ Bình Anh GPS...';

  try {
    const res = await fetch(API_BASE + '/gps/live', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi GPS');

    gpsCache = json.data || [];
    if (timeEl) timeEl.innerText = (json.status && json.status.newest_gps_time) || 'không có tín hiệu';

    const tbody = document.getElementById('gpsTableBody');
    if (tbody) {
      tbody.innerHTML = gpsCache.map(v => {
        let statusBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600">⚪ Tắt máy</span>';
        if (v.status_type === 'running') {
          statusBadge = `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700 animate-pulse flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> ${v.speed} km/h</span>`;
        } else if (v.status_type === 'idling') {
          statusBadge = '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 w-fit">🟡 Dừng nổ máy</span>';
        }

        let cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] text-slate-400 block text-center font-medium">Đậu bãi</span>';
        if (v.card_violation === 'running_no_card') {
          cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-black bg-rose-100 text-rose-700 border border-rose-300 animate-pulse block text-center shadow-xs">🚨 Chưa quẹt thẻ</span>';
        } else if (v.is_card_swiped) {
          cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 block text-center">🟢 Đã quẹt thẻ</span>';
        } else if (v.daily_km > 0) {
          cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200 block text-center">⚠️ Chưa quẹt</span>';
        }

        return `
          <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
            <td class="py-3 px-4 font-mono font-black text-blue-700 text-sm cursor-pointer hover:underline" onclick="focusVehicleOnMap('${v.plate_number}')" title="Nhấp để định vị trên bản đồ">${v.plate_number} 🎯</td>
            <td class="py-3 px-4 font-mono font-bold text-slate-700">${v.trailer_number || '—'}</td>
            <td class="py-3 px-4">${statusBadge}</td>
            <td class="py-3 px-4 text-center">${cardBadge}</td>
            <td class="py-3 px-4 text-right font-mono font-bold text-blue-600">${v.daily_km} km</td>
            <td class="py-3 px-4 text-slate-700 max-w-sm truncate" title="${v.address}">${v.address || 'Đang cập nhật...'}</td>
            <td class="py-3 px-4 font-medium text-slate-800">${getOfficialDriverName(v.plate_number, v.driver_name)}</td>
            <td class="py-3 px-4 text-center">${gpsTimeBadge(v)}</td>
          </tr>
        `;
      }).join('');
    }

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error fetching GPS:', err);
  }
}

// AUTO-SYNC REALTIME ENGINE (CHỦ ĐỘNG ĐỒNG BỘ MỖI 15S)
let autoSyncCountdown = 15;
let autoSyncInterval = null;

function startAutoSyncLoop() {
  if (autoSyncInterval) clearInterval(autoSyncInterval);
  autoSyncCountdown = 15;

  autoSyncInterval = setInterval(async () => {
    autoSyncCountdown--;
    const timerEl = document.getElementById('liveSyncCountdownBadge');
    if (timerEl) timerEl.innerText = `${autoSyncCountdown}s`;

    if (autoSyncCountdown <= 0) {
      autoSyncCountdown = 15;
      await silentRefreshLiveGps();
    }
  }, 1000);
}

async function silentRefreshLiveGps() {
  try {
    const res = await fetch(API_BASE + '/gps/live', { headers: getHeaders() });
    if (!res.ok) return;
    const json = await res.json();
    gpsCache = json.data || [];
    
    const timeEl = document.getElementById('gpsLastUpdateTime');
    if (timeEl && json.status) timeEl.innerText = json.status.newest_gps_time || 'không có tín hiệu';
    const headerGps = document.getElementById('headerGpsStatus');
    if (headerGps && json.status) headerGps.innerText = json.status.newest_gps_time ? `GPS: ${json.status.newest_gps_time}` : 'GPS: không có tín hiệu';

    const activeTabEl = document.querySelector('.tab-content:not(.hidden)');
    const activeTabId = activeTabEl ? activeTabEl.id.replace('tab-', '') : '';

    if (activeTabId === 'dashboard') {
      const runningNoCard = gpsCache.filter(v => v.card_violation === 'running_no_card' && v.speed > 0);
      const alertBox = document.getElementById('dashboardRunningNoCardAlertBox');
      const listEl = document.getElementById('dashboardRunningNoCardList');
      const countBadge = document.getElementById('dashNoCardRunningCountBadge');
      if (alertBox && listEl && countBadge) {
        if (runningNoCard.length > 0) {
          alertBox.classList.remove('hidden');
          countBadge.innerText = `${runningNoCard.length} Xe Đang Vi Phạm Nóng`;
          listEl.innerHTML = runningNoCard.map(v => `
            <div class="bg-white p-3 rounded-xl border border-rose-200 shadow-xs flex items-center justify-between">
              <div class="space-y-0.5">
                <div class="flex items-center gap-1.5">
                  <span class="font-mono font-black text-rose-700">${v.plate_number}</span>
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-black bg-rose-600 text-white animate-pulse">⚡ ${v.speed} km/h</span>
                </div>
                <p class="text-slate-700 font-medium text-[11px]">Tài xế: <b>${v.driver_name || 'Chưa đăng ký'}</b></p>
                <p class="text-[10px] text-slate-500 truncate max-w-[200px]">📍 ${v.address || 'Đang cập nhật'}</p>
              </div>
              <span class="text-xs text-rose-700 font-bold bg-rose-100 px-2 py-1 rounded-lg">🚨 Chưa Quẹt</span>
            </div>
          `).join('');
        } else {
          alertBox.classList.add('hidden');
        }
      }
    }
  } catch (err) {}
}

async function triggerGpsSync() {
  await loadGpsLive();
  loadDashboard(selectedDate);
}

function renderTiresUI(tireData) {
  const tireTbody = document.getElementById('tireTableBody');
  if (!tireTbody || !tireData) return;
  tireTbody.innerHTML = (tireData.summary || []).map(t => `
    <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
      <td class="py-3 px-4 font-mono font-bold text-blue-700">${t.plate_number}</td>
      <td class="py-3 px-4 text-center font-bold ${t.q1 > 0 ? 'text-slate-800' : 'text-slate-300'}">${t.q1 || '—'}</td>
      <td class="py-3 px-4 text-center font-bold ${t.q2 > 0 ? 'text-slate-800' : 'text-slate-300'}">${t.q2 || '—'}</td>
      <td class="py-3 px-4 text-center font-bold ${t.q3 > 0 ? 'text-slate-800' : 'text-slate-300'}">${t.q3 || '—'}</td>
      <td class="py-3 px-4 text-center font-bold ${t.q4 > 0 ? 'text-slate-800' : 'text-slate-300'}">${t.q4 || '—'}</td>
      <td class="py-3 px-4 text-right font-black text-blue-700">${t.total_tires} vỏ</td>
    </tr>
  `).join('');
  if (window.lucide) lucide.createIcons();
}

async function loadTires() {
  if (tiresClientCache) {
    renderTiresUI(tiresClientCache);
  }

  try {
    const res = await fetch(API_BASE + '/maintenance/tires/summary', { headers: getHeaders() });
    const tireData = await res.json();
    tiresClientCache = tireData;
    renderTiresUI(tireData);
  } catch (err) {
    console.error('Error loading tires', err);
  }
}

function renderBargesUI(list) {
  const tbody = document.getElementById('bargesTableBody');
  if (!tbody || !list) return;
  tbody.innerHTML = list.map(b => {
    const isOwned = b.ownership_type === 'owned';
    const typeBadge = isOwned
      ? '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-blue-100 text-blue-700">Sà lan nhà</span>'
      : '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">Sà lan thuê</span>';

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td class="py-3 px-4 font-bold text-slate-800">${b.name}</td>
        <td class="py-3 px-4 font-mono text-slate-600">${b.registration_number || '—'}</td>
        <td class="py-3 px-4 text-right font-bold text-slate-700">${b.payload_capacity} tấn</td>
        <td class="py-3 px-4 text-center">${typeBadge}</td>
        <td class="py-3 px-4 text-slate-600">${b.owner_name ? `${b.owner_name} (${b.owner_phone || '—'})` : 'Công ty Trường Phát'}</td>
      </tr>
    `;
  }).join('');
  if (window.lucide) lucide.createIcons();
}

async function loadBarges() {
  if (bargesClientCache) {
    renderBargesUI(bargesClientCache);
  }

  try {
    const res = await fetch(API_BASE + '/barges', { headers: getHeaders() });
    const list = await res.json();
    bargesClientCache = list;
    renderBargesUI(list);
  } catch (err) {
    console.error('Error loading barges', err);
  }
}

function openModal(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

// ĐỔI MÃ PIN CẤP 2 (chỉ admin) — nằm trong hộp thoại Đổi mật khẩu
async function handleUpdatePin(e) {
  e.preventDefault();
  const oldPin = document.getElementById('oldPinInput').value.trim();
  const newPin = document.getElementById('newPinInput').value.trim();
  const alertBox = document.getElementById('pinAlertBox');

  try {
    const res = await fetch(API_BASE + '/auth/update-pin', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ old_pin: oldPin, new_pin: newPin })
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi cập nhật mã PIN');

    alertBox.className = 'p-2.5 rounded-xl text-xs border bg-emerald-50 text-emerald-800 border-emerald-200 block';
    alertBox.innerText = `✅ ${json.message}`;
    document.getElementById('updatePinForm').reset();
    setTimeout(() => { alertBox.className = 'hidden'; }, 3000);
  } catch (err) {
    alertBox.className = 'p-2.5 rounded-xl text-xs border bg-rose-50 text-rose-800 border-rose-200 block';
    alertBox.innerText = `❌ ${err.message}`;
  }
}

// ==========================================
// PWA MOBILE APP INSTALLATION CONTROLLER
// ==========================================
let deferredPwaPrompt = null;

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      console.log('✅ ServiceWorker registered with scope:', reg.scope);
    }).catch((err) => {
      console.log('ServiceWorker registration error:', err);
    });
  });
}

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPwaPrompt = e;
  console.log('⚡ beforeinstallprompt fired - 1-Click install ready!');

  const btnAuto = document.getElementById('btnPwaAutoInstallAndroid');
  if (btnAuto) {
    btnAuto.classList.remove('opacity-50', 'cursor-not-allowed');
  }

  checkAndShowPwaBanner();
});

window.addEventListener('appinstalled', () => {
  console.log('🎉 Vận Tải Trường Phát app was installed successfully!');
  deferredPwaPrompt = null;
  const banner = document.getElementById('pwaMobileInstallBanner');
  if (banner) banner.classList.add('hidden');
});

function isRunningStandalone() {
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone || document.referrer.includes('android-app://');
}

function checkAndShowPwaBanner() {
  if (isRunningStandalone()) return;
  if (sessionStorage.getItem('pwa_banner_dismissed')) return;

  const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
  if (isMobile) {
    setTimeout(() => {
      const banner = document.getElementById('pwaMobileInstallBanner');
      if (banner && !isRunningStandalone() && !sessionStorage.getItem('pwa_banner_dismissed')) {
        banner.classList.remove('hidden');
        if (window.lucide) lucide.createIcons();
      }
    }, 1500);
  }
}

function dismissPwaBanner() {
  const banner = document.getElementById('pwaMobileInstallBanner');
  if (banner) banner.classList.add('hidden');
  sessionStorage.setItem('pwa_banner_dismissed', 'true');
}

function openInstallAppModal() {
  const isAndroid = /Android/i.test(navigator.userAgent);
  if (isAndroid) {
    switchInstallPlatformTab('android');
  } else {
    switchInstallPlatformTab('ios');
  }

  openModal('modalInstallApp');
}

function switchInstallPlatformTab(platform) {
  const tabIos = document.getElementById('installTabContentIos');
  const tabAndroid = document.getElementById('installTabContentAndroid');
  const btnIos = document.getElementById('tabBtnInstallIos');
  const btnAndroid = document.getElementById('tabBtnInstallAndroid');

  if (platform === 'ios') {
    tabIos.classList.remove('hidden');
    tabAndroid.classList.add('hidden');
    btnIos.className = 'flex-1 py-3 px-4 flex items-center justify-center gap-2 border-b-2 border-blue-600 text-blue-700 bg-white transition';
    btnAndroid.className = 'flex-1 py-3 px-4 flex items-center justify-center gap-2 border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition';
  } else {
    tabIos.classList.add('hidden');
    tabAndroid.classList.remove('hidden');
    btnAndroid.className = 'flex-1 py-3 px-4 flex items-center justify-center gap-2 border-b-2 border-emerald-600 text-emerald-700 bg-white transition';
    btnIos.className = 'flex-1 py-3 px-4 flex items-center justify-center gap-2 border-b-2 border-transparent text-slate-500 hover:text-slate-800 transition';
  }

  if (window.lucide) lucide.createIcons();
}

async function triggerPwaInstall() {
  if (deferredPwaPrompt) {
    deferredPwaPrompt.prompt();
    const { outcome } = await deferredPwaPrompt.userChoice;
    console.log(`User response to the install prompt: ${outcome}`);
    if (outcome === 'accepted') {
      closeModal('modalInstallApp');
      dismissPwaBanner();
    }
    deferredPwaPrompt = null;
  } else {
    alert('Để cài đặt trên Android: Bạn hãy nhấn vào dấu 3 chấm (⋮) ở góc trên bên phải trình duyệt Chrome và chọn "Cài đặt ứng dụng" hoặc "Thêm vào màn hình chính".');
  }
}

function copyAppUrl() {
  const url = window.location.origin;
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(() => {
      const btn = document.getElementById('btnCopyAppUrl');
      if (btn) {
        btn.innerHTML = '<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-300"></i><span>Đã Sao Chép!</span>';
        if (window.lucide) lucide.createIcons();
      }
      alert('ĐÃ SAO CHÉP LINK WEB!\n\n👉 Bạn hãy mở ứng dụng SAFARI trên iPhone, dán link vào và bấm nút Chia Sẻ [↑] để "Thêm vào MH chính".');
    }).catch(() => {
      prompt('Sao chép đường link này và dán vào trình duyệt Safari trên iPhone:', url);
    });
  } else {
    prompt('Sao chép đường link này và dán vào trình duyệt Safari trên iPhone:', url);
  }
}

function checkInAppBrowser() {
  const ua = navigator.userAgent || navigator.vendor || window.opera || '';
  const isIos = /iPhone|iPad|iPod/i.test(ua);
  const isZalo = /Zalo|ZaloPC|ZaloTheme/i.test(ua);
  const isFb = /FBAN|FBAV|Instagram|Messenger/i.test(ua);
  const isTikTok = /musical_ly|ByteLocale|BytedanceWebview/i.test(ua);

  if (isIos && (isZalo || isFb || isTikTok)) {
    const topBanner = document.getElementById('inAppBrowserWarningBanner');
    if (topBanner) {
      topBanner.classList.remove('hidden');
      if (window.lucide) lucide.createIcons();
    }
  }
}

// Auto check on load
window.addEventListener('DOMContentLoaded', checkInAppBrowser);
setTimeout(checkInAppBrowser, 800);
setTimeout(checkAndShowPwaBanner, 1000);


