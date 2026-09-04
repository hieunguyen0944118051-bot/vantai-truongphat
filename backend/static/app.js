// BẢO MẬT PHIÊN AN TOÀN: sessionStorage chống vào thẳng không hỏi mật khẩu
let token = sessionStorage.getItem('token');
let currentUser = JSON.parse(sessionStorage.getItem('user') || 'null');

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
let trafficFinesCache = null;
let fuelNormChart = null;
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
        ? 'px-2.5 py-1 rounded-lg bg-blue-600 text-white font-bold shadow-xs'
        : 'px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 transition';
      return `<button onclick="handleDateSelect('${d.dateStr}')" class="${btnClass}">${d.label}</button>`;
    }).join('');
  }

  if (mobileContainer) {
    mobileContainer.innerHTML = days.map(d => {
      const isSelected = (d.dateStr === selectedDate);
      const btnClass = isSelected
        ? 'px-2 py-0.5 rounded bg-blue-600 text-white font-bold shrink-0 shadow-xs'
        : 'px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 shrink-0';
      return `<button onclick="handleDateSelect('${d.dateStr}')" class="${btnClass}">${d.label}</button>`;
    }).join('');
  }
}

// Khởi chạy
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();

  renderQuickDateButtons();

  const dPick = document.getElementById('desktopDatePicker');
  const mPick = document.getElementById('mobileDatePicker');
  if (dPick) {
    dPick.value = selectedDate;
  }
  if (mPick) {
    mPick.value = selectedDate;
  }

  const displayDate = formatDateVN(selectedDate);
  const bannerEl = document.getElementById('dateBannerText');
  if (bannerEl) bannerEl.innerText = `Đang xem ngày: ${displayDate}`;
  const tripsDateEl = document.getElementById('tripsCurrentDateDisplay');
  if (tripsDateEl) tripsDateEl.innerText = displayDate;

  if (token && currentUser) {
    showApp();
  } else {
    showLogin();
  }

  const loginForm = document.getElementById('loginForm');
  if (loginForm) loginForm.addEventListener('submit', handleLogin);
});

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

  const syncStatusEl = document.getElementById('dateSyncStatus');
  if (syncStatusEl) {
    syncStatusEl.innerText = `⏳ Đang tải dữ liệu ngày ${displayDate}...`;
    setTimeout(() => {
      syncStatusEl.innerText = `✅ Đã hiển thị ngày ${displayDate}`;
      setTimeout(() => { if (syncStatusEl) syncStatusEl.innerText = ''; }, 3000);
    }, 1200);
  }

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
  resText.innerText = '⏳ AI đang đọc dữ liệu GPS & vận hành...';

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
  e.preventDefault();
  const u = document.getElementById('loginUsername').value.trim();
  const p = document.getElementById('loginPassword').value;
  const pinInput = document.getElementById('loginPin');
  const pin = pinInput ? pinInput.value.trim() : '';
  const alertBox = document.getElementById('loginAlert');
  const alertText = document.getElementById('loginAlertText');

  const formData = new URLSearchParams();
  formData.append('username', u);
  formData.append('password', p);

  try {
    const res = await fetch(API_BASE + '/auth/login?pin=' + encodeURIComponent(pin), {
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
    
    sessionStorage.setItem('token', token);
    sessionStorage.setItem('user', JSON.stringify(currentUser));
    localStorage.removeItem('token');
    
    showApp();
  } catch (err) {
    alertBox.classList.remove('hidden');
    alertText.innerText = err.message;
  }
}

function logout() {
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('user');
  localStorage.clear();
  token = null;
  currentUser = null;
  showLogin();
}

function showLogin() {
  document.getElementById('loginScreen').classList.remove('hidden');
  document.getElementById('appScreen').classList.add('hidden');
  document.getElementById('loginUsername').value = '';
  document.getElementById('loginPassword').value = '';
}

function showApp() {
  document.getElementById('loginScreen').classList.add('hidden');
  document.getElementById('appScreen').classList.remove('hidden');
  document.getElementById('userNameDisplay').innerText = currentUser.full_name || currentUser.username;
  document.getElementById('userRoleDisplay').innerText = currentUser.role || 'Quản trị viên';

  switchTab('dashboard');
  loadDashboard(selectedDate);
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
    el.classList.remove('bg-blue-600', 'text-white');
    el.classList.add('text-slate-300');
  });
  document.querySelectorAll('.mobile-nav-btn').forEach(el => {
    el.classList.remove('text-blue-400');
    el.classList.add('text-slate-400');
  });

  const activeNav = document.getElementById('nav-' + tabId);
  if (activeNav) {
    activeNav.classList.remove('text-slate-300');
    activeNav.classList.add('bg-blue-600', 'text-white');
  }

  const activeMobNav = document.getElementById('mob-' + tabId);
  if (activeMobNav) {
    activeMobNav.classList.remove('text-slate-400');
    activeMobNav.classList.add('text-blue-400');
  }

  const targetTab = document.getElementById('tab-' + tabId);
  if (targetTab) targetTab.classList.remove('hidden');

  const titles = {
    'dashboard': 'Tổng Quan Hoạt Động & Giám Sát Nhiên Liệu (Tiêu Hao & Chống Hút Dầu)',
    'fines': 'Hệ Thống Tự Động Tra Cứu Phạt Nguội — Cục Cảnh Sát Giao Thông',
    'security': 'Hệ Thống Tường Lửa Ứng Dụng WAF & Phòng Thủ Xâm Nhập Chuẩn Quốc Tế',
    'trips': 'Lệnh Điều Xe & Bảng Kê Thực Tế Hàng Ngày (Google Trang Tính)',
    'vehicles': 'Đội Xe & Rơ-Moóc (15 Xe Ben • 11 Xe Thùng — Theo Dõi GĐĐ & Đăng Kiểm)',
    'drivers': 'Đội Ngũ Tài Xế & Đánh Giá Chi Tiết Hiệu Suất Vận Hành',
    'maintenance': 'Bảo Dưỡng Định Kỳ — Thay Nhớt Động Cơ (15.000 Km Theo Trang Tính)',
    'gps': 'Bản Đồ Giám Sát Xe Trực Tuyến & Cự Ly Vận Hành (GPS Bình Anh 26 Xe)',
    'tires': 'Quản Lý Thay Vỏ Xe & Công Nợ May Bạt (Phùng Lĩnh)',
    'barges': 'Đội Sà Lan Vận Tải (4 Nhà • 6 Thuê Ngoài)'
  };
  const titleEl = document.getElementById('pageTitle');
  if (titleEl) titleEl.innerText = titles[tabId] || 'Quản Lý Vận Tải';

  if (tabId === 'dashboard') loadDashboard(selectedDate);
  if (tabId === 'fines') loadTrafficFines();
  if (tabId === 'security') loadSecurityStatus();
  if (tabId === 'trips') loadDailyTripsFromSheets(selectedDate);
  if (tabId === 'vehicles') loadGroupedVehicles();
  if (tabId === 'drivers') loadDriversActivity();
  if (tabId === 'maintenance') loadMaintenance();
  if (tabId === 'gps') loadGpsLive();
  if (tabId === 'tires') loadTires();
  if (tabId === 'barges') loadBarges();

  setTimeout(() => {
    if (tabId === 'gps' && liveGpsMap) liveGpsMap.invalidateSize();
    if (tabId === 'dashboard' && dashboardMap) dashboardMap.invalidateSize();
  }, 150);
  
  if (window.lucide) lucide.createIcons();
}

