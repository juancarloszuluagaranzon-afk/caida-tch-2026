# -*- coding: utf-8 -*-
r"""Riopaila: TCH por rango de tiempo térmico del ciclo, como la lámina de Cenicaña, con las cosechas 2020-2026.

Tiempo térmico de una cosecha = Σ (temperatura media del día − base) del corte anterior a la cosecha, con la media del día =
(máxima + mínima) ÷ 2 de la EMA de la suerte (La Paila o Bugalagrande, repo Precipitacion-riopaila; en 2026 los días sin dato
con el diario de Cenicaña). La base se calibra con la hoja «Suertes Tiempo Termico 2026 Sep» de «Riegos ciclo.xlsx» (315 cosechas
de 2026, ~18,4 °C), para que las cifras sean las mismas de esa hoja y de los rangos de Cenicaña.
Rangos: < 2.000, 2.000-2.500, 2.500-3.000, > 3.000 grados-día.
  · TCH por rango (ponderado por área) con intervalo de 95 % y comparación de medias (Tukey);
  · % del área cosechada en 2026 (enero a septiembre) en cada rango;
  · TCH que pierde cada rango frente al de > 3.000;
  · lo mismo descontando suerte, año y mes (cada suerte frente a sí misma), porque el tiempo térmico casi solo sigue la edad.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe tiempo_termico.py <datos intermedios> <repo Precipitacion-riopaila> <Clima_Cenicana_...xlsx>
       <Riegos ciclo.xlsx> <salida.xlsx> <lámina.png>
"""
import sys
import warnings
from pathlib import Path

import matplotlib
import numpy as np
import openpyxl
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multicomp import pairwise_tukeyhsd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8")
PK, REPO, CEN, RIEGOS, SAL, PNG = (Path(a) for a in sys.argv[1:7])
RANGOS = [(-np.inf, 2000, "< 2.000"), (2000, 2500, "2.000-2.500"), (2500, 3000, "2.500-3.000"), (3000, np.inf, "> 3.000")]
ET = [r[2] for r in RANGOS]

# ---------------------------------------------------------------- temperatura media diaria de cada EMA
e = pd.read_csv(REPO / "clima_estaciones.csv", sep=";")
e["f"] = pd.to_datetime(e.fc_obsrvcion)
w = openpyxl.load_workbook(CEN, read_only=True, data_only=True)
it = w["Diario 2026"].iter_rows(values_only=True)
enc = next(it)
M = pd.DataFrame(list(it), columns=enc)
M["Fecha"] = pd.to_datetime(M.Fecha)
dias = pd.date_range("2018-01-01", "2026-10-18", freq="D")
TM = {}
for nom, cod in (("La Paila", "PAI"), ("Bugalagrande", "BLG")):
    d = e[e.nm_ema == nom].set_index("f").sort_index()
    d = d[~d.index.duplicated()].reindex(dias)
    m = M[M["Código"] == cod].set_index("Fecha").reindex(dias)
    f26 = d.index >= "2026-01-01"
    for col, src in (("tmp_mxma", "Temperatura máxima (°C)"), ("tmp_mnma", "Temperatura mínima (°C)")):
        d.loc[f26 & d[col].isna(), col] = pd.to_numeric(m[src], errors="coerce")[f26 & d[col].isna()]
    TM[nom] = ((d.tmp_mxma + d.tmp_mnma) / 2)


def suma(est, ini, fin, base):
    s = TM[est].loc[ini:fin]
    ok = s.notna()
    return (s[ok] - base).sum() * len(s) / ok.sum() if ok.sum() >= 0.9 * len(s) else np.nan   # días sin dato: con la media del ciclo


