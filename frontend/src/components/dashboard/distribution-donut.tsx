"use client"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import { getCategoryColor } from "@/lib/constants"
import { formatCOP } from "@/lib/format"

interface DonutProps {
  data: { name: string; total: number }[]
}

export function DistributionDonut({ data }: DonutProps) {
  if (!data.length) {
    return <p className="text-muted-foreground text-sm">Sin datos</p>
  }

  const total = data.reduce((s, d) => s + d.total, 0)

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <h3 className="text-sm font-medium text-muted-foreground mb-4">Distribucion del mes</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="total"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={2}
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={getCategoryColor(entry.name)} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [formatCOP(Number(value)), ""]}
            contentStyle={{
              backgroundColor: "#181c24",
              border: "1px solid #2a3140",
              borderRadius: "8px",
              color: "#eef1f6",
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-wrap gap-3 mt-2 justify-center">
        {data.map((d) => (
          <div key={d.name} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: getCategoryColor(d.name) }}
            />
            {d.name} ({total > 0 ? Math.round((d.total / total) * 100) : 0}%)
          </div>
        ))}
      </div>
    </div>
  )
}
