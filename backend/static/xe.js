// =====================================================================
// MỤC "XE & CHI PHÍ" (GĐ2) — đọc Google Sheets, ghi qua Apps Script
// Màu trạng thái cố định: đỏ = quá/sắp hạn, vàng = gần hạn, xanh = ổn, xám = thiếu số liệu
// =====================================================================
let xeData = null;
let xeSub = 'todo';
let xeMonth = null;
let xePlate = '';
let xeDocKind = '';

const XE_SUBS = [
  ['todo', 'Việc cần xử lý'], ['docs', 'Giấy tờ'], ['fuel', 'Đổ dầu'], ['maint', 'Bảo dưỡng'],
  ['tires', 'Thay vỏ'], ['tarps', 'Thay bạt'], ['debts', 'Công nợ'], ['costs', 'Chi phí / tháng'], ['fleet', 'Danh sách xe'],
];

const ST = {
  overdue: { label: 'Quá hạn', cls: 'bg-red-600 text-white' },
  soon: { label: 'Sắp hạn', cls: 'bg-red-100 text-red-800 border border-red-300' },
  near: { label: 'Gần hạn', cls: 'bg-amber-100 text-amber-900 border border-amber-300' },
  ok: { label: 'Ổn', cls: 'bg-emerald-100 text-emerald-800 border border-emerald-300' },
  missing: { label: 'Thiếu số liệu', cls: 'bg-slate-200 text-slate-700 border border-slate-300' },
};

// ---------- định dạng
const money = v => (v === null || v === undefined || v === '') ? '—' : `${Math.round(Number(v)).toLocaleString('vi-VN')} đ`;
const num = (v, d = 0) => (v === null || v === undefined || v === '') ? '—' : Number(v).toLocaleString('vi-VN', { maximumFractionDigits: d });
const dmy = s => s ? s.slice(0, 10).split('-').reverse().join('/') : '—';
const chip = st => { const s = ST[st] || ST.missing; return `<span class="inline-block px-2.5 py-1 rounded-lg text-xs font-bold whitespace-nowrap ${s.cls}">${s.label}</span>`; };
const plateBtn = p => `<button type="button" onclick="openVehicleProfile('${escHtml(p)}')" class="font-mono font-black text-blue-700 underline decoration-dotted underline-offset-2 text-sm">${escHtml(p)}</button>`;
const esc = v => escHtml(v ?? '');
// Màu L/100km: đỏ = vượt định mức > 10%, xám = thấp bất thường (thường do số liệu), xanh = trong định mức
const fuelCls = (v, n) => (v === null || v === undefined || !n) ? 'text-slate-500' : ((v - n) / n > 0.1 ? 'text-red-700' : ((v - n) / n < -0.1 ? 'text-slate-500' : 'text-emerald-700'));

// ---------- tải dữ liệu
async function loadXe(force = false) {
  const box = document.getElementById('xeContent');
  if (box && !xeData) box.innerHTML = '<p class="p-6 text-center text-slate-500">Đang đọc Google Sheets…</p>';
  try {
    const res = await fetch(`${API_BASE}/xe/data${force ? '?refresh=1' : ''}`, { headers: getHeaders() });
    const json = await res.json();
    if (!res.ok) throw new Error(json.detail || 'Không đọc được dữ liệu');
    xeData = json;
    if (!xeMonth) xeMonth = latestMonth();
    renderXe();
    renderDashTodo(json);
  } catch (err) {
    if (box) box.innerHTML = `<div class="p-5 rounded-2xl bg-red-50 border border-red-300 text-red-800 font-bold">${esc(err.message)}</div>`;
  }
}

function latestMonth() {
  const ms = (xeData.fuel.rows || []).map(r => (r.date || '').slice(0, 7)).filter(Boolean).sort();
  return ms.length ? ms[ms.length - 1] : new Date().toISOString().slice(0, 7);
}

