# Caída del TCH Riopaila 2026: traspaso del proyecto

Explicamos con datos medidos por qué cayó el TCH de lo cosechado en Riopaila de enero a septiembre de 2026, lo probamos con datos que el modelo no vio y lo mostramos en un informe navegable para la gerencia. Estado al 24-oct-2026; la revisión con el jefe era el lunes 26-oct a primera hora.

## Reglas del proyecto

- Responder siempre en español, también los resúmenes finales.
- Términos de Riopaila: «cosecha mecanizada» (nunca «mecánica») y el rendimiento en «TCH» (nunca «t/ha»). La cosechadora daña la cepa y genera despoblación.
- **Nada del AgroFactors**: ni sus calificaciones 1-3-5 ni su nombre en lo que se presenta. Toda calificación sale de variables medidas y de nuestra estadística (pedido del jefe).
- Comparar siempre contra el PPTO además de contra la historia. PPTO = «TCH PPTO» del Maestro de Suertes 2026 (hoja MAESTRO, columna AG).
- Decir siempre lo que el modelo NO demuestra (suerte por suerte queda mucho sin explicar).
- No poner nombres de personas en tableros ni informes.
- `JUNTA DIRECTIVA` y `CASTILLA` son de solo lectura. Nunca imprimir ni copiar credenciales (la llave de Earth Engine está fuera de esta carpeta y no se comparte).
- Python con el entorno aislado `C:\Users\Agr349\tch-motor\.venv-gee` (no instalar earthengine-api en el Python global).
- Antes de implementar algo nuevo, reformular el pedido y confirmarlo: los pedidos llegan por capas.

## Cifras vigentes (versión 3, 24-oct)

- 305 cosechas con historia (2.717 ha) de 317: historia 2020-25 **116,6** → real **110,3 TCH**, caída **−6,3 TCH (−5,4 %, 17.107 t)**.
- Contra el PPTO (284 cosechas): PPTO 128,2 · historia 115,9 · real 110,5. De la brecha de 17,7 TCH, 12,3 (69 %) es PPTO por encima de la historia y 5,4 (31 %) es caída.
- Causas (TCH): cosecha mecanizada −4,8 · calor −2,0 · sequía al final −1,7 · corte anterior en suelo húmedo −0,6 · variedades −0,5 · corte anterior mecanizado −0,5 · lluvia del arranque −0,2 · renovación −0,2 · nivel freático +0,2 · labores +0,5 · riego +0,5 · número de corte +0,6 · edad de cosecha +1,8 · sin explicar +0,6 (las causas suman 6,9 TCH frente a 6,3 que cayó).
- Número de corte: cada corte resta (frente a la plantilla, misma suerte: 2º −5,0 %, 4º −9,5 %, 8º o más −17,7 %), pero en 2026 se cosecharon socas más jóvenes (27 % del área en 2º corte vs 13 % normal; 10 % en 6º-7º vs 19 %), por eso suma. Se calcula con el efecto completo (por corte + etapa de la soca) frente a la historia 2020-25 de cada suerte.
- Suelo húmedo (25-oct, suelo_humedo.py): el corte anterior hecho en un mes lluvioso resta −4,3 % por cada 100 mm (p < 0,001; igual con corte manual o mecanizado); en 2026 el 50 % del área venía de un corte en suelo húmedo (≥100 mm) contra 34 % en 2024-25. Roturar o fertilizar con el suelo húmedo (≥1 mm en los 5 días antes, regla de Cañicultura) se probó y no mostró efecto confiable (−0,3 % y +0,4 % por 10 mm; p = 0,39 y 0,11): quedó fuera de la cascada, en la hoja «Probadas sin efecto» del soporte.
- Validación: sin ver 2026 predice el **42 %** de la caída (antes se reportó 43 %, inflado: los años sin dato de agua/labores contaban como «normal = 0»; corregido en `validacion_modelo.py`). Años 2013-2026: correlación 0,91, sentido 13 de 14 (en 2018 se equivoca). Suerte por suerte R² 0,21 (sin ver 2026) a 0,29.
- Cosecha mecanizada: área 11 % (2023) → 54 % (2026). Corte anterior mecanizado: −2,3 % la primera vez, −4,5 % dos seguidos. Ejemplo: bloque 3501-550/551/560/561 (manual jul-24, mecanizada jul-25 y jul-26: 86-98 TCH); Sentinel-2 mismo día del calendario: NDVI 0,79 → 0,67, rebrote ralo 0 % → 22 %.
- Satélite, toda la cosecha 2026 (25-oct, `mecanizada_satelite.py`): soca a la misma edad después del corte manual y después del primer mecanizado, frente a un control manual→manual (descuenta el año); sin suertes renovadas en el periodo (FECHA DE SIEMBRA del maestro oficial) y solo edades con la ventana completa.
  - Grupo A (31 suertes, 307 ha, corte anterior = primer mecanizado) vs 95 de control: a los 60 días NDMI −0,055 (t −2,7, señal clara; empeoró 39 % vs 21 %), NDVI −0,035 (débil); a los 100 días nada claro; a los 150 días emparejado (rebrote ralo incluso −6 pts). El satélite ve el golpe al arranque; la pérdida en t la mide la báscula (−2,4 %).
  - Alerta 2027 (B: 59 suertes, 655 ha, primera mecanizada en 2026) vs 108 de control: a los 60 días (24 suertes) NDVI −0,079 (t −2,7, clara; bajó en 67 % vs 43 %), NDMI −0,051 (clara). Con −2,4 % ≈ 1.800 t menos en 2027. Parte puede ser hojarasca: alerta, no pronóstico. Imágenes lado a lado de 55 suertes en `tablero_web\img\sat`.
