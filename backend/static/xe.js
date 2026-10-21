// =====================================================================
// XE & CHI PHÍ — đọc Google Sheets "ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM", ghi qua Apps Script
// Hiển thị theo bố cục cũ: Đội xe & mooc, Bảo dưỡng, Thay vỏ & bạt, Đổ dầu, Công nợ & chi phí, Tổng quan
// Màu trạng thái cố định: đỏ = quá/sắp hạn, vàng = gần hạn, xanh = ổn, xám = thiếu số liệu
// =====================================================================
let xeData = null;
let xeLoadedAt = 0;
let xeLoading = null;
let xePage = null;      // trang đang mở: vehicles | maintenance | tires | fuel | costs
let xeMonth = null;
let xePlate = '';

const ST = {
  overdue: { label: 'Quá hạn', cls: 'bg-red-600 text-white' },
  soon: { label: 'Sắp hạn', cls: 'bg-red-100 text-red-800 border border-red-300' },
  near: { label: 'Gần hạn', cls: 'bg-amber-100 text-amber-900 border border-amber-300' },
  ok: { label: 'Ổn', cls: 'bg-emerald-100 text-emerald-800 border border-emerald-300' },
  missing: { label: 'Thiếu số liệu', cls: 'bg-slate-200 text-slate-700 border border-slate-300' },
};
const ST_TEXT = { overdue: 'text-red-700', soon: 'text-red-600', near: 'text-amber-700', ok: 'text-emerald-700', missing: 'text-slate-500' };

// ---------- định dạng
const money = v => (v === null || v === undefined || v === '') ? '—' : `${Math.round(Number(v)).toLocaleString('vi-VN')} đ`;
const num = (v, d = 0) => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString('vi-VN', { maximumFractionDigits: d });
const dmy = s => s ? s.slice(0, 10).split('-').reverse().join('/') : '—';
const chip = st => { const s = ST[st] || ST.missing; return `<span class="inline-block px-2.5 py-1 rounded-lg text-[11px] font-bold whitespace-nowrap ${s.cls}">${s.label}</span>`; };
const plateBtn = p => `<button type="button" onclick="openVehicleProfile('${escHtml(p)}')" class="font-mono font-black text-blue-700 underline decoration-dotted underline-offset-2 text-sm">${escHtml(p)}</button>`;
const esc = v => escHtml(v ?? '');
// Màu L/100km: đỏ = vượt định mức > 10%, xám = thấp bất thường (thường do số liệu), xanh = trong định mức
const fuelCls = (v, n) => (v === null || v === undefined || !n) ? 'text-slate-500' : ((v - n) / n > 0.1 ? 'text-red-700' : ((v - n) / n < -0.1 ? 'text-slate-500' : 'text-emerald-700'));

// ---------- tải dữ liệu (cache 3 phút, nút "Làm mới" đọc lại ngay)
async function loadXe(force = false) {
  if (!force && xeData && Date.now() - xeLoadedAt < 180000) { renderXe(); return xeData; }
  if (xeLoading && !force) return xeLoading;
  xeLoading = (async () => {
    try {
      const res = await fetch(`${API_BASE}/xe/data${force ? '?refresh=1' : ''}`, { headers: getHeaders() });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || 'Không đọc được dữ liệu');
      xeData = json;
      xeLoadedAt = Date.now();
      if (!xeMonth) xeMonth = latestMonth();
      renderXe();
      return json;
    } catch (err) {
      const box = xePage && document.getElementById(`xePage-${xePage}`);
      if (box && !xeData) box.innerHTML = `<div class="p-5 rounded-2xl bg-red-50 border border-red-300 text-red-800 font-bold">Không đọc được Google Sheets: ${esc(err.message)}</div>`;
      const todo = document.getElementById('dashTodoCard');
      if (todo && !xeData) todo.innerHTML = `<p class="text-red-700 font-bold text-sm">Không đọc được Sheets giấy tờ / bảo dưỡng: ${esc(err.message)}</p>`;
    } finally { xeLoading = null; }
  })();
  return xeLoading;
}

function showXePage(page) { xePage = page; if (xeData) renderXe(); loadXe(); }

function latestMonth() {
  const ms = (xeData.fuel.rows || []).map(r => (r.date || '').slice(0, 7)).filter(Boolean).sort();
  return ms.length ? ms[ms.length - 1] : new Date().toISOString().slice(0, 7);
}
function monthsAvailable() {
  const s = new Set();
  [...xeData.fuel.rows, ...xeData.maint.log, ...xeData.tires, ...xeData.tarps].forEach(r => r.date && s.add(r.date.slice(0, 7)));
  return [...s].sort().reverse();
}

const XE_PAGES = { vehicles: () => xeVehiclesPage(), maintenance: () => xeMaintPage(), tires: () => xeTiresPage(), fuel: () => xeFuelPage(), costs: () => xeCostsPage() };

function renderXe() {
  if (!xeData) return;
  renderDashXe(xeData);
  renderXeBadges(xeData);
  if (xePage && XE_PAGES[xePage]) {
    const box = document.getElementById(`xePage-${xePage}`);
    if (box) box.innerHTML = xeSourceBar() + XE_PAGES[xePage]();
  }
  if (typeof renderFinesPage === 'function') renderFinesPage();
  if (window.lucide) lucide.createIcons();
}

function xeSourceBar() {
  const src = xeData.source;
  return `<div class="flex flex-wrap items-center gap-2 text-xs">
      <span class="px-2.5 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-700 font-semibold">Nguồn: Google Sheets ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM • đọc lúc <b class="font-mono">${esc(src.read_at)}</b></span>
      ${xeData.stale_error ? `<span class="px-2.5 py-1.5 rounded-xl bg-amber-100 border border-amber-300 text-amber-900 font-semibold">Đang hiện bản cũ — lỗi đọc mới: ${esc(xeData.stale_error)}</span>` : ''}
      <span class="px-2.5 py-1.5 rounded-xl font-semibold ${xeData.write_enabled ? 'bg-emerald-50 border border-emerald-200 text-emerald-800' : 'bg-slate-100 border border-slate-200 text-slate-600'}">Ghi vào Sheets: <b>${xeData.write_enabled ? 'đang bật' : 'chưa bật'}</b></span>
      <button onclick="loadXe(true)" class="ml-auto px-4 py-2 rounded-2xl bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-800 font-bold flex items-center gap-1.5 active:scale-95"><i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>Tải lại số liệu</button>
    </div>
    ${src.missing_tabs.length ? `<p class="text-sm text-red-700 font-bold">Không thấy tab: ${src.missing_tabs.join(', ')}</p>` : ''}`;
}

// Khung thẻ kiểu cũ: viền trên màu + tiêu đề in hoa + icon
function oldCard({ icon, tone = 'blue', title, sub = '', right = '', body, top = '' }) {
  const t = { blue: 'bg-blue-50 text-blue-600 border-blue-200', amber: 'bg-amber-50 text-amber-600 border-amber-200', orange: 'bg-orange-100 text-orange-700 border-orange-200',
              emerald: 'bg-emerald-50 text-emerald-600 border-emerald-200', rose: 'bg-rose-50 text-rose-600 border-rose-200', indigo: 'bg-indigo-50 text-indigo-600 border-indigo-200', slate: 'bg-slate-100 text-slate-600 border-slate-200' }[tone];
  return `<div class="glass-card p-6 md:p-7 rounded-[2rem] shadow-sm space-y-4 ${top}">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
      <div class="flex items-center gap-3">
        <div class="p-2.5 rounded-2xl border ${t}"><i data-lucide="${icon}" class="w-5 h-5"></i></div>
        <div><h3 class="font-black text-slate-900 text-sm md:text-base uppercase">${title}</h3>${sub ? `<p class="text-xs text-slate-500 mt-0.5">${sub}</p>` : ''}</div>
      </div>
      ${right ? `<div class="flex flex-wrap items-center gap-2">${right}</div>` : ''}
    </div>
    ${body}
  </div>`;
}

