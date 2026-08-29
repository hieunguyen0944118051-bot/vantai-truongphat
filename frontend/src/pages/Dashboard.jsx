import React, { useState, useEffect } from 'react'
import { dashboardAPI } from '../api/client'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'
import { Truck, Ship, ClipboardList, TrendingUp, AlertTriangle } from 'lucide-react'
import { format } from 'date-fns'
import { vi } from 'date-fns/locale'

function formatVND(amount) {
  if (!amount && amount !== 0) return '—'
  return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount)
}

function StatCard({ title, value, icon: Icon, color, sub }) {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div className="min-w-0">
        <p className="text-sm text-gray-500 truncate">{title}</p>
        <p className="text-2xl font-bold text-gray-800">{value ?? '—'}</p>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-lg">
        <p className="text-sm font-medium text-gray-700 mb-1">{label}</p>
        <p className="text-sm text-[#1e3a5f] font-bold">
          {formatVND(payload[0].value)}
        </p>
      </div>
    )
  }
  return null
}

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    dashboardAPI.getStats()
      .then(res => setStats(res.data))
      .catch(() => {
        // Use mock data if API not available
        setStats({
          total_vehicles: 12,
          total_barges: 5,
          trips_today: 8,
          revenue_this_month: 325000000,
          alerts: [
            'Xe 51C-123.45 - Đăng kiểm hết hạn sau 5 ngày',
            'Xe 79C-456.78 - Bảo hiểm hết hạn sau 12 ngày',
            'Tài xế Nguyễn Văn A - Bằng lái hết hạn sau 20 ngày',
          ],
          monthly_revenue: [
            { month: 'T3', revenue: 280000000 },
            { month: 'T4', revenue: 310000000 },
            { month: 'T5', revenue: 295000000 },
            { month: 'T6', revenue: 340000000 },
            { month: 'T7', revenue: 315000000 },
            { month: 'T8', revenue: 325000000 },
          ],
        })
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-10 h-10 border-4 border-[#1e3a5f] border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">
          {format(new Date(), "EEEE, dd/MM/yyyy", { locale: vi })}
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          title="Xe đầu kéo hoạt động"
          value={stats?.total_vehicles}
          icon={Truck}
          color="bg-[#1e3a5f]"
          sub="Xe đang hoạt động"
        />
        <StatCard
          title="Sà lan hoạt động"
          value={stats?.total_barges}
          icon={Ship}
          color="bg-blue-500"
          sub="Sà lan đang hoạt động"
        />
        <StatCard
          title="Chuyến hôm nay"
          value={stats?.trips_today}
          icon={ClipboardList}
          color="bg-purple-500"
          sub="Chuyến đã lên bảng kê"
        />
        <StatCard
          title="Doanh thu tháng này"
          value={formatVND(stats?.revenue_this_month)}
          icon={TrendingUp}
          color="bg-green-500"
          sub="Tổng bảng kê tháng này"
        />
      </div>

      {/* Alerts */}
      {stats?.alerts && stats.alerts.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <h3 className="font-semibold text-amber-800">
              Cảnh báo giấy tờ ({stats.alerts.length})
            </h3>
          </div>
          <ul className="space-y-1.5">
            {stats.alerts.map((alert, i) => (
              <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                <span className="text-amber-400 mt-0.5">•</span>
                {alert}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Revenue chart */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
        <h3 className="font-semibold text-gray-800 mb-4">Doanh thu 6 tháng gần nhất</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={stats?.monthly_revenue || []} barSize={36}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 13, fill: '#6b7280' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#6b7280' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => `${(v / 1e6).toFixed(0)}tr`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f3f4f6' }} />
            <Bar
              dataKey="revenue"
              fill="#1e3a5f"
              radius={[6, 6, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
