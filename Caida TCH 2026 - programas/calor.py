# -*- coding: utf-8 -*-
"""Días con Tmax > 32 °C en los 30 días antes de la cosecha (escalado a 30 días), 2026 vs 2020-25, por planta y mes.
Riopaila: EMA La Paila / Bugalagrande (repo, hasta 8-sep-2026) + Meteoportal de Cenicaña (diario 2026, hasta 18-oct).
Castilla: promedio de sus estaciones de Cenicaña (CSV de Castilla hasta 27-sep-2026 + Meteoportal hasta 18-oct).
Efecto por día: el ya estimado el 29-sep con el modelo completo (Riopaila −0,27 %/día; Castilla −0,49 %/día)."""
import sys
sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
import numpy as np, pandas as pd, openpyxl
from tchmotor import dataset_gee as dg, produccion as pr
sys.stdout.reconfigure(encoding="utf-8")
EFECTO = {"riopaila": -0.0027, "castilla": -0.0049}
dias = pd.date_range("2010-01-01", "2026-10-18", freq="D")
# Meteoportal 2026
wb = openpyxl.load_workbook(r"C:\Users\Agr349\Documents\RIOPAILA AGRICOLA\Clima Cenicaña\Clima_Cenicana_Riopaila_Castilla_1993-2026.xlsx", read_only=True, data_only=True)
it = wb["Diario 2026"].iter_rows(values_only=True); enc = next(it)
M = pd.DataFrame(list(it), columns=enc)
M["Fecha"] = pd.to_datetime(M.Fecha)
Mt = M.pivot_table(index="Fecha", columns="Código", values="Temperatura máxima (°C)")
# Riopaila EMA
e = pd.read_csv("Precipitacion-riopaila/clima_estaciones.csv", sep=";")
e["f"] = pd.to_datetime(e.fc_obsrvcion)
E = e.pivot_table(index="f", columns="nm_ema", values="tmp_mxma").reindex(dias)
for est, cod in (("La Paila", "PAI"), ("Bugalagrande", "BLG")):
    ov = E[est].dropna().index.intersection(Mt[cod].dropna().index)
    print(f"{est}: repo vs Meteoportal en {len(ov)} días de 2026: diferencia media {(E.loc[ov, est] - Mt.loc[ov, cod]).mean():+.2f} °C, "
          f"r={np.corrcoef(E.loc[ov, est], Mt.loc[ov, cod])[0, 1]:.2f}")
    falta = E[est].isna() & (E.index >= "2026-01-01")
    E.loc[falta, est] = Mt[cod].reindex(E.index)[falta]
# Castilla
cs = pd.read_csv(r"C:\Users\Agr349\Documents\RIOPAILA AGRICOLA\04 Presupuesto, inversion y junta\JUNTA DIRECTIVA\CASTILLA\Consultas Climatologícas Cenicaña(Datos Originales).csv",
                 sep=";", encoding="latin-1", decimal=",", low_memory=False)
cs["f"] = pd.to_datetime(cs.Fecha, dayfirst=True, errors="coerce")
cs["tmax"] = pd.to_numeric(cs["Temperatura Maxima"].astype(str).str.replace(",", "."), errors="coerce")
cs = cs[cs.Depto.astype(str).str.strip() == "Valle"]
cs["Estacion"] = cs.Estacion.astype(str).str.strip().str.capitalize()
C = cs.pivot_table(index="f", columns="Estacion", values="tmax").reindex(dias)
C = C.where((C > 20) & (C < 42))  # quita máximas imposibles
nom = {"Pradera": "PRA", "Florida": "FLO", "Candelaria": "CAN", "El tiple": "TIP", "Cenicana": "CEN", "Miranda": "MIR"}
print("estaciones de Castilla (Valle) en el CSV:", sorted(C.columns))
ccol = [c for c in C.columns if c in nom]
for c in ccol:
    ov = C[c].dropna().index.intersection(Mt[nom[c]].dropna().index)
    if len(ov):
        print(f"  {c}: CSV vs Meteoportal {len(ov)} días: {(C.loc[ov, c] - Mt.loc[ov, nom[c]]).mean():+.2f} °C")
    falta = C[c].isna() & (C.index >= "2026-01-01")
    C.loc[falta, c] = Mt[nom[c]].reindex(C.index)[falta]
TMAX = {"castilla": C[ccol].mean(axis=1)}
es = pd.read_csv("Precipitacion-riopaila/estaciones_suertes.csv", sep=";", encoding="latin-1", skiprows=1)
print("estaciones_suertes:", es.columns.tolist()[:6])

def d32(serie, f):
    s = serie.loc[f - pd.Timedelta(days=30): f - pd.Timedelta(days=1)]
    return (s > 32).sum() * 30 / s.notna().sum() if s.notna().sum() >= 20 else np.nan

c = dg.cortes_zqm(dg.leer_zqm())
maestro, _ = pr.cargar_maestro()
rec, _ = pr.cosechas_recientes(pr.leer_cosechas_recientes(), maestro, c)
c = pd.concat([c, rec], ignore_index=True).drop_duplicates("key")
c = c[(c.ha > 0) & c.tch.between(20, 300) & (c.anio >= 2020)].copy()
c["f"] = pd.to_datetime(c.harvest)
c.to_pickle("cortes_2020_2026.pkl")
# estación de cada suerte de Riopaila
col_s = next(k for k in es.columns if "suerte" in k.lower() or "ste" in k.lower())
col_e = next(k for k in es.columns if "esta" in k.lower() or "ema" in k.lower())
est_de = dict(zip(es[col_s].astype(str).str.strip(), es[col_e].astype(str).str.strip()))
def serie(planta, sec):
    if planta == "castilla":
        return TMAX["castilla"]
    e_ = est_de.get(sec, "La Paila")
    return E["Bugalagrande"] if "buga" in e_.lower() else E["La Paila"]
c["d32"] = [d32(serie(p, s), f) for p, s, f in zip(c.planta, c.sec_ste, c.f)]
c.to_pickle("cortes_calor_oct.pkl")
wm = lambda d, k: np.average(d[k].dropna(), weights=d.ha[d[k].notna()]) if d[k].notna().any() else np.nan
for planta in ("riopaila", "castilla"):
    d = c[c.planta == planta]
    print(f"\n==== {planta.upper()}: días > 32 °C en los 30 días antes de cosechar (ponderado por área); efecto {100 * EFECTO[planta]:.2f} %/día")
    for lab, meses in [("ene-ago", range(1, 9)), ("ene-oct", range(1, 11)), ("sep", [9]), ("oct", [10]), ("sep-oct", [9, 10])]:
        q, r = d[(d.anio == 2026) & d.mes.isin(meses)], d[d.anio.between(2020, 2025) & d.mes.isin(meses)]
        a, b = wm(q, "d32"), wm(r, "d32")
        print(f"  {lab:8s} 2026 {a:5.1f} días vs 2020-25 {b:5.1f} → aporte {100 * EFECTO[planta] * (a - b):+.1f} %   "
              f"(cobertura {100 * q.d32.notna().mean():.0f} %)")
    print("  por año, sep-oct:", {a_: round(wm(d[(d.anio == a_) & d.mes.isin([9, 10])], "d32"), 1) for a_ in range(2020, 2027)})
