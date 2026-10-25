# -*- coding: utf-8 -*-
r"""Riopaila 2026: ¿la caña cosechada tuvo el desarrollo óptimo de su variedad?

Entradas:
  · «optimo de las variedades.xlsx»: hoja Matriz (una fila por cosecha ene-sep 2026; aforo suerte a suerte en las
    columnas Alltura [cm], Población [tallos/m] y Diametro [cm]) y hoja Optimo (altura, diámetro y tallos/m del óptimo
    de cada variedad).
  · tablero_web\data\suertes.json (informe_datos.py): TCH real, historia 2020-25, PPTO, corte anterior y tipo de cosecha.
Para cada cosecha con aforo: % del óptimo de su variedad en altura, población y diámetro, y un índice de peso de caña
(población × altura × diámetro², frente al mismo producto del óptimo). Luego:
  · despoblación según el corte anterior (el aforo se mide en la caña en pie, antes de la cosecha de 2026: la población
    que mide viene del corte anterior, no del método de la cosecha de 2026);
  · relación del desarrollo con el TCH real frente a la historia 2020-25 de la suerte y frente al PPTO.
Todo ponderado por área; regresiones con errores robustos. Sin nombres de personas en la salida.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe desarrollo_optimo.py <optimo de las variedades.xlsx> <suertes.json> <salida.xlsx>
       [<tablero_web>]
Con <tablero_web> escribe además data/desarrollo.json para el informe (pestaña Desarrollo, ficha de cada suerte y causa
Corte anterior mecanizado). Va después de informe_datos.py, porque lee su suertes.json.
"""
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 220)
XL, SJ, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
WEB = sys.argv[4] if len(sys.argv) > 4 else None
MED = {"alt": "Alltura", "pob": "Población", "dia": "Diametro"}
ANT = {"manual": "Manual", "mecánica tras manual": "Mecanizado, primera vez", "mecánica seguida": "Mecanizado, repetido",
       "mecánica, antes sin dato": "Mecanizado, antes sin dato", "plantilla o sin dato": "Plantilla o sin dato"}

hojas = pd.ExcelFile(XL).sheet_names
m = pd.read_excel(XL, sheet_name=next(h for h in hojas if "atriz" in h)).rename(columns=lambda c: str(c).strip())
o = pd.read_excel(XL, sheet_name=next(h for h in hojas if "ptimo" in h), header=1)
o.columns = ["Variedad", "opt_alt", "opt_dia", "opt_pob"]
o["Variedad"] = o.Variedad.astype(str).str.strip()

d = m[["suerte", "Zona", "MES", "Cor", "Variedad", "Area", "TCH"] + list(MED.values())].copy()
d = d.rename(columns={v: k for k, v in MED.items()})
d["suerte"], d["Variedad"] = d.suerte.astype(str).str.strip(), d.Variedad.astype(str).str.strip()
d = d.merge(o, on="Variedad", how="left")
con = (d[list(MED)].fillna(0) > 0).all(axis=1)
print(f"cosechas en la matriz: {len(d)} ({d.Area.sum():,.0f} ha); con aforo: {int(con.sum())} ({d.Area[con].sum():,.0f} ha); "
      f"con aforo y óptimo de su variedad: {int((con & d.opt_pob.notna()).sum())}")
print("  variedades sin óptimo:", sorted(d.Variedad[con & d.opt_pob.isna()].unique()))
d = d[con & d.opt_pob.notna()].copy()
for k in MED:
    d[f"p_{k}"] = 100 * d[k] / d[f"opt_{k}"]
# peso de caña ∝ tallos × altura × diámetro² (volumen del tallo); frente al mismo producto del óptimo
d["p_peso"] = 100 * (d.pob * d.alt * d.dia ** 2) / (d.opt_pob * d.opt_alt * d.opt_dia ** 2)

# ---------------------------------------------------------------- cruce con el informe (TCH, historia, PPTO, corte anterior)
S = pd.DataFrame(json.load(open(SJ, encoding="utf-8")))
S = S.rename(columns={"s": "suerte", "m": "MES"})[["suerte", "MES", "h", "tipo", "ant", "real", "hist", "ppto", "a"]]
d = d.merge(S, on=["suerte", "MES"], how="left")
d["ant_txt"] = d.ant.map(ANT)
print(f"cruzan con el informe (suerte y mes): {int(d.real.notna().sum())} de {len(d)}")

wm = lambda g, k: np.average(g[k], weights=g.Area) if len(g) else np.nan  # noqa: E731
P = ["p_pob", "p_alt", "p_dia", "p_peso"]


