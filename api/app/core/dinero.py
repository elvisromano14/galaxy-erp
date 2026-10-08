from decimal import ROUND_HALF_UP, Decimal

# Decimales estándar según especificación (Sección 15.3)
DECIMALES_MONTO = Decimal("0.01")  # NUMERIC(18,2) - Totales, subsecciones y documentos
DECIMALES_PRECIO = Decimal("0.0001")  # NUMERIC(18,4) - Precios unitarios y costos
DECIMALES_CANTIDAD = Decimal("0.0001")  # NUMERIC(18,4) - Cantidades físicas
DECIMALES_TASA = Decimal("0.000001")  # NUMERIC(18,6) - Tasas de cambio (BCV / manual)


def a_decimal(valor: int | str | Decimal) -> Decimal:
    """Convierte de forma segura a Decimal. Evita flotantes."""
    if isinstance(valor, float):
        raise TypeError("No se permite crear Decimal a partir de float. Use str o int.")
    return Decimal(str(valor))


def redondear_monto(valor: Decimal) -> Decimal:
    """Redondea a 2 decimales para totales de documentos contables."""
    return valor.quantize(DECIMALES_MONTO, rounding=ROUND_HALF_UP)


def redondear_precio(valor: Decimal) -> Decimal:
    """Redondea a 4 decimales para precios y costos unitarios."""
    return valor.quantize(DECIMALES_PRECIO, rounding=ROUND_HALF_UP)


def redondear_cantidad(valor: Decimal) -> Decimal:
    """Redondea a 4 decimales para inventario y cantidades físicas."""
    return valor.quantize(DECIMALES_CANTIDAD, rounding=ROUND_HALF_UP)


def redondear_tasa(valor: Decimal) -> Decimal:
    """Redondea a 6 decimales para tasas de cambio."""
    return valor.quantize(DECIMALES_TASA, rounding=ROUND_HALF_UP)
