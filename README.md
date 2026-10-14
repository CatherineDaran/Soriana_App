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
| `reporte_pdf.py` | Genera el reporte PDF con reportlab y gráficas de matplotlib. |
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

Las pruebas verifican, con los valores default y una tolerancia de 0.01%: beta 0.184577, WACC 7.8819%,
FCFF 2026–2030, valor terminal 130,725.8, EV 110,159.1, Equity 99,994.1, valor por acción $55.5523,
escenarios $37.3382 y $73.9676, valor ponderado $55.6026 y la matriz de sensibilidad WACC–g.


## Pestañas

1. **Dashboard**: tarjetas con precio, valor por acción, diferencia, beta, WACC, g, VT, EV, Equity y escenario;
   gráficas de inflación vs activo, IPC vs activo, escenarios, valor por acción y mapa de calor WACC–g.
2. **Inflación y mercado**: series, regresión precio vs inflación, tendencias lineal y exponencial con
   ecuaciones y R², pronóstico de oct-2026 y regresión contra el IPC.
3. **Beta y WACC**: dispersión con línea de regresión, patrón calculado / manual / usado, métodos de Rf,
   tabla de deuda y cálculo paso a paso.
4. **Proyección y valuación**: tabla del FCFF 2026–2030 y cascada de EV a Equity.
5. **Escenarios**: justificación editable, tabla comparativa e interpretación automática.
6. **Sensibilidad**: matriz WACC vs g, gráficas de una variable y tornado ±10%.
7. **Validación contra Excel**: Variable | Excel | App | Diferencia | Diferencia % | Estado.
8. **Reporte PDF**: genera y descarga el reporte con los valores en pantalla.
