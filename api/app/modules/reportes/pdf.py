"""Generador de documentos y reportes fiscales en PDF usando WeasyPrint y Jinja2."""

import weasyprint  # type: ignore[import-untyped]
from jinja2 import Template

CSS_BASE = """
@page {
    size: letter;
    margin: 12mm 15mm 15mm 15mm;
    @bottom-right {
        content: "Página " counter(page) " de " counter(pages);
        font-size: 8pt;
        color: #7f8c8d;
    }
}
body {
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    color: #2c3e50;
    margin: 0;
    padding: 0;
    font-size: 9pt;
    line-height: 1.3;
}
.header-table {
    width: 100%;
    margin-bottom: 15px;
    border-bottom: 2px solid #2980b9;
    padding-bottom: 8px;
}
.company-title {
    font-size: 14pt;
    font-weight: bold;
    color: #2c3e50;
}
.company-rif {
    font-size: 10pt;
    font-weight: bold;
    color: #7f8c8d;
}
.doc-box {
    border: 1px solid #2980b9;
    background-color: #ebf5fb;
    border-radius: 4px;
    padding: 8px;
    text-align: center;
}
.doc-type {
    font-size: 11pt;
    font-weight: bold;
    color: #2980b9;
    text-transform: uppercase;
}
.doc-number {
    font-size: 13pt;
    font-weight: bold;
    color: #c0392b;
}
.doc-control {
    font-size: 8pt;
    color: #34495e;
}
.info-section {
    width: 100%;
    margin-bottom: 15px;
    border: 1px solid #bdc3c7;
    border-radius: 4px;
    padding: 8px;
    background-color: #fcfcfc;
}
.info-grid {
    width: 100%;
    border-collapse: collapse;
}
.info-grid td {
    padding: 3px 6px;
    font-size: 8.5pt;
}
.label {
    font-weight: bold;
    color: #34495e;
    width: 20%;
}
.data-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    margin-bottom: 15px;
}
.data-table th {
    background-color: #34495e;
    color: #ffffff;
    font-weight: bold;
    font-size: 8pt;
    padding: 6px 4px;
    text-align: left;
    border: 1px solid #2c3e50;
}
.data-table td {
    padding: 5px 4px;
    font-size: 8pt;
    border: 1px solid #e0e0e0;
}
.data-table tr:nth-child(even) {
    background-color: #f9f9f9;
}
.text-right {
    text-align: right;
}
.text-center {
    text-align: center;
}
.totals-section {
    width: 100%;
    margin-top: 10px;
}
.totals-table {
    width: 45%;
    float: right;
    border-collapse: collapse;
}
.totals-table td {
    padding: 4px 8px;
    font-size: 8.5pt;
    border: 1px solid #e0e0e0;
}
.totals-table .total-label {
    font-weight: bold;
    background-color: #f2f4f4;
}
.totals-table .grand-total {
    font-size: 10pt;
    font-weight: bold;
    background-color: #eaeded;
    color: #1b2631;
}
.footer-notes {
    clear: both;
    margin-top: 25px;
    padding-top: 10px;
    border-top: 1px dashed #bdc3c7;
    font-size: 7.5pt;
    color: #7f8c8d;
}
"""

TEMPLATE_FACTURA_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{{ css }}</style>
</head>
<body>

<table class="header-table">
    <tr>
        <td style="width: 60%; vertical-align: top;">
            <div class="company-title">{{ empresa.razon_social }}</div>
            <div class="company-rif">RIF: {{ empresa.rif }}</div>
            <div style="font-size: 8pt; color: #555; margin-top: 4px;">
                {{ empresa.direccion_fiscal or '' }}
            </div>
            <div style="font-size: 8pt; color: #555;">
                Teléfono: {{ empresa.telefono or 'N/A' }}
            </div>
        </td>
        <td style="width: 40%; vertical-align: top;">
            <div class="doc-box">
                <div class="doc-type">{{ doc_titulo or 'FACTURA' }}</div>
                <div class="doc-number">N° {{ factura.numero }}</div>
                {% if factura.numero_control %}
                <div class="doc-control">N° Control: <b>{{ factura.numero_control }}</b></div>
                {% endif %}
                <div style="font-size: 8pt; margin-top: 4px;">
                    Fecha: <b>{{ factura.fecha_emision }}</b>
                </div>
            </div>
        </td>
    </tr>
