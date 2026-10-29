# TCH por tiempo térmico del ciclo · Riopaila 2020-2026

Lámina pedida para comparar con la de Cenicaña (29-oct-2026): TCH por rango de tiempo térmico del ciclo, el área cosechada
en 2026 en cada rango y lo que pierde cada rango frente al de más de 3.000 grados-día.

| Archivo | Qué es |
|---|---|
| `Lamina_tiempo_termico_Riopaila_2026.png` | La lámina (16:9, para pegar en una presentación). |
| `Tiempo_termico_Riopaila_2020-2026.xlsx` | Soporte: resumen por rango, comparación de Tukey, tiempo térmico de cada cosecha y calibración contra la hoja de 2026. |
| `../tiempo_termico.py` | El programa que lo calcula (en la carpeta de programas). |

## Resultado (3.604 cosechas de Riopaila 2020-2026)

| Grados-día | Cosechas | Edad media | TCH (IC 95 %) | Grupo (Tukey 5 %) | Frente a > 3.000 | Misma suerte, año y mes: frente a > 3.000 | Área 2026 (ene-sep) |
|---|---|---|---|---|---|---|---|
| < 2.000 | 16 | 10,5 meses | 107,4 ± 12,0 | bc | −20,0 TCH | −25,0 TCH | 0 % |
| 2.000-2.500 | 2.082 | 12,0 meses | 114,9 ± 1,1 | c | −12,6 TCH | −18,1 TCH | 53 % |
| 2.500-3.000 | 1.382 | 12,6 meses | 121,5 ± 1,4 | ab | −5,9 TCH | −12,8 TCH | 41 % |
| > 3.000 | 124 | 16,4 meses | 127,4 ± 6,1 | a | — | — | 6 % |

TCH = promedio ponderado por área; intervalo de 95 % con el tamaño efectivo de la muestra. Letras distintas = medias
distintas (Tukey al 5 %, entre cosechas). «Misma suerte, año y mes»: regresión del logaritmo del TCH con efectos fijos de suerte,
año y mes de cosecha, ponderada por área y con errores agrupados por suerte. Área 2026: 2.786 ha cosechadas de enero a septiembre.

## Cómo se calculó

- Tiempo térmico de una cosecha = Σ (temperatura media del día − 18,6 °C), del corte anterior a la cosecha. La temperatura media
  es (máxima + mínima) ÷ 2 de la EMA de la suerte (La Paila o Bugalagrande); en 2026 los días sin dato se llenan con el diario
  de Cenicaña.
- La base de 18,6 °C se calibró con la hoja «Suertes Tiempo Termico 2026 Sep» de «Riegos ciclo.xlsx» (315 cosechas de 2026): el
  cálculo coincide con esa hoja con correlación 0,995 y unos 50 grados-día de diferencia en promedio. Así las cifras son
  comparables con las de esa hoja y con los rangos de Cenicaña (con la base común de 10 °C darían unos 5.500 grados-día al año).

## Lo que hay que decir al presentarla

- **En Riopaila el tiempo térmico casi solo sigue la edad.** Da 6,6 grados-día por día de ciclo en todas las suertes (todas tienen
  casi la misma temperatura), y la edad media sube de un rango al siguiente (10,5 a 16,4 meses). La lámina muestra, en la
  práctica, el TCH por edad de corte. En el modelo de la caída eso ya está medido en la causa «Edad de cosecha» (+1,8 TCH en 2026,
  porque se cosechó caña más vieja); no es una causa nueva.
- El rango «< 2.000» tiene solo 16 cosechas: su intervalo es muy ancho y no se distingue de los dos del medio. En 2026 no hubo
  área en ese rango.
- La columna «Rango T_Termico» de la hoja de riegos está mal asignada (solo el 17 % coincide con su propio tiempo térmico): los
  rangos de la lámina se calcularon desde los grados-día.
- Es una comparación entre cosechas; no demuestra que la temperatura cause la diferencia, que sobre todo viene de la edad.

## Para volver a correrlo

```
<tch-motor>\.venv-gee\Scripts\python.exe tiempo_termico.py <datos intermedios> <repo Precipitacion-riopaila>
    <Clima_Cenicana_Riopaila_Castilla_1993-2026.xlsx> <Downloads\Riegos ciclo.xlsx> <salida.xlsx> <lámina.png>
```

Necesita matplotlib en el entorno de `tch-motor` (instalado el 29-oct).
