# -*- coding: utf-8 -*-
r"""Paquete para Analítica de Cenicaña (nivel 2: datos preparados + método).

Toma la base del modelo (rio_integrado_dataset.pkl, de caida_integrada_rio.py), deja solo las columnas que el modelo usa o
que describen la cosecha (sin columnas internas de cálculo ni rutas) y la escribe en CSV (UTF-8, coma, punto decimal) y en
Excel con su diccionario. Copia los programas de paquete_cenicana\ (el modelo y la validación, que corren solo con el CSV)
y el método (METODO.md; si hay pandoc, también METODO.docx).

Uso: <tch-motor>\.venv-gee\Scripts\python.exe paquete_cenicana.py <datos intermedios> <carpeta de salida>
Va después de caida_integrada_rio.py.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
PK, SAL = Path(sys.argv[1]), Path(sys.argv[2])
AQUI = Path(__file__).parent / "paquete_cenicana"

# variable, descripción, unidad, años con dato, fuente
D = [
    # ---- identificación y resultado
    ("ste", "Suerte (código hacienda-suerte)", "", "2011-2026", "ZQM (báscula)"),
    ("anio", "Año de la cosecha", "", "2011-2026", "ZQM"),
    ("Mes", "Mes de la cosecha", "1-12", "2011-2026", "ZQM"),
    ("cosecha", "Fecha de la cosecha (el ZQM da el mes; se toma el día 15)", "fecha", "2011-2026", "ZQM"),
    ("ini", "Inicio del ciclo estimado = cosecha − edad × 30,44 días", "fecha", "2011-2026", "ZQM"),
    ("Corte", "Número de corte (1 = plantilla, 2 = segundo corte…; 0 aparece en 7 cosechas, que quedan fuera del modelo)", "", "2011-2026", "ZQM"),
    ("Variedad Principal", "Variedad registrada", "", "2011-2026", "ZQM"),
    ("var", "Variedad agrupada: las de menos de 60 cosechas en la base van como «otra»", "", "2011-2026", "calculada"),
    ("Area", "Área neta cosechada (peso de la regresión)", "ha", "2011-2026", "ZQM"),
    ("Edad", "Edad a la cosecha", "meses", "2011-2026", "ZQM"),
    ("TC-Total", "Toneladas de caña cosechadas (el ciclo = fila de mayor acumulado de meses consecutivos)", "t", "2011-2026", "ZQM"),
    ("tch_calc", "TCH = TC-Total ÷ Area (se dejan 20-300 TCH y edad 8-24 meses)", "TCH", "2011-2026", "calculada"),
    ("y", "Logaritmo natural del TCH (variable que explica el modelo)", "log", "2011-2026", "calculada"),
    ("rel", "y menos el promedio de y de la misma suerte en 2020-25 (sin la propia cosecha si es de 2020-25); vacío si la "
            "suerte no tiene historia", "log", "2011-2026", "calculada"),
    ("Tipo Cosecha", "Manual o Mecanico (cosecha mecanizada)", "", "2011-2026", "ZQM"),
    ("Causa Cosecha", "Programa o Incendio", "", "2011-2026", "ZQM"),
    ("est", "Estación meteorológica asignada a la suerte (La Paila o Bugalagrande)", "", "2011-2026",
     "tabla estaciones_suertes del repo de clima; sin asignar = La Paila"),
    # ---- clima
    ("llu03", "Lluvia de los primeros 3 meses del ciclo (91 días desde ini; se escala si falta algún día, mínimo 70 días con dato)",
     "mm", "2011-2026", "EMA La Paila / Bugalagrande (2026: Meteoportal de Cenicaña)"),
    ("llu03_100", "llu03 ÷ 100", "100 mm", "2011-2026", "calculada"),
    ("d32", "Días con temperatura máxima > 32 °C en los 30 días antes de la cosecha (mínimo 20 días con dato)", "días",
     "2011-2026", "EMA"),
    # ---- cosecha
    ("mec", "1 = cosecha mecanizada", "0/1", "2011-2026", "ZQM"),
    ("inc", "1 = cosecha por incendio", "0/1", "2011-2026", "ZQM"),
    *[(f"mec_{y}", f"mec × (anio = {y}): brecha de la cosecha mecanizada propia de cada año", "0/1", "2011-2026", "calculada")
      for y in range(2011, 2027)],
    ("edad_b", "Edad en bandas (<9, 9-10 … >15); referencia 12-13", "", "2011-2026", "calculada"),
    ("soca_b", "Número de corte en bandas (0,1] (1,2] (2,3] (3,4] (4,5] (5,7] (7,99]; vacío con Corte 0, que queda fuera del modelo)",
     "", "2011-2026", "calculada"),
    # ---- agua al final del ciclo
    ("defsr_fin", "Falta de agua del mes 8 a la cosecha sin contar el riego = evaporación − lluvia", "mm", "2022-2026",
     "EMA (evaporación calculada y lluvia)"),
    ("mm_fin", "Lámina de riego aplicada del mes 8 a la cosecha (Σ área regada × mm ÷ área neta)", "mm", "2022-2026",
     "consolidado de riegos de Riopaila"),
    ("def_fin", "Falta de agua después del riego = defsr_fin − mm_fin", "mm", "2022-2026", "calculada"),
    ("def_na", "1 = cosecha 2022+ sin dato de agua", "0/1", "2022-2026", "control de dato"),
    ("def100", "def_fin ÷ 100 (0 si no hay dato); un solo coeficiente que luego se parte en sequía y riego", "100 mm",
     "2022-2026", "calculada"),
    ("defsr100", "defsr_fin ÷ 100", "100 mm", "2022-2026", "calculada"),
    ("mm100", "mm_fin ÷ 100", "100 mm", "2022-2026", "calculada"),
    # ---- labores del ciclo (socas)
    ("rot", "Oportunidad de la roturación: a tiempo, tardío, sin registro", "", "2024-2026",
     "control oficial de roturación; si no está, SimpleAgri (fecha − 10 días, tardía > 30 días del corte)"),
    ("rot_de", "De dónde salió rot: control o SimpleAgri", "", "2024-2026", ""),
    ("d_mal", "Días del corte al primer herbicida (SimpleAgri − 7 días)", "días", "2024-2026", "SimpleAgri"),
    ("d_fert", "Días del corte a la primera fertilización", "días", "2024-2026", "SimpleAgri"),
    ("lab_na", "1 = plantilla o ciclo sin dato de labores", "0/1", "2011-2026", "control de dato"),
    ("rot_na", "1 = roturación sin registro", "0/1", "2024-2026", "control de dato"),
    ("rot_tard", "1 = roturación tardía", "0/1", "2024-2026", "calculada"),
    ("mal_na", "1 = sin registro de herbicida", "0/1", "2024-2026", "control de dato"),
    ("mal_extra30", "Días de herbicida después de 90, ÷ 30", "30 días", "2024-2026", "calculada"),
    ("fert_na", "1 = sin registro de fertilización", "0/1", "2024-2026", "control de dato"),
    ("fert_120", "1 = fertilización después de 120 días", "0/1", "2024-2026", "calculada"),
    ("no_renov", "1 = suerte del plan de renovación 2025 que siguió como soca (cosechas 2026)", "0/1", "2026",
     "plan de renovación 2025"),
    # ---- corte anterior
    ("ant", "Corte anterior: manual, mecánica tras manual (primera vez), mecánica seguida (dos mecanizados), mecánica antes "
            "sin dato, plantilla o sin dato", "", "2011-2026", "ZQM (cosecha anterior de la misma suerte, corte consecutivo)"),
    ("pm_new", "1 = corte anterior mecanizado por primera vez (después de manual o plantilla)", "0/1", "2011-2026", "calculada"),
    ("pm_seg", "1 = dos cortes mecanizados seguidos", "0/1", "2011-2026", "calculada"),
    ("pm_nd", "1 = corte anterior mecanizado, el de antes sin dato", "0/1", "2011-2026", "calculada"),
    ("p_na", "1 = plantilla o corte anterior sin dato (control)", "0/1", "2011-2026", "control de dato"),
    # ---- nivel freático
    ("nf_ciclo", "Nivel freático promedio del ciclo (del corte anterior a la cosecha); IDW potencia 2 de hasta 4 pozos a menos de "
                 "1,5 km del centroide de la suerte", "m de profundidad", "2021-2026",
     "Registro de nivel freático de Ingeniería Agrícola de Riopaila (202 pozos)"),
    ("nf_45", "Nivel promedio de los 45 días antes de la cosecha", "m", "2021-2026", "ídem"),
    ("nf_min", "Nivel más superficial del ciclo", "m", "2021-2026", "ídem"),
    ("nf_lt1", "Parte de las lecturas del ciclo a menos de 1 m", "fracción", "2021-2026", "ídem"),
    ("nf_n", "Número de lecturas del ciclo", "", "2021-2026", "ídem"),
    ("nf_exc15", "Metros por encima de 1,5 m: máx(1,5 − nf_ciclo, 0); 0 si no hay dato", "m", "2021-2026", "calculada"),
    ("nf_na", "1 = sin dato de freático", "0/1", "2011-2026", "control de dato"),
    # ---- suelo húmedo
    ("mm_ca", "Lluvia de la EMA en el mes del corte anterior (corte consecutivo)", "mm", "2012-2026", "EMA"),
    ("ca_hum", "1 = corte anterior en suelo húmedo (mm_ca ≥ 100)", "0/1", "2012-2026", "calculada"),
    ("ca_mm100", "mm_ca topado en 400, ÷ 100 (0 si no hay dato)", "100 mm", "2012-2026", "calculada"),
    ("cah_na", "1 = corte anterior conocido sin dato de lluvia", "0/1", "2012-2026", "control de dato"),
    ("mm_rot", "Lluvia en el pluviómetro de la suerte en los 5 días antes de la roturación (probada, sin efecto confiable)",
     "mm", "2024-2026", "pluviómetros de Riopaila"),
    ("rot_hum", "1 = roturación con ≥ 1 mm en esos 5 días", "0/1", "2024-2026", "calculada"),
    ("mm_fert", "Lluvia en los 5 días antes de la fertilización (probada, sin efecto confiable)", "mm", "2024-2026",
     "pluviómetros de Riopaila"),
    ("fert_hum", "1 = fertilización con ≥ 1 mm en esos 5 días", "0/1", "2024-2026", "calculada"),
    ("rot_mm10", "mm_rot topado en 50, ÷ 10", "10 mm", "2024-2026", "calculada"),
    ("fert_mm10", "mm_fert topado en 50, ÷ 10", "10 mm", "2024-2026", "calculada"),
    ("roth_na", "1 = roturación registrada sin lluvia", "0/1", "2024-2026", "control de dato"),
    ("ferth_na", "1 = fertilización registrada sin lluvia", "0/1", "2024-2026", "control de dato"),
]
DIC = pd.DataFrame(D, columns=["variable", "descripción", "unidad", "años con dato", "fuente o cálculo"])

c = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
c = c[DIC.variable].copy()
c["cosecha"] = c.cosecha.dt.date
c["ini"] = c.ini.dt.date
c = c.sort_values(["ste", "anio", "Mes"]).reset_index(drop=True)
modelo = c.llu03.notna() & c.d32.notna() & c.soca_b.notna()
print(f"{len(c):,} cosechas ({int(modelo.sum()):,} entran al modelo) · {c.ste.nunique()} suertes · {c.columns.size} columnas")

(SAL / "datos").mkdir(parents=True, exist_ok=True)
(SAL / "programas").mkdir(exist_ok=True)
NOM = "cosechas_riopaila_2011-2026"
c.to_csv(SAL / "datos" / f"{NOM}.csv", index=False, encoding="utf-8-sig")
DIC.to_csv(SAL / "datos" / "diccionario_variables.csv", index=False, encoding="utf-8-sig")
with pd.ExcelWriter(SAL / "datos" / f"{NOM}.xlsx", engine="openpyxl") as w:
    c.to_excel(w, sheet_name="Cosechas", index=False)
    DIC.to_excel(w, sheet_name="Diccionario", index=False)
    resumen = c.assign(modelo=modelo).groupby("anio").agg(cosechas=("ste", "size"), en_modelo=("modelo", "sum"),
                                                         ha=("Area", "sum"), t=("TC-Total", "sum"))
    resumen["TCH"] = resumen.t / resumen.ha
    resumen.reset_index().to_excel(w, sheet_name="Resumen por año", index=False)
for f in AQUI.glob("*.py"):
    shutil.copy2(f, SAL / "programas" / f.name)
shutil.copy2(AQUI / "LEEME.md", SAL / "LEEME.md")
shutil.copy2(AQUI / "METODO.md", SAL / "METODO.md")
if shutil.which("pandoc"):
    subprocess.run(["pandoc", str(AQUI / "METODO.md"), "-o", str(SAL / "METODO.docx")], check=True)
print("guardado:", SAL)
