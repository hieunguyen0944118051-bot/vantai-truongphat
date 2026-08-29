import React, { useState, useEffect, useCallback } from 'react'
import { vehiclesAPI } from '../api/client'
import Modal from '../components/Modal'
import StatusBadge from '../components/StatusBadge'
import { ExpiryBadge } from '../components/ExpiryAlert'
import { Plus, Pencil, Trash2, Search, Filter } from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO } from 'date-fns'

const EMPTY_FORM = {
  plate_number: '', vehicle_type: '', brand: '', model: '', year: '',
  capacity: '', status: 'active', registration_expiry: '', insurance_expiry: '',
  badge_expiry: '', note: '',
}

function formatDate(d) {
  if (!d) return '—'
  try { return format(parseISO(d), 'dd/MM/yyyy') } catch { return d }
}

export default function Vehicles() {
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editItem, setEditItem] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const fetchVehicles = useCallback(() => {
    setLoading(true)
    vehiclesAPI.getAll({ status: filterStatus || undefined })
      .then(res => setVehicles(Array.isArray(res.data) ? res.data : res.data?.items || []))
      .catch(() => toast.error('Không thể tải danh sách xe'))
      .finally(() => setLoading(false))
  }, [filterStatus])

  useEffect(() => { fetchVehicles() }, [fetchVehicles])

  const openAdd = () => {
    setEditItem(null)
    setForm(EMPTY_FORM)
    setModalOpen(true)
  }

  const openEdit = (v) => {
    setEditItem(v)
    setForm({
      plate_number: v.plate_number || '',
      vehicle_type: v.vehicle_type || '',
      brand: v.brand || '',
      model: v.model || '',
      year: v.year || '',
      capacity: v.capacity || '',
      status: v.status || 'active',
      registration_expiry: v.registration_expiry?.slice(0, 10) || '',
      insurance_expiry: v.insurance_expiry?.slice(0, 10) || '',
      badge_expiry: v.badge_expiry?.slice(0, 10) || '',
      note: v.note || '',
    })
    setModalOpen(true)
  }

  const handleDelete = async (id, plate) => {
    if (!confirm(`Xóa xe ${plate}?`)) return
    try {
      await vehiclesAPI.delete(id)
      toast.success('Đã xóa xe')
      fetchVehicles()
    } catch {
      toast.error('Xóa thất bại')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.plate_number) { toast.error('Vui lòng nhập biển số xe'); return }
    setSaving(true)
    try {
      if (editItem) {
        await vehiclesAPI.update(editItem.id, form)
        toast.success('Cập nhật xe thành công')
      } else {
        await vehiclesAPI.create(form)
        toast.success('Thêm xe thành công')
      }
      setModalOpen(false)
      fetchVehicles()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Có lỗi xảy ra')
    } finally {
      setSaving(false)
    }
  }

  const filtered = vehicles.filter(v =>
    v.plate_number?.toLowerCase().includes(search.toLowerCase()) ||
    v.brand?.toLowerCase().includes(search.toLowerCase())
  )

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/30 focus:border-[#1e3a5f]'
  const lbl = 'block text-xs font-medium text-gray-600 mb-1'

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Xe đầu kéo</h1>
          <p className="text-sm text-gray-400 mt-0.5">Quản lý danh sách xe đầu kéo</p>
        </div>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 bg-[#1e3a5f] hover:bg-[#152a47] text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Thêm xe
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Tìm biển số, hãng xe..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/30 focus:border-[#1e3a5f]"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            className="border border-gray-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/30"
          >
            <option value="">Tất cả trạng thái</option>
            <option value="active">Hoạt động</option>
            <option value="inactive">Ngừng HĐ</option>
            <option value="maintenance">Bảo dưỡng</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="w-8 h-8 border-3 border-[#1e3a5f] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Biển số</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Loại xe</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Hãng / Model</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Tải trọng</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Trạng thái</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Đăng kiểm</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Bảo hiểm</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Phù hiệu</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-12 text-gray-400">
                      Không có dữ liệu
                    </td>
                  </tr>
                ) : (
                  filtered.map((v, i) => (
                    <tr key={v.id} className={`border-b border-gray-50 hover:bg-blue-50/30 transition-colors ${i % 2 === 1 ? 'bg-gray-50/50' : ''}`}>
                      <td className="px-4 py-3 font-semibold text-[#1e3a5f]">{v.plate_number}</td>
                      <td className="px-4 py-3 text-gray-600">{v.vehicle_type || '—'}</td>
                      <td className="px-4 py-3 text-gray-600">{[v.brand, v.model].filter(Boolean).join(' ') || '—'}</td>
                      <td className="px-4 py-3 text-gray-600">{v.capacity ? `${v.capacity} tấn` : '—'}</td>
                      <td className="px-4 py-3"><StatusBadge status={v.status} /></td>
                      <td className="px-4 py-3">
                        <div className="space-y-0.5">
                          <div className="text-gray-600">{formatDate(v.registration_expiry)}</div>
                          <ExpiryBadge date={v.registration_expiry} label="ĐK" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="space-y-0.5">
                          <div className="text-gray-600">{formatDate(v.insurance_expiry)}</div>
                          <ExpiryBadge date={v.insurance_expiry} label="BH" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="space-y-0.5">
                          <div className="text-gray-600">{formatDate(v.badge_expiry)}</div>
                          <ExpiryBadge date={v.badge_expiry} label="PH" />
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => openEdit(v)}
                            className="p-1.5 rounded-lg hover:bg-blue-100 text-blue-600 transition-colors"
                            title="Sửa"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(v.id, v.plate_number)}
                            className="p-1.5 rounded-lg hover:bg-red-100 text-red-500 transition-colors"
                            title="Xóa"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        {!loading && (
          <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-400">
            Tổng: {filtered.length} xe
          </div>
        )}
      </div>

      {/* Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editItem ? 'Sửa thông tin xe' : 'Thêm xe mới'}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 sm:col-span-1">
              <label className={lbl}>Biển số xe *</label>
              <input className={inp} value={form.plate_number} onChange={e => setForm(v => ({ ...v, plate_number: e.target.value }))} placeholder="51C-123.45" required />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <label className={lbl}>Loại xe</label>
              <input className={inp} value={form.vehicle_type} onChange={e => setForm(v => ({ ...v, vehicle_type: e.target.value }))} placeholder="Đầu kéo / Xe tải..." />
            </div>
            <div>
              <label className={lbl}>Hãng xe</label>
              <input className={inp} value={form.brand} onChange={e => setForm(v => ({ ...v, brand: e.target.value }))} placeholder="Hino, Isuzu, Volvo..." />
            </div>
            <div>
              <label className={lbl}>Model</label>
              <input className={inp} value={form.model} onChange={e => setForm(v => ({ ...v, model: e.target.value }))} placeholder="Model xe" />
            </div>
            <div>
              <label className={lbl}>Năm sản xuất</label>
              <input className={inp} type="number" value={form.year} onChange={e => setForm(v => ({ ...v, year: e.target.value }))} placeholder="2020" />
            </div>
            <div>
              <label className={lbl}>Tải trọng (tấn)</label>
              <input className={inp} type="number" step="0.1" value={form.capacity} onChange={e => setForm(v => ({ ...v, capacity: e.target.value }))} placeholder="20" />
            </div>
            <div className="col-span-2">
              <label className={lbl}>Trạng thái</label>
              <select className={inp} value={form.status} onChange={e => setForm(v => ({ ...v, status: e.target.value }))}>
                <option value="active">Hoạt động</option>
                <option value="inactive">Ngừng hoạt động</option>
                <option value="maintenance">Bảo dưỡng</option>
              </select>
            </div>
            <div>
              <label className={lbl}>Hạn đăng kiểm</label>
              <input className={inp} type="date" value={form.registration_expiry} onChange={e => setForm(v => ({ ...v, registration_expiry: e.target.value }))} />
            </div>
            <div>
              <label className={lbl}>Hạn bảo hiểm</label>
              <input className={inp} type="date" value={form.insurance_expiry} onChange={e => setForm(v => ({ ...v, insurance_expiry: e.target.value }))} />
            </div>
            <div>
              <label className={lbl}>Hạn phù hiệu</label>
              <input className={inp} type="date" value={form.badge_expiry} onChange={e => setForm(v => ({ ...v, badge_expiry: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className={lbl}>Ghi chú</label>
              <textarea className={inp} rows={2} value={form.note} onChange={e => setForm(v => ({ ...v, note: e.target.value }))} placeholder="Ghi chú thêm..." />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-gray-300 text-sm text-gray-600 hover:bg-gray-50 transition-colors">
              Hủy
            </button>
            <button type="submit" disabled={saving}
              className="px-6 py-2 rounded-xl bg-[#1e3a5f] text-white text-sm font-medium hover:bg-[#152a47] transition-colors disabled:opacity-60">
              {saving ? 'Đang lưu...' : (editItem ? 'Cập nhật' : 'Thêm xe')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
