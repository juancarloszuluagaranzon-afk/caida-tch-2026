# -*- coding: utf-8 -*-
r"""Riopaila: ¿la roturación, la fertilización y el corte anterior se hicieron con el suelo húmedo?

Para cada cosecha (la soca que salió de ese ciclo):
  · roturación y fertilización (cosechas 2024-26, ciclos_labores.pkl de labores_sa.py): fecha de la roturación = control
    oficial (1.ª labor, «FECHA DE ROTURACION PRIMERA», el corte a menos de 75 días); si no está, SimpleAgri − 10 días;
    fecha de la fertilización = SimpleAgri − 10 días. Lluvia en el pluviómetro de la suerte desde 5 días antes hasta el día
    de la labor; «en húmedo» = 1 mm o más (la regla de Cañicultura). Pluviómetro de la suerte = el del control de
    roturación; si no tiene, el más común de su sector; si no, el más cercano a menos de 3 km.
  · corte anterior (todas las cosechas desde 2012): lluvia de la EMA de la suerte en los 30 días alrededor del corte
    anterior (el ZQM da el mes: del día 1 al 30); «en suelo húmedo» = 100 mm o más (el umbral del análisis de septiembre).
Salida: suelo_humedo.pkl (una fila por cosecha, llaves ste, anio, Mes, Corte), que usa caida_integrada_rio.py.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe suelo_humedo.py <datos intermedios> <CONTROL DE ROTURACION.xlsm>
       <repo Precipitacion-riopaila>
Va después de factores_sep.py y labores_sa.py, y antes de caida_integrada_rio.py.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import gee  # noqa: E402  (solo para los centroides de las suertes)

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 220)
PK, CTRL, REPO = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
K = ["ste", "anio", "Mes", "Corte"]
VENT, UMBRAL, DESF = 5, 1.0, 10        # ≥1 mm desde 5 días antes hasta el día de la labor; SimpleAgri confirma ~10 días después
CORTE_MM = 100                          # corte anterior en suelo húmedo: ≥100 mm en los 30 días del corte

# ---------------------------------------------------------------- lluvia diaria por pluviómetro (2020-2026)
pl = pd.read_csv(REPO / "precipitacion.csv.csv", sep=";", encoding="latin-1", usecols=[1, 2, 3])
pl.columns = ["PLUV", "Fecha", "mm"]
pl["PLUV"] = pl.PLUV.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
pl["Fecha"] = pd.to_datetime(pl.Fecha, format="%d/%m/%Y", errors="coerce")
pl["mm"] = pd.to_numeric(pl.mm.astype(str).str.replace(",", "."), errors="coerce")
L = pl.dropna().groupby(["Fecha", "PLUV"]).mm.mean().unstack().sort_index()
print(f"pluviómetros: {L.shape[1]} · {L.index.min().date()} a {L.index.max().date()}")


def lluvia(p, f, w=VENT):
    if pd.isna(f) or p not in L.columns or f > L.index.max() or f < L.index.min():
        return np.nan
    s = L[p].loc[f - pd.Timedelta(days=w): f]
    return s.sum() if s.notna().sum() >= (w + 1) * 0.6 else np.nan


# ---------------------------------------------------------------- control de roturación: fecha y pluviómetro
F = list(openpyxl.load_workbook(CTRL, read_only=True, data_only=True)["B.D. ROTURACIÓN"].iter_rows(values_only=True))
h = next(i for i, r in enumerate(F) if r and str(r[0]).strip() == "SECTOR-SUERTE")
enc = [re.sub(r"\s+", " ", str(x)).strip() if x is not None else f"c{j}" for j, x in enumerate(F[h])]
C = pd.DataFrame([r[: len(enc)] for r in F[h + 1:]], columns=enc).loc[:, lambda d: ~d.columns.duplicated()]
C = C[C["SECTOR-SUERTE"].notna()].copy()
C["ste"] = C["SECTOR-SUERTE"].astype(str).str.strip()
C["corte_f"] = pd.to_datetime(C["FECHA DE CORTE"], errors="coerce")
C["f1"] = pd.to_datetime(C["FECHA DE ROTURACION PRIMERA"], errors="coerce")
C["pluv"] = C.PLUVIOMETRO.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
C.loc[~C.pluv.str.fullmatch(r"\d+"), "pluv"] = ""
pl_ste = C[C.pluv != ""].groupby("ste").pluv.agg(lambda s: s.mode().iloc[0])
pl_sec = C[C.pluv != ""].assign(sec=C.ste.str[:4]).groupby("sec").pluv.agg(lambda s: s.mode().iloc[0])
gp = json.load(open(r"C:\Users\Agr349\agrocontrol-campo\public\data\contexto_pluviometros.geojson", encoding="utf-8"))["features"]
GP = pd.DataFrame([(str(f["properties"]["Pluviometr"]), *f["geometry"]["coordinates"]) for f in gp], columns=["PLUV", "lon", "lat"])
GP = GP[GP.PLUV.isin(L.columns)].set_index("PLUV")
CEN = gee.centroides_suertes("riopaila")


def pluv_de(ste):
    if ste in pl_ste.index and pl_ste[ste] in L.columns:
        return pl_ste[ste]
    if ste[:4] in pl_sec.index and pl_sec[ste[:4]] in L.columns:
        return pl_sec[ste[:4]]
    c_ = CEN.get(ste)
    if c_ is None or GP.empty:
        return ""
    d = np.hypot((GP.lon - c_[0]) * 111320 * np.cos(np.radians(c_[1])), (GP.lat - c_[1]) * 110570)
    return d.idxmin() if d.min() <= 3000 else ""


CG = {s: g for s, g in C[C.f1.notna() & C.corte_f.notna()].groupby("ste")}


def f1_control(ste, corte):
    g = CG.get(ste)
    if g is None or pd.isna(corte):
        return pd.NaT
    dd = (g.corte_f - corte).dt.days.abs()
    return g.f1.loc[dd.idxmin()] if dd.min() <= 75 else pd.NaT


# ---------------------------------------------------------------- roturación y fertilización (cosechas 2024-26)
cl = pd.read_pickle(PK / "ciclos_labores.pkl").dropna(subset=["h_anio", "h_mes"])
cl = cl.assign(anio=cl.h_anio.astype(int), Mes=cl.h_mes.astype(int), Corte=cl.h_corte)
cl["pluv"] = cl.ste.map(pluv_de)
cl["f_rot_ctrl"] = [f1_control(s, f) for s, f in zip(cl.ste, cl.corte_f)]
cl["f_rot"] = cl.f_rot_ctrl.fillna(cl.corte_f + pd.to_timedelta(cl.d_rot - DESF, unit="D"))
cl["f_fert"] = cl.corte_f + pd.to_timedelta(cl.d_fert - DESF, unit="D")
cl["mm_rot"] = [lluvia(p, f) for p, f in zip(cl.pluv, cl.f_rot)]
cl["mm_fert"] = [lluvia(p, f) for p, f in zip(cl.pluv, cl.f_fert)]
cl["rot_hum"] = np.where(cl.mm_rot.notna(), (cl.mm_rot >= UMBRAL).astype(float), np.nan)
cl["fert_hum"] = np.where(cl.mm_fert.notna(), (cl.mm_fert >= UMBRAL).astype(float), np.nan)
print(f"\nciclos con labores: {len(cl)} · con pluviómetro {(cl.pluv != '').sum()} · fecha de roturación del control "
      f"{cl.f_rot_ctrl.notna().sum()}, de SimpleAgri {(cl.f_rot_ctrl.isna() & cl.d_rot.notna()).sum()} · fertilización {cl.f_fert.notna().sum()}")
print("en suelo húmedo, por año de cosecha (parte de las labores con dato):")
print(cl.groupby("anio")[["rot_hum", "fert_hum"]].agg(["mean", "count"]).round(2))
lab = cl[K + ["pluv", "f_rot", "mm_rot", "rot_hum", "f_fert", "mm_fert", "fert_hum"]].drop_duplicates(K)

# ---------------------------------------------------------------- corte anterior (todas las cosechas)
e = pd.read_csv(REPO / "clima_estaciones.csv", sep=";")
e["f"] = pd.to_datetime(e.fc_obsrvcion)
EMA = {k: g.set_index("f").sort_index().prcptcion for k, g in e.groupby("nm_ema")}
c = pd.read_pickle(PK / "rio_factores_sep.pkl").sort_values(["ste", "cosecha"])
c["prev_cos"] = c.groupby("ste").cosecha.shift()
c["prev_corte"] = c.groupby("ste").Corte.shift()


def lluvia_mes(est, f):
    if pd.isna(f) or est not in EMA:
        return np.nan
    s = EMA[est].loc[f - pd.Timedelta(days=14): f + pd.Timedelta(days=15)]
    return s.sum() * 30 / s.notna().sum() if s.notna().sum() >= 20 else np.nan


c["mm_ca"] = [lluvia_mes(es, f) if (pc is not None and not pd.isna(pc) and co - pc == 1) else np.nan
              for es, f, co, pc in zip(c.est, c.prev_cos, c.Corte, c.prev_corte)]
c["ca_hum"] = np.where(c.mm_ca.notna(), (c.mm_ca >= CORTE_MM).astype(float), np.nan)
print("\ncorte anterior en suelo húmedo (≥100 mm en el mes del corte), por año de cosecha:")
print(c[c.anio >= 2018].groupby("anio").ca_hum.agg(["mean", "count"]).round(2).T)

out = c[K + ["mm_ca", "ca_hum"]].merge(lab, on=K, how="left").drop_duplicates(K)
out.to_pickle(PK / "suelo_humedo.pkl")
print(f"\nguardado: {PK / 'suelo_humedo.pkl'} · {len(out)} cosechas")