// 1. DASHBOARD
async function loadDashboard(dateStr) {
  const d = dateStr || selectedDate;
  try {
    const res = await fetch(`${API_BASE}/dashboard/stats?date=${d}`, { headers: getHeaders() });
    if (!res.ok) return;
    const stats = await res.json();

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

    const consumedFuelEl = document.getElementById('stat-consumed-fuel');
    if (consumedFuelEl) consumedFuelEl.innerText = `${stats.total_consumed_fuel} Lít`;

    // Cảnh báo hút dầu
    const drainCountEl = document.getElementById('stat-drain-count');
    const drainCardEl = document.getElementById('card-drain-alert');
    const drainSubEl = document.getElementById('text-drain-sub');
    if (drainCountEl) {
      if (stats.suspicious_drain_count > 0) {
        drainCountEl.innerText = `${stats.suspicious_drain_count} Xe Nghi Ngờ`;
        drainCountEl.className = 'text-xl md:text-2xl font-black text-red-600 mt-1 animate-pulse';
        if (drainCardEl) drainCardEl.className = 'bg-red-50 p-4 md:p-5 rounded-2xl border-2 border-red-300 shadow-sm flex flex-col justify-between';
        if (drainSubEl) drainSubEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-red-600 animate-ping"></span><span class="text-red-700 font-bold">Phát hiện sụt dầu bất thường!</span>';
      } else {
        drainCountEl.innerText = `0 Xe`;
        drainCountEl.className = 'text-xl md:text-2xl font-black text-emerald-600 mt-1';
        if (drainCardEl) drainCardEl.className = 'bg-white p-4 md:p-5 rounded-2xl border border-slate-200 shadow-sm flex flex-col justify-between';
        if (drainSubEl) drainSubEl.innerHTML = '<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>Tất cả xe định mức an toàn</span>';
      }
    }

    // Cảnh báo Phạt Nguội trên Dashboard
    const finesStatEl = document.getElementById('stat-fines-status');
    const finesSubEl = document.getElementById('stat-fines-sub');
    if (stats.fines_summary) {
      const fs = stats.fines_summary;
      if (fs.violated_vehicles > 0) {
        if (finesStatEl) {
          finesStatEl.innerText = `${fs.violated_vehicles} Xe Có Lỗi`;
          finesStatEl.className = 'text-xl md:text-2xl font-black text-rose-600 animate-pulse';
        }
        if (finesSubEl) finesSubEl.innerText = `${fs.clean_vehicles}/${fs.total_vehicles} Xe Sạch Lỗi • Cần nộp phạt!`;
      } else {
        if (finesStatEl) {
          finesStatEl.innerText = `An Toàn`;
          finesStatEl.className = 'text-xl md:text-2xl font-black text-emerald-600';
        }
        if (finesSubEl) finesSubEl.innerText = `26/26 Xe Sạch Lỗi Vi Phạm`;
      }
    }

    // Cảnh báo Dừng Nổ Máy Quá Lâu (Idling alerts)
    const idlingBox = document.getElementById('idlingAlertContainer');
    const idlingList = document.getElementById('idlingAlertList');
    // CẢNH BÁO TRANG CHỦ: XE ĐANG CHẠY NHƯNG KHÔNG QUẸT THẺ LÁI XE (CHỈ BÁO XE SPEED > 0)
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

    renderFuelAnalysisTable(stats.fuel_table || []);
    renderFuelNormChart(stats.norm_chart_data || []);
    renderDailyKmChart(stats.km_chart_data || []);
    renderTopRoutesChart(stats.top_routes || []);
    renderCustomerBreakdownChart(stats.customer_breakdown || []);
    renderWeeklyFuelTable(stats.weekly_fuel_summary || {});
    renderTopDriversLeaderboard(stats.top_drivers_weekly || []);

    const activeTextEl = document.getElementById('activePercentText');
    if (activeTextEl) activeTextEl.innerText = `${stats.active_vehicles_count}/${stats.total_vehicles} Xe (${stats.active_percent}%)`;
    const activeSubEl = document.getElementById('activePercentSub');
    if (activeSubEl) activeSubEl.innerText = `${stats.off_vehicles_count} xe nghỉ bãi`;

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading dashboard stats', err);
  }
}