# ---------------------------------------------------------------- base calibrada con la hoja de 2026
h = pd.read_excel(RIEGOS, sheet_name="Suertes Tiempo Termico 2026 Sep").dropna(subset=["tiempo_termico", "fecha_inicial", "fecha_final"])
h["est"] = h.Estacion.astype(str).str.strip()
h = h[h.est.isin(TM)]
ini_h, fin_h = pd.to_datetime(h.fecha_inicial).dt.normalize(), pd.to_datetime(h.fecha_final).dt.normalize()
st = np.array([suma(es, a, b, 0.0) for es, a, b in zip(h.est, ini_h, fin_h)])
n = np.array([(b - a).days + 1 for a, b in zip(ini_h, fin_h)])
ok = ~np.isnan(st)
BASE = float(np.sum((st[ok] - h.tiempo_termico.values[ok]) * n[ok]) / np.sum(n[ok] ** 2))      # mínimos cuadrados: TT = Σ tm − base × días
tt_h = st - BASE * n
dif = tt_h[ok] - h.tiempo_termico.values[ok]
print(f"base calibrada con la hoja de 2026: {BASE:.2f} °C · {ok.sum()} cosechas · diferencia media {np.mean(dif):+.1f}, "
      f"absoluta {np.mean(np.abs(dif)):.1f} grados-día · correlación {np.corrcoef(tt_h[ok], h.tiempo_termico.values[ok])[0, 1]:.4f}")
print("rango de la hoja frente al calculado con su propio tiempo térmico: coinciden",
      f"{100 * np.mean(pd.cut(h.tiempo_termico, [r[0] for r in RANGOS] + [np.inf], labels=['<2000', '2000-2500', '2500-3000', '3000+']).astype(str).values == h['Rango T_Termico'].astype(str).str.replace('3500+', '3000+').replace('3000-3500', '3000+').values):.0f} %")

# ---------------------------------------------------------------- todas las cosechas 2020-2026
c = pd.read_pickle(PK / "rio_integrado_dataset.pkl")
c = c[c.anio.between(2020, 2026) & c.ini.notna() & c.est.isin(TM)].copy()
ini, fin = c.ini.dt.normalize(), c.cosecha
c["tt"] = [suma(es, a, b, BASE) for es, a, b in zip(c.est, ini, fin)]
c = c.dropna(subset=["tt"])
c["rango"] = pd.cut(c.tt, [r[0] for r in RANGOS] + [np.inf], labels=ET, right=False)
c["dias"] = (c.cosecha - ini).dt.days
print(f"cosechas 2020-2026 con tiempo térmico: {len(c)} · grados-día por día del ciclo {(c.tt / c.dias).mean():.2f} "
      f"(± {(c.tt / c.dias).std():.2f}) · correlación con la edad {np.corrcoef(c.tt, c.Edad)[0, 1]:.3f}")


def wm(g, k):
    return float(np.average(g[k], weights=g.Area))


def ic(g):
    """media ponderada por área con intervalo de 95 % (error estándar ponderado, tamaño efectivo de Kish)."""
    m = wm(g, "tch_calc")
    w_ = g.Area / g.Area.sum()
    var = float(np.sum(w_ * (g.tch_calc - m) ** 2))
    neff = g.Area.sum() ** 2 / np.sum(g.Area ** 2)
    se = np.sqrt(var / max(neff - 1, 1))
    return m, 1.96 * se, neff


filas = []
for r in ET:
    g = c[c.rango == r]
    m, e95, neff = ic(g)
    filas.append({"rango": r, "cosechas": len(g), "ha": g.Area.sum(), "TCH": m, "IC95 ±": e95, "edad media (meses)": wm(g, "Edad"),
                  "grados-día medio": wm(g, "tt")})
T = pd.DataFrame(filas)
T["frente a > 3.000 (TCH)"] = T.TCH - T.TCH.iloc[-1]
q26 = c[(c.anio == 2026) & c.Mes.between(1, 9)]
T["% del área 2026"] = [100 * q26.Area[q26.rango == r].sum() / q26.Area.sum() for r in ET]
tk = pairwise_tukeyhsd(c.tch_calc, c.rango.astype(str), alpha=0.05)
TK = pd.DataFrame(tk.summary().data[1:], columns=tk.summary().data[0])

# letras de grupo (rangos que no difieren comparten letra): conjuntos máximos de rangos sin diferencia entre sí, en orden de media
from itertools import combinations  # noqa: E402
dif_sig = {frozenset((a, b)): bool(rej) for a, b, rej in zip(TK.group1, TK.group2, TK.reject)}
orden = list(T.sort_values("TCH", ascending=False).rango)
iguales = lambda S: all(not dif_sig.get(frozenset(p), False) for p in combinations(S, 2))  # noqa: E731
conj = [set(S) for k in range(len(orden), 0, -1) for S in combinations(orden, k) if iguales(S)]
maximos = [S for S in conj if not any(S < O for O in conj)]
maximos.sort(key=lambda S: min(orden.index(r) for r in S))
letras = {r: "".join("abcd"[i] for i, S in enumerate(maximos) if r in S) for r in ET}
T["grupo (Tukey)"] = T.rango.map(letras)

