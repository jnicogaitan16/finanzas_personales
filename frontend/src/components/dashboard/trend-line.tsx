"use client"
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts"
import { formatCOP } from "@/lib/format"

interface TrendProps {
  data: { mes: string; gasto: number; ingreso: number }[]
}

export function TrendLine({ data }: TrendProps) {
  if (!data.length) {
    return <p className="text-muted-foreground text-sm">Sin datos de tendencia</p>
  }

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <h3 className="text-sm font-medium text-muted-foreground mb-4">Tendencia mensual</h3>
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={data} margin={{ left: 10, right: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a3140" />
          <XAxis
            dataKey="mes"
            tick={{ fill: "#93a0b5", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#93a0b5", fontSize: 11 }}
            tickFormatter={(v) => `${Math.round(v / 1000)}K`}
            axisLine={false}
            tickLine={false}
            width={50}
          />
          <Tooltip
            formatter={(value, name) => [
              formatCOP(Number(value)),
              name === "gasto" ? "Gastos" : "Ingresos",
            ]}
            contentStyle={{
              backgroundColor: "#181c24",
              border: "1px solid #2a3140",
              borderRadius: "8px",
              color: "#eef1f6",
            }}
          />
          <Line
            type="monotone"
            dataKey="gasto"
            stroke="#fda4af"
            strokeWidth={2}
            dot={{ r: 4, fill: "#fda4af" }}
          />
          <Line
            type="monotone"
            dataKey="ingreso"
            stroke="#6ee7b7"
            strokeWidth={2}
            dot={{ r: 4, fill: "#6ee7b7" }}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-6 mt-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-rose-400 rounded" /> Gastos
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 bg-primary rounded" /> Ingresos
        </div>
      </div>
    </div>
  )
}