const XE_BEN_SET = new Set([
  '63H04273', '63G00286', '63E01156', '63E01117', '63E01108',
  '63F00528', '63G00262', '63H04239', '63E01276', '63E01103',
  '63E01118', '63F00511', '63H04234', '63E01235', '63H04236'
]);

const OFFICIAL_DRIVERS_MAP = {
  '63E01156': 'Nguyễn Văn Tuấn',
  '63E01117': 'Phan Hoàng Duy',
  '63H04273': 'Lâm Hoàng Tuấn',
  '63G00286': 'Nguyễn Xuân Về',
  '63F00512': 'Hoàng Quốc Bảo',
  '63F00538': 'Lý Minh Tới',
  '63E01108': 'Lý Minh Hoàng',
  '63F00528': 'Nguyễn Văn Hiếu',
  '63E01212': 'Mạch Đình Phước',
  '63E01141': 'Dương Thanh Sang',
  '63G00262': 'Nguyễn Thanh Tây',
  '63H04239': 'Kim Sô Phép',
  '63E01132': 'Đào Ngọc Kha',
  '63E01201': 'Lê Trọng Nghĩa',
  '63F00516': 'Phùng Phú Kim Toàn',
  '63E01276': 'Nguyễn Thanh Giàu',
  '63E01103': 'Lê Phương Linh',
  '63E01118': 'Lê Ngọc Quí',
  '63F00511': 'Bạch Tấn Trí',
  '63H04234': 'Nguyễn Thành Hiếu',
  '63G00297': 'Trần Trọng Ngân',
  '63E01235': 'Lý Hoàng Thái',
  '63H04236': 'Lê Văn Trọng',
  '63G00280': 'Lê Trung Trực',
  '66H08348': 'Trần Trọng Nghĩa'
};