def resumen(g):
    r = {"cosechas": len(g), "ha": g.Area.sum()}
    for k in P:
        r[k] = wm(g, k)
    for k in ["p_pob", "p_alt", "p_dia"]:
        r[k + "_bajo"] = 100 * g.Area[g[k] < 95].sum() / g.Area.sum()   # más de 5 % por debajo del óptimo
    return pd.Series(r)


NOM = {"cosechas": "Cosechas", "ha": "Área (ha)", "p_pob": "Población % del óptimo", "p_alt": "Altura % del óptimo",
       "p_dia": "Diámetro % del óptimo", "p_peso": "Peso de caña % del óptimo (índice)",
       "p_pob_bajo": "% del área con población <95 %", "p_alt_bajo": "% del área con altura <95 %",
       "p_dia_bajo": "% del área con diámetro <95 %"}
total = resumen(d).to_frame("Riopaila ene-sep 2026").T
por_var = d.groupby("Variedad").apply(resumen, include_groups=False).sort_values("ha", ascending=False)
por_ant = d[d.ant_txt.notna()].groupby("ant_txt").apply(resumen, include_groups=False).sort_values("ha", ascending=False)
por_tipo = d[d.tipo.notna()].groupby("tipo").apply(resumen, include_groups=False)
por_zona = d.groupby("Zona").apply(resumen, include_groups=False)
print("\n", total.round(1).to_string())
print("\npor variedad:\n", por_var.round(1).to_string())
print("\npor corte anterior:\n", por_ant.round(1).to_string())

# ---------------------------------------------------------------- despoblación y corte anterior (misma variedad)
e = d[d.ant.isin(["manual", "mecánica tras manual", "mecánica seguida"])].copy()
e["ant_c"] = pd.Categorical(e.ant, ["manual", "mecánica tras manual", "mecánica seguida"])
pruebas = []
for k in ["p_pob", "p_alt", "p_dia", "p_peso"]:
    r = smf.wls(f"{k} ~ C(ant_c) + C(Variedad) + C(Zona)", data=e, weights=e.Area).fit(cov_type="HC1")
    for t, et in (("mecánica tras manual", "Mecanizado, primera vez"), ("mecánica seguida", "Mecanizado, repetido")):
        n = f"C(ant_c)[T.{t}]"
        pruebas.append({"k": k, "ant": t, "medida": NOM[k], "corte anterior (frente a manual)": et,
                        "diferencia (puntos de %)": r.params[n], "p": r.pvalues[n], "cosechas": int(r.nobs)})
pruebas = pd.DataFrame(pruebas)
print("\ndesarrollo según el corte anterior (frente a manual, misma variedad y zona):\n", pruebas.round(3).to_string())

# ---------------------------------------------------------------- desarrollo y TCH
t = d[d.real.notna() & d["hist"].notna()].copy()
t["y_hist"] = 100 * np.log(t.real / t["hist"])
tp = t[t.ppto.notna()].copy()
tp["y_ppto"] = 100 * np.log(tp.real / tp.ppto)
for g in (t, tp):
    for k in ["pob", "alt", "dia"]:
        g[f"l_{k}"] = 100 * np.log(g[f"p_{k}"] / 100)    # % por debajo (−) o por encima (+) del óptimo, en log
tch = []
for y, g, et in (("y_hist", t, "TCH real frente a la historia 2020-25"), ("y_ppto", tp, "TCH real frente al PPTO")):
    r = smf.wls(f"{y} ~ l_pob + l_alt + l_dia + C(Variedad)", data=g, weights=g.Area).fit(cov_type="HC1")
    for k, n in (("l_pob", "Población"), ("l_alt", "Altura"), ("l_dia", "Diámetro")):
        tch.append({"y": y, "k": k[2:], "comparación": et, "medida": n, "% de TCH por cada 1 % frente al óptimo": r.params[k],
                    "p": r.pvalues[k], "cosechas": int(r.nobs), "R²": r.rsquared})
tch = pd.DataFrame(tch)
print("\ndesarrollo y TCH (misma variedad):\n", tch.round(3).to_string())
# por grupos de peso de caña: ¿las suertes con menos caña que el óptimo cayeron más?
t["grupo_peso"] = pd.cut(t.p_peso, [0, 80, 90, 100, 110, 1e9], labels=["<80 %", "80-90 %", "90-100 %", "100-110 %", "≥110 %"])
gp = t.groupby("grupo_peso", observed=True).apply(lambda g: pd.Series({
    "cosechas": len(g), "ha": g.Area.sum(), "TCH historia": wm(g, "hist"), "TCH real": wm(g, "real"),
    "cambio frente a la historia (%)": 100 * (wm(g, "real") / wm(g, "hist") - 1),
    "TCH PPTO": wm(g[g.ppto.notna()], "ppto")}), include_groups=False)
