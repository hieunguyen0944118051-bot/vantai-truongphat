import React from 'react'

const statusConfig = {
  // Vehicle / Barge statuses
  active: { label: 'Hoạt động', className: 'bg-green-100 text-green-800 border-green-200' },
  inactive: { label: 'Ngừng HĐ', className: 'bg-gray-100 text-gray-600 border-gray-200' },
  maintenance: { label: 'Bảo dưỡng', className: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
  // Driver statuses
  available: { label: 'Sẵn sàng', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  on_trip: { label: 'Đang chạy', className: 'bg-purple-100 text-purple-800 border-purple-200' },
  // Trip payment
  paid: { label: 'Đã thanh toán', className: 'bg-green-100 text-green-800 border-green-200' },
  unpaid: { label: 'Chưa TT', className: 'bg-red-100 text-red-800 border-red-200' },
  partial: { label: 'TT một phần', className: 'bg-orange-100 text-orange-800 border-orange-200' },
  // Barge ownership
  owned: { label: 'Sở hữu', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  rented: { label: 'Thuê ngoài', className: 'bg-orange-100 text-orange-800 border-orange-200' },
}

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || {
    label: status,
    className: 'bg-gray-100 text-gray-600 border-gray-200',
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.className}`}>
      {config.label}
    </span>
  )
}
