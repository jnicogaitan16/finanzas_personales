"use client"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { formatCOP } from "@/lib/format"

interface TrendProps {
  data: { mes: string; gasto: number; ingreso: number }[]
}

export function TrendLine({ data }: TrendProps) {
  if (!data.length) {
    return null
  }

  return (
    <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs text-gray-400 uppercase tracking-wide">Tendencia mensual</h3>
        <div className="flex gap-4 text-xs text-gray-500">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[3px] bg-rose-400 rounded-full" /> Gastos
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-[3px] bg-emerald-400 rounded-full" /> Ingresos
          </div>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ left: 0, right: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
          <XAxis
            dataKey="mes"
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 10 }}
            tickFormatter={(v) => `${Math.round(v / 1000)}K`}
            axisLine={false}
            tickLine={false}
            width={45}
          />
          <Tooltip
            formatter={(value, name) => [
              formatCOP(Number(value)),
              name === "gasto" ? "Gastos" : "Ingresos",
            ]}
            contentStyle={{
              backgroundColor: "hsl(228,14%,12%)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "12px",
              color: "#f3f4f6",
              fontSize: "13px",
            }}
          />
          <Line
            type="monotone"
            dataKey="gasto"
            stroke="#fb7185"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#fb7185", strokeWidth: 0 }}
          />
          <Line
            type="monotone"
            dataKey="ingreso"
            stroke="#34d399"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#34d399", strokeWidth: 0 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
