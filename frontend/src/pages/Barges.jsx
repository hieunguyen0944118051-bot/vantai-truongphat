import React, { useState, useEffect, useCallback } from 'react'
import { bargesAPI } from '../api/client'
import Modal from '../components/Modal'
import StatusBadge from '../components/StatusBadge'
import { Plus, Pencil, Trash2, Search, Ship } from 'lucide-react'
import toast from 'react-hot-toast'

const EMPTY_FORM = {
  name: '', code: '', capacity: '', ownership_type: 'owned',
  owner_name: '', rental_price_per_day: '', status: 'active', note: '',
}

function formatVND(v) {
  if (!v && v !== 0) return '—'
  return new Intl.NumberFormat('vi-VN').format(v) + '₫'
}

export default function Barges() {
  const [barges, setBarges] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editItem, setEditItem] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const fetchBarges = useCallback(() => {
    setLoading(true)
    bargesAPI.getAll()
      .then(res => setBarges(Array.isArray(res.data) ? res.data : res.data?.items || []))
      .catch(() => toast.error('Không thể tải danh sách sà lan'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { fetchBarges() }, [fetchBarges])

  const openAdd = () => { setEditItem(null); setForm(EMPTY_FORM); setModalOpen(true) }

  const openEdit = (b) => {
    setEditItem(b)
    setForm({
      name: b.name || '',
      code: b.code || '',
      capacity: b.capacity || '',
      ownership_type: b.ownership_type || 'owned',
      owner_name: b.owner_name || '',
      rental_price_per_day: b.rental_price_per_day || '',
      status: b.status || 'active',
      note: b.note || '',
    })
    setModalOpen(true)
  }

  const handleDelete = async (id, name) => {
    if (!confirm(`Xóa sà lan ${name}?`)) return
    try {
      await bargesAPI.delete(id)
      toast.success('Đã xóa sà lan')
      fetchBarges()
    } catch {
      toast.error('Xóa thất bại')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name) { toast.error('Vui lòng nhập tên sà lan'); return }
    setSaving(true)
    try {
      if (editItem) {
        await bargesAPI.update(editItem.id, form)
        toast.success('Cập nhật sà lan thành công')
      } else {
        await bargesAPI.create(form)
        toast.success('Thêm sà lan thành công')
      }
      setModalOpen(false)
      fetchBarges()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Có lỗi xảy ra')
    } finally {
      setSaving(false)
    }
  }

  const filtered = barges.filter(b =>
    b.name?.toLowerCase().includes(search.toLowerCase()) ||
    b.code?.toLowerCase().includes(search.toLowerCase())
  )

  const inp = 'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/30 focus:border-[#1e3a5f]'
  const lbl = 'block text-xs font-medium text-gray-600 mb-1'

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Sà lan</h1>
          <p className="text-sm text-gray-400 mt-0.5">Quản lý danh sách sà lan</p>
        </div>
        <button
          onClick={openAdd}
          className="flex items-center gap-2 bg-[#1e3a5f] hover:bg-[#152a47] text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Thêm sà lan
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Tìm tên, mã sà lan..."
          className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/30"
        />
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
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Tên sà lan</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Mã số</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Tải trọng</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Loại</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Chủ sở hữu</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Giá thuê/ngày</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Trạng thái</th>
                  <th className="text-right px-4 py-3 font-semibold text-gray-600">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-12 text-gray-400">
                      <Ship className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                      Không có dữ liệu
                    </td>
                  </tr>
                ) : (
                  filtered.map((b, i) => (
                    <tr key={b.id} className={`border-b border-gray-50 hover:bg-blue-50/30 transition-colors ${i % 2 === 1 ? 'bg-gray-50/50' : ''}`}>
                      <td className="px-4 py-3 font-semibold text-[#1e3a5f]">{b.name}</td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">{b.code || '—'}</td>
                      <td className="px-4 py-3 text-gray-600">{b.capacity ? `${b.capacity} tấn` : '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                          b.ownership_type === 'owned'
                            ? 'bg-blue-100 text-blue-800 border-blue-200'
                            : 'bg-orange-100 text-orange-800 border-orange-200'
                        }`}>
                          {b.ownership_type === 'owned' ? 'Sở hữu' : 'Thuê ngoài'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-600">{b.owner_name || '—'}</td>
                      <td className="px-4 py-3 text-gray-600">
                        {b.ownership_type === 'rented' ? formatVND(b.rental_price_per_day) : '—'}
                      </td>
                      <td className="px-4 py-3"><StatusBadge status={b.status} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1">
                          <button onClick={() => openEdit(b)}
                            className="p-1.5 rounded-lg hover:bg-blue-100 text-blue-600">
                            <Pencil className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleDelete(b.id, b.name)}
                            className="p-1.5 rounded-lg hover:bg-red-100 text-red-500">
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
            Tổng: {filtered.length} sà lan
          </div>
        )}
      </div>

      {/* Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editItem ? 'Sửa thông tin sà lan' : 'Thêm sà lan mới'}
        size="md"
      >
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className={lbl}>Tên sà lan *</label>
              <input className={inp} value={form.name} onChange={e => setForm(v => ({ ...v, name: e.target.value }))} placeholder="Sà lan ABC" required />
            </div>
            <div>
              <label className={lbl}>Mã số</label>
              <input className={inp} value={form.code} onChange={e => setForm(v => ({ ...v, code: e.target.value }))} placeholder="SL-001" />
            </div>
            <div>
              <label className={lbl}>Tải trọng (tấn)</label>
              <input className={inp} type="number" step="0.1" value={form.capacity} onChange={e => setForm(v => ({ ...v, capacity: e.target.value }))} placeholder="500" />
            </div>
            <div>
              <label className={lbl}>Loại</label>
              <select className={inp} value={form.ownership_type} onChange={e => setForm(v => ({ ...v, ownership_type: e.target.value }))}>
                <option value="owned">Sở hữu</option>
                <option value="rented">Thuê ngoài</option>
              </select>
            </div>
            <div>
              <label className={lbl}>Trạng thái</label>
              <select className={inp} value={form.status} onChange={e => setForm(v => ({ ...v, status: e.target.value }))}>
                <option value="active">Hoạt động</option>
                <option value="inactive">Ngừng HĐ</option>
                <option value="maintenance">Bảo dưỡng</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className={lbl}>Chủ sở hữu</label>
              <input className={inp} value={form.owner_name} onChange={e => setForm(v => ({ ...v, owner_name: e.target.value }))} placeholder="Tên chủ sở hữu / công ty" />
            </div>
            {form.ownership_type === 'rented' && (
              <div className="col-span-2">
                <label className={lbl}>Giá thuê / ngày (₫)</label>
                <input className={inp} type="number" value={form.rental_price_per_day} onChange={e => setForm(v => ({ ...v, rental_price_per_day: e.target.value }))} placeholder="2000000" />
              </div>
            )}
            <div className="col-span-2">
              <label className={lbl}>Ghi chú</label>
              <textarea className={inp} rows={2} value={form.note} onChange={e => setForm(v => ({ ...v, note: e.target.value }))} />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-gray-300 text-sm text-gray-600 hover:bg-gray-50">
              Hủy
            </button>
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