// Bảng kiểu cũ (máy tính) — tự thành thẻ trên điện thoại (class rtable + data-label)
function oldTable(cols, rows, empty = 'Không có dữ liệu', rowCls = () => '') {
  if (!rows.length) return `<p class="p-6 text-center text-slate-500 bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-sm">${empty}</p>`;
  return `<div class="rtable-wrap overflow-x-auto rounded-2xl border border-slate-200/90 shadow-2xs">
    <table class="rtable w-full text-left text-xs whitespace-nowrap">
      <thead class="bg-slate-100/90 text-slate-700 font-extrabold uppercase tracking-wider border-b border-slate-200"><tr>
        ${cols.map(c => `<th class="py-3.5 px-4 ${c[2] === 'right' ? 'text-right' : (c[2] === 'center' ? 'text-center' : '')}">${c[0]}</th>`).join('')}
      </tr></thead>
      <tbody class="divide-y divide-slate-100">
        ${rows.map((r, i) => `<tr class="hover:bg-slate-50 transition text-xs ${rowCls(r)}">${cols.map(c => `<td data-label="${esc(c[0])}" class="py-3 px-4 align-top ${c[2] === 'right' ? 'text-right font-mono' : (c[2] === 'center' ? 'text-center' : '')}">${c[1](r, i)}</td>`).join('')}</tr>`).join('')}
      </tbody>
    </table></div>`;
}

// ---------- Badge số cảnh báo trên menu
function renderXeBadges(d) {
  const set = (id, n) => { const el = document.getElementById(id); if (!el) return; el.classList.toggle('hidden', !n); el.innerText = n ? `${n}` : ''; };
  const docsBad = d.docs.filter(x => x.status === 'overdue' || x.status === 'soon').length;
  set('badgeDocsAlert', docsBad);
  const maintBad = [...d.maint.oil, ...d.maint.gearbox, ...d.maint.grease].filter(x => x.status === 'overdue' || x.status === 'soon').length;
  set('badgeMaintAlert', maintBad);
  set('badgeFuelAlert', fuelOverPlates(d).length);
}

// Xe mà lần đo gần nhất (giữa 2 lần đầy bình) vượt định mức > 10%
function fuelOverPlates(d) {
  return Object.entries(d.fuel.by_plate)
    .filter(([, v]) => v.latest_l_per_100km !== null && v.norm && (v.latest_l_per_100km - v.norm) / v.norm > 0.1)
    .map(([p, v]) => ({ plate: p, ...v }))
    .sort((a, b) => (b.latest_l_per_100km - b.norm) / b.norm - (a.latest_l_per_100km - a.norm) / a.norm);
}
function fuelInfoForPlate(plate) {
  if (!xeData) return null;
  const e = Object.entries(xeData.fuel.by_plate).find(([k]) => samePlate(k, plate));
  return e ? e[1] : null;
}

// =====================================================================
// TỔNG QUAN: thẻ dầu, cảnh báo hao dầu, giấy tờ, việc cần xử lý, biểu đồ định mức
// =====================================================================
let fuelNormChart = null;
function renderDashXe(d) {
  // Thẻ 3: dầu đã đổ trong tháng gần nhất có số liệu
  const m = latestMonth();
  const rows = d.fuel.rows.filter(r => !r.cancelled && (r.date || '').startsWith(m));
  const liters = rows.reduce((a, r) => a + (Number(r.liters) || 0), 0);
  const amount = rows.reduce((a, r) => a + (Number(r.amount) || 0), 0);
  const setText = (id, t) => { const el = document.getElementById(id); if (el) el.innerText = t; };
  setText('stat-fuel-title', `Dầu Đã Đổ Tháng ${m.slice(5, 7)}/${m.slice(0, 4)}`);
  setText('stat-consumed-fuel', `${num(liters)} Lít`);
  const lag = d.todo.fuel_log_lag_days;
  setText('stat-fuel-sub', `${money(amount)} • sổ nhập đến ${dmy(d.todo.fuel_log_last_date)}${lag > 3 ? ` (trễ ${lag} ngày)` : ''}`);

  // Thẻ 4: xe đang hao dầu vượt định mức
  const over = fuelOverPlates(d);
  const drainEl = document.getElementById('stat-drain-count');
  if (drainEl) { drainEl.innerText = `${over.length} Xe`; drainEl.className = `text-2xl md:text-3xl font-black mt-1.5 font-mono tracking-tight ${over.length ? 'text-red-600' : 'text-emerald-600'}`; }
  const card4 = document.getElementById('card-drain-alert');
  if (card4) card4.classList.toggle('border-t-red-500', !!over.length), card4.classList.toggle('border-t-emerald-500', !over.length);
  const sub4 = document.getElementById('text-drain-sub');
  if (sub4) sub4.innerHTML = over.length
    ? `<span class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span><span class="truncate">${over.slice(0, 3).map(o => `${esc(o.plate)} ${num(o.latest_l_per_100km, 1)}L`).join(' • ')}${over.length > 3 ? '…' : ''}</span>`
    : '<span class="w-2 h-2 rounded-full bg-emerald-500"></span><span>Lần đo gần nhất trong định mức</span>';

  // Thẻ 5: giấy tờ
  const c = d.todo.counts;
  const docsDue = d.docs.filter(x => ['overdue', 'soon', 'near'].includes(x.status));
  const dOver = docsDue.filter(x => x.status === 'overdue').length, dSoon = docsDue.filter(x => x.status === 'soon').length, dNear = docsDue.filter(x => x.status === 'near').length;
  const docsEl = document.getElementById('stat-docs-status');
  if (docsEl) { docsEl.innerText = (dOver + dSoon) ? `${dOver + dSoon} Cảnh Báo` : 'Ổn'; docsEl.className = `text-2xl md:text-3xl font-black font-mono tracking-tight ${(dOver + dSoon) ? 'text-rose-600' : 'text-emerald-600'}`; }
  setText('stat-docs-sub', `${dOver} quá hạn • ${dSoon} sắp hạn • ${dNear} gần hạn`);

  // Định mức trên bảng GPS + vẽ lại bảng với cột dầu
  const nb = document.getElementById('fuelNormBadge');
  if (nb) nb.innerText = `Định mức: Ben ${num(d.todo.fuel_norms['Xe Ben'], 1)} • Thùng ${num(d.todo.fuel_norms['Xe Thùng'], 1)} L/100km`;
  if (typeof lastDashStats !== 'undefined' && lastDashStats && typeof renderGpsTable === 'function') renderGpsTable(lastDashStats.gps_table || []);

  renderDashTodo(d);
  renderFuelNormChart(d);
}

function renderFuelNormChart(d) {
  const el = document.getElementById('fuelNormChart');
  if (!el || !window.Chart) return;
  const list = Object.entries(d.fuel.by_plate).filter(([, v]) => v.latest_l_per_100km !== null).sort((a, b) => b[1].latest_l_per_100km - a[1].latest_l_per_100km);
  if (fuelNormChart) fuelNormChart.destroy();
  fuelNormChart = new Chart(el.getContext('2d'), {
    type: 'bar',
    data: {
      labels: list.map(([p]) => p),
      datasets: [
        { label: 'L/100km gần nhất', data: list.map(([, v]) => v.latest_l_per_100km),
          backgroundColor: list.map(([, v]) => ((v.latest_l_per_100km - v.norm) / v.norm > 0.1 ? '#dc2626' : ((v.latest_l_per_100km - v.norm) / v.norm < -0.1 ? '#94a3b8' : '#10b981'))), borderRadius: 6 },
        { label: 'Định mức', data: list.map(([, v]) => v.norm), type: 'line', borderColor: '#f59e0b', backgroundColor: '#f59e0b', borderDash: [6, 4], pointRadius: 0, borderWidth: 2 },
      ],
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11, weight: 'bold' } } } },
               scales: { x: { ticks: { font: { size: 10 }, maxRotation: 70, minRotation: 50 } }, y: { beginAtZero: true, title: { display: true, text: 'L/100km' } } } },
  });
}

