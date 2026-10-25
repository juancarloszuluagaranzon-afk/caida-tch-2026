# -*- coding: utf-8 -*-
"""Tamaño de la caída 2026 a octubre: cada suerte frente a su propio promedio 2020-25 (log TCH), por planta y mes.
Cortes del ZQM (2011-ago 2026) + cosechas_recientes.xlsx (sep-oct 2026), como la corrida del motor."""
import sys
sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
import numpy as np, pandas as pd
from tchmotor import dataset_gee as dg, produccion as pr
sys.stdout.reconfigure(encoding="utf-8")
c = dg.cortes_zqm(dg.leer_zqm())
maestro, _ = pr.cargar_maestro()
rec, _ = pr.cosechas_recientes(pr.leer_cosechas_recientes(), maestro, c)
c = pd.concat([c, rec], ignore_index=True).drop_duplicates("key")
c = c[(c.ha > 0) & c.tch.between(20, 300) & (c.anio >= 2020)].copy()
c["y"] = np.log(c.tch)
eb = c.anio.between(2020, 2025)
g = c[eb].groupby("sec_ste").y.agg(["sum", "count"])
c = c.join(g, on="sec_ste")
c["rel"] = np.where(eb, (c.y - (c["sum"] - c.y) / (c["count"] - 1)), c.y - c["sum"] / c["count"])
c.loc[eb & (c["count"] <= 1), "rel"] = np.nan
wm = lambda d, k: np.average(d[k].dropna(), weights=d.ha[d[k].notna()]) if d[k].notna().any() else np.nan
for planta in ("riopaila", "castilla"):
    d = c[c.planta == planta]
    print(f"\n==== {planta.upper()} (misma suerte frente a 2020-25; TCH ponderado por área)")
    print("  periodo     cortes      ha   TCH 2026  TCH 2020-25 mismos meses   bruto   misma suerte")
    for lab, meses in [("ene-ago", range(1, 9)), ("ene-oct", range(1, 11)), ("sep", [9]), ("oct", [10]), ("sep-oct", [9, 10])] + \
                      [(f"mes {m:>2}", [m]) for m in range(1, 11)]:
        q, r = d[(d.anio == 2026) & d.mes.isin(meses)], d[d.anio.between(2020, 2025) & d.mes.isin(meses)]
        if not len(q):
            continue
        t26 = (q.tch * q.ha).sum() / q.ha.sum()
        tr = (r.tch * r.ha).sum() / r.ha.sum()
        gap = wm(q, "rel") - wm(r, "rel")
        print(f"  {lab:9s} {len(q):6d} {q.ha.sum():8,.0f} {t26:9.1f} {tr:12.1f} {100 * (t26 / tr - 1):+15.1f} % {100 * (np.exp(gap) - 1):+9.1f} %")
    print("  suertes 2026 sin historia 2020-25:", int(d[(d.anio == 2026)].rel.isna().sum()))
