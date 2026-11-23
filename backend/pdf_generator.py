from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from models import PagoComprobante, Compra

def generar_pdf_comprobante(comprobante: PagoComprobante, compra: Compra) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    elementos = []

    titulo_style = ParagraphStyle(
        "TituloMuni", parent=styles["Heading1"], fontSize=15,
        textColor=colors.HexColor("#1b4332"), spaceAfter=4
    )
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=10, textColor=colors.grey)

    elementos.append(Paragraph(compra.municipalidad.nombre.upper(), titulo_style))
    elementos.append(Paragraph(f"Comuna: {compra.municipalidad.comuna} | RUT: {compra.municipalidad.rut_institucional}", sub_style))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph("<b>COMPROBANTE DE PAGO - PERMISO DE CIRCULACIÓN</b>", styles["Heading2"]))
    elementos.append(Spacer(1, 8))

    modalidad_txt = "Pago Total (1 operación)" if compra.modalidad == "TOTAL" else "Plan Dos Cuotas"
    cuota_txt = f"Cuota {comprobante.numero_cuota_pagada} de 2" if comprobante.numero_cuota_pagada else "Pago Único"
    cuotas_pend = sum(1 for c in compra.cuotas if c.estado == "PENDIENTE")

    info_general = [
        ["Folio Único:", comprobante.folio, "Fecha de Pago:", comprobante.fecha_pago.strftime("%d/%m/%Y %H:%M")],
        ["Cliente:", compra.cliente.nombre, "RUT Cliente:", compra.cliente.rut],
        ["Período:", str(compra.periodo), "Modalidad:", modalidad_txt],
        ["Detalle de Pago:", cuota_txt, "Estado Compra:", compra.estado.replace("_", " ")],
    ]
    tabla_info = Table(info_general, colWidths=[95, 190, 95, 150])
    tabla_info.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f6f8")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elementos.append(tabla_info)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("<b>Detalle de Vehículos Incluidos</b>", styles["Heading3"]))
    filas_veh = [["Patente", "Tipo / Vehículo", "Valor Base", "Cargos Muni.", "Subtotal"]]
    for d in compra.detalles:
        v = d.vehiculo
        filas_veh.append([
            v.patente,
            f"{v.tipo} - {v.marca} {v.modelo} ({v.anio})",
            f"${d.valor_base_historico:,}".replace(",", "."),
            f"${d.cargos_historico:,}".replace(",", "."),
            f"${d.subtotal:,}".replace(",", "."),
        ])

    tabla_veh = Table(filas_veh, colWidths=[70, 210, 80, 85, 85])
    tabla_veh.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4332")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_veh)
    elementos.append(Spacer(1, 16))

    resumen = [
        ["Total General de la Compra:", f"${compra.total_general:,}".replace(",", ".")],
        ["Monto Pagado en esta Operación:", f"${comprobante.monto_pagado:,}".replace(",", ".")],
        ["Total Acumulado Pagado:", f"${compra.monto_pagado:,}".replace(",", ".")],
        ["Saldo Pendiente:", f"${comprobante.saldo_restante:,}".replace(",", ".")],
        ["Cuotas Pendientes:", str(cuotas_pend)],
    ]
    tabla_res = Table(resumen, colWidths=[380, 150])
    tabla_res.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, 1), (-1, 1), 1, colors.HexColor("#1b4332")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#e8f5e9")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(tabla_res)
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(
        f"Operación registrada por: {comprobante.usuario_operador} | Documento emitido desde base de datos municipal.",
        sub_style
    ))

    doc.build(elementos)
    buffer.seek(0)
    return buffer