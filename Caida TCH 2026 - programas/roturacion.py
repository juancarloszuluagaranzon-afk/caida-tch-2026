# -*- coding: utf-8 -*-
"""Riopaila: oportunidad de la roturación (control oficial «CONTROL DE ROTURACION. est 2025») y su efecto en el TCH.

Cada fila del control = un corte (fecha exacta, oct-2023 a ene-2026) con la oportunidad de la 1.ª y 2.ª labor según el
criterio de Riopaila (1.ª: IDEAL ≤15 días, NORMAL 16-30, TARDÍO >30; 2.ª: IDEAL ≤20, NORMAL 21-40, TARDÍO >40), lo
pendiente y la condición del suelo. Se une con la cosecha siguiente de la suerte (ZQM / G&P / cosechas recientes, de 8 a
24 meses después del corte) y se mide el TCH frente al promedio 2020-25 de la misma suerte, con efectos de año y mes de
cosecha, edad y número de corte. Ciclos sin cosechar todavía (cosecha 2026-27): se reporta su oportunidad.

Uso: python roturacion.py <CONTROL DE ROTURACION.xlsm> <rio_factores_sep.pkl>
"""
import sys
import warnings

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import dataset_gee as dg, produccion as pr  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
F = list(openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)["B.D. ROTURACIÓN"].iter_rows(values_only=True))
h = next(i for i, r in enumerate(F) if r and str(r[0]).strip() == "SECTOR-SUERTE")
enc = [str(c).strip() if c is not None else f"c{j}" for j, c in enumerate(F[h])]
d = pd.DataFrame(F[h + 1:], columns=dg._dedup(enc))
d = d[d["SECTOR-SUERTE"].notna()].copy()
d["ste"] = d["SECTOR-SUERTE"].astype(str).str.strip()
d["corte_f"] = pd.to_datetime(d["FECHA DE CORTE"], errors="coerce")
d["area"] = pd.to_numeric(d["AREA NETA"], errors="coerce")
txt = lambda s: s.astype(str).str.strip().str.upper().replace({"NONE": "", "NAN": "", "#N/A": ""})  # noqa: E731
d["op1"] = txt(d["OPORTUNIDAD 1RA LABOR"])
d["op1p"] = txt(d["OPORTUNIDAD PENDIENTES PRIMERA"])
d["op2"] = txt(d["OPORTUNIDAD DE LA LABOR SEGUNDA"])
d["est1"] = txt(d["ESTADO PRIMERA LABORE"]) if "ESTADO PRIMERA LABORE" in d else ""
d["noret"] = txt(d["No se returo"]) if "No se returo" in d else ""
d["suelo1"] = txt(d["CONDICION SUELO PRIMERA"])
# oportunidad de la primera roturación: la realizada; si sigue pendiente, «PENDIENTE»; si no se roturó, «NO SE ROTURÓ»
d["rot1"] = np.where(d.op1.isin(["IDEAL", "NORMAL", "TARDIO"]), d.op1,
                     np.where(d.op1p == "TARDIO", "PENDIENTE (TARDÍO)", np.where(d.noret != "", "NO SE ROTURÓ", "SIN DATO")))
print(f"control: {len(d)} cortes, {d.corte_f.min().date()} a {d.corte_f.max().date()} · {d.area.sum():,.0f} ha")
print("1.ª labor:", d.groupby("rot1").area.sum().round(0).to_dict())
print("2.ª labor:", d.groupby(d.op2.replace("", "SIN 2.ª")).area.sum().round(0).to_dict())
print("suelo en la 1.ª:", d.groupby(d.suelo1.replace("", "SIN DATO")).area.sum().round(0).to_dict())
print("columnas con «retur»:", [k for k in d.columns if "retur" in k.lower() or "rotur" in k.lower()][:12])
print("valores de «No se returo»:", d["noret"].value_counts().head(5).to_dict() if "noret" in d else "-")
print("estado 1.ª labor:", d.groupby(d.est1.replace("", "SIN DATO")).area.sum().round(0).to_dict())
print("1.ª SIN oportunidad, por estado:", d[~d.op1.isin(["IDEAL", "NORMAL", "TARDIO"])].groupby("est1").area.sum().round(0).to_dict())

# cosecha siguiente
c = pd.read_pickle(sys.argv[2])
cos = c[["ste", "cosecha", "anio", "Mes", "Edad", "Corte", "tch_calc", "Area", "rel", "y"]].copy()
mp, _ = pr.cargar_maestro()
rec, _ = pr.cosechas_recientes(pr.leer_cosechas_recientes(), mp, dg.cortes_zqm(dg.leer_zqm()))
rec = rec[(rec.planta == "riopaila") & (rec.mes == 10) & (rec.anio == 2026)]
cos = pd.concat([cos, pd.DataFrame({"ste": rec.sec_ste, "cosecha": pd.to_datetime(rec.harvest), "anio": rec.anio, "Mes": rec.mes,
                                    "Edad": rec.edad, "Corte": rec.corte, "tch_calc": rec.tch, "Area": rec.ha})], ignore_index=True)
