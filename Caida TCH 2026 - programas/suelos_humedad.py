# -*- coding: utf-8 -*-
r"""Riopaila por grupo de humedad del suelo (H0-H5: exceso de humedad en mm/año y permeabilidad).

Entradas:
  · «suelos tch}.xlsx»: suerte, orden, suborden, consociación, régimen de humedad, grupo de humedad (H0-H5) y permeabilidad.
  · Maestro de Suertes 2026: área neta y zona agroecológica (su código también trae el grupo de humedad, p. ej. 5H3).
  · rio_integrado_dataset.pkl: cosechas 2011-2026 (TCH de báscula, controles del modelo).
  · <web>/data/suertes.json: las cosechas ene-sep 2026 con historia, PPTO y lo que le quitó cada causa.
Qué responde: cuánta área hay en cada grupo, cuánto rinde cada grupo (historia, 2026, PPTO), cómo le fue en 2026 y si la
cosecha mecanizada o el corte con el suelo húmedo pegan más en los suelos con exceso de humedad (H3-H4, permeabilidad lenta).
Interacciones con el mismo modelo de la caída (efectos fijos de suerte, año y mes; edad, etapa de la soca, incendio).

Uso: <tch-motor>\.venv-gee\Scripts\python.exe suelos_humedad.py <suelos tch}.xlsx> <Maestro Suertes 2026.xlsx>
       <datos intermedios> <carpeta web> <salida.xlsx>
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
SUE, MAESTRO, PK, WEB, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
GR = ["H0", "H1", "H2", "H3", "H4", "H5"]


def arregla(v):   # el Excel trae tildes mal codificadas (Ãcuico → Ácuico)
    if not isinstance(v, str):
        return v
    v = v.replace("Ã", "Á")
    try:
        return v.encode("cp1252").decode("utf-8").strip()
    except (UnicodeEncodeError, UnicodeDecodeError):
        return v.strip()


s = pd.read_excel(SUE)
s.columns = [c.strip() for c in s.columns]
s = s.apply(lambda c: c.map(arregla))
s = s.rename(columns={"suerte": "ste", "Grupo humedad": "grupo", "Permeabilidad": "perm", "regimen_humedad": "regimen"})
s["ste"] = s.ste.astype(str).str.strip()
dup = s[s.ste.duplicated(keep=False)]
conflicto = dup.groupby("ste").grupo.nunique().gt(1).sum()
s = s.drop_duplicates("ste")

M = list(openpyxl.load_workbook(MAESTRO, read_only=True, data_only=True)["MAESTRO"].iter_rows(min_row=5, values_only=True))
pm = pd.DataFrame(M[1:], columns=[str(v).strip() if v is not None else f"c{j}" for j, v in enumerate(M[0])])
pm = pm.loc[:, ~pm.columns.duplicated()]
pm = pm[pm.SUERTE.notna()].assign(ste=lambda t: t.SUERTE.astype(str).str.strip()).drop_duplicates("ste").set_index("ste")
pm["ha"] = pd.to_numeric(pm["AREA NETA HA"], errors="coerce")
pm["za"] = pm["Zona Agroecologica"].astype(str).str.strip()
pm["grupo_za"] = pm.za.str.extract(r"(H\d)")[0]
s["ha"] = s.ste.map(pm.ha)
s["grupo_za"] = s.ste.map(pm.grupo_za)
s["en_maestro"] = s.ste.isin(pm.index)
S0 = pd.DataFrame(json.load(open(WEB / "data" / "suertes.json", encoding="utf-8")))

print(f"cosechadas ene-sep 2026 que están en el Excel: {S0.s.isin(s.ste).sum()} de {len(S0)}")
print(f"Excel: {len(s)} suertes ({len(dup)} filas repetidas, {conflicto} con grupos distintos) · en el Maestro {s.en_maestro.sum()} · "
      f"{s.ha.sum():,.0f} ha de {pm.ha.sum():,.0f} ha del Maestro")
print("sin grupo de humedad:", s.grupo.isna().sum(), "suertes", round(s.ha[s.grupo.isna()].sum()), "ha")
cmp_ = s.dropna(subset=["grupo", "grupo_za"])
print(f"grupo del Excel = grupo del código de zona agroecológica en {100 * (cmp_.grupo == cmp_.grupo_za).mean():.0f} % de {len(cmp_)}")
print(pd.crosstab(cmp_.grupo, cmp_.grupo_za).to_string())

# ---------------------------------------------------------------- área cosechada ene-sep 2026 y suelos por grupo
S0["grupo"] = S0.s.map(s.set_index("ste").grupo).fillna("sin dato")
a26 = S0.groupby("grupo").agg(cosechas=("k", "size"), ha=("a", "sum"))
a26["%"] = 100 * a26.ha / a26.ha.sum()
a26 = a26.reindex([g for g in GR + ["sin dato"] if g in a26.index])
print("área cosechada ene-sep 2026 por grupo:\n", a26.round(1).to_string())
area = s.groupby("grupo").agg(suertes=("ste", "size"), ha=("ha", "sum"),
                              permeabilidad=("perm", lambda x: ", ".join(f"{k} {v}" for k, v in x.value_counts().items())),
                              regimen=("regimen", lambda x: ", ".join(f"{k} {v}" for k, v in x.value_counts().items())),
                              orden=("Orden", lambda x: ", ".join(f"{k} {v}" for k, v in x.value_counts().head(3).items())))
area["% del área"] = (100 * area.ha / area.ha.sum()).round(1)
area = area.reindex([g for g in GR if g in area.index])
print(area.round(0).to_string())

# ---------------------------------------------------------------- TCH por grupo
ds = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
ds["grupo"] = ds.ste.map(s.set_index("ste").grupo)
w = lambda g, c: float(np.average(g[c], weights=g.Area)) if len(g) else np.nan  # noqa: E731
hist = ds[ds.anio.between(2020, 2025)].groupby("grupo").apply(lambda g: pd.Series({"TCH 2020-25": w(g, "tch_calc"), "cosechas 2020-25": len(g)}))
S = pd.DataFrame(json.load(open(WEB / "data" / "suertes.json", encoding="utf-8")))
S["grupo"] = S.s.map(s.set_index("ste").grupo)
S = S[S["hist"].notna() & S["real"].notna()].assign(Area=lambda t: t.a)
AP = pd.DataFrame(list(S.ap), index=S.index)


def g26(g):
    a = AP.loc[g.index]
    out = {"cosechas 2026": len(g), "ha 2026": g.a.sum(), "historia": w(g, "hist"), "real 2026": w(g, "real"),
           "caída TCH": w(g, "real") - w(g, "hist"), "t perdidas": float(((g["real"] - g["hist"]) * g.a).sum()),
           "PPTO": w(g.dropna(subset=["ppto"]), "ppto"), "% cosecha mecanizada": 100 * float(np.average(g.tipo == "Mecanizada", weights=g.a))}
    for k, et in (("mecanica", "cosecha mecanizada"), ("corte-humedo", "suelo húmedo"), ("freatico", "nivel freático"),
                  ("sequia", "sequía"), ("riego", "riego"), ("corte-anterior", "corte anterior mecanizado")):
        out[f"le quitó: {et}"] = -float(np.average(a[k].fillna(0), weights=g.a))
    out["sin explicar"] = -float(np.average(g.se.fillna(0), weights=g.a))
    return pd.Series(out)


r26 = S.groupby("grupo").apply(g26)
tch = hist.join(r26, how="outer").reindex([g for g in GR if g in hist.index or g in r26.index])
print(tch.round(1).T.to_string())

# ---------------------------------------------------------------- ¿pega más la cosecha mecanizada en suelos húmedos?
d = ds[ds.grupo.notna()].copy()
d["humedo"] = d.grupo.isin(["H3", "H4", "H5"]).astype(float)
BASE = "y ~ C(ste) + C(anio) + C(Mes) + C(edad_b) + C(soca_b) + inc"
pruebas = []
for nombre, extra, k in (
        ("Cosecha mecanizada en suelos H0-H2", "mec + mec:humedo", "mec"),
        ("Cosecha mecanizada: diferencia adicional en H3-H4", "mec + mec:humedo", "mec:humedo"),
        ("Corte anterior en suelo húmedo (por 100 mm) en H0-H2", "ca_mm100 + ca_mm100:humedo + mec", "ca_mm100"),
        ("Corte anterior en suelo húmedo: diferencia adicional en H3-H4", "ca_mm100 + ca_mm100:humedo + mec", "ca_mm100:humedo")):
    dd = d.dropna(subset=["ca_mm100"]) if "ca_mm100" in extra else d
    mo = smf.wls(f"{BASE} + {extra}", data=dd, weights=dd.Area)
    f = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dd.loc[mo.data.row_labels, "ste"])[0]})
    pct = 100 * np.expm1(f.params[k])
    pruebas.append({"prueba": nombre, "efecto %": round(pct, 1), "TCH (sobre 118,4)": round(pct / 100 * 118.4, 1),
                    "p": round(f.pvalues[k], 3), "cosechas": int(f.nobs)})
pr = pd.DataFrame(pruebas)

# ---------------------------------------------------------------- datos del informe (pestaña «Suelos y humedad» y ficha de cada suerte)
DEF = {"H0": "Déficit de humedad, sin exceso", "H1": "Exceso menor a 200 mm/año",
       "H2": "Exceso de 200 a 400 mm/año (o menos de 200 en suelos de permeabilidad baja)",
       "H3": "Exceso de 400 a 600 mm/año (o 200 a 400 en suelos de permeabilidad baja)",
       "H4": "Exceso mayor a 600 mm/año (o 400 a 600 en suelos arcillosos de permeabilidad baja)",
       "H5": "Exceso mayor a 600 mm/año en suelos arcillosos de permeabilidad baja a media y relieve plano"}
r1 = lambda v, n=1: None if v is None or pd.isna(v) else round(float(v), n)  # noqa: E731
mayor = lambda x: x.value_counts().index[0] if x.notna().any() else None  # noqa: E731
grupos = []
for g in GR:
    if g not in a26.index:
        continue
    sg_ = s[s.grupo == g]
    t = tch.loc[g] if g in tch.index else pd.Series(dtype=float)
    grupos.append({"g": g, "def": DEF[g], "cosechas": int(a26.loc[g, "cosechas"]), "ha": r1(a26.loc[g, "ha"], 0), "pct": r1(a26.loc[g, "%"]),
                   "perm": mayor(sg_.perm), "regimen": mayor(sg_.regimen), "orden": mayor(sg_.Orden),
                   "hist2025": r1(t.get("TCH 2020-25")), "historia": r1(t.get("historia")), "real": r1(t.get("real 2026")),
                   "caida": r1(t.get("caída TCH")), "t": r1(t.get("t perdidas"), 0), "ppto": r1(t.get("PPTO")),
                   "mec": r1(t.get("% cosecha mecanizada"), 0), "n26": int(t.get("cosechas 2026", 0) or 0),
                   "quito": {k: r1(t.get("le quitó: " + k)) for k in ["cosecha mecanizada", "suelo húmedo", "nivel freático", "sequía", "riego", "corte anterior mecanizado"]},
                   "se": r1(t.get("sin explicar"))})
sd = a26.loc["sin dato"] if "sin dato" in a26.index else None
out = {"grupos": grupos, "sin_dato": None if sd is None else [int(sd.cosechas), r1(sd.ha, 0), r1(sd["%"])],
       "coinciden_za": r1(100 * (cmp_.grupo == cmp_.grupo_za).mean(), 0),
       "pruebas": [[p["prueba"], p["efecto %"], p["TCH (sobre 118,4)"], p["p"]] for p in pruebas],
       "suertes": {r.ste: [r.grupo, r.perm, r.Orden, r.suborden, r.regimen] for r in s.itertuples() if isinstance(r.grupo, str)}}
json.dump(out, open(WEB / "data" / "suelos.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("escrito:", WEB / "data" / "suelos.json")
print(pr.to_string(index=False))

lee = pd.DataFrame({"Nota": [
    "Grupo de humedad = exceso de humedad del suelo: H0 sin exceso, H1 < 200 mm/año, H2 200-400, H3 400-600, H4 > 600 "
    "(los rangos bajan un escalón en suelos de permeabilidad baja). Fuente: «suelos tch}.xlsx».",
    "Área: área neta del Maestro de Suertes 2026. TCH 2020-25: todas las cosechas de esos años. 2026: cosechas ene-sep con historia.",
    "«le quitó»: TCH promedio que le quitó cada causa del modelo a las cosechas 2026 del grupo (negativo = sumó).",
    "Pruebas: mismo modelo de la caída (cada suerte frente a sí misma), con la cosecha mecanizada o el corte en suelo húmedo "
    "separados entre suelos H0-H2 y H3-H4. «diferencia adicional» = cuánto más (o menos) pega en H3-H4.",
    "Lo que no demuestra: el grupo de humedad no cambia dentro de una suerte, así que su efecto propio sobre el TCH no se puede "
    "separar de todo lo demás que tiene cada suerte; la comparación entre grupos es descriptiva."]})
with pd.ExcelWriter(OUT) as x:
    lee.to_excel(x, sheet_name="Léeme", index=False)
    area.reset_index().to_excel(x, sheet_name="Área por grupo", index=False)
    tch.round(1).reset_index().to_excel(x, sheet_name="TCH por grupo", index=False)
    pr.to_excel(x, sheet_name="Pruebas", index=False)
    s.drop(columns=["en_maestro"]).rename(columns={"ste": "suerte"}).to_excel(x, sheet_name="Suertes", index=False)
print("escrito:", OUT)
