"""Elementos de interfaz hechos en HTML/CSS/JS: barra de íconos y tutorial de bienvenida.

Se insertan con st.html(..., unsafe_allow_javascript=True), que ejecuta el script en el documento de la app.
Ambos elementos se crean una sola vez y viven fuera del árbol de Streamlit, así que los reruns no los tocan.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"

# Íconos de línea (24×24, trazo 1.8), estilo consistente entre sí.
_SVG = {
    "menu": '<path d="M13 6l6 6-6 6"/><path d="M5 6l6 6-6 6"/>',
    "escenario": '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
    "economicas": '<path d="M4 19h16"/><path d="M6 15l4-4 3 3 5-6"/><path d="M15 8h3v3"/>',
    "mercado": '<path d="M7 4v16"/><rect x="5" y="8" width="4" height="7" rx="1"/><path d="M17 4v16"/>'
               '<rect x="15" y="6" width="4" height="9" rx="1"/>',
    "financieras": '<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="12" cy="12" r="2.5"/>'
                   '<path d="M6 9h.01M18 15h.01"/>',
    "valuacion": '<path d="M4 21h16"/><path d="M5 21V10l7-5 7 5v11"/><path d="M9 21v-6h6v6"/>',
    "ajustes": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/>'
               '<circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "pdf": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'
           '<path d="M12 11v6M9.5 14.5L12 17l2.5-2.5"/>',
    "ayuda": '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.3a2.5 2.5 0 0 1 4.8.9c0 1.7-2.4 2.2-2.4 3.6"/>'
             '<path d="M12 17h.01"/>',
}


def _icono(nombre: str) -> str:
    return (f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{_SVG[nombre]}</svg>')


def imagen_b64(nombre: str) -> str:
    return "data:image/png;base64," + base64.b64encode((ASSETS / nombre).read_bytes()).decode()


# Secciones de la barra lateral que aparecen como íconos cuando se colapsa.
SECCIONES = [
    ("escenario", "Escenario", "radio"),
    ("economicas", "Económicas", "expander"),
    ("mercado", "Mercado", "expander"),
    ("financieras", "Financieras", "expander"),
    ("valuacion", "Valuación", "expander"),
    ("ajustes", "Ajustes de escenarios", "expander"),
]

PASOS_TUTORIAL = [
    ("Bienvenida",
     "Esta app valúa <b>Organización Soriana (SORIANA B)</b> con flujos de caja descontados (FCFF) y "
     "reproduce el modelo de Excel. Incluye valor por acción, tres escenarios, sensibilidad, validación "
     "contra el Excel y un reporte PDF."),
    ("Mueve las variables",
     "En la <b>barra lateral</b> eliges el escenario y editas las variables por grupo: Económicas, Mercado, "
     "Financieras y Valuación. Cada cambio recalcula toda la cadena: "
     "<b>Beta → WACC → Flujos → Valor terminal → EV → Equity → Valor por acción</b>. "
     "Con <i>Usar valor manual</i> reemplazas un valor calculado."),
    ("Explora las pestañas",
     "<b>Dashboard</b> resume los resultados. <b>Inflación y mercado</b> y <b>Beta y WACC</b> muestran las "
     "regresiones y el costo de capital. <b>Proyección</b> tiene el FCFF 2026–2030, <b>Escenarios</b> los "
     "compara y <b>Sensibilidad</b> muestra la matriz WACC–g y el tornado."),
    ("Valida y descarga",
     "<b>Validación contra Excel</b> compara la app con el modelo original. <b>Descargar reporte PDF</b> genera "
     "el reporte con los valores en pantalla. Puedes volver a ver esta guía con <b>Ver tutorial</b> en la barra "
     "lateral o con el ícono <b>?</b> cuando está cerrada."),
]


def css(prim: str, prim_cl: str, carbon: str, gris_texto: str) -> str:
    return f"""
    <style>
    /* Logo en la barra lateral, a la altura del botón de colapsar */
    [data-testid="stSidebarHeader"] {{ height: 3.4rem; }}
    [data-testid="stSidebarUserContent"] {{ padding-top: 0 !important; }}
    .lateral-logo {{ margin: -3.05rem 0 14px 2px; height: 40px; width: max-content; display: flex;
                     align-items: center; pointer-events: none; position: relative; z-index: 0; }}
    .lateral-logo img {{ height: 34px; width: auto; display: block; }}

    /* Los bloques que solo contienen estilos o scripts no deben ocupar espacio */
    [data-testid="stElementContainer"]:has(> [data-testid="stHtml"] script),
    [data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style) {{ display: none; }}
    .block-container {{ padding-top: 2.6rem !important; }}
    [data-testid="stHeader"] {{ background: transparent !important; pointer-events: none; }}
    [data-testid="stHeader"] * {{ pointer-events: auto; }}
    [data-testid="stDecoration"] {{ display: none; }}

    /* Pestañas compactas para que quepan las ocho */
    [data-baseweb="tab-list"] {{ gap: 0 !important; }}
    [data-baseweb="tab"] {{ padding: 10px 9px !important; }}
    [data-baseweb="tab"] p {{ font-size: .875rem !important; }}

    /* Barra de íconos cuando la barra lateral está cerrada */
    #riel {{ position: fixed; top: 0; left: 0; bottom: 0; width: 60px; z-index: 1000001;
             background: {carbon}; display: none; flex-direction: column; align-items: center;
             padding: 12px 0; gap: 4px; box-shadow: 1px 0 0 rgba(0,0,0,.06);
             animation: rielEntra .25s ease-out both; }}
    @keyframes rielEntra {{ from {{ transform: translateX(-100%); }} to {{ transform: none; }} }}
    body:has([data-testid="stSidebar"][aria-expanded="false"]) #riel {{ display: flex; }}
    body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stMain"] {{ padding-left: 60px; }}
    body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"] {{
        opacity: 0; pointer-events: none; }}
    #riel .marca {{ width: 34px; height: 34px; margin: 2px 0 10px 0; }}
    #riel .marca img {{ width: 100%; height: 100%; }}
    #riel .sep {{ width: 28px; height: 1px; background: rgba(255,255,255,.14); margin: 6px 0; }}
    #riel .espacio {{ flex: 1; }}
    #riel button {{ all: unset; box-sizing: border-box; width: 44px; height: 42px; border-radius: 10px;
                    display: flex; align-items: center; justify-content: center; color: #E9E6E3;
                    cursor: pointer; position: relative; transition: background-color .18s ease, color .18s ease; }}
    #riel button svg {{ width: 21px; height: 21px; }}
    #riel button:hover {{ background: rgba(255,255,255,.10); color: #FFFFFF; }}
    #riel button:hover::before {{ content: ""; position: absolute; left: -8px; top: 10px; bottom: 10px; width: 3px;
                                  border-radius: 2px; background: {prim}; }}
    #riel button::after {{ content: attr(data-titulo); position: absolute; left: 54px; top: 50%;
                           transform: translate(-4px, -50%); background: {carbon}; color: #FFFFFF;
                           font-size: .78rem; font-weight: 500; white-space: nowrap; padding: 5px 10px;
                           border-radius: 6px; opacity: 0; pointer-events: none;
                           transition: opacity .15s ease, transform .15s ease;
                           box-shadow: 0 4px 12px rgba(0,0,0,.18); }}
    #riel button:hover::after {{ opacity: 1; transform: translate(0, -50%); }}
    #riel button:focus-visible {{ outline: 2px solid {prim_cl}; }}
    @media (max-width: 700px) {{
      body:has([data-testid="stSidebar"][aria-expanded="false"]) #riel {{ display: none; }}
      body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stMain"] {{ padding-left: 0; }}
      body:has([data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stExpandSidebarButton"] {{
          opacity: 1; pointer-events: auto; }}
    }}

    /* Botón Ver tutorial en la barra lateral */
    .abrir-tutorial {{ all: unset; box-sizing: border-box; width: 100%; display: flex; align-items: center;
                       justify-content: center; gap: 8px; padding: 9px 12px; border-radius: 8px; cursor: pointer;
                       color: {carbon}; font-size: .9rem; border: 1px dashed #D9D3CF; background: transparent;
                       transition: background-color .2s ease, border-color .2s ease, color .2s ease; }}
    .abrir-tutorial svg {{ width: 17px; height: 17px; }}
    .abrir-tutorial:hover {{ border-color: {prim_cl}; color: {prim}; background: #FFFFFF; }}

    /* Tutorial */
    #tutorial {{ position: fixed; inset: 0; z-index: 1000010; display: none; align-items: center;
                 justify-content: center; background: rgba(38,40,46,.42); backdrop-filter: blur(3px);
                 padding: 16px; }}
    #tutorial.abierto {{ display: flex; animation: tutFondo .25s ease-out both; }}
    @keyframes tutFondo {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    @keyframes tutCaja {{ from {{ opacity: 0; transform: translateY(14px) scale(.98); }}
                          to {{ opacity: 1; transform: none; }} }}
    @keyframes tutPaso {{ from {{ opacity: 0; transform: translateX(10px); }} to {{ opacity: 1; transform: none; }} }}
    #tutorial .caja {{ width: min(520px, 100%); background: #FFFFFF; border-radius: 16px; overflow: hidden;
                       box-shadow: 0 24px 60px rgba(30,32,38,.28); animation: tutCaja .35s cubic-bezier(.2,.7,.2,1) both;
                       font-family: Inter, "Helvetica Neue", Arial, sans-serif; }}
    #tutorial .franja {{ height: 5px; background: linear-gradient(90deg, {prim} 0 50%, #6AAE5A 50% 75%, #A8BF3F 75% 100%); }}
    #tutorial .contenido {{ padding: 22px 26px 18px 26px; }}
    #tutorial .cabeza {{ display: flex; align-items: center; justify-content: space-between; }}
    #tutorial .cabeza img {{ height: 30px; }}
    #tutorial .contador {{ font-size: .75rem; color: {gris_texto}; font-weight: 600; letter-spacing: .04em; }}
    #tutorial .paso {{ animation: tutPaso .3s ease-out both; min-height: 150px; }}
    #tutorial h3 {{ margin: 18px 0 8px 0; font-size: 1.2rem; font-weight: 700; color: {carbon}; padding: 0; }}
    #tutorial p {{ margin: 0; font-size: .93rem; line-height: 1.6; color: #4A4D55; }}
    #tutorial p b {{ color: {carbon}; }}
    #tutorial .puntos {{ display: flex; gap: 6px; margin: 16px 0 4px 0; }}
    #tutorial .punto {{ width: 8px; height: 8px; border-radius: 99px; background: #E4DFDC;
                        transition: width .25s ease, background-color .25s ease; }}
    #tutorial .punto.activo {{ width: 22px; background: {prim}; }}
    #tutorial .pie {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 26px;
                      border-top: 1px solid #F0ECEA; background: #FAF9F8; }}
    #tutorial button {{ all: unset; cursor: pointer; font-size: .9rem; font-weight: 600; border-radius: 8px;
                        padding: 8px 16px; transition: background-color .18s ease, color .18s ease; }}
    #tutorial .saltar {{ color: {gris_texto}; padding-left: 0; }}
    #tutorial .saltar:hover {{ color: {carbon}; }}
    #tutorial .atras {{ color: {carbon}; }}
    #tutorial .atras:hover {{ background: #EFEBE8; }}
    #tutorial .siguiente {{ background: {prim}; color: #FFFFFF; }}
    #tutorial .siguiente:hover {{ background: #9C302A; }}
    @media (prefers-reduced-motion: reduce) {{
      #riel, #tutorial, #tutorial * {{ animation: none !important; transition: none !important; }}
    }}
    </style>
    """


def script(logo: str, icono: str) -> str:
    botones = "".join(
        f'<button type="button" data-seccion="{nombre}" data-tipo="{tipo}" data-titulo="{nombre}" '
        f'aria-label="{nombre}">{_icono(clave)}</button>'
        for clave, nombre, tipo in SECCIONES
    )
    riel = (
        f'<div class="marca"><img src="{icono}" alt="Soriana"></div>'
        f'<button type="button" data-accion="abrir" data-titulo="Abrir barra lateral" '
        f'aria-label="Abrir barra lateral">{_icono("menu")}</button>'
        f'<div class="sep"></div>{botones}<div class="sep"></div>'
        f'<button type="button" data-accion="pdf" data-titulo="Descargar reporte PDF" '
        f'aria-label="Descargar reporte PDF">{_icono("pdf")}</button>'
        f'<div class="espacio"></div>'
        f'<button type="button" data-accion="tutorial" data-titulo="Ver tutorial" '
        f'aria-label="Ver tutorial">{_icono("ayuda")}</button>'
    )
    pasos = ",".join(
        "{t:" + _js(t) + ",x:" + _js(x) + "}" for t, x in PASOS_TUTORIAL
    )
    codigo = _codigo(logo, icono, riel, pasos)
    # El sanitizador de Streamlit elimina scripts cuyo texto contiene "<etiqueta"; dentro de las cadenas
    # de JavaScript se escribe "<" como \u003c, que el navegador interpreta igual.
    codigo = re.sub(r"<(?=[/A-Za-z!])", r"\\u003c", codigo)
    return "<script>" + codigo + "</script>"


def _codigo(logo: str, icono: str, riel: str, pasos: str) -> str:
    return f"""
    (function () {{
      if (window.__sorianaInterfaz) {{ return; }}
      window.__sorianaInterfaz = true;
      var CLAVE = "soriana_tutorial_visto_v1";
      var PASOS = [{pasos}];

      // ---------- Barra de íconos ----------
      var riel = document.createElement("nav");
      riel.id = "riel";
      riel.setAttribute("aria-label", "Secciones");
      riel.innerHTML = {_js(riel)};
      document.body.appendChild(riel);

      function lateral() {{ return document.querySelector('[data-testid="stSidebar"]'); }}
      function cerrada() {{ var s = lateral(); return s && s.getAttribute("aria-expanded") === "false"; }}
      function abrirLateral(despues) {{
        if (cerrada()) {{
          var b = document.querySelector('[data-testid="stExpandSidebarButton"]');
          if (b) {{ b.click(); }}
          setTimeout(despues || function () {{}}, 380);
        }} else if (despues) {{ despues(); }}
      }}
      function irA(nombre, tipo) {{
        var s = lateral(); if (!s) {{ return; }}
        var destino = null;
        if (tipo === "radio") {{
          destino = s.querySelector('[data-testid="stRadio"]');
        }} else {{
          s.querySelectorAll('[data-testid="stExpander"]').forEach(function (ex) {{
            var t = ex.querySelector("summary [data-testid='stMarkdownContainer']") || ex.querySelector("summary");
            if (!destino && t && t.textContent.trim() === nombre) {{ destino = ex; }}
          }});
          if (destino) {{
            var det = destino.querySelector("details");
            if (det && !det.open) {{ destino.querySelector("summary").click(); }}
          }}
        }}
        if (destino) {{
          setTimeout(function () {{ destino.scrollIntoView({{ behavior: "smooth", block: "start" }}); }}, 60);
        }}
      }}
      riel.addEventListener("click", function (e) {{
        var b = e.target.closest("button"); if (!b) {{ return; }}
        var accion = b.getAttribute("data-accion");
        if (accion === "tutorial") {{ abrirTutorial(); return; }}
        if (accion === "pdf") {{
          var pdf = Array.prototype.find.call(
            document.querySelectorAll('[data-testid="stSidebar"] [data-testid="stDownloadButton"] button'),
            function (x) {{ return true; }});
          if (pdf) {{ pdf.click(); }}
          return;
        }}
        if (accion === "abrir") {{ abrirLateral(); return; }}
        var nombre = b.getAttribute("data-seccion"), tipo = b.getAttribute("data-tipo");
        abrirLateral(function () {{ irA(nombre, tipo); }});
      }});

      // ---------- Tutorial ----------
      var capa = document.createElement("div");
      capa.id = "tutorial";
      capa.setAttribute("role", "dialog");
      capa.setAttribute("aria-modal", "true");
      capa.setAttribute("aria-label", "Tutorial de la aplicación");
      capa.innerHTML =
        '<div class="caja"><div class="franja"></div><div class="contenido">' +
        '<div class="cabeza"><img src="{logo}" alt="Soriana"><span class="contador"></span></div>' +
        '<div class="paso"></div><div class="puntos"></div></div>' +
        '<div class="pie"><button type="button" class="saltar">Saltar</button>' +
        '<div><button type="button" class="atras">Atrás</button> ' +
        '<button type="button" class="siguiente">Siguiente</button></div></div></div>';
      document.body.appendChild(capa);
      var actual = 0;
      function pintar() {{
        var p = PASOS[actual];
        var paso = capa.querySelector(".paso");
        paso.innerHTML = "<h3>" + p.t + "</h3><p>" + p.x + "</p>";
        paso.style.animation = "none"; void paso.offsetWidth; paso.style.animation = "";
        capa.querySelector(".contador").textContent = (actual + 1) + " DE " + PASOS.length;
        capa.querySelector(".puntos").innerHTML = PASOS.map(function (_, i) {{
          return '<span class="punto' + (i === actual ? " activo" : "") + '"></span>';
        }}).join("");
        capa.querySelector(".atras").style.visibility = actual === 0 ? "hidden" : "visible";
        capa.querySelector(".siguiente").textContent = actual === PASOS.length - 1 ? "Comenzar" : "Siguiente";
      }}
      function abrirTutorial() {{ actual = 0; pintar(); capa.classList.add("abierto");
                                  capa.querySelector(".siguiente").focus(); }}
      function cerrarTutorial() {{
        capa.classList.remove("abierto");
        try {{ window.localStorage.setItem(CLAVE, "1"); }} catch (e) {{}}
        window.__sorianaTutorialVisto = true;
      }}
      window.__sorianaTutorial = {{ abrir: abrirTutorial, cerrar: cerrarTutorial }};
      capa.querySelector(".saltar").addEventListener("click", cerrarTutorial);
      capa.querySelector(".atras").addEventListener("click", function () {{ if (actual > 0) {{ actual--; pintar(); }} }});
      capa.querySelector(".siguiente").addEventListener("click", function () {{
        if (actual < PASOS.length - 1) {{ actual++; pintar(); }} else {{ cerrarTutorial(); }}
      }});
      capa.addEventListener("click", function (e) {{ if (e.target === capa) {{ cerrarTutorial(); }} }});
      document.addEventListener("keydown", function (e) {{
        if (!capa.classList.contains("abierto")) {{ return; }}
        if (e.key === "Escape") {{ cerrarTutorial(); }}
        if (e.key === "ArrowRight") {{ capa.querySelector(".siguiente").click(); }}
        if (e.key === "ArrowLeft") {{ capa.querySelector(".atras").click(); }}
      }});
      // Botón "Ver tutorial" de la barra lateral (delegado: Streamlit puede volver a dibujarlo).
      document.addEventListener("click", function (e) {{
        if (e.target.closest && e.target.closest(".abrir-tutorial")) {{ abrirTutorial(); }}
      }});

      // Solo se muestra automáticamente la primera vez.
      var visto = false;
      try {{ visto = window.localStorage.getItem(CLAVE) === "1"; }} catch (e) {{ visto = !!window.__sorianaTutorialVisto; }}
      if (!visto) {{ setTimeout(abrirTutorial, 900); }}
    }})();
    """


def boton_tutorial() -> str:
    return f'<button type="button" class="abrir-tutorial">{_icono("ayuda")}<span>Ver tutorial</span></button>'


def _js(texto: str) -> str:
    """Cadena de JavaScript segura (comillas dobles escapadas)."""
    import json
    return json.dumps(texto, ensure_ascii=False).replace("</", "<\\/")