</table>

<div class="info-section">
    <table class="info-grid">
        <tr>
            <td class="label">CLIENTE:</td>
            <td>{{ cliente.nombre }}</td>
            <td class="label">RIF / C.I.:</td>
            <td>{{ cliente.tipo_identificacion }}-{{ cliente.identificacion }}</td>
        </tr>
        <tr>
            <td class="label">DIRECCIÓN:</td>
            <td colspan="3">{{ cliente.direccion or 'No especificada' }}</td>
        </tr>
        <tr>
            <td class="label">CONDICIÓN:</td>
            <td>{{ factura.condicion_pago | upper }}</td>
            <td class="label">VENCIMIENTO:</td>
            <td>{{ factura.fecha_vencimiento or factura.fecha_emision }}</td>
        </tr>
    </table>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th class="text-center" style="width: 8%;">ÍTEM</th>
            <th class="text-center" style="width: 15%;">CÓDIGO</th>
            <th style="width: 37%;">DESCRIPCIÓN</th>
            <th class="text-center" style="width: 10%;">CANT.</th>
            <th class="text-right" style="width: 15%;">PRECIO U.</th>
            <th class="text-right" style="width: 15%;">TOTAL</th>
        </tr>
    </thead>
    <tbody>
        {% for linea in detalles %}
        <tr>
            <td class="text-center">{{ loop.index }}</td>
            <td class="text-center">{{ linea.codigo }}</td>
            <td>{{ linea.descripcion }}</td>
            <td class="text-center">{{ "%.2f" | format(linea.cantidad) }}</td>
            <td class="text-right">{{ "%.2f" | format(linea.precio_unitario) }}</td>
            <td class="text-right">{{ "%.2f" | format(linea.subtotal) }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<div class="totals-section">
    <table class="totals-table">
        <tr>
            <td class="total-label">SUBTOTAL:</td>
            <td class="text-right">
                {{ "%.2f" | format(factura.base_imponible + factura.monto_exento) }}
            </td>
        </tr>
        {% if factura.monto_exento > 0 %}
        <tr>
            <td class="total-label">EXENTO:</td>
            <td class="text-right">{{ "%.2f" | format(factura.monto_exento) }}</td>
        </tr>
        {% endif %}
        <tr>
            <td class="total-label">BASE IMPONIBLE:</td>
            <td class="text-right">{{ "%.2f" | format(factura.base_imponible) }}</td>
        </tr>
        <tr>
            <td class="total-label">IVA:</td>
            <td class="text-right">{{ "%.2f" | format(factura.monto_iva) }}</td>
        </tr>
        <tr class="grand-total">
            <td>TOTAL {{ factura.moneda }}:</td>
            <td class="text-right">{{ "%.2f" | format(factura.monto_total) }}</td>
        </tr>
        {% if factura.moneda == 'USD' and factura.tasa_cambio %}
        <tr style="background-color: #fcf3cf; font-weight: bold;">
            <td>TOTAL BS. (BCV {{ "%.4f" | format(factura.tasa_cambio) }}):</td>
            <td class="text-right">
                {{ "%.2f" | format(factura.monto_total * factura.tasa_cambio) }}
            </td>
        </tr>
        {% endif %}
    </table>
</div>

<div class="footer-notes">
    <p>Documento emitido conforme a las providencias del SENIAT. Gracias por su compra.</p>
</div>

</body>
</html>
"""

TEMPLATE_RETENCION_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{{ css }}</style>
</head>
<body>

<table class="header-table">
    <tr>
        <td style="width: 55%; vertical-align: top;">
            <div class="company-title">{{ agente.razon_social }}</div>
            <div class="company-rif">RIF: {{ agente.rif }}</div>
            <div style="font-size: 8pt; color: #555;">{{ agente.direccion_fiscal or '' }}</div>
            <div style="font-size: 8pt; color: #27ae60; font-weight: bold; margin-top: 4px;">
                AGENTE DE RETENCIÓN
            </div>
        </td>
        <td style="width: 45%; vertical-align: top;">
            <div class="doc-box">
                <div class="doc-type">COMPROBANTE DE RETENCIÓN {{ tipo_retencion | upper }}</div>
                <div class="doc-number">N° {{ comprobante.numero }}</div>
                <div style="font-size: 8pt; margin-top: 4px;">
                    Fecha: <b>{{ comprobante.fecha_emision }}</b>
                </div>
                <div style="font-size: 8pt;">
                    Período Fiscal: <b>{{ comprobante.periodo_fiscal }}</b>
                </div>
            </div>
        </td>
    </tr>
</table>

<div class="info-section">
    <table class="info-grid">
        <tr>
            <td class="label">SUJETO RETENIDO:</td>
            <td>{{ sujeto.nombre }}</td>
            <td class="label">RIF / C.I.:</td>
            <td>{{ sujeto.tipo_identificacion }}-{{ sujeto.identificacion }}</td>
        </tr>
        <tr>
            <td class="label">DIRECCIÓN:</td>
            <td colspan="3">{{ sujeto.direccion or 'No especificada' }}</td>
        </tr>
    </table>
</div>

<table class="data-table">
    <thead>
        <tr>
            <th class="text-center" style="width: 8%;">N° OP.</th>
            <th class="text-center" style="width: 12%;">FECHA FACT.</th>
            <th class="text-center" style="width: 15%;">N° FACTURA</th>
            <th class="text-center" style="width: 15%;">N° CONTROL</th>
            <th class="text-right" style="width: 15%;">BASE IMPONIBLE</th>
            <th class="text-right" style="width: 12%;">IMPUESTO</th>
            <th class="text-center" style="width: 8%;">% RET.</th>
            <th class="text-right" style="width: 15%;">MONTO RETENIDO</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="text-center">1</td>
            <td class="text-center">{{ comprobante.fecha_emision }}</td>
            <td class="text-center">{{ comprobante.factura_numero }}</td>
            <td class="text-center">{{ comprobante.numero_control or 'N/A' }}</td>
            <td class="text-right">{{ "%.2f" | format(comprobante.base_imponible) }}</td>
            <td class="text-right">{{ "%.2f" | format(comprobante.monto_impuesto) }}</td>
            <td class="text-center">{{ "%.2f" | format(comprobante.porcentaje) }}%</td>
            <td class="text-right" style="font-weight: bold;">
                {{ "%.2f" | format(comprobante.monto_retenido) }}
            </td>
        </tr>
    </tbody>
</table>

<div class="totals-section">
    <table class="totals-table">
        <tr class="grand-total">
            <td>TOTAL RETENIDO (Bs.):</td>
            <td class="text-right">{{ "%.2f" | format(comprobante.monto_retenido) }}</td>
        </tr>
    </table>
</div>

<br><br><br>
<table style="width: 100%; text-align: center; margin-top: 40px;">
    <tr>
        <td style="width: 45%; border-top: 1px solid #333; padding-top: 6px;">
            <b>Agente de Retención (Firma y Sello)</b><br>
            <span style="font-size: 8pt;">{{ agente.razon_social }}</span>
        </td>
        <td style="width: 10%;"></td>
        <td style="width: 45%; border-top: 1px solid #333; padding-top: 6px;">
            <b>Beneficiario / Sujeto Retenido</b><br>
            <span style="font-size: 8pt;">Firma de recepción</span>
        </td>
    </tr>
</table>

<div class="footer-notes">
    <p>Comprobante emitido de acuerdo a la normativa vigente del SENIAT.</p>
</div>

</body>
</html>
"""


def generar_factura_pdf(
    empresa: dict,
    cliente: dict,
    factura: dict,
    detalles: list[dict],
    doc_titulo: str = "FACTURA",
) -> bytes:
    """Renderiza una factura de venta o presupuesto en formato PDF."""
    template = Template(TEMPLATE_FACTURA_HTML)
    html_content = template.render(
        css=CSS_BASE,
        empresa=empresa,
        cliente=cliente,
        factura=factura,
        detalles=detalles,
        doc_titulo=doc_titulo,
    )
    return weasyprint.HTML(string=html_content).write_pdf()


def generar_comprobante_retencion_pdf(
    agente: dict,
    sujeto: dict,
    comprobante: dict,
    tipo_retencion: str = "IVA",
) -> bytes:
    """Renderiza un comprobante de retención de IVA o ISLR en formato PDF."""
    template = Template(TEMPLATE_RETENCION_HTML)
    html_content = template.render(
        css=CSS_BASE,
        agente=agente,
        sujeto=sujeto,
        comprobante=comprobante,
        tipo_retencion=tipo_retencion,
    )
    return weasyprint.HTML(string=html_content).write_pdf()
