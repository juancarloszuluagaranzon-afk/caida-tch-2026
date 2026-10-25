# -*- coding: utf-8 -*-
"""Mismo modelo para las dos plantas: log TCH con efectos fijos de suerte, año y mes + edad, soca, variedad, incendio, cosecha
mecánica, lluvia de los meses 0-3 (arranque) y días > 32 °C en los 30 días antes de la cosecha (final).
Aportes de 2026 frente a 2020-2025, total ene-ago y por bimestre. Diatraea aparte (evaluaciones) y mezcla varietal aparte."""
import sys, warnings
import numpy as np, pandas as pd, openpyxl
import statsmodels.formula.api as smf
warnings.filterwarnings("ignore"); sys.stdout.reconfigure(encoding="utf-8"); pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
S = r"C:\Users\Agr349\AppData\Local\Temp\claude\C--Users-Agr349\39506705-db06-4ee1-9a78-cdc4dba16d29\scratchpad"
BIM = {1: "ene-feb", 2: "ene-feb", 3: "mar-abr", 4: "mar-abr", 5: "may-jun", 6: "may-jun", 7: "jul-ago", 8: "jul-ago"}
EDADES = ["<9", "9-10", "10-11", "11-12", "12-13", "13-14", "14-15", ">15"]
wm = lambda g, k: np.average(g[k].dropna(), weights=g.Area[g[k].notna()]) if g[k].notna().any() else np.nan

def fitc(f, d, grp):
    mo = smf.wls(f, data=d, weights=d.Area); rows = mo.data.row_labels
    return mo.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.loc[rows, grp])[0]})

def aportes(mo, q, r, mec_cols, ed):
    for k in EDADES:
        q["e_" + k] = (q.edad_b == k).astype(float); r["e_" + k] = (r.edad_b == k).astype(float)
    a = {"lluvia 0-3 m": mo.params["llu03_100"] * (wm(q, "llu03_100") - wm(r, "llu03_100")),
         "días >32 °C": mo.params["d32"] * (wm(q, "d32") - wm(r, "d32")),
         "edad": sum(ed[k] * (wm(q, "e_" + k) - wm(r, "e_" + k)) for k in EDADES),
         "incendio": mo.params["inc"] * (wm(q, "inc") - wm(r, "inc")),
         "soca": mo.params["Corte"] * (wm(q, "Corte") - wm(r, "Corte"))}
    if isinstance(mec_cols, dict):   # Riopaila: brecha mecánica de cada año
        a["mecánica"] = sum(mo.params[k] * wm(q, k) for k in mec_cols["q"]) - sum(mo.params[k] * wm(r, k) for k in mec_cols["r"])
    else:
        a["mecánica"] = mo.params["mec"] * (wm(q, "mec") - wm(r, "mec"))
    return a

def informe(nombre, d, est, grp, ton, mec_cols, extra_diatraea):
    ED = "C(edad_b, Treatment('12-13'))"
    mec_f = " + ".join(mec_cols["all"]) if isinstance(mec_cols, dict) else "mec"
    f = f"y ~ C({grp}) + C(anio) + C(Mes) + {ED} + C(soca_b) + C(var) + inc + Corte + {mec_f} + llu03_100 + d32"
    mo = fitc(f, est, grp)
    ed = {k: mo.params.get(f"{ED}[T.{k}]", 0.0) for k in EDADES}
    print(f"\n==================== {nombre} (n={int(mo.nobs)}, R²={mo.rsquared:.2f})")
    for k in ["llu03_100", "d32", "inc", "Corte"] + (mec_cols["all"][-3:] if isinstance(mec_cols, dict) else ["mec"]):
        print(f"  {k:<10} {100*(np.exp(mo.params[k])-1):+6.2f}%  (p={mo.pvalues[k]:.3f})")
    print("  edad:", {k: round(100 * (np.exp(v) - 1), 1) for k, v in ed.items()})
    filas = []
    for lab, meses in [("ene-ago", range(1, 9))] + [(b, [m for m, bb in BIM.items() if bb == b]) for b in ["ene-feb", "mar-abr", "may-jun", "jul-ago"]]:
        q = d[(d.anio == 2026) & d.Mes.isin(meses)].copy(); r = d[d.anio.between(2020, 2025) & d.Mes.isin(meses)].copy()
        T = q[ton].sum(); HA = q.Area.sum()
        gap = wm(q.dropna(subset=["rel"]), "rel") - wm(r.dropna(subset=["rel"]), "rel")
        a = aportes(mo, q, r, mec_cols, ed)
        dia = extra_diatraea(q, r)
        a["Diatraea"] = dia
        row = {"periodo": lab, "cortes": len(q), "ha": HA, "t": T, "TCH": T / HA, "resultado": 100 * gap}
        row.update({k: 100 * v for k, v in a.items()})
        row["sin explicar"] = 100 * gap - sum(100 * v for v in a.values() if pd.notna(v))
        row["t_resultado"] = -gap * T
        row.update({"t_" + k: -v * T for k, v in a.items()})
        row.update({"llu03 26": wm(q, "llu03"), "llu03 ref": wm(r, "llu03"), "d32 26": wm(q, "d32"), "d32 ref": wm(r, "d32")})
        filas.append(row)
    t = pd.DataFrame(filas).set_index("periodo")
    cols = ["cortes", "ha", "TCH", "resultado", "lluvia 0-3 m", "días >32 °C", "edad", "incendio", "mecánica", "soca", "Diatraea", "sin explicar"]
    print(t[cols].round(1).to_string())
    print(t[["t_resultado", "t_lluvia 0-3 m", "t_días >32 °C", "t_edad", "t_mecánica", "t_Diatraea"]].round(-2).to_string())
    print(t[["llu03 26", "llu03 ref", "d32 26", "d32 ref"]].round(1).to_string())
    return mo, t

