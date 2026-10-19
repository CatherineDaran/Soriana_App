"""Aplicación de valuación de Organización Soriana (SORIANA B).

Ejecutar con:  streamlit run app.py
"""

from __future__ import annotations

import copy
import html
import importlib
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import interfaz
import modelo as m
import relativa
import reporte_pdf


def _recargar_modulos(*modulos):
    """Streamlit solo vuelve a ejecutar app.py; los módulos importados se quedan en memoria. Si un módulo cambió
    en disco (por ejemplo, tras una actualización en Streamlit Cloud) o aún no se ha revisado, se recarga para
    que app.py nunca use una versión vieja."""
    for mod in modulos:
        try:
            mtime = os.path.getmtime(mod.__file__)
        except (OSError, AttributeError, TypeError):
            continue
        if getattr(mod, "_mtime_cargado", None) != mtime:
            importlib.reload(mod)
            mod._mtime_cargado = mtime


# El orden importa: relativa y reporte_pdf usan modelo.
_recargar_modulos(m, relativa, interfaz, reporte_pdf)

# Paleta de Soriana, suavizada para lectura cómoda
PRIM = "#B23A33"       # rojo Soriana
PRIM_CL = "#E6B5AF"    # rojo claro
PRIM_FONDO = "#FBF3F2"
VERDE_M = "#6AAE5A"    # verde Soriana
LIMA = "#A8BF3F"       # verde lima del logotipo
SEC = "#4A90BE"        # azul (Pantone 3005, suavizado)
SEC_CL = "#9CC8DA"     # azul claro (Pantone 311)
CARBON = "#43464F"     # gris carbón de la marca
GRIS = "#A9A3A0"       # gris cálido (Pantone 407)
GRIS_C = "#D9D5D2"
GRIS_TEXTO = "#62646B"
VERDE = "#3E8A3A"      # diferencias positivas
ROJO = "#B23A33"       # diferencias negativas
VERSION = "v3.2 · 19-oct-2026"  # se muestra al pie de la barra lateral
# Integrantes del equipo (se muestran en la barra lateral y en el encabezado del Dashboard)
EQUIPO = [
    ("Alejandro Ochoa", "A01613152"),
    ("Catherine Daran", "A01611885"),
    ("Dheneb Velazquez", "A01614817"),
    ("Julio Gaspar", "A01613250"),
]
FUENTE = "Inter, 'Helvetica Neue', Arial, sans-serif"

