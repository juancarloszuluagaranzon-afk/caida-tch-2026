# Cerebro del proyecto · Caída del TCH Riopaila 2026

Índice de todo lo que sabe este repositorio, para consultarlo desde un chat de Claude o desde Claude Code. Dice qué hay, dónde
está cada cifra y qué falta. Las cifras detalladas, con su historia y sus salvedades, están en
`Caida TCH 2026 - programas/CLAUDE.md`. Este archivo es el mapa para llegar a ellas. Actualizado el 29-oct-2026.

## Cómo consultarlo

1. Leer primero este archivo y luego `Caida TCH 2026 - programas/CLAUDE.md`, que tiene las reglas, las cifras vigentes, la
   cadena de programas y las fuentes.
2. Para el detalle de una causa o de una suerte, ir a los JSON de `web/data/`. Son los mismos datos del informe en línea.
3. Para saber cómo se calculó algo, leer el encabezado del programa que lo produce (tabla «Programas», más abajo).
4. Un chat de claude.ai lee bien los `.md`, `.py`, `.json`, `.csv` y `.html`. No puede abrir los `.pkl`, y los `.xlsx` y `.png` le
   cuestan. Por eso las cifras clave están escritas en Markdown.

### Reglas al responder con este cerebro

- **Idioma y términos:** responder en español; decir «cosecha mecanizada» (nunca «mecánica») y «TCH» (nunca «t/ha»).
- **Calificaciones:** nada del AgroFactors (ni su nombre ni sus calificaciones 1-3-5); toda calificación sale de variables medidas.
- **Comparaciones:** comparar siempre contra el PPTO además de contra la historia.
- **Límites del modelo:** decir siempre lo que el modelo no demuestra; suerte por suerte queda mucho sin explicar (R² 0,21-0,29).
- **Nombres:** no poner nombres de personas.
- **Datos:** el repositorio es privado porque trae datos por suerte.

## Respuestas rápidas: dónde está cada cosa

| Si preguntan… | Respuesta corta | Dónde está el detalle |
|---|---|---|
| ¿Cuánto cayó el TCH? | **305 cosechas con historia** (2.717 ha): de 116,6 en la historia 2020-25 a 110,3 TCH reales. **Caída de −6,3 TCH** (−5,4 %, 17.107 t). | `CLAUDE.md` › Cifras vigentes; `web/data/resumen.json` |
| ¿Y frente al PPTO? | **284 cosechas:** PPTO 128,2, historia 115,9, real 110,5. **De la brecha de 17,7 TCH**, el 69 % es PPTO por encima de la historia y el 31 % es caída. | `CLAUDE.md`; `web/data/resumen.json` |
| ¿Por qué cayó? (causas) | **Restan:** cosecha mecanizada −5,3 · calor y sequía al final del ciclo −3,7 · corte anterior en suelo húmedo −0,6 · variedades −0,4 · lluvia del arranque −0,2 · renovación −0,2.<br>**Suman:** nivel freático +0,2 · labores +0,5 · riego +0,5 · número de corte +0,6 · edad de cosecha +1,8.<br>**Sin explicar:** +0,5. | `web/data/causas.json`; `salidas/Caida_TCH_..._soporte_v3.xlsx` |
| ¿Qué tan confiable es el modelo? | **Sin ver 2026** predice el 42 % de la caída. **Años 2013-2026:** correlación 0,91, acierta el sentido en 13 de 14 años. **Suerte por suerte:** R² 0,21-0,29. | `web/data/validacion.json`; `web/data/referencias.json`; `salidas/Validacion_..._v3.xlsx` |
| ¿Cuánto le quitó la cosecha mecanizada a una suerte? | **Por suerte:** cada una tiene su ficha con todas las causas. **El área mecanizada** pasó del 11 % (2023) al 54 % (2026). | `web/data/fichas.json`, `web/data/suertes.json` |
| ¿Se ve en el satélite? | **Tras el primer corte mecanizado** la soca rebrota peor (NDMI −0,055 a los 60 días); a los 150 días se empareja. **Alerta 2027:** 59 suertes (655 ha), unas 1.800 t. | `CLAUDE.md` › Satélite; `datos intermedios/satelite_mecanizada/`; `web/img/sat/` |
| ¿El satélite anticipa la caída? | **Sí:** la brecha de NDRE a los 5-7 meses frente a la normal de la suerte anticipa la caída en cada año 2022-2026. **Sin ver 2026** anticipa el 39 %. Es alerta temprana: no entra al modelo. | `web/data/satciclo.json`; `satelite_ciclo.py` |
| ¿Faltó agua o riego? | **Sequía del mes 8 a la cosecha:** −1,7 TCH. **El riego** suma +0,5. **Por etapa del cultivo (Cenicaña):** en los 2 últimos meses −4,6 % de TCH por cada 100 mm sin cubrir; en el gran crecimiento −3,6 %. | `web/data/balance.json`, `web/data/riego_etapas.json` |
| ¿Fue el calor? | **Días con Tmax > 32 °C** en los 30 días antes del corte: −2,0 TCH. **El VPD** no mejora la explicación (empate). | `calor.py`, `vpd_prueba.py` |
| ¿El suelo o el nivel freático? | **Grupo de humedad (H0-H4):** describe, no causa. **Freático:** +0,2 TCH en 2026. **Corte anterior en suelo húmedo:** −4,3 % por cada 100 mm. | `web/data/suelos.json`, `web/data/humedad.json`; `suelo_humedo.py` |
| ¿La caña llegó más pequeña? | **Mismas 217 suertes, frente al óptimo de la variedad:** peso de caña 92 % → 86 %, altura 102 % → 94 %, población 91 % → 89 %. | `web/data/desarrollo.json`; `desarrollo_optimo.py` |
| ¿El madurante tuvo que ver? | **No explica la caída** (neto ≈ +0,5 TCH). **Fusilade:** −0,2 TCH. **Dosis de trinexapac por encima de 12 cc/t:** no da más TCH ni más azúcar por ha. Aún no está en el informe. | `salidas/Madurante_Riopaila_2026_analisis.xlsx`; `CLAUDE.md` › Madurante |
| ¿Tiempo térmico? | **Sigue casi solo la edad** (6,6 grados-día por día de ciclo). **TCH por rango:** < 2.000 107,4 · 2.000-2.500 114,9 · 2.500-3.000 121,5 · > 3.000 127,4. No es una causa nueva. | `Caida TCH 2026 - programas/tiempo_termico/LEEME.md` |
| ¿Cómo lo audita Cenicaña? | **Paquete de datos preparados + método.** El **modelo parametrizado** vive en otro repositorio. | `Caida TCH 2026 - programas/paquete_cenicana/`; repositorio `modelo-caida-tch` |

