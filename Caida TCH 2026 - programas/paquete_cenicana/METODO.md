---
title: "Caída del TCH Riopaila 2026: preparación de datos, modelo y validación"
subtitle: "Documento de método para Analítica de Cenicaña"
date: "Octubre de 2026"
---

# 1. Pregunta y alcance

**Pregunta.** ¿Por qué el TCH de lo que Riopaila cosechó de enero a septiembre de 2026 quedó por debajo de su historia, y cuánto aporta cada causa medida?

**Alcance.** Son 317 cosechas de Riopaila. De ellas, 305 (2.717 ha) tienen historia 2020-25 de la misma suerte. En esas 305, el TCH pasó de 116,6 en la historia a 110,3 en 2026: una caída de 6,3 TCH (−5,4 %), o 17.107 t.

**Enfoque.** Cada suerte se compara consigo misma. El modelo usa efectos fijos de suerte, así que las diferencias permanentes de suelo, ubicación y manejo no se confunden con las causas. Toda calificación sale de variables medidas (báscula, clima, registros de labores y riego, pozos de nivel freático); no se usan calificaciones expertas.

# 2. Unidad de análisis y fuentes

**Unidad.** Una fila es una cosecha: una suerte en un ciclo.

- El registro de báscula (ZQM) trae filas por mes. Una cosecha que se hace en meses consecutivos (con huecos de 2 meses o menos) se junta en un solo ciclo, y de ese ciclo se toma la fila de mayor acumulado.
- Se dejan las cosechas con TCH entre 20 y 300 y con edad entre 8 y 24 meses.
- Así quedan 7.867 cosechas de 673 suertes, de 2011 a septiembre de 2026. De ellas, 7.433 entran al modelo. Las demás se quedan por dos razones:
  - a 427 les falta la lluvia del arranque y a 14 los días de calor (en total 7.440 tienen las dos);
  - 7 tienen el número de corte en 0.

| Fuente | Qué aporta | Años |
|---|---|---|
| ZQM de Riopaila (báscula); 2026 de la planilla de seguimiento | Toneladas, área, edad, corte, variedad, tipo y causa de cosecha | 2011-2026 |
| EMA La Paila y Bugalagrande (2026 completado con el Meteoportal de Cenicaña) | Lluvia, temperatura máxima, evaporación | 2011-2026 |
| Consolidado de riegos de Riopaila | Lámina de riego aplicada por suerte | 2021-2026 |
| Control de roturación y SimpleAgri | Fechas de roturación, primer herbicida y fertilización | cosechas 2024-2026 |
| Plan de renovación 2025 | Suertes que estaban para renovar y siguieron como soca | 2026 |
| Registro de nivel freático de Ingeniería Agrícola (202 pozos) | Nivel freático por suerte y ciclo | 2021-2026 |
| Pluviómetros de Riopaila | Lluvia en los días de la roturación y la fertilización | 2024-2026 |

La tabla `cosechas_riopaila_2011-2026.csv` trae solo las variables ya calculadas por cosecha. El diccionario dice, para cada columna, cómo se calculó, en qué unidad está y desde qué año hay dato.

# 3. Preparación de las variables

## Clima

- **Lluvia del arranque** (`llu03`): lluvia de los primeros 91 días del ciclo en la EMA asignada a la suerte.
  - El inicio del ciclo se estima como la fecha de cosecha (día 15 del mes) menos la edad × 30,44 días.
  - Se exigen al menos 70 días con dato, y la suma se escala a 91 días.
- **Calor** (`d32`): días con temperatura máxima mayor de 32 °C en los 30 días antes de la cosecha. Se exigen al menos 20 días con dato.

## Agua al final del ciclo

Se mide del mes 8 a la cosecha, solo en cosechas desde 2022, con ciclos que empezaron desde 2021.

- **Falta de agua sin riego**: evaporación − lluvia de la EMA (`defsr_fin`).
- **Lámina de riego aplicada** (`mm_fin`).
- **Falta de agua después del riego**: `def_fin = defsr_fin − mm_fin`.

El modelo usa un solo coeficiente para `def_fin`. Al calcular los aportes, ese efecto se parte en dos: sequía (`defsr`) y riego aplicado (`mm`).

## Labores del ciclo

Se miden en socas cosechadas en 2024-26.

- **Roturación tardía**: más de 30 días del corte a la roturación. La fecha sale del control oficial; si no está, de SimpleAgri menos 10 días.
- **Herbicida tarde**: cada 30 días después del día 90.
- **Fertilización tardía**: después de 120 días.

«Sin registro» no se trata como una labor mal hecha. Va como variable de control del dato (`_na`), porque el registro en SimpleAgri fue mejorando año a año: la roturación sin registro pasó de 52 % en 2024 a 10 % en 2026.

## Corte anterior

Se mira la cosecha anterior de la misma suerte, siempre que sea el corte consecutivo:

- **Primera vez**: mecanizada después de un corte manual o de plantilla (`pm_new`).
- **Seguida**: dos cortes mecanizados seguidos (`pm_seg`).
- **Suelo húmedo**: lluvia de la EMA en el mes del corte anterior (`ca_mm100`, topada en 400 mm).

