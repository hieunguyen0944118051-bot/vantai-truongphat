import React from 'react'
import { differenceInDays, parseISO } from 'date-fns'
import { AlertTriangle, AlertCircle } from 'lucide-react'

export function ExpiryBadge({ date, label }) {
  if (!date) return null

  let days
  try {
    days = differenceInDays(parseISO(date), new Date())
  } catch {
    return null
  }

  if (days > 30) return null

  const isExpired = days < 0
  const isWarning = days >= 0 && days <= 30

  return (
    <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
      isExpired
        ? 'bg-red-100 text-red-700'
        : 'bg-yellow-100 text-yellow-700'
    }`}>
      {isExpired ? (
        <AlertCircle className="w-3 h-3" />
      ) : (
        <AlertTriangle className="w-3 h-3" />
      )}
      {label}: {isExpired ? `Hết hạn ${Math.abs(days)} ngày` : `Còn ${days} ngày`}
    </div>
  )
}

export default function ExpiryAlert({ items }) {
  if (!items || items.length === 0) return null

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-amber-600" />
        <h3 className="font-semibold text-amber-800">Cảnh báo giấy tờ sắp hết hạn</h3>
      </div>
      <ul className="space-y-1">
        {items.map((item, idx) => (
          <li key={idx} className="text-sm text-amber-700">
            • {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
