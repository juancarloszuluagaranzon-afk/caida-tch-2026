# -*- coding: utf-8 -*-
r"""Riopaila: ¿la soca rebrota peor después del primer corte mecanizado? Sentinel-2, suerte por suerte, frente a un control.

Grupos (cosechas de 2026 de rio_integrado_dataset.pkl):
  A        corte anterior = primer mecanizado después de manual (p. ej. manual 2024 → mecanizado 2025 → cosecha 2026):
           se compara el ciclo que salió del corte manual con el que salió del primer corte mecanizado.
  control  los mismos años con dos cortes manuales seguidos (manual → manual): mide cuánto cambia el rebrote solo por el año.
  B        primer corte mecanizado EN 2026 (su soca es la cosecha 2027): ciclo después del corte manual de 2025 frente al
           ciclo después del corte mecanizado de 2026, hasta donde va (alerta temprana para 2027).
  controlB los mismos años con corte manual en 2025 y en 2026.
Por suerte: serie de escenas despejadas (Cloud Score+ cs_cdf ≥ 0,6 en ≥ 90 % del área) con NDVI, NDMI y la parte del área
con NDVI < 0,6 («rebrote ralo»); fecha real de cada corte = la caída del NDVI cerca del mes del ZQM; valor a los 100 y
150 días del corte = promedio de las escenas entre 85-115 y 135-165 días. Diferencia = ciclo después del segundo corte
menos ciclo después del primero; efecto de la cosecha mecanizada = diferencia del grupo − diferencia del control.
Imágenes NDVI lado a lado (a ~100 días) para los grupos A y B.
Se excluyen las suertes sembradas (renovadas) dentro del periodo comparado, según la FECHA DE SIEMBRA del maestro oficial,
y una edad solo cuenta si su ventana ya pasó completa antes de HOY.

Uso: <tch-motor>\.venv-gee\Scripts\python.exe mecanizada_satelite.py <datos intermedios> <salida> <maestro.csv>
     [--reusar] [--prueba N]
  --reusar     usa las series e imágenes ya bajadas en <salida> (no vuelve a pedirlas a Earth Engine)
  --prueba N   solo N suertes por grupo
"""
import datetime as dt
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import ee
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, r"C:\Users\Agr349\tch-motor")
from tchmotor import gee  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
pd.set_option("display.width", 220)
PK, SAL, MAESTRO = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
REUSAR = "--reusar" in sys.argv
PRUEBA = int(sys.argv[sys.argv.index("--prueba") + 1]) if "--prueba" in sys.argv else None
(SAL / "imagenes").mkdir(parents=True, exist_ok=True)
HOY = pd.Timestamp("2026-10-20")
EDADES = {60: (45, 75), 100: (85, 115), 150: (135, 165)}
PALETA = ["7f3b08", "b35806", "e08214", "fdb863", "f7f7c4", "d9f0a3", "78c679", "238443", "004529"]
gee.iniciar()
POL = gee.coords_suertes("riopaila")
CS = ee.ImageCollection("GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED")

# ---------------------------------------------------------------- grupos
c = pd.read_pickle(PK / "rio_integrado_dataset.pkl").sort_values(["ste", "cosecha"])
g = c.groupby("ste")
c["c1"], c["c2"] = g.cosecha.shift(), g.cosecha.shift(2)          # cosecha anterior y la de antes
c["k1"], c["k2"] = g.Corte.shift(), g.Corte.shift(2)
c["mm1"], c["mm2"] = g.mec.shift(), g.mec.shift(2)
q = c[(c.anio == 2026) & c.ste.isin(POL)].copy()
seg = (q.Corte - q.k1 == 1) & (q.k1 >= 2) & (q.k1 - q.k2 == 1)  # tres cortes seguidos de la misma plantación
filas = []
for r in q[seg].itertuples():
    if r.mm1 == 1 and r.mm2 == 0:
        filas.append(("A", r.ste, r.c2, r.c1, r.cosecha, r.Area))
    elif r.mm1 == 0 and r.mm2 == 0:
        filas.append(("control", r.ste, r.c2, r.c1, r.cosecha, r.Area))