st.set_page_config(page_title="Valuación SORIANA B", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, .stApp, [data-testid="stSidebar"], button, input, textarea, select,
    [data-testid="stMarkdownContainer"] {{ font-family: {FUENTE}; }}
    .block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1380px; }}
    h1, h2, h3, h4 {{ color: {CARBON}; font-family: {FUENTE}; letter-spacing: -0.01em; }}

    /* Encabezado */
    .hero {{ background: #FFFFFF; border: 1px solid #ECE8E6; border-radius: 14px; overflow: hidden;
             margin-bottom: 18px; box-shadow: 0 1px 3px rgba(67,70,79,.06); }}
    .hero .franja {{ height: 6px; background: linear-gradient(90deg, {PRIM} 0 50%, {VERDE_M} 50% 75%, {LIMA} 75% 100%); }}
    .hero .cuerpo {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 24px; align-items: center;
                     padding: 20px 26px; }}
    .hero .titulo {{ color: {CARBON}; font-size: 1.6rem; font-weight: 700; line-height: 1.25; }}
    .hero .titulo span {{ color: {PRIM}; }}
    .hero .sub {{ color: {GRIS_TEXTO}; font-size: .9rem; margin-top: 4px; }}
    .hero .equipo {{ display: grid; grid-template-columns: repeat(2, max-content); gap: 3px 28px; margin-top: 8px;
                      font-size: .84rem; color: {GRIS_TEXTO}; }}
    .hero .equipo b {{ color: {CARBON}; font-weight: 600; }}
    .hero .chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }}
    .hero .chip {{ background: #F6F4F3; border: 1px solid #E7E2DF; border-radius: 999px; padding: 3px 11px;
                   font-size: .78rem; color: {CARBON}; }}
    .hero .chip.esc {{ background: {PRIM_FONDO}; border-color: {PRIM_CL}; color: {PRIM}; font-weight: 600; }}
    .hero .precio {{ text-align: right; background: #F8F7F6; border-radius: 12px; padding: 14px 20px; min-width: 250px; }}
    .hero .precio .etq {{ color: {GRIS_TEXTO}; font-size: .72rem; text-transform: uppercase; letter-spacing: .06em;
                          font-weight: 600; }}
    .hero .precio .val {{ font-size: 2.1rem; font-weight: 700; line-height: 1.15; color: {PRIM}; }}
    .hero .precio .dif {{ display: inline-block; margin-top: 4px; padding: 2px 10px; border-radius: 999px;
                          font-size: .82rem; font-weight: 600; }}
    .hero .precio .dif.pos {{ background: #EAF4E8; }}
    .hero .precio .dif.neg {{ background: #F9E9E7; }}
    .hero .precio .sub {{ font-size: .8rem; margin-top: 6px; }}
    @media (max-width: 900px) {{
      .hero .cuerpo {{ grid-template-columns: 1fr; }}
      .hero .precio {{ text-align: left; }}
    }}

    /* Pestañas */
    [data-baseweb="tab-list"] {{ gap: 2px; border-bottom: 1px solid #ECE8E6; }}
    [data-baseweb="tab"] {{ padding: 10px 14px !important; }}
    [data-baseweb="tab"] p {{ font-size: .92rem; font-weight: 500; color: {GRIS_TEXTO}; }}
    [data-baseweb="tab"][aria-selected="true"] p {{ color: {PRIM}; font-weight: 600; }}
    [data-baseweb="tab-highlight"] {{ background-color: {PRIM} !important; height: 3px !important; }}

    /* Secciones */
    .seccion {{ margin: 26px 0 10px 0; padding-bottom: 6px; border-bottom: 1px solid #ECE8E6; }}
    .seccion h3 {{ font-size: 1.12rem; font-weight: 650; margin: 0; padding: 0; border-left: 4px solid {PRIM};
                   padding-left: 10px; }}
    .seccion p {{ color: {GRIS_TEXTO}; font-size: .86rem; margin: 4px 0 0 14px; }}

    /* Tarjetas */
    .tarjeta {{ border: 1px solid #ECE8E6; border-radius: 12px; padding: 13px 16px; background: #FFFFFF;
               margin-bottom: 12px; min-height: 100px; box-shadow: 0 1px 2px rgba(67,70,79,.05); }}
    .tarjeta {{ overflow: hidden; }}
    .tarjeta .etq {{ font-size: .7rem; color: {GRIS_TEXTO}; text-transform: uppercase; letter-spacing: .05em;
                     font-weight: 600; word-break: normal; overflow-wrap: normal; hyphens: none; }}
    .tarjeta .val {{ font-size: clamp(1.05rem, 1.55vw, 1.5rem); font-weight: 700; color: {CARBON}; margin-top: 4px;
                     font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .tarjeta .sub {{ font-size: .78rem; color: #85878D; margin-top: 2px; }}
    .tarjeta.destacada {{ background: {PRIM_FONDO}; border-color: {PRIM_CL}; }}
    .tarjeta.destacada .val {{ color: {PRIM}; }}
    .pos {{ color: {VERDE} !important; }}
    .neg {{ color: {ROJO} !important; }}

    /* Tablas financieras */
    .tabla-wrap {{ border: 1px solid #ECE8E6; border-radius: 12px; overflow-x: auto; margin: 6px 0 14px 0;
                   background: #FFFFFF; }}
    table.tf {{ width: 100%; border-collapse: collapse; font-size: .86rem; font-variant-numeric: tabular-nums; }}
    table.tf th {{ background: #F6F4F3; color: {CARBON}; font-weight: 600; text-align: right; padding: 9px 14px;
                   border-bottom: 1px solid #E2DDDA; white-space: nowrap; }}
    table.tf td {{ padding: 7px 14px; border-bottom: 1px solid #F1EEEC; text-align: right; color: #2E3036;
                   white-space: nowrap; }}
    table.tf th.izq, table.tf td.izq {{ text-align: left; white-space: normal; }}
    table.tf tr:last-child td {{ border-bottom: none; }}
    table.tf tr:hover td {{ background: #FAF9F8; }}
    table.tf tr.total td {{ font-weight: 700; color: {PRIM}; border-top: 1.5px solid {PRIM_CL}; background: {PRIM_FONDO}; }}
    table.tf tr.sutil td {{ color: {GRIS_TEXTO}; font-size: .82rem; }}
    .badge {{ display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700; }}
    .badge.ok {{ background: #EAF4E8; color: {VERDE}; }}
    .badge.mal {{ background: #F9E9E7; color: {ROJO}; }}

    /* Nota */
    .nota {{ background: #F8F7F6; border-left: 3px solid {VERDE_M}; border-radius: 8px; padding: 12px 16px;
             color: {CARBON}; font-size: .9rem; line-height: 1.55; margin: 8px 0 14px 0; }}

    /* Barra lateral */
    [data-testid="stSidebar"] {{ background: #F8F7F6; border-right: 1px solid #ECE8E6; }}
    [data-testid="stSidebar"] [data-testid="stExpander"] details {{ background: #FFFFFF; border-color: #ECE8E6;
                                                                    border-radius: 10px; }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary p {{ font-weight: 600; color: {CARBON}; }}
    .lateral-titulo {{ background: #FFFFFF; border: 1px solid #ECE8E6; border-top: 4px solid {PRIM};
                       border-radius: 10px; padding: 12px 16px; margin-bottom: 12px; }}
    .lateral-titulo .t {{ font-size: 1.05rem; font-weight: 700; color: {CARBON}; }}
    .lateral-titulo .eq-t {{ margin-top: 10px; padding-top: 8px; border-top: 1px solid #F0ECEA; font-size: .68rem;
                             font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: {GRIS_TEXTO}; }}
    .lateral-titulo .eq div {{ display: flex; justify-content: space-between; gap: 8px; font-size: .8rem;
                               padding: 2px 0; color: {CARBON}; }}
    .lateral-titulo .eq div span:last-child {{ color: {GRIS_TEXTO}; font-variant-numeric: tabular-nums; }}
    .lateral-titulo .s {{ font-size: .78rem; color: {GRIS_TEXTO}; margin-top: 2px; }}
    .manual-etq {{ font-size: .86rem; font-weight: 600; color: {CARBON}; margin-top: 6px; }}
    .manual-etq code {{ font-size: .78rem; color: {PRIM}; background: {PRIM_FONDO}; }}
    [data-testid="stSidebar"] [role="radiogroup"] label {{ background: #FFFFFF; border: 1px solid #ECE8E6;
                                                            border-radius: 8px; padding: 6px 10px; margin-bottom: 4px; width: 100%; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background: {PRIM_FONDO};
                                                                              border-color: {PRIM_CL}; }}
    [data-testid="stSidebar"] [data-testid="stTextInputRootElement"] {{ border: 1px solid #E2DDDA; border-radius: 8px;
        background: #FAF9F8; transition: border-color .2s ease, box-shadow .2s ease; }}
    [data-testid="stSidebar"] [data-testid="stTextInputRootElement"]:focus-within {{ border-color: {PRIM_CL};
        box-shadow: 0 0 0 3px {PRIM_FONDO}; }}
    [data-testid="stSidebar"] input {{ font-variant-numeric: tabular-nums; }}

    /* Animaciones: entrada suave, realce al pasar el cursor y transiciones */
    @keyframes aparecer {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
    @keyframes desvanecer {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes franja {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
    .hero {{ animation: aparecer .6s cubic-bezier(.2,.7,.2,1) both; }}
    .hero .franja {{ transform-origin: left; animation: franja 1s cubic-bezier(.2,.7,.2,1) .15s both; }}
    .hero .precio {{ animation: aparecer .6s cubic-bezier(.2,.7,.2,1) .2s both; }}
    .tarjeta, .tabla-wrap, .nota, .seccion {{ animation: aparecer .5s cubic-bezier(.2,.7,.2,1) both; }}
    [data-testid="stColumn"]:nth-child(2) .tarjeta {{ animation-delay: .06s; }}
    [data-testid="stColumn"]:nth-child(3) .tarjeta {{ animation-delay: .12s; }}
    [data-testid="stColumn"]:nth-child(4) .tarjeta {{ animation-delay: .18s; }}
    [data-testid="stColumn"]:nth-child(5) .tarjeta {{ animation-delay: .24s; }}
    [data-testid="stPlotlyChart"] {{ animation: desvanecer .7s ease-out .1s both; }}
    [data-testid="stTabPanel"] > div {{ animation: desvanecer .35s ease-out both; }}
    .tarjeta, .tabla-wrap, .hero .chip, [data-testid="stSidebar"] [data-testid="stExpander"] details {{
        transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease, background-color .2s ease; }}
    .tarjeta:hover {{ transform: translateY(-3px); box-shadow: 0 8px 20px rgba(67,70,79,.10); border-color: #DCD6D2; }}
    .tarjeta.destacada:hover {{ border-color: {PRIM_CL}; }}
    .tabla-wrap:hover {{ box-shadow: 0 4px 14px rgba(67,70,79,.07); }}
    table.tf td {{ transition: background-color .15s ease; }}
    .hero .chip:hover {{ transform: translateY(-1px); }}
    [data-testid="stSidebar"] [data-testid="stExpander"] details:hover {{ border-color: #DCD6D2; }}
    button {{ transition: background-color .2s ease, border-color .2s ease, color .2s ease, transform .1s ease !important; }}
    button:active {{ transform: scale(.98); }}
    [data-baseweb="tab"] p {{ transition: color .2s ease; }}
    [data-baseweb="tab"]:hover p {{ color: {PRIM}; }}
    [data-baseweb="tab-highlight"] {{ transition: all .3s cubic-bezier(.2,.7,.2,1) !important; }}
    @media (prefers-reduced-motion: reduce) {{
      *, *::before, *::after {{ animation: none !important; transition: none !important; }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Las cifras de las tarjetas y del encabezado se animan (conteo) al aparecer y al cambiar de valor.
st.html(
    r"""
    <script>
    (function () {
      if (window.__sorianaConteo) { return; }
      window.__sorianaConteo = true;
      var quieto = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      var previos = {};
      var patron = /^([^0-9+\-]*)([+\-]?)([0-9][0-9,]*\.?[0-9]*)(.*)$/;
      function escribir(el, txt) {
        // Se modifica el nodo de texto existente para no romper la referencia que usa Streamlit.
        var t = el.firstChild;
        el.__escrito = txt;
        if (t && t.nodeType === 3) { t.nodeValue = txt; } else { el.textContent = txt; }
      }
      function animar(el) {
        var texto = el.textContent.trim();
        if (texto === el.__escrito) { return; }
        var clave = el.getAttribute("data-anim");
        if (el.__raf) { cancelAnimationFrame(el.__raf); }
        var m = texto.match(patron);
        if (!m) { previos[clave] = undefined; el.__escrito = texto; return; }
        var pre = m[1], signo = m[2], num = m[3], suf = m[4];
        var dec = (num.split(".")[1] || "").length;
        var meta = parseFloat(num.replace(/,/g, "")) * (signo === "-" ? -1 : 1);
        var dur = 800, ahora = performance.now(), p = previos[clave], desde, inicio;
        if (p && p.meta === meta && ahora - p.inicio < dur) {
          // Streamlit reemplazó el elemento a mitad de la animación: se continúa en el nuevo.
          desde = p.desde; inicio = p.inicio;
        } else if (p && p.meta === meta) {
          el.__escrito = texto; return;
        } else {
          desde = p ? p.meta : 0; inicio = ahora;
          previos[clave] = { meta: meta, desde: desde, inicio: inicio };
        }
        if (quieto) { el.__escrito = texto; return; }
        function cuadro(t) {
          var k = Math.min(1, Math.max(0, (performance.now() - inicio) / dur));
          var e = 1 - Math.pow(1 - k, 3);
          var v = desde + (meta - desde) * e;
          var s = Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
          var sg = v < 0 ? "-" : (signo === "+" ? "+" : "");
          if (k < 1) { escribir(el, pre + sg + s + suf); el.__raf = requestAnimationFrame(cuadro); }
          else { escribir(el, texto); el.__raf = null; }
        }
        el.__raf = requestAnimationFrame(cuadro);
      }
      function revisar(n) {
        if (!n) { return; }
        var el = n.nodeType === 3 ? n.parentElement : n;
        if (!el || !el.closest) { return; }
        var propio = el.closest("[data-anim]");
        if (propio) { animar(propio); }
        if (el.querySelectorAll) { el.querySelectorAll("[data-anim]").forEach(animar); }
      }
      new MutationObserver(function (cambios) {
        cambios.forEach(function (c) {
          if (c.type === "characterData") { revisar(c.target); }
          else { revisar(c.target); c.addedNodes.forEach(revisar); }
        });
      }).observe(document.body, { childList: true, subtree: true, characterData: true });
      document.querySelectorAll("[data-anim]").forEach(animar);
    })();
    </script>
    """,
    unsafe_allow_javascript=True,
)


LOGO = interfaz.imagen_b64("logo_soriana.png")
ICONO = interfaz.imagen_b64("icono_soriana.png")
st.markdown(interfaz.css(PRIM, PRIM_CL, CARBON, GRIS_TEXTO), unsafe_allow_html=True)
# Barra de íconos (visible con la barra lateral cerrada) y tutorial de bienvenida.
st.html(interfaz.script(LOGO, ICONO), unsafe_allow_javascript=True)


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


@st.cache_data
def resumen_modos():
    return m.resumen_modos(datos(), estadisticas())


@st.cache_data
def validacion_banamex():
    return relativa.validacion_reporte(datos(), estadisticas(), datos_relativa())


@st.cache_data
def datos_relativa():
    return relativa.cargar_relativa()


DATA = datos()
EST = estadisticas()
REL = datos_relativa()
DEF = m.parametros_default(DATA)
EMP = DATA["empresa"]


# ---------------------------------------------------------------------------
# Formatos y componentes visuales
# ---------------------------------------------------------------------------

def _nd(v):
    return v is None or (isinstance(v, float) and np.isnan(v))


def fm(v, dec=1):
    return "n.d." if _nd(v) else f"{v:,.{dec}f}"


def fp(v, dec=2):
    return "n.d." if _nd(v) else f"{v * 100:,.{dec}f}%"


def fd(v, dec=2):
    return "n.d." if _nd(v) else f"${v:,.{dec}f}"


def h(texto) -> str:
    """Escapa HTML y evita que Streamlit lea el signo $ como LaTeX."""
    return html.escape(str(texto)).replace("$", "&#36;")


def esc_md(texto: str) -> str:
    return texto.replace("$", "\\$")


def layout(fig, titulo=None, alto=360):
    fig.update_layout(
        template="plotly_white",
        title=dict(text=titulo, font=dict(color=CARBON, size=14, family=FUENTE), x=0, xanchor="left")
        if titulo else None,
        height=alto,
        margin=dict(l=8, r=8, t=44 if titulo else 12, b=8),
        font=dict(family=FUENTE, size=12, color="#344054"),
        legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="left", x=0, font=dict(size=11)),
        hoverlabel=dict(font_family=FUENTE, bgcolor="#FFFFFF", bordercolor="#D0D5DD"),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        transition=dict(duration=600, easing="cubic-in-out"),
    )
    fig.update_xaxes(gridcolor="#EEF1F5", zerolinecolor="#D0D5DD", linecolor="#D0D5DD", title_font=dict(size=11))
    fig.update_yaxes(gridcolor="#EEF1F5", zerolinecolor="#D0D5DD", title_font=dict(size=11))
    return fig


_CONTADOR = {"n": 0}


def grafica(fig, dest=None):
    """Dibuja la gráfica dentro de una tarjeta con borde; clave única para evitar IDs duplicados."""
    _CONTADOR["n"] += 1
    with (dest or st).container(border=True):
        st.plotly_chart(fig, key=f"graf_{_CONTADOR['n']}", width="stretch",
                        config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


def seccion(titulo, descripcion=None, dest=None):
    desc = f"<p>{h(descripcion)}</p>" if descripcion else ""
    (dest or st).markdown(f"<div class='seccion'><h3>{h(titulo)}</h3>{desc}</div>", unsafe_allow_html=True)


def tarjeta(col, etiqueta, valor, sub="", clase="", destacada=False):
    _CONTADOR["t"] = _CONTADOR.get("t", 0) + 1
    col.markdown(
        f"<div class='tarjeta{' destacada' if destacada else ''}'><div class='etq'>{h(etiqueta)}</div>"
        f"<div class='val {clase}' data-anim='t{_CONTADOR['t']}'>{h(valor)}</div>"
        f"<div class='sub'>{h(sub)}</div></div>",
        unsafe_allow_html=True,
    )


def nota(texto_html, dest=None):
    (dest or st).markdown(f"<div class='nota'>{texto_html.replace('$', '&#36;')}</div>", unsafe_allow_html=True)


def tabla(df: pd.DataFrame, indice=True, totales=(), sutiles=(), izq=(), estilos=None, dest=None):
    """Tabla financiera en HTML: números alineados a la derecha, encabezado gris claro y renglones de total."""
    estilos = estilos or {}
    cols = list(df.columns)
    enc = "".join(f"<th class='{'izq' if c in izq else ''}'>{h(c)}</th>" for c in cols)
    if indice:
        enc = f"<th class='izq'>{h(df.index.name or '')}</th>" + enc
    filas = []
    for i, (idx, fila) in enumerate(df.iterrows()):
        clase = "total" if idx in totales else ("sutil" if idx in sutiles else "")
        celdas = f"<td class='izq'>{h(idx)}</td>" if indice else ""
        for j, c in enumerate(cols):
            v = fila[c]
            st_ = estilos.get((i, j), "")
            contenido = v if isinstance(v, str) and v.startswith("<span") else h(v)
            celdas += f"<td class='{'izq' if c in izq else ''}' style='{st_}'>{contenido}</td>"
        filas.append(f"<tr class='{clase}'>{celdas}</tr>")
    (dest or st).markdown(
        f"<div class='tabla-wrap'><table class='tf'><thead><tr>{enc}</tr></thead>"
        f"<tbody>{''.join(filas)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def color_calor(v, vmin, vmax):
    """Interpola entre un azul muy claro y el azul marino."""
    if _nd(v) or vmax == vmin:
        return "", "#1D2939"
    t = (v - vmin) / (vmax - vmin)
    a, b = np.array([0xF3, 0xF8, 0xFB]), np.array([0x2F, 0x78, 0xA8])
    r, g, bl = (a + (b - a) * t).astype(int)
    return f"#{r:02X}{g:02X}{bl:02X}", ("#FFFFFF" if t > 0.55 else "#1D2939")


# ---------------------------------------------------------------------------
# Barra lateral: variables
# ---------------------------------------------------------------------------

PREFIJO = "w_"


def restablecer():
    for k in list(st.session_state.keys()):
        if k.startswith(PREFIJO):
            del st.session_state[k]


def _decimales(fmt):
    return int(fmt.split(".")[1][0]) if fmt and "." in fmt else 2


def _texto(v, dec):
    return f"{v:,.{dec}f}"


def _leer(texto):
    """Convierte el texto capturado a número; acepta comas, %, $ y espacios."""
    try:
        return float(str(texto).replace(",", "").replace("%", "").replace("$", "").replace(" ", ""))
    except ValueError:
        return None


def campo(label, k, valor, dec, minimo=None, ayuda=None, disabled=False, oculto=False):
    """Campo numérico como texto: no captura la rueda del mouse, así la barra lateral hace scroll normal.
    Si el texto coincide con el valor por defecto formateado, se usa el valor exacto (sin redondear)."""
    defecto = _texto(valor, dec)
    st.session_state.setdefault(k, defecto)
    txt = st.text_input(label, key=k, help=ayuda, disabled=disabled,
                        label_visibility="collapsed" if oculto else "visible")
    if txt.strip() == defecto:
        return valor
    v = _leer(txt)
    if v is None or (minimo is not None and v < minimo):
        st.caption(f":red[Valor no válido; se usa {defecto}]")
        return valor
    return v


def num(label, clave, default, pct=False, paso=None, fmt=None, minimo=None, ayuda=None):
    """Número editable. Si pct=True se muestra en % y se devuelve en decimal."""
    base = default * 100 if pct else default
    v = campo(label, PREFIJO + clave, base, _decimales(fmt or ("%.4f" if pct else "%.2f")),
              minimo=None if minimo is None else (minimo * 100 if pct else minimo), ayuda=ayuda)
    return v / 100 if pct else v


def manual(label, clave, calculado, pct=True, fmt="%.4f", paso=None, mostrar_dec=4):
    """Patrón calculado / manual / usado del Excel."""
    kc, kv = PREFIJO + clave + "_usar", PREFIJO + clave + "_valor"
    st.session_state.setdefault(kc, False)
    texto = fp(calculado, mostrar_dec) if pct else f"{calculado:,.{mostrar_dec}f}"
    st.markdown(f"<div class='manual-etq'>{h(label)} · calculado <code>{h(texto)}</code></div>",
                unsafe_allow_html=True)
    base = calculado * 100 if pct else calculado
    if not st.session_state[kc]:
        # Mientras no se use, el campo muestra el valor calculado vigente.
        st.session_state[kv] = _texto(base, _decimales(fmt))
    usar = st.checkbox("Usar valor manual", key=kc)
    v = campo(f"{label} manual" + (" (%)" if pct else ""), kv, base, _decimales(fmt), disabled=not usar,
              oculto=True)
    if not usar:
        return None
    return v / 100 if pct else v


with st.sidebar:
    st.markdown(f"<div class='lateral-logo'><img src='{LOGO}' alt='Soriana'></div>", unsafe_allow_html=True)

    st.session_state.setdefault(PREFIJO + "escenario", "Base")
    escenario = st.radio("Escenario", m.ESCENARIOS, key=PREFIJO + "escenario")

    RM = resumen_modos()
    MODOS_WACC = {"redondeado": f"Redondeado a {fp(RM['redondeado']['wacc'])} (reporte Banamex)",
                  "exacto": f"Exacto ({fp(RM['exacto']['wacc'], 4)}, Excel integrador)"}
    st.session_state.setdefault(PREFIJO + "modo_wacc", DEF["modo_wacc"])
    modo_wacc = st.radio("WACC del DCF", list(MODOS_WACC), key=PREFIJO + "modo_wacc",
                         format_func=MODOS_WACC.get)
    st.caption(f"La diferencia de {fd(abs(RM['diferencia']))} por acción viene solo del redondeo del WACC.")

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
            format_func=lambda i: f"Método {i}",
            help="1: promedio del cambio % diario del bono × 252. 2: promedio del nivel del bono / 100. "
                 "3: último nivel del bono / 100.")
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

    st.write("")
    st.button("Restablecer valores del Excel", on_click=restablecer, width="stretch")


# ---------------------------------------------------------------------------
# Cálculo de toda la cadena
# ---------------------------------------------------------------------------

# El modo de WACC elegido alimenta el DCF y el precio objetivo (un WACC manual siempre tiene prioridad).
p = relativa.con_wacc(p, EST, modo_wacc)


def _inclusion(clave):
    """Lee las casillas Incluir editadas en la tabla (st.data_editor guarda solo los cambios)."""
    estado = st.session_state.get(clave) or {}
    return {int(i): bool(c["Incluir"]) for i, c in estado.get("edited_rows", {}).items() if "Incluir" in c}


def _valor_texto(k, valor, dec):
    """Valor de un campo de texto numérico antes de dibujarlo (misma regla que campo())."""
    txt = st.session_state.get(k)
    if txt is None or txt.strip() == _texto(valor, dec):
        return valor
    v = _leer(txt)
    return valor if v is None else v


POND_DEFAULT = REL["precio_objetivo"]["ponderaciones_default"]
for _e in ("est_comp", "est_trans"):
    st.session_state.setdefault(PREFIJO + _e, "Media")
POND = {k: _valor_texto(PREFIJO + f"pond_{k}", POND_DEFAULT[k] * 100, 2) / 100 for k in POND_DEFAULT}
UMBRALES = {"comprar": _valor_texto(PREFIJO + "umbral_comprar", relativa.UMBRALES_DEFAULT["comprar"] * 100, 1) / 100,
            "vender": _valor_texto(PREFIJO + "umbral_vender", relativa.UMBRALES_DEFAULT["vender"] * 100, 1) / 100}
VR = relativa.valuacion_completa(
    p, DATA, EST, REL, incluir_comp=_inclusion(PREFIJO + "editor_comp"),
    incluir_trans=_inclusion(PREFIJO + "editor_trans"), est_comp=st.session_state[PREFIJO + "est_comp"],
    est_trans=st.session_state[PREFIJO + "est_trans"], pond=POND, umbrales=UMBRALES)
PO = VR["precio_objetivo"]

R = m.modelo_completo(p, DATA, EST, escenario)
CC = R["costo_capital"]
V = R["valuacion"]
ESC = m.todos_escenarios(p, DATA, EST)
INF = inflacion()
IPC = ipc()


def pdf_actual() -> bytes:
    """Se ejecuta solo al hacer clic en el botón de descarga, con los valores en pantalla."""
    return reporte_pdf.generar_pdf(p, DATA, EST, escenario, VR)


NOMBRE_PDF = f"Valuacion_Soriana_{escenario}.pdf"

# Encabezado
dif = V["diferencia_precio"]
if dif is None:
    chip_dif = "<span class='dif'>Valor no disponible</span>"
else:
    chip_dif = (f"<span class='dif {'pos' if dif >= 0 else 'neg'}'>"
                f"{'+' if dif >= 0 else ''}{fp(dif, 1)} vs precio</span>")
# El HTML va en una sola línea para que Markdown no lo interprete como bloque de código.
hero = "".join([
    "<div class='hero'><div class='franja'></div><div class='cuerpo'>",
    "<div>",
    f"<div class='titulo'>Valuación de <span>{h(EMP['nombre'])}</span></div>",
    f"<div class='sub'>{h(EMP['curso'])} · Tecnológico de Monterrey</div>",
    "<div class='equipo'>" + "".join(f"<span><b>{h(n)}</b> {h(mt)}</span>" for n, mt in EQUIPO) + "</div>",
    "<div class='chips'>",
    f"<span class='chip'>{h(EMP['emisora'])} · BMV</span>",
    f"<span class='chip esc'>Escenario {h(escenario)}</span>",
    f"<span class='chip'>WACC {fp(V['wacc'])}</span>",
    f"<span class='chip'>g {fp(V['g'])}</span>",
    "<span class='chip'>Cifras en millones de pesos</span>",
    "</div></div>",
    "<div class='precio'>",
    "<div class='etq'>Valor estimado por acción</div>",
    f"<div class='val' data-anim='hero'>{h(fd(V['valor_por_accion']))}</div>",
    chip_dif,
    f"<div class='sub'>Precio de mercado {h(fd(p['precio_mercado']))} · {h(EMP['fecha_precio'])}</div>",
    "</div></div></div>",
])
st.markdown(hero, unsafe_allow_html=True)

if not V["valido"]:
    st.warning(f"El WACC ({fp(V['wacc'])}) no es mayor que el crecimiento perpetuo g ({fp(V['g'])}). "
               "No se calcula el valor terminal; ajusta las variables.")
if abs(ESC["suma_prob"] - 1) > 1e-9:
    st.info(f"Las probabilidades de los escenarios suman {fp(ESC['suma_prob'], 0)}, no 100%.")

TOP = st.tabs([":material/space_dashboard: Dashboard", ":material/functions: DCF",
               ":material/groups: Valuación relativa", ":material/flag: Precio objetivo",
               ":material/insights: Contexto financiero", ":material/fact_check: Validación",
               ":material/picture_as_pdf: Reporte PDF"], key="pestana")
with TOP[1]:
    SUB_DCF = st.tabs(["Inflación y mercado", "Beta y WACC", "Proyección y valuación", "Escenarios", "Sensibilidad"],
                      key="pestana_dcf")
with TOP[2]:
    SUB_REL = st.tabs(["Empresas comparables", "Transacciones precedentes"], key="pestana_rel")
# Índices de las secciones originales (se conservan sin cambios)
tabs = [TOP[0], *SUB_DCF, TOP[5], TOP[6]]


# ---------------------------------------------------------------------------
# Gráficas reutilizables
# ---------------------------------------------------------------------------

def fig_inflacion_activo():
    s = INF["serie"]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(x=s.index, y=s["soriana"], name="Precio SORIANA B ($)",
                             line=dict(color=PRIM, width=2.2)), secondary_y=False)
    fig.add_trace(go.Scatter(x=s.index, y=s["inflacion_anual"] * 100, name="Inflación anual (%)",
                             line=dict(color=GRIS, width=1.6, dash="dash")), secondary_y=True)
    fig.update_yaxes(title_text="Precio ($)", secondary_y=False)
    fig.update_yaxes(title_text="Inflación anual (%)", secondary_y=True, showgrid=False)
    return layout(fig, "Inflación vs activo")


def fig_ipc_activo():
    s = IPC["serie"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s["base100_soriana"], name="SORIANA B",
                             line=dict(color=PRIM, width=2.2)))
    fig.add_trace(go.Scatter(x=s.index, y=s["base100_ipc"], name="S&P/BMV IPC", line=dict(color=GRIS, width=1.6)))
    fig.update_yaxes(title_text="Base 100 (nov-2021)")
    return layout(fig, "IPC vs activo (base 100)")


def fig_escenarios():
    vals = [ESC["resultados"][e]["valuacion"]["valor_por_accion"] for e in m.ESCENARIOS]
    fig = go.Figure(go.Bar(x=m.ESCENARIOS, y=[v or 0 for v in vals], marker_color=[SEC_CL, PRIM, VERDE_M],
                           text=[fd(v) for v in vals], textposition="outside", name="Valor por acción",
                           showlegend=False, width=0.55))
    fig.add_trace(go.Scatter(x=m.ESCENARIOS, y=[p["precio_mercado"]] * 3, mode="lines",
                             name=f"Precio de mercado {fd(p['precio_mercado'])}",
                             line=dict(color=CARBON, dash="dash", width=1.6)))
    if ESC["ponderado"] is not None:
        fig.add_trace(go.Scatter(x=m.ESCENARIOS, y=[ESC["ponderado"]] * 3, mode="lines",
                                 name=f"Valor ponderado {fd(ESC['ponderado'])}",
                                 line=dict(color=GRIS, dash="dot", width=1.6)))
    fig.update_yaxes(title_text="$ por acción")
    return layout(fig, "Escenarios vs precio de mercado")


def fig_valor_accion():
    cats = ["Precio de mercado", f"Valor estimado ({escenario})", "Valor ponderado"]
    vals = [p["precio_mercado"], V["valor_por_accion"], ESC["ponderado"]]
    fig = go.Figure(go.Bar(x=cats, y=[v or 0 for v in vals], marker_color=[GRIS_C, PRIM, VERDE_M],
                           text=[fd(v) for v in vals], textposition="outside", width=0.55))
    fig.update_yaxes(title_text="$ por acción")
    return layout(fig, "Valor por acción")


def matriz():
    return m.matriz_sensibilidad(p, DATA, EST, escenario)


def celda_base(mat):
    i = int(np.argmin(np.abs(mat.index.values - V["wacc"])))
    gs = np.array(mat.columns, dtype=float)
    j = int(np.argmin(np.abs(gs - V["g"]))) if np.min(np.abs(gs - V["g"])) < 1e-9 else None
    return i, j


def fig_heatmap(mat):
    z = mat.values.astype(float)
    texto = [[fd(v) if not np.isnan(v) else "n.d." for v in fila] for fila in z]
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{g * 100:.1f}%" for g in mat.columns], y=[f"{w * 100:.2f}%" for w in mat.index],
        text=texto, texttemplate="%{text}", colorscale=[[0, "#F3F8FB"], [1, "#2F78A8"]], showscale=False,
        xgap=2, ygap=2, hovertemplate="WACC %{y}<br>g %{x}<br>%{text}<extra></extra>"))
    i, j = celda_base(mat)
    if j is not None:
        fig.add_shape(type="rect", x0=j - 0.5, x1=j + 0.5, y0=i - 0.5, y1=i + 0.5,
                      line=dict(color=CARBON, width=3))
    fig.update_xaxes(title_text="Crecimiento perpetuo (g)", side="bottom", showgrid=False)
    fig.update_yaxes(title_text="WACC", autorange="reversed", showgrid=False)
    return layout(fig, "Sensibilidad WACC – g (valor por acción)", 380)


COLOR_RECOMENDACION = {"COMPRAR": (VERDE, "#EAF4E8"), "MANTENER": (GRIS_TEXTO, "#F3F1EF"),
                       "VENDER": (ROJO, "#F9E9E7"), "n.d.": (GRIS_TEXTO, "#F3F1EF")}


def recomendacion_html(rec, umbrales, dest=None):
    color, fondo = COLOR_RECOMENDACION.get(rec, COLOR_RECOMENDACION["n.d."])
    regla = (f"Regla del equipo: comprar si potencial &gt; {fp(umbrales['comprar'], 0)}, "
             f"vender si &lt; {fp(umbrales['vender'], 0)}")
    (dest or st).markdown(
        f"<div class='tarjeta' style='background:{fondo};border-color:{fondo}'><div class='etq'>Recomendación</div>"
        f"<div class='val' style='color:{color}'>{h(rec)}</div><div class='sub'>{regla}</div></div>",
        unsafe_allow_html=True)


def fig_football():
    rangos = VR["rangos"]
    nombres = [k for k, (a, b) in rangos.items() if a is not None and b is not None]
    colores = [PRIM, PRIM_CL, SEC, SEC_CL, VERDE_M]
    fig = go.Figure()
    for i, k in enumerate(nombres):
        a, b = rangos[k]
        fig.add_trace(go.Bar(y=[k], x=[b - a], base=[a], orientation="h", marker_color=colores[i % len(colores)],
                             text=[f"{fd(a)} – {fd(b)}"], textposition="inside", insidetextanchor="middle",
                             textfont=dict(color="#FFFFFF" if i % 2 == 0 else CARBON), showlegend=False,
                             hovertemplate=f"{k}<br>{fd(a)} – {fd(b)}<extra></extra>"))
    fig.add_vline(x=p["precio_mercado"], line=dict(color=CARBON, dash="dash", width=2))
    fig.add_annotation(x=p["precio_mercado"], y=1.0, yref="paper", yanchor="bottom", xanchor="right", showarrow=False,
                       text=f"Precio {fd(p['precio_mercado'])}", font=dict(color=CARBON, size=11))
    if PO["objetivo"] is not None:
        fig.add_vline(x=PO["objetivo"], line=dict(color=PRIM, width=2.5))
        fig.add_annotation(x=PO["objetivo"], y=1.0, yref="paper", yanchor="bottom", xanchor="left", showarrow=False,
                           text=f"Objetivo {fd(PO['objetivo'])}", font=dict(color=PRIM, size=11))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="$ por acción")
    layout(fig, "Rango de valuación (football field)", 440)
    fig.update_layout(margin=dict(t=72))
    return fig


def boton_pdf(dest, clave, primario=True):
    dest.download_button(
        "Descargar reporte PDF", data=pdf_actual, file_name=NOMBRE_PDF, mime="application/pdf",
        key=clave, on_click="ignore", type="primary" if primario else "secondary", width="stretch")


boton_pdf(st.sidebar, "pdf_lateral", primario=False)
st.sidebar.html(interfaz.boton_tutorial(), unsafe_allow_javascript=True)
st.sidebar.caption(VERSION)


# ---------------------------------------------------------------------------
# 1. Dashboard
# ---------------------------------------------------------------------------

with tabs[0]:
    clase = "" if dif is None else ("pos" if dif >= 0 else "neg")
    c = st.columns(5)
    tarjeta(c[0], "Precio de mercado", fd(p["precio_mercado"]), f"Cierre {EMP['fecha_precio']}")
    tarjeta(c[1], "Valor por acción", fd(V["valor_por_accion"]), f"Estimado · escenario {escenario}",
            destacada=True)
    tarjeta(c[2], "Diferencia vs precio", ("n.d." if dif is None else f"{'+' if dif >= 0 else ''}{fp(dif, 1)}"),
            "Potencial de subida" if (dif or 0) >= 0 else "Potencial de baja", clase)
    tarjeta(c[3], "Beta", f"{CC['beta']['usado']:.4f}", "manual" if p["beta_manual"] is not None else "calculada")
    tarjeta(c[4], "WACC", fp(V["wacc"]), f"Ke {fp(CC['ke'])} · Kd {fp(CC['kd']['usado'])}")
    c = st.columns(5)
    tarjeta(c[0], "Crecimiento perpetuo", fp(V["g"]), f"Inflación {fp(p['inflacion_lp'])} + real {fp(p['crec_real'])}")
    tarjeta(c[1], "Valor terminal", fm(V["valor_terminal"]), f"Peso en EV: {fp(V['peso_vt'], 1)}")
    tarjeta(c[2], "Enterprise Value", fm(V["enterprise_value"]), "mdp")
    tarjeta(c[3], "Equity Value", fm(V["equity_value"]), "mdp")
    tarjeta(c[4], "Valor ponderado", fd(ESC["ponderado"]), f"Escenario seleccionado: {escenario}")

    seccion("Precio objetivo y valuación relativa",
            "Precio objetivo = ponderación del DCF base, empresas comparables y transacciones precedentes.")
    c = st.columns(3)
    pot = PO["potencial"]
    tarjeta(c[0], "Precio objetivo (12 meses)", fd(PO["objetivo"]), "Ponderación DCF · comparables · transacciones",
            destacada=True)
    tarjeta(c[1], "Potencial", "n.d." if pot is None else f"{'+' if pot >= 0 else ''}{fp(pot, 1)}",
            f"vs precio de mercado {fd(p['precio_mercado'])}", "" if pot is None else ("pos" if pot >= 0 else "neg"))
    with c[2]:
        recomendacion_html(PO["recomendacion"], UMBRALES)
    c = st.columns(3)
    tarjeta(c[0], "DCF (escenario base)", fd(VR["dcf"]), f"Peso {fp(POND['dcf'], 1)} · WACC {fp(VR['wacc'])}")
    tarjeta(c[1], "Empresas comparables", fd(VR["comparables"]["valor"]),
            f"Peso {fp(POND['comparables'], 1)} · {VR['comparables']['estadistico'].lower()} de 3 múltiplos")
    tarjeta(c[2], "Transacciones precedentes", fd(VR["transacciones"]["valor"]),
            f"Peso {fp(POND['transacciones'], 1)} · {VR['transacciones']['n_incluidas']} operaciones")

    c1, c2 = st.columns(2)
    grafica(fig_inflacion_activo(), c1)
    grafica(fig_ipc_activo(), c2)
    c1, c2 = st.columns(2)
    grafica(fig_escenarios(), c1)
    grafica(fig_valor_accion(), c2)
    grafica(fig_heatmap(matriz()))


# ---------------------------------------------------------------------------
# 2. Inflación y mercado
# ---------------------------------------------------------------------------

with tabs[1]:
    seccion("Inflación (INPC de Banxico)", "Inflación anual = INPC_t / INPC_(t−12) − 1; mensual = INPC_t / INPC_(t−1) − 1.")
    inf_c = INF["inflacion_completa"].dropna(subset=["inflacion_mensual"])
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=inf_c.index, y=inf_c["inflacion_mensual"] * 100, name="Inflación mensual (%)",
                         marker_color=SEC_CL, opacity=0.8), secondary_y=True)
    fig.add_trace(go.Scatter(x=inf_c.index, y=inf_c["inflacion_anual"] * 100, name="Inflación anual (%)",
                             line=dict(color=PRIM, width=2.2)), secondary_y=False)
    fig.update_yaxes(title_text="Anual (%)", secondary_y=False)
    fig.update_yaxes(title_text="Mensual (%)", secondary_y=True, showgrid=False)
    grafica(layout(fig, "Inflación anual y mensual"))

    seccion("Precio de SORIANA B vs inflación anual", "Meses con ambos datos: nov-2021 a sep-2026.")
    reg = INF["regresion"]
    s = INF["serie"]
    c = st.columns(4)
    tarjeta(c[0], "Correlación", f"{INF['correlacion']:.4f}", f"{len(s)} meses")
    tarjeta(c[1], "Intercepto", f"{reg['intercepto']:.2f}", "pesos")
    tarjeta(c[2], "Pendiente", f"{reg['pendiente_por_pp']:.3f}", "pesos por punto porcentual")
    tarjeta(c[3], "R²", f"{reg['r2']:.3f}")
    c1, c2 = st.columns(2)
    grafica(fig_inflacion_activo(), c1)
    xs = np.linspace(s["inflacion_anual"].min(), s["inflacion_anual"].max(), 50)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s["inflacion_anual"] * 100, y=s["soriana"], mode="markers", name="Observado",
                             marker=dict(color=PRIM, size=7, opacity=0.8)))
    fig.add_trace(go.Scatter(x=xs * 100, y=reg["intercepto"] + reg["pendiente"] * xs, name="Regresión",
                             line=dict(color=CARBON, dash="dash", width=1.6)))
    fig.update_xaxes(title_text="Inflación anual (%)")
    fig.update_yaxes(title_text="Precio ($)")
    grafica(layout(fig, f"Precio = {reg['intercepto']:.2f} {reg['pendiente_por_pp']:+.3f} × inflación (pp)"), c2)

    seccion("Tendencias contra el tiempo", "x = 1 en nov-2021. La exponencial se estima con LN(y) contra x; a = e^(intercepto).")
    tl, te = INF["tendencia_precio_lineal"], INF["tendencia_precio_exponencial"]
    il, ie = INF["tendencia_inflacion_lineal"], INF["tendencia_inflacion_exponencial"]
    x = s["x"].values
    c1, c2 = st.columns(2)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=s["soriana"], mode="markers", name="Precio",
                             marker=dict(color=PRIM, size=6, opacity=0.8)))
    fig.add_trace(go.Scatter(x=x, y=tl["intercepto"] + tl["pendiente"] * x, name="Lineal",
                             line=dict(color=GRIS, width=1.8)))
    fig.add_trace(go.Scatter(x=x, y=te["a"] * np.exp(te["b"] * x), name="Exponencial",
                             line=dict(color=CARBON, dash="dash", width=1.6)))
    fig.update_xaxes(title_text="x (mes)")
    grafica(layout(fig, "Precio de SORIANA B"), c1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=s["inflacion_anual"] * 100, mode="markers", name="Inflación",
                             marker=dict(color=PRIM, size=6, opacity=0.8)))
    fig.add_trace(go.Scatter(x=x, y=(il["intercepto"] + il["pendiente"] * x) * 100, name="Lineal",
                             line=dict(color=GRIS, width=1.8)))
    fig.add_trace(go.Scatter(x=x, y=ie["a"] * np.exp(ie["b"] * x) * 100, name="Exponencial",
                             line=dict(color=CARBON, dash="dash", width=1.6)))
    fig.update_xaxes(title_text="x (mes)")
    fig.update_yaxes(title_text="%")
    grafica(layout(fig, "Inflación anual"), c2)
    modelos = pd.DataFrame([
        ["Precio", "Lineal", f"y = {tl['intercepto']:.4f} + {tl['pendiente']:.4f}·x", f"{tl['r2']:.4f}"],
        ["Precio", "Exponencial", f"y = {te['a']:.4f}·e^({te['b']:.5f}·x)", f"{te['r2']:.4f}"],
        ["Inflación anual", "Lineal", f"y = {il['intercepto']:.5f} + {il['pendiente']:.6f}·x", f"{il['r2']:.4f}"],
        ["Inflación anual", "Exponencial", f"y = {ie['a']:.5f}·e^({ie['b']:.5f}·x)", f"{ie['r2']:.4f}"],
    ], columns=["Serie", "Modelo", "Ecuación", "R²"])
    tabla(modelos, indice=False, izq=("Serie", "Modelo", "Ecuación"))

    pr = INF["pronostico"]
    seccion(f"Pronóstico de oct-2026 (x = {pr['x']})", f"Valor observado: {fd(pr['observado'])}.")
    tabla(pd.DataFrame([
        {"Modelo": k, "Pronóstico": fd(v), "Observado": fd(pr["observado"]),
         "Error": fd(v - pr["observado"]), "Error %": fp(v / pr["observado"] - 1)}
        for k, v in pr["modelos"].items()]), indice=False, izq=("Modelo",))

    seccion("SORIANA B vs S&P/BMV IPC", "Rendimientos mensuales y desempeño en base 100.")
    rg = IPC["regresion"]
    c = st.columns(3)
    tarjeta(c[0], "Correlación", f"{rg['correlacion']:.4f}", f"{rg['n']} rendimientos")
    tarjeta(c[1], "Pendiente (beta mensual)", f"{rg['pendiente']:.4f}")
    tarjeta(c[2], "R²", f"{rg['r2']:.4f}")
    c1, c2 = st.columns(2)
    grafica(fig_ipc_activo(), c1)
    si = IPC["serie"].dropna()
    xs = np.linspace(si["rend_ipc"].min(), si["rend_ipc"].max(), 20)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=si["rend_ipc"] * 100, y=si["rend_soriana"] * 100, mode="markers",
                             name="Meses", marker=dict(color=PRIM, size=7, opacity=0.8)))
    fig.add_trace(go.Scatter(x=xs * 100, y=(rg["intercepto"] + rg["pendiente"] * xs) * 100, name="Regresión",
                             line=dict(color=CARBON, dash="dash", width=1.6)))
    fig.update_xaxes(title_text="Rendimiento IPC (%)")
    fig.update_yaxes(title_text="Rendimiento SORIANA B (%)")
    grafica(layout(fig, "Rendimientos mensuales"), c2)


# ---------------------------------------------------------------------------
# 3. Beta y WACC
# ---------------------------------------------------------------------------

with tabs[2]:
    seccion("Beta con rendimientos diarios", "31-mar-2021 a 31-mar-2026. Beta = pendiente de SORIANA B contra el IPC.")
    c = st.columns(4)
    tarjeta(c[0], "Beta", f"{EST['beta']:.6f}", f"{EST['n_rendimientos']:,} rendimientos", destacada=True)
    tarjeta(c[1], "R²", f"{EST['r2']:.5f}")
    tarjeta(c[2], "Alfa diaria", f"{EST['alfa']:.6f}")
    tarjeta(c[3], "Correlación", f"{EST['correlacion']:.4f}")
    sd = EST["serie"].dropna()
    xs = np.linspace(sd["rend_ipc"].min(), sd["rend_ipc"].max(), 20)
    fig = go.Figure()
    fig.add_trace(go.Scattergl(x=sd["rend_ipc"] * 100, y=sd["rend_soriana"] * 100, mode="markers",
                               name="Días", marker=dict(color=PRIM, size=4, opacity=0.4)))
    fig.add_trace(go.Scatter(x=xs * 100, y=(EST["alfa"] + EST["beta"] * xs) * 100,
                             name=f"y = {EST['alfa']:.5f} + {EST['beta']:.4f}x", line=dict(color=CARBON, width=2.2)))
    fig.update_xaxes(title_text="Rendimiento diario IPC (%)")
    fig.update_yaxes(title_text="Rendimiento diario SORIANA B (%)")
    grafica(layout(fig, "Regresión de rendimientos diarios", 420))

    c1, c2 = st.columns([3, 2])
    with c1:
        seccion("Variables: calculado / manual / usado", "Si el campo manual está activo se usa ese valor.")
        filas = []
        for nombre, clave, es_pct in (("Beta", "beta", False), ("Rf", "rf", True), ("Rm", "rm", True),
                                      ("Prima de riesgo", "prima", True), ("Kd", "kd", True),
                                      ("WACC", "wacc", True)):
            d = CC[clave]
            f = (lambda v: fp(v, 4)) if es_pct else (lambda v: f"{v:.6f}")
            filas.append({"Variable": nombre, "Calculado": f(d["calculado"]),
                          "Manual": "—" if d["manual"] is None else f(d["manual"]), "Usado": f(d["usado"])})
        tabla(pd.DataFrame(filas), indice=False, izq=("Variable",))
        if CC["rf"]["traslado"]:
            st.caption(f"Rf incluye {fp(CC['rf']['traslado'])} por traslado de la inflación sobre 3%.")
    with c2:
        seccion("Métodos de Rf (bono)", f"Método seleccionado: {p['metodo_rf']}.")
        rf_tab = pd.DataFrame([
            {"Método": "1. Promedio del cambio % diario × 252", "Rf": fp(EST["rf_metodos"][1], 4)},
            {"Método": "2. Promedio del nivel / 100", "Rf": fp(EST["rf_metodos"][2], 4)},
            {"Método": "3. Último nivel / 100", "Rf": fp(EST["rf_metodos"][3], 4)},
        ])
        tabla(rf_tab, indice=False, izq=("Método",),
              estilos={(p["metodo_rf"] - 1, 0): "font-weight:700;color:#B23A33",
                       (p["metodo_rf"] - 1, 1): "font-weight:700;color:#B23A33"})

    seccion("Costo de la deuda (fuentes al 2T26)",
            f"Tasa del arrendamiento = ({p['gastos_financieros_trim']:,.0f} × 4 − Σ monto × tasa de las tres deudas) "
            f"/ saldo del arrendamiento = {fp(CC['kd_info']['tasa_arrendamiento'])}.")
    kd = CC["kd_info"]
    deuda = pd.DataFrame([{"Tipo": f["tipo"], "Monto (mdp)": fm(f["monto"], 0), "Tasa": fp(f["tasa"]),
                           "Peso": fp(f["peso"]), "Interés anual": fm(f["interes"])}
                          for f in kd["tabla"]], index=[f["fuente"] for f in kd["tabla"]])
    deuda.loc["Total / Kd"] = ["", fm(kd["total"], 0), fp(kd["kd"]), "100.00%", fm(kd["costo_anual"])]
    deuda.index.name = "Fuente"
    tabla(deuda, totales=("Total / Kd",), izq=("Tipo",))

    seccion("Cálculo paso a paso del WACC")
    pasos = pd.DataFrame([
        ["Ke = Rf + β × (Rm − Rf)",
         f"{fp(CC['rf']['usado'], 4)} + {CC['beta']['usado']:.4f} × {fp(CC['prima']['usado'], 4)}", fp(CC["ke"], 4)],
        ["Kd (promedio ponderado)", "Σ monto × tasa / Σ monto", fp(CC["kd"]["usado"], 4)],
        ["Kd después de impuestos", f"{fp(CC['kd']['usado'], 4)} × (1 − {fp(CC['isr'])})",
         fp(CC["kd"]["usado"] * (1 - CC["isr"]), 4)],
        ["Pesos", f"D = {fm(CC['d'], 0)} · E = {fm(CC['e'], 0)}", f"D/V {fp(CC['wd'])} · E/V {fp(CC['we'])}"],
        ["WACC = E/V × Ke + D/V × Kd × (1 − t)", "", fp(CC["wacc"]["calculado"], 4)],
        [f"WACC según el modo: {MODOS_WACC[CC['wacc']['modo']]}",
         "redondeo a 4 decimales" if CC["wacc"]["modo"] == "redondeado" else "sin redondeo",
         fp(CC["wacc"]["redondeado"] if CC["wacc"]["modo"] == "redondeado" else CC["wacc"]["calculado"], 4)],
        ["WACC usado (manual, si lo hay; si no, el del modo)", "", fp(CC["wacc"]["usado"], 4)],
        [f"WACC del escenario {escenario}", f"ajuste {fp(R['ajustes']['d_wacc'])}", fp(V["wacc"], 4)],
    ], columns=["Concepto", "Operación", "Resultado"], index=range(1, 9))
    pasos.index.name = "Paso"
    tabla(pasos, totales=(8,), izq=("Concepto", "Operación"))
    nota(f"<b>Referencia.</b> Con el capital a valor de mercado (precio × {fm(p['acciones'], 0)} millones de "
         f"acciones = {fm(CC['e_mercado'], 0)} mdp) el WACC sería <b>{fp(CC['wacc_mercado'], 4)}</b>. "
         "La valuación usa el capital contable en libros, como el Excel.")


# ---------------------------------------------------------------------------
# 4. Proyección y valuación
# ---------------------------------------------------------------------------

with tabs[3]:
    seccion(f"Proyección del FCFF 2026–2030 · escenario {escenario}",
            "FCFF = NOPAT + D&A − CAPEX − ΔCTNO. Cifras en millones de pesos.")
    proy = R["proyeccion"]
    pct_rows = {"Crecimiento de ventas", "Margen EBIT"}
    vista = pd.DataFrame({str(c): [fp(proy.loc[r, c]) if r in pct_rows else fm(proy.loc[r, c])
                                   for r in proy.index] for c in proy.columns}, index=proy.index)
    base_2025 = {"Ingresos": p["ingresos_base"], "Activo fijo neto": p["activo_fijo_base"],
                 "Pasivo por arrendamiento": p["pasivo_arr_base"],
                 "Capital de trabajo neto operativo": p["ctno_base"]}
    vista.insert(0, "2025", [fm(base_2025[r]) if r in base_2025 else "" for r in proy.index])
    vista.loc["Factor de descuento"] = [""] + [f"{f:.4f}" for f in V["factores"]]
    vista.loc["VP del FCFF"] = [""] + [fm(v) for v in V["vp_fcff"]]
    vista.index.name = "mdp"
    tabla(vista, totales=("FCFF", "VP del FCFF"),
          sutiles=("Crecimiento de ventas", "Margen EBIT", "Factor de descuento"))

    c = st.columns(4)
    tarjeta(c[0], "Σ VP de los flujos", fm(V["suma_vp_fcff"]), "2026–2030")
    tarjeta(c[1], "Valor terminal", fm(V["valor_terminal"]), "FCFF2030 × (1+g) / (WACC − g)")
    tarjeta(c[2], "VP del valor terminal", fm(V["vp_valor_terminal"]), f"{fp(V['peso_vt'], 1)} del EV")
    tarjeta(c[3], "Valor por acción", fd(V["valor_por_accion"]),
            f"Equity / {fm(p['acciones'], 0)} millones de acciones", destacada=True)

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
            increasing=dict(marker=dict(color=VERDE_M)), decreasing=dict(marker=dict(color=ROJO)),
            totals=dict(marker=dict(color=CARBON)), connector=dict(line=dict(color=GRIS_C))))
        fig.update_yaxes(title_text="mdp")
        grafica(layout(fig, "Cascada de Enterprise Value a Equity Value", 440))
    else:
        st.warning("Sin valor terminal no se puede construir la cascada de EV a Equity.")

    with st.expander("Históricos 2021–2025"):
        hd = DATA["historicos_2021_2025"]
        hist = pd.DataFrame({k: v for k, v in hd.items() if k != "anios"}, index=hd["anios"]).T
        hist.columns = [str(c) for c in hist.columns]
        hist.index.name = "mdp"
        tabla(hist.map(lambda v: fm(v, 0)))


# ---------------------------------------------------------------------------
# 5. Escenarios
# ---------------------------------------------------------------------------

with tabs[4]:
    seccion("Justificación de cada escenario", "Los textos son editables y se incluyen en el reporte PDF.")
    c = st.columns(3)
    for col, e in zip(c, m.ESCENARIOS):
        aj = p["escenarios"][e]
        with col.container(border=True):
            st.markdown(f"**{e}** · {esc_md(fd(ESC['resultados'][e]['valuacion']['valor_por_accion']))} por acción")
            st.text_area(f"Justificación {e}", key=PREFIJO + f"just_{e}", height=110, label_visibility="collapsed")
            st.caption(f"Δ ventas {fp(aj['d_crec'])} · Δ margen {fp(aj['d_margen'])} · Δ WACC {fp(aj['d_wacc'])} · "
                       f"probabilidad {fp(aj['prob'], 0)}")

    seccion("Tabla comparativa", "Crecimiento = promedio del crecimiento de ventas 2026–2030. "
                                 "Inflación = inflación de largo plazo.")
    comp = m.tabla_comparativa(p, ESC)
    formatos = {"Inflación": fp, "Crecimiento": fp, "Beta": lambda v: f"{v:.4f}", "WACC": fp,
                "Crecimiento perpetuo": fp, "Valor por acción": fd}
    vista = pd.DataFrame({e: [formatos.get(r, fm)(comp.loc[r, e]) for r in comp.index] for e in m.ESCENARIOS},
                         index=comp.index)
    vista.loc["Probabilidad"] = [fp(p["escenarios"][e]["prob"], 0) for e in m.ESCENARIOS]
    vista.index.name = "Concepto"
    tabla(vista, totales=("Valor por acción",), sutiles=("Probabilidad",))

    c1, c2 = st.columns([2, 3])
    with c1:
        tarjeta(st, "Valor ponderado por probabilidad", fd(ESC["ponderado"]),
                " · ".join(f"{e} {fp(p['escenarios'][e]['prob'], 0)}" for e in m.ESCENARIOS), destacada=True)
        seccion("Interpretación")
        nota(m.interpretacion_escenarios(p, DATA, EST, ESC).replace("**", ""))
    grafica(fig_escenarios(), c2)


# ---------------------------------------------------------------------------
# 6. Sensibilidad
# ---------------------------------------------------------------------------

with tabs[5]:
    seccion("Matriz WACC vs crecimiento perpetuo (valor por acción)",
            "Filas: WACC base ± 1 pp en pasos de 0.5 pp. Columnas: g. La celda con borde es el caso actual.")
    mat = matriz()
    i_base, j_base = celda_base(mat)
    z = mat.values.astype(float)
    vmin, vmax = np.nanmin(z) if np.isfinite(z).any() else 0, np.nanmax(z) if np.isfinite(z).any() else 0
    vista = pd.DataFrame([[fd(v) for v in fila] for fila in z], index=[fp(w) for w in mat.index],
                         columns=[f"g {fp(g, 1)}" for g in mat.columns])
    vista.index.name = "WACC"
    estilos = {}
    for i in range(z.shape[0]):
        for j in range(z.shape[1]):
            fondo, letra = color_calor(z[i, j], vmin, vmax)
            estilos[(i, j)] = f"background:{fondo};color:{letra};text-align:center"
            if i == i_base and j == j_base:
                estilos[(i, j)] += f";outline:3px solid {CARBON};outline-offset:-3px;font-weight:700"
    tabla(vista, estilos=estilos)

    seccion("Gráficas de una variable", "La línea punteada marca el valor actual de cada variable.")
    c1, c2 = st.columns(2)
    cv = m.curva(p, DATA, EST, escenario, "inflacion", np.arange(0.01, 0.0601, 0.0025))
    fig = go.Figure(go.Scatter(x=cv["x"] * 100, y=cv["y"], line=dict(color=PRIM, width=2.4)))
    fig.add_vline(x=p["inflacion_lp"] * 100, line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="Inflación de largo plazo (%)")
    fig.update_yaxes(title_text="$ por acción")
    grafica(layout(fig, "Inflación vs valor por acción"), c1)

    cv = m.curva(p, DATA, EST, escenario, "wacc", np.arange(max(V["g"] + 0.005, 0.05), 0.1301, 0.0025))
    fig = go.Figure(go.Scatter(x=cv["x"] * 100, y=cv["y"], line=dict(color=PRIM, width=2.4)))
    fig.add_vline(x=V["wacc"] * 100, line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="WACC (%)")
    fig.update_yaxes(title_text="$ por acción")
    grafica(layout(fig, "WACC vs valor por acción"), c2)

    c1, c2 = st.columns(2)
    cv = m.curva(p, DATA, EST, escenario, "crecimiento", np.arange(-0.05, 0.0501, 0.005))
    fig = go.Figure(go.Scatter(x=cv["x"] * 100, y=cv["y"], line=dict(color=PRIM, width=2.4)))
    fig.add_vline(x=float(np.mean(R["proyeccion"].loc["Crecimiento de ventas"])) * 100,
                  line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="Crecimiento promedio de ventas 2026–2030 (%)")
    fig.update_yaxes(title_text="Enterprise Value (mdp)")
    grafica(layout(fig, "Crecimiento vs Enterprise Value"), c1)

    cv = m.curva(p, DATA, EST, escenario, "beta", np.arange(0, 1.501, 0.05))
    fig = go.Figure(go.Scatter(x=cv["x"], y=cv["y"] * 100, line=dict(color=PRIM, width=2.4)))
    fig.add_vline(x=CC["beta"]["usado"], line=dict(color=GRIS, dash="dot"))
    fig.update_xaxes(title_text="Beta")
    fig.update_yaxes(title_text="Ke (%)")
    grafica(layout(fig, "Beta vs costo de capital (Ke)"), c2)

    seccion("Tornado: cada variable ±10%", "Variables ordenadas por su impacto en el valor por acción.")
    tor = m.tornado(p, DATA, EST, escenario)
    base = tor.attrs["base"]
    if base is not None:
        c1, c2 = st.columns([3, 2])
        fig = go.Figure()
        fig.add_trace(go.Bar(y=tor["Variable"], x=tor["-10%"] - base, base=base, orientation="h",
                             name="Variable −10%", marker_color=PRIM_CL,
                             hovertemplate="%{y}: $%{x:,.2f}<extra>−10%</extra>"))
        fig.add_trace(go.Bar(y=tor["Variable"], x=tor["+10%"] - base, base=base, orientation="h",
                             name="Variable +10%", marker_color=PRIM,
                             hovertemplate="%{y}: $%{x:,.2f}<extra>+10%</extra>"))
        fig.add_vline(x=base, line=dict(color="#344054", width=1))
        fig.update_layout(barmode="overlay")
        fig.update_xaxes(title_text="Valor por acción ($)")
        grafica(layout(fig, f"Impacto en el valor por acción (base {fd(base)})", 540), c1)
        t = tor.iloc[::-1].copy()
        with c2:
            tabla(pd.DataFrame({"Variable": t["Variable"].values, "−10%": t["-10%"].map(fd).values,
                                "+10%": t["+10%"].map(fd).values, "Rango": t["Impacto"].map(fd).values}),
                  indice=False, izq=("Variable",))
    else:
        st.warning("El tornado requiere que el WACC sea mayor que g.")


# ---------------------------------------------------------------------------
# Valuación relativa: tablas y gráficas compartidas
# ---------------------------------------------------------------------------

def _fx(v, dec=2):
    return "n.d." if _nd(v) else f"{v:,.{dec}f}x"


def tabla_estadisticos_html(est_df):
    vista = est_df.loc[relativa.ESTADISTICOS].copy()
    vista = vista.map(lambda v: _fx(v)) if hasattr(vista, "map") else vista
    vista.loc["Observaciones"] = [str(int(est_df.loc["n", c])) for c in est_df.columns]
    vista.index.name = "Estadístico"
    tabla(vista, sutiles=("Observaciones",))


def tabla_precios_html(res, multiplos):
    filas = []
    for k in multiplos:
        nombre = relativa.NOMBRE_MULTIPLO[k]
        mult = res["estadisticos"].loc[res["estadistico"], nombre]
        metrica, con_puente = relativa.METRICA[k]
        base = None if mult is None else mult * REL["metricas_soriana_2025"][metrica]
        aj = relativa.ajuste_neto(REL) if con_puente else 0
        filas.append({
            "Múltiplo": nombre, f"{res['estadistico']}": _fx(mult),
            "Métrica de Soriana 2025": fm(REL["metricas_soriana_2025"][metrica], 0),
            "Valor implícito": fm(base, 0), "Ajuste a Equity": fm(aj, 0) if con_puente else "no aplica",
            "Equity": fm(None if base is None else base + aj, 0), "Precio por acción": fd(res["precios"][nombre]),
        })
    df = pd.DataFrame(filas).set_index("Múltiplo")
    df.loc["Promedio de los múltiplos"] = [""] * (len(df.columns) - 1) + [fd(res["valor"])]
    tabla(df, totales=("Promedio de los múltiplos",))


def editor_inclusion(filas, columnas, clave, numericas):
    """Tabla con casilla Incluir; el resto de las columnas es de solo lectura."""
    df = pd.DataFrame([{"Incluir": bool(f["incluir"]),
                        **{et: (_fx(f.get(k)) if et in numericas else f.get(k)) for k, et in columnas}} for f in filas])
    st.data_editor(df, key=clave, hide_index=True, width="stretch", disabled=[c for c in df.columns if c != "Incluir"],
                   column_config={"Incluir": st.column_config.CheckboxColumn("Incluir", width="small")})


def selector_estadistico(clave, texto):
    st.radio(texto, relativa.ESTADISTICOS, key=clave, horizontal=True)


# ---------------------------------------------------------------------------
# 9. Empresas comparables
# ---------------------------------------------------------------------------

with SUB_REL[0]:
    comp = VR["comparables"]
    ref = REL["comparables"]["soriana_referencia"]
    seccion("Empresas comparables", f"Fuente: {REL['comparables']['fuente']}. Marca o desmarca los pares que "
                                    "entran en los estadísticos.")
    editor_inclusion(REL["comparables"]["pares"],
                     [("empresa", "Empresa"), ("ticker", "Ticker"), ("pais", "País"), ("ev_ebitda", "EV/EBITDA"),
                      ("ev_ventas", "EV/Ventas"), ("p_u", "P/U"), ("justificacion", "Justificación")],
                     PREFIJO + "editor_comp", ["EV/EBITDA", "EV/Ventas", "P/U"])
    nota(f"<b>Soriana (referencia):</b> {_fx(ref['ev_ebitda'])} EV/EBITDA, {_fx(ref['ev_ventas'])} EV/Ventas y "
         f"{_fx(ref['p_u'], 1)} P/U en Capital IQ (con precio anterior); no entra en los estadísticos. "
         f"<b>Excluidos:</b> {h(REL['comparables']['excluidos'])}.")

    c1, c2 = st.columns([1, 1])
    filas_c = comp["filas"]
    nombres = [f["empresa"] for f in filas_c] + ["Soriana (ref.)"]
    valores = [f["ev_ebitda"] for f in filas_c] + [ref["ev_ebitda"]]
    colores = [SEC if f["incluir"] else GRIS_C for f in filas_c] + [PRIM]
    fig = go.Figure(go.Bar(x=nombres, y=valores, marker_color=colores, text=[_fx(v) for v in valores],
                           textposition="outside", width=0.6, hovertemplate="%{x}: %{y:.2f}x<extra></extra>"))
    media = comp["estadisticos"].loc["Media", "EV/EBITDA"]
    if media is not None:
        fig.add_trace(go.Scatter(x=nombres, y=[media] * len(nombres), mode="lines", name=f"Media de pares {_fx(media)}",
                                 line=dict(color=CARBON, dash="dash", width=1.5), hoverinfo="skip"))
    fig.update_layout(showlegend=True)
    fig.update_yaxes(title_text="EV/EBITDA (veces)")
    grafica(layout(fig, "EV/EBITDA por par (Soriana resaltada; gris = excluido)", 380), c1)
    with c2:
        tabla_estadisticos_html(comp["estadisticos"])

    seccion("Precio implícito por múltiplo",
            "EV/EBITDA y EV/Ventas: Equity = múltiplo × métrica + ajuste neto (−10,165 mdp). P/U: Equity = P/U × "
            "utilidad neta de la controladora, sin puente. Precio = Equity / 1,800 millones de acciones.")
    selector_estadistico(PREFIJO + "est_comp", "Estadístico")
    tabla_precios_html(comp, relativa.MULTIPLOS_COMPARABLES)
    c = st.columns(3)
    dif_c = None if comp["valor"] is None else comp["valor"] / p["precio_mercado"] - 1
    tarjeta(c[0], "Valor por comparables", fd(comp["valor"]), "Promedio de EV/EBITDA, EV/Ventas y P/U",
            destacada=True)
    tarjeta(c[1], "Diferencia vs precio", "n.d." if dif_c is None else f"{'+' if dif_c >= 0 else ''}{fp(dif_c, 1)}",
            f"Precio de mercado {fd(p['precio_mercado'])}", "" if dif_c is None else ("pos" if dif_c >= 0 else "neg"))
    tarjeta(c[2], "Pares incluidos", f"{sum(1 for f in filas_c if f['incluir'])} de {len(filas_c)}",
            "Soriana no entra en los estadísticos")
    seccion("Lectura")
    nota("<b>EV/EBITDA es el ancla</b>: no lo distorsionan la deuda ni los arrendamientos, porque compara el valor "
         "de la operación con su flujo. <b>EV/Ventas sobrevalúa a Soriana</b> porque su margen es menor que el de sus "
         "pares: cada peso de venta genera menos EBITDA. <b>P/U la subvalúa</b> porque su utilidad neta está "
         "presionada por los intereses de la deuda y los arrendamientos.")


# ---------------------------------------------------------------------------
# 10. Transacciones precedentes
# ---------------------------------------------------------------------------

with SUB_REL[1]:
    tr = VR["transacciones"]
    seccion("Transacciones precedentes", f"Fuente: {REL['transacciones']['fuente']}.")
    c = st.columns(3)
    tarjeta(c[0], "Operaciones", f"{tr['n_total']} → {tr['n_incluidas']} incluidas",
            "Se depuran otros giros, múltiplos atípicos y datos faltantes")
    tarjeta(c[1], "Media EV/EBITDA, muestra completa", _fx(tr["media_ev_ebitda_muestra_completa"], 1),
            "Todas las operaciones con dato")
    tarjeta(c[2], "Media EV/EBITDA, muestra depurada", _fx(tr["media_ev_ebitda_depurada"]),
            "Solo las operaciones incluidas", destacada=True)
    editor_inclusion(REL["transacciones"]["operaciones"],
                     [("objetivo", "Objetivo"), ("comprador", "Comprador"), ("pais", "País"), ("anuncio", "Anuncio"),
                      ("ev_ventas", "EV/Ventas"), ("ev_ebitda", "EV/EBITDA"), ("ev_ebit", "EV/EBIT"),
                      ("motivo", "Motivo")],
                     PREFIJO + "editor_trans", ["EV/Ventas", "EV/EBITDA", "EV/EBIT"])
    c1, c2 = st.columns([1, 1])
    filas_t = tr["filas"]
    fig = go.Figure()
    xs = [f["objetivo"] for f in filas_t if f["ev_ebitda"] is not None]
    ys = [f["ev_ebitda"] for f in filas_t if f["ev_ebitda"] is not None]
    cs = [SEC if f["incluir"] else GRIS_C for f in filas_t if f["ev_ebitda"] is not None]
    fig.add_trace(go.Bar(x=xs, y=ys, marker_color=cs, text=[_fx(v, 1) for v in ys], textposition="outside",
                         width=0.6, hovertemplate="%{x}: %{y:.2f}x<extra></extra>", showlegend=False))
    fig.add_trace(go.Scatter(x=xs, y=[tr["media_ev_ebitda_muestra_completa"]] * len(xs), mode="lines",
                             name=f"Media muestra completa {_fx(tr['media_ev_ebitda_muestra_completa'], 1)}",
                             line=dict(color=GRIS, dash="dot", width=1.6), hoverinfo="skip"))
    if tr["media_ev_ebitda_depurada"] is not None:
        fig.add_trace(go.Scatter(x=xs, y=[tr["media_ev_ebitda_depurada"]] * len(xs), mode="lines",
                                 name=f"Media depurada {_fx(tr['media_ev_ebitda_depurada'])}",
                                 line=dict(color=PRIM, dash="dash", width=1.6), hoverinfo="skip"))
    fig.update_yaxes(title_text="EV/EBITDA (veces)")
    grafica(layout(fig, "EV/EBITDA por operación (gris = excluida)", 380), c1)
    with c2:
        tabla_estadisticos_html(tr["estadisticos"])
    seccion("Precio implícito por múltiplo", "Equity = múltiplo × métrica de Soriana + ajuste neto (−10,165 mdp).")
    selector_estadistico(PREFIJO + "est_trans", "Estadístico")
    tabla_precios_html(tr, relativa.MULTIPLOS_TRANSACCIONES)
    c = st.columns(2)
    dif_t = None if tr["valor"] is None else tr["valor"] / p["precio_mercado"] - 1
    tarjeta(c[0], "Valor por transacciones", fd(tr["valor"]), "Promedio de EV/Ventas, EV/EBITDA y EV/EBIT",
            destacada=True)
    tarjeta(c[1], "Diferencia vs precio", "n.d." if dif_t is None else f"{'+' if dif_t >= 0 else ''}{fp(dif_t, 1)}",
            f"Precio de mercado {fd(p['precio_mercado'])}", "" if dif_t is None else ("pos" if dif_t >= 0 else "neg"))


# ---------------------------------------------------------------------------
# 11. Precio objetivo
# ---------------------------------------------------------------------------

with TOP[3]:
    seccion("Valor por método", f"DCF con WACC {fp(VR['wacc'], 4)}: {MODOS_WACC[modo_wacc]}.")
    c = st.columns(3)
    tarjeta(c[0], "DCF (escenario base)", fd(VR["dcf"]), f"WACC {fp(VR['wacc'])}")
    tarjeta(c[1], "Empresas comparables", fd(VR["comparables"]["valor"]), VR["comparables"]["estadistico"])
    tarjeta(c[2], "Transacciones precedentes", fd(VR["transacciones"]["valor"]), VR["transacciones"]["estadistico"])

    c1, c2 = st.columns(2)
    with c1:
        seccion("Ponderaciones", "Editables; deben sumar 100%.")
        cc_ = st.columns(3)
        for col, (k, nombre) in zip(cc_, [("dcf", "DCF (%)"), ("comparables", "Comparables (%)"),
                                          ("transacciones", "Transacciones (%)")]):
            with col:
                campo(nombre, PREFIJO + f"pond_{k}", POND_DEFAULT[k] * 100, 2)
        if PO["aviso"]:
            st.warning(f"Las ponderaciones suman {fp(PO['suma'], 2)}; deben sumar 100%.")
        else:
            st.caption(f"Suma: {fp(PO['suma'], 2)}")
    with c2:
        seccion("Regla del equipo", "Umbrales de potencial para la recomendación.")
        cc_ = st.columns(2)
        with cc_[0]:
            campo("Comprar si el potencial es mayor a (%)", PREFIJO + "umbral_comprar",
                  relativa.UMBRALES_DEFAULT["comprar"] * 100, 1)
        with cc_[1]:
            campo("Vender si el potencial es menor a (%)", PREFIJO + "umbral_vender",
                  relativa.UMBRALES_DEFAULT["vender"] * 100, 1)
        st.caption("Entre ambos umbrales: MANTENER.")

    c = st.columns(3)
    pot = PO["potencial"]
    tarjeta(c[0], "Precio objetivo (12 meses)", fd(PO["objetivo"]),
            " + ".join(f"{fp(POND[k], 1)} {n}" for k, n in
                       [("dcf", "DCF"), ("comparables", "comp."), ("transacciones", "trans.")]), destacada=True)
    tarjeta(c[1], "Potencial", "n.d." if pot is None else f"{'+' if pot >= 0 else ''}{fp(pot, 1)}",
            f"Precio de mercado {fd(p['precio_mercado'])}", "" if pot is None else ("pos" if pot >= 0 else "neg"))
    with c[2]:
        recomendacion_html(PO["recomendacion"], UMBRALES)
    grafica(fig_football())
    nota(f"Al precio de mercado de {fd(p['precio_mercado'])}, Soriana cotiza a <b>{_fx(VR['ev_ebitda_al_precio'])} "
         f"EV/EBITDA</b>, por debajo de la media de sus comparables ({_fx(VR['comparables']['estadisticos'].loc['Media', 'EV/EBITDA'])}).")

    seccion("Contraste con LSEG", REL["lseg"]["fuente"])
    lseg = VR["lseg"]
    c1, c2 = st.columns([3, 2])
    with c1:
        df = pd.DataFrame([{"Empresa": e["empresa"], "RIC": e["ric"], "EV/EBITDA": _fx(e["ev_ebitda"]),
                            "P/U adelantado": _fx(e["p_u_fwd"], 1), "P/VL": _fx(e["p_vl"])} for e in lseg["empresas"]])
        sor = df.index[df["Empresa"] == "Soriana"][0]
        tabla(df, indice=False, izq=("Empresa", "RIC"),
              estilos={(sor, j): f"font-weight:700;color:{PRIM}" for j in range(5)})
    with c2:
        tarjeta(st, "Media de pares EV/EBITDA (sin Soriana)", _fx(lseg["media_pares_ev_ebitda"]),
                f"Precio implícito {fd(lseg['precio_implicito'])}", destacada=True)
        nota(f"Soriana cotiza a <b>{_fx(lseg['soriana']['p_vl'])}</b> su valor en libros, la más barata del grupo.")


# ---------------------------------------------------------------------------
# 12. Contexto financiero
# ---------------------------------------------------------------------------

with TOP[4]:
    cf = REL["contexto_financiero"]
    anios = [str(a) for a in cf["anios"]]
    seccion("Márgenes 2021–2025", "El margen bruto sube, pero el margen EBITDA cae: los gastos crecen más que la venta.")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=anios, y=[v * 100 for v in cf["margen_bruto"]], name="Margen bruto",
                             mode="lines+markers+text", text=[fp(v, 1) for v in cf["margen_bruto"]],
                             textposition="top center", line=dict(color=VERDE_M, width=2.6)))
    fig.add_trace(go.Scatter(x=anios, y=[v * 100 for v in cf["margen_ebitda"]], name="Margen EBITDA",
                             mode="lines+markers+text", text=[fp(v, 1) for v in cf["margen_ebitda"]],
                             textposition="top center", line=dict(color=PRIM, width=2.6)))
    fig.update_yaxes(title_text="% de las ventas", rangemode="tozero")
    grafica(layout(fig, "Margen bruto vs margen EBITDA", 380))

    seccion("Razones financieras")
    razones = pd.DataFrame({
        "ROE": [fp(v, 1) for v in cf["roe"]], "ROA": [fp(v, 1) for v in cf["roa"]],
        "Razón circulante": [f"{v:.2f}x" for v in cf["razon_circulante"]],
        "Deuda con costo / EBITDA": [f"{v:.2f}x" for v in cf["deuda_con_costo_ebitda"]],
        "Flujo de operación / utilidad": [f"{v:.2f}x" for v in cf["flujo_operacion_utilidad"]],
        "Margen neto": [fp(v, 1) for v in cf["margen_neto"]],
    }, index=anios).T
    razones.index.name = "Razón"
    tabla(razones)

    seccion("Datos clave y su efecto en los supuestos")
    gg = cf["gastos_generales_sobre_ventas"]
    ke = CC["ke"]
    c = st.columns(4)
    datos_clave = [
        ("Crecimiento", f"{fp(cf['cagr_ventas_soriana_2021_2025'], 1)} vs {fp(cf['cagr_antad_2022_2025'], 1)}",
         "CAGR de ventas de Soriana contra el sector (ANTAD).",
         "Las ventas se proyectan con la g del sector decreciente y el escenario conservador resta 3 pp."),
        ("Gastos generales", f"{fp(gg['2021'], 1)} → {fp(gg['2025'], 1)}", "Gastos generales sobre ventas, 2021 a 2025.",
         "Presionan el margen EBIT; por eso se usa un margen base de 4.25% y el conservador resta 0.5 pp."),
        ("Flujo de operación", f"{cf['flujo_operacion_utilidad'][-1]:.1f}x", "Flujo de operación sobre utilidad neta, 2025.",
         "La caja es mucho mayor que la utilidad: valuar por flujos (FCFF) captura mejor el valor que P/U."),
        ("ROE vs Ke", f"{fp(cf['roe'][-1], 1)} vs {fp(ke, 2)}", "Rentabilidad sobre capital contra costo de capital.",
         "El ROE está debajo del Ke: explica el P/VL bajo y castiga el WACC en el escenario conservador."),
    ]
    for col, (t, v, s_, efecto) in zip(c, datos_clave):
        with col:
            tarjeta(st, t, v, s_)
            st.caption(f"**Efecto:** {efecto}")
    mac = cf["macro"]
    nota(f"<b>Contexto macro:</b> tasa de Banxico {fp(mac['tasa_banxico'], 2)}, inflación de sep-2026 "
         f"{fp(mac['inflacion_sep_2026'], 2)} y tipo de cambio de {mac['tipo_cambio_aprox']:.1f} pesos por dólar.")


# ---------------------------------------------------------------------------
# 7. Validación contra Excel
# ---------------------------------------------------------------------------

with tabs[6]:
    nota("<b>Nota.</b> " + m.nota_modos(resumen_modos(), fp, fd))
    val, red = validacion_excel()
    n_pass = int((val["Estado"] == "PASS").sum())
    c = st.columns(3)
    tarjeta(c[0], "Resultado", f"{n_pass} de {len(val)} en PASS", "Criterio: diferencia menor a 0.01%",
            destacada=True)
    tarjeta(c[1], "Diferencia máxima", f"{val['Diferencia %'].abs().max() * 100:.2e}%", "en valor absoluto")
    tarjeta(c[2], "Valores comparados", "Defaults del Excel", "Sin importar lo que se mueva en la barra lateral")

    seccion("Validación contra el Excel integrador", f"Siempre con el WACC exacto de "
            f"{fp(resumen_modos()['exacto']['wacc'], 4)}. Celdas: '7 Valuación'!B11, B12, B16, B18, B24, B26 y '9 Escenarios'!B12:D12.")

    def _f(k, v):
        return fp(v, 4) if k in ("WACC", "g") else (fd(v, 4) if "acción" in k else fm(v, 2))

    vista = pd.DataFrame({
        "Variable": val["Variable"].values,
        "Excel": [_f(k, v) for k, v in zip(val["Variable"], val["Excel"])],
        "App": [_f(k, v) for k, v in zip(val["Variable"], val["App"])],
        "Diferencia": [f"{d:.2e}" for d in val["Diferencia"]],
        "Diferencia %": [f"{d * 100:.2e}%" for d in val["Diferencia %"]],
        "Estado": [f"<span class='badge {'ok' if e == 'PASS' else 'mal'}'>{e}</span>" for e in val["Estado"]],
    })
    tabla(vista, indice=False, izq=("Variable",))
    nota(
        f"<b>Fuente de los valores del Excel:</b> {h(val.attrs['fuente'])}.<br><br>"
        "<b>Nota sobre diferencias.</b> Esta tabla se calcula siempre con el WACC exacto y los valores por defecto, "
        "sin importar lo que se haya movido en la barra lateral. La app trabaja con la misma precisión que Excel "
        "(doble precisión), por lo que las diferencias son del orden de 10⁻¹⁰ y vienen solo del orden de las "
        f"operaciones de punto flotante. Con el WACC redondeado a {fp(red['wacc_redondeado'])}, el modo por defecto "
        f"de la app, el valor sale <b>{fd(red['valor_por_accion'])}</b> en lugar de <b>{fd(val.iloc[5]['Excel'])}</b>."
    )


with TOP[5]:
    vb = validacion_banamex()
    nb = int((vb["Estado"] == "PASS").sum())
    seccion("Validación contra el reporte Banamex",
            f"Siempre con el WACC redondeado a {fp(resumen_modos()['redondeado']['wacc'])} y los valores por defecto, "
            "sin importar lo que haya en pantalla. "
            "Tolerancia de redondeo: ±0.01 en pesos por acción y ±1 mdp en montos.")

    def _fu(v, u):
        return {"mdp": fm(v, 1), "$": fd(v, 2), "%": fp(v, 1), "x": _fx(v)}[u]

    vista = pd.DataFrame({
        "Concepto": vb["Concepto"].values,
        "Reporte": [_fu(v, u) for v, u in zip(vb["Reporte"], vb["Unidad"])],
        "App": [_fu(v, u) for v, u in zip(vb["App"], vb["Unidad"])],
        "Diferencia": [f"{d:+.4f}" if u != "%" else f"{d * 100:+.3f} pp" for d, u in zip(vb["Diferencia"], vb["Unidad"])],
        "Tolerancia": [{"mdp": "±1 mdp", "$": "±$0.01", "%": "±0.1 pp", "x": "±0.01x"}[u] for u in vb["Unidad"]],
        "Estado": [f"<span class='badge {'ok' if e == 'PASS' else 'mal'}'>{e}</span>" for e in vb["Estado"]],
    })
    tarjeta(st, "Reporte Banamex", f"{nb} de {len(vb)} en PASS",
            f"WACC redondeado a {fp(resumen_modos()['redondeado']['wacc'])} · valores por defecto",
            destacada=True)
    tabla(vista, indice=False, izq=("Concepto",))


# ---------------------------------------------------------------------------
# 8. Reporte PDF
# ---------------------------------------------------------------------------

with tabs[7]:
    c1, c2 = st.columns([3, 2])
    with c1:
        seccion("Reporte PDF", f"Refleja los valores que están en pantalla en este momento (escenario {escenario}).")
        contenido = ["Nombre del estudiante", "Empresa analizada", "Variables utilizadas", "Modelo financiero", "Beta",
                     "WACC", "Crecimiento perpetuo", "Valor terminal", "Enterprise Value", "Equity Value",
                     "Valor por acción", "Escenario conservador", "Escenario base", "Escenario optimista",
                     "Valuación relativa", "Precio objetivo y recomendación", "Rango de valuación (football field)",
                     "Contraste con LSEG", "Gráficas", "Validación", "Conclusiones"]
        mitad = (len(contenido) + 1) // 2
        a, b = st.columns(2)
        a.markdown("\n".join(f"{i}. {t}" for i, t in enumerate(contenido[:mitad], 1)))
        b.markdown("\n".join(f"{i}. {t}" for i, t in enumerate(contenido[mitad:], mitad + 1)))
    with c2:
        with st.container(border=True):
            st.markdown(f"**{NOMBRE_PDF}**")
            st.caption(f"Valor por acción {esc_md(fd(V['valor_por_accion']))} · WACC {fp(V['wacc'])} · "
                       f"g {fp(V['g'])}")
            boton_pdf(st, "pdf_pestana")
            st.caption("El PDF se genera al hacer clic y se descarga directamente (tarda unos segundos).")
