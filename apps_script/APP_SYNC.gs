/**
 * TRƯỜNG PHÁT – CẦU NỐI APP → GOOGLE SHEETS (GĐ2)
 *
 * Dự án Apps Script ĐỘC LẬP (tạo mới ở script.google.com), KHÔNG dán vào project đang gắn với file
 * → không đụng menu 🚛, email nhắc hạn 7–8h, việc tự lấy KM 6h đang chạy.
 *
 * Việc làm: nhận 1 yêu cầu từ app (có khóa bí mật) → ghi / sửa / hủy đúng 1 dòng trong NHẬT KÝ
 * của file "ĐỔ DẦU - BẢO DƯỠNG - ĐĂNG KIỂM - THAY VỎ - GIẤY ĐI ĐƯỜNG".
 *  - Chỉ ghi vào cột nhập liệu; KHÔNG ghi vào cột công thức (STT, Thành tiền, cột ẩn…), giữ nguyên ô chọn ▼ và định dạng.
 *  - Mỗi dòng do app ghi có MÃ APP (UUID) → bấm 2 lần không ghi trùng; chỉ dòng có mã mới được sửa / hủy.
 *  - Hủy = ghi "ĐÃ HỦY" vào GHI CHÚ + gạch ngang dòng, KHÔNG xóa.
 *  - Lần ghi đầu tiên: tự sao lưu cả file thành "BACKUP_<tên file>_<yyyy-MM-dd>".
 *  - Mọi thao tác ghi vào tab "NHẬT KÝ APP" (ai, lúc nào, làm gì, dòng nào).
 *
 * Cài đặt: xem apps_script/HUONG_DAN.md
 */

var APPSYNC_SHEET_ID = '1SzlPdtSjhBeqvFlZq5WiznFOVtF6SEvQ-5xKFF6I8Es';
var APPSYNC_LOG_TAB = 'NHẬT KÝ APP';

// Cấu hình từng nhật ký: tiền tố tên tab, các cột bắt buộc để nhận dòng tiêu đề, cột khóa (để tìm dòng cuối),
// cột MÃ APP (cột trống bên phải bảng), cột được phép ghi, cột GHI CHÚ, cột ngày.
var APPSYNC_TABS = {
  dodau: {
    prefix: 'DO DAU', required: ['NGAY DO', 'SO XE', 'CAY DAU', 'SO LIT'], keyHeader: 'SO XE', uuidCol: 'R',
    writable: ['NGAY DO', 'SO XE', 'CAY DAU', 'SO LIT', 'DON GIA', 'KM LUC DO', 'TINH TRANG BINH',
               'SO HOA DON', 'THANH TOAN', 'NGAY THANH TOAN', 'GHI CHU'],
    dateHeaders: ['NGAY DO', 'NGAY THANH TOAN'], noteHeader: 'GHI CHU'
  },
  baoduong: {
    prefix: 'BAO DUONG', required: ['NGAY', 'BIEN SO', 'HANG MUC', 'KM ODO'], keyHeader: 'BIEN SO', uuidCol: 'M',
    writable: ['NGAY', 'BIEN SO', 'HANG MUC', 'KM ODO', 'NOI DUNG', 'GARA / NCC', 'SO HD', 'SO TIEN', 'THANH TOAN', 'GHI CHU'],
    dateHeaders: ['NGAY'], noteHeader: 'GHI CHU'
  },
  vo: {
    prefix: 'THAY VO', required: ['NGAY', 'BIEN SO', 'VI TRI', 'SO LUONG'], keyHeader: 'BIEN SO', uuidCol: 'L',
    writable: ['NGAY', 'BIEN SO', 'VI TRI', 'SO LUONG', 'LOAI / HIEU', 'GARA / NCC', 'SO HD', 'SO TIEN', 'THANH TOAN', 'GHI CHU'],
    dateHeaders: ['NGAY'], noteHeader: 'GHI CHU'
  },
  bat: {
    prefix: 'THAY BAT', required: ['NGAY', 'BIEN SO', 'NOI DUNG', 'NCC'], keyHeader: 'BIEN SO', uuidCol: 'J',
    writable: ['NGAY', 'BIEN SO', 'NOI DUNG', 'NCC', 'SO HD', 'SO TIEN', 'THANH TOAN', 'GHI CHU'],
    dateHeaders: ['NGAY'], noteHeader: 'GHI CHU'
  }
};