seg1 = (q.Corte - q.k1 == 1) & (q.k1 >= 1)
for r in q[seg1].itertuples():
    if r.mm1 == 0 and r.mec == 1:
        filas.append(("B", r.ste, r.c1, r.cosecha, HOY, r.Area))
    elif r.mm1 == 0 and r.mec == 0:
        filas.append(("controlB", r.ste, r.c1, r.cosecha, HOY, r.Area))
G = pd.DataFrame(filas, columns=["grupo", "ste", "corte1", "corte2", "fin", "area"])
# renovadas: sembradas después del primer corte comparado → su ciclo no es rebrote de soca
M = pd.read_csv(MAESTRO, sep=";", encoding="utf-8-sig", usecols=["SUERTE", "FECHA DE SIEMBRA"])
siembra = pd.to_datetime(M.drop_duplicates("SUERTE").set_index("SUERTE")["FECHA DE SIEMBRA"], dayfirst=True, errors="coerce")
renov = G.ste.map(siembra) > G.corte1 - pd.Timedelta(days=30)
print(f"renovadas en el periodo (fuera): {renov.sum()} · {', '.join(G[renov].grupo + ' ' + G[renov].ste)}")
G = G[~renov].reset_index(drop=True)
if PRUEBA:  # prueba rápida: pocas suertes por grupo
    G = G.groupby("grupo").head(PRUEBA)
print(G.groupby("grupo").agg(suertes=("ste", "size"), ha=("area", "sum")).round(0))


# ---------------------------------------------------------------- serie Sentinel-2 por suerte
def serie(ste, d0, d1):
    zona = gee.geom_ee(POL[ste])
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(zona).filterDate(str(d0.date()), str(d1.date()))
           .linkCollection(CS, ["cs_cdf"]))

    def f(img):
        ok = img.select("cs_cdf").gte(0.6).rename("ok")
        nd = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
        nm = img.normalizedDifference(["B8", "B11"]).rename("ndmi")
        r = ok.reduceRegion(ee.Reducer.mean(), zona, 20)
        r2 = ee.Image.cat([nd, nm, nd.lt(0.6).rename("rala")]).updateMask(ok).reduceRegion(ee.Reducer.mean(), zona, 10)
        return ee.Feature(None, r.combine(r2)).set("t", img.get("system:time_start"))
    for intento in range(3):
        try:
            rows = ee.FeatureCollection(col.map(f)).filter(ee.Filter.gte("ok", 0.9)).getInfo()["features"]
            break
        except Exception as e:  # cuota o tiempo: reintentar
            if intento == 2:
                print("  falla", ste, e)
                return pd.DataFrame()
    d = pd.DataFrame([x["properties"] for x in rows])
    if d.empty:
        return d
    d["f"] = pd.to_datetime(d.t, unit="ms").dt.normalize()
    return d.dropna(subset=["ndvi"]).groupby("f")[["ndvi", "ndmi", "rala"]].mean().reset_index().sort_values("f")


def fecha_corte(s, mes):
    """el corte = la caída del NDVI más cerca del mes del ZQM (día 15 ± 45 días); si no se ve, el día 15."""
    w = s[(s.f >= mes - pd.Timedelta(days=60)) & (s.f <= mes + pd.Timedelta(days=60))].reset_index(drop=True)
    mejor = None
    for i in range(1, len(w)):
        if w.ndvi[i - 1] >= 0.5 and w.ndvi[i] <= 0.35:
            m = w.f[i - 1] + (w.f[i] - w.f[i - 1]) / 2
            if mejor is None or abs((m - mes).days) < abs((mejor - mes).days):
                mejor = m
    return (mejor, True) if mejor is not None and abs((mejor - mes).days) <= 50 else (mes, False)


def a_edad(s, corte):
    out = {}
    for e, (a, b) in EDADES.items():
        x = s[(s.f >= corte + pd.Timedelta(days=a)) & (s.f <= corte + pd.Timedelta(days=b))]
        if corte + pd.Timedelta(days=b) > HOY:  # ventana sin terminar: no se compara
            x = x.iloc[:0]
        for k in ("ndvi", "ndmi", "rala"):
            out[f"{k}_{e}"] = x[k].mean() if len(x) else np.nan
        out[f"n_{e}"] = len(x)
    return out