// Thẻ "Việc cần xử lý hôm nay" trên Tổng quan
function renderDashTodo(d) {
  const box = document.getElementById('dashTodoCard');
  if (!box || !d) return;
  const t = d.todo;
  const items = t.items;
  const row = i => `
      <div class="flex flex-wrap items-center gap-2 text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-200">
        ${chip(i.level)}<span class="font-bold text-slate-800">${esc(i.category)}</span>${plateBtn(i.plate)}${i.subject !== i.plate ? `<span class="text-slate-500">(${esc(i.subject)})</span>` : ''}
        <span class="ml-auto font-black ${ST_TEXT[i.level] || ''}">${esc(i.detail)}</span></div>`;
  box.innerHTML = `
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
      <div class="flex items-center gap-3">
        <div class="p-2.5 bg-rose-50 text-rose-600 rounded-2xl border border-rose-200"><i data-lucide="clipboard-list" class="w-5 h-5"></i></div>
        <div><h3 class="font-black text-slate-900 text-sm md:text-base">VIỆC CẦN XỬ LÝ — GIẤY TỜ & BẢO DƯỠNG</h3>
        <p class="text-xs text-slate-500">Nguồn: Google Sheets, đọc lúc ${esc(d.source.read_at)} • vàng ≤ ${d.thresholds.yellow} ngày, đỏ ≤ ${d.thresholds.red} ngày</p></div>
      </div>
      <div class="flex gap-2 text-[11px] font-black">
        ${[['overdue', 'Quá hạn', t.counts.overdue], ['soon', 'Sắp hạn', t.counts.soon], ['near', 'Gần hạn', t.counts.near], ['missing', 'Thiếu số liệu', t.missing_count]]
          .map(([s, l, n]) => `<span class="px-2.5 py-1.5 rounded-xl ${ST[s].cls}">${l}: ${n}</span>`).join('')}
      </div>
    </div>
    <div class="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-2">${items.slice(0, 8).map(row).join('') || '<p class="text-emerald-700 font-bold text-sm">Không có giấy tờ / bảo dưỡng quá hạn hoặc sắp hạn.</p>'}</div>
    ${items.length > 8 ? `<details class="mt-2"><summary class="cursor-pointer text-xs font-bold text-blue-700">Xem thêm ${items.length - 8} việc</summary>
      <div class="mt-2 grid grid-cols-1 lg:grid-cols-2 gap-2">${items.slice(8).map(row).join('')}</div></details>` : ''}
    ${t.missing.length ? `<details class="mt-2"><summary class="cursor-pointer text-xs font-bold text-slate-600">Số liệu còn thiếu trên Sheets (${t.missing_count})</summary>
      <div class="mt-2 space-y-1.5">${t.missing.map(mi => `<p class="text-xs text-slate-600"><b>${esc(mi.category)}</b> (${mi.count}): ${mi.plates.map(esc).join(' • ')}</p>`).join('')}</div></details>` : ''}`;
  if (window.lucide) lucide.createIcons();
}

// =====================================================================
// TRANG ĐỘI XE & MOOC — 2 khúc Ben / Thùng như bản cũ, hạn giấy tờ từ Sheets
// =====================================================================
const DOC_COLS = [
  ['GĐĐ Đầu Kéo', 'Giấy đi đường – đầu kéo'], ['GĐĐ Rơ-Moóc', 'Giấy đi đường – romoóc'],
  ['Đăng Kiểm Đầu Kéo', 'Đăng kiểm – đầu kéo'], ['Đăng Kiểm Rơ-Moóc', 'Đăng kiểm – romoóc'], ['Tem Đường Bộ', 'Tem đường bộ'],
];
function docCell(doc) {
  if (!doc || !doc.expiry) return '<span class="text-slate-400 font-bold">Thiếu</span>';
  const left = doc.days_left === null ? '' : (doc.days_left < 0 ? `quá ${-doc.days_left} ngày` : `còn ${doc.days_left} ngày`);
  return `<div class="font-mono font-bold text-slate-800">${dmy(doc.expiry)}</div><div class="text-[11px] font-bold ${ST_TEXT[doc.status] || ''}">${left}</div>`;
}
function worstStatus(list) {
  const order = ['overdue', 'soon', 'near', 'missing', 'ok'];
  const sts = list.map(d => d.status);
  return order.find(s => sts.includes(s)) || 'missing';
}

function xeVehiclesPage() {
  const fleet = (typeof FLEET_LIST !== 'undefined' && FLEET_LIST.length) ? FLEET_LIST
    : (xeData.dm.plates || []).map(p => ({ plate_number: p, vehicle_type: '', trailer_number: '', driver_name: '' }));
  const docsOf = p => xeData.docs.filter(d => samePlate(d.plate, p));
  const cols = [
    ['STT', (r, i) => `<span class="font-bold text-slate-400">${i + 1}</span>`, 'center'],
    ['Số Xe Đầu Kéo', r => plateBtn(r.plate_number)],
    ['Số Rơ-Moóc', r => `<span class="font-mono font-bold text-slate-800">${esc(r.trailer_number || (docsOf(r.plate_number)[0] || {}).trailer || '—')}</span>`],
    ...DOC_COLS.map(([label, kind]) => [label, r => docCell(docsOf(r.plate_number).find(d => d.kind === kind)), 'center']),
    ['Tình Trạng Giấy Tờ', r => chip(worstStatus(docsOf(r.plate_number))), 'center'],
  ];
  const ben = fleet.filter(v => v.vehicle_type === 'Xe Ben');
  const thung = fleet.filter(v => v.vehicle_type !== 'Xe Ben');
  const thr = `Đối chiếu bảng theo dõi trên Google Sheets (cảnh báo: vàng ≤ ${xeData.thresholds.yellow} ngày, đỏ ≤ ${xeData.thresholds.red} ngày). Bấm biển số để xem hồ sơ xe.`;
  return oldCard({ icon: 'truck', tone: 'orange', top: 'border-t-4 border-t-orange-500',
      title: `ĐỘI XE BEN (${ben.length} XE) — THEO DÕI GIẤY ĐI ĐƯỜNG & ĐĂNG KIỂM`, sub: thr,
      right: `<span class="px-3.5 py-1.5 bg-orange-50 text-orange-800 border border-orange-200 rounded-xl font-bold text-xs font-mono">${ben.length} Xe Ben</span>`,
      body: oldTable(cols, ben) })
    + oldCard({ icon: 'container', tone: 'blue', top: 'border-t-4 border-t-blue-500',
      title: `ĐỘI XE THÙNG / CÔNG DÀI (${thung.length} XE) — THEO DÕI GIẤY ĐI ĐƯỜNG & ĐĂNG KIỂM`, sub: 'Đối chiếu bảng theo dõi trên Google Sheets',
      right: `<span class="px-3.5 py-1.5 bg-blue-50 text-blue-800 border border-blue-200 rounded-xl font-bold text-xs font-mono">${thung.length} Xe Thùng</span>`,
      body: oldTable(cols, thung) });
}