## Nivel freático

- **Nivel de la suerte**: se interpola por distancia inversa (potencia 2) con hasta 4 pozos a menos de 1,5 km del centroide de la suerte.
- **Variable del modelo**: metros por encima de 1,5 m del nivel promedio del ciclo (`nf_exc15`).

## Variedad, edad y corte

- **Variedad**: las variedades con menos de 60 cosechas en la base se agrupan como «otra».
- **Edad**: en bandas de un mes, con referencia de 12 a 13 meses.
- **Número de corte**: entra de dos formas, como número (lineal) y en bandas.
- **Cosecha mecanizada**: lleva un coeficiente propio para cada año (`mec_2011` … `mec_2026`), porque su brecha frente a la cosecha manual cambia con los años.

**Variables con dato desde cierto año.** El agua, las labores y el freático solo existen desde cierto año. Donde no hay dato se llenan con 0 y se marcan con una variable indicadora (`def_na`, `lab_na`, `nf_na`…), así el coeficiente se estima solo con las cosechas que tienen el dato.

# 4. El modelo

Es una regresión lineal por mínimos cuadrados ponderados del logaritmo del TCH:

> log TCH = efecto de la suerte + efecto del año + efecto del mes de cosecha + edad (bandas) + número de corte (lineal + bandas) + variedad + incendio + cosecha mecanizada × año + lluvia 0-3 meses + días > 32 °C + falta de agua al final del ciclo + labores + renovación no hecha + corte anterior mecanizado + nivel freático + lluvia del corte anterior + indicadores de dato faltante

- **Peso**: el área de cada cosecha.
- **Errores**: agrupados por suerte.
- **Ajuste**: n = 7.433 y R² = 0,64 (ese R² incluye los efectos fijos).

Efectos principales (cambio en el TCH, misma suerte):

| Variable | Efecto | p |
|---|---|---|
| Cosecha mecanizada en 2026 (frente a manual) | −8,1 % | < 0,001 |
| Cosecha mecanizada en 2025 | −3,7 % | 0,004 |
| Días > 32 °C, por día | −0,24 % | < 0,001 |
| Falta de agua del mes 8 a la cosecha, por 100 mm | −0,93 % | < 0,001 |
| Lluvia de los meses 0-3, por 100 mm | −0,77 % | < 0,001 |
| Corte anterior mecanizado, primera vez | −2,4 % | < 0,001 |
| Dos cortes mecanizados seguidos | −4,3 % | < 0,001 |
| Lluvia en el mes del corte anterior, por 100 mm | −4,3 % | < 0,001 |
| Nivel freático, por metro por encima de 1,5 m | −8,0 % | < 0,001 |
| Incendio | −3,9 % | 0,004 |
| Roturación tardía | −1,8 % | 0,30 |
| Herbicida tarde, por 30 días | −0,4 % | 0,61 |
| Fertilización después de 120 días | −0,8 % | 0,51 |
| Renovación no hecha | −2,3 % | 0,63 |

**Número de corte.** Frente a la plantilla y en la misma suerte, el 2º corte resta 5,0 %, el 4º resta 9,5 % y el 8º o más resta 17,7 %.

**Labores y renovación.** Las tres labores y la renovación no hecha no son significativas. Se dejan en el modelo para medir su aporte, pero sus cifras son débiles.

# 5. Aporte de cada causa a la caída de 2026

**Fórmula.** Aporte de una causa = coeficiente × (nivel en ene-sep 2026 − nivel normal). El normal se calcula en los mismos meses (enero a septiembre), ponderado por área:

| Causas | Período normal | Qué cosechas cuentan |
|---|---|---|
| Clima, cosecha mecanizada, edad e incendio | 2020-25 | todas |
| Agua al final del ciclo y nivel freático | 2022-25 | solo las que tienen el dato |
| Labores | 2024-25 | solo lo registrado |
| Renovación no hecha | — | normal = 0 |

**Variedad y número de corte.** Cada cosecha de 2026 se compara con la historia 2020-25 de su propia suerte, no con el promedio de Riopaila. Si se comparara con el promedio, a una suerte se le cargaría el efecto de una variedad que ya tenía o de un número de corte normal para ella.

**Cómo cuadra.** Lo que los factores no explican queda como «Sin explicar». Para cada cosecha, los aportes más lo sin explicar suman exactamente su caída.

**De log a TCH.** El aporte en TCH = aporte en log × TCH real × (e^L − 1)/L, donde L es la caída de la cosecha en log. Con este factor los aportes en TCH suman exactamente la diferencia entre el histórico y el real.

Resultado (305 cosechas con historia, 2.717 ha; negativo = resta TCH):

| Causa | TCH |
|---|---|
| Cosecha mecanizada | −4,8 |
| Calor (días > 32 °C) | −2,0 |
| Sequía al final del ciclo | −1,7 |
| Corte anterior en suelo húmedo | −0,6 |
| Corte anterior mecanizado | −0,5 |
| Variedades | −0,4 |
| Lluvia del arranque | −0,2 |
| Renovación no hecha | −0,2 |
| Nivel freático | +0,2 |
| Labores (roturación, herbicida, fertilización) | +0,5 |
| Riego aplicado | +0,5 |
| Número de corte | +0,6 |
| Edad de cosecha | +1,8 |
| Sin explicar | +0,5 |
| **Caída total** | **−6,3** |