// ---------------------------------------------------------------- vào / ra

function doPost(e) {
  var lock = LockService.getScriptLock();
  try {
    var req = JSON.parse(e.postData.contents || '{}');
    var key = PropertiesService.getScriptProperties().getProperty('APP_SYNC_KEY');
    if (!key || req.key !== key) return APPSYNC_out({ ok: false, error: 'Sai khóa bí mật' });
    if (!lock.tryLock(20000)) return APPSYNC_out({ ok: false, error: 'Sheet đang bận, thử lại sau' });

    var ss = SpreadsheetApp.openById(APPSYNC_SHEET_ID);
    if (req.action === 'ping') return APPSYNC_out({ ok: true, file: ss.getName() });
    APPSYNC_backupOnce(ss);

    var result;
    if (req.action === 'append') result = APPSYNC_append(ss, req);
    else if (req.action === 'update') result = APPSYNC_update(ss, req);
    else if (req.action === 'cancel') result = APPSYNC_cancel(ss, req);
    else if (req.action === 'mark_paid') result = APPSYNC_markPaid(ss, req);
    else return APPSYNC_out({ ok: false, error: 'Thao tác không hỗ trợ: ' + req.action });

    APPSYNC_log(ss, req, result);
    return APPSYNC_out(result);
  } catch (err) {
    return APPSYNC_out({ ok: false, error: String(err && err.message || err) });
  } finally {
    try { lock.releaseLock(); } catch (x) {}
  }
}

function APPSYNC_out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// ---------------------------------------------------------------- thao tác

function APPSYNC_append(ss, req) {
  var t = APPSYNC_table(ss, req.tab);
  if (!req.uuid) throw new Error('Thiếu mã bản ghi (uuid)');
  var existing = APPSYNC_findUuid(t, req.uuid);
  if (existing) return { ok: true, row: existing, duplicate: true, message: 'Đã có dòng này (bấm 2 lần) — không ghi thêm' };

  var row = APPSYNC_lastDataRow(t) + 1;
  APPSYNC_writeValues(t, row, req.values || {});
  t.sheet.getRange(t.uuidCol + row).setValue(req.uuid).setFontColor('#9aa0a6').setFontSize(8);
  return { ok: true, row: row, message: 'Đã ghi dòng ' + row + ' tab ' + t.sheet.getName() };
}

function APPSYNC_update(ss, req) {
  var t = APPSYNC_table(ss, req.tab);
  var row = APPSYNC_findUuid(t, req.uuid);
  if (!row) throw new Error('Không tìm thấy dòng có mã ' + req.uuid + ' (chỉ sửa được dòng do app ghi)');
  var note = APPSYNC_get(t, row, t.cfg.noteHeader);
  if (APPSYNC_norm(note).indexOf('DA HUY') >= 0) throw new Error('Dòng đã hủy, không sửa được');
  APPSYNC_writeValues(t, row, req.values || {});
  return { ok: true, row: row, message: 'Đã sửa dòng ' + row };
}

function APPSYNC_cancel(ss, req) {
  var t = APPSYNC_table(ss, req.tab);
  var row = APPSYNC_findUuid(t, req.uuid);
  if (!row) throw new Error('Không tìm thấy dòng có mã ' + req.uuid + ' (chỉ hủy được dòng do app ghi)');
  var noteCol = t.cols[t.cfg.noteHeader];
  var old = t.sheet.getRange(row, noteCol).getValue();
  if (APPSYNC_norm(old).indexOf('DA HUY') >= 0) return { ok: true, row: row, message: 'Dòng đã hủy từ trước' };
  var stamp = 'ĐÃ HỦY (' + Utilities.formatDate(new Date(), 'Asia/Ho_Chi_Minh', 'dd/MM/yyyy HH:mm') + ', ' +
              (req.user || 'app') + (req.reason ? ': ' + req.reason : '') + ')';
  t.sheet.getRange(row, noteCol).setValue(old ? stamp + ' — ' + old : stamp);
  var firstCol = Math.min.apply(null, Object.keys(t.cols).map(function (k) { return t.cols[k]; }));
  t.sheet.getRange(row, firstCol, 1, noteCol - firstCol + 1).setFontLine('line-through');
  return { ok: true, row: row, message: 'Đã hủy dòng ' + row + ' (không xóa)' };
}

