CATEGORIAS_INICIALES: list[dict[str, str | bool]] = [
    # Gastos originales
    {"nombre": "Mercado", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Transporte", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Servicios", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Ocio", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Salud", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Otros", "tipo": "gasto", "es_fijo": False},
    # Gastos nuevos (granulares)
    {"nombre": "Hogar", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Seguridad Social", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Administracion", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Suscripciones", "tipo": "gasto", "es_fijo": True},
    {"nombre": "Tarjeta", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Celular", "tipo": "gasto", "es_fijo": True},
    {"nombre": "GYM", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Ahorro", "tipo": "gasto", "es_fijo": False},
    {"nombre": "Deuda", "tipo": "gasto", "es_fijo": False},
    # Ingresos
    {"nombre": "Salario", "tipo": "ingreso", "es_fijo": True},
    {"nombre": "Freelance", "tipo": "ingreso", "es_fijo": False},
]
