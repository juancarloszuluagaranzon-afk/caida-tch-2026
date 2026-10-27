# -*- coding: utf-8 -*-
r"""Curva satelital de cada cosecha 2026 por edad frente a sus propios ciclos anteriores, cruzada con la falta de agua por edad.

  · Curva: NDRE y NDMI mensual de Sentinel-2 por suerte (Earth Engine, mensual_riopaila.csv.gz; meses con más de la mitad
    despejada). NDRE = (B8 − B5)/(B8 + B5): usa el borde rojo y se satura menos que el NDVI con la caña cerrada; se eligió (27-oct)
    porque en la prueba 4 le gana al NDVI en cada año 2022-25 y en cada edad (3-5, 5-7, 7-10 meses), antes de mirar 2026.
    La prueba 5 repite la 4 con NDVI, NDRE, EVI, GNDVI, WDRVI (del NDVI del mes, α 0,1) y NDMI en la misma muestra (hoja del Excel).
    Mes de edad k = el k-ésimo mes calendario después del mes del corte anterior, hasta el mes antes de la cosecha.
    Normal propia = promedio de los ciclos de la misma suerte cosechados en 2020-2025 a la misma edad (al menos 2 ciclos).
  · Falta de agua del mes = máx(0,8 × evaporación − lluvia, 0) en la EMA de la suerte (clima mensual de Cenicaña, la misma
    regla de balance_riego.py), sumada por ventana de edad: 0-3, 3-5, 5-7, 7-10 meses y del 10 a la cosecha.
  · Pruebas, cada suerte frente a sí misma:
      1) TCH: regresión del log TCH 2011-2026 como el modelo de la caída (suerte, año, mes, edad, etapa de la soca, variedad,
         incendio, corte, cosecha mecanizada, calor) con la falta de las cinco ventanas juntas.
      2) Satélite: índice promedio de la ventana ~ falta de la ventana, ciclos 2019-2026 (suerte, año y mes de inicio fijos,
         corte anterior mecanizado, etapa de la soca).
      3) Suerte por suerte en 2026: caída % de TCH frente a su historia ~ brecha de NDRE de cada ventana.
      4) Años 2022-2026 y 2022-25 → 2026 sin ver 2026: ¿la brecha a los 5-7 meses anticipa la caída?
      5) La prueba 4 con cada índice y cada ventana de edad (comparación).
  · Opcional: la hoja DEFICIT de «Riegos ciclo.xlsx» (regla de pérdida por edad al empezar el déficit) se compara solo en el Excel.
Solo describe y respalda la causa calor y sequía; no entra al modelo de la caída.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe satelite_ciclo.py <datos intermedios> <Clima_Cenicana_...xlsx> <repo Precipitacion-riopaila>
       <mensual_riopaila.csv.gz> <carpeta web> <salida.xlsx> [<Riegos ciclo.xlsx>]
Escribe <carpeta web>/data/satciclo.json (pestaña «Satélite del ciclo» y ficha de cada suerte). Lee data/suertes.json: va después de informe_datos.py.
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
PK, CLIMA, REPO, SAT, WEB, OUT = (Path(a) for a in sys.argv[1:7])
XLS = Path(sys.argv[7]) if len(sys.argv) > 7 else None
ETC = 0.8
EDADES = list(range(1, 13))
CORTES, VENT = [0, 3, 5, 7, 10, 24], ["0-3", "3-5", "5-7", "7-10", "10-cosecha"]
PRI = "NDRE"                                            # índice principal de la curva (antes NDVI)
IND = [PRI, "NDMI"]
COMP = ["NDVI", "NDRE", "EVI", "GNDVI", "WDRVI", "NDMI"]  # prueba 5
WA = 0.1                                                # α del WDRVI
r1 = lambda v, n=1: None if v is None or pd.isna(v) else round(float(v), n)  # noqa: E731
wm = lambda g, c, p="Area": float(np.average(g[c].dropna(), weights=g.loc[g[c].notna(), p])) if g[c].notna().any() else np.nan  # noqa: E731

# ---------------------------------------------------------------- satélite, clima y estación de cada suerte
s = pd.read_csv(SAT)
s = s[s.despejado.fillna(0) > 0.5]
s["WDRVI"] = ((WA + 1) * s.NDVI + (WA - 1)) / ((WA - 1) * s.NDVI + (WA + 1))   # mismo resultado que con las bandas, pero sobre el NDVI del mes
s["f"] = pd.PeriodIndex.from_fields(year=s.anio, month=s.mes, freq="M")
SI = s.set_index(["sec_ste", "f"])[COMP]
m = pd.read_excel(CLIMA, sheet_name="Mensual")
m = m[m["Estación"].isin(["La Paila", "Bugalagrande"])][["Estación", "Fecha", "Precipitación (mm)", "Evaporación (mm)"]]
m.columns = ["est", "f", "p", "e"]
m["f"] = pd.to_datetime(m.f).dt.to_period("M")
m["falta"] = (ETC * m.e - m.p).clip(lower=0)
FA = m.set_index(["est", "f"]).falta
e = pd.read_csv(REPO / "estaciones_suertes.csv", sep=";", skiprows=1, encoding="latin-1").iloc[:, [1, 2]].dropna()
e.columns = ["ste", "est"]
EST = e.assign(ste=e.ste.astype(str).str.strip(), est=e.est.astype(str).str.strip()).drop_duplicates("ste").set_index("ste").est

d = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
d = d[(d.anio >= 2011) & d.ini.notna()].copy()
d["estB"] = d.ste.map(EST).fillna(d.est)
d["mi"] = d.ini.dt.month
ref = d[d.anio.between(2020, 2025) & d.Mes.between(1, 9)]
TN = float(np.average(ref.tch_calc, weights=ref.Area))

# cada cosecha, mes a mes de edad: falta de agua y (desde 2019) índices
filas = []
for x in d.itertuples():
    p0, pc = x.ini.to_period("M"), x.cosecha.to_period("M")
    for k in range(0, 25):      # k = 0 (mes del corte) solo para la definición alterna de las ventanas
        f = p0 + k
        if f >= pc:
            break
        r = {"i": x.Index, "k": k, "falta": FA.get((x.estB, f), np.nan)}
        if (x.ste, f) in SI.index:
            r.update(SI.loc[(x.ste, f)].to_dict())
        filas.append(r)
L = pd.DataFrame(filas).merge(d[["ste", "anio", "Mes", "Area"]], left_on="i", right_index=True)
for c in COMP:
    if c not in L:
        L[c] = np.nan
L["v"] = pd.cut(L.k, CORTES, labels=VENT)
print(f"cosechas 2011-2026: {L.i.nunique()} · con satélite (ciclo desde 2019): {L[L[PRI].notna()].i.nunique()}")

# ---------------------------------------------------------------- 1) TCH: cuánto resta la falta de agua según la edad (2011-2026)
FV = L.groupby(["i", "v"], observed=True).falta.agg(lambda z: z.sum() / 100 if z.notna().all() else np.nan).unstack()
FV.columns = ["f_" + c.replace("-", "_") for c in FV.columns]
D = d.join(FV).dropna(subset=list(FV.columns))
FX = " + ".join(FV.columns)
mo = smf.wls("y ~ C(ste) + C(anio) + C(Mes) + C(edad_b) + C(soca_b) + C(var) + inc + Corte + mec + d32 + " + FX, data=D, weights=D.Area)
ft = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(D.loc[mo.data.row_labels, "ste"])[0]})
n26 = D[(D.anio == 2026) & D.Mes.between(1, 9)]
nor = D[D.anio.between(2020, 2025) & D.Mes.between(1, 9)]
ventanas = []
for v, c in zip(VENT, FV.columns):
    pct = 100 * (np.exp(ft.params[c]) - 1)
    fn, f6 = 100 * wm(nor, c), 100 * wm(n26, c)
    ventanas.append({"v": v, "tch_pct": r1(pct, 2), "tch": r1(pct / 100 * TN, 2), "tch_p": r1(ft.pvalues[c], 3),
                     "falta_normal": r1(fn, 0), "falta_2026": r1(f6, 0), "aporte": r1(pct / 100 * TN * (f6 - fn) / 100, 2)})
print(f"1) TCH por 100 mm de falta (n {int(ft.nobs)}):", [(x["v"], x["tch"], x["tch_p"]) for x in ventanas])
# sensibilidad: la misma prueba contando el mes del corte como edad 0 (ventanas un mes antes)
L["v2"] = pd.cut(L.k, CORTES, labels=VENT, right=False)
F2 = L.groupby(["i", "v2"], observed=True).falta.agg(lambda z: z.sum() / 100 if z.notna().all() else np.nan).unstack()
F2.columns = ["f_" + c.replace("-", "_") for c in F2.columns]
D2 = d.join(F2).dropna(subset=list(F2.columns))
mo = smf.wls("y ~ C(ste) + C(anio) + C(Mes) + C(edad_b) + C(soca_b) + C(var) + inc + Corte + mec + d32 + " + FX, data=D2, weights=D2.Area)
f2 = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(D2.loc[mo.data.row_labels, "ste"])[0]})
for x, c in zip(ventanas, FV.columns):
    x["tch_alt"], x["tch_alt_p"] = r1((np.exp(f2.params[c]) - 1) * TN, 2), r1(f2.pvalues[c], 3)
print("   contando el mes del corte:", [(x["v"], x["tch_alt"], x["tch_alt_p"]) for x in ventanas])

# ---------------------------------------------------------------- 2) satélite: ¿la falta de agua de la ventana se ve en el índice? (2019-2026)
P = L[L[PRI].notna() | L.NDMI.notna()].groupby(["i", "v"], observed=True).agg(N=(PRI, "mean"), M=("NDMI", "mean"), F=("falta", "sum")).reset_index()
P = P.merge(d[["ste", "anio", "mi", "Area", "pm_new", "pm_seg", "soca_b"]], left_on="i", right_index=True)
P["F100"] = P.F / 100
for x in ventanas:
    for ind, et in (("N", "ndre"), ("M", "ndmi")):
        q = P[P.v == x["v"]].dropna(subset=[ind, "F100"])
        mo = smf.wls(f"{ind} ~ F100 + C(ste) + C(anio) + C(mi) + pm_new + pm_seg + C(soca_b)", data=q, weights=q.Area)
        f = mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(q.loc[mo.data.row_labels, "ste"])[0]})
        x[et], x[et + "_p"], x[et + "_n"] = r1(f.params["F100"], 4), r1(f.pvalues["F100"], 3), int(f.nobs)
        if ind == "N":   # cuánto más bajo queda el NDRE de esa edad después del primer corte mecanizado (2019-2026)
            x["mec_ndre"], x["mec_p"] = r1(f.params["pm_new"], 4), r1(f.pvalues["pm_new"], 3)
print("2) índice por 100 mm de falta:", [(x["v"], x["ndre"], x["ndre_p"], x["ndmi"], x["ndmi_p"]) for x in ventanas])

# ---------------------------------------------------------------- curva 2026 frente a la normal propia
c26 = d[(d.anio == 2026) & d.Mes.between(1, 9)]
hist = L[L.anio.between(2020, 2025)]
prev = hist.groupby(["ste", "k"])[IND + ["NDVI", "falta"]].mean()
nprev = hist[hist[PRI].notna()].groupby("ste").i.nunique()
A = L[L.i.isin(c26.index) & (L.ste.map(nprev).fillna(0) >= 2)].join(prev, on=["ste", "k"], rsuffix="_n")
for c in IND + ["NDVI", "falta"]:
    A["g_" + c] = A[c] - A[c + "_n"]
A = A.merge(d[["pm_new", "pm_seg"]], left_on="i", right_index=True)
A["ant"] = np.where(A.pm_seg == 1, "seg", np.where(A.pm_new == 1, "new", "man"))
E12 = A[A.k.isin(EDADES)]
curva = []
for k, g in E12.groupby("k"):
    gg = g.dropna(subset=["g_" + PRI])
    curva.append({"k": int(k), "n": int(len(gg)), "ndre": r1(wm(g, PRI), 3), "ndre_n": r1(wm(g, PRI + "_n"), 3), "dif": r1(wm(g, "g_" + PRI), 3),
                  "bajo": r1(100 * np.average(gg["g_" + PRI] < 0, weights=gg.Area), 0),
                  "ndvi": r1(wm(g, "NDVI"), 3), "ndvi_n": r1(wm(g, "NDVI_n"), 3), "dif_ndvi": r1(wm(g, "g_NDVI"), 3), "ndmi": r1(wm(g, "NDMI"), 3), "ndmi_n": r1(wm(g, "NDMI_n"), 3),
                  "difm": r1(wm(g, "g_NDMI"), 3), "falta": r1(wm(g, "falta"), 0), "falta_n": r1(wm(g, "falta_n"), 0),
                  **{"dif_" + a: r1(wm(g[g.ant == a], "g_" + PRI), 3) for a in ("man", "new", "seg")}})
por_ant = {a: int(A[A.ant == a].i.nunique()) for a in ("man", "new", "seg")}
# todo Riopaila, todas las edades: ¿2025-26 se vio más verde que otros años?
anual = s[s.anio.between(2019, 2026)].groupby("anio")[PRI].mean()

# ---------------------------------------------------------------- 3) suerte por suerte: ¿la brecha de la curva marca las que cayeron?
S = pd.DataFrame(json.load(open(WEB / "data" / "suertes.json", encoding="utf-8")))
S = S[S["hist"].notna()].copy()
key = c26[["ste", "Mes"]].rename(columns={"ste": "s", "Mes": "m"}).reset_index()
S = S.merge(key, on=["s", "m"], how="inner").drop_duplicates("index").set_index("index")
S["caida"] = 100 * (S["real"] / S["hist"] - 1)
S["mecn"] = (S.tipo == "Mecanizada").astype(int)
GV = A.groupby(["i", "v"], observed=True).agg(gN=("g_" + PRI, "mean"), gF=("g_falta", "sum")).reset_index()
W = GV.pivot(index="i", columns="v", values="gN")
W.columns = ["n_" + c.replace("-", "_") for c in W.columns]
Z = S.join(W)
marca = []
for x, c in zip(ventanas, W.columns):
    q = Z.dropna(subset=[c])
    r = smf.wls(f"caida ~ {c}", data=q, weights=q.a).fit(cov_type="HC1")
    x.update({"brecha": r1(wm(q.assign(a2=q.a), c, "a"), 3), "caida_005": r1(r.params[c] * 0.05, 2), "caida_p": r1(r.pvalues[c], 3), "r2": r1(r.rsquared, 2)})
    qf = GV[GV.v == x["v"]].dropna(subset=["gN", "gF"]).merge(d[["Area"]], left_on="i", right_index=True)
    rf = smf.wls("gN ~ I(gF / 100)", data=qf, weights=qf.Area).fit(cov_type="HC1")
    x.update({"falta_mas": r1(wm(qf, "gF"), 0), "c26_ndre": r1(rf.params["I(gF / 100)"], 4), "c26_p": r1(rf.pvalues["I(gF / 100)"], 3)})
q = Z.dropna(subset=["n_3_5", "n_5_7", "n_7_10"])
rj = smf.wls("caida ~ n_3_5 + n_5_7 + n_7_10 + mecn + ed", data=q, weights=q.a).fit(cov_type="HC1")
r0 = smf.wls("caida ~ mecn + ed", data=q, weights=q.a).fit(cov_type="HC1")
junto = {"n": int(rj.nobs), "r2": r1(rj.rsquared, 2), "r2_sin": r1(r0.rsquared, 2),
         "efectos": {k: [r1(rj.params[k] * 0.05, 2), r1(rj.pvalues[k], 3)] for k in ("n_3_5", "n_5_7", "n_7_10")}}
# quintiles de la brecha de 5 a 7 meses
q = Z.dropna(subset=["n_5_7"]).copy()
q["qq"] = pd.qcut(q.n_5_7, 5, labels=False)
quint = [{"q": int(k) + 1, "n": int(len(g)), "ha": r1(g.a.sum(), 0), "brecha": r1(wm(g, "n_5_7", "a"), 3), "hist": r1(wm(g, "hist", "a")),
          "real": r1(wm(g, "real", "a")), "caida": r1(wm(g, "real", "a") - wm(g, "hist", "a")), "mec": r1(100 * wm(g, "mecn", "a"), 0)}
         for k, g in q.groupby("qq")]
print("3) caída ~ brecha:", [(x["v"], x["caida_005"], x["r2"]) for x in ventanas], junto)

# ---------------------------------------------------------------- ficha: la curva de cada cosecha 2026
fichas = {}
for i, g in E12.groupby("i"):
    if i not in S.index:
        continue
    g = g.set_index("k").reindex(EDADES)
    fichas[f"{S.at[i, 's']}|{int(S.at[i, 'm'])}"] = {"n": int(nprev.get(d.at[i, "ste"], 0)), "v": [r1(z, 3) for z in g[PRI]], "vn": [r1(z, 3) for z in g[PRI + "_n"]],
                                                    "f": [r1(z, 0) for z in g.falta], "fn": [r1(z, 0) for z in g.falta_n]}

# ---------------------------------------------------------------- 4) prueba con años que no se usaron: ¿la brecha a los 5-7 meses anticipa la caída?
# Para cada año Y: normal satelital y TCH histórico (6 años) solo con cosechas ANTERIORES a Y; controles: cosecha mecanizada,
# edad y el corte anterior frente a su historia (descuenta la vuelta a la media de una suerte que venía de un mal corte).
def anio_val(Y, ind=PRI, ks=(6, 7), LL=None):
    LL = L if LL is None else LL
    c = d[(d.anio == Y) & d.Mes.between(1, 9)]
    pv = LL[LL.anio.between(2020, Y - 1) & LL[ind].notna()]
    n = pv.groupby("ste").i.nunique()
    a = LL[LL.i.isin(c.index) & LL.k.isin(ks) & LL[ind].notna()].join(pv.groupby(["ste", "k"])[ind].mean().rename("nor"), on=["ste", "k"]).dropna(subset=["nor"])
    a = a[a.ste.map(n).fillna(0) >= 2]
    H = d[d.anio.between(Y - 6, Y - 1)]
    hi = (H.tch_calc * H.Area).groupby(H.ste).sum() / H.Area.groupby(H.ste).sum()
    z = c.join((a[ind] - a.nor).groupby(a.i).mean().rename("gap"), how="inner").assign(hist=lambda t: t.ste.map(hi),
                                                                                        ult=lambda t: t.ste.map(H.sort_values("cosecha").groupby("ste").tch_calc.last()))
    z = z.dropna(subset=["hist", "ult"])
    return z.assign(caida=100 * (z.tch_calc / z["hist"] - 1), ult_rel=100 * (z.ult / z["hist"] - 1), Y=Y)


FC = "caida ~ gap + mec + Edad + ult_rel"
val = []
for Y in range(2022, 2027):
    z = anio_val(Y)
    rc = smf.wls(FC, data=z, weights=z.Area).fit(cov_type="HC1")
    r0 = smf.wls("caida ~ mec + Edad + ult_rel", data=z, weights=z.Area).fit(cov_type="HC1")
    rz, rs = z[z.gap <= -0.02], z[z.gap > -0.02]
    dt = lambda g: wm(g, "tch_calc") - wm(g, "hist")  # noqa: E731
    cayo = lambda g: 100 * float(np.average(g.caida < -5, weights=g.Area))  # noqa: E731
    val.append({"anio": Y, "n": int(len(z)), "ha": r1(z.Area.sum(), 0), "caida": r1(dt(z)), "ef": r1(rc.params["gap"] * 0.05, 1), "p": r1(rc.pvalues["gap"], 4),
                "r2_sin": r1(r0.rsquared, 2), "r2": r1(rc.rsquared, 2), "rez_n": int(len(rz)), "rez_ha": r1(rz.Area.sum(), 0), "rez_caida": r1(dt(rz)),
                "rez_cayo": r1(cayo(rz), 0), "resto_caida": r1(dt(rs)), "resto_cayo": r1(cayo(rs), 0)})
print("4) por año:", [(x["anio"], x["ef"], x["p"], x["rez_caida"], x["resto_caida"]) for x in val])
Zv = pd.concat([anio_val(Y) for Y in range(2022, 2026)])
z6 = anio_val(2026)
rp = smf.wls(FC + " + C(Y)", data=Zv, weights=Zv.Area).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(Zv.ste)[0]})
r0 = smf.wls("caida ~ mec + Edad + ult_rel + C(Y)", data=Zv, weights=Zv.Area).fit()
pr = lambda b, ks: sum(b[k] * z6[k] for k in ks)  # noqa: E731
r2p = lambda p: float(np.corrcoef(p, z6.caida)[0, 1] ** 2)  # noqa: E731
fuera = {"ef": r1(rp.params["gap"] * 0.05, 1), "p": r1(rp.pvalues["gap"], 4), "n": int(len(z6)),
         "r2": r1(r2p(pr(rp.params, ["gap", "mec", "Edad", "ult_rel"])), 2), "r2_sin": r1(r2p(pr(r0.params, ["mec", "Edad", "ult_rel"])), 2)}
print("   2022-25 → 2026 sin ver 2026:", fuera)

# ---------------------------------------------------------------- 5) la prueba 4 con cada índice, en la MISMA muestra (meses con los seis índices)
# Para elegir sin mirar 2026: t de la brecha en cada año 2022-25 y R² dejando un año fuera (entrenar con tres de 2022-25, predecir el cuarto).
LC = L.dropna(subset=COMP)
VC = {"3-5": (4, 5), "5-7": (6, 7), "7-10": (8, 9, 10)}
FC0 = "caida ~ mec + Edad + ult_rel"


def r2_fuera(tr, te):
    b = smf.wls(FC + " + C(Y)", data=tr, weights=tr.Area).fit().params
    b0 = smf.wls(FC0 + " + C(Y)", data=tr, weights=tr.Area).fit().params
    return r2p_(pr_(b, te, ["gap", "mec", "Edad", "ult_rel"]), te), r2p_(pr_(b0, te, ["mec", "Edad", "ult_rel"]), te)


pr_ = lambda b, z, ks: sum(b[k] * z[k] for k in ks)  # noqa: E731
r2p_ = lambda p, z: float(np.corrcoef(p, z.caida)[0, 1] ** 2)  # noqa: E731
comp = []
for vn, ks in VC.items():
    Zc = {ind: {Y: anio_val(Y, ind, ks, LC) for Y in range(2022, 2027)} for ind in COMP}
    com = {Y: sorted(set.intersection(*[set(Zc[ind][Y].index) for ind in COMP])) for Y in range(2022, 2027)}
    for ind in COMP:
        zs = {Y: Zc[ind][Y].loc[com[Y]] for Y in range(2022, 2027)}
        x = {"v": vn, "ind": ind, "n26": len(zs[2026])}
        for Y, z in zs.items():
            x[f"t{Y}"] = r1(smf.wls(FC, data=z, weights=z.Area).fit(cov_type="HC1").tvalues["gap"], 1)
        x["loo"] = r1(np.mean([r2_fuera(pd.concat([zs[y] for y in range(2022, 2026) if y != Y]), zs[Y])[0] for Y in range(2022, 2026)]), 3)
        x["r2"], x["r2_sin"] = (r1(v, 3) for v in r2_fuera(pd.concat([zs[Y] for Y in range(2022, 2026)]), zs[2026]))
        comp.append(x)
for vn in VC:   # ¿el principal le gana al NDVI en cada año 2022-25? (la regla de la elección)
    a, b = (next(c for c in comp if c["v"] == vn and c["ind"] == i) for i in (PRI, "NDVI"))
    print(f"5) {vn}: {PRI} t > NDVI en {sum(a[f't{Y}'] > b[f't{Y}'] for Y in range(2022, 2026))} de 4 años 2022-25 · R² sin ver 2026",
          {c["ind"]: c["r2"] for c in comp if c["v"] == vn})

out = {"ind": PRI, "comparacion": comp, "tch_base": r1(TN), "etc": ETC, "validacion": val, "fuera": fuera, "cosechas": int(A.i.nunique()), "cosechas_2026": int(len(c26)), "ha": r1(d.loc[A.i.unique(), "Area"].sum(), 0),
       "ciclos_sat": int(P.i.nunique()), "n_tch": int(ft.nobs), "anual": {int(k): r1(v, 3) for k, v in anual.items()},
       "curva": curva, "ventanas": ventanas, "junto": junto, "quintiles": quint, "por_ant": por_ant, "fichas": fichas}
json.dump(out, open(WEB / "data" / "satciclo.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("escrito:", WEB / "data" / "satciclo.json", f"({len(fichas)} fichas)")

# ---------------------------------------------------------------- Excel
lee = pd.DataFrame({"Léeme": [
    "Curva satelital (NDRE y NDMI de Sentinel-2; el NDVI queda como comparación) de cada cosecha ene-sep 2026 por mes de edad, frente a sus propios ciclos cosechados en 2020-2025 a la misma edad.",
    f"Falta de agua del mes = máx({ETC} × evaporación − lluvia, 0) en la EMA de la suerte (clima mensual de Cenicaña).",
    "Ventanas: hoja «TCH y satélite por edad»: cuánto resta en TCH cada 100 mm de falta (2011-2026, como el modelo de la caída) y cuánto baja el índice (2019-2026).",
    "«Caída según la curva»: suerte por suerte en 2026, la caída % de TCH frente a la brecha de NDRE de la ventana.",
    "«Comparación de índices»: la prueba por años (normal y historia solo con años anteriores; controles cosecha mecanizada, edad y corte anterior) "
    "con cada índice en la misma muestra. t = fuerza de la señal en cada año; R² 2022-25 = dejando un año fuera (para elegir sin ver 2026); "
    "R² 2026 = entrenado con 2022-25, sin ver 2026. El WDRVI se calcula del NDVI del mes (α 0,1). Se eligió NDRE: le gana al NDVI en cada año 2022-25 y en cada edad; "
    "el EVI tiene el mejor R² de 2022-25 pero en 2026 no mejora al NDVI (banda azul, sensible a la bruma).",
    "Lo que no demuestra: el NDRE se satura menos que el NDVI, pero también mide el follaje, no altura ni peso; la brecha marca las suertes que cayeron, "
    "pero no dice por qué. Describe y respalda la causa calor y sequía; no entra al modelo."]})
fil = []
for i, g in A.groupby("i"):
    if i not in S.index:
        continue
    r = {"Suerte": S.at[i, "s"], "Mes cosecha": int(S.at[i, "m"]), "Área (ha)": r1(S.at[i, "a"], 2), "Ciclos propios 2020-25": int(nprev.get(d.at[i, "ste"], 0)),
         "Corte anterior": {"man": "manual", "new": "primer mecanizado", "seg": "dos mecanizados"}[g.ant.iloc[0]],
         "Historia TCH": r1(S.at[i, "hist"]), "Real 2026": r1(S.at[i, "real"]), "Caída %": r1(S.at[i, "caida"])}
    for v in VENT:
        h = g[g.v == v]
        r[f"Brecha NDRE {v}"] = r1(h["g_" + PRI].mean(), 3)
        r[f"Brecha NDVI {v}"] = r1(h.g_NDVI.mean(), 3)
        r[f"Falta {v} 2026 (mm)"] = r1(h.falta.sum(), 0)
        r[f"Falta {v} normal (mm)"] = r1(h.falta_n.sum(), 0)
    fil.append(r)
det = pd.DataFrame(fil)
hojas = {"Léeme": lee, "Curva por edad": pd.DataFrame(curva).rename(columns={
    "k": "Mes de edad", "n": "Cosechas", "ndre": "NDRE 2026", "ndre_n": "NDRE normal propio", "dif": "Diferencia NDRE", "bajo": "% del área por debajo",
    "ndvi": "NDVI 2026", "ndvi_n": "NDVI normal propio", "dif_ndvi": "Diferencia NDVI",
    "ndmi": "NDMI 2026", "ndmi_n": "NDMI normal propio", "difm": "Diferencia NDMI", "falta": "Falta 2026 (mm)", "falta_n": "Falta normal (mm)",
    "dif_man": "Dif. NDRE tras corte manual", "dif_new": "Dif. NDRE tras primer mecanizado", "dif_seg": "Dif. NDRE tras dos mecanizados"}),
    "TCH y satélite por edad": pd.DataFrame(ventanas).rename(columns={
        "v": "Edad (meses)", "tch_pct": "% TCH por 100 mm", "tch": "TCH por 100 mm", "tch_p": "p (TCH)", "falta_normal": "Falta normal 2020-25 (mm)",
        "falta_2026": "Falta 2026 (mm)", "aporte": "Aporte 2026 (TCH)", "ndre": "NDRE por 100 mm", "ndre_p": "p (NDRE)", "ndre_n": "n (NDRE)",
        "ndmi": "NDMI por 100 mm", "ndmi_p": "p (NDMI)", "ndmi_n": "n (NDMI)", "brecha": "Brecha NDRE 2026", "caida_005": "Caída % por 0,05 de NDRE",
        "caida_p": "p (caída)", "r2": "R² (caída)", "falta_mas": "Falta de más 2026 (mm)", "mec_ndre": "NDRE tras primer mecanizado", "mec_p": "p (mecanizado)", "c26_ndre": "NDRE por 100 mm de más (2026)", "c26_p": "p (2026)"}),
    "Caída según la curva": pd.DataFrame(quint).rename(columns={"q": "Quinto (brecha 5-7 meses)", "n": "Cosechas", "ha": "ha", "brecha": "Brecha NDRE 5-7",
                                                                "hist": "Historia", "real": "Real 2026", "caida": "Caída TCH", "mec": "% cosecha mecanizada"}),
    "Comparación de índices": pd.DataFrame(comp).rename(columns={"v": "Edad (meses)", "ind": "Índice", "n26": "Cosechas 2026",
        **{f"t{Y}": f"t {Y}" for Y in range(2022, 2027)}, "loo": "R² 2022-25 (un año fuera)", "r2": "R² 2026 sin verlo", "r2_sin": "R² 2026 sin el índice"}),
    "Suertes": det}
if XLS is not None and XLS.exists():
    X = pd.read_excel(XLS, sheet_name="DEFICIT").rename(columns={"SEC-STE": "s", "Rango": "rango", "TCH (Perdida)": "perd"})
    X["s"] = X.s.astype(str).str.strip()
    X["m"] = pd.to_datetime(X["fecha final"]).dt.month
    h = det.merge(X[["s", "m", "rango", "perd"]], left_on=["Suerte", "Mes cosecha"], right_on=["s", "m"])
    hojas["Hoja DEFICIT"] = h.groupby("rango").apply(lambda g: pd.Series({
        "Cosechas": len(g), "ha": g["Área (ha)"].sum(), "Pérdida según la hoja (TCH)": g.perd.mean(),
        **{f"Brecha NDRE {v}": np.average(g[f"Brecha NDRE {v}"].fillna(0), weights=g["Área (ha)"]) for v in VENT},
        "Caída %": np.average(g["Caída %"], weights=g["Área (ha)"])})).round(3).reset_index()
with pd.ExcelWriter(OUT) as x:
    for k, v in hojas.items():
        v.to_excel(x, sheet_name=k, index=False)
print("escrito:", OUT)