def procesar(r):
    arch = SAL / "imagenes" / f"serie_{r.grupo}_{r.ste}.csv"
    if REUSAR and arch.exists():
        s = pd.read_csv(arch, parse_dates=["f"])
    else:
        s = serie(r.ste, r.corte1 - pd.Timedelta(days=75), min(r.fin + pd.Timedelta(days=30), HOY))
    if s.empty:
        return None
    f1, ok1 = fecha_corte(s, r.corte1)
    f2, ok2 = fecha_corte(s, r.corte2)
    a, b = a_edad(s, f1), a_edad(s, f2)
    out = {"grupo": r.grupo, "ste": r.ste, "area": r.area, "corte1": f1.date(), "corte2": f2.date(), "visto1": ok1, "visto2": ok2}
    out.update({f"{k}_1": v for k, v in a.items()})
    out.update({f"{k}_2": v for k, v in b.items()})
    s.to_csv(SAL / "imagenes" / f"serie_{r.grupo}_{r.ste}.csv", index=False)
    return out


print(f"\nserie de {len(G)} suertes en Earth Engine (8 a la vez)…", flush=True)
with ThreadPoolExecutor(max_workers=8) as ex:
    res = [x for x in ex.map(procesar, G.itertuples()) if x]
R = pd.DataFrame(res)
for e in EDADES:
    for k in ("ndvi", "ndmi", "rala"):
        R[f"d_{k}_{e}"] = R[f"{k}_{e}_2"] - R[f"{k}_{e}_1"]
R.to_csv(SAL / "satelite_por_suerte.csv", index=False)
print(f"listas: {len(R)} · fecha del corte vista en el satélite: {100 * R[['visto1', 'visto2']].all(axis=1).mean():.0f} %")


# ---------------------------------------------------------------- resumen: grupo frente a su control
def resumen(gr, ctrl):
    filas = []
    for e in EDADES:
        for k in ("ndvi", "ndmi", "rala"):
            col = f"d_{k}_{e}"
            a, b = R[R.grupo == gr][col].dropna(), R[R.grupo == ctrl][col].dropna()
            if len(a) < 3 or len(b) < 3:
                continue
            se = np.sqrt(a.var() / len(a) + b.var() / len(b))
            filas.append({"comparacion": f"{gr} frente a {ctrl}", "edad": e, "indice": k, "n_grupo": len(a), "n_control": len(b),
                          "cambio_grupo": a.mean(), "cambio_control": b.mean(), "efecto": a.mean() - b.mean(),
                          "t": (a.mean() - b.mean()) / se if se > 0 else np.nan,
                          "peor_grupo_pct": 100 * ((a > 0.05) if k == "rala" else (a < -0.03)).mean(),
                          "peor_control_pct": 100 * ((b > 0.05) if k == "rala" else (b < -0.03)).mean()})
    return filas


RS = pd.DataFrame(resumen("A", "control") + resumen("B", "controlB"))
RS.to_csv(SAL / "satelite_resumen.csv", index=False)
print("\nresumen (efecto = cambio del grupo − cambio del control; NDVI y NDMI en unidades del índice, rala en fracción del área):")
print(RS.round(3).to_string(index=False))


# ---------------------------------------------------------------- imágenes lado a lado (~100 días), grupos A y B
F = r"C:\Windows\Fonts\tahoma.ttf"
FB = r"C:\Windows\Fonts\tahomabd.ttf"
f1_, f2_ = ImageFont.truetype(FB, 15), ImageFont.truetype(F, 13)
MC = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
fmt = lambda d: f"{d.day} {MC[d.month - 1]} {d.year}"  # noqa: E731