## Inventario del repositorio

### Raíz

| Archivo | Qué es |
|---|---|
| `CEREBRO.md` | Este índice. |
| `README.md` | Qué es el proyecto y cómo se publica el informe. |
| `LEEME.md` | Paquete de traspaso del 25-oct y cómo cargarlo en otra cuenta. |

### `web/`: el informe en línea (https://caida-tch-yy76h1.vercel.app)

- `index.html`, `app.js`: el informe. Tiene pestañas por causa, la ficha de cada suerte, «Para la gerencia» (con un botón para
  descargar en PDF), Satélite del ciclo, Suelos y humedad, Desarrollo de la caña y Prueba del modelo.
- `data/*.json`, todo lo que muestra el informe:

| Archivo | Qué trae |
|---|---|
| `resumen.json` | Cifras generales y puente al PPTO. |
| `causas.json` | Cada causa: aporte, área afectada, soporte y suertes. |
| `suertes.json`, `fichas.json` | Cada cosecha de 2026: caída y aporte de cada causa. |
| `validacion.json` | Prueba con datos que el modelo no vio. |
| `referencias.json` | R² del PPTO y del aforo, para leer el R² del modelo. |
| `balance.json` | Falta de agua y riego en mm. |
| `riego_etapas.json` | Agua por etapa del cultivo. |
| `satciclo.json` | Curva NDRE del ciclo frente a la normal. |
| `suelos.json`, `humedad.json` | Grupo de humedad del suelo y su comportamiento en 2026. |
| `desarrollo.json` | Aforo frente al óptimo de la variedad. |
| `escenas_bloque3501.json` | Ejemplo satelital del bloque 3501. |

- `img/`: imágenes Sentinel-2 lado a lado (`img/sat/`) y gráficas del informe.

### `Caida TCH 2026 - programas/`: programas y datos intermedios

- `CLAUDE.md`: el traspaso completo. Es lo más importante después de este archivo.
- `tiempo_termico/`: lámina, Excel y LEEME del tiempo térmico.
- `paquete_cenicana/`: método (`METODO.md`) y programas que reproducen el modelo solo con la tabla por cosecha.
- `datos intermedios/`: resultados en `.pkl`/`.csv` (`rio_integrado_dataset.pkl` es la base del modelo; `tablero_v3/` tiene las
  salidas vigentes; `satelite_mecanizada/` tiene las series y las imágenes; `etp_cenicana/` la ETP diaria de La Paila y Bugalagrande;
  y una carpeta con el nivel freático de los pozos). Los `*_v2_respaldo` son la versión anterior.