# descontando suerte, año y mes (misma suerte)
fe = smf.wls("np.log(tch_calc) ~ C(rango, Treatment('> 3.000')) + C(ste) + C(anio) + C(Mes)", data=c.assign(rango=c.rango.astype(str)), weights=c.Area)
fe = fe.fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(c.ste)[0]})
TN = wm(c[c.anio.between(2020, 2025)], "tch_calc")
T["misma suerte, año y mes: frente a > 3.000 (TCH)"] = [
    0.0 if r == "> 3.000" else 100 * np.expm1(fe.params[f"C(rango, Treatment('> 3.000'))[T.{r}]"]) / 100 * TN for r in ET]
T["p (misma suerte)"] = [np.nan if r == "> 3.000" else fe.pvalues[f"C(rango, Treatment('> 3.000'))[T.{r}]"] for r in ET]
print(T.round(2).to_string(index=False))
print(TK.to_string(index=False))

# ---------------------------------------------------------------- lámina
ROJO, GRIS, TINTA, CLARO = "#C8102E", "#8C8C8C", "#1C1917", "#F3F2F1"
es = lambda v, d=1, s=False: (("+" if v > 0 else "−" if v < 0 else "") if s else ("−" if v < 0 else "")) + f"{abs(v):,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
COL = ["#7A0A1B", "#C8102E", "#E8707F", "#F4B8C0"]
fig = plt.figure(figsize=(13.33, 7.5), dpi=150)
fig.patch.set_facecolor("white")
fig.text(0.04, 0.93, "TCH por tiempo térmico del ciclo · Riopaila 2020-2026", fontsize=22, fontweight="bold", color=TINTA)
fig.text(0.04, 0.885, f"Grados-día del corte anterior a la cosecha (temperatura media − {es(BASE)} °C, EMA de cada suerte), la misma medida de Cenicaña",
         fontsize=11.5, color="#57534E")
ax = fig.add_axes([0.06, 0.30, 0.52, 0.53])
x = np.arange(len(ET))
ax.bar(x, T.TCH, color=COL, width=0.62, zorder=2)
ax.errorbar(x, T.TCH, yerr=T["IC95 ±"], fmt="none", ecolor=TINTA, capsize=6, lw=1.4, zorder=3)
for i, r in T.iterrows():
    ax.text(i, r.TCH + r["IC95 ±"] + 2.5, es(r.TCH), ha="center", fontsize=14, fontweight="bold", color=TINTA)
    ax.text(i, r.TCH + r["IC95 ±"] + 12, r["grupo (Tukey)"], ha="center", fontsize=12, color=ROJO, fontweight="bold")
    ax.text(i, 6, f"{es(r.cosechas, 0)} cosechas\n{es(r['edad media (meses)'])} meses", ha="center", fontsize=9.5, color="white")
ax.set_xticks(x, [f"{t}\ngrados-día" for t in ET], fontsize=11)
ax.set_ylabel("TCH (promedio ponderado por área, IC 95 %)", fontsize=11)
ax.set_ylim(0, max(T.TCH + T["IC95 ±"]) + 24)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color="#E7E5E4", zorder=0)
ax.set_title("TCH por rango (letras distintas = medias distintas, Tukey 5 %)", fontsize=12, loc="left", color=TINTA)
ax2 = fig.add_axes([0.64, 0.29, 0.31, 0.43])
sz = T["% del área 2026"].values
ws, _ = ax2.pie(sz, colors=COL, startangle=90, counterclock=False, wedgeprops=dict(width=0.42, edgecolor="white"))
for wdg, v, et in zip(ws, sz, ET):
    ang = np.deg2rad((wdg.theta2 + wdg.theta1) / 2)
    if v >= 2:
        ax2.text(1.3 * np.cos(ang), 1.3 * np.sin(ang), f"{et}\n{es(v, 0)} %", ha="center", va="center", fontsize=10.5, color=TINTA)
