export interface Movimiento {
  id: number
  user_id: number
  usuario: string | null
  categoria_id: number | null
  categoria: string | null
  tipo: "gasto" | "ingreso" | null
  monto_cop: number
  monto_fmt: string
  descripcion: string | null
  marca_dedup?: string | null
  fecha_gasto: string | null
  fecha_registro: string | null
  es_compartido?: boolean
  medio_pago?: string | null
  compra_cuotas_id?: number | null
}

export interface Categoria {
  id: number
  nombre: string
  tipo: "gasto" | "ingreso"
}

export interface Usuario {
  id: number
  nombre: string
  email: string | null
}

export interface MovimientoIn {
  user_id: number
  categoria_id: number | null
  monto_cop: number
  descripcion: string | null
  fecha_gasto: string | null
}

export interface MovimientoPatch {
  user_id?: number
  categoria_id?: number | null
  limpiar_categoria?: boolean
  monto_cop?: number
  descripcion?: string | null
  fecha_gasto?: string | null
}

export interface Presupuesto {
  id: number
  user_id: number
  usuario: string | null
  categoria_id: number
  categoria: string | null
  monto_limite_cop: number
  mes_vigente: string
}

export interface PresupuestoResumen {
  categoria_id: number
  categoria: string
  limite: number
  gastado: number
  porcentaje: number
  restante: number
}

export interface GastoFijo {
  id: number
  user_id: number
  usuario: string | null
  categoria_id: number
  categoria: string | null
  nombre: string
  monto_cop: number
  es_compartido: boolean
  porcentaje_compartido: number | null
  activo: boolean
  dia_esperado: number | null
}

export interface CompraCuotas {
  id: number
  user_id: number
  usuario: string | null
  tarjeta_id: number | null
  fecha_compra: string | null
  establecimiento: string
  descripcion: string | null
  valor_total_cop: number
  num_cuotas: number
  cuotas_pagadas: number
  valor_cuota_cop: number
  valor_intereses_cop: number
  tasa_ea: number | null
  numero_transaccion: string | null
  tarjeta: string | null
  saldo_pendiente_cop: number
  liquidada: boolean
  cuotas_restantes: number
  es_compartido: boolean
}

export interface TarjetaCredito {
  id: number
  user_id: number
  usuario: string | null
  banco: string
  nombre: string
  ultimos_4: string | null
  fecha_corte: number
  fecha_pago: number
  tasa_ea: number | null
  cupo_total_cop: number | null
  activa: boolean
}

export interface ProyeccionMes {
  total: number
  compras: {
    id: number
    establecimiento: string
    valor_cuota: number
    cuota_num: number
    num_cuotas: number
  }[]
}

export interface IngresoRecurrente {
  id: number
  user_id: number
  usuario: string | null
  nombre: string
  tipo: "fijo" | "variable"
  frecuencia: "mensual" | "quincenal" | "semanal" | "anual"
  monto_cop: number
  dia_pago_1: number | null
  dia_pago_2: number | null
  activo: boolean
}

export interface ResumenIngresos {
  mes: string
  esperado_fijo: number
  esperado_variable: number
  esperado_total: number
  recibido: number
  diferencia: number
  ingresos: IngresoRecurrente[]
}

export interface Deuda {
  id: number
  user_id: number
  nombre: string
  tipo: string
  acreedor: string | null
  monto_original_cop: number
  saldo_cop: number
  cuota_mensual_cop: number | null
  tasa_ea: number | null
  activa: boolean
  notas: string | null
}

export interface MetaAhorro {
  id: number
  user_id: number
  nombre: string
  monto_objetivo_cop: number
  monto_actual_cop: number
  fecha_limite: string | null
  activa: boolean
  progreso: number
}

export interface BalanceCompartido {
  usuarios: Record<string, string>
  detalles: {
    concepto: string
    valor_compra?: number
    total: number
    mitad: number
    paga: string
    debe: string
    fuente: string
    porcentaje: number
    fecha?: string | null
  }[]
  resumen_por_usuario: Record<string, { nombre: string; pago_total: number; debe_total: number }>
  balance_neto: number
  quien_debe: string
}