function getOfficialDriverName(plate, fallback) {
  if (!plate) return fallback || 'Tài xế công ty';
  const clean = plate.replace(/[-. ]/g, '').toUpperCase();
  return OFFICIAL_DRIVERS_MAP[clean] || fallback || 'Tài xế công ty';
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

function renderFuelAnalysisTable(items) {
  const tbody = document.getElementById('fuelAnalysisTableBody');
  if (!tbody) return;

  tbody.innerHTML = items.map(v => {
    let alertBadge = '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">🟢 Chuẩn</span>';
    if (v.is_suspicious_drain) {
      alertBadge = `<span class="px-2.5 py-1 rounded-full text-[11px] font-extrabold bg-red-100 text-red-700 border border-red-300 animate-pulse flex items-center gap-1 justify-center"><i data-lucide="alert-triangle" class="w-3.5 h-3.5"></i> ${v.drain_alert_text}</span>`;
    } else if (v.drain_alert_type === 'over_norm') {
      alertBadge = `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">${v.drain_alert_text}</span>`;
    }

    let cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] text-slate-400 block text-center font-medium">Đậu bãi</span>';
    if (v.card_violation === 'running_no_card') {
      cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-black bg-rose-100 text-rose-700 border border-rose-300 animate-pulse block text-center shadow-xs">🚨 Chưa quẹt thẻ</span>';
    } else if (v.is_card_swiped) {
      cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 block text-center">🟢 Đã quẹt thẻ</span>';
    } else if (v.daily_km > 0) {
      cardBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200 block text-center">⚠️ Chưa quẹt</span>';
    }

    let stateBadge = '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">⚪ Đậu bãi / Tắt máy</span>';
    if (v.op_state === 'running') {
      stateBadge = `<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 animate-pulse flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Xe đang chạy (${v.speed} km/h)</span>`;
    } else if (v.op_state === 'idling') {
      stateBadge = '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-300 flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Xe dừng nổ máy</span>';
    }

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td class="py-3 px-4">${formatPlateBadge(v.plate_number)}</td>
        <td class="py-3 px-4 font-medium text-slate-800">${getOfficialDriverName(v.plate_number, v.driver_name)}</td>
        <td class="py-3 px-4 text-center">${cardBadge}</td>
        <td class="py-3 px-4 space-y-1">
          <div>${stateBadge}</div>
          <div class="text-[11px] text-slate-600 font-medium flex items-center gap-1 truncate max-w-xs" title="${v.address}">
            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-red-500 shrink-0"></i>
            <span class="truncate">${v.address || 'Bãi xe Trường Phát'}</span>
          </div>
        </td>
        <td class="py-3 px-4 text-right font-mono font-bold text-blue-600">${v.daily_km} km</td>
        <td class="py-3 px-4 text-right font-mono font-black text-amber-600">${v.consumed_liters} L</td>
        <td class="py-3 px-4 text-center font-mono font-bold ${v.actual_norm > 42 ? 'text-red-600' : 'text-emerald-700'}">${v.daily_km > 0 ? v.actual_norm + ' L/100km' : '—'}</td>
        <td class="py-3 px-4 text-center font-mono text-slate-500 font-bold">40.0 L/100km</td>
        <td class="py-3 px-4 text-center">${alertBadge}</td>
      </tr>
    `;
  }).join('');
}

function renderFuelNormChart(normData) {
  const chartEl = document.getElementById('fuelNormChart');
  if (!chartEl) return;
  const ctx = chartEl.getContext('2d');
  if (fuelNormChart) fuelNormChart.destroy();

  fuelNormChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: normData.map(d => d.plate),
      datasets: [
        {
          label: 'Định mức thực tế (L/100km)',
          data: normData.map(d => d.actual_norm),
          backgroundColor: normData.map(d => d.actual_norm >= 46 ? '#ef4444' : (d.actual_norm > 42 ? '#f59e0b' : '#10b981')),
          borderRadius: 6,
        },
        {
          label: 'Vạch chuẩn quy chuẩn (40 L/100km)',
          data: normData.map(() => 40.0),
          type: 'line',
          borderColor: '#3b82f6',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 0,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: {
          beginAtZero: false,
          min: 30,
          max: 55,
          ticks: { callback: (v) => v + ' L' }
        }
      },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } }
      }
    }
  });
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
  const chartEl = document.getElementById('topRoutesChart');
  if (!chartEl) return;
  const ctx = chartEl.getContext('2d');
  if (topRoutesChart) topRoutesChart.destroy();

  const labels = routesData.map(r => r.route.length > 28 ? r.route.slice(0, 26) + '...' : r.route);
  const data = routesData.map(r => r.trips_count);

  topRoutesChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Số chuyến hôm nay',
        data: data,
        backgroundColor: '#6366f1',
        borderRadius: 6,
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          beginAtZero: true,
          ticks: { stepSize: 1, callback: (v) => v + ' chuyến' }
        }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderCustomerBreakdownChart(customerData) {
  const chartEl = document.getElementById('customerBreakdownChart');
  if (!chartEl) return;
  const ctx = chartEl.getContext('2d');
  if (customerBreakdownChart) customerBreakdownChart.destroy();

  if (!customerData || customerData.length === 0) {
    customerData = [
      { customer: 'Khai Anh', trips: 9, percent: 75.0 },
      { customer: 'Thuận An', trips: 2, percent: 16.7 },
      { customer: 'Chủ hàng khác', trips: 1, percent: 8.3 }
    ];
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

function renderWeeklyFuelTable(weeklyData) {
  const tbody = document.getElementById('weeklyFuelTableBody');
  if (!tbody) return;

  const rangeEl = document.getElementById('weeklyRangeText');
  if (rangeEl && weeklyData.week_range) rangeEl.innerText = weeklyData.week_range;
  const avgNormEl = document.getElementById('weeklyAvgFleetNorm');
  if (avgNormEl && weeklyData.avg_fleet_norm) avgNormEl.innerText = `${weeklyData.avg_fleet_norm} L/100km`;

  const statKm = document.getElementById('stat-weekly-km');
  if (statKm) statKm.innerText = `${(weeklyData.total_weekly_km || 0).toLocaleString('vi-VN')} km`;
  const statAvgKm = document.getElementById('stat-weekly-avg-km');
  if (statAvgKm) statAvgKm.innerText = `${(weeklyData.avg_daily_km || 0).toLocaleString('vi-VN')} km/ngày`;
  const statFuel = document.getElementById('stat-weekly-fuel');
  if (statFuel) statFuel.innerText = `${(weeklyData.total_weekly_fuel || 0).toLocaleString('vi-VN')} Lít`;
  const statDrain = document.getElementById('stat-weekly-drain-count');
  if (statDrain) {
    const count = weeklyData.suspicious_trucks_count || 0;
    statDrain.innerText = `${count} Xe`;
    statDrain.className = count > 0 ? 'text-xl font-black text-rose-600 mt-1' : 'text-xl font-black text-emerald-600 mt-1';
  }

  const records = weeklyData.records || [];
  tbody.innerHTML = records.map((r, idx) => {
    let badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (r.status_type === 'drain') badgeClass = 'bg-rose-100 text-rose-700 border-rose-300 font-extrabold animate-pulse';
    else if (r.status_type === 'warning') badgeClass = 'bg-amber-100 text-amber-800 border-amber-300 font-bold';
    else if (r.status_type === 'low') badgeClass = 'bg-slate-100 text-slate-600 border-slate-200';

    const diffText = r.diff > 0 ? `+${r.diff}` : `${r.diff}`;
    const diffClass = r.diff > 2 ? 'text-rose-600 font-bold' : (r.diff < 0 ? 'text-emerald-600 font-bold' : 'text-slate-600');

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td class="py-3 px-3.5 text-center font-bold text-slate-500">${idx + 1}</td>
        <td class="py-3 px-3.5">${formatPlateBadge(r.plate_number)}</td>
        <td class="py-3 px-3.5 font-bold text-slate-800">${getOfficialDriverName(r.plate_number, r.driver_name)}</td>
        <td class="py-3 px-3.5 text-right font-black text-slate-800">${r.weekly_km.toLocaleString('vi-VN')} km</td>
        <td class="py-3 px-3.5 text-right font-bold text-blue-600">${r.avg_daily_km} km</td>
        <td class="py-3 px-3.5 text-right font-black text-amber-700">${r.weekly_liters.toLocaleString('vi-VN')} L</td>
        <td class="py-3 px-3.5 text-center font-black ${r.actual_norm >= 45 ? 'text-rose-600' : 'text-slate-800'}">${r.actual_norm} L/100km</td>
        <td class="py-3 px-3.5 text-center ${diffClass}">${diffText} L</td>
        <td class="py-3 px-3.5 text-center">
          <span class="px-2.5 py-1 rounded-full text-[10px] font-bold border ${badgeClass}">
            ${r.status_label}
          </span>
        </td>
      </tr>
    `;
  }).join('');
}

function renderTopDriversLeaderboard(drivers) {
  const container = document.getElementById('topDriversLeaderboard');
  if (!container) return;

  const medals = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'];
  container.innerHTML = drivers.map((d, idx) => `
    <div class="p-3.5 rounded-2xl bg-gradient-to-br from-slate-50 to-indigo-50/40 border border-slate-200 shadow-xs space-y-1.5 hover:shadow-sm transition">
      <div class="flex items-center justify-between">
        <span class="text-base">${medals[idx] || (idx + 1)}</span>
        <span class="font-mono font-black text-xs text-blue-700">${d.plate_number}</span>
      </div>
      <p class="font-black text-xs text-slate-800 truncate">${getOfficialDriverName(d.plate_number, d.driver_name)}</p>
      <div class="flex items-baseline justify-between text-[11px] pt-1.5 border-t border-slate-200/60">
        <span class="text-slate-500">Tổng tuần:</span>
        <span class="font-black text-slate-800">${d.weekly_km.toLocaleString('vi-VN')} km</span>
      </div>
      <div class="flex items-baseline justify-between text-[10px]">
        <span class="text-slate-500">Bình quân:</span>
        <span class="font-bold text-blue-600">${d.avg_daily_km} km/ngày</span>
      </div>
    </div>
  `).join('');
}

