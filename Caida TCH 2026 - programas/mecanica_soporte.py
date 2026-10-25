# -*- coding: utf-8 -*-
"""Riopaila: soporte de la cosecha mecánica como causa de la caída del TCH 2026.

Preguntas:
  1. ¿Cuánto ha subido la cosecha mecánica? (% del área cosechada por año, 2011-2026)
  2. ¿La soca rinde menos cuando el corte ANTERIOR fue mecánico (cepa aporreada), sobre todo si fue la primera vez?
     Se separa del efecto del corte actual mecánico (la caña que la máquina deja en el campo).
     Mismo modelo de caida_integrada_rio.py (efectos fijos de suerte, año y mes; edad, soca, variedad, incendio,
     mecánica del corte actual por año, lluvia 0-3 m, calor) + el tipo del corte anterior.
  3. ¿El satélite lo ve? NDVI y NDMI de la soca en los meses 2-5 de edad (rebrote y población), frente a la misma
     suerte en sus otros ciclos, según cómo fue el corte que la dejó.
  4. Ejemplos: suertes cosechadas en 2026 cuyo corte anterior (2025) fue su primera cosecha mecánica.

Fuentes: rio_integrado_dataset.pkl (caida_integrada_rio.py) y la tabla mensual de Sentinel-2 por suerte
(tch-motor/data/gee/mensual_riopaila.csv.gz, Earth Engine).

Uso: <tch-motor>\\.venv-gee\\Scripts\\python.exe mecanica_soporte.py <carpeta con los .pkl> <mensual_riopaila.csv.gz> <salida>
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
PK, SAT, SAL = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
SAL.mkdir(parents=True, exist_ok=True)
wm = lambda g, k: np.average(g[k], weights=g.Area) if len(g) else np.nan  # noqa: E731
pct = lambda b: 100 * (np.exp(b) - 1)  # noqa: E731

c = pd.read_pickle(PK / "rio_integrado_dataset.pkl").sort_values(["ste", "cosecha"]).reset_index(drop=True)

# ---------------------------------------------------------------- 1. % mecánica por año
a = c.groupby("anio").apply(lambda g: pd.Series({
    "cosechas": len(g), "ha": g.Area.sum(), "ha_mecanica": (g.Area * g.mec).sum(),
    "pct_area_mecanica": 100 * (g.Area * g.mec).sum() / g.Area.sum(),
    "tch_manual": wm(g[g.mec == 0], "tch_calc"), "tch_mecanica": wm(g[g.mec == 1], "tch_calc")})).reset_index()
print("1. Cosecha mecánica por año (Riopaila; 2026 = ene-sep)")
print(a.round(1).to_string(index=False))

# ---------------------------------------------------------------- 2. corte anterior
g = c.groupby("ste")
c["pc"], c["prev_mec"], c["prev_anio"], c["prev_tch"] = g.Corte.shift(), g.mec.shift(), g.anio.shift(), g.tch_calc.shift()
c["cont"] = (c.Corte >= 2) & (c.Corte - c.pc == 1)  # el corte anterior es el que dejó esta soca
# mecánicas previas de la suerte (desde 2011; antes de 2012 no había cosecha mecánica en la base)
c["n_mec_antes"] = g.mec.cumsum() - c.mec
c["n_mec_antes_prev"] = c.groupby("ste").n_mec_antes.shift()
c["ant"] = np.select(
    [~c.cont, c.prev_mec.eq(0), c.prev_mec.eq(1) & c.n_mec_antes_prev.eq(0), c.prev_mec.eq(1)],
    ["plantilla o sin dato", "manual", "mecánica, primera vez", "mecánica, repetida"], "plantilla o sin dato")
c["prev_mec1"] = (c.ant == "mecánica, primera vez").astype(int)
c["prev_mecR"] = (c.ant == "mecánica, repetida").astype(int)
c["prev_na"] = (c.ant == "plantilla o sin dato").astype(int)
print("\nTipo del corte anterior por año de cosecha (n)")
print(pd.crosstab(c.anio, c.ant).to_string())

ED = "C(edad_b, Treatment('12-13'))"
MEC = " + ".join(f"mec_{y}" for y in range(2011, 2027))
NUEVAS = ["def100", "def_na", "rot_tard", "rot_na", "mal_extra30", "mal_na", "fert_120", "fert_na", "lab_na", "no_renov"]
BASE = f"y ~ C(ste) + C(anio) + C(Mes) + {ED} + C(soca_b) + C(var) + inc + Corte + {MEC} + llu03_100 + d32 + " + " + ".join(NUEVAS)
est = c.dropna(subset=["llu03", "d32"]).copy()


def fit(f, d):
    mo = smf.wls(f, data=d, weights=d.Area)
    return mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.loc[mo.data.row_labels, "ste"])[0]})


m0 = fit(BASE, est)
m1 = fit(BASE + " + prev_mec1 + prev_mecR + prev_na", est)
# ¿cambió con los años? corte anterior mecánico por época
est["prev_mec1_rec"] = est.prev_mec1 * (est.anio >= 2024)
est["prev_mecR_rec"] = est.prev_mecR * (est.anio >= 2024)
m2 = fit(BASE + " + prev_mec1 + prev_mecR + prev_mec1_rec + prev_mecR_rec + prev_na", est)
rows = []
for nom, mo in (("sin corte anterior", m0), ("con corte anterior", m1), ("con corte anterior por época", m2)):
    for k in ["mec_2024", "mec_2025", "mec_2026", "prev_mec1", "prev_mecR", "prev_mec1_rec", "prev_mecR_rec"]:
        if k in mo.params:
            rows.append({"modelo": nom, "termino": k, "efecto_pct": pct(mo.params[k]), "p": mo.pvalues[k],
                         "ic_bajo": pct(mo.conf_int().loc[k, 0]), "ic_alto": pct(mo.conf_int().loc[k, 1])})
ef = pd.DataFrame(rows)
print(f"\n2. Modelo (n={int(m1.nobs)}, cosechas {est.anio.min()}-{est.anio.max()}); efecto en % sobre el TCH")
print(ef.round(3).to_string(index=False))

# aportes 2026 frente a 2020-25 (ene-sep) del corte anterior, en t/ha
q = c[(c.anio == 2026)]
ref = c[c.anio.between(2020, 2025) & c.Mes.between(1, 9)]
P0, P1 = m0.params, m1.params
L26 = wm(q, "tch_calc")
apo = lambda P, ks: sum(P[k] * (wm(q, k) - wm(ref, k)) for k in ks)  # noqa: E731
mec_act = lambda P: P["mec_2026"] * wm(q, "mec_2026") - sum(P[f"mec_{y}"] * wm(ref, f"mec_{y}") for y in range(2020, 2026))  # noqa: E731
print("\nAporte a la caída 2026 (log; × TCH ≈ t/ha)")
print(f"  modelo actual:   corte actual mecánico {mec_act(P0):+.4f} ({mec_act(P0) * L26:+.2f} t/ha)")
print(f"  con anterior:    corte actual mecánico {mec_act(P1):+.4f} ({mec_act(P1) * L26:+.2f} t/ha); "
      f"corte anterior mecánico {apo(P1, ['prev_mec1', 'prev_mecR']):+.4f} ({apo(P1, ['prev_mec1', 'prev_mecR']) * L26:+.2f} t/ha)")
for k in ["prev_mec1", "prev_mecR", "prev_na", "mec"]:
    print(f"    % área {k}: 2026 {100 * wm(q, k):.1f} · 2020-25 {100 * wm(ref, k):.1f}")

# ---------------------------------------------------------------- 2b. cuadro simple 2026: cada suerte frente a su historia
hist = c[c.anio.between(2015, 2025)].groupby("ste").apply(lambda x: wm(x, "tch_calc")).rename("tch_hist")
q = q.join(hist, on="ste")
q["dif"] = q.tch_calc - q.tch_hist
tab = q.dropna(subset=["tch_hist"]).groupby(["ant", "mec"]).apply(lambda x: pd.Series({
    "cosechas": len(x), "ha": x.Area.sum(), "tch_2026": wm(x, "tch_calc"), "tch_historia": wm(x, "tch_hist"),
    "cambio_pct": 100 * (wm(x, "tch_calc") / wm(x, "tch_hist") - 1)})).reset_index()
tab["mec"] = tab.mec.map({0: "manual", 1: "mecánica"})
tab = tab.rename(columns={"ant": "corte_anterior", "mec": "corte_2026"})
print("\n2b. Cosechas 2026 frente a su propia historia 2015-25, según el corte anterior y el actual")
print(tab.round(1).to_string(index=False))

# ---------------------------------------------------------------- 3. satélite: rebrote de la soca
s = pd.read_csv(SAT)
s["f"] = pd.to_datetime(dict(year=s.anio, month=s.mes, day=15))
s = s.rename(columns={"sec_ste": "ste"})
S = {k: v.set_index("f") for k, v in s.groupby("ste")}
cur = []
for r in c[c.cosecha >= "2019-06-01"].itertuples():
    v = S.get(r.ste)
    if v is None:
        continue
    for e in range(0, 15):
        f = (r.ini + pd.DateOffset(months=e)).to_period("M").to_timestamp() + pd.Timedelta(days=14)
        if f in v.index and f <= r.cosecha:
            x = v.loc[f]
            cur.append({"ste": r.ste, "anio": r.anio, "Mes": r.Mes, "Corte": r.Corte, "edad_m": e, "f": f,
                        "NDVI": x.NDVI, "NDMI": x.NDMI, "despejado": x.despejado, "ant": r.ant, "mec": r.mec})
cur = pd.DataFrame(cur)
cur = cur[cur.despejado >= 0.6].dropna(subset=["NDVI"])
cur.to_csv(SAL / "curvas_satelite_ciclos.csv", index=False)
# rebrote: promedio de los meses 2-5 de edad; modelo con efectos fijos de suerte y del mes calendario observado
rb = cur[cur.edad_m.between(2, 5)].groupby(["ste", "anio", "Mes", "Corte", "ant", "mec"]).agg(
    NDVI=("NDVI", "mean"), NDMI=("NDMI", "mean"), n=("NDVI", "size"), f=("f", "mean")).reset_index()
rb = rb[rb.n >= 2]
rb["ym"] = rb.f.dt.to_period("M").astype(str)
sat = []
for ind in ("NDVI", "NDMI"):
    ms = smf.ols(f"{ind} ~ C(ste) + C(ym) + C(ant, Treatment('manual'))", data=rb).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(rb.ste)[0]})
    for k in ms.params.index:
        if k.startswith("C(ant"):
            sat.append({"indice": ind, "corte_anterior": k.split("[T.")[1][:-1], "dif_vs_manual": ms.params[k],
                        "p": ms.pvalues[k], "media_manual": rb.loc[rb.ant == "manual", ind].mean()})
sat = pd.DataFrame(sat)
print(f"\n3. Satélite: índice promedio de los meses 2-5 de edad (n={len(rb)} ciclos con ≥2 meses despejados)")
print(sat.round(4).to_string(index=False))
print(rb.groupby("ant")[["NDVI", "NDMI"]].agg(["mean", "count"]).round(3))

# ---------------------------------------------------------------- 4. ejemplos
e = q[(q.ant == "mecánica, primera vez")].dropna(subset=["tch_hist"]).copy()
e["pct"] = 100 * (e.tch_calc / e.tch_hist - 1)
ncic = cur.groupby("ste").apply(lambda x: x[["anio", "Mes"]].drop_duplicates().shape[0]).rename("ciclos_sat")
e = e.join(ncic, on="ste").sort_values("pct")
print("\n4. Cosechas 2026 cuya cosecha anterior fue la primera mecánica de la suerte")
print(e[["ste", "Mes", "Corte", "Area", "var", "mec", "prev_anio", "prev_tch", "tch_calc", "tch_hist", "pct", "ciclos_sat"]]
      .round(1).to_string(index=False))

# historial de cada suerte de 2026 (para las fichas)
hh = c[c.ste.isin(q.ste)][["ste", "anio", "Mes", "Corte", "Edad", "Area", "var", "Tipo Cosecha", "mec", "tch_calc", "ant"]]
a.to_csv(SAL / "mecanica_por_anio.csv", index=False)
ef.to_csv(SAL / "efecto_corte_anterior.csv", index=False)
tab.to_csv(SAL / "cosechas_2026_por_corte_anterior.csv", index=False)
sat.to_csv(SAL / "satelite_rebrote.csv", index=False)
e.to_csv(SAL / "ejemplos_primera_mecanica.csv", index=False)
hh.to_csv(SAL / "historial_suertes_2026.csv", index=False)
rb.to_csv(SAL / "rebrote_ciclos.csv", index=False)