// =====================================================================
// TRANG BẢO DƯỠNG THAY NHỚT
// =====================================================================
function xeMaintPage() {
  const m = xeData.maint;
  const kmCell = v => v === null || v === undefined ? '—' : (v < 0 ? `<b class="text-red-700">quá ${num(-v)} km</b>` : `<b class="${v <= 3000 ? (v <= 1000 ? 'text-red-600' : 'text-amber-700') : 'text-emerald-700'}">${num(v)}</b>`);
  const oil = oldTable([
    ['STT', (r, i) => `<span class="font-bold text-slate-400">${i + 1}</span>`, 'center'],
    ['Số Xe Đầu Kéo', r => plateBtn(r.plate)], ['Định Mức', r => num(r.norm_km), 'right'],
    ['Km Thay Gần Nhất', r => num(r.last_km), 'right'], ['Ngày Thay Gần Nhất', r => dmy(r.last_date), 'center'],
    ['Km Hiện Tại', r => `<b class="text-slate-900">${num(r.current_km)}</b>${r.odo_source_date ? `<div class="text-[10px] text-slate-500">ODO sổ dầu ${dmy(r.odo_source_date)}</div>` : ''}`, 'right'],
    ['Km Đến Hạn', r => `<span class="text-indigo-600 font-bold">${num(r.due_km)}</span>`, 'right'],
    ['Còn Lại (Km)', r => kmCell(r.remaining_km), 'right'], ['Tình Trạng', r => chip(r.status), 'center'],
    ['Ghi Chú Kỹ Thuật', r => `<span class="font-bold text-[11px] text-slate-700 whitespace-normal">${esc(r.warning || r.note || '')}</span>`],
  ], m.oil.filter(plateOk));
  const gear = oldTable([
    ['Số Xe', r => plateBtn(r.plate)], ['Ngày Thay', r => dmy(r.last_date), 'center'], ['Km Lúc Thay', r => num(r.last_km), 'right'],
    ['Còn Lại (Km)', r => kmCell(r.remaining_km), 'right'], ['Hạn Theo Ngày', r => dmy(r.due_date), 'center'], ['Tình Trạng', r => chip(r.status), 'center'],
  ], m.gearbox.filter(plateOk));
  const grease = oldTable([
    ['Số Xe', r => plateBtn(r.plate)], ['Lần Gần Nhất', r => dmy(r.last_date), 'center'], ['Hạn Tiếp Theo', r => dmy(r.due_date), 'center'],
    ['Còn Lại', r => r.days_left === null ? '—' : `${r.days_left} ngày`, 'right'], ['Tình Trạng', r => chip(r.status), 'center'],
  ], m.grease.filter(plateOk));
  const log = oldTable([
    ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Hạng Mục', r => esc(r.item)], ['Km ODO', r => num(r.odo), 'right'],
    ['Nội Dung', r => `<span class="whitespace-normal">${esc(r.content)}</span>`], ['Gara / NCC', r => esc(r.vendor)], ['Số Tiền', r => `<b>${money(r.amount)}</b>`, 'right'],
    ['Thanh Toán', r => esc(r.payment || '—')], ['', r => rowActions('bao-duong', r)],
  ], m.log.filter(r => monthOk(r) && plateOk(r)).slice().reverse(), 'Không có dòng trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '');
  return oldCard({ icon: 'wrench', tone: 'amber', title: 'BẢO DƯỠNG ĐỊNH KỲ — THAY NHỚT ĐỘNG CƠ (15.000 KM)',
      sub: 'Đồng bộ từ Google Sheets (tab BẢO DƯỠNG XE + MOOC). Km hiện tại = số lớn hơn giữa sheet và ODO mới nhất trong sổ dầu. Sắp hạn ≤ 1.000 km, gần hạn ≤ 3.000 km.',
      right: filterBar(false, true) + writeButtons('bao-duong'), body: oil })
    + oldCard({ icon: 'cog', tone: 'indigo', title: 'NHỚT HỘP SỐ (50.000 KM HOẶC 1 NĂM)', body: gear })
    + oldCard({ icon: 'droplets', tone: 'slate', title: 'BÔI MỠ RƠ-MOÓC (1 NĂM)', body: grease })
    + oldCard({ icon: 'notebook-pen', tone: 'blue', title: 'NHẬT KÝ BẢO DƯỠNG – SỬA CHỮA', right: filterBar(), body: log });
}

// =====================================================================
// TRANG THAY VỎ & BẠT PHÙNG LĨNH — bảng theo quý như bản cũ + nhật ký
// =====================================================================
function xeTiresPage() {
  const year = (xeMonth || new Date().toISOString()).slice(0, 4);
  const live = xeData.tires.filter(r => !r.cancelled && (r.date || '').startsWith(year));
  const byPlate = {};
  live.forEach(r => {
    const k = r.plate || '—';
    const q = Math.floor((Number(r.date.slice(5, 7)) - 1) / 3);
    byPlate[k] = byPlate[k] || { plate: k, q: [0, 0, 0, 0], total: 0, amount: 0 };
    byPlate[k].q[q] += Number(r.quantity) || 0;
    byPlate[k].total += Number(r.quantity) || 0;
    byPlate[k].amount += Number(r.amount) || 0;
  });
  const qRows = Object.values(byPlate).sort((a, b) => b.total - a.total);
  const qc = n => n ? `<b class="text-slate-800">${num(n)}</b>` : '<span class="text-slate-300">—</span>';
  const quarter = oldTable([
    ['Số Xe', r => plateBtn(r.plate)], ['Quý 1', r => qc(r.q[0]), 'center'], ['Quý 2', r => qc(r.q[1]), 'center'],
    ['Quý 3', r => qc(r.q[2]), 'center'], ['Quý 4', r => qc(r.q[3]), 'center'],
    [`Tổng Vỏ (${year})`, r => `<b class="text-blue-700">${num(r.total)} vỏ</b>`, 'right'], ['Tiền Vỏ', r => money(r.amount), 'right'],
  ], qRows, `Chưa có dòng thay vỏ năm ${year}`);
  const rows = xeData.tires.filter(r => monthOk(r) && plateOk(r)).slice().reverse();
  const tires = oldTable([
    ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Vị Trí', r => esc(r.position || '—')], ['Số Lượng', r => num(r.quantity), 'right'],
    ['Loại / Hiệu', r => esc(r.brand)], ['Gara / NCC', r => esc(r.vendor)], ['Số Tiền', r => `<b>${money(r.amount)}</b>`, 'right'],
    ['Thanh Toán', r => esc(r.payment || '—')], ['Ghi Chú', r => `<span class="whitespace-normal">${esc(r.note)}</span>`], ['', r => rowActions('thay-vo', r)],
  ], rows, 'Không có dòng trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '');
  const tarps = oldTable([
    ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Nội Dung', r => `<span class="whitespace-normal">${esc(r.content)}</span>`], ['NCC', r => esc(r.vendor)],
    ['Số HĐ', r => esc(r.invoice || '—')], ['Số Tiền', r => `<b>${money(r.amount)}</b>`, 'right'], ['Thanh Toán', r => esc(r.payment || '—')],
    ['Ghi Chú', r => `<span class="whitespace-normal">${esc(r.note)}</span>`], ['', r => rowActions('thay-bat', r)],
  ], xeData.tarps.filter(r => monthOk(r) && plateOk(r)).slice().reverse(), 'Không có dòng trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '');
  const liveMonth = rows.filter(r => !r.cancelled);
  return oldCard({ icon: 'disc', tone: 'amber', title: `THEO DÕI THAY VỎ XE — CẢ ĐỘI XE NĂM ${year}`, sub: 'Tổng hợp từ nhật ký THAY VỎ trên Google Sheets', body: quarter })
    + oldCard({ icon: 'notebook-pen', tone: 'blue', title: 'NHẬT KÝ THAY VỎ', right: filterBar() + writeButtons('thay-vo'),
      body: `<div class="grid grid-cols-2 gap-3">${stat('Số vỏ trong tháng', num(liveMonth.reduce((a, r) => a + (r.quantity || 0), 0)))}${stat('Tiền vỏ trong tháng', money(liveMonth.reduce((a, r) => a + (r.amount || 0), 0)))}</div>${tires}` })
    + oldCard({ icon: 'umbrella', tone: 'emerald', title: 'MAY / SỬA BẠT — PHÙNG LĨNH', right: writeButtons('thay-bat'), body: tarps });
}

// =====================================================================
// TRANG ĐỔ DẦU & ĐỊNH MỨC
// =====================================================================
function xeFuelPage() {
  const t = xeData.todo;
  const rows = xeData.fuel.rows.filter(r => monthOk(r) && plateOk(r)).slice().reverse();
  const live = rows.filter(r => !r.cancelled);
  const sum = k => live.reduce((a, r) => a + (Number(r[k]) || 0), 0);
  const debt = live.filter(r => (r.payment || '').startsWith('Công nợ')).reduce((a, r) => a + (r.amount || 0), 0);
  const byPlate = Object.entries(xeData.fuel.by_plate).filter(([p]) => !xePlate || samePlate(p, xePlate))
    .sort((a, b) => (b[1].latest_l_per_100km || 0) - (a[1].latest_l_per_100km || 0));
  const lag = t.fuel_log_lag_days;
  const norms = `Định mức: xe ben ${num(t.fuel_norms['Xe Ben'], 1)}, xe thùng ${num(t.fuel_norms['Xe Thùng'], 1)} L/100km (mức thực tế bình quân 07–09/2026).`;
  const perPlate = oldTable([
    ['Số Xe', r => plateBtn(r[0])], ['Số Lượt Đổ', r => num(r[1].fills), 'right'],
    ['L/100km Gần Nhất', r => { const v = r[1].latest_l_per_100km, n = r[1].norm; return v === null ? '—' : `<b class="${fuelCls(v, n)}">${num(v, 1)}</b>`; }, 'right'],
    ['Định Mức', r => num(r[1].norm, 1), 'right'], ['L/100km Bình Quân', r => num(r[1].avg_l_per_100km, 1), 'right'],
    ['Cảnh Báo', r => { const v = r[1].latest_l_per_100km, n = r[1].norm; if (v === null || !n) return '<span class="text-slate-400">—</span>'; const p = (v - n) / n * 100;
      return p > 10 ? `<span class="px-2 py-0.5 rounded-full text-[11px] font-black bg-red-100 text-red-700 border border-red-300">Vượt ${num(p, 1)}%</span>` : (p < -10 ? '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">Thấp bất thường</span>' : '<span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-300">Trong định mức</span>'); }, 'center'],
    ['ODO Mới Nhất', r => r[1].odo ? `${num(r[1].odo.odo)} <span class="text-[10px] text-slate-500">(${dmy(r[1].odo.date)})</span>` : '—', 'right'],
  ], byPlate);
  const alerts = oldTable([
    ['Xe', r => plateBtn(r.plate)], ['Từ – Đến', r => `${dmy(r.from)} → ${dmy(r.to)}`], ['Km', r => num(r.km), 'right'],
    ['Lít', r => num(r.liters, 1), 'right'], ['L/100km', r => `<b class="text-red-700">${num(r.l_per_100km, 1)}</b>`, 'right'], ['Định Mức', r => num(r.norm, 1), 'right'],
    ['Lệch', r => `<b class="text-red-700">+${num(r.deviation_pct, 1)}%</b>`, 'right'],
  ], t.fuel_alerts.filter(plateOk).slice().reverse(), 'Không có lần nào vượt định mức > 10%');
  const log = oldTable([
    ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Cây Dầu', r => esc(r.station)],
    ['Số Lít', r => num(r.liters, 2), 'right'], ['Đơn Giá', r => money(r.price), 'right'], ['Thành Tiền', r => `<b>${money(r.amount)}</b>`, 'right'],
    ['ODO', r => num(r.odo), 'right'], ['Bình', r => esc(r.tank)], ['Thanh Toán', r => esc(r.payment || '—')],
    ['Kiểm Tra', r => r.flags.length ? r.flags.map(f => `<span class="inline-block mb-1 px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 text-[11px] font-bold">${esc(f)}</span>`).join(' ') : '<span class="text-emerald-700 text-[11px] font-bold">OK</span>'],
    ['', r => rowActions('do-dau', r)],
  ], rows, 'Không có lượt đổ trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '');
  return oldCard({ icon: 'gauge', tone: 'amber', title: 'ĐỊNH MỨC TIÊU HAO THEO TỪNG XE (GIỮA 2 LẦN ĐẦY BÌNH)', sub: norms,
      right: `<span class="px-3 py-1.5 rounded-xl ${lag > 3 ? 'bg-red-50 text-red-700 border-red-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200'} border font-bold text-xs">Sổ dầu nhập đến ${dmy(t.fuel_log_last_date)}${lag !== null ? ` • trễ ${lag} ngày` : ''}</span>`, body: perPlate })
    + oldCard({ icon: 'alert-triangle', tone: 'rose', title: 'CẢNH BÁO HAO DẦU VƯỢT ĐỊNH MỨC > 10% (MỚI NHẤT TRƯỚC)', sub: 'Chỉ tính đoạn ≥ 300 km giữa 2 lần đổ đầy bình. Đoạn số liệu vô lý (nghi nhập sai) không tính vào đây.', body: alerts })
    + oldCard({ icon: 'fuel', tone: 'orange', title: 'SỔ ĐỔ DẦU', right: filterBar() + writeButtons('do-dau'),
      body: `<div class="grid grid-cols-2 lg:grid-cols-4 gap-3">${stat('Số lượt đổ', num(live.length))}${stat('Tổng số lít', num(sum('liters'), 1) + ' L')}${stat('Tổng tiền dầu', money(sum('amount')))}${stat('Còn nợ cây dầu', money(debt), debt ? 'text-red-600' : 'text-emerald-600')}</div>${log}` });
}

// =====================================================================
// TRANG CÔNG NỢ & CHI PHÍ XE
// =====================================================================
function xeCostsPage() {
  const total = xeData.debts.filter(g => g.unpaid > 0).reduce((a, g) => a + g.unpaid, 0);
  return oldCard({ icon: 'wallet', tone: 'rose', title: 'CÔNG NỢ NHÀ CUNG CẤP (DẦU • VỎ • BẠT • GARA)', sub: 'Chọn các dòng đã trả rồi bấm "Đánh dấu đã TT" — app ghi vào cột THANH TOÁN trên Sheets.',
      right: `<span class="px-3.5 py-1.5 bg-rose-50 text-rose-800 border border-rose-200 rounded-xl font-black text-sm font-mono">Còn nợ: ${money(total)}</span>`, body: xeDebtsHtml() })
    + oldCard({ icon: 'bar-chart-3', tone: 'emerald', title: 'CHI PHÍ XE THEO THÁNG', sub: 'Dầu + bảo dưỡng + vỏ + bạt theo từng xe, kèm chi phí / km.', body: xeCostsHtml() });
}

// ---------- khối dùng chung
function card(inner, extra = '') { return `<div class="bg-white rounded-2xl border border-slate-200 p-4 md:p-5 shadow-sm ${extra}">${inner}</div>`; }
function stat(label, value, cls = 'text-slate-900', sub = '') {
  return `<div class="bg-white rounded-2xl border border-slate-200 p-4"><p class="text-xs font-bold text-slate-500 uppercase">${label}</p>
    <p class="text-xl md:text-2xl font-black mt-1 break-words ${cls}">${value}</p>${sub ? `<p class="text-xs text-slate-500 mt-1">${sub}</p>` : ''}</div>`;
}
function select(id, options, value, onchange, allLabel) {
  return `<select id="${id}" onchange="${onchange}" class="px-3 py-2.5 rounded-xl border border-slate-300 bg-white text-base font-semibold">
    ${allLabel !== undefined ? `<option value="">${allLabel}</option>` : ''}
    ${options.map(o => { const [v, l] = Array.isArray(o) ? o : [o, o]; return `<option value="${esc(v)}" ${v === value ? 'selected' : ''}>${esc(l)}</option>`; }).join('')}
  </select>`;
}
function monthLabel(m) { const [y, mm] = m.split('-'); return `Tháng ${mm}/${y}`; }
function filterBar(withMonth = true, withPlate = true) {
  const plates = (xeData.dm.plates || []).map(p => [p, p]);
  return `<div class="flex flex-wrap gap-2 items-center">
    ${withMonth ? select('xeMonthSel', monthsAvailable().map(m => [m, monthLabel(m)]), xeMonth, 'xeMonth=this.value;renderXe()') : ''}
    ${withPlate ? select('xePlateSel', plates, xePlate, 'xePlate=this.value;renderXe()', 'Tất cả xe') : ''}
  </div>`;
}
const samePlate = (a, b) => (a || '').replace(/[-. ]/g, '').toUpperCase() === (b || '').replace(/[-. ]/g, '').toUpperCase();
const plateOk = r => !xePlate || samePlate(r.plate, xePlate);
const monthOk = r => !xeMonth || (r.date || '').startsWith(xeMonth);

/** Danh sách responsive: bảng trên máy tính, thẻ trên điện thoại. cols: [[tiêu đề, hàm(row) -> html, 'right'?]] */
function rlist(rows, cols, empty = 'Không có dữ liệu', rowCls = () => '') {
  if (!rows.length) return `<p class="p-5 text-center text-slate-500 bg-white rounded-2xl border border-slate-200">${empty}</p>`;
  const table = `<div class="hidden md:block overflow-x-auto rounded-2xl border border-slate-200 bg-white">
    <table class="w-full text-sm"><thead class="bg-slate-100 text-slate-700 text-xs uppercase"><tr>
      ${cols.map(c => `<th class="py-3 px-3 text-left ${c[2] === 'right' ? 'text-right' : ''}">${c[0]}</th>`).join('')}
    </tr></thead><tbody class="divide-y divide-slate-100">
      ${rows.map(r => `<tr class="${rowCls(r)}">${cols.map(c => `<td class="py-2.5 px-3 align-top ${c[2] === 'right' ? 'text-right font-mono' : ''}">${c[1](r)}</td>`).join('')}</tr>`).join('')}
    </tbody></table></div>`;
  const cards = `<div class="md:hidden space-y-2.5">${rows.map(r => `
    <div class="bg-white rounded-2xl border border-slate-200 p-4 space-y-1.5 ${rowCls(r)}">
      ${cols.map(c => `<div class="flex justify-between gap-3 text-[15px]"><span class="text-slate-500 shrink-0">${c[0]}</span><span class="text-right font-semibold text-slate-900">${c[1](r)}</span></div>`).join('')}
    </div>`).join('')}</div>`;
  return table + cards;
}

function writeButtons(kind) {
  const can = xeData.write_enabled && xeData.can_write;
  const title = !xeData.write_enabled ? 'Chưa bật ghi vào Sheets (xem apps_script/HUONG_DAN.md)' : (!xeData.can_write ? 'Tài khoản chỉ được xem' : '');
  return `<button onclick="openXeForm('${kind}')" ${can ? '' : 'disabled'} title="${esc(title)}"
    class="px-5 py-3 rounded-xl font-bold text-base ${can ? 'bg-blue-600 text-white active:scale-95' : 'bg-slate-200 text-slate-500 cursor-not-allowed'}">+ Nhập mới</button>
    ${can ? '' : `<span class="text-xs text-slate-500">${esc(title)}</span>`}`;
}

function rowActions(kind, r) {
  if (!r.uuid || r.cancelled || !(xeData.write_enabled && xeData.can_write)) return r.cancelled ? '<span class="text-xs text-slate-500">Đã hủy</span>' : '';
  return `<span class="inline-flex gap-1.5">
    <button onclick='openXeForm("${kind}", ${JSON.stringify(r).replace(/'/g, '&#39;')})' class="px-2.5 py-1.5 rounded-lg bg-slate-100 border text-xs font-bold">Sửa</button>
    <button onclick="cancelXeRow('${kind}','${esc(r.uuid)}')" class="px-2.5 py-1.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs font-bold">Hủy</button></span>`;
}


// ---------- 7. Công nợ
function xeDebtsHtml() {
  const groups = xeData.debts.filter(g => g.unpaid > 0 || g.no_status > 0);
  const total = groups.reduce((a, g) => a + g.unpaid, 0);
  const can = xeData.write_enabled && xeData.can_write;
  return `<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      ${['Dầu', 'Vỏ xe', 'Bạt', 'Bảo dưỡng – gara'].map(c => stat(c, money(xeData.debts.filter(g => g.category === c).reduce((a, g) => a + g.unpaid, 0)), 'text-red-600', 'còn nợ')).join('')}
    </div>
    <p class="mb-3 text-sm text-slate-600">Tổng còn nợ: <b class="text-red-700">${money(total)}</b>. Dòng "chưa ghi thanh toán" chưa tính là nợ.</p>
    <div class="space-y-3">${groups.map((g, gi) => card(`
      <div class="flex flex-wrap justify-between gap-2 items-center">
        <div><p class="text-xs font-bold text-slate-500 uppercase">${esc(g.category)}</p><p class="text-lg font-black">${esc(g.vendor)}</p></div>
        <div class="text-right"><p class="text-xl font-black text-red-700">${money(g.unpaid)}</p><p class="text-xs text-slate-500">${g.unpaid_count} dòng nợ • đã trả ${money(g.paid)}${g.no_status_count ? ` • chưa ghi TT: ${money(g.no_status)} (${g.no_status_count} dòng)` : ''}</p></div>
      </div>
      ${g.items.length ? `<details class="mt-3"><summary class="cursor-pointer text-sm font-bold text-blue-700">Xem ${g.items.length} dòng nợ</summary>
        <div class="mt-2 space-y-1.5">${g.items.slice().reverse().map((it, ii) => `
          <label class="flex items-center gap-3 p-2.5 rounded-xl border border-slate-200 text-[15px]">
            <input type="checkbox" class="w-5 h-5 xe-debt-cb" ${can ? '' : 'disabled'} data-item='${JSON.stringify({ kind: it.kind, sheet_row: it.sheet_row, uuid: it.uuid || '', plate: it.plate, date: it.date, amount: it.amount }).replace(/'/g, '&#39;')}' />
            <span class="w-24 shrink-0">${dmy(it.date)}</span><span class="font-mono font-bold">${esc(it.plate)}</span>
            <span class="ml-auto font-mono font-bold">${money(it.amount)}</span><span class="text-xs text-slate-400">dòng ${it.sheet_row}</span>
          </label>`).join('')}</div></details>` : ''}`)).join('')}
    </div>
    <div class="sticky bottom-20 md:bottom-4 mt-4 flex flex-wrap gap-2 items-center bg-white/95 border border-slate-200 rounded-2xl p-3 shadow-lg">
      ${select('xePayMethod', [['transfer', 'Chuyển khoản'], ['cash', 'Tiền mặt']], 'transfer', '')}
      <input type="date" id="xePayDate" value="${new Date().toISOString().slice(0, 10)}" class="px-3 py-2.5 rounded-xl border border-slate-300 text-base" />
      <button onclick="markDebtsPaid()" ${can ? '' : 'disabled'} class="px-5 py-3 rounded-xl font-bold ${can ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-500'}">Đánh dấu đã TT các dòng đã chọn</button>
      ${can ? '' : '<span class="text-xs text-slate-500">Chưa bật ghi vào Sheets hoặc tài khoản chỉ được xem</span>'}
    </div>`;
}

async function markDebtsPaid() {
  const items = [...document.querySelectorAll('.xe-debt-cb:checked')].map(cb => JSON.parse(cb.dataset.item));
  if (!items.length) return xeToast('Chưa chọn dòng nào', false);
  const total = items.reduce((a, i) => a + (i.amount || 0), 0);
  if (!confirm(`Đánh dấu ${items.length} dòng (${money(total)}) là ĐÃ THANH TOÁN trên Google Sheets?`)) return;
  try {
    const res = await fetch(`${API_BASE}/xe/cong-no/da-tt`, { method: 'POST', headers: getHeaders(),
      body: JSON.stringify({ items, method: document.getElementById('xePayMethod').value, date: document.getElementById('xePayDate').value }) });
    const json = await res.json();
    if (!res.ok) throw new Error(typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail));
    xeToast(`${json.message}${json.skipped.length ? ` — bỏ qua ${json.skipped.length} dòng đã thay đổi` : ''}`, true);
    loadXe(true);
  } catch (err) { xeToast(err.message, false); }
}

// ---------- 8. Chi phí theo tháng
function xeCostsHtml() {
  const rows = xeData.costs.filter(r => r.month === xeMonth && plateOk(r)).sort((a, b) => b.total - a.total);
  const tot = k => rows.reduce((a, r) => a + (r[k] || 0), 0);
  return `<div class="flex flex-wrap gap-2 items-center justify-between mb-3">${filterBar()}
      <button onclick="downloadXeExcel()" class="px-5 py-3 rounded-xl bg-emerald-600 text-white font-bold">Xuất Excel tháng cho kế toán</button></div>
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-4">
      ${stat('Dầu', money(tot('fuel')))}${stat('Bảo dưỡng', money(tot('maint')))}${stat('Vỏ', money(tot('tires')))}${stat('Bạt', money(tot('tarps')))}${stat('Tổng', money(tot('total')), 'text-blue-700')}
    </div>
    <p class="text-sm text-slate-500 mb-2">Km trong tháng tính theo ODO sổ dầu (lần đổ cuối tháng trước → lần cuối tháng này). Thiếu ODO thì không tính chi phí/km.</p>
    ${rlist(rows, [
      ['Xe', r => plateBtn(r.plate)], ['Dầu', r => money(r.fuel), 'right'], ['Lít', r => num(r.fuel_liters), 'right'],
      ['Bảo dưỡng', r => money(r.maint), 'right'], ['Vỏ', r => money(r.tires), 'right'], ['Bạt', r => money(r.tarps), 'right'],
      ['Tổng', r => `<b>${money(r.total)}</b>`, 'right'], ['Km', r => num(r.km), 'right'], ['Chi phí/km', r => money(r.cost_per_km), 'right'],
    ], 'Chưa có chi phí trong tháng này')}`;
}

async function downloadXeExcel() {
  try {
    const res = await fetch(`${API_BASE}/xe/export?month=${xeMonth}`, { headers: getHeaders() });
    if (!res.ok) throw new Error((await res.json()).detail || 'Lỗi xuất file');
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `XE_CHI_PHI_${xeMonth}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (err) { xeToast(err.message, false); }
}


// ---------- Hồ sơ 1 xe
async function openVehicleProfile(plate) {
  const modal = document.getElementById('modalVehicleProfile');
  const body = document.getElementById('vehicleProfileBody');
  modal.classList.remove('hidden');
  body.innerHTML = '<p class="p-6 text-center text-slate-500">Đang tải…</p>';
  try {
    const res = await fetch(`${API_BASE}/xe/vehicle/${encodeURIComponent(plate)}`, { headers: getHeaders() });
    const v = await res.json();
    if (!res.ok) throw new Error(v.detail || 'Lỗi');
    const fs = v.fuel_summary || {};
    const costs = v.costs.slice().reverse();
    document.getElementById('vehicleProfileTitle').innerText = `Hồ sơ xe ${v.vehicle.plate_number}`;
    body.innerHTML = `
      <div class="grid grid-cols-2 gap-3">
        ${stat('Loại xe', esc(v.vehicle.vehicle_type))}${stat('Romoóc', esc(v.vehicle.trailer_number || '—'))}
        ${stat('Tài xế', esc(v.vehicle.driver_name || 'Chưa phân công'), 'text-slate-900 text-lg')}
        ${stat('ODO mới nhất', fs.odo ? num(fs.odo.odo) : '—', 'text-slate-900', fs.odo ? `sổ dầu ${dmy(fs.odo.date)}` : '')}
        ${stat('L/100km gần nhất', num(fs.latest_l_per_100km, 1), fuelCls(fs.latest_l_per_100km, fs.norm), `bình quân ${num(fs.avg_l_per_100km, 1)} • định mức ${num(fs.norm, 1)}`)}
        ${stat('Việc cần xử lý', v.todo.length, v.todo.length ? 'text-red-600' : 'text-emerald-600')}
      </div>
      <h4 class="mt-5 mb-2 font-black">Giấy tờ</h4>
      ${rlist(v.docs, [['Loại', r => esc(r.kind)], ['Hạn', r => dmy(r.expiry)], ['Còn lại', r => r.days_left === null ? '—' : (r.days_left < 0 ? `<b class="text-red-700">quá ${-r.days_left} ngày</b>` : `${r.days_left} ngày`), 'right'], ['', r => chip(r.status)]])}
      <h4 class="mt-5 mb-2 font-black">Bảo dưỡng định kỳ</h4>
      ${rlist([v.oil && { k: 'Nhớt máy', s: v.oil.status, d: v.oil.remaining_km !== null ? `còn ${num(v.oil.remaining_km)} km` : (v.oil.warning || 'thiếu số liệu') },
               v.gearbox && { k: 'Nhớt hộp số', s: v.gearbox.status, d: v.gearbox.remaining_km !== null ? `còn ${num(v.gearbox.remaining_km)} km` : 'thiếu số liệu' },
               v.grease && { k: 'Bôi mỡ romoóc', s: v.grease.status, d: v.grease.days_left !== null ? `còn ${v.grease.days_left} ngày` : 'chưa có ngày' }].filter(Boolean),
        [['Hạng mục', r => r.k], ['Tình trạng', r => chip(r.s)], ['Còn lại', r => esc(r.d)]])}
      <h4 class="mt-5 mb-2 font-black">Chi phí theo tháng</h4>
      ${rlist(costs, [['Tháng', r => monthLabel(r.month)], ['Dầu', r => money(r.fuel), 'right'], ['Bảo dưỡng', r => money(r.maint), 'right'],
        ['Vỏ', r => money(r.tires), 'right'], ['Bạt', r => money(r.tarps), 'right'], ['Tổng', r => `<b>${money(r.total)}</b>`, 'right'],
        ['Km', r => num(r.km), 'right'], ['đ/km', r => money(r.cost_per_km), 'right']])}
      <h4 class="mt-5 mb-2 font-black">Tiêu hao (giữa 2 lần đầy bình)</h4>
      ${rlist(v.consumption.slice().reverse(), [['Từ – đến', r => `${dmy(r.from)} → ${dmy(r.to)}`], ['Km', r => num(r.km), 'right'], ['Lít', r => num(r.liters, 1), 'right'],
        ['L/100km', r => `<b class="${fuelCls(r.l_per_100km, r.norm)}">${num(r.l_per_100km, 1)}</b>${r.alert === 'under' ? ' <span class="text-xs text-slate-500">thấp bất thường — kiểm tra số liệu</span>' : (r.alert === 'data' ? ' <span class="text-xs text-slate-500">vô lý — nghi sai số liệu</span>' : '')}`, 'right']])}
      <h4 class="mt-5 mb-2 font-black">Bảo dưỡng – vỏ – bạt gần đây</h4>
      ${rlist([...v.maint_log.map(r => ({ ...r, t: 'Bảo dưỡng', c: `${r.item} ${r.content || ''}` })), ...v.tires.map(r => ({ ...r, t: 'Vỏ', c: `${num(r.quantity)} vỏ ${r.position || ''} ${r.brand || ''}` })),
               ...v.tarps.map(r => ({ ...r, t: 'Bạt', c: r.content }))].sort((a, b) => (b.date || '').localeCompare(a.date || '')).slice(0, 20),
        [['Ngày', r => dmy(r.date)], ['Loại', r => r.t], ['Nội dung', r => esc(r.c)], ['Số tiền', r => money(r.amount), 'right']])}
      <p class="mt-4 text-xs text-slate-500">Nguồn: Google Sheets, đọc lúc ${esc(v.source.read_at)}. Lịch sử chuyến xem ở mục Điều xe.</p>`;
  } catch (err) {
    body.innerHTML = `<p class="p-5 text-red-700 font-bold">${esc(err.message)}</p>`;
  }
}

// ---------- Form nhập (1 cột, nút to, bàn phím số)
const XE_FORMS = {
  'do-dau': { title: 'Nhập đổ dầu', fields: [
    ['date', 'Ngày đổ', 'date'], ['plate', 'Số xe', 'plates'], ['station', 'Cây dầu', 'stations'],
    ['liters', 'Số lít', 'decimal'], ['price', 'Đơn giá (đ/lít)', 'number'], ['odo', 'KM lúc đổ (ODO)', 'number'],
    ['tank', 'Tình trạng bình', 'tank'], ['invoice', 'Số hóa đơn', 'text'], ['payment', 'Thanh toán', 'payment'],
    ['paid_date', 'Ngày thanh toán', 'date-opt'], ['note', 'Ghi chú', 'text']] },
  'bao-duong': { title: 'Nhập bảo dưỡng / sửa chữa', fields: [
    ['date', 'Ngày', 'date'], ['plate', 'Biển số', 'plates'], ['item', 'Hạng mục', 'maint_items'], ['odo', 'KM ODO', 'number'],
    ['content', 'Nội dung', 'text'], ['vendor', 'Gara / NCC', 'garages'], ['invoice', 'Số HĐ', 'text'],
    ['amount', 'Số tiền (đ)', 'number'], ['payment', 'Thanh toán', 'paid2'], ['note', 'Ghi chú', 'text']] },
  'thay-vo': { title: 'Nhập thay vỏ', fields: [
    ['date', 'Ngày', 'date'], ['plate', 'Biển số', 'plates'], ['position', 'Vị trí', 'tirepos'], ['quantity', 'Số lượng', 'number'],
    ['brand', 'Loại / Hiệu', 'text'], ['vendor', 'Gara / NCC', 'garages'], ['invoice', 'Số HĐ', 'text'],
    ['amount', 'Số tiền (đ)', 'number'], ['payment', 'Thanh toán', 'paid2'], ['note', 'Ghi chú', 'text']] },
  'thay-bat': { title: 'Nhập may / sửa bạt', fields: [
    ['date', 'Ngày', 'date'], ['plate', 'Biển số', 'plates'], ['content', 'Nội dung', 'text'], ['vendor', 'NCC', 'garages'],
    ['invoice', 'Số HĐ', 'text'], ['amount', 'Số tiền (đ)', 'number'], ['payment', 'Thanh toán', 'paid2'], ['note', 'Ghi chú', 'text']] },
};
let xeFormState = null;

function openXeForm(kind, row) {
  const cfg = XE_FORMS[kind];
  const dm = xeData.dm;
  const today = new Date().toISOString().slice(0, 10);
  const lists = { plates: dm.plates, stations: dm.stations, tank: dm.tank, payment: dm.payment, maint_items: dm.maint_items,
                  garages: dm.garages, paid2: ['Chưa thanh toán', 'Đã thanh toán'], tirepos: ['Đầu kéo', 'Romoóc', 'Dự phòng'] };
  const val = (k) => {
    if (!row) return k === 'date' ? today : (k === 'tank' ? 'Đầy bình' : (k === 'vendor' && kind === 'thay-bat' ? 'Phùng Lĩnh' : ''));
    const map = { content: row.content, item: row.item, plate: (row.plate || '').replace(/[-. ]/g, '') };
    return (k in map ? map[k] : row[k]) ?? '';
  };
  xeFormState = { kind, uuid: row ? row.uuid : (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random()), edit: !!row };
  const inputCls = 'w-full px-4 py-3.5 rounded-xl border border-slate-300 bg-white text-base';
  document.getElementById('xeFormTitle').innerText = (row ? 'Sửa — ' : '') + cfg.title;
  document.getElementById('xeFormFields').innerHTML = cfg.fields.map(([k, label, type]) => {
    let input;
    if (lists[type]) {
      const cur = String(val(k));
      input = `<select name="${k}" class="${inputCls}" ${['plate', 'station', 'tank', 'item', 'content'].includes(k) || type === 'plates' ? 'required' : ''}>
        <option value="">— chọn —</option>${(lists[type] || []).map(o => `<option ${String(o).replace(/[-. ]/g, '') === cur.replace(/[-. ]/g, '') || o === cur ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
    } else if (type === 'date' || type === 'date-opt') {
      input = `<input type="date" name="${k}" value="${esc(val(k))}" max="${today}" class="${inputCls}" ${type === 'date' ? 'required' : ''} />`;
    } else if (type === 'decimal' || type === 'number') {
      input = `<input type="text" name="${k}" inputmode="${type === 'decimal' ? 'decimal' : 'numeric'}" value="${esc(val(k))}" class="${inputCls} font-mono" autocomplete="off" />`;
    } else {
      input = `<input type="text" name="${k}" value="${esc(val(k))}" class="${inputCls}" autocomplete="off" ${k === 'content' && kind === 'thay-bat' ? 'required' : ''} />`;
    }
    return `<label class="block"><span class="block text-sm font-bold text-slate-700 mb-1">${label}</span>${input}</label>`;
  }).join('') + (kind === 'do-dau' ? '<p id="xeFormAmount" class="text-base font-bold text-slate-700">Thành tiền: —</p>' : '');
  document.getElementById('xeFormMsg').innerHTML = '';
  document.getElementById('xeFormConfirm').classList.add('hidden');
  const form = document.getElementById('xeForm');
  form.oninput = () => {
    if (kind !== 'do-dau') return;
    const l = parseNum(form.liters.value), p = parseNum(form.price.value);
    document.getElementById('xeFormAmount').innerText = 'Thành tiền: ' + (l && p ? money(l * p) : '—');
  };
  form.oninput();
  document.getElementById('modalXeForm').classList.remove('hidden');
  setTimeout(() => { const f = form.querySelector('select,input'); if (f) f.focus(); }, 50);
}

function parseNum(s) {
  if (s === null || s === undefined || String(s).trim() === '') return null;
  let t = String(s).trim().replace(/\s/g, '');
  if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(t)) t = t.replace(/\./g, '').replace(',', '.');
  else t = t.replace(',', '.');
  const n = Number(t);
  return isNaN(n) ? NaN : n;
}

async function submitXeForm(e, confirmWarnings = false) {
  if (e) e.preventDefault();
  const form = document.getElementById('xeForm');
  const st = xeFormState;
  const body = { uuid: st.uuid, confirm_warnings: confirmWarnings };
  for (const [k, , type] of XE_FORMS[st.kind].fields) {
    const v = form[k].value.trim();
    if (type === 'decimal' || type === 'number') {
      const n = parseNum(v);
      if (Number.isNaN(n)) return showXeFormMsg([`"${k}" không phải số`], []);
      body[k] = n;
    } else body[k] = v || (type === 'date-opt' ? null : '');
  }
  const btn = document.getElementById('xeFormSubmit');
  btn.disabled = true; btn.innerText = 'Đang ghi…';
  try {
    const url = st.edit ? `${API_BASE}/xe/${st.kind}/${encodeURIComponent(st.uuid)}` : `${API_BASE}/xe/${st.kind}`;
    const res = await fetch(url, { method: st.edit ? 'PUT' : 'POST', headers: getHeaders(), body: JSON.stringify(body) });
    const json = await res.json();
    if (res.status === 409) { showXeFormMsg([], json.detail.warnings); document.getElementById('xeFormConfirm').classList.remove('hidden'); return; }
    if (res.status === 422 && json.detail && json.detail.errors) return showXeFormMsg(json.detail.errors, json.detail.warnings || []);
    if (!res.ok) throw new Error(typeof json.detail === 'string' ? json.detail : JSON.stringify(json.detail));
    closeModal('modalXeForm');
    xeToast(json.duplicate ? 'Dòng này đã được ghi trước đó — không ghi trùng' : `${json.message}`, true);
    loadXe(true);
  } catch (err) {
    showXeFormMsg([err.message], []);
  } finally {
    btn.disabled = false; btn.innerText = 'Ghi vào Google Sheets';
  }
}

function showXeFormMsg(errors, warnings) {
  document.getElementById('xeFormMsg').innerHTML =
    errors.map(m => `<p class="p-3 rounded-xl bg-red-50 border border-red-300 text-red-800 font-bold">${esc(m)}</p>`).join('') +
    warnings.map(m => `<p class="p-3 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 font-semibold">⚠ ${esc(m)}</p>`).join('');
}

async function cancelXeRow(kind, uuid) {
  const reason = prompt('Lý do hủy dòng này? (dòng sẽ được đánh dấu ĐÃ HỦY, không bị xóa)');
  if (reason === null) return;
  try {
    const res = await fetch(`${API_BASE}/xe/${kind}/${encodeURIComponent(uuid)}/huy`, { method: 'POST', headers: getHeaders(), body: JSON.stringify({ reason }) });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Lỗi hủy');
    xeToast(json.message, true);
    loadXe(true);
  } catch (err) { xeToast(err.message, false); }
}

function xeToast(msg, ok) {
  const el = document.getElementById('xeToast');
  el.className = `fixed left-1/2 -translate-x-1/2 bottom-24 md:bottom-6 z-[60] px-5 py-3 rounded-2xl shadow-xl text-base font-bold ${ok ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'}`;
  el.innerText = msg;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add('hidden'), 5000);
}