function monthsAvailable() {
  const s = new Set();
  [...xeData.fuel.rows, ...xeData.maint.log, ...xeData.tires, ...xeData.tarps].forEach(r => r.date && s.add(r.date.slice(0, 7)));
  return [...s].sort().reverse();
}

function switchXeSub(sub) { xeSub = sub; renderXe(); }

function renderXe() {
  if (!xeData) return;
  const head = document.getElementById('xeHeader');
  if (head) {
    const src = xeData.source;
    head.innerHTML = `
      <div class="flex flex-wrap items-center gap-2 text-sm">
        <span class="px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-200 text-slate-700">Nguồn: Google Sheets • đọc lúc <b>${esc(src.read_at)}</b></span>
        ${xeData.stale_error ? `<span class="px-2.5 py-1 rounded-lg bg-amber-100 border border-amber-300 text-amber-900">Đang hiện bản cũ — lỗi đọc mới: ${esc(xeData.stale_error)}</span>` : ''}
        <span class="px-2.5 py-1 rounded-lg ${xeData.write_enabled ? 'bg-emerald-100 border border-emerald-300 text-emerald-800' : 'bg-slate-100 border border-slate-200 text-slate-600'}">
          Ghi vào Sheets: <b>${xeData.write_enabled ? 'đang bật' : 'chưa bật'}</b></span>
        <button onclick="loadXe(true)" class="ml-auto px-4 py-2.5 rounded-xl bg-slate-900 text-white font-bold text-sm active:scale-95">Làm mới</button>
      </div>
      ${src.missing_tabs.length ? `<p class="mt-2 text-sm text-red-700 font-bold">Không thấy tab: ${src.missing_tabs.join(', ')}</p>` : ''}`;
  }
  const nav = document.getElementById('xeSubnav');
  if (nav) {
    nav.innerHTML = XE_SUBS.map(([k, label]) => `
      <button onclick="switchXeSub('${k}')" class="shrink-0 px-4 py-2.5 rounded-xl text-sm font-bold border transition ${xeSub === k ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-slate-700 border-slate-200'}">${label}</button>`).join('');
  }
  const box = document.getElementById('xeContent');
  const fn = { todo: xeTodoHtml, docs: xeDocsHtml, fuel: xeFuelHtml, maint: xeMaintHtml, tires: xeTiresHtml,
               tarps: xeTarpsHtml, debts: xeDebtsHtml, costs: xeCostsHtml, fleet: xeFleetHtml }[xeSub];
  box.innerHTML = fn();
  if (window.lucide) lucide.createIcons();
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

// ---------- 1. Việc cần xử lý
function xeTodoHtml() {
  const t = xeData.todo;
  const lag = t.fuel_log_lag_days;
  return `
  <div class="grid grid-cols-2 lg:grid-cols-5 gap-3">
    ${stat('Quá hạn', t.counts.overdue, t.counts.overdue ? 'text-red-600' : 'text-emerald-600')}
    ${stat('Sắp hạn', t.counts.soon, t.counts.soon ? 'text-red-600' : 'text-emerald-600', `≤ ${xeData.thresholds.red} ngày`)}
    ${stat('Gần hạn', t.counts.near, t.counts.near ? 'text-amber-600' : 'text-emerald-600', `≤ ${xeData.thresholds.yellow} ngày`)}
    ${stat('Thiếu số liệu', t.missing_count, 'text-slate-600')}
    ${stat('Sổ dầu nhập đến', dmy(t.fuel_log_last_date), lag > 3 ? 'text-red-600' : 'text-slate-900', lag !== null ? `trễ ${lag} ngày` : '')}
  </div>
  <h3 class="mt-5 mb-2 font-black text-slate-900 text-lg">Việc cần xử lý — xếp theo mức độ</h3>
  ${rlist(t.items, [
    ['Mức', r => chip(r.level)], ['Hạng mục', r => esc(r.category)], ['Xe / romoóc', r => `${plateBtn(r.plate)}${r.subject !== r.plate ? ` <span class="text-slate-500 text-xs">(${esc(r.subject)})</span>` : ''}`],
    ['Hạn', r => dmy(r.due)], ['Còn lại', r => `<b>${esc(r.detail)}</b>`],
  ], 'Không có việc quá hạn / sắp hạn')}
  ${t.fuel_alerts.length ? `<h3 class="mt-5 mb-2 font-black text-slate-900 text-lg">Hao dầu vượt định mức &gt; 10% (mới nhất trước)</h3>
    <p class="text-sm text-slate-500 mb-2">Tính giữa 2 lần đổ đầy bình (≥ 300 km), từ sổ ĐỔ DẦU. Định mức: xe ben ${num(t.fuel_norms['Xe Ben'], 1)}, xe thùng ${num(t.fuel_norms['Xe Thùng'], 1)} L/100km (mức thực tế bình quân 07–09/2026).</p>
    ${rlist(t.fuel_alerts.slice().reverse(), [
      ['Xe', r => plateBtn(r.plate)], ['Từ – đến', r => `${dmy(r.from)} → ${dmy(r.to)}`], ['Km', r => num(r.km), 'right'],
      ['Lít', r => num(r.liters, 1), 'right'], ['L/100km', r => `<b class="text-red-700">${num(r.l_per_100km, 1)}</b>`, 'right'], ['Định mức', r => num(r.norm, 1), 'right'],
      ['Lệch', r => `${r.deviation_pct > 0 ? '+' : ''}${num(r.deviation_pct, 1)}%`, 'right'],
    ])}` : ''}
  <h3 class="mt-5 mb-2 font-black text-slate-900 text-lg">Số liệu còn thiếu</h3>
  <div class="space-y-2">${t.missing.map(m => `
    <details class="bg-white rounded-2xl border border-slate-200 p-4"><summary class="cursor-pointer font-bold text-slate-800 flex justify-between">
      <span>${esc(m.category)}</span><span class="px-2.5 py-0.5 rounded-lg bg-slate-200 text-slate-700 text-sm">${m.count}</span></summary>
      <p class="mt-2 text-sm text-slate-600 leading-relaxed">${m.plates.map(esc).join(' • ')}</p></details>`).join('') || '<p class="text-slate-500">Đủ số liệu</p>'}
  </div>`;
}

// ---------- 2. Giấy tờ
function xeDocsHtml() {
  const kinds = [...new Set(xeData.docs.map(d => d.kind))];
  const order = { overdue: 0, soon: 1, near: 2, missing: 3, ok: 4 };
  const rows = xeData.docs.filter(d => (!xeDocKind || d.kind === xeDocKind) && plateOk(d))
    .sort((a, b) => order[a.status] - order[b.status] || (a.days_left ?? 99999) - (b.days_left ?? 99999));
  return `<div class="flex flex-wrap gap-2 items-center mb-3">
      ${select('xeDocKind', kinds, xeDocKind, 'xeDocKind=this.value;renderXe()', 'Tất cả loại giấy')}
      ${filterBar(false, true)}
      <span class="text-sm text-slate-500">Ngưỡng từ sheet: vàng ≤ ${xeData.thresholds.yellow} ngày, đỏ ≤ ${xeData.thresholds.red} ngày. "Còn lại" do app tự tính từ ngày hạn.</span>
    </div>
    ${rlist(rows, [
      ['Tình trạng', r => chip(r.status)], ['Loại', r => esc(r.kind)], ['Xe', r => plateBtn(r.plate)],
      ['Romoóc', r => esc(r.trailer || '—')], ['Hạn', r => `<b>${dmy(r.expiry)}</b>`],
      ['Còn lại', r => r.days_left === null ? '—' : (r.days_left < 0 ? `<b class="text-red-700">quá ${-r.days_left} ngày</b>` : `${r.days_left} ngày`), 'right'],
      ['Ghi chú', r => esc(r.note)],
    ])}`;
}

// ---------- 3. Đổ dầu
function xeFuelHtml() {
  const rows = xeData.fuel.rows.filter(r => monthOk(r) && plateOk(r)).slice().reverse();
  const live = rows.filter(r => !r.cancelled);
  const sum = (k) => live.reduce((a, r) => a + (Number(r[k]) || 0), 0);
  const debt = live.filter(r => (r.payment || '').startsWith('Công nợ')).reduce((a, r) => a + (r.amount || 0), 0);
  const byPlate = Object.entries(xeData.fuel.by_plate).filter(([p]) => !xePlate || samePlate(p, xePlate))
    .sort((a, b) => (b[1].latest_l_per_100km || 0) - (a[1].latest_l_per_100km || 0));
  return `<div class="flex flex-wrap gap-2 items-center justify-between mb-3">${filterBar()}<div class="flex gap-2 items-center">${writeButtons('do-dau')}</div></div>
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
      ${stat('Số lượt đổ', num(live.length))}${stat('Tổng số lít', num(sum('liters'), 1) + ' L')}
      ${stat('Tổng tiền dầu', money(sum('amount')))}${stat('Còn nợ cây dầu', money(debt), debt ? 'text-red-600' : 'text-emerald-600')}
    </div>
    ${rlist(rows, [
      ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Cây dầu', r => esc(r.station)],
      ['Số lít', r => num(r.liters, 2), 'right'], ['Đơn giá', r => money(r.price), 'right'], ['Thành tiền', r => `<b>${money(r.amount)}</b>`, 'right'],
      ['ODO', r => num(r.odo), 'right'], ['Bình', r => esc(r.tank)], ['Thanh toán', r => esc(r.payment || '—')],
      ['Kiểm tra', r => r.flags.length ? r.flags.map(f => `<span class="inline-block mb-1 px-2 py-0.5 rounded-md bg-amber-100 text-amber-900 text-xs font-bold">${esc(f)}</span>`).join(' ') : '<span class="text-emerald-700 text-xs font-bold">OK</span>'],
      ['', r => rowActions('do-dau', r)],
    ], 'Không có lượt đổ trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '')}
    <h3 class="mt-6 mb-2 font-black text-slate-900 text-lg">Tiêu hao theo xe (giữa 2 lần đầy bình)</h3>
    ${rlist(byPlate, [
      ['Xe', r => plateBtn(r[0])], ['Số lượt', r => num(r[1].fills), 'right'],
      ['L/100km gần nhất', r => { const v = r[1].latest_l_per_100km, n = r[1].norm; return v === null ? '—' : `<b class="${fuelCls(v, n)}">${num(v, 1)}</b>`; }, 'right'],
      ['Định mức', r => num(r[1].norm, 1), 'right'],
      ['L/100km bình quân', r => num(r[1].avg_l_per_100km, 1), 'right'],
      ['ODO mới nhất', r => r[1].odo ? `${num(r[1].odo.odo)} <span class="text-xs text-slate-500">(${dmy(r[1].odo.date)})</span>` : '—', 'right'],
    ])}`;
}

// ---------- 4. Bảo dưỡng
function xeMaintHtml() {
  const m = xeData.maint;
  const kmCell = (v) => v === null || v === undefined ? '—' : (v < 0 ? `<b class="text-red-700">quá ${num(-v)} km</b>` : `${num(v)} km`);
  return `<div class="flex justify-end mb-3 gap-2 items-center">${writeButtons('bao-duong')}</div>
    <h3 class="mb-2 font-black text-slate-900 text-lg">Thay nhớt máy (định mức theo sheet, thường 15.000 km)</h3>
    <p class="text-sm text-slate-500 mb-2">KM hiện tại = số lớn hơn giữa sheet và ODO mới nhất trong sổ dầu. Sắp hạn ≤ 1.000 km, gần hạn ≤ 3.000 km.</p>
    ${rlist(m.oil.filter(plateOk), [
      ['Tình trạng', r => chip(r.status)], ['Xe', r => plateBtn(r.plate)], ['Định mức', r => num(r.norm_km), 'right'],
      ['KM thay gần nhất', r => num(r.last_km), 'right'], ['Ngày', r => dmy(r.last_date)],
      ['KM hiện tại', r => `${num(r.current_km)}${r.odo_source_date ? ` <span class="text-xs text-slate-500">(${dmy(r.odo_source_date)})</span>` : ''}`, 'right'],
      ['Còn lại', r => kmCell(r.remaining_km), 'right'], ['Ghi chú', r => esc(r.warning || r.note)],
    ])}
    <h3 class="mt-6 mb-2 font-black text-slate-900 text-lg">Nhớt hộp số (50.000 km hoặc 1 năm)</h3>
    ${rlist(m.gearbox.filter(plateOk), [
      ['Tình trạng', r => chip(r.status)], ['Xe', r => plateBtn(r.plate)], ['Ngày thay', r => dmy(r.last_date)],
      ['KM lúc thay', r => num(r.last_km), 'right'], ['Còn lại (km)', r => kmCell(r.remaining_km), 'right'],
      ['Hạn theo ngày', r => dmy(r.due_date)],
    ])}
    <h3 class="mt-6 mb-2 font-black text-slate-900 text-lg">Bôi mỡ romoóc (1 năm)</h3>
    ${rlist(m.grease.filter(plateOk), [
      ['Tình trạng', r => chip(r.status)], ['Xe', r => plateBtn(r.plate)], ['Lần gần nhất', r => dmy(r.last_date)],
      ['Hạn tiếp theo', r => dmy(r.due_date)], ['Còn lại', r => r.days_left === null ? '—' : `${r.days_left} ngày`, 'right'],
    ])}
    <h3 class="mt-6 mb-2 font-black text-slate-900 text-lg">Nhật ký bảo dưỡng – sửa chữa</h3>
    <div class="mb-2">${filterBar()}</div>
    ${rlist(m.log.filter(r => monthOk(r) && plateOk(r)).slice().reverse(), [
      ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Hạng mục', r => esc(r.item)], ['KM ODO', r => num(r.odo), 'right'],
      ['Nội dung', r => esc(r.content)], ['Gara/NCC', r => esc(r.vendor)], ['Số tiền', r => money(r.amount), 'right'],
      ['Thanh toán', r => esc(r.payment || '—')], ['', r => rowActions('bao-duong', r)],
    ], 'Không có dòng trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '')}`;
}

// ---------- 5–6. Vỏ / Bạt
function xeTiresHtml() {
  const rows = xeData.tires.filter(r => monthOk(r) && plateOk(r)).slice().reverse();
  const live = rows.filter(r => !r.cancelled);
  return `<div class="flex flex-wrap gap-2 items-center justify-between mb-3">${filterBar()}<div class="flex gap-2 items-center">${writeButtons('thay-vo')}</div></div>
    <div class="grid grid-cols-2 gap-3 mb-4">${stat('Số vỏ trong tháng', num(live.reduce((a, r) => a + (r.quantity || 0), 0)))}${stat('Tiền vỏ trong tháng', money(live.reduce((a, r) => a + (r.amount || 0), 0)))}</div>
    ${rlist(rows, [
      ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Vị trí', r => esc(r.position || '—')], ['Số lượng', r => num(r.quantity), 'right'],
      ['Loại/Hiệu', r => esc(r.brand)], ['Gara/NCC', r => esc(r.vendor)], ['Số tiền', r => money(r.amount), 'right'],
      ['Thanh toán', r => esc(r.payment || '—')], ['Ghi chú', r => esc(r.note)], ['', r => rowActions('thay-vo', r)],
    ], 'Không có dòng trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '')}`;
}

function xeTarpsHtml() {
  const rows = xeData.tarps.filter(r => monthOk(r) && plateOk(r)).slice().reverse();
  return `<div class="flex flex-wrap gap-2 items-center justify-between mb-3">${filterBar()}<div class="flex gap-2 items-center">${writeButtons('thay-bat')}</div></div>
    ${rlist(rows, [
      ['Ngày', r => dmy(r.date)], ['Xe', r => plateBtn(r.plate)], ['Nội dung', r => esc(r.content)], ['NCC', r => esc(r.vendor)],
      ['Số HĐ', r => esc(r.invoice || '—')], ['Số tiền', r => money(r.amount), 'right'], ['Thanh toán', r => esc(r.payment || '—')],
      ['Ghi chú', r => esc(r.note)], ['', r => rowActions('thay-bat', r)],
    ], 'Không có dòng trong tháng này', r => r.cancelled ? 'opacity-50 line-through' : '')}`;
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

// ---------- 9. Danh sách xe
function xeFleetHtml() {
  const fuel = xeData.fuel.by_plate;
  const docs = xeData.docs;
  const worst = p => {
    const order = ['overdue', 'soon', 'near', 'missing', 'ok'];
    const sts = docs.filter(d => samePlate(d.plate, p)).map(d => d.status);
    return order.find(s => sts.includes(s)) || 'missing';
  };
  const rows = (xeData.dm.plates || []).map(p => ({ plate: p }));
  return rlist(rows, [
    ['Xe', r => plateBtn(r.plate)], ['Giấy tờ', r => chip(worst(r.plate))],
    ['ODO mới nhất', r => { const f = Object.entries(fuel).find(([k]) => samePlate(k, r.plate)); return f && f[1].odo ? `${num(f[1].odo.odo)} (${dmy(f[1].odo.date)})` : '—'; }, 'right'],
    ['L/100km gần nhất', r => { const f = Object.entries(fuel).find(([k]) => samePlate(k, r.plate)); return f ? num(f[1].latest_l_per_100km, 1) : '—'; }, 'right'],
    ['', r => `<button onclick="openVehicleProfile('${esc(r.plate)}')" class="px-3 py-2 rounded-lg bg-blue-50 border border-blue-200 text-blue-700 font-bold text-sm">Hồ sơ xe</button>`],
  ]);
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

// ---------- Thẻ "Việc cần xử lý hôm nay" trên Tổng quan
function renderDashTodo(d) {
  const box = document.getElementById('dashTodoCard');
  if (!box || !d) return;
  const t = d.todo;
  const top = t.items.slice(0, 6);
  box.innerHTML = `
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h3 class="font-black text-slate-900 text-base md:text-lg">VIỆC CẦN XỬ LÝ HÔM NAY</h3>
      <button onclick="switchTab('xe'); switchXeSub('todo')" class="text-sm font-bold text-blue-700">Xem tất cả →</button>
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3">
      ${[['overdue', 'Quá hạn', t.counts.overdue], ['soon', 'Sắp hạn', t.counts.soon], ['near', 'Gần hạn', t.counts.near], ['missing', 'Thiếu số liệu', t.missing_count]]
        .map(([s, l, n]) => `<div class="rounded-xl p-3 ${ST[s].cls}"><p class="text-xs font-bold">${l}</p><p class="text-2xl font-black">${n}</p></div>`).join('')}
    </div>
    <div class="mt-3 space-y-1.5">${top.map(i => `
      <div class="flex flex-wrap items-center gap-2 text-[15px] p-2.5 rounded-xl bg-slate-50 border border-slate-200">
        ${chip(i.level)}<span class="font-semibold">${esc(i.category)}</span>${plateBtn(i.plate)}
        <span class="ml-auto font-bold">${esc(i.detail)}</span></div>`).join('') || '<p class="text-emerald-700 font-bold">Không có giấy tờ / bảo dưỡng quá hạn hoặc sắp hạn.</p>'}</div>
    <p class="mt-2 text-xs text-slate-500">Nguồn: Google Sheets ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM, đọc lúc ${esc(d.source.read_at)}${t.fuel_log_lag_days !== null ? ` • sổ dầu nhập đến ${dmy(t.fuel_log_last_date)} (trễ ${t.fuel_log_lag_days} ngày)` : ''}</p>`;
}
