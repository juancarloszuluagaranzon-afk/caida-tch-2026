# -*- coding: utf-8 -*-
"""Riopaila: oportunidad corte a siembra (efecto en el TCH de la plantilla) y lucro cesante (días sin caña).

Plantío vigente del maestro: fecha de siembra; corte anterior = última cosecha de la suerte antes de esa siembra
(ZQM / G&P, día 15 del mes; si está en «Areas no renovadas» se usa su fecha de corte exacta). Días sin caña = siembra − corte.
  · Efecto en la plantilla: TCH de las plantillas cosechadas 2019-2026 frente a los días sin caña, con efectos de año,
    mes, edad y variedad (la plantilla no tiene historia propia: se compara contra las demás plantillas del año).
  · Lucro cesante = área × meses sin caña × TCHM de Riopaila (t/ha por mes de 2024-25): crecimiento que no ocurrió.
    2026: renovaciones sembradas en 2026 (los días sin caña acumulados hasta la siembra).
    2027: suertes cortadas que siguen sin sembrar (RENOVACION en el maestro), días acumulados hasta hoy.

Uso: python siembra_lucro.py <rio_factores_sep.pkl> <Areas no renovadas.xlsx>
"""
import sys
import warnings
from datetime import date

import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
sys.path.insert(0, r"C:\Users\Agr349\tch-motor\scripts")
import presupuesto_cosecha as pc  # noqa: E402
from tchmotor import dataset_gee as dg, produccion as pr  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
c = pd.read_pickle(sys.argv[1])
HOY = pd.Timestamp(date.today())
tchm = float(c[c.anio.between(2024, 2025)]["TC-Total"].sum() / (c[c.anio.between(2024, 2025)].Area * c[c.anio.between(2024, 2025)].Edad).sum())
print(f"TCHM Riopaila 2024-25: {tchm:.2f} t/ha por mes")

# cortes con fecha: ZQM/G&P (día 15) + cosechas recientes (fecha real) + fechas exactas del archivo de no renovadas
cos = c[["ste", "cosecha", "Corte", "tch_calc", "Area", "anio", "Mes", "Edad", "Variedad Principal"]].copy()
mp, _ = pr.cargar_maestro()
rec, _ = pr.cosechas_recientes(pr.leer_cosechas_recientes(), mp, dg.cortes_zqm(dg.leer_zqm()))
rec = rec[rec.planta == "riopaila"]
cos = pd.concat([cos, pd.DataFrame({"ste": rec.sec_ste, "cosecha": pd.to_datetime(rec.harvest), "Corte": rec.corte,
                                    "tch_calc": rec.tch, "Area": rec.ha, "anio": rec.anio, "Mes": rec.mes})], ignore_index=True)
F = [list(r) for r in openpyxl.load_workbook(sys.argv[2], read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True)]
exacta = {str(r[13]).strip(): pd.Timestamp(r[16]) for r in F if len(r) > 19 and r[13] and "-" in str(r[13]) and hasattr(r[16], "year")}

ma, _ = pc.leer_maestro("riopaila")
m = pd.DataFrame([dict(ste=s, siembra=v["siembra"], ult=v["ult"], var=v["var"], ncorte=v["ncorte"], area=v["area"]) for s, v in ma.items()])
m["siembra"] = pd.to_datetime(m.siembra)
m["ult"] = pd.to_datetime(m.ult)


def corte_previo(ste, siembra):
    if ste in exacta and exacta[ste] < siembra:
        return exacta[ste]
    g = cos[(cos.ste == ste) & (cos.cosecha < siembra - pd.Timedelta(days=10))]
    return g.cosecha.max() if len(g) else pd.NaT


m["corte_prev"] = [corte_previo(s, f) if pd.notna(f) else pd.NaT for s, f in zip(m.ste, m.siembra)]
m["dias_sin_cana"] = (m.siembra - m.corte_prev).dt.days
ok = m[m.dias_sin_cana.between(0, 900)]
print(f"\nplantíos del maestro con siembra y corte anterior: {len(ok)} de {len(m)} · días sin caña mediana {ok.dias_sin_cana.median():.0f}")
print("por año de siembra (suertes, ha, mediana de días, % > 90 días):")
print(ok.groupby(ok.siembra.dt.year).apply(lambda g: (len(g), round(g.area.sum()), round(g.dias_sin_cana.median()),
                                                      round(100 * (g.dias_sin_cana > 90).mean()))).tail(8).to_dict())