- `resultados_*.txt`: salidas en texto de corridas anteriores (factores a septiembre, riego, frecuencia de riego, no renovadas).
- `recuperados_29sep/`: los primeros modelos (29-sep), solo como historia.

### Programas

**La cadena del modelo, en orden** (detalle de entradas en `CLAUDE.md` › Cadena de programas):

| Programa | Qué hace |
|---|---|
| `factores_sep.py` | Arma las cosechas 2011-2026 con calor y lluvia de las EMA. |
| `freatico_suertes.py` | Calcula el nivel freático por suerte y por ciclo. |
| `riego_2026.py`, `labores_sa.py`, `roturacion.py`, `malezas_aplicaciones.py`, `no_renovadas_2026.py` | Calculan el riego, las labores, la roturación, el control de malezas y el área que no se renovó. |
| `suelo_humedo.py` | Mide si el corte anterior, la roturación o la fertilización se hicieron con el suelo húmedo. |
| `caida_integrada_rio.py` | **El modelo:** una sola regresión con todas las causas y el aporte de cada una. |
| `tablero_datos.py` | Calcula cuánto le quitó o le dio cada variable a cada cosecha. |
| `validacion_modelo.py` | Prueba el modelo sin ver 2026, por años y suerte por suerte. |
| `informe_datos.py` | Escribe los JSON del informe. |
| `desarrollo_optimo.py` | Compara el aforo con el óptimo de la variedad. |
| `balance_riego.py` | Calcula el balance hídrico y el riego en mm. |
| `referencias_r2.py` | Calcula el R² del PPTO y del aforo. |
| `suelos_humedad.py` | Analiza los grupos de humedad del suelo. |
| `humedad_comportamiento.py` | Revisa si cada suerte se comportó como su grupo de humedad. |
| `satelite_ciclo.py` | Compara la curva satelital del ciclo con la falta de agua. |
| `paquete_cenicana.py` | Arma el paquete para Cenicaña. |
| `riego_por_edad.py` | Mide el agua por etapa del cultivo. |

**Apoyo y pruebas aparte:**

| Programa | Qué hace |
|---|---|
| `mecanica_soporte.py`, `mecanica_imagenes.py`, `mecanizada_satelite.py` | Soporte de la cosecha mecanizada, imágenes Sentinel-2 y el rebrote después del primer corte mecanizado. |
| `madurante_analisis.py` | Madurante aplicado y su efecto. |
| `etp_cenicana.py` | ETP de Cenicaña por cosecha. |
| `calor.py`, `tamano.py` | Días > 32 °C por planta y mes; tamaño de la caída a octubre. |
| `vpd_prueba.py`, `tiempo_termico.py` | VPD y humedad relativa; tiempo térmico. No cambian el modelo. |
| `matriz_ponderada.py` | Matriz ponderada por suerte con efectos medidos. |
| `riego_frecuencia.py`, `frecuencia_excel.py`, `riego_2027.py` | Frecuencia del riego y agua de la caña de 2027. |
| `labores_perdidas.py`, `siembra_lucro.py`, `impacto_excel.py` | Toneladas perdidas por labores tardías, oportunidad de siembra e impacto presupuestal 2026-2027. |
| `benchmark_variedad_zona.py`, `variedad_potencial.py` | TCH por variedad y zona agroecológica. |
| `calidad_suelo_lluvia.py`, `calificacion_rot_fert.py` | Columnas de oportunidad y calidad de la base de maduración. |

### `salidas/`, `documento_gerente/`, `presentacion/`, `tablero_claude/`

| Carpeta | Qué tiene |
|---|---|
| `salidas/` | Todos los Excel y PDF de resultados (lista más abajo). |
| `documento_gerente/` | Texto del documento para el gerente (versión 3), en Markdown. |
| `presentacion/` | Las 11 láminas (HTML) y sus imágenes. |
| `tablero_claude/` | Página y CSV del tablero de claude.ai. |

Estas carpetas no se bajan en el checkout parcial de la máquina original, pero están en GitHub.

### Los Excel y PDF de `salidas/`

Un chat los lee con dificultad; las cifras clave también están en `CLAUDE.md` y en los JSON de `web/data/`.

