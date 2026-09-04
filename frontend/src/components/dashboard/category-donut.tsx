"use client"
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts"
import { getCategoryColor } from "@/lib/constants"
import { formatCOP } from "@/lib/format"

interface Props {
  data: { name: string; total: number }[]
  gastoTotal: number
}

export function CategoryDonut({ data, gastoTotal }: Props) {
  if (!data.length) {
    return null
  }

  const sorted = [...data].sort((a, b) => b.total - a.total)
  const total = data.reduce((s, d) => s + d.total, 0)

  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
      {/* Category chips - scrollable row */}
      <div className="flex gap-2 overflow-x-auto pb-3 -mx-1 px-1 scrollbar-hide">
        {sorted.slice(0, 6).map((cat) => (
          <div
            key={cat.name}
            className="shrink-0 rounded-xl px-3 py-2 min-w-[90px] text-center"
            style={{ backgroundColor: getCategoryColor(cat.name) + "20" }}
          >
            <p className="text-[11px] text-gray-300 truncate">{cat.name}</p>
            <p
              className="text-sm font-bold tabular-nums mt-0.5"
              style={{ color: getCategoryColor(cat.name) }}
            >
              {formatCOP(cat.total)}
            </p>
          </div>
        ))}
      </div>

      {/* Donut chart with center text */}
      <div className="relative">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={sorted}
              dataKey="total"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={65}
              outerRadius={95}
              paddingAngle={2}
              strokeWidth={0}
            >
              {sorted.map((entry) => (
                <Cell key={entry.name} fill={getCategoryColor(entry.name)} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <p className="text-xs text-gray-400">Gastos</p>
          <p className="text-xl font-bold text-gray-100 tabular-nums">{formatCOP(gastoTotal)}</p>
        </div>
      </div>

      {/* Legend grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mt-2">
        {sorted.map((d) => (
          <div key={d.name} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: getCategoryColor(d.name) }}
              />
              <span className="text-gray-400 truncate">{d.name}</span>
            </div>
            <span className="text-gray-300 tabular-nums shrink-0 ml-2">
              {total > 0 ? Math.round((d.total / total) * 100) : 0}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
