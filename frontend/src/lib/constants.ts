export const CATEGORY_COLORS: Record<string, string> = {
  Mercado: "#6ee7b7",
  Transporte: "#93c5fd",
  Servicios: "#c4b5fd",
  Ocio: "#fda4af",
  Salud: "#fdba74",
  Hogar: "#a78bfa",
  "Seguridad Social": "#f0abfc",
  Administracion: "#cbd5e1",
  Suscripciones: "#67e8f9",
  Tarjeta: "#fca5a5",
  Celular: "#86efac",
  GYM: "#fcd34d",
  Ahorro: "#34d399",
  Deuda: "#fb923c",
  Otros: "#94a3b8",
  Salario: "#86efac",
  Freelance: "#a5f3fc",
}

export function getCategoryColor(name: string | null): string {
  return CATEGORY_COLORS[name || ""] || "#94a3b8"
}
