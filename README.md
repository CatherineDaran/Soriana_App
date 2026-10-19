# Valuación de Organización Soriana (SORIANA B)

Aplicación interactiva en Python y Streamlit que reproduce el modelo de valuación por flujos descontados
(FCFF) de `Estudio_Financiero_Soriana.xlsx`. Es para la materia Valuación de Empresas del Tec de Monterrey.
Autora: Catherine Daran Argueta (A01611885).

Cualquier cambio en una variable recalcula toda la cadena:

**Beta → WACC → Flujos → Valor terminal → Enterprise Value → Equity Value → Valor por acción**

## Archivos

| Archivo | Contenido |
|---|---|
| `app.py` | Interfaz de Streamlit: barra lateral con variables y 8 pestañas. |
| `modelo.py` | Motor de cálculo con funciones puras (regresiones, beta, WACC, FCFF, valuación, escenarios, sensibilidad, validación). |
| `relativa.py` | Valuación relativa: estadísticos tipo Excel, comparables, transacciones, precio objetivo, LSEG y validación contra el reporte Banamex. |
| `test_relativa.py` | Pruebas de la valuación relativa contra el reporte Banamex. |
| `datos_valuacion_relativa.json` | Datos de comparables, transacciones, LSEG y contexto financiero. |
| `reporte_pdf.py` | Genera el reporte PDF con reportlab y gráficas de matplotlib. |
| `interfaz.py` | Barra de íconos (cuando la barra lateral está cerrada) y tutorial de bienvenida. |
| `assets/` | Logotipo e ícono de Soriana. |
| `test_modelo.py` | Pruebas con pytest contra los resultados del Excel (tolerancia 0.01%). |
| `datos_modelo_soriana.json` | Datos de entrada extraídos del Excel. Es la única fuente de datos de la app. |
| `Estudio_Financiero_Soriana.xlsx` | Opcional. Si está en la carpeta, la pestaña de validación lee sus celdas con `openpyxl`; si no, usa `resultados_excel_para_validar` del JSON. |

## Correr la app localmente

Requiere Python 3.10 o posterior.

```bash
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

La app se abre en `http://localhost:8501`.

## Pruebas

```bash
pytest -q
```

Las pruebas de `test_modelo.py` corren en modo exacto y verifican, con una tolerancia de 0.01%: beta 0.184577, WACC 7.8819%,
FCFF 2026–2030, valor terminal 130,725.8, EV 110,159.1, Equity 99,994.1, valor por acción $55.5523,
escenarios $37.3382 y $73.9676, valor ponderado $55.6026 y la matriz de sensibilidad WACC–g.


## Pestañas

1. **Dashboard**: tarjetas del DCF (precio, valor por acción, beta, WACC, g, VT, EV, Equity), precio objetivo,
   potencial, recomendación y valor de cada método; gráficas de inflación, IPC, escenarios y sensibilidad.
2. **DCF**, con cinco subpestañas:
   - **Inflación y mercado**: series, regresiones, tendencias lineal y exponencial y pronóstico de oct-2026.
   - **Beta y WACC**: regresión diaria, calculado / manual / usado, métodos de Rf, deuda y cálculo paso a paso.
   - **Proyección y valuación**: FCFF 2026–2030 y cascada de EV a Equity.
   - **Escenarios**: justificación editable, tabla comparativa e interpretación.
   - **Sensibilidad**: matriz WACC vs g, gráficas de una variable y tornado ±10%.
3. **Valuación relativa**: **Empresas comparables** y **Transacciones precedentes**, con casillas para incluir
   o excluir, estadísticos (PERCENTILE.INC), selector de estadístico y precio implícito por múltiplo.
4. **Precio objetivo**: ponderaciones editables, regla del equipo, recomendación, football field y contraste
   con LSEG.
5. **Contexto financiero**: márgenes, razones financieras 2021–2025 y datos clave.
6. **Validación**: contra el Excel integrador y contra el reporte Banamex (WACC redondeado a 7.88%).
7. **Reporte PDF**: genera y descarga el reporte con los valores en pantalla (21 secciones).

En la barra lateral, **WACC del DCF** elige el modo. Por defecto es el WACC redondeado a 7.88% del reporte y la
presentación Banamex ($55.58 por acción); la opción "Exacto" usa el WACC de 7.8819% del Excel integrador ($55.55).
Un WACC manual siempre tiene prioridad. La validación contra el Excel se calcula siempre en modo exacto.