# ================= Riopaila =================
c = pd.read_pickle("rio_clima2.pkl")
c["y"] = np.log(c.tch_calc); c = c[np.isfinite(c.y) & c.Area.gt(0) & c.tch_calc.between(20, 300)].dropna(subset=["Edad", "Mes"])
c["anio"] = c["AÑO"].astype(int); c["Mes"] = c.Mes.astype(int)
c["edad_b"] = pd.cut(c.Edad, [0, 9, 10, 11, 12, 13, 14, 15, 40], labels=EDADES).astype(str)
c["soca_b"] = pd.cut(c.Corte.fillna(3), [0, 1, 2, 3, 4, 5, 7, 99]).astype(str); c["Corte"] = c.Corte.fillna(3)
top = c["Variedad Principal"].value_counts(); c["var"] = c["Variedad Principal"].where(c["Variedad Principal"].map(top) >= 60, "otra")
c["mec"] = (c["Tipo Cosecha"] == "Mecanico").astype(int); c["inc"] = (c["Causa Cosecha"].astype(str) == "Incendio").astype(int)
for a_ in range(2011, 2027): c[f"mec_{a_}"] = c.mec * (c.anio == a_)
c["llu03_100"] = c.llu03 / 100
base = c[c.anio.between(2020, 2025)].groupby("ste").y.agg(["sum", "count"]); c = c.join(base, on="ste"); eb = c.anio.between(2020, 2025)
c["rel"] = np.where(c.anio >= 2020, c.y - np.where(eb, (c["sum"] - c.y) / (c["count"] - 1), c["sum"] / c["count"]), np.nan)
c.loc[eb & (c["count"] <= 1), "rel"] = np.nan
b = pd.read_csv(rf"{S}\caida\sanidad\cortes_barrenador.csv"); b["k"] = b.ste.astype(str).str.strip() + "|" + b.anio.astype(int).astype(str) + "|" + b.Mes.astype(int).astype(str)
c["k"] = c.ste + "|" + c.anio.astype(str) + "|" + c.Mes.astype(str)
c = c.merge(b.drop_duplicates("k")[["k", "i_dia"]], on="k", how="left").set_index(c.index)
est = c[c.anio >= 2011].dropna(subset=["llu03", "d32"])
mec_cols = {"all": [f"mec_{a_}" for a_ in range(2011, 2027)], "q": ["mec_2026"], "r": [f"mec_{a_}" for a_ in range(2020, 2026)]}
m3 = c.dropna(subset=["i_dia", "rel"]).copy(); m3["am"] = m3.anio.astype(str) + "-" + m3.Mes.astype(str)
bI_r = fitc("rel ~ i_dia + C(am) + Edad + Corte + mec", m3, "ste").params["i_dia"]
print("Riopaila Diatraea por punto:", round(100 * bI_r, 2), "(no significativo; se reporta 0)")
dia_r = lambda q, r: 0.0
mo_r, t_r = informe("RIOPAILA", c[c.anio >= 2020], est, "ste", "TC-Total", mec_cols, dia_r)
t_r.to_pickle("tabla_riopaila.pkl")

# ================= Castilla =================
h = pd.read_pickle("cas_clima2.pkl")
h = h.dropna(subset=["ltch", "Edad"]).copy()
h["y"] = h.ltch; h["anio"] = h["AÑO"].astype(int); h["Mes"] = h.MES.astype(int)
h["soca_b"] = pd.cut(h.Corte.fillna(3), [0, 1, 2, 3, 4, 5, 7, 99]).astype(str); h["Corte"] = h.Corte.fillna(3)
top = h.VARIEDAD.value_counts(); h["var"] = h.VARIEDAD.where(h.VARIEDAD.map(top) >= 60, "otra")
h["llu03_100"] = h.llu03 / 100
estc = h.dropna(subset=["llu03", "d32"])
A = h[h.ten == "AGRICOLA"].copy()
mA = A.dropna(subset=["II", "rel"]).copy(); mA["am"] = mA.cosecha.dt.strftime("%Y-%m")
bI_c = fitc("rel ~ II + C(am) + Edad + Corte + mec", mA, "ut").params["II"]
print("\nCastilla Diatraea por punto:", round(100 * bI_c, 2))
IIref = wm(mA[mA.anio.between(2020, 2025)], "II")
def dia_c(q, r):
    e26 = q.dropna(subset=["II"]); eR = r.dropna(subset=["II"])
    return bI_c * (wm(e26, "II") - wm(eR, "II")) if len(e26) >= 5 and len(eR) >= 5 else np.nan
mo_c, t_c = informe("CASTILLA (tierras propias; estimado con todas las tenencias)", A, estc, "ut", "TONS REAL", "mec", dia_c)
t_c.to_pickle("tabla_castilla.pkl")
# Diatraea por bimestre (datos)
print("\nCastilla %I.I. por bimestre 2026 vs 2020-25:", {b_: (round(wm(mA[(mA.anio == 2026) & mA.Mes.map(BIM).eq(b_)], "II"), 2) if (mA[(mA.anio == 2026) & mA.Mes.map(BIM).eq(b_)]).shape[0] else None, round(wm(mA[mA.anio.between(2020, 2025) & mA.Mes.map(BIM).eq(b_)], "II"), 2), int((mA[(mA.anio == 2026) & mA.Mes.map(BIM).eq(b_)]).shape[0])) for b_ in ["ene-feb", "mar-abr", "may-jun", "jul-ago"]})
