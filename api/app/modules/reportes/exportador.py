"""Módulo de exportación de reportes fiscales a Excel (.xlsx) y PDF (WeasyPrint)."""

import io

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet

from app.modules.impuestos.schemas import LibroComprasResponse, LibroVentasResponse


def exportar_libro_ventas_excel(libro: LibroVentasResponse, empresa_nombre: str) -> bytes:
    """Genera el Libro de Ventas en formato Excel según especificación fiscal SENIAT."""
    wb = openpyxl.Workbook()
    ws: Worksheet = wb.active  # type: ignore[assignment]
    ws.title = "Libro de Ventas"

    # Encabezado
    ws.merge_cells("A1:K1")
    ws["A1"] = f"LIBRO DE VENTAS - {empresa_nombre}"
    ws["A1"].font = Font(size=14, bold=True, color="1B365D")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:K2")
    ws["A2"] = f"Período Fiscal: {libro.periodo_fiscal}"
    ws["A2"].font = Font(size=11, bold=True)
    ws["A2"].alignment = Alignment(horizontal="center")

    columnas = [
        "N° Op.",
        "Fecha",
        "RIF Cliente",
        "Razón Social",
        "N° Factura",
        "N° Control",
        "Total Ventas (Bs.)",
        "Exento (Bs.)",
        "Base Imponible (Bs.)",
        "IVA Débito (Bs.)",
        "IVA Retenido (Bs.)",
    ]
    ws.append([])
    ws.append(columnas)

    # Estilo cabecera
    header_fill = PatternFill(start_color="EAECEE", end_color="EAECEE", fill_type="solid")
    for col_num in range(1, len(columnas) + 1):
        cell = ws.cell(row=4, column=col_num)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for f in libro.filas:
        ws.append(
            [
                f.operacion,
                f.fecha.strftime("%d/%m/%Y"),
                f.rif_cliente,
                f.nombre_cliente,
                f.numero_factura,
                f.numero_control,
                float(f.total_ventas_ves),
                float(f.ventas_exentas_ves),
                float(f.base_imponible_ves),
                float(f.iva_ves),
                float(f.iva_retenido_ves),
            ]
        )

    # Totales
    ws.append([])
    ws.append(
        [
            "TOTALES",
            "",
            "",
            "",
            "",
            "",
            float(libro.total_ventas_ves),
            float(libro.total_exento_ves),
            float(libro.total_base_ves),
            float(libro.total_iva_ves),
            float(libro.total_iva_retenido_ves),
        ]
    )

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def exportar_libro_compras_excel(libro: LibroComprasResponse, empresa_nombre: str) -> bytes:
    """Genera el Libro de Compras en formato Excel según especificación fiscal SENIAT."""
    wb = openpyxl.Workbook()
    ws: Worksheet = wb.active  # type: ignore[assignment]
    ws.title = "Libro de Compras"

    ws.merge_cells("A1:L1")
    ws["A1"] = f"LIBRO DE COMPRAS - {empresa_nombre}"
    ws["A1"].font = Font(size=14, bold=True, color="1B365D")
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:L2")
    ws["A2"] = f"Período Fiscal: {libro.periodo_fiscal}"
    ws["A2"].font = Font(size=11, bold=True)
    ws["A2"].alignment = Alignment(horizontal="center")

    columnas = [
        "N° Op.",
        "Fecha",
        "RIF Proveedor",
        "Razón Social",
        "N° Factura",
        "N° Control",
        "Total Compras (Bs.)",
        "Exento (Bs.)",
        "Base Imponible (Bs.)",
        "IVA Crédito (Bs.)",
        "IVA Retenido (Bs.)",
        "N° Comprobante Ret.",
    ]
    ws.append([])
    ws.append(columnas)

    header_fill = PatternFill(start_color="EAECEE", end_color="EAECEE", fill_type="solid")
    for col_num in range(1, len(columnas) + 1):
        cell = ws.cell(row=4, column=col_num)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for f in libro.filas:
        ws.append(
            [
                f.operacion,
                f.fecha.strftime("%d/%m/%Y"),
                f.rif_proveedor,
                f.nombre_proveedor,
                f.numero_factura,
                f.numero_control or "—",
                float(f.total_compras_ves),
                float(f.compras_exentas_ves),
                float(f.base_imponible_ves),
                float(f.iva_ves),
                float(f.iva_retenido_ves),
                f.numero_comprobante_retencion or "—",
            ]
        )

    ws.append([])
    ws.append(
        [
            "TOTALES",
            "",
            "",
            "",
            "",
            "",
            float(libro.total_compras_ves),
            float(libro.total_exento_ves),
            float(libro.total_base_ves),
            float(libro.total_iva_ves),
            float(libro.total_iva_retenido_ves),
            "",
        ]
    )

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