def escena(ste, corte, edad=100):
    zona = gee.geom_ee(POL[ste])
    t = corte + pd.Timedelta(days=edad)
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(zona)
           .filterDate(str((t - pd.Timedelta(days=25)).date()), str((t + pd.Timedelta(days=25)).date())).linkCollection(CS, ["cs_cdf"]))
    col = col.map(lambda i: i.set("ok", i.select("cs_cdf").gte(0.6).reduceRegion(ee.Reducer.mean(), zona, 20).get("cs_cdf")))
    col = col.filter(ee.Filter.gte("ok", 0.95))
    ts = col.aggregate_array("system:time_start").getInfo()
    if not ts:
        return None
    tt = min(ts, key=lambda x: abs(pd.Timestamp(x, unit="ms") - t))
    img = col.filter(ee.Filter.eq("system:time_start", tt)).first()
    nd = img.normalizedDifference(["B8", "B4"])
    m = ee.Image.cat([nd.rename("ndvi"), nd.lt(0.6).rename("rala")]).reduceRegion(ee.Reducer.mean(), zona, 10).getInfo()
    fc = ee.FeatureCollection([ee.Feature(zona)])
    vis = nd.visualize(min=0.1, max=0.9, palette=PALETA).blend(ee.Image().byte().paint(fc, 1, 2).visualize(palette=["111111"]))
    url = vis.getThumbURL({"region": zona.bounds().buffer(120).bounds(), "dimensions": 360, "format": "png"})
    arch = SAL / "imagenes" / f"tmp_{ste}_{tt}.png"
    urllib.request.urlretrieve(url, arch)
    return {"png": arch, "fecha": pd.Timestamp(tt, unit="ms"), "dias": (pd.Timestamp(tt, unit="ms") - corte).days,
            "ndvi": m["ndvi"], "rala": m["rala"]}


def par(r):
    dias2 = (HOY - pd.Timestamp(r.corte2)).days
    edad = 100 if dias2 >= 115 else 60 if dias2 >= 75 else None  # la soca 2027 todavía es joven
    if edad is None:
        return None
    try:
        a = escena(r.ste, pd.Timestamp(r.corte1), edad)
        b = escena(r.ste, pd.Timestamp(r.corte2), edad)
    except Exception as e:
        print("  imagen falla", r.ste, e)
        return None
    if not a or not b:
        for z in (a, b):
            if z:
                z["png"].unlink(missing_ok=True)
        return None
    ims = [Image.open(x["png"]).convert("RGB") for x in (a, b)]
    h = max(i.height for i in ims)
    W = sum(max(i.width, 300) for i in ims) + 16
    out = Image.new("RGB", (W, h + 70), "white")
    d = ImageDraw.Draw(out)
    x = 0
    seg2 = "mecanizado" if r.grupo in ("A", "B") else "manual"
    for im, inf, et in zip(ims, (a, b), ("después del corte manual", f"después del corte {seg2}")):
        d.text((x, 2), fmt(inf["fecha"]), font=f1_, fill=(26, 26, 26))
        d.text((x, 21), et, font=f2_, fill=(26, 26, 26))
        d.text((x, 39), f"{inf['dias']} días · NDVI {inf['ndvi']:.2f} · ralo {100 * inf['rala']:.0f} %".replace(".", ","), font=f2_,
               fill=(153, 27, 27) if inf is b and inf["rala"] > a["rala"] + 0.05 else (68, 64, 60))
        out.paste(im, (x, 62))
        x += max(im.width, 300) + 16
    nombre = f"{r.grupo}_{r.ste}.png"
    out.save(SAL / "imagenes" / nombre, optimize=True)
    for z in (a, b):
        z["png"].unlink(missing_ok=True)
    return {"grupo": r.grupo, "ste": r.ste, "imagen": nombre, "edad": edad, "fecha1": a["fecha"].date(), "fecha2": b["fecha"].date(),
            "ndvi1": a["ndvi"], "ndvi2": b["ndvi"], "rala1": a["rala"], "rala2": b["rala"]}


print("\nimágenes de los grupos A y B…", flush=True)
PREV = {}
if REUSAR and (SAL / "satelite_imagenes.csv").exists():
    PREV = {(x["grupo"], x["ste"]): x for x in pd.read_csv(SAL / "satelite_imagenes.csv").to_dict("records")
            if (SAL / "imagenes" / x["imagen"]).exists()}
AB = R[R.grupo.isin(["A", "B"])]
im = [PREV[(r.grupo, r.ste)] for r in AB.itertuples() if (r.grupo, r.ste) in PREV]
with ThreadPoolExecutor(max_workers=6) as ex:
    im += [x for x in ex.map(par, [r for r in AB.itertuples() if (r.grupo, r.ste) not in PREV]) if x]
pd.DataFrame(im).to_csv(SAL / "satelite_imagenes.csv", index=False)
print(f"imágenes: {len(im)} de {len(AB)}")
