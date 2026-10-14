"""Aplicación de valuación de Organización Soriana (SORIANA B).

Ejecutar con:  streamlit run app.py
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import modelo as m
import reporte_pdf

AZUL = "#1F3864"
AZUL_CLARO = "#8EA3C8"
AZUL_MEDIO = "#4A6699"
GRIS = "#8C8C8C"
VERDE = "#2E7D32"
ROJO = "#C62828"

st.set_page_config(page_title="Valuación SORIANA B", layout="wide")

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{ font-family: "Helvetica Neue", Arial, sans-serif; }}
    h1, h2, h3 {{ color: {AZUL}; font-weight: 600; }}
    .tarjeta {{ border: 1px solid #E0E0E0; border-left: 4px solid {AZUL}; border-radius: 4px;
               padding: 10px 14px; background: #FFFFFF; margin-bottom: 10px; min-height: 84px; }}
    .tarjeta .etq {{ font-size: 0.78rem; color: #595959; text-transform: uppercase; letter-spacing: .03em; }}
    .tarjeta .val {{ font-size: 1.45rem; font-weight: 600; color: {AZUL}; margin-top: 2px; }}
    .tarjeta .sub {{ font-size: 0.78rem; color: #7F7F7F; }}
    .pos {{ color: {VERDE} !important; }}
    .neg {{ color: {ROJO} !important; }}
    thead tr th {{ background-color: #F2F2F2 !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Datos y cálculos que no dependen de las variables editables
# ---------------------------------------------------------------------------

@st.cache_data
def datos():
    return m.cargar_datos()


@st.cache_data
def estadisticas():
    return m.estadisticas_beta(datos())


@st.cache_data
def inflacion():
    return m.analisis_inflacion(datos())


@st.cache_data
def ipc():
    return m.analisis_ipc(datos())


@st.cache_data
def validacion_excel():
    return m.validacion(datos(), estadisticas()), m.efecto_redondeo_wacc(datos(), estadisticas())


DATA = datos()
EST = estadisticas()
DEF = m.parametros_default(DATA)


# ---------------------------------------------------------------------------
# Formatos
# ---------------------------------------------------------------------------

def fm(v, dec=1):
    return "n.d." if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:,.{dec}f}"


def fp(v, dec=2):
    return "n.d." if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v * 100:,.{dec}f}%"


def fd(v, dec=2):
    return "n.d." if v is None or (isinstance(v, float) and np.isnan(v)) else f"${v:,.{dec}f}"


def layout(fig, titulo=None, alto=360):
    fig.update_layout(
        template="plotly_white",
        title=dict(text=titulo, font=dict(color=AZUL, size=14)) if titulo else None,
        height=alto,
        margin=dict(l=10, r=10, t=45 if titulo else 15, b=10),
        font=dict(family="Helvetica Neue, Arial, sans-serif", size=12),
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0),
    )
    return fig


_CONTADOR = {"n": 0}


def kgraf():
    """Clave única por gráfica (evita IDs duplicados de Streamlit)."""
    _CONTADOR["n"] += 1
    return f"graf_{_CONTADOR['n']}"


def esc_md(texto: str) -> str:
    """Evita que Streamlit interprete el signo $ como LaTeX."""
    return texto.replace("$", "\\$")


def tarjeta(col, etiqueta, valor, sub="", clase=""):
    valor, sub = str(valor).replace("$", "&#36;"), str(sub).replace("$", "&#36;")
    col.markdown(
        f"<div class='tarjeta'><div class='etq'>{etiqueta}</div>"
        f"<div class='val {clase}'>{valor}</div><div class='sub'>{sub}</div></div>",
        unsafe_allow_html=True,
    )


def tabla_html(df: pd.DataFrame):
    st.dataframe(df, width="stretch")


# ---------------------------------------------------------------------------
# Barra lateral: variables
# ---------------------------------------------------------------------------

PREFIJO = "w_"


def restablecer():
    for k in list(st.session_state.keys()):
        if k.startswith(PREFIJO):
            del st.session_state[k]


def num(label, clave, default, pct=False, paso=None, fmt=None, minimo=None, ayuda=None):
    """Número editable. Si pct=True se muestra en % y se devuelve en decimal."""
    k = PREFIJO + clave
    st.session_state.setdefault(k, float(default * 100 if pct else default))
    v = st.number_input(label, key=k, step=paso or (0.01 if pct else 1.0),
                        format=fmt or ("%.4f" if pct else "%.2f"), min_value=minimo, help=ayuda)
    return v / 100 if pct else v


def manual(label, clave, calculado, pct=True, fmt="%.4f", paso=None, mostrar_dec=4):
    """Patrón calculado / manual / usado del Excel."""
    kc, kv = PREFIJO + clave + "_usar", PREFIJO + clave + "_valor"
    st.session_state.setdefault(kc, False)
    st.session_state.setdefault(kv, float(calculado * 100 if pct else calculado))
    texto = fp(calculado, mostrar_dec) if pct else f"{calculado:,.{mostrar_dec}f}"
    st.markdown(f"**{label}** · calculado: `{texto}`")
    usar = st.checkbox("Valor manual", key=kc)
    v = st.number_input(f"{label} manual" + (" (%)" if pct else ""), key=kv, format=fmt,
                        step=paso or (0.01 if pct else 0.01), disabled=not usar,
                        label_visibility="collapsed")
    if not usar:
        return None
    return v / 100 if pct else v


with st.sidebar:
    st.markdown(f"<h2 style='margin-bottom:0'>SORIANA B</h2>"
                f"<div style='color:#595959;font-size:.85rem'>Valuación por FCFF · "
                f"{DATA['empresa']['estudiante']}</div>", unsafe_allow_html=True)
    st.button("Restablecer valores del Excel", on_click=restablecer, width="stretch")

    st.session_state.setdefault(PREFIJO + "escenario", "Base")
    escenario = st.selectbox("Escenario", m.ESCENARIOS, key=PREFIJO + "escenario")

    p = copy.deepcopy(DEF)
    ajuste = m.ajuste_antad(DATA)

    with st.expander("Económicas", expanded=False):
        p["inflacion_lp"] = num("Inflación de largo plazo (%)", "inflacion_lp", DEF["inflacion_lp"], pct=True,
                                fmt="%.2f", paso=0.25, ayuda="Meta de Banxico: 3%.")
        p["crec_real"] = num("Crecimiento real (%)", "crec_real", DEF["crec_real"], pct=True, fmt="%.2f",
                             paso=0.25)
        st.caption(f"g perpetuo calculado = {fp(p['inflacion_lp'] + p['crec_real'])}")
        st.session_state.setdefault(PREFIJO + "trasladar", False)
        p["trasladar_inflacion_rf"] = st.checkbox("Trasladar cambios de inflación a Rf", key=PREFIJO + "trasladar",
                                                  help="Cada punto que la inflación suba sobre 3% se suma a Rf.")
        p["antad_a_manual"] = manual("g del sector: a", "antad_a", ajuste["a"], pct=False, mostrar_dec=6,
                                     fmt="%.6f", paso=0.001)
        p["antad_b_manual"] = manual("g del sector: b", "antad_b", ajuste["b"], pct=False, mostrar_dec=6,
                                     fmt="%.6f", paso=0.001)

    with st.expander("Mercado", expanded=False):
        p["precio_mercado"] = num("Precio de mercado ($)", "precio", DEF["precio_mercado"], minimo=0.01)
        p["beta_manual"] = manual("Beta", "beta", EST["beta"], pct=False, mostrar_dec=6, fmt="%.6f",
                                  paso=0.01)
        st.session_state.setdefault(PREFIJO + "metodo_rf", 1)
        p["metodo_rf"] = st.radio(
            "Método de Rf", [1, 2, 3], key=PREFIJO + "metodo_rf", horizontal=True,
            format_func=lambda i: f"M{i}",
            help="M1: promedio del cambio % diario del bono × 252. M2: promedio del nivel del bono / 100. "
                 "M3: último nivel del bono / 100.")
        p["rf_manual"] = manual("Rf", "rf", EST["rf_metodos"][p["metodo_rf"]])
        p["rm_manual"] = manual("Rm", "rm", EST["rm"])
        cc_tmp = m.costo_capital(p, EST)
        p["prima_manual"] = manual("Prima de riesgo (Rm − Rf)", "prima", cc_tmp["prima"]["calculado"])

    with st.expander("Financieras", expanded=False):
        p["ingresos_base"] = num("Ingresos base 2025 (mdp)", "ingresos", DEF["ingresos_base"], fmt="%.0f",
                                 paso=100.0)
        p["margen_ebit"] = num("Margen EBIT (%)", "margen", DEF["margen_ebit"], pct=True)
        p["tasa_nopat"] = num("Tasa de impuestos NOPAT (%)", "tasa_nopat", DEF["tasa_nopat"], pct=True,
                              ayuda="Mediana de la tasa efectiva 2021–2025.")
        p["capex_ingresos"] = num("CAPEX / ingresos (%)", "capex", DEF["capex_ingresos"], pct=True)
        p["da_activo_fijo"] = num("D&A / activo fijo (%)", "da", DEF["da_activo_fijo"], pct=True)
        p["ctno_ingresos"] = num("Capital de trabajo / ingresos (%)", "ctno", DEF["ctno_ingresos"], pct=True)
        p["crec_arrendamiento"] = num("Crecimiento del pasivo por arrendamiento (%)", "crec_arr",
                                      DEF["crec_arrendamiento"], pct=True)
        p["pagos_arr_pasivo"] = num("Pagos de arrendamiento / pasivo (%)", "pagos_arr",
                                    DEF["pagos_arr_pasivo"], pct=True)
        p["activo_fijo_base"] = num("Activo fijo neto 2025 (mdp)", "af", DEF["activo_fijo_base"], fmt="%.0f")
        p["pasivo_arr_base"] = num("Pasivo por arrendamiento 2025 (mdp)", "pasivo_arr", DEF["pasivo_arr_base"],
                                   fmt="%.0f")
        p["ctno_base"] = num("Capital de trabajo 2025 (mdp)", "ctno_base", DEF["ctno_base"], fmt="%.0f")
        p["deuda_wacc"] = num("Deuda con costo D (mdp)", "deuda", DEF["deuda_wacc"], fmt="%.0f", minimo=0.0)
        p["capital_wacc"] = num("Capital contable E (mdp)", "capital", DEF["capital_wacc"], fmt="%.0f",
                                minimo=0.0)
        kd_calc = m.calcular_kd(p["fuentes_deuda"], p["gastos_financieros_trim"])["kd"]
        p["kd_manual"] = manual("Kd", "kd", kd_calc)
        p["isr"] = num("ISR (%)", "isr", DEF["isr"], pct=True, fmt="%.2f")
        cc_tmp = m.costo_capital(p, EST)
        p["wacc_manual"] = manual("WACC", "wacc", cc_tmp["wacc"]["calculado"])

    with st.expander("Valuación", expanded=False):
        p["g_manual"] = manual("Crecimiento perpetuo g", "g", p["inflacion_lp"] + p["crec_real"])
        p["acciones"] = num("Acciones (millones)", "acciones", DEF["acciones"], fmt="%.0f", minimo=1.0)
        st.markdown("**Puente a Equity (mdp)**")
        p["efectivo"] = num("Efectivo", "efectivo", DEF["efectivo"], fmt="%.0f")
        p["asociadas"] = num("Inversión en asociadas", "asociadas", DEF["asociadas"], fmt="%.0f")
        p["deuda_puente"] = num("Deuda bursátil y bancaria", "deuda_puente", DEF["deuda_puente"], fmt="%.0f")
        p["arrendamiento_puente"] = num("Pasivo por arrendamiento", "arr_puente", DEF["arrendamiento_puente"],
                                        fmt="%.0f")
        p["no_controladora"] = num("Participación no controladora", "no_contr", DEF["no_controladora"],
                                   fmt="%.0f")

    with st.expander("Ajustes de escenarios", expanded=False):
        for e in m.ESCENARIOS:
            st.markdown(f"**{e}**")
            d = DEF["escenarios"][e]
            p["escenarios"][e] = {
                "d_crec": num("Δ crecimiento de ventas (pp)", f"{e}_dcrec", d["d_crec"], pct=True, fmt="%.2f",
                              paso=0.25),
                "d_margen": num("Δ margen EBIT (pp)", f"{e}_dmargen", d["d_margen"], pct=True, fmt="%.2f",
                                paso=0.1),
                "d_wacc": num("Δ WACC (pp)", f"{e}_dwacc", d["d_wacc"], pct=True, fmt="%.2f", paso=0.25),
                "prob": num("Probabilidad (%)", f"{e}_prob", d["prob"], pct=True, fmt="%.0f", paso=5.0,
                            minimo=0.0),
            }

    for e in m.ESCENARIOS:
        st.session_state.setdefault(PREFIJO + f"just_{e}", m.JUSTIFICACIONES_DEFAULT[e])
        p["justificaciones"][e] = st.session_state[PREFIJO + f"just_{e}"]


# ---------------------------------------------------------------------------
# Cálculo de toda la cadena
# ---------------------------------------------------------------------------

R = m.modelo_completo(p, DATA, EST, escenario)
CC = R["costo_capital"]
V = R["valuacion"]
ESC = m.todos_escenarios(p, DATA, EST)
INF = inflacion()
IPC = ipc()

st.markdown(f"<h1 style='margin-bottom:0'>Valuación de {DATA['empresa']['nombre']} ({DATA['empresa']['emisora']})</h1>"
            f"<div style='color:#595959'>{DATA['empresa']['curso']} · Tecnológico de Monterrey · "
            f"{DATA['empresa']['estudiante']} ({DATA['empresa']['matricula']}) · Cifras en millones de pesos</div>",
            unsafe_allow_html=True)
st.write("")

if not V["valido"]:
    st.warning(f"El WACC ({fp(V['wacc'])}) no es mayor que el crecimiento perpetuo g ({fp(V['g'])}). "
               "No se calcula el valor terminal; ajusta las variables.")
if abs(ESC["suma_prob"] - 1) > 1e-9:
    st.info(f"Las probabilidades de los escenarios suman {fp(ESC['suma_prob'], 0)}, no 100%.")

tabs = st.tabs(["Dashboard", "Inflación y mercado", "Beta y WACC", "Proyección y valuación", "Escenarios",
                "Sensibilidad", "Validación contra Excel", "Reporte PDF"])


# ---------------------------------------------------------------------------
# Gráficas reutilizables
# ---------------------------------------------------------------------------

def fig_inflacion_activo():
    s = INF["serie"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=s.index, y=s["soriana"], name="Precio SORIANA B ($)",
                             line=dict(color=AZUL, width=2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=s.index, y=s["inflacion_anual"] * 100, name="Inflación anual (%)",
                             line=dict(color=GRIS, width=1.5, dash="dash")), secondary_y=True)
    fig.update_yaxes(title_text="Precio ($)", secondary_y=False)
    fig.update_yaxes(title_text="Inflación anual (%)", secondary_y=True, showgrid=False)
    return layout(fig, "Inflación vs activo")


def fig_ipc_activo():
    s = IPC["serie"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s["base100_soriana"], name="SORIANA B", line=dict(color=AZUL, width=2)))
    fig.add_trace(go.Scatter(x=s.index, y=s["base100_ipc"], name="S&P/BMV IPC", line=dict(color=GRIS, width=1.5)))
    fig.update_yaxes(title_text="Base 100 (nov-2021)")
    return layout(fig, "IPC vs activo (base 100)")


def fig_escenarios():
    vals = [ESC["resultados"][e]["valuacion"]["valor_por_accion"] for e in m.ESCENARIOS]
    fig = go.Figure(go.Bar(x=m.ESCENARIOS, y=[v or 0 for v in vals], marker_color=[AZUL_CLARO, AZUL, AZUL_MEDIO],
                           text=[fd(v) for v in vals], textposition="outside", name="Valor por acción", showlegend=False))
    fig.add_trace(go.Scatter(x=m.ESCENARIOS, y=[p["precio_mercado"]] * 3, mode="lines",
                             name=f"Precio de mercado {fd(p['precio_mercado'])}",
                             line=dict(color=ROJO, dash="dash", width=1.5)))
    if ESC["ponderado"] is not None:
        fig.add_trace(go.Scatter(x=m.ESCENARIOS, y=[ESC["ponderado"]] * 3, mode="lines",
                                 name=f"Valor ponderado {fd(ESC['ponderado'])}",
                                 line=dict(color=GRIS, dash="dot", width=1.5)))
    fig.update_yaxes(title_text="$ por acción")
    return layout(fig, "Escenarios vs precio de mercado")


def fig_valor_accion():
    cats = ["Precio de mercado", f"Valor estimado ({escenario})", "Valor ponderado"]
    vals = [p["precio_mercado"], V["valor_por_accion"], ESC["ponderado"]]
    fig = go.Figure(go.Bar(x=cats, y=[v or 0 for v in vals], marker_color=[GRIS, AZUL, AZUL_MEDIO],
                           text=[fd(v) for v in vals], textposition="outside"))
    fig.update_yaxes(title_text="$ por acción")
    return layout(fig, "Valor por acción")


def matriz():
    return m.matriz_sensibilidad(p, DATA, EST, escenario)


def fig_heatmap(mat):
    z = mat.values.astype(float)
    texto = [[fd(v) if not np.isnan(v) else "n.d." for v in fila] for fila in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{g * 100:.1f}%" for g in mat.columns], y=[f"{w * 100:.2f}%" for w in mat.index],
        text=texto, texttemplate="%{text}", colorscale=[[0, "#F2F5FA"], [1, AZUL]], showscale=False,
        hovertemplate="WACC %{y}<br>g %{x}<br>%{text}<extra></extra>"))
    # Celda base resaltada
    i = int(np.argmin(np.abs(mat.index.values - V["wacc"])))
    gs = np.array(mat.columns, dtype=float)
    if np.min(np.abs(gs - V["g"])) < 1e-9:
        j = int(np.argmin(np.abs(gs - V["g"])))
        fig.add_shape(type="rect", x0=j - 0.5, x1=j + 0.5, y0=i - 0.5, y1=i + 0.5,
                      line=dict(color=ROJO, width=3))
    fig.update_xaxes(title_text="Crecimiento perpetuo (g)", side="bottom")
    fig.update_yaxes(title_text="WACC", autorange="reversed")
    return layout(fig, "Sensibilidad WACC – g (valor por acción)")


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------

with tabs[0]:
    dif = V["diferencia_precio"]
    clase = "" if dif is None else ("pos" if dif >= 0 else "neg")
    c = st.columns(5)
    tarjeta(c[0], "Precio de mercado", fd(p["precio_mercado"]), DATA["empresa"]["fecha_precio"])
    tarjeta(c[1], "Valor estimado por acción", fd(V["valor_por_accion"]), f"Escenario {escenario}")
    tarjeta(c[2], "Diferencia vs precio", ("n.d." if dif is None else f"{'+' if dif >= 0 else ''}{fp(dif, 1)}"),
            "Potencial de subida" if (dif or 0) >= 0 else "Potencial de baja", clase)
    tarjeta(c[3], "Beta", f"{CC['beta']['usado']:.4f}", "manual" if p["beta_manual"] is not None else "calculada")
    tarjeta(c[4], "WACC", fp(V["wacc"]), f"Ke {fp(CC['ke'])} · Kd {fp(CC['kd']['usado'])}")
    c = st.columns(5)
    tarjeta(c[0], "Crecimiento perpetuo g", fp(V["g"]), f"Inflación {fp(p['inflacion_lp'])} + real {fp(p['crec_real'])}")
    tarjeta(c[1], "Valor terminal", fm(V["valor_terminal"]), f"Peso en EV: {fp(V['peso_vt'], 1)}")
    tarjeta(c[2], "Enterprise Value", fm(V["enterprise_value"]), "mdp")
    tarjeta(c[3], "Equity Value", fm(V["equity_value"]), "mdp")
    tarjeta(c[4], "Escenario seleccionado", escenario,
            f"Valor ponderado: {fd(ESC['ponderado'])}")

    c1, c2 = st.columns(2)
    c1.plotly_chart(key=kgraf(), figure_or_data=fig_inflacion_activo(), width="stretch")
    c2.plotly_chart(key=kgraf(), figure_or_data=fig_ipc_activo(), width="stretch")
    c1, c2 = st.columns(2)
    c1.plotly_chart(key=kgraf(), figure_or_data=fig_escenarios(), width="stretch")
    c2.plotly_chart(key=kgraf(), figure_or_data=fig_valor_accion(), width="stretch")
    st.plotly_chart(key=kgraf(), figure_or_data=fig_heatmap(matriz()), width="stretch")


# ---------------------------------------------------------------------------
# 2. Inflación y mercado
# ---------------------------------------------------------------------------

with tabs[1]:
    st.subheader("Inflación (INPC de Banxico)")
    inf_c = INF["inflacion_completa"].dropna(subset=["inflacion_mensual"])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=inf_c.index, y=inf_c["inflacion_anual"] * 100, name="Inflación anual (%)",
                             line=dict(color=AZUL, width=2)), secondary_y=False)
    fig.add_trace(go.Bar(x=inf_c.index, y=inf_c["inflacion_mensual"] * 100, name="Inflación mensual (%)",
                         marker_color=AZUL_CLARO, opacity=0.7), secondary_y=True)
    fig.update_yaxes(title_text="Anual (%)", secondary_y=False)
    fig.update_yaxes(title_text="Mensual (%)", secondary_y=True, showgrid=False)
    st.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Inflación anual y mensual"), width="stretch")

    st.subheader("Precio de SORIANA B vs inflación anual (nov-2021 a sep-2026)")
    reg = INF["regresion"]
    s = INF["serie"]
    c = st.columns(4)
    tarjeta(c[0], "Correlación", f"{INF['correlacion']:.4f}", f"{len(s)} meses")
    tarjeta(c[1], "Intercepto", f"{reg['intercepto']:.2f}", "pesos")
    tarjeta(c[2], "Pendiente", f"{reg['pendiente_por_pp']:.3f}", "pesos por punto porcentual")
    tarjeta(c[3], "R²", f"{reg['r2']:.3f}")
    c1, c2 = st.columns(2)
    c1.plotly_chart(key=kgraf(), figure_or_data=fig_inflacion_activo(), width="stretch")
    xs = np.linspace(s["inflacion_anual"].min(), s["inflacion_anual"].max(), 50)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s["inflacion_anual"] * 100, y=s["soriana"], mode="markers", name="Observado",
                             marker=dict(color=AZUL, size=7)))
    fig.add_trace(go.Scatter(x=xs * 100, y=reg["intercepto"] + reg["pendiente"] * xs, name="Regresión",
                             line=dict(color=GRIS, dash="dash")))
    fig.update_xaxes(title_text="Inflación anual (%)")
    fig.update_yaxes(title_text="Precio ($)")
    c2.plotly_chart(key=kgraf(), figure_or_data=layout(fig, f"Precio = {reg['intercepto']:.2f} {reg['pendiente_por_pp']:+.3f} × inflación (pp)"),
                    width="stretch")

    st.subheader("Tendencias contra el tiempo (x = 1 en nov-2021)")
    tl, te = INF["tendencia_precio_lineal"], INF["tendencia_precio_exponencial"]
    il, ie = INF["tendencia_inflacion_lineal"], INF["tendencia_inflacion_exponencial"]
    x = s["x"].values
    c1, c2 = st.columns(2)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=s["soriana"], mode="markers", name="Precio", marker=dict(color=AZUL, size=6)))
    fig.add_trace(go.Scatter(x=x, y=tl["intercepto"] + tl["pendiente"] * x, name="Lineal",
                             line=dict(color=GRIS)))
    fig.add_trace(go.Scatter(x=x, y=te["a"] * np.exp(te["b"] * x), name="Exponencial",
                             line=dict(color=AZUL_MEDIO, dash="dash")))
    fig.update_xaxes(title_text="x (mes)")
    c1.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Precio de SORIANA B"), width="stretch")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=s["inflacion_anual"] * 100, mode="markers", name="Inflación",
                             marker=dict(color=AZUL, size=6)))
    fig.add_trace(go.Scatter(x=x, y=(il["intercepto"] + il["pendiente"] * x) * 100, name="Lineal",
                             line=dict(color=GRIS)))
    fig.add_trace(go.Scatter(x=x, y=ie["a"] * np.exp(ie["b"] * x) * 100, name="Exponencial",
                             line=dict(color=AZUL_MEDIO, dash="dash")))
    fig.update_xaxes(title_text="x (mes)")
    fig.update_yaxes(title_text="%")
    c2.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Inflación anual"), width="stretch")
    modelos = pd.DataFrame([
        ["Precio", "Lineal", f"y = {tl['intercepto']:.4f} + {tl['pendiente']:.4f}·x", f"{tl['r2']:.4f}"],
        ["Precio", "Exponencial", f"y = {te['a']:.4f}·e^({te['b']:.5f}·x)", f"{te['r2']:.4f}"],
        ["Inflación anual", "Lineal", f"y = {il['intercepto']:.5f} + {il['pendiente']:.6f}·x", f"{il['r2']:.4f}"],
        ["Inflación anual", "Exponencial", f"y = {ie['a']:.5f}·e^({ie['b']:.5f}·x)", f"{ie['r2']:.4f}"],
    ], columns=["Serie", "Modelo", "Ecuación", "R²"])
    st.dataframe(modelos, hide_index=True, width="stretch")

    pr = INF["pronostico"]
    st.markdown(f"**Pronóstico de oct-2026 (x = {pr['x']}) contra el valor observado de {esc_md(fd(pr['observado']))}**")
    st.dataframe(pd.DataFrame([
        {"Modelo": k, "Pronóstico": fd(v), "Observado": fd(pr["observado"]),
         "Error": fd(v - pr["observado"]), "Error %": fp(v / pr["observado"] - 1)}
        for k, v in pr["modelos"].items()]), hide_index=True, width="stretch")

    st.subheader("SORIANA B vs S&P/BMV IPC (rendimientos mensuales)")
    rg = IPC["regresion"]
    c = st.columns(3)
    tarjeta(c[0], "Correlación", f"{rg['correlacion']:.4f}", f"{rg['n']} rendimientos")
    tarjeta(c[1], "Pendiente (beta mensual)", f"{rg['pendiente']:.4f}")
    tarjeta(c[2], "R²", f"{rg['r2']:.4f}")
    c1, c2 = st.columns(2)
    c1.plotly_chart(key=kgraf(), figure_or_data=fig_ipc_activo(), width="stretch")
    si = IPC["serie"].dropna()
    xs = np.linspace(si["rend_ipc"].min(), si["rend_ipc"].max(), 20)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=si["rend_ipc"] * 100, y=si["rend_soriana"] * 100, mode="markers",
                             name="Meses", marker=dict(color=AZUL, size=7)))
    fig.add_trace(go.Scatter(x=xs * 100, y=(rg["intercepto"] + rg["pendiente"] * xs) * 100, name="Regresión",
                             line=dict(color=GRIS, dash="dash")))
    fig.update_xaxes(title_text="Rendimiento IPC (%)")
    fig.update_yaxes(title_text="Rendimiento SORIANA B (%)")
    c2.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Rendimientos mensuales"), width="stretch")


# ---------------------------------------------------------------------------
# 3. Beta y WACC
# ---------------------------------------------------------------------------

with tabs[2]:
    st.subheader("Beta con rendimientos diarios (31-mar-2021 a 31-mar-2026)")
    c = st.columns(4)
    tarjeta(c[0], "Beta", f"{EST['beta']:.6f}", f"{EST['n_rendimientos']:,} rendimientos")
    tarjeta(c[1], "R²", f"{EST['r2']:.5f}")
    tarjeta(c[2], "Alfa diaria", f"{EST['alfa']:.6f}")
    tarjeta(c[3], "Correlación", f"{EST['correlacion']:.4f}")
    sd = EST["serie"].dropna()
    xs = np.linspace(sd["rend_ipc"].min(), sd["rend_ipc"].max(), 20)
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=sd["rend_ipc"] * 100, y=sd["rend_soriana"] * 100, mode="markers",
                               name="Días", marker=dict(color=AZUL, size=4, opacity=0.45)))
    fig.add_trace(go.Scatter(x=xs * 100, y=(EST["alfa"] + EST["beta"] * xs) * 100,
                             name=f"y = {EST['alfa']:.5f} + {EST['beta']:.4f}x", line=dict(color=ROJO, width=2)))
    fig.update_xaxes(title_text="Rendimiento diario IPC (%)")
    fig.update_yaxes(title_text="Rendimiento diario SORIANA B (%)")
    st.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Regresión de rendimientos diarios", 420), width="stretch")

    st.subheader("Variables: calculado / manual / usado")
    filas = []
    for nombre, clave, es_pct in (("Beta", "beta", False), ("Rf", "rf", True), ("Rm", "rm", True),
                                  ("Prima de riesgo", "prima", True), ("Kd", "kd", True), ("WACC", "wacc", True)):
        d = CC[clave]
        f = (lambda v: fp(v, 4)) if es_pct else (lambda v: f"{v:.6f}")
        filas.append({"Variable": nombre, "Calculado": f(d["calculado"]),
                      "Manual": "" if d["manual"] is None else f(d["manual"]), "Usado": f(d["usado"])})
    st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
    if CC["rf"]["traslado"]:
        st.caption(f"Rf incluye {fp(CC['rf']['traslado'])} por traslado de la inflación sobre 3%.")
    st.markdown("**Métodos de Rf (bono)**")
    st.dataframe(pd.DataFrame([
        {"Método": "1. Promedio del cambio % diario × 252", "Rf": fp(EST["rf_metodos"][1], 4)},
        {"Método": "2. Promedio del nivel / 100", "Rf": fp(EST["rf_metodos"][2], 4)},
        {"Método": "3. Último nivel / 100", "Rf": fp(EST["rf_metodos"][3], 4)},
    ]), hide_index=True, width="stretch")

    st.subheader("Costo de la deuda (fuentes al 2T26)")
    kd = CC["kd_info"]
    deuda = pd.DataFrame([{"Fuente": f["fuente"], "Tipo": f["tipo"], "Monto (mdp)": fm(f["monto"], 0),
                           "Tasa": fp(f["tasa"]), "Peso": fp(f["peso"]), "Interés anual": fm(f["interes"])}
                          for f in kd["tabla"]])
    deuda.loc[len(deuda)] = ["Total", "", fm(kd["total"], 0), fp(kd["kd"]), "100.00%", fm(kd["costo_anual"])]
    st.dataframe(deuda, hide_index=True, width="stretch")
    st.caption(f"Tasa del arrendamiento = ({p['gastos_financieros_trim']:,.0f} × 4 − Σ monto × tasa de las tres "
               f"deudas) / saldo del arrendamiento = {fp(kd['tasa_arrendamiento'])}.")

    st.subheader("Cálculo paso a paso")
    pasos = pd.DataFrame([
        ["1", "Ke = Rf + β × (Rm − Rf)",
         f"{fp(CC['rf']['usado'], 4)} + {CC['beta']['usado']:.4f} × {fp(CC['prima']['usado'], 4)}", fp(CC["ke"], 4)],
        ["2", "Kd (promedio ponderado)", "Σ monto × tasa / Σ monto", fp(CC["kd"]["usado"], 4)],
        ["3", "Kd después de impuestos", f"{fp(CC['kd']['usado'], 4)} × (1 − {fp(CC['isr'])})",
         fp(CC["kd"]["usado"] * (1 - CC["isr"]), 4)],
        ["4", "Pesos", f"D = {fm(CC['d'], 0)}, E = {fm(CC['e'], 0)}",
         f"D/V {fp(CC['wd'])} · E/V {fp(CC['we'])}"],
        ["5", "WACC = E/V × Ke + D/V × Kd × (1 − t)", "", fp(CC["wacc"]["calculado"], 4)],
        ["6", "WACC usado (manual o calculado)", "", fp(CC["wacc"]["usado"], 4)],
        ["7", f"Ajuste del escenario {escenario}", fp(R["ajustes"]["d_wacc"]), fp(V["wacc"], 4)],
    ], columns=["Paso", "Concepto", "Operación", "Resultado"])
    st.dataframe(pasos, hide_index=True, width="stretch")
    st.caption(f"Referencia: con el capital a valor de mercado (precio × {fm(p['acciones'], 0)} millones de "
               f"acciones = {fm(CC['e_mercado'], 0)} mdp) el WACC sería {fp(CC['wacc_mercado'], 4)}. "
               "La valuación usa el capital contable en libros, como el Excel.")


# ---------------------------------------------------------------------------
# 4. Proyección y valuación
# ---------------------------------------------------------------------------

with tabs[3]:
    st.subheader(f"Proyección del FCFF 2026–2030 · escenario {escenario}")
    proy = R["proyeccion"]
    pct_rows = {"Crecimiento de ventas", "Margen EBIT"}
    tabla = pd.DataFrame({str(c): [fp(proy.loc[r, c]) if r in pct_rows else fm(proy.loc[r, c])
                                   for r in proy.index] for c in proy.columns}, index=proy.index)
    base_2025 = {"Ingresos": p["ingresos_base"], "Activo fijo neto": p["activo_fijo_base"],
                 "Pasivo por arrendamiento": p["pasivo_arr_base"],
                 "Capital de trabajo neto operativo": p["ctno_base"]}
    tabla.insert(0, "2025", [fm(base_2025[r]) if r in base_2025 else "" for r in proy.index])
    tabla.loc["Factor de descuento"] = [""] + [f"{f:.4f}" for f in V["factores"]]
    tabla.loc["VP del FCFF"] = [""] + [fm(v) for v in V["vp_fcff"]]
    st.dataframe(tabla, width="stretch", height=640)

    c = st.columns(4)
    tarjeta(c[0], "Σ VP de los flujos", fm(V["suma_vp_fcff"]))
    tarjeta(c[1], "Valor terminal", fm(V["valor_terminal"]), "FCFF2030 × (1+g) / (WACC − g)")
    tarjeta(c[2], "VP del valor terminal", fm(V["vp_valor_terminal"]), f"{fp(V['peso_vt'], 1)} del EV")
    tarjeta(c[3], "Valor por acción", fd(V["valor_por_accion"]),
            f"Equity / {fm(p['acciones'], 0)} millones de acciones")

    if V["valido"]:
        pu = V["puente"]
        etiquetas = ["VP flujos", "VP valor terminal", "Enterprise Value", "Efectivo", "Asociadas", "Deuda",
                     "Arrendamiento", "No controladora", "Equity Value"]
        valores = [V["suma_vp_fcff"], V["vp_valor_terminal"], 0, pu["efectivo"], pu["asociadas"], pu["deuda"],
                   pu["arrendamiento"], pu["no_controladora"], 0]
        medidas = ["relative", "relative", "total", "relative", "relative", "relative", "relative", "relative",
                   "total"]
        textos = [fm(V["suma_vp_fcff"]), fm(V["vp_valor_terminal"]), fm(V["enterprise_value"]),
                  fm(pu["efectivo"], 0), fm(pu["asociadas"], 0), fm(pu["deuda"], 0), fm(pu["arrendamiento"], 0),
                  fm(pu["no_controladora"], 0), fm(V["equity_value"])]
        fig = go.Figure(go.Waterfall(
            x=etiquetas, y=valores, measure=medidas, text=textos, textposition="outside",
            increasing=dict(marker=dict(color=VERDE)), decreasing=dict(marker=dict(color=ROJO)),
            totals=dict(marker=dict(color=AZUL)), connector=dict(line=dict(color="#BFBFBF"))))
        fig.update_yaxes(title_text="mdp")
        st.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Cascada de Enterprise Value a Equity Value", 440), width="stretch")
    else:
        st.warning("Sin valor terminal no se puede construir la cascada de EV a Equity.")

    with st.expander("Históricos 2021–2025"):
        h = DATA["historicos_2021_2025"]
        hist = pd.DataFrame({k: v for k, v in h.items() if k != "anios"}, index=h["anios"]).T
        st.dataframe(hist.map(lambda v: fm(v, 0)), width="stretch")


# ---------------------------------------------------------------------------
# 5. Escenarios
# ---------------------------------------------------------------------------

with tabs[4]:
    st.subheader("Justificación de cada escenario")
    c = st.columns(3)
    for col, e in zip(c, m.ESCENARIOS):
        aj = p["escenarios"][e]
        col.text_area(f"{e}", key=PREFIJO + f"just_{e}", height=120)
        col.caption(f"Δ ventas {fp(aj['d_crec'])} · Δ margen {fp(aj['d_margen'])} · Δ WACC {fp(aj['d_wacc'])} · "
                    f"probabilidad {fp(aj['prob'], 0)}")

    st.subheader("Tabla comparativa")
    comp = m.tabla_comparativa(p, ESC)
    formatos = {"Inflación": fp, "Crecimiento": fp, "Beta": lambda v: f"{v:.4f}", "WACC": fp,
                "Crecimiento perpetuo": fp, "Valor por acción": fd}
    vista = pd.DataFrame({e: [formatos.get(r, fm)(comp.loc[r, e]) for r in comp.index] for e in m.ESCENARIOS},
                         index=comp.index)
    vista.loc["Probabilidad"] = [fp(p["escenarios"][e]["prob"], 0) for e in m.ESCENARIOS]
    st.dataframe(vista, width="stretch")
    st.markdown(f"**Valor ponderado por probabilidad: {esc_md(fd(ESC['ponderado']))}**")
    st.caption("Crecimiento = promedio del crecimiento de ventas 2026–2030. Inflación = inflación de largo plazo.")

    st.subheader("Interpretación")
    st.markdown(esc_md(m.interpretacion_escenarios(p, DATA, EST, ESC)))
    st.plotly_chart(key=kgraf(), figure_or_data=fig_escenarios(), width="stretch")


# ---------------------------------------------------------------------------
# 6. Sensibilidad
# ---------------------------------------------------------------------------

with tabs[5]:
    st.subheader("Matriz WACC vs crecimiento perpetuo (valor por acción)")
    mat = matriz()
    vista = mat.copy()
    vista.index = [fp(w) for w in mat.index]
    vista.columns = [fp(g, 1) for g in mat.columns]
    i_base = int(np.argmin(np.abs(mat.index.values - V["wacc"])))
    gs = np.array(mat.columns, dtype=float)
    j_base = int(np.argmin(np.abs(gs - V["g"]))) if np.min(np.abs(gs - V["g"])) < 1e-9 else None

    def resaltar(df):
        estilos = pd.DataFrame("", index=df.index, columns=df.columns)
        if j_base is not None:
            estilos.iloc[i_base, j_base] = f"background-color: {AZUL}; color: white; font-weight: 600"
        return estilos

    st.dataframe(vista.style.format(lambda v: fd(v)).apply(resaltar, axis=None), width="stretch")
    st.caption("Filas: WACC (base ± 1 pp en pasos de 0.5 pp). Columnas: g. Celda resaltada: caso actual.")
    st.plotly_chart(key=kgraf(), figure_or_data=fig_heatmap(mat), width="stretch")

    st.subheader("Gráficas de una variable")
    c1, c2 = st.columns(2)
    cv = m.curva(p, DATA, EST, escenario, "inflacion", np.arange(0.01, 0.0601, 0.0025))
    fig = go.Figure(go.Scatter(x=cv["x"] * 100, y=cv["y"], line=dict(color=AZUL, width=2)))
    fig.add_vline(x=p["inflacion_lp"] * 100, line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="Inflación de largo plazo (%)")
    fig.update_yaxes(title_text="$ por acción")
    c1.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Inflación vs valor por acción"), width="stretch")

    cv = m.curva(p, DATA, EST, escenario, "wacc", np.arange(max(V["g"] + 0.005, 0.05), 0.1301, 0.0025))
    fig = go.Figure(go.Scatter(x=cv["x"] * 100, y=cv["y"], line=dict(color=AZUL, width=2)))
    fig.add_vline(x=V["wacc"] * 100, line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="WACC (%)")
    fig.update_yaxes(title_text="$ por acción")
    c2.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "WACC vs valor por acción"), width="stretch")

    c1, c2 = st.columns(2)
    cv = m.curva(p, DATA, EST, escenario, "crecimiento", np.arange(-0.05, 0.0501, 0.005))
    fig = go.Figure(go.Scatter(x=cv["x"] * 100, y=cv["y"], line=dict(color=AZUL, width=2)))
    fig.add_vline(x=float(np.mean(R["proyeccion"].loc["Crecimiento de ventas"])) * 100,
                  line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="Crecimiento promedio de ventas 2026–2030 (%)")
    fig.update_yaxes(title_text="Enterprise Value (mdp)")
    c1.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Crecimiento vs Enterprise Value"), width="stretch")

    cv = m.curva(p, DATA, EST, escenario, "beta", np.arange(0, 1.501, 0.05))
    fig = go.Figure(go.Scatter(x=cv["x"], y=cv["y"] * 100, line=dict(color=AZUL, width=2)))
    fig.add_vline(x=CC["beta"]["usado"], line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="Beta")
    fig.update_yaxes(title_text="Ke (%)")
    c2.plotly_chart(key=kgraf(), figure_or_data=layout(fig, "Beta vs costo de capital (Ke)"), width="stretch")

    st.subheader("Tornado: cada variable ±10%")
    tor = m.tornado(p, DATA, EST, escenario)
    base = tor.attrs["base"]
    if base is not None:
        fig = go.Figure()
        fig.add_trace(go.Bar(y=tor["Variable"], x=tor["-10%"] - base, base=base, orientation="h",
                             name="Variable −10%", marker_color=AZUL_CLARO,
                             hovertemplate="%{y}: $%{x:,.2f}<extra>−10%</extra>"))
        fig.add_trace(go.Bar(y=tor["Variable"], x=tor["+10%"] - base, base=base, orientation="h",
                             name="Variable +10%", marker_color=AZUL,
                             hovertemplate="%{y}: $%{x:,.2f}<extra>+10%</extra>"))
        fig.add_vline(x=base, line=dict(color="black", width=1))
        fig.update_layout(barmode="overlay")
        fig.update_xaxes(title_text="Valor por acción ($)")
        st.plotly_chart(key=kgraf(), figure_or_data=layout(fig, f"Impacto en el valor por acción (base {fd(base)})", 520), width="stretch")
        t = tor.iloc[::-1].copy()
        st.dataframe(pd.DataFrame({"Variable": t["Variable"], "−10%": t["-10%"].map(fd), "+10%": t["+10%"].map(fd),
                                   "Rango": t["Impacto"].map(fd)}), hide_index=True, width="stretch")
    else:
        st.warning("El tornado requiere que el WACC sea mayor que g.")


# ---------------------------------------------------------------------------
# 7. Validación contra Excel
# ---------------------------------------------------------------------------

with tabs[6]:
    st.subheader("Validación contra Excel (valores default)")
    val, red = validacion_excel()
    vista = pd.DataFrame({
        "Variable": val["Variable"],
        "Excel": [fp(v, 4) if k in ("WACC", "g") else (fd(v, 4) if "acción" in k else fm(v, 2))
                  for k, v in zip(val["Variable"], val["Excel"])],
        "App": [fp(v, 4) if k in ("WACC", "g") else (fd(v, 4) if "acción" in k else fm(v, 2))
                for k, v in zip(val["Variable"], val["App"])],
        "Diferencia": [f"{d:.2e}" for d in val["Diferencia"]],
        "Diferencia %": [f"{d * 100:.2e}%" for d in val["Diferencia %"]],
        "Estado": val["Estado"],
    })
    st.dataframe(vista.style.map(lambda v: f"color: {VERDE if v == 'PASS' else ROJO}; font-weight: 600",
                                 subset=["Estado"]), hide_index=True, width="stretch")
    n_pass = int((val["Estado"] == "PASS").sum())
    st.markdown(f"**{n_pass} de {len(val)} variables en PASS** (diferencia menor a 0.01%).")
    st.markdown(
        f"Fuente de los valores del Excel: `{val.attrs['fuente']}`. Celdas: `7 Valuación`!B11, B12, B16, B18, B24, "
        "B26 y `9 Escenarios`!B12:D12.\n\n"
        "**Nota sobre diferencias.** La comparación usa siempre los valores default, sin importar lo que se haya "
        "movido en la barra lateral. La app trabaja con la misma precisión que Excel (doble precisión), por lo que "
        "las diferencias son del orden de 10⁻¹⁰ y vienen solo del orden de las operaciones de punto flotante. "
        f"Las diferencias visibles aparecen cuando se redondea un insumo: por ejemplo, con el WACC redondeado a "
        f"{fp(red['wacc_redondeado'])} el valor sale {esc_md(fd(red['valor_por_accion']))} en lugar de "
        f"{esc_md(fd(val.iloc[5]['Excel']))}. Por eso la app no redondea ningún valor intermedio."
    )


# ---------------------------------------------------------------------------
# 8. Reporte PDF
# ---------------------------------------------------------------------------

with tabs[7]:
    st.subheader("Reporte PDF")
    st.markdown(
        "El reporte refleja los valores que están en pantalla en este momento (escenario "
        f"**{escenario}**) e incluye: estudiante, empresa, variables, modelo financiero, beta, WACC, crecimiento "
        "perpetuo, valor terminal, Enterprise Value, Equity Value, valor por acción, los tres escenarios, "
        "gráficas, validación y conclusiones.")
    if st.button("Generar reporte PDF", type="primary"):
        with st.spinner("Generando el PDF..."):
            st.session_state["pdf_bytes"] = reporte_pdf.generar_pdf(p, DATA, EST, escenario)
    if st.session_state.get("pdf_bytes"):
        st.download_button("Descargar PDF", data=st.session_state["pdf_bytes"],
                           file_name=f"Valuacion_Soriana_{escenario}.pdf", mime="application/pdf")
