# -*- coding: utf-8 -*-
"""Riopaila: ¿cuánto afectó el área que estaba en el plan de renovación 2025 y no se renovó?

Archivo «Areas no renovadas.xlsx» (hoja Area no renovada 2025): 124 suertes presupuestadas para renovar, SI/NO
renovada; lista de suertes renovadas (incluye fuera del plan) y área en proceso (cortada, sin sembrar).
Cosechas: rio_factores_sep.pkl (ZQM 2011-2025 + G&P 2026 ene-sep) + cosechas_recientes.xlsx (octubre).
Lo que habría dado la suerte renovada: curva por número de corte en el MISMO lote (log TCH con efecto fijo de suerte,
año, mes y edad; igual que analisis_cortes_renovacion.py): ciclo renovado = promedio de los cortes 1 a 5 del lote.
Pendientes de 2026: TCH del motor (estimados.json, corrida vigente) de la caña en pie.

Uso: python no_renovadas_2026.py <Areas no renovadas.xlsx> <rio_factores_sep.pkl>
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
sys.path.insert(0, r"C:\Users\Agr349\tch-motor\scripts")
from tchmotor import dataset_gee as dg, produccion as pr, rutas  # noqa: E402
import presupuesto_cosecha as pc  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
XLS, PKL = Path(sys.argv[1]), Path(sys.argv[2])
TOPE = 13

# ---------------------------------------------------------------- el archivo
wb = openpyxl.load_workbook(XLS, read_only=True, data_only=True)
F = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
txt = lambda v: str(v).strip() if v is not None else ""  # noqa: E731
i0 = next(i for i, r in enumerate(F) if txt(r[0]) == "Zona" and txt(r[2]) == "Sect-Sue")
plan = pd.DataFrame([dict(zona=r[0], finca=txt(r[1]), ste=txt(r[2]), area=float(r[3]), renovada=txt(r[4]).upper() == "SI")
                     for r in F[i0 + 1:] if txt(r[2])])
j0 = next(i for i, r in enumerate(F) if txt(r[7]) == "Sect-Sue")
renov = pd.DataFrame([dict(ste=txt(r[7]), hac=txt(r[8]), area=float(r[9])) for r in F[j0 + 1:]
                      if txt(r[7]) and txt(r[7]) != "TOTAL" and r[9] is not None])
proc = pd.DataFrame([dict(ste=txt(r[13]), area=r[14], corte=r[16], siembra=r[17], lucro=r[19]) for r in F[j0 + 1:]
                     if len(r) > 19 and txt(r[13]) and "-" in txt(r[13])])
print(f"Plan de renovación 2025: {len(plan)} suertes · {plan.area.sum():,.1f} ha")
print(f"  renovadas del plan: {plan.renovada.sum()} · {plan.area[plan.renovada].sum():,.1f} ha · "
      f"NO renovadas: {(~plan.renovada).sum()} · {plan.area[~plan.renovada].sum():,.1f} ha")
fuera = renov[~renov.ste.isin(plan.ste)]
print(f"  lista de renovadas: {len(renov)} suertes · {renov.area.sum():,.1f} ha (fuera del plan: {len(fuera)} · {fuera.area.sum():,.1f} ha)")
print(f"  en proceso (cortadas, sin sembrar): {len(proc)} suertes · {pd.to_numeric(proc.area).sum():,.1f} ha · "
      f"días de lucro promedio {pd.to_numeric(proc.lucro).mean():.0f}")
print("  NO renovadas por zona y tipo de finca:", plan[~plan.renovada].groupby(["zona", "finca"]).area.agg(["size", "sum"]).round(1).to_dict("index"))
NO = set(plan.ste[~plan.renovada])
TARDE = NO & set(proc.ste)  # marcadas NO en el plan, pero cortadas en 2025 y sembradas en 2026 (renovación tardía)
print(f"  de las NO renovadas, {len(TARDE)} ({plan.area[plan.ste.isin(TARDE)].sum():,.1f} ha) están en «área en proceso»: se "
      f"renovaron tarde (sembradas en 2026): {sorted(TARDE)}")
NO = NO - TARDE

# ---------------------------------------------------------------- estado hoy (maestro)
ma, _ = pc.leer_maestro("riopaila")
m = pd.DataFrame([dict(ste=s, ncorte=v["ncorte"], var=v["var"], area_m=v["area"], prox=v["prox"], ult=v["ult"]) for s, v in ma.items()])
mn = plan[~plan.renovada & plan.ste.isin(NO)].merge(m, on="ste", how="left")
print(f"\nNO renovadas en el maestro hoy: {mn.ncorte.notna().sum()} de {len(mn)}; corte de la caña en pie: "
      + ", ".join(f"{g}: {n}" for g, n in pd.cut(mn.ncorte, [0, 5, 7, 10, 99], labels=["≤5", "6-7", "8-10", "11+"]).value_counts().sort_index().items())
      + f" · mediana {mn.ncorte.median():.0f}")
print("  variedades:", mn["var"].value_counts().head(6).to_dict())
print("  en RENOVACION en el maestro hoy:", int((mn["var"].str.upper() == "RENOVACION").sum()))

# ---------------------------------------------------------------- curva por corte en el mismo lote
c = pd.read_pickle(PKL)
c["k"] = c.Corte.clip(upper=TOPE).astype(int)
c["e2"] = c.Edad ** 2
mo = smf.wls("y ~ C(k, Treatment(1)) + C(anio) + C(Mes) + Edad + e2 + C(ste)", c, weights=c.Area).fit(
    cov_type="cluster", cov_kwds={"groups": pd.factorize(c.ste)[0]})
b = pd.Series({k: (0.0 if k == 1 else mo.params[f"C(k, Treatment(1))[T.{k}]"]) for k in range(1, TOPE + 1)})
ren = float(b[1:6].mean())
print("\ncurva frente a la plantilla (mismo lote):", {k: f"{100 * (np.exp(v) - 1):+.1f}%" for k, v in b.items()})


def perdida(df, tch, k, ha):
    """t/ha y toneladas que faltan frente al lote renovado (promedio de un ciclo de cortes 1 a 5) y frente a plantilla."""
    kk = df[k].clip(upper=TOPE).astype(int)
    t_ren = df[tch] * np.exp(ren - kk.map(b))
    t_pla = df[tch] * np.exp(0 - kk.map(b))
    return t_ren, t_pla


# ---------------------------------------------------------------- cosechas 2026 de las NO renovadas
cs = c[(c.anio == 2026)][["ste", "Mes", "Corte", "Area", "tch_calc", "rel"]].rename(columns={"tch_calc": "tch"})
cs["fuente"] = "G&P"
maestro_pr, _ = pr.cargar_maestro()
zz = dg.cortes_zqm(dg.leer_zqm())
rec, _ = pr.cosechas_recientes(pr.leer_cosechas_recientes(), maestro_pr, zz)
oc = rec[(rec.planta == "riopaila") & (rec.anio == 2026) & (rec.mes == 10)]
oc = pd.DataFrame({"ste": oc.sec_ste, "Mes": 10, "Corte": oc.corte, "Area": oc.ha, "tch": oc.tch, "rel": np.nan, "fuente": "octubre"})
cs = pd.concat([cs, oc[~oc.ste.isin(cs[cs.Mes >= 9].ste)]], ignore_index=True).dropna(subset=["Corte", "tch", "Area"])
cs["no_renov"] = cs.ste.isin(NO)
cs["t_ren"], cs["t_pla"] = perdida(cs, "tch", "Corte", "Area")
w = lambda g, k: np.average(g[k], weights=g.Area)  # noqa: E731
print("\nCosechas de 2026 (ene-oct): las del plan NO renovadas frente al resto de Riopaila")
for nom, g in (("NO renovadas", cs[cs.no_renov]), ("resto", cs[~cs.no_renov])):
    print(f"  {nom:13s} {len(g):4d} cortes · {g.Area.sum():7,.0f} ha · corte medio {w(g, 'Corte'):4.1f} · TCH {w(g, 'tch'):6.1f}")
g = cs[cs.no_renov]
print(f"  NO renovadas: si estuvieran renovadas daría TCH {w(g, 't_ren'):.1f} (ciclo 1-5) → faltan "
      f"{w(g, 't_ren') - w(g, 'tch'):.1f} t/ha · {((g.t_ren - g.tch) * g.Area).sum():,.0f} t; como plantilla {w(g, 't_pla'):.1f} → "
      f"{((g.t_pla - g.tch) * g.Area).sum():,.0f} t")
print("  por corte:", g.groupby(pd.cut(g.Corte, [0, 5, 7, 10, 99], labels=["≤5", "6-7", "8-10", "11+"]), observed=True).apply(
    lambda x: (len(x), round(x.Area.sum()), round(w(x, "tch"), 1), round(((x.t_ren - x.tch) * x.Area).sum()))).to_dict())

# misma suerte frente a su promedio 2020-25: ¿cayeron más que el resto?
rr = c[c.anio == 2026].dropna(subset=["rel"]).copy()
rr["no_renov"] = rr.ste.isin(NO)
ref = c[c.anio.between(2020, 2025)].dropna(subset=["rel"])
gap = lambda x: 100 * (np.exp(w(x, "rel") - w(ref[ref.Mes.isin(x.Mes.unique())], "rel")) - 1)  # noqa: E731
gn, gr = gap(rr[rr.no_renov]), gap(rr[~rr.no_renov])
print(f"\nCaída 2026 (ene-sep) de cada suerte frente a su propio promedio 2020-25: NO renovadas {gn:+.1f} % · resto {gr:+.1f} %")
sh = rr.Area[rr.no_renov].sum() / rr.Area.sum()
ton26 = (rr.tch_calc * rr.Area).sum()
print(f"  peso de las NO renovadas: {100 * sh:.0f} % del área cosechada ene-sep; si hubieran caído como el resto, la planta "
      f"habría caído {(gn - gr) * sh:+.1f} puntos menos (≈ {abs((gn - gr) / 100 * sh * ton26):,.0f} t)")

# ---------------------------------------------------------------- lo que falta de 2026 y 2027
est = {e["sec_ste"]: e for e in json.load(open(rutas.TABLERO_DATA / "estimados.json", encoding="utf-8")) if e["planta"] == "riopaila"}
pend = mn[mn.ste.isin(est) & ~mn.ste.isin(cs[cs.no_renov].ste) & (mn.ncorte > 1) & (mn["var"].str.upper() != "RENOVACION")].copy()
pend["tch"] = pend.ste.map(lambda s: est[s]["tch_estimado"])
pend["Corte"] = pend.ncorte
pend["Area"] = pend.area_m.fillna(pend.area)
pend["prox_anio"] = pd.to_datetime(pend.prox, errors="coerce").dt.year
pend = pend.dropna(subset=["tch", "Corte"])
pend["t_ren"], pend["t_pla"] = perdida(pend, "tch", "Corte", "Area")
for anio in (2026, 2027):
    x = pend[pend.prox_anio == anio]
    if len(x):
        print(f"\nNO renovadas con próximo corte en {anio} (motor): {len(x)} suertes · {x.Area.sum():,.0f} ha · TCH {w(x, 'tch'):.1f} · "
              f"renovada {w(x, 't_ren'):.1f} → {((x.t_ren - x.tch) * x.Area).sum():,.0f} t")
viejas = mn[(mn.ncorte > 1) & (mn["var"].str.upper() != "RENOVACION")]
print(f"\nNO renovadas que siguen como soca en el maestro: {len(viejas)} suertes · {viejas.area_m.sum():,.0f} ha · corte mediano "
      f"{viejas.ncorte.median():.0f}; las que no están en el maestro: {int(mn.ncorte.isna().sum())}")
print(f"Total NO renovadas en el maestro: {mn.area_m.sum():,.0f} ha; a la pérdida media por hectárea de este año, cada cosecha "
      f"sin renovar cuesta ≈ {(w(g, 't_ren') - w(g, 'tch')) * mn.area_m.sum():,.0f} t")
cs.to_pickle("no_renovadas_cosechas_2026.pkl")