print("\npor peso de caña frente al óptimo:\n", gp.round(1).to_string())

# ---------------------------------------------------------------- salida
suertes = d[["suerte", "Zona", "h", "MES", "Cor", "Variedad", "Area", "tipo", "ant_txt", "real", "hist", "ppto",
             "alt", "opt_alt", "p_alt", "pob", "opt_pob", "p_pob", "dia", "opt_dia", "p_dia", "p_peso"]].rename(columns={
    "suerte": "Suerte", "h": "Hacienda", "MES": "Mes", "Cor": "Corte", "Area": "Área (ha)", "tipo": "Cosecha 2026",
    "ant_txt": "Corte anterior", "real": "TCH real", "hist": "TCH historia", "ppto": "TCH PPTO",
    "alt": "Altura (cm)", "opt_alt": "Altura óptima", "p_alt": "Altura % del óptimo", "pob": "Población (tallos/m)",
    "opt_pob": "Población óptima", "p_pob": "Población % del óptimo", "dia": "Diámetro (cm)", "opt_dia": "Diámetro óptimo",
    "p_dia": "Diámetro % del óptimo", "p_peso": "Peso de caña % del óptimo (índice)"}).sort_values("Peso de caña % del óptimo (índice)")
with pd.ExcelWriter(OUT) as w:
    total.rename(columns=NOM).round(1).to_excel(w, sheet_name="Resumen")
    por_var.rename(columns=NOM).round(1).to_excel(w, sheet_name="Por variedad")
    por_ant.rename(columns=NOM).round(1).to_excel(w, sheet_name="Por corte anterior")
    por_tipo.rename(columns=NOM).round(1).to_excel(w, sheet_name="Por cosecha 2026")
    por_zona.rename(columns=NOM).round(1).to_excel(w, sheet_name="Por zona")
    pruebas.drop(columns=["k", "ant"]).round(3).to_excel(w, sheet_name="Prueba corte anterior", index=False)
    tch.drop(columns=["y", "k"]).round(3).to_excel(w, sheet_name="Desarrollo y TCH", index=False)
    gp.round(1).to_excel(w, sheet_name="Por peso de caña")
    suertes.round(1).to_excel(w, sheet_name="Suertes", index=False)
    o.rename(columns={"opt_alt": "Altura (cm)", "opt_dia": "Diámetro (cm)", "opt_pob": "Tallos/m"}).round(2).to_excel(
        w, sheet_name="Óptimo por variedad", index=False)
print("\nescrito:", OUT)

# ---------------------------------------------------------------- datos para el informe (el filtrado y los promedios se hacen en la página)
if WEB:
    r1 = lambda v, n=1: None if pd.isna(v) else round(float(v), n)  # noqa: E731
    out = {"cosechas_matriz": len(m), "sin_aforo": int((~con).sum()),
           "sin_optimo": sorted(m.Variedad[con].astype(str).str.strip()[~m.Variedad[con].astype(str).str.strip().isin(o.Variedad)].unique()),
           "filas": [{"s": r.suerte, "m": int(r.MES), "v": r.Variedad, "a": r1(r.Area, 2),
                      "alt": r1(r.alt), "oalt": r1(r.opt_alt), "pob": r1(r.pob, 2), "opob": r1(r.opt_pob, 2),
                      "dia": r1(r.dia, 2), "odia": r1(r.opt_dia, 2)} for r in d.itertuples()],
           "pruebas": [{"k": r["k"], "ant": r["ant"], "dif": r1(r["diferencia (puntos de %)"], 2), "p": r1(r["p"], 3),
                        "n": r["cosechas"]} for r in pruebas.to_dict("records")],
           "tch": [{"y": r["y"], "k": r["k"], "coef": r1(r["% de TCH por cada 1 % frente al óptimo"], 3), "p": r1(r["p"], 3),
                    "n": r["cosechas"]} for r in tch.to_dict("records")],
           "optimo": [[r.Variedad, r1(r.opt_alt), r1(r.opt_dia, 2), r1(r.opt_pob, 2)] for r in o.itertuples()]}
    p = f"{WEB}/data/desarrollo.json"
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("escrito:", p, f"({len(out['filas'])} cosechas)")
