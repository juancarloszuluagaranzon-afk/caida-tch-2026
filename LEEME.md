# Caída del TCH Riopaila 2026: paquete de traspaso

Paquete armado el 25 de octubre de 2026 para seguir el trabajo desde otra cuenta de Claude. Trae todo lo necesario: programas, datos intermedios, salidas en Excel y una copia del documento, la presentación y el tablero.

## Qué hay en el paquete

| Carpeta | Qué tiene |
| --- | --- |
| `Caida TCH 2026 - programas/` | Programas en Python y `datos intermedios/` (incluye la comparación por satélite); el informe en línea está en `web/`, en la raíz del repositorio. Su `CLAUDE.md` es el traspaso completo: reglas, cifras vigentes, la cadena de programas en orden y las fuentes. |
| `salidas/` | Soporte del modelo v3, matriz ponderada v3, validación v3 y análisis del madurante, en Excel. |
| `documento_gerente/` | Texto del documento para el gerente en Markdown. Las gráficas y la imagen del documento original quedan como marcas de texto. |
| `presentacion/` | Las 11 láminas (`project/deck.json` y `project/slides/*.html`) y sus imágenes en `imagenes/`. Cada lámina nombra la imagen como `/_blob/<id>` y el archivo lleva ese mismo id. |
| `tablero_claude/` | Página del tablero (`index.html`) y sus datos (`datasets/*.csv`), con la descripción de cada fuente en `fuentes.json`. |

## Cómo usarlo en la otra cuenta

**En Claude Code (recomendado).** Descomprimir en `Documents\RIOPAILA AGRICOLA\01 Estimados y TCH\` y abrir Claude Code en la carpeta `Caida TCH 2026 - programas`. El `CLAUDE.md` se carga solo y trae las reglas del proyecto. Para volver a correr los programas hace falta:

- el entorno de Python con Earth Engine (`tch-motor\.venv-gee`); la llave de Earth Engine no viene en el paquete y no se comparte;
- las fuentes originales que lista el `CLAUDE.md` (ZQM, G&P, Maestro, riego, control de roturación); los resultados intermedios ya vienen en `datos intermedios/`;
- acceso al equipo `riegos` de Vercel para volver a publicar el informe en línea.

**En claude.ai.** Subir este `LEEME.md`, el `CLAUDE.md` y el documento en Markdown para dar el contexto. Para rehacer cada pieza:

- **Documento:** pedir un documento nuevo a partir de `documento_gerente/`.
- **Presentación:** pedir una presentación de tipo Slides con los archivos de `presentacion/project/`, subiendo antes las imágenes de `presentacion/imagenes/` y cambiando cada `/_blob/<id>` por la dirección nueva que dé la subida.
- **Tablero:** pedir un tablero de tipo Dashboard que use `tablero_claude/index.html` como página y cada CSV de `tablero_claude/datasets/` como fuente, con el mismo nombre sin `.csv`.

## Los originales

Siguen en la cuenta que armó el paquete. Desde allí se pueden compartir con **Share** en claude.ai:

- Documento para el gerente: https://claude.ai/artifact/9qFynjygAZ1dGXf3AuCrm6
- Presentación de 11 láminas: https://claude.ai/artifact/CPH8sUS8DWV3Vu64xLNjZs
- Tablero: https://claude.ai/artifact/BYGc4HUpQXXffyvdpsJLTw
- Informe en línea (público, sin indexar): https://caida-tch-yy76h1.vercel.app

## Reglas que no hay que perder

- Responder siempre en español. Decir «cosecha mecanizada» (nunca «mecánica») y «TCH» (nunca «t/ha»).
- Nada del AgroFactors: toda calificación sale de variables medidas.
- Comparar siempre contra el PPTO (TCH PPTO del Maestro de Suertes 2026) además de contra la historia.
- Decir siempre lo que el modelo no demuestra: suerte por suerte queda mucho sin explicar.
- Sin nombres de personas en tableros ni informes.
- `JUNTA DIRECTIVA` y `CASTILLA` son de solo lectura.
- La conversación completa de esta sesión va aparte, en el .zip de exportación que acompaña este paquete.
