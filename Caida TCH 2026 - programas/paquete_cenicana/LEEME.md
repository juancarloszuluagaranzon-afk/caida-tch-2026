# Caída del TCH Riopaila 2026: datos preparados y método

Paquete de Riopaila para Analítica de Cenicaña. Con él se puede repetir el modelo que explica la caída del TCH de lo cosechado en Riopaila de enero a septiembre de 2026, revisar la validación y probar otras especificaciones.

## Contenido

- `METODO.docx` / `METODO.md`: cómo se prepararon los datos, el modelo, cómo se calcula el aporte de cada causa, cómo se validó, lo que se probó sin efecto y lo que el modelo no demuestra.
- `datos/cosechas_riopaila_2011-2026.csv`: una fila por cosecha (suerte × ciclo) de Riopaila, 2011 a septiembre de 2026, con todas las variables del modelo ya calculadas. UTF-8, separador coma y punto decimal. Las celdas vacías son «sin dato».
- `datos/cosechas_riopaila_2011-2026.xlsx`: la misma tabla, con las hojas «Diccionario» y «Resumen por año».
- `datos/diccionario_variables.csv`: qué es cada columna, su unidad, los años con dato y de dónde sale.
- `programas/modelo_caida_tch.py`: ajusta el modelo y calcula el aporte de cada causa en ene-sep 2026.
- `programas/validacion_modelo.py`: prueba el modelo con datos que no vio (años completos, 2026 sin 2026 y suertes de 2026).

## Cómo correrlo

Python 3.11 o más reciente, con pandas, numpy, statsmodels y openpyxl.

```
python programas/modelo_caida_tch.py datos/cosechas_riopaila_2011-2026.csv aportes_2026.xlsx
python programas/validacion_modelo.py datos/cosechas_riopaila_2011-2026.csv validacion.xlsx
```

Cada programa tarda menos de un minuto (la validación ajusta el modelo unas 20 veces). Las cifras que deben salir están en el método, sección 8.

## Lo que no trae

- Las bases originales (báscula, riegos, labores, nivel freático, pluviómetros). Van solo las variables ya calculadas por cosecha. La forma de calcular cada una está en el diccionario y en el método.
- El presupuesto (TCH PPTO) por suerte, ni la zona o la hacienda.
- Nombres de personas.

Uso confidencial, solo para el trabajo de apoyo de Analítica de Cenicaña con Riopaila.
