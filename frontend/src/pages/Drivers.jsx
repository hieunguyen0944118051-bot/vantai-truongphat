import React, { useState, useEffect, useCallback } from 'react'
import { driversAPI, vehiclesAPI } from '../api/client'
import Modal from '../components/Modal'
import StatusBadge from '../components/StatusBadge'
import { ExpiryBadge } from '../components/ExpiryAlert'
import { Plus, Pencil, Trash2, Search, Users } from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO } from 'date-fns'

const EMPTY_FORM = {
  full_name: '', phone: '', id_number: '', license_number: '',
  license_expiry: '', assigned_vehicle_id: '', status: 'available', note: '',
}

function formatDate(d) {
  if (!d) return '—'
  try { return format(parseISO(d), 'dd/MM/yyyy') } catch { return d }
}

export default function Drivers() {
  const [drivers, setDrivers] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editItem, setEditItem] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const fetchData = useCallback(() => {
    setLoading(true)
    Promise.all([
      driversAPI.getAll({ status: filterStatus || undefined }),
      vehiclesAPI.getAll({ status: 'active' }),
    ])
      .then(([drRes, vehRes]) => {
        setDrivers(Array.isArray(drRes.data) ? drRes.data : drRes.data?.items || [])
        setVehicles(Array.isArray(vehRes.data) ? vehRes.data : vehRes.data?.items || [])
      })
      .catch(() => toast.error('Không thể tải dữ liệu'))
      .finally(() => setLoading(false))
  }, [filterStatus])

  useEffect(() => { fetchData() }, [fetchData])

  const openAdd = () => { setEditItem(null); setForm(EMPTY_FORM); setModalOpen(true) }

  const openEdit = (d) => {
    setEditItem(d)
    setForm({
      full_name: d.full_name || '',
      phone: d.phone || '',
      id_number: d.id_number || '',
      license_number: d.license_number || '',
      license_expiry: d.license_expiry?.slice(0, 10) || '',
      assigned_vehicle_id: d.assigned_vehicle_id || '',
      status: d.status || 'available',
      note: d.note || '',
    })
    setModalOpen(true)
  }

  const handleDelete = async (id, name) => {
    if (!confirm(`Xóa tài xế ${name}?`)) return
    try {
      await driversAPI.delete(id)
      toast.success('Đã xóa tài xế')
      fetchData()
    } catch { toast.error('Xóa thất bại') }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.full_name) { toast.error('Vui lòng nhập họ tên'); return }
    setSaving(true)
    try {
      if (editItem) {
        await driversAPI.update(editItem.id, form)
        toast.success('Cập nhật thành công')
      } else {
        await driversAPI.create(form)
        toast.success('Thêm tài xế thành công')
      }
      setModalOpen(false)
      fetchData()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Có lỗi xảy ra')
    } finally {
      setSaving(false)
    }
  }

  const filtered = drivers.filter(d =>
    d.full_name?.toLowerCase().includes(search.toLowerCase()) ||
    d.phone?.includes(search) ||
    d.license_number?.toLowerCase().includes(search.toLowerCase())
  )

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/30 focus:border-[#1e3a5f]'
  const lbl = 'block text-xs font-medium text-gray-600 mb-1'

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Tài xế</h1>
          <p className="text-sm text-gray-400 mt-0.5">Quản lý danh sách tài xế</p>
        </div>
        <button onClick={openAdd}
          className="flex items-center gap-2 bg-[#1e3a5f] hover:bg-[#152a47] text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm">
          <Plus className="w-4 h-4" />
          Thêm tài xế
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Tìm tên, số điện thoại, bằng lái..."
            className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/30" />
        </div>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          className="border border-gray-300 rounded-xl px-3 py-2 text-sm focus:outline-none">
          <option value="">Tất cả trạng thái</option>
          <option value="available">Sẵn sàng</option>
          <option value="on_trip">Đang chạy</option>
          <option value="inactive">Ngừng HĐ</option>
        </select>
      </div>

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
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Họ tên</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Điện thoại</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">CCCD</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Bằng lái</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Hạn bằng lái</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Xe phân công</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Trạng thái</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-gray-400">
                      <Users className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                      Không có dữ liệu
                    </td>
                  </tr>
                ) : (
                  filtered.map((d, i) => {
                    const vehicle = vehicles.find(v => v.id === d.assigned_vehicle_id)
                    return (
                      <tr key={d.id} className={`border-b border-gray-50 hover:bg-blue-50/30 transition-colors ${i % 2 === 1 ? 'bg-gray-50/50' : ''}`}>
                        <td className="px-4 py-3 font-semibold text-gray-800">{d.full_name}</td>
                        <td className="px-4 py-3 text-gray-600">{d.phone || '—'}</td>
                        <td className="px-4 py-3 text-gray-600 font-mono text-xs">{d.id_number || '—'}</td>
                        <td className="px-4 py-3 text-gray-600">{d.license_number || '—'}</td>
                        <td className="px-4 py-3">
                          <div className="space-y-0.5">
                            <div className="text-gray-600">{formatDate(d.license_expiry)}</div>
                            <ExpiryBadge date={d.license_expiry} label="BL" />
                          </div>
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {vehicle ? (
                            <span className="text-[#1e3a5f] font-medium">{vehicle.plate_number}</span>
                          ) : '—'}
                        </td>
                        <td className="px-4 py-3"><StatusBadge status={d.status} /></td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end gap-1">
                            <button onClick={() => openEdit(d)}
                              className="p-1.5 rounded-lg hover:bg-blue-100 text-blue-600">
                              <Pencil className="w-4 h-4" />
                            </button>
                            <button onClick={() => handleDelete(d.id, d.full_name)}
                              className="p-1.5 rounded-lg hover:bg-red-100 text-red-500">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
        {!loading && (
          <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-400">
            Tổng: {filtered.length} tài xế
          </div>
        )}
      </div>

      {/* Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)}
        title={editItem ? 'Sửa thông tin tài xế' : 'Thêm tài xế mới'}
        size="md">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className={lbl}>Họ và tên *</label>
              <input className={inp} value={form.full_name} onChange={e => setForm(v => ({ ...v, full_name: e.target.value }))} placeholder="Nguyễn Văn A" required />
            </div>
            <div>
              <label className={lbl}>Số điện thoại</label>
              <input className={inp} value={form.phone} onChange={e => setForm(v => ({ ...v, phone: e.target.value }))} placeholder="0901234567" />
            </div>
            <div>
              <label className={lbl}>CCCD / CMND</label>
              <input className={inp} value={form.id_number} onChange={e => setForm(v => ({ ...v, id_number: e.target.value }))} placeholder="012345678901" />
            </div>
            <div>
              <label className={lbl}>Số bằng lái</label>
              <input className={inp} value={form.license_number} onChange={e => setForm(v => ({ ...v, license_number: e.target.value }))} placeholder="BL-123456" />
            </div>
            <div>
              <label className={lbl}>Hạn bằng lái</label>
              <input className={inp} type="date" value={form.license_expiry} onChange={e => setForm(v => ({ ...v, license_expiry: e.target.value }))} />
            </div>
            <div>
              <label className={lbl}>Xe phân công</label>
              <select className={inp} value={form.assigned_vehicle_id} onChange={e => setForm(v => ({ ...v, assigned_vehicle_id: e.target.value }))}>
                <option value="">— Chưa phân công —</option>
                {vehicles.map(v => (
                  <option key={v.id} value={v.id}>{v.plate_number}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={lbl}>Trạng thái</label>
              <select className={inp} value={form.status} onChange={e => setForm(v => ({ ...v, status: e.target.value }))}>
                <option value="available">Sẵn sàng</option>
                <option value="on_trip">Đang chạy</option>
                <option value="inactive">Ngừng HĐ</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className={lbl}>Ghi chú</label>
              <textarea className={inp} rows={2} value={form.note} onChange={e => setForm(v => ({ ...v, note: e.target.value }))} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-gray-300 text-sm text-gray-600 hover:bg-gray-50">Hủy</button>
            <button type="submit" disabled={saving}
              className="px-6 py-2 rounded-xl bg-[#1e3a5f] text-white text-sm font-medium hover:bg-[#152a47] disabled:opacity-60">
              {saving ? 'Đang lưu...' : (editItem ? 'Cập nhật' : 'Thêm')}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