/** Đánh dấu đã thanh toán. items: [{tab, sheet_row, uuid, plate, date, amount}] — kiểm tra khớp dòng trước khi ghi. */
function APPSYNC_markPaid(ss, req) {
  var done = [], skipped = [];
  (req.items || []).forEach(function (it) {
    var t = APPSYNC_table(ss, it.tab);
    var row = it.uuid ? APPSYNC_findUuid(t, it.uuid) : Number(it.sheet_row);
    if (!row || row <= t.headerRow) { skipped.push({ item: it, reason: 'Không tìm thấy dòng' }); return; }
    var plate = APPSYNC_norm(APPSYNC_get(t, row, t.cfg.keyHeader)).replace(/[^A-Z0-9]/g, '');
    if (plate !== APPSYNC_norm(it.plate).replace(/[^A-Z0-9]/g, '')) {
      skipped.push({ item: it, reason: 'Dòng ' + row + ' đã thay đổi (biển số khác) — tải lại app' }); return;
    }
    var payCol = t.cols['THANH TOAN'];
    if (it.tab === 'dodau') {
      t.sheet.getRange(row, payCol).setValue(req.method === 'cash' ? 'Đã TT - Tiền mặt' : 'Đã TT - Chuyển khoản');
      if (t.cols['NGAY THANH TOAN']) t.sheet.getRange(row, t.cols['NGAY THANH TOAN']).setValue(APPSYNC_date(req.date) || new Date());
    } else {
      t.sheet.getRange(row, payCol).setValue('Đã thanh toán');
    }
    done.push(row);
  });
  return { ok: true, rows: done, skipped: skipped, message: 'Đã đánh dấu ' + done.length + ' dòng đã thanh toán' };
}

// ---------------------------------------------------------------- bảng

function APPSYNC_table(ss, tabKey) {
  var cfg = APPSYNC_TABS[tabKey];
  if (!cfg) throw new Error('Không biết nhật ký: ' + tabKey);
  var sheet = ss.getSheets().filter(function (s) {
    var n = APPSYNC_norm(s.getName());
    return n.indexOf(cfg.prefix) === 0 && n.indexOf('LUU TRU') !== 0;
  })[0];
  if (!sheet) throw new Error('Không thấy tab bắt đầu bằng "' + cfg.prefix + '"');
  var values = sheet.getRange(1, 1, Math.min(sheet.getMaxRows(), 400), sheet.getMaxColumns()).getValues();
  for (var r = 0; r < values.length; r++) {
    var cols = {};
    values[r].forEach(function (v, c) { if (v !== '' && v !== null) cols[APPSYNC_norm(v)] = c + 1; });
    var ok = cfg.required.every(function (h) {
      return Object.keys(cols).some(function (k) { return k === h || k.indexOf(h) === 0; });
    });
    if (ok) {
      var full = {};
      Object.keys(cols).forEach(function (k) {
        cfg.writable.concat([cfg.keyHeader]).forEach(function (h) { if (k === h || k.indexOf(h) === 0) full[h] = full[h] || cols[k]; });
      });
      var t = { sheet: sheet, cfg: cfg, headerRow: r + 1, cols: full, uuidCol: cfg.uuidCol };
      var need = APPSYNC_colIndex(cfg.uuidCol);
      if (sheet.getMaxColumns() < need) sheet.insertColumnsAfter(sheet.getMaxColumns(), need - sheet.getMaxColumns());
      var head = sheet.getRange(cfg.uuidCol + (r + 1));
      if (APPSYNC_norm(head.getValue()) !== 'MA APP') {
        if (head.getValue() !== '') throw new Error('Cột ' + cfg.uuidCol + ' đã có dữ liệu, không dùng làm MÃ APP được');
        head.setValue('MÃ APP').setFontColor('#9aa0a6').setFontSize(8);
      }
      return t;
    }
  }
  throw new Error('Không thấy dòng tiêu đề trong tab ' + sheet.getName());
}

function APPSYNC_lastDataRow(t) {
  var keyCol = t.cols[t.cfg.keyHeader];
  var n = t.sheet.getLastRow();
  if (n <= t.headerRow) return t.headerRow;
  var vals = t.sheet.getRange(t.headerRow + 1, keyCol, n - t.headerRow, 1).getValues();
  for (var i = vals.length - 1; i >= 0; i--) if (String(vals[i][0]).trim() !== '') return t.headerRow + 1 + i;
  return t.headerRow;
}

