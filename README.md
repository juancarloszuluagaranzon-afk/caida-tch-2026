# Caída del TCH Riopaila 2026

Por qué cayó el TCH de lo cosechado en Riopaila de enero a septiembre de 2026, medido con un modelo de 7.433 cosechas (2011-2026), validado con datos que el modelo no vio y presentado en un informe navegable para la gerencia.

**Repositorio privado:** trae datos por suerte. No hacerlo público.

## Contenido

| Carpeta | Qué tiene |
| --- | --- |
| `Caida TCH 2026 - programas/` | Programas en Python y `datos intermedios/`. Su `CLAUDE.md` es el traspaso completo: reglas, cifras vigentes, la cadena de programas en orden y las fuentes. |
| `web/` | El informe en línea (antes `Caida TCH 2026 - programas/tablero_web/`) y la función del chat (`api/chat.js`). |
| `salidas/` | Soporte del modelo v3, matriz ponderada v3, validación v3 y análisis del madurante, en Excel. |
| `documento_gerente/` | Texto del documento para el gerente, en Markdown. |
| `presentacion/` | Las 11 láminas de la presentación (formato Slides de claude.ai) y sus imágenes. |
| `tablero_claude/` | Página y datos del tablero de claude.ai. |
| `LEEME.md` | Cómo se armó el paquete de traspaso y cómo cargarlo en otra cuenta. |

## Informe en línea

`web/` es un sitio estático (index.html, app.js, data/*.json, img/) con una función de Vercel para el chat (`api/chat.js`, Gemini; la llave va en la variable de entorno `GEMINI_API_KEY` del proyecto, nunca en el repositorio). En Vercel, el proyecto `caida-tch-yy76h1` publica esa carpeta: **Settings → Build and Deployment → Root Directory** = `web`, sin comando de compilación. Está en la raíz porque Vercel no acepta funciones en rutas con espacios.

## Correr la cadena

Ver `Caida TCH 2026 - programas/CLAUDE.md`. Los pasos que parten de `datos intermedios/` (validación, `tablero_datos.py`, `informe_datos.py`) corren con pandas, statsmodels y openpyxl más el paquete `tchmotor` del repositorio `tch-motor`; los que leen los Excel originales (ZQM, G&P, Maestro, riego, roturación) o Earth Engine necesitan esas fuentes y su propia llave.