fig.text(0.795, 0.80, "Área cosechada en 2026 (enero a septiembre)", fontsize=12, color=TINTA, ha="center")
ax2.text(0, 0, f"{es(q26.Area.sum(), 0)} ha", ha="center", va="center", fontsize=13, fontweight="bold", color=TINTA)
vin = [f"• {r.rango}: {es(r['frente a > 3.000 (TCH)'], 1, True)} TCH frente al rango > 3.000" for _, r in T.iloc[:-1].iterrows()]
fe_txt = "; ".join(f"{r}: {es(v, 1, True)}" for r, v in zip(ET[:-1], T["misma suerte, año y mes: frente a > 3.000 (TCH)"][:-1]))
fig.text(0.04, 0.215, "Lo que pierde cada rango", fontsize=13, fontweight="bold", color=TINTA)
fig.text(0.04, 0.10, "\n".join(vin), fontsize=11.5, color=TINTA, va="bottom")
fig.text(0.47, 0.215, "Cómo leerla", fontsize=13, fontweight="bold", color=TINTA)
fig.text(0.47, 0.055, (f"En Riopaila el tiempo térmico casi solo sigue la edad: {es(np.mean(c.tt / c.dias))} grados-día por día de ciclo\n"
                       f"en todas las suertes (correlación con la edad {es(np.corrcoef(c.tt, c.Edad)[0, 1], 2)}). El rango es, en la práctica, la edad de corte.\n"
                       f"Descontando suerte, año y mes (cada suerte frente a sí misma), frente a > 3.000:\n{fe_txt} TCH.\n"
                       "En el modelo de la caída esto ya está en «Edad de cosecha» (+1,8 TCH en 2026)."), fontsize=10, color="#44403C", va="bottom")
fig.text(0.04, 0.02, f"{es(len(c), 0)} cosechas de Riopaila 2020-2026 (ZQM + G&P). Base de {es(BASE)} °C calibrada con la hoja «Suertes Tiempo Térmico 2026» "
         f"(diferencia media {es(np.mean(np.abs(dif)), 0)} grados-día). Tukey entre cosechas.", fontsize=8.5, color=GRIS)
fig.savefig(PNG, dpi=150)
print("lámina:", PNG)

with pd.ExcelWriter(SAL) as xw:
    pd.DataFrame({"Léeme": [
        "Tiempo térmico = Σ (temperatura media del día − base) del corte anterior a la cosecha; media = (máxima + mínima) ÷ 2 de la EMA de la suerte.",
        f"Base {BASE:.2f} °C, calibrada con la hoja «Suertes Tiempo Termico 2026 Sep» de «Riegos ciclo.xlsx» ({ok.sum()} cosechas; diferencia absoluta media {np.mean(np.abs(dif)):.1f} grados-día).",
        "TCH por rango ponderado por área, IC 95 % con tamaño efectivo de Kish; comparación de medias con Tukey (5 %).",
        "«Misma suerte»: regresión del log TCH con efectos fijos de suerte, año y mes, ponderada por área, errores agrupados por suerte.",
        "En Riopaila el tiempo térmico casi solo sigue la edad del ciclo: no es una causa aparte de la edad de cosecha."]}).to_excel(xw, sheet_name="Léeme", index=False)
    T.round(3).to_excel(xw, sheet_name="Por rango", index=False)
    TK.to_excel(xw, sheet_name="Tukey", index=False)
    c[["ste", "anio", "Mes", "Corte", "Area", "tch_calc", "Edad", "dias", "est", "tt", "rango"]].rename(
        columns={"ste": "suerte", "tch_calc": "TCH", "tt": "tiempo térmico (grados-día)", "dias": "días del ciclo"}).to_excel(xw, sheet_name="Cosechas", index=False)
    pd.DataFrame({"suerte": h.suerte.values[ok], "tiempo térmico hoja": h.tiempo_termico.values[ok], "calculado": tt_h[ok],
                  "diferencia": dif, "rango en la hoja": h["Rango T_Termico"].values[ok]}).to_excel(xw, sheet_name="Calibración 2026", index=False)
print("Excel:", SAL)
