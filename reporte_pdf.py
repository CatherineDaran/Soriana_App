"""Reporte PDF de la valuación de SORIANA B (reportlab + gráficas de matplotlib).

El reporte refleja los valores que estén en pantalla en el momento de generarlo.
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import letter  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

import modelo as m  # noqa: E402

from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402

# DejaVu Sans (incluida con matplotlib) cubre Δ, Σ, β, −, → y ≤, que Helvetica no tiene.
_FUENTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
pdfmetrics.registerFont(TTFont("DejaVu", str(_FUENTES / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_FUENTES / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu",
                              boldItalic="DejaVu-Bold")
FUENTE, FUENTE_B = "DejaVu", "DejaVu-Bold"

# Paleta de Soriana, suavizada
AZUL = "#B23A33"      # color principal (rojo Soriana); se conserva el nombre por compatibilidad
CARBON = "#43464F"
GRIS = "#EFECEA"
VERDE = "#3E8A3A"
ROJO = "#B23A33"
VERDE_M = "#6AAE5A"
SEC_CL = "#9CC8DA"
PRIM_CL = "#E6B5AF"


# ---------------------------------------------------------------------------
# Formatos
# ---------------------------------------------------------------------------

def fm(v, dec=1):
    return "n.d." if v is None else f"{v:,.{dec}f}"


def fp(v, dec=2):
    return "n.d." if v is None else f"{v * 100:,.{dec}f}%"


def fd(v, dec=2):
    return "n.d." if v is None else f"${v:,.{dec}f}"


# ---------------------------------------------------------------------------
# Gráficas (matplotlib)
# ---------------------------------------------------------------------------

def _estilo(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#E5E5E5", linewidth=0.6)
    ax.tick_params(labelsize=7)


def _png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def grafica_inflacion(infl: dict) -> io.BytesIO:
    s = infl["serie"]
    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.plot(s.index, s["soriana"], color=AZUL, lw=1.5, label="Precio SORIANA B ($)")
    ax.set_ylabel("Precio ($)", fontsize=8)
    ax2 = ax.twinx()
    ax2.plot(s.index, s["inflacion_anual"] * 100, color="#A9A3A0", lw=1.2, ls="--",
             label="Inflación anual (%)")
    ax2.set_ylabel("Inflación anual (%)", fontsize=8)
    ax2.tick_params(labelsize=7)
    _estilo(ax)
    ax2.spines["top"].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, frameon=False, loc="upper left")
    ax.set_title("Inflación vs precio de SORIANA B", fontsize=9, color=AZUL)
    return _png(fig)


def grafica_ipc(ipc: dict) -> io.BytesIO:
    s = ipc["serie"]
    fig, ax = plt.subplots(figsize=(7, 2.6))
    ax.plot(s.index, s["base100_soriana"], color=AZUL, lw=1.5, label="SORIANA B")
    ax.plot(s.index, s["base100_ipc"], color="#A9A3A0", lw=1.2, label="S&P/BMV IPC")
    _estilo(ax)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("Desempeño base 100 (nov-2021 = 100)", fontsize=9, color=AZUL)
    return _png(fig)


def grafica_escenarios(esc: dict, precio: float) -> io.BytesIO:
    nombres = m.ESCENARIOS
    vals = [esc["resultados"][e]["valuacion"]["valor_por_accion"] or 0 for e in nombres]
    fig, ax = plt.subplots(figsize=(6, 2.6))
    barras = ax.bar(nombres, vals, color=[SEC_CL, AZUL, VERDE_M], width=0.55)
    ax.axhline(precio, color=CARBON, lw=1, ls="--", label=f"Precio de mercado ${precio:,.2f}")
    for b, v in zip(barras, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"${v:,.2f}", ha="center", va="bottom", fontsize=7)
    _estilo(ax)
    ax.legend(fontsize=7, frameon=False)
    ax.set_title("Valor por acción por escenario", fontsize=9, color=AZUL)
    return _png(fig)


def grafica_fcff(proy) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6, 2.4))
    anios = [str(a) for a in proy.columns]
    vals = proy.loc["FCFF"].values
    ax.bar(anios, vals, color=AZUL, width=0.55)
    for x, v in zip(anios, vals):
        ax.text(x, v, f"{v:,.0f}", ha="center", va="bottom", fontsize=7)
    _estilo(ax)
    ax.set_title("FCFF proyectado (mdp)", fontsize=9, color=AZUL)
    return _png(fig)


def grafica_sensibilidad(mat, wacc_base: float, g_base: float) -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(6, 3))
    z = mat.values.astype(float)
    im = ax.imshow(z, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(mat.columns)), [f"{g * 100:.1f}%" for g in mat.columns])
    ax.set_yticks(range(len(mat.index)), [f"{w * 100:.2f}%" for w in mat.index])
    ax.set_xlabel("Crecimiento perpetuo (g)", fontsize=8)
    ax.set_ylabel("WACC", fontsize=8)
    ax.tick_params(labelsize=7)
    vmax = np.nanmax(z) if np.isfinite(z).any() else 0
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            v = z[i, j]
            txt = "n.d." if np.isnan(v) else f"${v:,.2f}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=7,
                    color="white" if (not np.isnan(v) and v > 0.6 * vmax) else "black")
    for i, w in enumerate(mat.index):
        for j, g in enumerate(mat.columns):
            if abs(w - wacc_base) < 1e-9 and abs(g - g_base) < 1e-9:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, ec=CARBON, lw=2))
    fig.colorbar(im, ax=ax, shrink=0.8).ax.tick_params(labelsize=7)
    ax.set_title("Sensibilidad del valor por acción: WACC vs g", fontsize=9, color=AZUL)
    return _png(fig)


def grafica_tornado(tor) -> io.BytesIO:
    base = tor.attrs["base"]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    y = np.arange(len(tor))
    bajo = tor["-10%"].astype(float).values - base
    alto = tor["+10%"].astype(float).values - base
    ax.barh(y, bajo, left=base, color=PRIM_CL, label="Variable −10%")
    ax.barh(y, alto, left=base, color=AZUL, label="Variable +10%")
    ax.axvline(base, color="black", lw=0.8)
    ax.set_yticks(y, tor["Variable"])
    ax.tick_params(labelsize=7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(fontsize=7, frameon=False, loc="lower right")
    ax.set_xlabel("Valor por acción ($)", fontsize=8)
    ax.set_title("Tornado: cada variable ±10%", fontsize=9, color=AZUL)
    return _png(fig)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def _tabla(filas, anchos=None, encabezado=True, alinear_der_desde=1):
    t = Table(filas, colWidths=anchos, hAlign="LEFT")
    estilo = [
        ("FONTNAME", (0, 0), (-1, -1), FUENTE),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BFBFBF")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (alinear_der_desde, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if encabezado:
        estilo += [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(GRIS)),
            ("FONTNAME", (0, 0), (-1, 0), FUENTE_B),
        ]
    t.setStyle(TableStyle(estilo))
    return t


def generar_pdf(p: dict, data: dict, est: dict, escenario: str = "Base") -> bytes:
    emp = data["empresa"]
    infl = m.analisis_inflacion(data)
    ipc = m.analisis_ipc(data)
    r = m.modelo_completo(p, data, est, escenario)
    cc = r["costo_capital"]
    v = r["valuacion"]
    esc = m.todos_escenarios(p, data, est)
    comp = m.tabla_comparativa(p, esc)
    mat = m.matriz_sensibilidad(p, data, est, escenario)
    tor = m.tornado(p, data, est, escenario)
    val = m.validacion(data, est)
    red = m.efecto_redondeo_wacc(data, est)

    estilos = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=estilos["Heading1"], fontName=FUENTE_B, fontSize=15,
                        textColor=colors.HexColor(AZUL), spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=estilos["Heading2"], fontName=FUENTE_B, fontSize=11,
                        textColor=colors.HexColor(AZUL), spaceBefore=8, spaceAfter=4)
    txt = ParagraphStyle("txt", parent=estilos["BodyText"], fontName=FUENTE, fontSize=8.5,
                         leading=11.5)
    centro = ParagraphStyle("c", parent=txt, alignment=TA_CENTER)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title="Valuación de Organización Soriana (SORIANA B)",
                            author=", ".join(i["nombre"] for i in emp["equipo"]))
    el = []

    def seccion(n, titulo):
        el.append(Paragraph(f"{n}. {titulo}", h2))

    el.append(Paragraph("Valuación de Organización Soriana (SORIANA B)", h1))
    el.append(Paragraph(f"{emp['curso']} · Tecnológico de Monterrey · Generado el "
                        f"{date.today().strftime('%d/%m/%Y')} · Escenario en pantalla: <b>{escenario}</b>",
                        txt))
    el.append(Spacer(1, 6))

    # 1. Estudiante
    seccion(1, "Integrantes del equipo")
    filas = [["Nombre", "Matrícula"]] + [[i["nombre"], i["matricula"]] for i in emp["equipo"]]
    el.append(_tabla(filas, [7 * cm, 4 * cm]))

    # 2. Empresa
    seccion(2, "Empresa analizada")
    el.append(Paragraph(
        f"{emp['nombre']}, emisora <b>{emp['emisora']}</b> en la Bolsa Mexicana de Valores. Cadena de "
        f"autoservicio con ingresos de {fm(p['ingresos_base'], 0)} mdp en 2025. Precio de mercado de "
        f"referencia: {fd(p['precio_mercado'])} (12-oct-2026). Cifras en millones de pesos (mdp).", txt))

    # 3. Variables
    seccion(3, "Variables utilizadas")
    aj = r["ajustes"]
    filas = [["Variable", "Valor", "Variable", "Valor"]]
    pares = [
        ("Inflación de largo plazo", fp(p["inflacion_lp"])),
        ("Crecimiento real", fp(p["crec_real"])),
        ("g del sector: a", f"{r['sector']['a']:.4f}"),
        ("g del sector: b", f"{r['sector']['b']:.4f}"),
        ("Precio de mercado", fd(p["precio_mercado"])),
        ("Método de Rf", f"Método {p['metodo_rf']}"),
        ("Traslado de inflación a Rf", "Sí" if p["trasladar_inflacion_rf"] else "No"),
        ("Ingresos base 2025", fm(p["ingresos_base"], 0)),
        ("Margen EBIT", fp(p["margen_ebit"], 4)),
        ("Tasa NOPAT", fp(p["tasa_nopat"])),
        ("CAPEX / ingresos", fp(p["capex_ingresos"])),
        ("D&A / activo fijo", fp(p["da_activo_fijo"])),
        ("CTNO / ingresos", fp(p["ctno_ingresos"])),
        ("Crec. pasivo arrendamiento", fp(p["crec_arrendamiento"])),
        ("Pagos arrend. / pasivo", fp(p["pagos_arr_pasivo"])),
        ("Deuda (D)", fm(p["deuda_wacc"], 0)),
        ("Capital (E)", fm(p["capital_wacc"], 0)),
        ("ISR", fp(p["isr"])),
        ("Acciones (millones)", fm(p["acciones"], 0)),
        ("Efectivo", fm(p["efectivo"], 0)),
        ("Asociadas", fm(p["asociadas"], 0)),
        ("Deuda bursátil y bancaria", fm(p["deuda_puente"], 0)),
        ("Pasivo por arrendamiento", fm(p["arrendamiento_puente"], 0)),
        ("Participación no controladora", fm(p["no_controladora"], 0)),
        ("Ajuste crecimiento (escenario)", fp(aj["d_crec"])),
        ("Ajuste margen EBIT (escenario)", fp(aj["d_margen"])),
        ("Ajuste WACC (escenario)", fp(aj["d_wacc"])),
        ("Escenario", escenario),
    ]
    for i in range(0, len(pares), 2):
        a = pares[i]
        b = pares[i + 1] if i + 1 < len(pares) else ("", "")
        filas.append([a[0], a[1], b[0], b[1]])
    t = _tabla(filas, [5 * cm, 3 * cm, 5 * cm, 3 * cm])
    t.setStyle(TableStyle([("ALIGN", (2, 0), (2, -1), "LEFT")]))
    el.append(t)

    # 4. Modelo financiero
    seccion(4, "Modelo financiero")
    el.append(Paragraph(
        "Flujo de caja libre de la firma (FCFF) descontado al WACC. Cadena de cálculo: "
        "<b>Beta → WACC → Flujos → Valor terminal → Enterprise Value → Equity Value → Valor por acción</b>. "
        "Las ventas crecen con la g del sector ANTAD (g = a·e<super>b·x</super>, x = 6 a 10) más el ajuste del "
        "escenario; EBIT = ingresos × margen; NOPAT = EBIT × (1 − tasa NOPAT); "
        "FCFF = NOPAT + D&amp;A − CAPEX − ΔCTNO. El valor terminal usa Gordon: FCFF<sub>2030</sub>×(1+g)/(WACC−g).",
        txt))
    el.append(Spacer(1, 4))
    proy = r["proyeccion"]
    renglones = [("Crecimiento de ventas", "p"), ("Ingresos", "m"), ("EBIT", "m"), ("NOPAT", "m"),
                 ("D&A", "m"), ("CAPEX", "m"), ("Δ Capital de trabajo", "m"), ("FCFF", "m")]
    filas = [["mdp"] + [str(a) for a in proy.columns]]
    for nombre, tipo in renglones:
        filas.append([nombre] + [fp(x) if tipo == "p" else fm(x) for x in proy.loc[nombre]])
    filas.append(["Factor de descuento"] + [f"{f:.4f}" for f in v["factores"]])
    filas.append(["VP del FCFF"] + [fm(x) for x in v["vp_fcff"]])
    el.append(_tabla(filas, [4.6 * cm] + [2.3 * cm] * 5))
    el.append(Spacer(1, 4))
    el.append(Image(grafica_fcff(proy), width=13 * cm, height=5.2 * cm))

    # 5. Beta
    seccion(5, "Beta")
    el.append(Paragraph(
        f"Regresión de {est['n_rendimientos']:,} rendimientos diarios de SORIANA B contra el S&amp;P/BMV IPC "
        f"(31-mar-2021 a 31-mar-2026). Beta calculada {est['beta']:.6f}; beta usada "
        f"<b>{cc['beta']['usado']:.6f}</b>. R² {est['r2']:.5f}, alfa diaria {est['alfa']:.6f}, "
        f"correlación {est['correlacion']:.4f}. Rm = {fp(cc['rm']['usado'])}; Rf = {fp(cc['rf']['usado'])} "
        f"(método {p['metodo_rf']}); prima de riesgo {fp(cc['prima']['usado'])}.", txt))

    # 6. WACC
    seccion(6, "WACC")
    filas = [["Componente", "Valor"],
             ["Ke = Rf + β × (Rm − Rf)", fp(cc["ke"], 4)],
             ["Kd (promedio ponderado de 4 fuentes)", fp(cc["kd"]["usado"], 4)],
             ["Tasa del arrendamiento implícita", fp(cc["kd_info"]["tasa_arrendamiento"], 4)],
             ["ISR", fp(cc["isr"])],
             ["D / (D + E)", fp(cc["wd"])],
             ["E / (D + E)", fp(cc["we"])],
             ["WACC (valor en libros)", fp(cc["wacc"]["usado"], 4)],
             ["Ajuste del escenario", fp(aj["d_wacc"])],
             ["WACC usado en la valuación", fp(v["wacc"], 4)],
             ["Referencia: WACC con capital a mercado", fp(cc["wacc_mercado"], 4)]]
    el.append(_tabla(filas, [8 * cm, 4 * cm]))

    # 7–11. Resultados
    seccion(7, "Crecimiento perpetuo")
    el.append(Paragraph(
        f"g = inflación de largo plazo {fp(p['inflacion_lp'])} + crecimiento real {fp(p['crec_real'])} = "
        f"{fp(r['g']['calculado'])}; g usada <b>{fp(v['g'])}</b>. "
        + ("Se cumple WACC &gt; g." if v["valido"] else
           "<font color='#C62828'>Aviso: WACC ≤ g, no se calcula el valor terminal.</font>"), txt))
    seccion(8, "Valor terminal")
    el.append(Paragraph(
        f"VT = FCFF<sub>2030</sub> × (1 + g) / (WACC − g) = <b>{fm(v['valor_terminal'])} mdp</b>; "
        f"valor presente {fm(v['vp_valor_terminal'])} mdp ({fp(v['peso_vt'], 1)} del EV).", txt))
    seccion(9, "Enterprise Value")
    el.append(Paragraph(
        f"EV = Σ VP FCFF {fm(v['suma_vp_fcff'])} + VP del VT {fm(v['vp_valor_terminal'])} = "
        f"<b>{fm(v['enterprise_value'])} mdp</b>.", txt))
    seccion(10, "Equity Value")
    pu = v["puente"]
    el.append(Paragraph(
        f"Equity = EV + efectivo {fm(pu['efectivo'], 0)} + asociadas {fm(pu['asociadas'], 0)} − deuda "
        f"{fm(-pu['deuda'], 0)} − arrendamiento {fm(-pu['arrendamiento'], 0)} − no controladora "
        f"{fm(-pu['no_controladora'], 0)} = <b>{fm(v['equity_value'])} mdp</b>.", txt))
    seccion(11, "Valor por acción")
    dif = v["diferencia_precio"]
    color = VERDE if (dif or 0) >= 0 else ROJO
    el.append(Paragraph(
        f"Valor por acción = Equity / {fm(p['acciones'], 0)} millones de acciones = "
        f"<b>{fd(v['valor_por_accion'])}</b>. Frente al precio de mercado de {fd(p['precio_mercado'])} la "
        f"diferencia es <font color='{color}'><b>{'+' if (dif or 0) >= 0 else ''}{fp(dif, 1)}</b></font>.",
        txt))

    # 12–14. Escenarios
    for n, e in zip((12, 13, 14), m.ESCENARIOS):
        re_ = esc["resultados"][e]
        ve = re_["valuacion"]
        a = re_["ajustes"]
        nombre = "Escenario conservador" if e == "Conservador" else f"Escenario {e.lower()}"
        seccion(n, nombre)
        el.append(Paragraph(
            f"{p['justificaciones'][e]} Ajustes: crecimiento {fp(a['d_crec'])}, margen EBIT "
            f"{fp(a['d_margen'])}, WACC {fp(a['d_wacc'])}; probabilidad {fp(a['prob'], 0)}. "
            f"WACC {fp(ve['wacc'])}, FCFF 2030 {fm(ve['fcff'][-1])}, VT {fm(ve['valor_terminal'])}, "
            f"EV {fm(ve['enterprise_value'])}, Equity {fm(ve['equity_value'])}, "
            f"valor por acción <b>{fd(ve['valor_por_accion'])}</b>.", txt))
    el.append(Spacer(1, 4))
    filas = [["Concepto"] + m.ESCENARIOS]
    formatos = {"Inflación": fp, "Crecimiento": fp, "Beta": lambda x: f"{x:.4f}", "WACC": fp,
                "Crecimiento perpetuo": fp, "Valor por acción": fd}
    for fila in comp.index:
        f = formatos.get(fila, fm)
        filas.append([fila] + [f(comp.loc[fila, e]) for e in m.ESCENARIOS])
    el.append(_tabla(filas, [5.5 * cm, 3.3 * cm, 3.3 * cm, 3.3 * cm]))
    el.append(Paragraph(f"Valor ponderado por probabilidad: <b>{fd(esc['ponderado'])}</b>.", txt))

    # 15. Gráficas
    el.append(PageBreak())
    seccion(15, "Gráficas")
    el.append(Image(grafica_inflacion(infl), width=16 * cm, height=6.4 * cm))
    el.append(Image(grafica_ipc(ipc), width=16 * cm, height=5.9 * cm))
    el.append(Image(grafica_escenarios(esc, p["precio_mercado"]), width=13.5 * cm, height=5.8 * cm))
    el.append(Image(grafica_sensibilidad(mat, v["wacc"], v["g"]), width=14 * cm, height=7 * cm))
    if tor.attrs["base"] is not None:
        el.append(Image(grafica_tornado(tor), width=15 * cm, height=7.8 * cm))
    else:
        el.append(Paragraph("El tornado no se calcula porque el WACC no supera a g.", txt))
    reg = infl["regresion"]
    el.append(Paragraph(
        f"Correlación precio–inflación anual {infl['correlacion']:.4f}; regresión precio = "
        f"{reg['intercepto']:.2f} {reg['pendiente_por_pp']:+.3f} × inflación (pp), R² {reg['r2']:.3f}. "
        f"Correlación de rendimientos mensuales SORIANA–IPC {ipc['regresion']['correlacion']:.4f}.", txt))

    # 16. Validación
    seccion(16, "Validación contra Excel")
    filas = [["Variable", "Excel", "App", "Diferencia", "Dif. %", "Estado"]]
    for _, f in val.iterrows():
        es_tasa = f["Variable"] in ("WACC", "g")
        fmt = (lambda x: fp(x, 4)) if es_tasa else (fd if "acción" in f["Variable"] else fm)
        filas.append([Paragraph(f["Variable"], txt), fmt(f["Excel"]), fmt(f["App"]),
                      f"{f['Diferencia']:.2e}", f"{f['Diferencia %'] * 100:.2e}%", f["Estado"]])
    t = _tabla(filas, [5.6 * cm, 2.4 * cm, 2.4 * cm, 2 * cm, 2.2 * cm, 1.4 * cm])
    for i, f in enumerate(val.itertuples(), start=1):
        t.setStyle(TableStyle([("TEXTCOLOR", (5, i), (5, i),
                                colors.HexColor(VERDE if f.Estado == "PASS" else ROJO))]))
    el.append(KeepTogether([t]))
    el.append(Paragraph(
        f"Fuente de los valores del Excel: {val.attrs['fuente']}. La validación usa siempre los valores "
        f"default. Criterio: PASS si la diferencia es menor a 0.01%. Las diferencias residuales vienen de la "
        f"precisión de punto flotante. Si el WACC se redondea a {fp(red['wacc_redondeado'])} el valor por "
        f"acción sale {fd(red['valor_por_accion'])} en lugar de {fd(val.iloc[5]['Excel'])}, por eso la app "
        f"trabaja con el WACC sin redondear.", txt))

    # 17. Conclusiones
    seccion(17, "Conclusiones")
    interp = m.interpretacion_escenarios(p, data, est, esc).replace("**", "")
    if v["valor_por_accion"] is not None:
        postura = ("subvaluada" if v["valor_por_accion"] > p["precio_mercado"] else "sobrevaluada")
        concl = (
            f"Con los supuestos del escenario {escenario.lower()}, el valor intrínseco de SORIANA B es "
            f"{fd(v['valor_por_accion'])} por acción, {fp(abs(dif), 1)} "
            f"{'por encima' if dif >= 0 else 'por debajo'} del precio de {fd(p['precio_mercado'])}, por lo que "
            f"la acción luce {postura}. El valor terminal explica {fp(v['peso_vt'], 1)} del EV, lo que hace "
            f"que el resultado dependa sobre todo del diferencial WACC − g. La beta diaria "
            f"({cc['beta']['usado']:.4f}) es baja y tiene un R² de {est['r2']:.4f}, por lo que el Ke podría "
            f"subestimar el riesgo; el escenario conservador lo compensa con un WACC más alto. {interp}"
        )
    else:
        concl = "Con los supuestos actuales el WACC no supera a g, por lo que el modelo no es válido."
    el.append(Paragraph(concl, txt))
    el.append(Spacer(1, 10))
    el.append(Paragraph(" · ".join(f"{i['nombre']} {i['matricula']}" for i in emp["equipo"]), centro))

    doc.build(el)
    return buf.getvalue()
