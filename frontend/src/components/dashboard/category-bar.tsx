"use client"
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts"
import { getCategoryColor } from "@/lib/constants"
import { formatCOP } from "@/lib/format"

interface CategoryBarProps {
  data: { name: string; total: number }[]
}

export function CategoryBar({ data }: CategoryBarProps) {
  if (!data.length) {
    return <p className="text-muted-foreground text-sm">Sin gastos este mes</p>
  }

  const sorted = [...data].sort((a, b) => b.total - a.total)

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <h3 className="text-sm font-medium text-muted-foreground mb-4">Gasto por categoria</h3>
      <ResponsiveContainer width="100%" height={sorted.length * 40 + 20}>
        <BarChart data={sorted} layout="vertical" margin={{ left: 0, right: 10 }}>
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            width={110}
            tick={{ fill: "#93a0b5", fontSize: 12 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(value) => [formatCOP(Number(value)), "Total"]}
            contentStyle={{
              backgroundColor: "#181c24",
              border: "1px solid #2a3140",
              borderRadius: "8px",
              color: "#eef1f6",
            }}
          />
          <Bar dataKey="total" radius={[0, 6, 6, 0]} barSize={20}>
            {sorted.map((entry) => (
              <Cell key={entry.name} fill={getCategoryColor(entry.name)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