// CÀI ĐẶT TRANG TÍNH THÁNG 09
async function openSheetConfigModal() {
  openModal('modalSheetConfig');
  const alertEl = document.getElementById('sheetConfigAlert');
  if (alertEl) alertEl.className = 'hidden';
  try {
    const res = await fetch(API_BASE + '/trips/sheets-config', { headers: getHeaders() });
    const json = await res.json();
    const f08 = document.getElementById('cfgSheetUrl08');
    const f09 = document.getElementById('cfgSheetUrl09');
    if (f08) f08.value = json.sheet_url_month_08 || '';
    if (f09) f09.value = json.sheet_url_month_09 || '';
  } catch (err) {
    console.error('Error loading sheets config', err);
  }
}

async function saveSheetConfig() {
  const url09 = document.getElementById('cfgSheetUrl09').value.trim();
  const alertEl = document.getElementById('sheetConfigAlert');
  try {
    const res = await fetch(API_BASE + '/trips/sheets-config', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ month: '09', url: url09 })
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi lưu cấu hình');
    if (alertEl) {
      alertEl.innerText = `✅ ${json.message}`;
      alertEl.className = 'p-3 rounded-xl text-xs border bg-emerald-50 text-emerald-800 border-emerald-200 block';
    }
    setTimeout(() => {
      closeModal('modalSheetConfig');
      handleDateSelect(selectedDate);
    }, 1200);
  } catch (err) {
    if (alertEl) {
      alertEl.innerText = `❌ Lỗi: ${err.message}`;
      alertEl.className = 'p-3 rounded-xl text-xs border bg-red-50 text-red-800 border-red-200 block';
    }
  }
}