- Madurante (aún NO está en el modelo ni en el informe): trinexapac (Bonus, Tronuspac) pasó de 0,7-0,9 L/ha (2020-23) a 1,5 L/ha (2025-26); más de 12 cc/t en ~70 % de las cosechas con trinexapac en 2025-26. En TCH no hay efecto confiable; en sacarosa % caña +0,09 (≤12 cc/t) y +0,23 puntos (>12). Fusilade −4,5 % de TCH sin ganar sacarosa. Los cc/t dependen del TCH del denominador: en 2026, 200 cosechas >12 con el real (sesgado), 177 con el promedio de los 3 cortes anteriores, 122 con el PPTO (recomendado).

## Dónde está cada cosa

- Programas: esta carpeta. Intermedios (.pkl, CSV, imágenes): `datos intermedios\` (`tablero_v3\` = salidas vigentes; `*_v2_respaldo` = versión anterior).
- Salidas en `..\` (01 Estimados y TCH): `Caida_TCH_Riopaila_ene-sep_2026_soporte_v3.xlsx`, `Matriz ponderada Riopaila 2026 v3.xlsx`, `Validacion_modelo_caida_TCH_2026_v3.xlsx`, `Madurante_Riopaila_2026_analisis.xlsx`.
- Informe navegable: `tablero_web\` (index.html + app.js + data/*.json + img/). Publicado en https://caida-tch-yy76h1.vercel.app (proyecto Vercel `caida-tch-yy76h1`, equipo riegos, noindex, sin Git). Se publica desde PowerShell, sin `&&`:
  `vercel deploy "<ruta>\tablero_web" --prod --yes --name caida-tch-yy76h1 --scope riegos`
- En claude.ai (cuenta del usuario original; se comparten con **Share** dentro de la organización o se exportan):
  - Documento para el gerente (versión 3, con satélite y alerta 2027): https://claude.ai/artifact/9qFynjygAZ1dGXf3AuCrm6
  - Tablero (versión 3, pestaña «Cosecha mecanizada y satélite» desde el 25-oct): https://claude.ai/artifact/BYGc4HUpQXXffyvdpsJLTw
  - Presentación de 11 láminas (versión 3, 25-oct: sin AgroFactors, en TCH, con cosecha mecanizada, satélite y alerta 2027): https://claude.ai/artifact/CPH8sUS8DWV3Vu64xLNjZs
  - Copia de los tres (texto del documento, láminas HTML con sus imágenes, página y datos del tablero) en el paquete `Downloads\Caida TCH 2026 - traspaso.zip`, con un LEEME para cargarlo en otra cuenta.

## Cadena de programas (en este orden)

1. `factores_sep.py <repo Precipitacion-riopaila>` → `rio_factores_sep.pkl` (ZQM 2011-25 + G&P 2026, calor y lluvia de las EMA).
2. `freatico_suertes.py <freatico.json> <datos intermedios>` → nivel freático por suerte y por ciclo.
3. `riego_2026.py`, `labores_sa.py`, `roturacion.py`, `malezas_aplicaciones.py`, `no_renovadas_2026.py` (cada uno documenta sus entradas en su encabezado).
   Después `suelo_humedo.py <datos intermedios> <CONTROL DE ROTURACION.xlsm> <repo Precipitacion-riopaila>`.
4. `caida_integrada_rio.py <datos intermedios> <CONTROL DE ROTURACION.xlsm> <Maestro Suertes 2026.xlsx> <soporte_v3.xlsx>` → modelo y aportes; escribe `rio_integrado_dataset.pkl` y `caida_por_suerte.pkl`.
5. `tablero_datos.py` → `datos intermedios\tablero_v3\suertes_caida_tch.csv` y `pesos_variables.csv`.
6. `validacion_modelo.py <rio_integrado_dataset.pkl> <suertes_caida_tch.csv> <salida.xlsx> <carpeta csv>`.
7. `informe_datos.py ... <tablero_web>` → los JSON del informe. Luego publicar.

Apoyo: `mecanica_soporte.py` (análisis de la cosecha mecanizada), `mecanica_imagenes.py` (imágenes Sentinel-2 por Earth Engine), `madurante_analisis.py`.
`mecanizada_satelite.py <datos intermedios> <datos intermedios\satelite_mecanizada> <maestro-riopaila\maestro.csv> [--reusar] [--prueba N]` va antes de `informe_datos.py` (que lo lee si existe). La corrida completa por Earth Engine tarda ~30 min; `--reusar` recalcula con las series e imágenes ya bajadas.

## Fuentes de datos

- ZQM histórico: `Documents\RIOPAILA AGRICOLA\02 Cosecha y molienda\historico zqm.xlsx`; 2026: `Documents\G&P Suertes_26.xlsx` (hoja ZQM101). Ambos traen sacarosa («Sacarosa C» = % caña).
- Maestro: `Documents\Maestro Suertes 2026.xlsx` (PPTO, zona, hacienda, fecha del último corte).
- Clima: repo `github.com/mar96ospina-a/Precipitacion-riopaila` (EMA La Paila y Bugalagrande desde 2011, 38 pluviómetros desde 2020; clonar donde se necesite) + `Clima Cenicaña\Clima_Cenicana_Riopaila_Castilla_1993-2026.xlsx` para 2026.
- Riego: `Documents\HISTORICO DE RIEGO.xlsb`. Roturación: `03 Labores, riego y maquinaria\CONTROL DE ROTURACION. est 2025 con formatos.xlsm`.
- Nivel freático: Registro de NF de Ingeniería Agrícola, tomado del portal Comité APS (`js/datos.js` publicado; 202 pozos, oct-2020 a sep-2026), en `datos intermedios\freatico_luis\`. Lo formal es que el área comparta su Excel «Registro de NF actualizada.xlsx».
- Madurante: `04 Presupuesto, inversion y junta\JUNTA DIRECTIVA\Riopaila\Base_Reporte Aplicaciones Agrícola 2019 -2026- Septiembre 14.xlsx`, hoja Madurante (solo lectura; 46 filas con fecha 1970).
- Satélite: `C:\Users\Agr349\tch-motor\data\gee\mensual_riopaila.csv.gz` (NDVI/NDMI mensual por suerte, Earth Engine).

## Decisiones técnicas que no hay que perder

- Modelo: regresión de log TCH, 7.433 cosechas 2011-2026, ponderada por área, efectos fijos de suerte, año y mes; errores agrupados por suerte. Aporte de una causa = efecto × (nivel 2026 − nivel normal); los aportes + «sin explicar» suman exacto la caída de cada suerte.
- Variables que solo existen desde cierto año (agua 2022, labores 2024, freático 2021): su nivel normal se toma solo de las cosechas con dato.
- Nivel freático: IDW de los pozos a menos de 1,5 km del centroide de la suerte; variable = metros por encima de 1,5 m del nivel promedio del ciclo. No se usa la escala 5/3/1 del Registro de NF.
- Corte anterior: «primera vez» = mecanizado después de manual o plantilla; «seguido» = dos mecanizados.
- Imágenes de satélite: elegir escenas con Cloud Score+ (la máscara SCL deja pasar bruma).
- Dosis de madurante en cc/t: nunca dividir por el TCH real (sesga); usar PPTO o el TCH esperado.

## Pendiente

- Decidir si el madurante entra al informe y al documento (recomendación: página aparte, cc/t con PPTO, sin meterlo al modelo).
- Subir el proyecto a un repositorio (falta decidir si público o privado; `tch-motor` es público: no subir datos por suerte sin decidirlo).
- Conectar el Registro de NF como fuente fija y actualizar la cadena cada mes.