**Calor y sequía.** Se presentan juntos como una sola causa de −3,7 TCH. El modelo los mide por separado, así que la suma es exacta. Además se probó la interacción calor × falta de agua y no resta más (p = 0,35).

**Número de corte.** Aporta a favor aunque cada corte resta TCH. La razón es que en 2026 se cosecharon socas más jóvenes que lo normal: el 27 % del área estaba en 2º corte, contra 13 % en la historia.

# 6. Validación con datos que el modelo no vio

**V1. Años que no vio.** Cada año de 2013 a 2026 se predice con un modelo ajustado sin ese año. La anomalía de cada suerte se mide frente a sus 6 años anteriores.

- La correlación entre la anomalía real y la predicha, año por año, es 0,91.
- El sentido (sube o baja) es correcto en 13 de los 14 años. Se equivoca en 2018.
- La parte común de cada año que los factores no explican sigue siendo grande. En 2023, por ejemplo, la anomalía real fue −26 % y la predicha −6 %.

**V2. 2026 sin ver 2026.** El modelo completo se ajusta solo con 2011-2025 y se aplica a ene-sep 2026, con referencia 2020-25. Predice una anomalía de −2,9 % frente a −6,9 % real: explica el **42 %** de la caída.

**V5. Suertes de 2026 que el modelo no vio.** Es una validación cruzada en 5 partes dentro de 2026; el modelo conoce el año por las demás suertes.

- Suerte por suerte, el R² es 0,29.
- Sin ver nada de 2026 (con el modelo de V2) es 0,21.

**Para leer esos R².** En la misma medida, el presupuesto (PPTO) da un R² de −0,58 y el aforo de campo hecho antes del corte da −0,62.

**Una corrección.** Antes se había reportado que el modelo explicaba el 43 %. Esa cifra estaba inflada: los años sin dato de agua o de labores contaban como «normal = 0». Ahora el nivel normal de esas variables se calcula solo con las cosechas que tienen el dato.

# 7. Lo que se probó y no entró

| Prueba | Resultado |
|---|---|
| Roturación con el suelo húmedo (≥ 1 mm en los 5 días antes) | −0,3 % por 10 mm, p = 0,39 |
| Fertilización con el suelo húmedo | +0,4 % por 10 mm, p = 0,11 |
| Interacción calor × falta de agua | p = 0,35 |
| Falta de agua de los meses 2-10 en vez del mes 8 a la cosecha | Explica menos (−0,45 % por 100 mm; junto a la actual pierde fuerza, p = 0,21). En 2026 esos meses no fueron más secos |
| Número de riegos (en vez de la lámina) | Sin efecto (p = 0,97) |

Los siguientes análisis complementarios se hicieron aparte y **no** entran en el modelo:

- **Satélite**: el NDRE a los 5-7 meses, frente a la normal de la suerte, anticipa la caída; se usa como alerta temprana.
- **Aforos frente al óptimo de cada variedad.**
- **Grupos de humedad del suelo.**
- **Madurante.**

Se pueden compartir por separado si sirven.

# 8. Lo que el modelo no demuestra

- **No explica cada suerte.** Explica bien el promedio y la dirección de los años, pero suerte por suerte queda mucho sin explicar: R² de 0,21 a 0,29 fuera de muestra.
- **Sin ver 2026 explica el 42 % de la caída.** El resto es una parte común del año que las variables medidas no recogen.
- **Es un análisis de asociación con datos de operación, no un experimento.**
  - El riego se programa donde falta agua, así que su efecto puede salir menor que el real.
  - La cosecha mecanizada se asigna a ciertas suertes y meses. Los efectos fijos de suerte, año y mes controlan una parte de eso, no todo.
- **Las labores tienen poco historial.** Solo hay dos años de referencia (2024-25) y sus coeficientes no son significativos.
- **El agua y el freático están en la escala de la EMA.** La falta de agua se mide con la EMA asignada (dos estaciones), no con el balance de cada suerte. El freático depende de que haya pozos a menos de 1,5 km.
- **Así debe dar al correr los programas del paquete:**
  - `modelo_caida_tch.py`: 7.433 cosechas en el modelo y −6,3 TCH en 305 cosechas, con los aportes de la sección 5.
  - `validacion_modelo.py`: 42 %, 0,91 y R² 0,21 / 0,29.

# 9. Dónde nos sirve el apoyo de Analítica

- Revisar la especificación: efectos fijos, bandas de edad y corte, y la brecha anual de la cosecha mecanizada.
- Dar una lectura independiente de la parte común del año que queda sin explicar en 2026 (≈ 58 % fuera de muestra).
- Proponer mejores medidas del agua por suerte: balance con el suelo y estaciones más cercanas.
- Revisar si la cosecha mecanizada se asigna de forma selectiva a ciertas suertes y meses, y cómo corregirlo.