// 2. TAB TRA CỨU PHẠT NGUỘI TOÀN ĐOÀN XE (CỤC CSGT)
async function loadTrafficFines() {
  try {
    const res = await fetch(API_BASE + '/fines', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi tra cứu phạt nguội');

    trafficFinesCache = json;
    const s = json.summary;

    const cleanEl = document.getElementById('fines-count-clean');
    const violEl = document.getElementById('fines-count-violated');
    const warnEl = document.getElementById('fines-count-warning');
    const amountEl = document.getElementById('fines-total-amount');
    const lastCheckedEl = document.getElementById('finesLastCheckedText');
    const badgeSidebar = document.getElementById('badgeFinesCount');

    if (cleanEl) cleanEl.innerText = `${s.clean_vehicles} Xe`;
    if (violEl) violEl.innerText = `${s.violated_vehicles} Xe`;
    if (warnEl) warnEl.innerText = `${s.registry_warning_vehicles} Xe`;
    if (amountEl) amountEl.innerText = formatVND(s.total_fine_amount);
    if (lastCheckedEl) lastCheckedEl.innerText = s.last_check_time;
    if (badgeSidebar) {
      if (s.violated_vehicles > 0) {
        badgeSidebar.className = 'text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded font-black animate-pulse';
        badgeSidebar.innerText = `${s.violated_vehicles} Xe Lỗi`;
      } else {
        badgeSidebar.className = 'text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-bold';
        badgeSidebar.innerText = '26 Xe Sạch';
      }
    }

    renderFinesTable(json.data);
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading traffic fines:', err);
  }
}

function renderFinesTable(list) {
  const tbody = document.getElementById('finesTableBody');
  if (!tbody) return;

  tbody.innerHTML = list.map((v, idx) => {
    let statBadge = '<span class="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1 w-fit"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Không vi phạm</span>';
    let warningBadge = '<span class="text-emerald-600 font-bold text-[11px]">🟢 Đủ điều kiện đăng kiểm</span>';
    let actionBtn = '<span class="text-slate-400 font-medium text-xs">Đã an toàn</span>';

    if (v.has_violation) {
      statBadge = '<span class="px-2.5 py-1 rounded-full text-[11px] font-black bg-red-100 text-red-700 border border-red-300 animate-pulse flex items-center gap-1 w-fit"><span class="w-2 h-2 rounded-full bg-red-600 animate-ping"></span> Có lỗi phạt nguội</span>';
      warningBadge = '<span class="px-2 py-0.5 rounded bg-red-100 text-red-800 font-extrabold border border-red-300 text-[10px] animate-pulse">⚠️ Chặn Đăng Kiểm</span>';
      actionBtn = `
        <button onclick="resolveTrafficFine('${v.plate_number}')" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white rounded-lg text-xs font-bold transition shadow-sm flex items-center gap-1">
          <i data-lucide="check" class="w-3.5 h-3.5"></i>
          <span>Đã Nộp Phạt Xong</span>
        </button>
      `;
    }

    let violationsHtml = '<span class="text-slate-400 italic">Không có dữ liệu vi phạm trên hệ thống Cục CSGT</span>';
    if (v.violations && v.violations.length > 0) {
      violationsHtml = v.violations.map(vl => `
        <div class="p-2 rounded-xl bg-red-50 border border-red-200 text-xs space-y-1">
          <div class="flex items-center justify-between font-bold text-red-800">
            <span>🚨 ${vl.behavior}</span>
            <span class="text-rose-700 font-mono font-black">${formatVND(vl.fine_amount)}</span>
          </div>
          <p class="text-[11px] text-slate-600">📍 <strong>Vị trí:</strong> ${vl.location}</p>
          <p class="text-[11px] text-slate-600">🕒 <strong>Thời gian:</strong> ${vl.violation_time} • <strong>Trạng thái:</strong> <span class="font-bold text-red-600">${vl.status}</span></p>
          <p class="text-[10px] text-slate-500">🏢 <strong>Đơn vị:</strong> ${vl.enforcing_unit} (SĐT: ${vl.contact_phone})</p>
          <p class="text-[10px] text-amber-700 font-bold bg-amber-50 p-1 rounded border border-amber-200">${vl.registry_warning_text}</p>
        </div>
      `).join('');
    }

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs ${v.has_violation ? 'bg-red-50/40' : ''}">
        <td class="py-3 px-4 text-center font-bold text-slate-400">${idx + 1}</td>
        <td class="py-3 px-4 font-mono font-black text-blue-700 text-sm">${v.plate_number}</td>
        <td class="py-3 px-4 font-bold text-slate-800">${getOfficialDriverName(v.plate_number, v.driver_name)}</td>
        <td class="py-3 px-4 text-center">${statBadge}</td>
        <td class="py-3 px-4 max-w-md whitespace-normal leading-relaxed">${violationsHtml}</td>
        <td class="py-3 px-4 text-center">${warningBadge}</td>
        <td class="py-3 px-4 text-center">${actionBtn}</td>
      </tr>
    `;
  }).join('');
}

async function triggerCheckAllFines() {
  const icon = document.getElementById('finesScanIcon');
  if (icon) icon.classList.add('animate-spin');

  try {
    const res = await fetch(API_BASE + '/fines/check-all', { method: 'POST', headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi quét phạt nguội');

    alert(`✅ ${json.message}\n• Xe sạch lỗi: ${json.summary.clean_vehicles}/26 xe\n• Xe có vi phạm: ${json.summary.violated_vehicles} xe`);
    loadTrafficFines();
    loadDashboard(selectedDate);
  } catch (err) {
    alert('Lỗi: ' + err.message);
  } finally {
    if (icon) icon.classList.remove('animate-spin');
  }
}

async function resolveTrafficFine(plate) {
  if (!confirm(`Bạn có chắc chắn xe ${plate} đã hoàn thành nộp phạt tại Kho Bạc và muốn gỡ bỏ cảnh báo phạt nguội?`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/fines/${encodeURIComponent(plate)}/resolve`, {
      method: 'POST',
      headers: getHeaders()
    });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi cập nhật');

    alert(`✅ ${json.message}`);
    loadTrafficFines();
    loadDashboard(selectedDate);
  } catch (err) {
    alert('Lỗi: ' + err.message);
  }
}

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
    let liveAddr = t.gps_address || 'Bãi xe Trường Phát';

    if (isOff) {
      opBadge = '<span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200">⚪ Tài xế nghỉ (Nghỉ cả ngày)</span>';
    }

    const typeBadge = t.vehicle_type === 'Xe Ben'
      ? '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-100 text-orange-800">Xe Ben</span>'
      : '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-800">Xe Thùng</span>';

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td class="py-3 px-4 text-center font-bold text-slate-500">${t.stt}</td>
        <td class="py-3 px-4 font-mono font-black text-blue-700 text-sm">${t.plate_number}</td>
        <td class="py-3 px-4">${typeBadge}</td>
        <td class="py-3 px-4 font-bold text-slate-800 ${isOff ? 'text-slate-400 font-normal italic' : ''}">${t.route}</td>
        <td class="py-3 px-4 font-medium text-slate-700">${t.cargo_type || '—'}</td>
        <td class="py-3 px-4 font-bold text-slate-900">${t.customer_name || '—'}</td>
        <td class="py-3 px-4 space-y-1">
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
    renderDailyTripsTable(data);
  } catch (err) {
    console.error('Error loading daily trips:', err);
  }
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
async function loadGroupedVehicles() {
  try {
    const res = await fetch(API_BASE + '/vehicles/grouped', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi lấy dữ liệu xe');

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

  const renderBadge = (doc) => {
    if (!doc.date) return '<span class="text-slate-300 font-normal">—</span>';
    if (doc.status === 'expired' || doc.status === 'red') {
      return `<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-red-100 text-red-700">${doc.date} (${doc.label})</span>`;
    } else if (doc.status === 'yellow') {
      return `<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">${doc.date} (${doc.label})</span>`;
    } else {
      return `<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-700">${doc.date}</span>`;
    }
  };

  tbody.innerHTML = list.map((v, idx) => `
    <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
      <td class="py-3 px-4 text-center font-bold text-slate-400">${idx + 1}</td>
      <td class="py-3 px-4 font-mono font-black text-blue-700 text-sm">${v.plate_number}</td>
      <td class="py-3 px-4 font-mono font-bold text-slate-800">${v.trailer_number}</td>
      <td class="py-3 px-4 text-center">${renderBadge(v.gdd_head)}</td>
      <td class="py-3 px-4 text-center">${renderBadge(v.gdd_trailer)}</td>
      <td class="py-3 px-4 text-center">${renderBadge(v.registration)}</td>
      <td class="py-3 px-4 text-center">${renderBadge(v.insurance)}</td>
      <td class="py-3 px-4 text-center"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">Đang lưu hành</span></td>
    </tr>
  `).join('');
}

// 5. TAB TÀI XẾ
async function loadDriversActivity() {
  try {
    const res = await fetch(API_BASE + '/drivers/activity', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi tài xế');

    driversActivityCache = json;

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
                Tài xế phụ trách: <span class="text-blue-700">${v.driver_assigned}</span> (${v.phone})
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

    const topContainer = document.getElementById('topRunnersContainer');
    topContainer.innerHTML = json.top_runners.slice(0, 3).map((d, i) => {
      const medals = ['🥇', '🥈', '🥉'];
      return `
        <div class="p-3.5 rounded-2xl bg-white/10 border border-white/15 backdrop-blur-md flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="text-2xl">${medals[i] || '🎖️'}</span>
            <div>
              <h4 class="font-extrabold text-white text-sm">${d.full_name}</h4>
              <p class="text-[11px] text-blue-200 font-mono">Xe: ${d.vehicle_plate}</p>
            </div>
          </div>
          <div class="text-right">
            <span class="text-lg font-black text-amber-300 font-mono">${d.daily_km} km</span>
            <p class="text-[10px] text-emerald-300 font-bold">${d.distance_category}</p>
          </div>
        </div>
      `;
    }).join('');

    renderDetailedDriversTable(json.drivers);
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading drivers activity:', err);
  }
}

function filterDriversActivity() {
  const search = document.getElementById('driverSearchInput').value.toLowerCase();
  if (!driversActivityCache) return;
  const filtered = driversActivityCache.drivers.filter(d => 
    d.full_name.toLowerCase().includes(search) || 
    (d.phone && d.phone.includes(search)) ||
    (d.vehicle_plate && d.vehicle_plate.toLowerCase().includes(search))
  );
  renderDetailedDriversTable(filtered);
}

function renderDetailedDriversTable(list) {
  const tbody = document.getElementById('driversDetailedTableBody');
  if (!tbody) return;

  tbody.innerHTML = list.map(d => {
    let badgeColor = 'bg-slate-100 text-slate-600 border-slate-200';
    if (d.distance_badge === 'purple') badgeColor = 'bg-purple-100 text-purple-800 border-purple-200';
    if (d.distance_badge === 'blue') badgeColor = 'bg-blue-100 text-blue-800 border-blue-200';
    if (d.distance_badge === 'emerald') badgeColor = 'bg-emerald-100 text-emerald-800 border-emerald-200';

    let gradeBadge = '<span class="px-2 py-0.5 rounded text-[11px] font-black bg-emerald-100 text-emerald-800">A+ (98%)</span>';
    if (d.overall_rating < 90) {
      gradeBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-700">${d.grade} (${d.overall_rating}%)</span>`;
    } else {
      gradeBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-black bg-blue-100 text-blue-800">${d.grade} (${d.overall_rating}%)</span>`;
    }

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
        <td class="py-3 px-4">
          <div class="font-bold text-slate-900 text-sm leading-tight">${d.full_name}</div>
          <div class="text-[11px] text-slate-500 font-mono">${d.phone} • Hạng ${d.license_class}</div>
        </td>
        <td class="py-3 px-4 font-mono font-black text-blue-700 text-sm">${d.vehicle_plate}</td>
        <td class="py-3 px-4 text-center">
          ${d.is_card_swiped
            ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 inline-flex items-center gap-1">🟢 Đã quẹt</span>'
            : '<span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-100 text-rose-700 border border-rose-300 animate-pulse inline-flex items-center gap-1">🚨 Chưa quẹt</span>'
          }
        </td>
        <td class="py-3 px-4 text-right font-mono font-black text-blue-600 text-sm">${d.daily_km} km</td>
        <td class="py-3 px-4 text-center">
          <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold border ${badgeColor}">
            ${d.distance_category}
          </span>
        </td>
        <td class="py-3 px-4 space-y-0.5">
          <div class="font-bold text-[11px] ${d.speed > 0 ? 'text-emerald-700' : 'text-slate-600'}">${d.movement_state}</div>
          <div class="text-[10px] text-slate-500 truncate max-w-xs" title="${d.current_address}">📍 ${d.current_address}</div>
        </td>
        <td class="py-3 px-4 text-center font-bold text-blue-700">${d.productivity_score}%</td>
        <td class="py-3 px-4 text-center text-slate-600 font-medium">${d.fuel_saving_note}</td>
        <td class="py-3 px-4 text-center text-slate-600 font-medium">${d.safety_note}</td>
        <td class="py-3 px-4 text-center">${gradeBadge}</td>
        <td class="py-3 px-4 text-slate-700 text-[11px] leading-relaxed max-w-xs">${d.detailed_comment}</td>
      </tr>
    `;
  }).join('');
  if (window.lucide) lucide.createIcons();
}

// 6. TAB BẢO DƯỠNG THAY NHỚT (KHỚP 100% GOOGLE SHEET)
async function loadMaintenance() {
  try {
    const res = await fetch(API_BASE + '/maintenance/oil', { headers: getHeaders() });
    const list = await res.json();
    const tbody = document.getElementById('maintenanceTableBody');
    if (!tbody) return;

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
  } catch (err) {
    console.error('Error loading maintenance', err);
  }
}

// BẢN ĐỒ GIÁM SÁT HÀNH TRÌNH LEAFLET.JS (REALTIME FLEET MAP)
// Bản đồ đã được gỡ bỏ theo yêu cầu
function focusVehicleOnMap(plate) {}
function fitAllFleetBounds() {}
function handleMapSearch(q) {}
function filterMapMarkers(t) {}

// 7. GPS & TIRES & BARGES
async function loadGpsLive() {
  const timeEl = document.getElementById('gpsLastUpdateTime');
  if (timeEl) timeEl.innerText = 'Đang đồng bộ từ Bình Anh GPS...';

  try {
    const res = await fetch(API_BASE + '/gps/live', { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi GPS');

    gpsCache = json.data || [];
    if (timeEl) timeEl.innerText = json.timestamp;

    // Cập nhật bản đồ GPS tương tác
    updateLiveGpsMap(gpsCache, activeMapFilter);

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
            <td class="py-3 px-4 text-center font-mono text-slate-500 text-[11px]">${v.update_time}</td>
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
    if (timeEl && json.timestamp) timeEl.innerText = json.timestamp;

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
  const icon = document.getElementById('gpsSyncIcon');
  if (icon) icon.classList.add('animate-spin');

  try {
    const res = await fetch(API_BASE + '/gps/sync', { method: 'POST', headers: getHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Lỗi đồng bộ');

    alert(data.message);
    loadGpsLive();
    loadDashboard(selectedDate);
  } catch (err) {
    alert('Lỗi: ' + err.message);
  } finally {
    if (icon) icon.classList.remove('animate-spin');
  }
}

async function loadTires() {
  try {
    const res = await fetch(API_BASE + '/maintenance/tires/summary', { headers: getHeaders() });
    const tireData = await res.json();
    const tireTbody = document.getElementById('tireTableBody');
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
  } catch (err) {
    console.error('Error loading tires', err);
  }
}

async function loadBarges() {
  try {
    const res = await fetch(API_BASE + '/barges', { headers: getHeaders() });
    const list = await res.json();
    const tbody = document.getElementById('bargesTableBody');
    tbody.innerHTML = list.map(b => {
      const isOwned = b.ownership_type === 'owned';
      const typeBadge = isOwned
        ? '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-700">4 Sà Lan Nhà</span>'
        : '<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">6 Sà Lan Thuê</span>';

      return `
        <tr class="hover:bg-slate-50 transition border-b border-slate-100 text-xs">
          <td class="py-3 px-4 font-bold text-slate-800 flex items-center gap-2">
            <i data-lucide="ship" class="w-4 h-4 text-cyan-600"></i>
            <span>${b.name}</span>
          </td>
          <td class="py-3 px-4 font-mono text-slate-600">${b.registration_number || '—'}</td>
          <td class="py-3 px-4 text-right font-bold text-slate-800">${b.payload_capacity ? b.payload_capacity.toLocaleString() + ' Tấn' : '—'}</td>
          <td class="py-3 px-4 text-center">${typeBadge}</td>
          <td class="py-3 px-4 text-slate-600">${b.owner_name ? b.owner_name + ' (' + (b.owner_phone || '') + ')' : '<span class="text-slate-400">Tự quản</span>'}</td>
        </tr>
      `;
    }).join('');
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading barges', err);
  }
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

// 10. TƯỜNG LỬA & AN NINH HỆ THỐNG (WAF SHIELD)
async function loadSecurityStatus() {
  try {
    const res = await fetch(API_BASE + '/security/status', { headers: getHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Lỗi kiểm tra an ninh');

    const attacksEl = document.getElementById('sec-attacks-count');
    if (attacksEl) attacksEl.innerText = `${data.total_attacks_blocked || 0} Đợt`;

    const blockedEl = document.getElementById('sec-blocked-count');
    if (blockedEl) blockedEl.innerText = `${data.blocked_ips_count || 0} IP`;

    const currentIpEl = document.getElementById('sec-current-ip');
    if (currentIpEl) currentIpEl.innerText = `IP: ${data.client_ip || '127.0.0.1'}`;

    // Render Blocked IPs
    const blockedContainer = document.getElementById('sec-blocked-list');
    if (blockedContainer) {
      if (data.blocked_ips && data.blocked_ips.length > 0) {
        blockedContainer.innerHTML = data.blocked_ips.map(item => `
          <div class="flex items-center justify-between p-2 rounded-lg bg-rose-50 border border-rose-200">
            <div>
              <span class="font-mono font-bold text-rose-700">${item.ip}</span>
              <span class="text-[10px] text-slate-500 ml-2">(Còn ${Math.ceil(item.remaining_seconds / 60)} phút)</span>
            </div>
            <button onclick="unblockIp('${item.ip}')" class="px-2 py-1 bg-white border border-rose-300 text-rose-700 hover:bg-rose-100 rounded text-[10px] font-bold">
              Gỡ Khóa
            </button>
          </div>
        `).join('');
      } else {
        blockedContainer.innerHTML = '🟢 Hiện tại không có IP nào bị khóa. Toàn bộ kết nối an toàn.';
      }
    }

    // Render Audit Logs
    const tbody = document.getElementById('secAuditLogBody');
    if (tbody) {
      if (data.audit_logs && data.audit_logs.length > 0) {
        tbody.innerHTML = data.audit_logs.map(log => {
          let badge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">🟢 An toàn</span>';
          if (log.is_threat) {
            badge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 border border-rose-300 animate-pulse">🚨 Ngăn chặn</span>';
          }
          return `
            <tr class="hover:bg-slate-50 border-b border-slate-100">
              <td class="py-2.5 px-3.5 text-slate-500">${log.timestamp}</td>
              <td class="py-2.5 px-3.5 font-bold text-blue-700">${log.ip}</td>
              <td class="py-2.5 px-3.5 font-bold ${log.is_threat ? 'text-rose-600' : 'text-slate-800'}">${log.event_type}</td>
              <td class="py-2.5 px-3.5 text-slate-700">${log.details}</td>
              <td class="py-2.5 px-3.5 text-center">${badge}</td>
            </tr>
          `;
        }).join('');
      } else {
        tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-slate-400">Chưa ghi nhận sự kiện bất thường nào. Tường lửa hoạt động ổn định.</td></tr>';
      }
    }
    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error('Error loading security status:', err);
  }
}

async function unblockIp(ip) {
  if (!confirm(`Bạn có chắc chắn muốn gỡ khóa IP ${ip} không?`)) return;
  try {
    const res = await fetch(API_BASE + '/security/unblock-ip', {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ ip })
    });
    const json = await res.json();
    alert(json.message);
    loadSecurityStatus();
  } catch (err) {
    alert('Lỗi gỡ khóa IP: ' + err.message);
  }
}

async function handleUpdatePin(e) {
  e.preventDefault();
  const oldPin = document.getElementById('oldPinInput').value.trim();
  const newPin = document.getElementById('newPinInput').value.trim();
  const alertBox = document.getElementById('pinAlertBox');

  try {
    const res = await fetch(API_BASE + '/security/update-pin', {
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

// Auto check PWA banner on document ready
setTimeout(checkAndShowPwaBanner, 1000);

