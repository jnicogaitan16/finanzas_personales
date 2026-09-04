export const CATEGORY_COLORS: Record<string, string> = {
  Mercado: "#8b5cf6",       // violet
  Transporte: "#06b6d4",    // cyan
  Servicios: "#a78bfa",     // violet claro
  Ocio: "#f472b6",          // pink
  Salud: "#fb923c",         // orange
  Hogar: "#7c3aed",         // purple
  "Seguridad Social": "#c084fc", // purple claro
  Administracion: "#94a3b8", // gris
  Suscripciones: "#22d3ee",  // cyan claro
  Tarjeta: "#f43f5e",       // rose
  Celular: "#34d399",       // emerald
  GYM: "#fbbf24",           // amber
  Ahorro: "#10b981",        // emerald oscuro
  Deuda: "#ef4444",         // red
  Otros: "#64748b",         // slate
  Salario: "#34d399",       // emerald
  Freelance: "#38bdf8",     // sky
}

export function getCategoryColor(name: string | null): string {
  return CATEGORY_COLORS[name || ""] || "#64748b"
}