function APPSYNC_findUuid(t, uuid) {
  var n = t.sheet.getLastRow();
  if (n <= t.headerRow) return null;
  var vals = t.sheet.getRange(t.uuidCol + (t.headerRow + 1) + ':' + t.uuidCol + n).getValues();
  for (var i = 0; i < vals.length; i++) if (String(vals[i][0]) === String(uuid)) return t.headerRow + 1 + i;
  return null;
}

function APPSYNC_writeValues(t, row, values) {
  Object.keys(values).forEach(function (rawKey) {
    var key = APPSYNC_norm(rawKey);
    if (t.cfg.writable.indexOf(key) < 0) throw new Error('Không được ghi cột ' + rawKey);
    var col = t.cols[key];
    if (!col) throw new Error('Không thấy cột ' + rawKey + ' trong tab ' + t.sheet.getName());
    var v = values[rawKey];
    if (t.cfg.dateHeaders.indexOf(key) >= 0) v = APPSYNC_date(v) || '';
    t.sheet.getRange(row, col).setValue(v === null || v === undefined ? '' : v);
  });
}

function APPSYNC_get(t, row, header) {
  var c = t.cols[header];
  return c ? t.sheet.getRange(row, c).getValue() : '';
}

// ---------------------------------------------------------------- sao lưu + nhật ký

function APPSYNC_backupOnce(ss) {
  var props = PropertiesService.getScriptProperties();
  if (props.getProperty('APP_SYNC_BACKUP_DONE')) return;
  var file = DriveApp.getFileById(ss.getId());
  var parents = file.getParents();
  var name = 'BACKUP_' + ss.getName() + '_' + Utilities.formatDate(new Date(), 'Asia/Ho_Chi_Minh', 'yyyy-MM-dd');
  var copy = parents.hasNext() ? file.makeCopy(name, parents.next()) : file.makeCopy(name);
  props.setProperty('APP_SYNC_BACKUP_DONE', copy.getId());
}

function APPSYNC_log(ss, req, result) {
  var sh = ss.getSheetByName(APPSYNC_LOG_TAB);
  if (!sh) {
    sh = ss.insertSheet(APPSYNC_LOG_TAB);
    sh.appendRow(['THỜI GIAN', 'NGƯỜI DÙNG', 'THAO TÁC', 'NHẬT KÝ', 'DÒNG', 'MÃ APP', 'NỘI DUNG', 'KẾT QUẢ']);
    sh.getRange('A1:H1').setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  sh.appendRow([
    new Date(), req.user || '', req.action, req.tab || (req.items || []).map(function (i) { return i.tab; }).join(','),
    result.row || (result.rows || []).join(','), req.uuid || '', JSON.stringify(req.values || req.items || {}).slice(0, 1000),
    result.message || ''
  ]);
}

// ---------------------------------------------------------------- tiện ích

function APPSYNC_colIndex(letters) {
  var n = 0;
  String(letters).toUpperCase().split('').forEach(function (ch) { n = n * 26 + (ch.charCodeAt(0) - 64); });
  return n;
}

function APPSYNC_norm(s) {
  return String(s === null || s === undefined ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/Đ/g, 'D').replace(/đ/g, 'd').replace(/\s+/g, ' ').trim().toUpperCase();
}

/** '2026-10-21' hoặc '21/10/2026' -> Date (giờ VN, 0h). */
function APPSYNC_date(v) {
  if (!v) return null;
  if (v instanceof Date) return v;
  var m = String(v).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  m = String(v).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
  return null;
}

/** Chạy tay 1 lần trong trình soạn thảo để cấp quyền + tạo khóa bí mật. Khóa in ở Nhật ký thực thi. */
function APPSYNC_setup() {
  var props = PropertiesService.getScriptProperties();
  var key = props.getProperty('APP_SYNC_KEY');
  if (!key) {
    key = Utilities.getUuid() + Utilities.getUuid().replace(/-/g, '');
    props.setProperty('APP_SYNC_KEY', key);
  }
  var ss = SpreadsheetApp.openById(APPSYNC_SHEET_ID);
  Logger.log('Mở được file: ' + ss.getName());
  Logger.log('APP_SYNC_KEY (dán vào Render): ' + key);
}