base = c[c.anio.between(2020, 2025)].groupby("ste").y.mean()
cos["rel"] = cos.rel.fillna(np.log(cos.tch_calc) - cos.ste.map(base))


def siguiente(r):
    g = cos[(cos.ste == r.ste) & (cos.cosecha > r.corte_f + pd.Timedelta(days=240)) & (cos.cosecha < r.corte_f + pd.Timedelta(days=730))]
    return g.sort_values("cosecha").iloc[0] if len(g) else None


filas = []
for r in d.itertuples():
    s = siguiente(r)
    if s is not None:
        filas.append({**r._asdict(), **{f"c_{k}": v for k, v in s.items()}})
j = pd.DataFrame(filas)
j = j.dropna(subset=["c_rel"])
print(f"\ncortes del control con su cosecha siguiente: {len(j)} ({j.area.sum():,.0f} ha) · cosechas {j.c_anio.min()}-{j.c_anio.max()}")
j["Area"] = j.c_Area
print("TCH relativo por oportunidad de la 1.ª:", j.groupby("rot1").apply(lambda g: (len(g), round(100 * (np.exp(np.average(g.c_rel, weights=g.Area)) - 1), 1))).to_dict())
j["op2g"] = j.op2.replace("", "SIN 2.ª")
for f in ("c_rel ~ C(rot1, Treatment('IDEAL')) + C(c_anio) + C(c_Mes) + c_Edad + c_Corte",
          "c_rel ~ C(rot1, Treatment('IDEAL')) + C(op2g, Treatment('IDEAL')) + C(c_anio) + C(c_Mes) + c_Edad + c_Corte",
          "c_rel ~ C(rot1, Treatment('IDEAL')) + C(suelo1) + C(c_anio) + C(c_Mes) + c_Edad + c_Corte"):
    jj = j[j.suelo1 != ""] if "suelo1" in f else j
    mod = smf.wls(f, jj, weights=jj.Area)
    mo = mod.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(jj.loc[mod.data.row_labels, "ste"])[0]})
    print("  ", f.split("~")[1].split("+ C(c_anio)")[0].strip(), "→",
          {k.split("[T.")[1][:-1] + (" (2.ª)" if "op2g" in k else "") + (" (suelo)" if "suelo1" in k else ""):
           f"{100 * (np.exp(v) - 1):+.1f}% (p={mo.pvalues[k]:.2f})" for k, v in mo.params.items() if "[T." in k and ("rot1" in k or "op2g" in k or "suelo1" in k)})
mod = smf.wls("c_rel ~ C(rot1, Treatment('IDEAL')) + C(c_anio) + C(c_Mes) + c_Edad + c_Corte", j, weights=j.Area)
mo = mod.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(j.loc[mod.data.row_labels, "ste"])[0]})
ef = {k.split("[T.")[1][:-1]: v for k, v in mo.params.items() if "rot1" in k}
pv = {k.split("[T.")[1][:-1]: mo.pvalues[k] for k in mo.params.index if "rot1" in k}
# pérdidas: frente a haberla hecho IDEAL; solo efectos negativos
j["perd_t"] = [max(0.0, (np.exp(-ef.get(o, 0.0)) - 1)) * t * a if ef.get(o, 0.0) < 0 else 0.0 for o, t, a in zip(j.rot1, j.c_tch_calc, j.Area)]
for anio in (2026,):
    q = j[j.c_anio == anio]
    print(f"\n{anio}: cosechas con 1.ª labor no ideal: " + ", ".join(f"{k} {q.Area[q.rot1 == k].sum():,.0f} ha" for k in ("NORMAL", "TARDIO", "PENDIENTE (TARDÍO)", "NO SE ROTURÓ"))
          + f" · pérdida frente a IDEAL {q.perd_t.sum():,.0f} t")
pend = d[~d.index.isin(j.index)] if False else d[~d.set_index(["ste", "corte_f"]).index.isin(j.set_index(["ste", "corte_f"]).index)]
pend = pend[pend.corte_f >= "2025-08-01"]
print(f"\ncortes del control sin cosechar todavía (cortados desde ago-2025, se cosechan fin 2026-2027): {len(pend)} · {pend.area.sum():,.0f} ha · "
      + ", ".join(f"{k} {pend.area[pend.rot1 == k].sum():,.0f} ha" for k in ("IDEAL", "NORMAL", "TARDIO", "PENDIENTE (TARDÍO)", "NO SE ROTURÓ", "SIN DATO")))
pd.to_pickle({"ef": ef, "pv": pv, "j": j, "pend": pend, "d": d}, "roturacion.pkl")
