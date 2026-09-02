"use client"
import { formatCOP, formatDate } from "@/lib/format"
import type { Movimiento } from "@/lib/types"

interface Props {
  movimientos: Movimiento[]
}

export function RecentTable({ movimientos }: Props) {
  const recientes = movimientos.slice(0, 10)

  if (!recientes.length) {
    return <p className="text-muted-foreground text-sm">Sin movimientos recientes</p>
  }

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <h3 className="text-sm font-medium text-muted-foreground px-4 pt-4 pb-2">Ultimos movimientos</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-2 text-muted-foreground font-medium text-xs uppercase">Fecha</th>
              <th className="text-left px-4 py-2 text-muted-foreground font-medium text-xs uppercase">Categoria</th>
              <th className="text-right px-4 py-2 text-muted-foreground font-medium text-xs uppercase">Monto</th>
              <th className="text-left px-4 py-2 text-muted-foreground font-medium text-xs uppercase hidden sm:table-cell">Descripcion</th>
            </tr>
          </thead>
          <tbody>
            {recientes.map((m) => (
              <tr key={m.id} className="border-b border-border last:border-0">
                <td className="px-4 py-2.5 text-muted-foreground">{formatDate(m.fecha_gasto)}</td>
                <td className="px-4 py-2.5">{m.categoria || "—"}</td>
                <td className={`px-4 py-2.5 text-right tabular-nums font-medium ${
                  m.tipo === "ingreso" ? "text-primary" : "text-rose-400"
                }`}>
                  {formatCOP(m.monto_cop)}
                </td>
                <td className="px-4 py-2.5 text-muted-foreground hidden sm:table-cell truncate max-w-[200px]">
                  {m.descripcion || ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