# ---------------------------------------------------------------- efecto en el TCH de la plantilla
pl = cos[(cos.Corte == 1)].merge(m[["ste", "siembra", "dias_sin_cana", "corte_prev"]], on="ste")
pl = pl[(pl.cosecha > pl.siembra) & ((pl.cosecha - pl.siembra).dt.days.between(270, 760)) & pl.dias_sin_cana.between(0, 900)].copy()
pl = pl.dropna(subset=["tch_calc", "Area"])
pl["y"] = np.log(pl.tch_calc)
pl["edad_pl"] = (pl.cosecha - pl.siembra).dt.days / 30.44
pl["e2"] = pl.edad_pl ** 2
pl["sin_g"] = pd.cut(pl.dias_sin_cana, [-1, 60, 120, 180, 900], labels=["≤60", "61-120", "121-180", ">180"]).astype(str)
pl["sin100"] = pl.dias_sin_cana / 100
top = pl["Variedad Principal"].fillna("?").value_counts()
pl["var"] = pl["Variedad Principal"].fillna("?").where(pl["Variedad Principal"].fillna("?").map(top) >= 8, "otra")
print(f"\nplantillas cosechadas 2019-2026 con siembra y corte anterior conocidos: {len(pl)} ({pl.Area.sum():,.0f} ha)")
print("  por grupo de días sin caña:", pl.groupby("sin_g").apply(lambda g: (len(g), round(np.average(g.tch_calc, weights=g.Area), 1))).to_dict())
for f in ("y ~ sin100 + C(anio) + C(Mes) + edad_pl + e2 + C(var)", "y ~ C(sin_g, Treatment('≤60')) + C(anio) + C(Mes) + edad_pl + e2 + C(var)"):
    mo = smf.wls(f, pl, weights=pl.Area).fit(cov_type="HC1")
    print("  ", {k.replace("C(sin_g, Treatment('≤60'))", "días"): f"{100 * (np.exp(v) - 1):+.1f}% (p={mo.pvalues[k]:.2f})"
               for k, v in mo.params.items() if "sin" in k})
b_dia = smf.wls("y ~ sin100 + C(anio) + C(Mes) + edad_pl + e2 + C(var)", pl, weights=pl.Area).fit(cov_type="HC1")
efecto100, p100 = b_dia.params["sin100"], b_dia.pvalues["sin100"]

# plantillas de 2026 y de 2027
nivel = float(np.average(pl[pl.anio.between(2024, 2025)].tch_calc, weights=pl[pl.anio.between(2024, 2025)].Area))
for anio, grupo in ((2026, pl[pl.anio == 2026]),):
    exceso = (grupo.dias_sin_cana - 60).clip(lower=0) / 100
    perd = (grupo.tch_calc * (np.exp(-efecto100 * exceso) - 1) * grupo.Area).sum()
    print(f"\n{anio}: {len(grupo)} plantillas · {grupo.Area.sum():,.0f} ha · días sin caña mediana {grupo.dias_sin_cana.median():.0f}; "
          f"pérdida por los días de más de 60 (efecto {100 * (np.exp(efecto100) - 1):+.1f}% por 100 días, p={p100:.2f}): {perd:,.0f} t")
fut = m[(m.siembra >= "2025-10-01") & (m.siembra <= HOY) & m.dias_sin_cana.between(0, 900)]
exceso = (fut.dias_sin_cana - 60).clip(lower=0) / 100
perd27 = (nivel * (1 - np.exp(efecto100 * exceso)) * fut.area).sum()
print(f"2027: {len(fut)} plantillas sembradas desde oct-2025 · {fut.area.sum():,.0f} ha · días sin caña mediana {fut.dias_sin_cana.median():.0f}; "
      f"pérdida esperada {perd27:,.0f} t (a TCH plantilla {nivel:.0f})")

# ---------------------------------------------------------------- lucro cesante
s26 = m[(m.siembra.dt.year == 2026) & m.dias_sin_cana.between(0, 900)].copy()
s26["meses"] = s26.dias_sin_cana / 30.44
s26["t"] = s26.area * s26.meses * tchm
s26["t60"] = s26.area * ((s26.dias_sin_cana - 60).clip(lower=0) / 30.44) * tchm
print(f"\nLucro cesante 2026 (renovaciones sembradas en 2026): {len(s26)} suertes · {s26.area.sum():,.1f} ha · "
      f"días sin caña promedio {np.average(s26.dias_sin_cana, weights=s26.area):.0f} · {s26.t.sum():,.0f} t "
      f"({s26.t60.sum():,.0f} t por encima de 60 días)")
print(s26.sort_values("dias_sin_cana", ascending=False)[["ste", "area", "corte_prev", "siembra", "dias_sin_cana"]].head(25).to_string(index=False))
ren = m[m["var"].str.upper().eq("RENOVACION")].copy()
ren["corte_prev"] = [exacta.get(s) or (cos[cos.ste == s].cosecha.max() if (cos.ste == s).any() else pd.NaT) for s in ren.ste]
ren["corte_prev"] = ren.corte_prev.fillna(ren.ult)
ya = ren.siembra.notna() & (ren.siembra > pd.to_datetime(ren.corte_prev))  # el maestro dice RENOVACION pero ya tiene siembra
print(f"\nRENOVACION en el maestro con siembra posterior al corte (ya sembradas, se excluyen del lucro 2027): {sorted(ren.ste[ya])}")
ren = ren[~ya].copy()
ren["dias"] = (HOY - pd.to_datetime(ren.corte_prev)).dt.days
ren["t"] = ren.area * ren.dias / 30.44 * tchm
ren["t60"] = ren.area * (ren.dias - 60).clip(lower=0) / 30.44 * tchm
print(f"\nLucro cesante 2027 (cortadas y sin sembrar hoy, RENOVACION en el maestro): {len(ren)} suertes · {ren.area.sum():,.1f} ha · "
      f"días sin caña hasta hoy promedio {np.average(ren.dias.fillna(0), weights=ren.area):.0f} · {ren.t.sum():,.0f} t "
      f"({ren.t60.sum():,.0f} t por encima de 60 días)")
print(ren[["ste", "area", "corte_prev", "dias"]].to_string(index=False))
pd.to_pickle({"tchm": tchm, "efecto100": efecto100, "p100": p100, "s26": s26, "ren": ren, "fut": fut, "pl": pl}, "siembra_lucro.pkl")