| Archivo | Qué trae | Programa |
|---|---|---|
| `Caida_TCH_Riopaila_ene-sep_2026_soporte_v3.xlsx` | Soporte del modelo: causas, efectos y aportes, y las variables probadas sin efecto. | `caida_integrada_rio.py` |
| `Matriz ponderada Riopaila 2026 v3.xlsx` | Cuánto le quita o le da cada variable a cada suerte. | `matriz_ponderada.py` |
| `Validacion_modelo_caida_TCH_2026_v3.xlsx` | Prueba con datos que el modelo no vio. | `validacion_modelo.py` |
| `Madurante_Riopaila_2026_analisis.xlsx` | Madurante y su efecto (aún no está en el informe). | `madurante_analisis.py` |
| `Desarrollo_vs_optimo_variedad_2026.xlsx` | Aforo frente al óptimo de la variedad. | `desarrollo_optimo.py` |
| `Suelos_grupo_humedad_Riopaila.xlsx` | TCH y caída por grupo de humedad del suelo. | `suelos_humedad.py` |
| `Humedad_comportamiento_suelos_2026.xlsx` | Si cada suerte se comportó como su grupo de humedad. | `humedad_comportamiento.py` |
| `Satelite_ciclo_vs_falta_agua_2026.xlsx` | Curva satelital del ciclo, comparación de índices y falta de agua por edad. | `satelite_ciclo.py` |
| `Riego_por_edad_vs_ventana_Cenicana_2026.xlsx` | Agua y riego por etapa del cultivo. | `riego_por_edad.py` |
| `ETP_Cenicana_La_Paila_Bugalagrande.xlsx` | ETP y lluvia por cosecha. | `etp_cenicana.py` |
| `VPD_humedad_relativa_vs_TCH_2026.xlsx` | Prueba del VPD y la humedad relativa frente a los días > 32 °C. | `vpd_prueba.py` |
| `Benchmark_variedad_zona_agroecologica_2026.xlsx` | TCH por variedad y zona agroecológica. | `benchmark_variedad_zona.py` |
| `Variedad_potencial_por_zona_y_sector_Riopaila.xlsx` | Variedad con mejor potencial por zona y sector. | `variedad_potencial.py` |
| `Impacto_TCH_Riopaila_2026_2027_soporte_v3.xlsx` | Impacto de la restricción presupuestal en el TCH 2026-2027 (renovación, labores, riego, lucro cesante). Su hoja de fertilización trae la calificación 1-5 de la base de maduración: no es del modelo y no se presenta. | `impacto_excel.py` |
| `Rendimiento_vs_mecanizada_TCH_2011-2026.xlsx` | TCH y cosecha mecanizada por año, Riopaila y Castilla, con la fase del ENSO. | — |
| `Balance_hidrico_y_riego_vs_TCH_Riopaila_2026.pdf` | Nota: balance hídrico y riego en mm frente al TCH. | `balance_riego.py` |
| `Riegos_teoricos_vs_TCH_Riopaila_2026.pdf` | Nota: riegos teóricos frente a los aplicados y el TCH. | — |

El tiempo térmico tiene su propia carpeta: `Caida TCH 2026 - programas/tiempo_termico/`.

## Lo que NO está en este repositorio

**Fuentes originales:** ZQM, G&P, Maestro de Suertes, riego, control de roturación, aforos, aplicaciones del madurante, clima de
Cenicaña y el repositorio de precipitación. `CLAUDE.md` › Fuentes de datos dice dónde está cada una.

**Otros lugares:**

- **Modelo parametrizado para Cenicaña:** está en el repositorio privado `juancarloszuluagaranzon-afk/modelo-caida-tch`, con su
  app en https://modelo-caida-tch.vercel.app. Ese repositorio no trae datos reales. Las plantillas con datos de Riopaila y
  Castilla quedan solo en la máquina original.
- **Paquete completo para Cenicaña** (tabla por cosecha con datos): en `Paquete Analitica Cenicana 2026-10`, fuera de git. Aún no
  se ha enviado.
- **Documento, tablero y presentación originales:** están en claude.ai (enlaces en `LEEME.md`).

## Lo que el modelo NO demuestra

- **Suerte por suerte** explica poco: R² 0,21 sin ver 2026, 0,29 sin ver esas suertes. El PPTO y el aforo de campo no lo hacen
  mejor.
- **Sin ver 2026** predice el 42 % de la caída, no toda.
- **En 2018** el modelo se equivoca de sentido.
- **Varias cifras son descriptivas, no causas del modelo:** el satélite del ciclo, el suelo por grupo de humedad, el desarrollo
  frente al óptimo, el agua por etapa y el tiempo térmico.
- **La alerta 2027 es una alerta, no un pronóstico:** parte de la señal satelital puede ser hojarasca.
- **Castilla** (en el modelo parametrizado) aún no es presentable sin salvedades: el calor sale como causa mayor, la cosecha
  mecanizada sale positiva y solo hay 5 años de prueba.
