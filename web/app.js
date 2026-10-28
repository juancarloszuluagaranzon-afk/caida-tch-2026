/* Informe navegable «Caída del TCH Riopaila 2026».
   Datos en data/*.json (informe_datos.py). Rutas: #resumen · #causa/<id> · #suertes · #suerte/<clave> · #prueba · #metodo */
'use strict';

const $app = document.getElementById('app');
let R, C, S, F, V, E, CAUSA, SUERTE;
let HU = null;   // cómo se comportó cada suerte frente a su grupo de humedad (humedad.json, humedad_comportamiento.py); opcional
let SU = null;   // grupo de humedad del suelo de lo cosechado en 2026 (suelos.json, suelos_humedad.py); opcional
let DV = null, AFO = {};   // aforo frente al óptimo de la variedad (desarrollo.json, desarrollo_optimo.py); opcional
let BL = null;             // balance hídrico de Cenicaña y riego aplicado en mm (balance.json, balance_riego.py); opcional
let SC = null;             // curva satelital del ciclo 2026 frente a la normal propia y falta de agua por edad (satciclo.json, satelite_ciclo.py); opcional
let RF = null;             // R² del PPTO y del aforo para comparar con el del modelo (referencias.json, referencias_r2.py); opcional
let vistaActual = '';

// ---------------------------------------------------------------- formatos
const nf = (v, d = 1) => v == null || Number.isNaN(+v) ? '—'
  : (+v).toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
const sg = (v, d = 1) => v == null || Number.isNaN(+v) ? '—' : (v > 0.0049 ? '+' : v < -0.0049 ? '−' : '') + nf(Math.abs(v), d);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const MES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MC = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const fecha = iso => { if (!iso) return '—'; const [y, m, d] = iso.split('-'); return `${+d} ${MC[m - 1]} ${y}`; };
const mesAnio = ym => { if (!ym) return '—'; const [y, m] = ym.split('-'); return `${MC[m - 1]} ${y}`; };
const ANT = { 'manual': 'Manual', 'mecánica tras manual': 'Mecanizado, primera vez', 'mecánica seguida': 'Mecanizado, repetido',
  'mecánica, antes sin dato': 'Mecanizado', 'plantilla o sin dato': 'Plantilla o sin dato' };
const imp = ap => ap == null ? null : -ap;                 // aporte (TCH que quitó) → impacto en el TCH
const clsImp = v => v < -0.005 ? 't-q' : v > 0.005 ? 't-s' : '';
const hrefS = k => '#suerte/' + encodeURIComponent(k);
const corteTxt = s => s.f ? fecha(s.f) : MES[s.m - 1] + ' 2026';

// ---------------------------------------------------------------- gráficos (SVG al ancho real del contenedor)
function ticks(lo, hi, n = 5) {
  const span = hi - lo || 1, paso0 = span / n, mag = 10 ** Math.floor(Math.log10(paso0));
  const paso = [1, 2, 2.5, 5, 10].map(f => f * mag).find(p => span / p <= n) || 10 * mag;
  const out = [];
  for (let v = Math.floor(lo / paso) * paso; v <= hi + paso * 1e-9; v += paso) out.push(+v.toFixed(10));
  return out;
}

function grafico(el, o) {
  const W = Math.max(260, el.clientWidth || 600), H = o.alto || 230;
  const m = { l: o.ml || 46, r: 14, t: 14, b: o.mb || 36 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b, n = o.x.length;
  const vals = o.series.flatMap(s => s.valores).filter(v => v != null && !Number.isNaN(v));
  (o.lineasH || []).forEach(l => vals.push(l.v));
  let lo = o.ymin ?? Math.min(0, ...vals), hi = o.ymax ?? Math.max(...vals, 0);
  if (o.ymax == null) hi += (hi - lo) * 0.08 || 1;
  if (o.ymin == null && lo < 0) lo -= (hi - lo) * 0.06;
  const tk = ticks(lo, hi, o.nt || 5);
  if (o.ymin == null) lo = Math.min(lo, tk[0]);
  if (o.ymax == null) hi = Math.max(hi, tk[tk.length - 1]);
  const Y = v => o.invertir ? m.t + (v - lo) / (hi - lo) * ih : m.t + ih - (v - lo) / (hi - lo) * ih;
  const bw = iw / n, X = i => m.l + bw * (i + 0.5);
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="${esc(o.titulo || '')}">`;
  (o.bandas || []).forEach(b => {
    const y1 = Y(b.desde), y2 = Y(b.hasta);
    s += `<rect x="${m.l}" y="${Math.min(y1, y2)}" width="${iw}" height="${Math.abs(y2 - y1)}" style="fill:${b.color}" opacity=".16"/>`;
    if (b.et) s += `<text x="${m.l + iw - 4}" y="${Math.min(y1, y2) + 13}" text-anchor="end" style="font-size:11px">${esc(b.et)}</text>`;
  });
  tk.filter(v => v >= Math.min(lo, hi) - 1e-9 && v <= Math.max(lo, hi) + 1e-9).forEach(v => {
    s += `<line class="rej" x1="${m.l}" x2="${m.l + iw}" y1="${Y(v)}" y2="${Y(v)}"/>`;
    s += `<text x="${m.l - 6}" y="${Y(v) + 4}" text-anchor="end">${(o.yfmt || (x => nf(x, Math.abs(x) < 10 && x % 1 ? 1 : 0)))(v)}</text>`;
  });
  if (lo < 0 && hi > 0 && !o.invertir) s += `<line class="eje" x1="${m.l}" x2="${m.l + iw}" y1="${Y(0)}" y2="${Y(0)}"/>`;
  (o.marcasX || []).forEach(mk => {
    const x = m.l + bw * mk.i;
    s += `<line x1="${x}" x2="${x}" y1="${m.t}" y2="${m.t + ih}" style="stroke:var(--ink-2)" stroke-dasharray="3 3"/>`;
    s += `<text x="${x + 4}" y="${m.t + 11}" style="font-size:11px;fill:var(--ink-2)">${esc(mk.et)}</text>`;
  });
  const barras = o.series.filter(se => (se.tipo || 'barra') === 'barra');
  const nb = barras.length, gw = bw * (o.anchoBarra || 0.78), w1 = gw / Math.max(nb, 1);
  barras.forEach((se, j) => se.valores.forEach((v, i) => {
    if (v == null || Number.isNaN(v)) return;
    const x = X(i) - gw / 2 + j * w1, y0 = Y(o.invertir ? lo : Math.max(lo, 0)), y1 = Y(v);
    const col = se.colores ? se.colores[i] : se.color;
    s += `<rect x="${x + 0.5}" y="${Math.min(y0, y1)}" width="${Math.max(1, w1 - 1)}" height="${Math.max(1, Math.abs(y1 - y0))}" style="fill:${col}" rx="1"><title>${esc(o.x[i])}: ${nf(v, se.d ?? 1)}</title></rect>`;
    if (se.etiquetas) s += `<text x="${x + w1 / 2}" y="${(v >= 0 ? Math.min(y0, y1) - 4 : Math.max(y0, y1) + 12)}" text-anchor="middle" style="font-size:11px;fill:var(--ink-2)">${nf(v, se.d ?? 0)}</text>`;
  }));
  (o.lineasH || []).forEach(l => {
    s += `<line x1="${m.l}" x2="${m.l + iw}" y1="${Y(l.v)}" y2="${Y(l.v)}" style="stroke:${l.color}" stroke-width="2" ${l.dash ? 'stroke-dasharray="6 4"' : ''}/>`;
    if (l.et) s += `<text x="${m.l + 4}" y="${Y(l.v) - 5}" style="font-size:11px;fill:${l.color}">${esc(l.et)}</text>`;
  });
  o.series.filter(se => se.tipo === 'linea').forEach(se => {
    let d = '', pen = false;
    se.valores.forEach((v, i) => {
      if (v == null || Number.isNaN(v)) { pen = false; return; }
      d += `${pen ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; pen = true;
    });
    s += `<path d="${d}" fill="none" style="stroke:${se.color}" stroke-width="${se.grosor || 2}" ${se.dash ? 'stroke-dasharray="5 4"' : ''} stroke-linejoin="round"/>`;
    if (se.puntos !== false) se.valores.forEach((v, i) => {
      if (v == null || Number.isNaN(v)) return;
      s += `<circle cx="${X(i)}" cy="${Y(v)}" r="${se.r || 2.6}" style="fill:${se.color}"><title>${esc(o.x[i])}: ${nf(v, se.d ?? 2)}</title></circle>`;
    });
  });
  const cada = Math.max(1, Math.ceil(n * (o.anchoEt || 46) / iw));
  o.x.forEach((t, i) => {
    if (i % cada && i !== n - 1) return;
    if (i === n - 1 && i % cada && (i % cada) < cada * 0.6) return;
    s += `<text x="${X(i)}" y="${H - m.b + 16}" text-anchor="middle" ${o.destacarX === i ? 'style="fill:var(--ink);font-weight:700"' : ''}>${esc(t)}</text>`;
  });
  if (o.ejeX) s += `<text x="${m.l + iw / 2}" y="${H - 4}" text-anchor="middle" style="font-size:11px">${esc(o.ejeX)}</text>`;
  s += `<line class="eje" x1="${m.l}" x2="${m.l + iw}" y1="${m.t + ih}" y2="${m.t + ih}"/></svg>`;
  el.innerHTML = s;
}

const leyenda = items => `<div class="leyenda">${items.map(([c, t, raya]) =>
  `<span><i class="${raya ? 'raya' : ''}" style="background:${c}"></i>${esc(t)}</span>`).join('')}</div>`;

// barras divergentes en HTML (se leen bien en el teléfono): filas [{et, v, dato, href, fuerte}]
function divergentes(filas, o = {}) {
  const mx = o.max || Math.max(0.5, ...filas.map(f => Math.abs(f.v || 0)));
  return `<div role="list" style="display:flex;flex-direction:column;gap:2px">${filas.map(f => {
    const w = Math.min(50, 50 * Math.abs(f.v || 0) / mx), neg = (f.v || 0) < 0;
    const barra = `<div style="position:relative;height:16px;background:linear-gradient(var(--line-2),var(--line-2)) 50% 0/1px 100% no-repeat">
      <div style="position:absolute;top:2px;height:12px;border-radius:2px;${neg ? `right:50%;` : `left:50%;`}width:${w}%;background:${f.color || (neg ? 'var(--quita)' : 'var(--suma)')}"></div></div>`;
    const et = f.href ? `<a href="${f.href}" style="text-decoration:none;font-weight:${f.fuerte ? 700 : 400}">${esc(f.et)}</a>` : `<span style="font-weight:${f.fuerte ? 700 : 400}">${esc(f.et)}</span>`;
    return `<div role="listitem" ${f.href ? `class="fila" tabindex="0" data-href="${f.href}"` : ''} style="display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr) 64px;gap:10px;align-items:center;padding:5px 6px;border-radius:4px">
      <div style="min-width:0">${et}${f.dato ? `<div style="font-size:12px;color:var(--muted);white-space:normal">${esc(f.dato)}</div>` : ''}</div>${barra}
      <div class="num ${clsImp(f.v)}" style="text-align:right">${sg(f.v, o.d ?? 1)}</div></div>`;
  }).join('')}</div>`;
}

function enlazarFilas(root) {
  root.querySelectorAll('[data-href]').forEach(el => {
    el.addEventListener('click', ev => { if (ev.target.closest('a')) return; location.hash = el.dataset.href; });
    el.addEventListener('keydown', ev => { if (ev.key === 'Enter') location.hash = el.dataset.href; });
  });
}

// tabla ordenable: cols [{t, f(row)→html, v(row)→valor para ordenar, n:bool}]
function tabla(el, cols, rows, o = {}) {
  let orden = o.orden ?? -1, dir = o.dir ?? -1;
  const pintar = () => {
    const rs = orden < 0 ? rows : [...rows].sort((a, b) => {
      const va = cols[orden].v(a), vb = cols[orden].v(b);
      if (va == null) return 1; if (vb == null) return -1;
      return (va > vb ? 1 : va < vb ? -1 : 0) * dir;
    });
    el.innerHTML = `<div class="tabla"><table><thead><tr>${cols.map((c, i) =>
      `<th class="${c.n ? 'n' : ''}" ${c.v ? `aria-sort="${i === orden ? (dir > 0 ? 'ascending' : 'descending') : 'none'}"` : ''}>${c.v ? `<button data-i="${i}">${esc(c.t)}${i === orden ? (dir > 0 ? ' ▲' : ' ▼') : ''}</button>` : esc(c.t)}</th>`).join('')}
      </tr></thead><tbody>${rs.map(r => `<tr tabindex="0" data-href="${hrefS(r.k)}">${cols.map(c =>
      `<td class="${c.n ? 'n' : ''}">${c.f(r)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
      <p class="sub" style="margin:6px 0 0">${rs.length} cosechas${o.pie ? ' · ' + o.pie : ''}</p>`;
    el.querySelectorAll('th button').forEach(b => b.onclick = () => {
      const i = +b.dataset.i; dir = i === orden ? -dir : (cols[i].asc ? 1 : -1); orden = i; pintar();
    });
    enlazarFilas(el);
  };
  pintar();
}

const barraImp = (v, mx) => `<span class="num ${clsImp(v)}">${sg(v, 1)}</span> <span class="barrita" style="width:${Math.round(46 * Math.min(1, Math.abs(v || 0) / mx))}px;background:${v < 0 ? 'var(--quita)' : 'var(--suma)'}"></span>`;
const colReal = [
  { t: 'Real', n: true, f: s => nf(s.real), v: s => s.real },
  { t: 'Historia', n: true, f: s => nf(s.hist), v: s => s.hist },
  { t: 'PPTO', n: true, f: s => nf(s.ppto), v: s => s.ppto },
];
const colSuerte = [
  { t: 'Suerte', f: s => `<a href="${hrefS(s.k)}"><b>${esc(s.s)}</b></a>${s.k.includes('(') ? ' (2)' : ''}`, v: s => s.s, asc: true },
  { t: 'Hacienda', f: s => esc(s.h), v: s => s.h, asc: true },
  { t: 'Corte', f: s => corteTxt(s), v: s => s.f || `2026-0${s.m}-15`, asc: true },
];

// ---------------------------------------------------------------- textos por causa para una suerte
function dato(id, s) {
  const mesN = MES[s.m - 1];
  switch (id) {
    case 'mecanica': return (s.tipo === 'Mecanizada' ? `Cosecha mecanizada${s.f ? ' el ' + fecha(s.f) : ''}` : 'Cosecha manual') +
      ` · corte anterior: ${ANT[s.ant] || s.ant}${s.ant_f ? ` (${mesAnio(s.ant_f)})` : ''}`;
    case 'corte-anterior': return `Corte anterior: ${ANT[s.ant] || s.ant}${s.ant_f ? ` (${mesAnio(s.ant_f)}${s.ant_tch ? ', ' + nf(s.ant_tch) + ' TCH' : ''})` : ''}`;
    case 'corte-humedo': return s.mmca == null ? 'Sin dato de lluvia del corte anterior' : `${nf(s.mmca, 0)} mm de lluvia en el mes del corte anterior${s.ant_f ? ' (' + mesAnio(s.ant_f) + ')' : ''}: suelo ${s.mmca >= 100 ? 'húmedo' : 'seco'} · EMA ${s.ema}`;
    case 'clima': return `${nf(s.d32, 0)} días >32 °C en los 30 días antes del corte (normal en ${mesN}: ${nf(s.d32n, 0)}); ` +
      (s.dsr == null ? 'sin dato de agua en ese ciclo' : `falta de agua del mes 8 a la cosecha ${nf(s.dsr, 0)} mm (normal: ${nf(s.dsrn, 0)})`) + ` · EMA ${s.ema}`;
    case 'riego': return s.rie == null ? 'Sin dato de riego en ese ciclo' : `Riego aplicado ${nf(s.rie, 0)} mm (normal en ${mesN}: ${nf(s.rien, 0)}); déficit que quedó ${nf(s.def, 0)} mm`;
    case 'freatico': return s.nf == null ? 'Sin pozo de observación a menos de 1,5 km con lecturas en el ciclo' :
      `Nivel promedio del ciclo ${nf(s.nf, 2)} m; 45 días antes del corte ${nf(s.nf45, 2)} m (normal en ${mesN}: ${nf(s.nfn, 2)} m)`;
    case 'lluvia': return `${nf(s.llu, 0)} mm en los meses 0-3 del ciclo (normal en ${mesN}: ${nf(s.llun, 0)} mm)`;
    case 'variedades': return `Variedad ${s.v}`;
    case 'edad': return `Cortada a los ${nf(s.ed)} meses`;
    case 'renovacion': return s.nr ? 'Estaba en el plan de renovación 2025 y siguió como soca' : 'No estaba pendiente de renovar';
    case 'roturacion': return s.rot ? `Roturación ${s.rot} (según ${s.rot_de === 'control' ? 'el control de roturación' : 'SimpleAgri'})${s.mmrot != null ? `; lluvia en los 5 días antes: ${nf(s.mmrot, 0)} mm` : ''}` : 'Sin dato de labores (plantilla o sin registro)';
    case 'malezas': return s.dmal != null ? `Primer herbicida a los ${s.dmal} días del corte` : 'Sin registro del herbicida';
    case 'fertilizacion': return s.dfert != null ? `Fertilización a los ${s.dfert} días del corte${s.mmfert != null ? `; lluvia en los 5 días antes: ${nf(s.mmfert, 0)} mm` : ''}` : 'Sin registro de la fertilización';
    case 'corte': return `Corte número ${s.c}`;
    case 'incendio': return s.inc ? 'Cosecha forzada por incendio' : 'Sin incendio';
  }
  return '';
}

const COLS = {
  'mecanica': [{ t: 'Tipo 2026', f: s => `<span class="chip ${s.tipo === 'Mecanizada' ? 'mec' : ''}">${esc(s.tipo)}</span>`, v: s => s.tipo },
    { t: 'Corte anterior', f: s => `${esc(ANT[s.ant] || s.ant)} · ${mesAnio(s.ant_f)}`, v: s => s.ant }],
  'corte-anterior': [{ t: 'Corte anterior', f: s => `<span class="chip ${s.ant.startsWith('mec') ? 'mec' : ''}">${esc(ANT[s.ant] || s.ant)}</span>`, v: s => s.ant },
    { t: 'Fecha', f: s => mesAnio(s.ant_f), v: s => s.ant_f }, { t: 'TCH corte anterior', n: true, f: s => nf(s.ant_tch), v: s => s.ant_tch },
    { t: 'Tipo 2026', f: s => esc(s.tipo), v: s => s.tipo }],
  'corte-humedo': [{ t: 'Corte anterior', f: s => mesAnio(s.ant_f), v: s => s.ant_f }, { t: 'Lluvia del mes (mm)', n: true, f: s => nf(s.mmca, 0), v: s => s.mmca },
    { t: 'Suelo', f: s => s.mmca == null ? '—' : (s.mmca >= 100 ? '<span class="chip mec">Húmedo</span>' : 'Seco'), v: s => s.mmca }],
  'clima': [{ t: 'Días >32 °C', n: true, f: s => nf(s.d32, 0), v: s => s.d32 }, { t: 'Normal', n: true, f: s => nf(s.d32n, 0), v: s => s.d32n },
    { t: 'Falta de agua (mm)', n: true, f: s => nf(s.dsr, 0), v: s => s.dsr }, { t: 'Normal', n: true, f: s => nf(s.dsrn, 0), v: s => s.dsrn }],
  'riego': [{ t: 'Riego (mm)', n: true, f: s => nf(s.rie, 0), v: s => s.rie }, { t: 'Normal', n: true, f: s => nf(s.rien, 0), v: s => s.rien },
    { t: 'Déficit que quedó (mm)', n: true, f: s => nf(s.def, 0), v: s => s.def }],
  'freatico': [{ t: 'Nivel del ciclo (m)', n: true, f: s => nf(s.nf, 2), v: s => s.nf, asc: true }, { t: '45 días antes (m)', n: true, f: s => nf(s.nf45, 2), v: s => s.nf45, asc: true },
    { t: 'Normal (m)', n: true, f: s => nf(s.nfn, 2), v: s => s.nfn }, { t: 'Pozo', n: true, f: s => (F[s.k] && F[s.k].fre && F[s.k].fre.pozo) || '—', v: s => F[s.k] && F[s.k].fre && F[s.k].fre.pozo }],
  'lluvia': [{ t: 'Lluvia meses 0-3 (mm)', n: true, f: s => nf(s.llu, 0), v: s => s.llu }, { t: 'Normal', n: true, f: s => nf(s.llun, 0), v: s => s.llun }],
  'variedades': [{ t: 'Variedad', f: s => esc(s.v), v: s => s.v, asc: true }],
  'edad': [{ t: 'Edad (meses)', n: true, f: s => nf(s.ed), v: s => s.ed }],
  'renovacion': [{ t: 'Renovación pendiente', f: s => s.nr ? 'Sí' : 'No', v: s => s.nr }],
  'roturacion': [{ t: 'Roturación', f: s => esc(s.rot || 'sin dato'), v: s => s.rot }, { t: 'Fuente', f: s => esc(s.rot_de || ''), v: s => s.rot_de }],
  'malezas': [{ t: 'Días al herbicida', n: true, f: s => nf(s.dmal, 0), v: s => s.dmal }],
  'fertilizacion': [{ t: 'Días a la fertilización', n: true, f: s => nf(s.dfert, 0), v: s => s.dfert }],
  'corte': [{ t: 'N° de corte', n: true, f: s => s.c, v: s => s.c }],
  'incendio': [{ t: 'Incendio', f: s => s.inc ? 'Sí' : 'No', v: s => s.inc }],
};

// ---------------------------------------------------------------- filtros (los mismos en Resumen y Suertes; cada vista guarda los suyos)
const FILTRO0 = { q: '', h: '', z: '', za: '', v: '', t: '', m: '' };
const SIN = '(sin dato)';                                  // variedad o zona agroecológica vacía en el Maestro
const valV = s => s.v || SIN, valZA = s => s.za || SIN;
const ordenZA = (a, b) => a === SIN ? 1 : b === SIN ? -1 : parseInt(a) - parseInt(b) || a.localeCompare(b);   // 1H1, 1H2, 4H1… 23H1
const ordenV = (a, b) => (a === SIN) - (b === SIN) || (a === 'VARIAS') - (b === 'VARIAS') || a.localeCompare(b);
function filtrosHtml(f) {
  const hac = [...new Set(S.map(s => s.h).filter(Boolean))].sort();
  const zas = [...new Set(S.map(valZA))].sort(ordenZA), vs = [...new Set(S.map(valV))].sort(ordenV);
  const op = (v, t, sel) => `<option value="${esc(v)}"${v === sel ? ' selected' : ''}>${esc(t)}</option>`;
  return `<div class="filtros">
      <input id="q" type="search" placeholder="Buscar suerte o hacienda" aria-label="Buscar suerte o hacienda" value="${esc(f.q)}">
      <label>Hacienda <select id="fh">${op('', 'Todas', f.h)}${hac.map(h => op(h, h, f.h)).join('')}</select></label>
      <label>Zona <select id="fz">${op('', 'Todas', f.z)}${op('1', '1', f.z)}${op('2', '2', f.z)}</select></label>
      <label>Zona agroecológica <select id="fza">${op('', 'Todas', f.za)}${zas.map(z => op(z, z, f.za)).join('')}</select></label>
      <label>Variedad <select id="fv">${op('', 'Todas', f.v)}${vs.map(v => op(v, v, f.v)).join('')}</select></label>
      <label>Cosecha <select id="ft">${op('', 'Todas', f.t)}${op('Mecanizada', 'Mecanizada', f.t)}${op('Manual', 'Manual', f.t)}</select></label>
      <label>Mes <select id="fm">${op('', 'Todos', f.m)}${MES.slice(0, 9).map((m, i) => op(String(i + 1), m, f.m)).join('')}</select></label>
    </div>`;
}
const leerFiltros = () => ({ q: document.getElementById('q').value.trim().toLowerCase(), h: document.getElementById('fh').value,
  z: document.getElementById('fz').value, za: document.getElementById('fza').value, v: document.getElementById('fv').value,
  t: document.getElementById('ft').value, m: document.getElementById('fm').value });
const filtrar = f => S.filter(s => (!f.q || s.s.includes(f.q) || s.h.toLowerCase().includes(f.q)) && (!f.h || s.h === f.h) &&
  (!f.z || String(s.z) === f.z) && (!f.za || valZA(s) === f.za) && (!f.v || valV(s) === f.v) &&
  (!f.t || s.tipo === f.t) && (!f.m || String(s.m) === f.m));
const escucharFiltros = fn => ['q', 'fh', 'fz', 'fza', 'fv', 'ft', 'fm'].forEach(i => document.getElementById(i).addEventListener('input', fn));

// promedios ponderados por área de un grupo de cosechas (los mismos cálculos de informe_datos.py: sin filtro dan resumen.json)
function agregado(rows) {
  const pond = (L, fn) => { const a = L.reduce((x, s) => x + s.a, 0); return a ? L.reduce((x, s) => x + fn(s) * s.a, 0) / a : null; };
  const h = rows.filter(s => s.hist != null), p = h.filter(s => s.ppto != null);
  const ha = h.reduce((x, s) => x + s.a, 0), hist = pond(h, s => s.hist), caida = pond(h, s => s.caida);
  const ap = {};
  C.causas.forEach(c => ap[c.id] = pond(h, s => s.ap[c.id] || 0));
  return { n: rows.length, cosechas: h.length, ha, hist, real: pond(h, s => s.real), caida, caida_pct: hist ? -100 * caida / hist : null,
    t_caida: h.reduce((x, s) => x + s.caida * s.a, 0), sin_explicar: pond(h, s => s.se), ap,
    puente: { cosechas: p.length, ha: p.reduce((x, s) => x + s.a, 0), ppto: pond(p, s => s.ppto), hist: pond(p, s => s.hist), real: pond(p, s => s.real),
      t: p.reduce((x, s) => x + (s.ppto - s.real) * s.a, 0) } };
}

function textoFiltro(f) {
  const t = [];
  if (f.q) t.push(`«${f.q}»`);
  if (f.h) t.push(`hacienda ${f.h}`);
  if (f.z) t.push(`zona ${f.z}`);
  if (f.za) t.push(`zona agroecológica ${f.za}`);
  if (f.v) t.push(`variedad ${f.v}`);
  if (f.t) t.push(`cosecha ${f.t.toLowerCase()}`);
  if (f.m) t.push(MES[f.m - 1]);
  return t.join(' · ');
}

// ---------------------------------------------------------------- vista: resumen
let filtroRes = { ...FILTRO0 };
function vResumen() {
  $app.innerHTML = `<div class="pila">
    <div><h2>¿Cuánto cayó el TCH y por qué?</h2><p class="sub" id="res-sub"></p></div>
    ${filtrosHtml(filtroRes)}<div id="res-cuerpo" class="pila"></div></div>`;
  const pintar = () => { filtroRes = leerFiltros(); pintarResumen(filtroRes); };
  escucharFiltros(pintar);
  pintarResumen(filtroRes);
}

function pintarResumen(f) {
  const filtrado = textoFiltro(f), A = agregado(filtrar(f)), P = A.puente;
  if (!filtrado) A.t_caida = R.t_caida;  // la caída por suerte viene redondeada: sin filtro, la cifra oficial
  const sub = document.getElementById('res-sub'), $c = document.getElementById('res-cuerpo');
  sub.innerHTML = filtrado
    ? `Filtro: <b>${esc(filtrado)}</b> · ${A.n} de ${S.length} cosechas; ${A.cosechas} con historia (${nf(A.ha, 0)} ha). Cada suerte se compara con su propio promedio 2020-25.
       <button type="button" id="res-limpiar" class="limpiar">Quitar filtros</button>`
    : `${A.cosechas} cosechas de ${R.periodo} con historia (${nf(A.ha, 0)} ha). Cada suerte se compara con su propio promedio 2020-25.`;
  const lim = document.getElementById('res-limpiar');
  if (lim) lim.onclick = () => { filtroRes = { ...FILTRO0 }; vResumen(); };
  if (!A.cosechas) {
    $c.innerHTML = `<div class="nota">Ninguna cosecha con historia 2020-25 cumple el filtro${A.n ? ` (las ${A.n} que lo cumplen no tienen con qué compararse)` : ''}.</div>`;
    return;
  }
  const subio = A.caida < 0, sobrePPTO = P.cosechas && P.t < 0;
  const filas = C.causas.map(c => ({ et: c.nombre, v: -A.ap[c.id], href: '#causa/' + c.id, g: c.grupo }))
    .filter(x => Math.abs(x.v) >= 0.05).sort((a, b) => a.v - b.v);
  filas.push({ et: 'Sin explicar', v: -A.sin_explicar, color: 'var(--hist)' });
  const grupos = {};
  C.causas.forEach(c => grupos[c.grupo] = (grupos[c.grupo] || 0) - A.ap[c.id]);
  const pocas = A.cosechas < 20
    ? `<div class="nota"><b>Pocas cosechas.</b> Son ${A.cosechas} cosechas con historia: el promedio depende mucho de unas pocas suertes y cada causa puede moverse bastante. Tómelo como orientación y revise las suertes una por una.</div>` : '';
  $c.innerHTML = `${pocas}
    <div class="kpis">
      <div class="kpi"><div class="et">Histórico 2020-25</div><div class="v num">${nf(A.hist)} <small>TCH</small></div></div>
      <div class="kpi ppto"><div class="et">Presupuesto 2026</div><div class="v num">${nf(P.ppto)} <small>TCH</small></div></div>
      <div class="kpi real"><div class="et">Real 2026</div><div class="v num">${nf(A.real)} <small>TCH</small></div></div>
      <div class="kpi ${subio ? 'subio' : 'caida'}"><div class="et">Toneladas ${subio ? 'ganadas' : 'perdidas'} frente al histórico</div>
        <div class="v num">${nf(Math.abs(A.t_caida), 0)} <small>t</small></div><div class="pie num">${sg(-A.caida)} TCH · ${sg(A.caida_pct)} %</div></div>
      <div class="kpi ${sobrePPTO ? 'subio' : 'caida'}"><div class="et">Toneladas ${sobrePPTO ? 'ganadas' : 'perdidas'} frente al presupuesto</div>
        <div class="v num">${P.cosechas ? nf(Math.abs(P.t), 0) : '—'} <small>t</small></div>
        <div class="pie num">${P.cosechas ? `${sg(P.real - P.ppto)} TCH · ${sg(100 * (P.real - P.ppto) / P.ppto)} %${P.cosechas < A.cosechas ? ` · ${P.cosechas} cosechas con presupuesto` : ''}` : 'Sin presupuesto en el Maestro'}</div></div>
    </div>
    <div class="grid2">
      <div class="caja"><h3>Lo que quitó y lo que sumó cada causa (TCH)</h3>
        <p class="sub" style="margin-bottom:8px">Toque una causa para ver sus suertes, sus datos y la gráfica de soporte${filtrado ? ' (la página de la causa muestra todas las suertes, sin este filtro)' : ''}.</p>
        ${divergentes(filas)}
        <p class="sub" style="margin:10px 0 0">Suman ${sg(-A.caida)} TCH: de ${nf(A.hist)} a ${nf(A.real)} TCH.</p></div>
      <div class="pila">
        <div class="caja"><h3>Contra el presupuesto</h3>${puentePPTO(P)}</div>
        <div class="caja"><h3>Por tipo de causa (TCH)</h3>
          ${divergentes(Object.entries(grupos).sort((a, b) => a[1] - b[1]).map(([g, v]) => ({ et: g, v })))}</div>
      </div>
    </div>
    <div class="nota"><b>Qué tan seguro es.</b> Con los datos de 2026, ${subio
      ? `en este grupo el TCH no cayó frente a la historia: las barras muestran qué le quitó y qué le sumó (quedan ${sg(-A.sin_explicar)} TCH sin explicar).`
      : A.sin_explicar >= 0 ? `las variables medidas explican el ${nf(100 * (1 - A.sin_explicar / A.caida), 0)} % de la caída promedio (quedan ${nf(A.sin_explicar)} TCH sin explicar).`
      : `las causas medidas suman ${nf(A.caida - A.sin_explicar)} TCH frente a ${nf(A.caida)} que cayó: dan cuenta de toda la caída promedio.`}
      La prueba dura es sin ver 2026: el modelo ajustado solo con 2011-2025 predijo el ${nf(prediccion().pct, 0)} % de la caída y,
      año por año desde 2013, se movió con lo real (correlación ${nf(V.corr, 2)})${filtrado ? '; esa prueba es del modelo con todas las suertes y no cambia con el filtro' : ''}.
      Suerte por suerte explica una parte; en cada ficha se ve cuánto queda sin explicar. <a href="#prueba">Ver la prueba</a></div>`;
  enlazarFilas($c);
}

function puentePPTO(P) {
  if (!P.cosechas) return '<p class="sub" style="margin:0">Ninguna de estas cosechas tiene PPTO en el Maestro de Suertes 2026.</p>';
  const brecha = P.ppto - P.real, sobre = P.ppto - P.hist, caida = P.hist - P.real;
  const mxp = Math.max(P.ppto, P.hist, P.real) * 1.02;
  const barraP = (et, v, col) => `<div style="display:grid;grid-template-columns:110px 1fr 56px;gap:10px;align-items:center;margin:4px 0">
    <span style="font-size:14px">${et}</span><div style="background:var(--surface-2);border-radius:3px"><div style="height:18px;width:${100 * v / mxp}%;background:${col};border-radius:3px"></div></div>
    <b class="num" style="text-align:right">${nf(v)}</b></div>`;
  // la barra partida solo tiene sentido cuando los dos tramos son brecha (PPTO ≥ historia ≥ real)
  const partida = brecha > 0 && sobre >= 0 && caida >= 0;
  return `<p class="sub" style="margin-bottom:8px">${P.cosechas} cosechas con PPTO en el Maestro de Suertes 2026 (columna AG) · ${nf(P.ha, 0)} ha</p>
    ${barraP('PPTO', P.ppto, 'var(--ppto-fill)')}${barraP('Historia', P.hist, 'var(--hist)')}${barraP('Real', P.real, 'var(--real)')}
    <div style="margin-top:12px;font-size:14px">${brecha >= 0 ? 'Brecha contra el PPTO' : 'Por encima del PPTO'}: <b class="num">${nf(Math.abs(brecha))} TCH</b></div>
    ${partida ? `<div style="display:flex;height:22px;border-radius:3px;overflow:hidden;margin:6px 0">
      <div style="width:${100 * sobre / brecha}%;background:var(--ppto-fill)" title="PPTO por encima de la historia"></div>
      <div style="width:${100 * caida / brecha}%;background:var(--quita)" title="Caída"></div></div>
    ${leyenda([['var(--ppto-fill)', `PPTO por encima de lo que esas suertes daban: ${nf(sobre)} TCH (${nf(100 * sobre / brecha, 0)} %)`],
      ['var(--quita)', `Caída real: ${nf(caida)} TCH (${nf(100 * caida / brecha, 0)} %)`]])}`
    : `<p style="margin:6px 0 0;font-size:14px">PPTO ${sobre >= 0 ? 'por encima' : 'por debajo'} de la historia: <b class="num">${nf(Math.abs(sobre))} TCH</b> ·
      real ${caida >= 0 ? 'por debajo' : 'por encima'} de la historia: <b class="num">${nf(Math.abs(caida))} TCH</b></p>`}
    <p class="sub" style="margin:10px 0 0">Las causas de campo explican la caída frente a la historia. El tramo del PPTO por encima de la historia no lo explica ninguna causa de campo: es cómo se armó el presupuesto.</p>`;
}

function prediccion() {
  const fac = V.v2.filter(f => !f[0].startsWith('Sin explicar')), se = V.v2.find(f => f[0].startsWith('Sin explicar'));
  const pred = fac.reduce((a, f) => a + f[1], 0), tot = pred + se[1];
  return { pred, tot, pct: 100 * pred / tot, fac, se: se[1] };
}

// ---------------------------------------------------------------- vista: causa
function soporte(id, el) {
  const sp = C.soporte[id];
  if (!sp) { el.innerHTML = '<p class="sub">Esta causa no tiene una gráfica aparte: el detalle está en la tabla de suertes.</p>'; return; }
  const bloques = [];
  const caja = (t, sub, ley) => { const id_ = 'g' + bloques.length; bloques.push(id_); return `<div><h3>${t}</h3>${sub ? `<p class="sub" style="margin-bottom:6px">${sub}</p>` : ''}<div id="${id_}"></div>${ley || ''}</div>`; };
  const meses = sp.meses ? sp.meses.map(r => MC[r[0] - 1]) : [];
  const porMes = (unid, d = 0) => ({ x: meses, series: [{ valores: sp.meses.map(r => r[2]), color: 'var(--hist)', d }, { valores: sp.meses.map(r => r[1]), color: 'var(--quita)', d }], ejeX: 'mes de cosecha', titulo: unid });
  const leyMes = leyenda([['var(--quita)', '2026'], ['var(--hist)', 'Normal 2020-25, mismo mes']]);
  let html = '', specs = [];
  if (id === 'mecanica') {
    const h26 = sp.ha.find(r => r[0] === 2026) || [];
    const pt = sp.partes || {};
    html = (pt['este corte'] != null ? `<p>Esta causa suma la cosecha mecanizada de 2026 (${sg(-pt['este corte'], 2)} TCH) y la cepa que dejó el corte anterior mecanizado
      (${sg(-pt['corte anterior'], 2)} TCH). El modelo mide las dos por separado y aquí se suman.</p>` : '') + caja('Área con cosecha mecanizada (ha)', `Riopaila, por año de cosecha (2026 = enero a septiembre: ${nf(h26[1], 0)} ha de ${nf(h26[2], 0)} cosechadas)`) +
      caja('Cuánto rindió la cosecha mecanizada frente a la manual (TCH)', 'Misma suerte, mismo año; efecto del modelo llevado a TCH con el TCH promedio de la cosecha manual de cada año') + seg('Cosecha') +
      (sp.alerta2027 ? satAlerta(sp.alerta2027) : '');
    specs = [{ x: sp.ha.map(r => r[0]), series: [{ valores: sp.ha.map(r => r[1]), colores: sp.ha.map(r => r[0] === 2026 ? 'var(--quita)' : 'var(--hist)'), etiquetas: true, d: 0 }], destacarX: sp.ha.length - 1, yfmt: v => nf(v, 0), anchoEt: 40 },
      { x: sp.brecha_tch.map(r => r[0]), series: [{ valores: sp.brecha_tch.map(r => r[1]), colores: sp.brecha_tch.map(r => r[0] === 2026 ? 'var(--quita)' : 'var(--hist)'), etiquetas: true, d: 1 }], alto: 200 }];
  }
  if (id === 'mecanica') {          // la cepa que deja el corte anterior: va dentro de la causa (28-oct)
    const sp2 = C.soporte['corte-anterior'];
    const mx = Math.max(...sp2.tabla.map(r => Math.abs(r[4])));
    html += `<div><h3>La cepa que deja el corte anterior</h3><p>Esta causa incluye la soca que sale de un corte mecanizado (${sg(-sp2.t_ha, 2)} TCH de la causa). ${esc(sp2.efecto)}</p></div>
      <div><h3>Suertes cosechadas en 2026 frente a su propia historia 2015-25, según cómo fue el corte anterior (TCH)</h3>
      ${divergentes(sp2.tabla.map(r => ({ et: `${ANT[r[0]] || r[0]} · ${r[1]} cosechas · ${nf(r[2], 0)} ha`, v: r[4], color: r[0].startsWith('mec') ? 'var(--quita)' : r[4] < 0 ? 'var(--hist)' : 'var(--suma)' })), { max: mx })}
      <p class="sub" style="margin-top:6px">Cambio del TCH frente a la historia de cada suerte. Las que venían de un corte mecanizado cayeron casi el doble.</p></div>` +
      caja('El satélite lo ve: NDVI de la soca frente a la que salió de corte manual', 'Diferencia por mes de edad, misma suerte y mismo mes del año (3.500 ciclos 2019-2026)',
        leyenda([['var(--quita)', 'Corte anterior mecanizado, primera vez', 1], ['var(--mec)', 'Mecanizado repetido', 1]])) +
      caja('NDMI (humedad del follaje), igual', '', leyenda([['var(--quita)', 'Primera vez', 1], ['var(--mec)', 'Repetido', 1]])) +
      (sp2.cosecha2026 ? satCosecha(sp2.cosecha2026) : '') + ejemplo();
    const x = sp2.sat.map(r => r[0] + ' m');
    specs.push({ x, series: [{ tipo: 'linea', valores: sp2.sat.map(r => r[1]), color: 'var(--quita)', d: 3 }, { tipo: 'linea', valores: sp2.sat.map(r => r[2]), color: 'var(--mec)', dash: true, d: 3 }], yfmt: v => nf(v, 2), ejeX: 'meses de edad de la soca', alto: 210 },
      { x, series: [{ tipo: 'linea', valores: sp2.sat.map(r => r[3]), color: 'var(--quita)', d: 3 }, { tipo: 'linea', valores: sp2.sat.map(r => r[4]), color: 'var(--mec)', dash: true, d: 3 }], yfmt: v => nf(v, 2), ejeX: 'meses de edad de la soca', alto: 210 });
  } else if (id === 'clima') {
    const ar = sp.area, pm = (m, d = 0) => ({ x: m.meses.map(r => MC[r[0] - 1]), series: [{ valores: m.meses.map(r => r[2]), color: 'var(--hist)', d }, { valores: m.meses.map(r => r[1]), color: 'var(--quita)', d }], ejeX: 'mes de cosecha' });
    html = `<div class="pila"><h3 style="margin:0">Una sola causa: calor y sequía al final del ciclo</h3>
      <p>Son dos condiciones del clima al cerrar el ciclo. El <b>calor</b> cuenta los días con más de 32 °C en los 30 días antes del corte: la caña transpira y respira más y pierde peso.
        La <b>sequía</b> cuenta el agua que faltó (evaporación menos lluvia, sin contar el riego) del mes 8 a la cosecha: la caña llena menos el tallo.
        En 2026 el calor le quitó ${sg(-sp.tch[0], 2)} TCH y la sequía ${sg(-sp.tch[1], 2)} TCH: juntas, ${sg(-(sp.tch[0] + sp.tch[1]), 2)} TCH.</p>
      <p><b>Por qué se pueden sumar sin contar dos veces.</b> El modelo mide las dos al mismo tiempo, así que el efecto de cada una ya descuenta a la otra. Además se probó si un mes
        caliente y seco resta más que la suma de los dos, y no (p 0,35). Lo que sí se repetía era el <b>área</b>: separadas, el calor le quitó más de 0,5 TCH a ${ar.calor[0]} cosechas
        (${nf(ar.calor[1], 0)} ha) y la sequía a ${ar.sequia[0]} (${nf(ar.sequia[1], 0)} ha), pero ${ar.las_dos[0]} cosechas (${nf(ar.las_dos[1], 0)} ha) estaban en las dos.
        Unidas, le quitaron más de 0,5 TCH a <b>${ar.unidas[0]} cosechas (${nf(ar.unidas[1], 0)} ha)</b> de ${ar.total[0]} (${nf(ar.total[1], 0)} ha), cada una contada una vez.</p>
      <p class="nota" style="margin:0">El riego cubre parte de la falta de agua y va aparte, en «Riego aplicado», porque es lo que se puede manejar.</p></div>` +
      caja('Días con más de 32 °C en los 30 días antes del corte', 'Promedio de las cosechas de cada mes', leyMes) +
      caja('Días con más de 32 °C por mes · EMA La Paila', 'Desde julio de 2024; la línea es el promedio 2011-25 de ese mes', leyenda([['var(--quita)', 'Ese mes'], ['var(--ink-2)', 'Normal', 1]])) +
      caja('Falta de agua sin riego del mes 8 a la cosecha (mm)', 'Promedio de las cosechas de cada mes; normal = 2022-25 (años con registro de riego)', leyMes);
    specs = [{ ...pm(sp.calor), titulo: 'días' }, { x: sp.calor.ema.map(r => mesAnio(r[0])), series: [{ valores: sp.calor.ema.map(r => r[1]), color: 'var(--quita)', d: 0 }, { tipo: 'linea', valores: sp.calor.ema.map(r => r[2]), color: 'var(--ink-2)', dash: true, puntos: false }], anchoEt: 56 },
      { ...pm(sp.sequia), titulo: 'mm' }];
  } else if (id === 'lluvia') {
    html = caja('Lluvia de los meses 0-3 del ciclo (mm)', 'Promedio de las cosechas de cada mes', leyMes) +
      caja('Lluvia por mes · EMA La Paila (mm)', 'Desde julio de 2024; la línea es el promedio 2011-25 de ese mes', leyenda([['var(--hist)', 'Ese mes'], ['var(--ink-2)', 'Normal', 1]]));
    specs = [porMes('mm'), { x: sp.ema.map(r => mesAnio(r[0])), series: [{ valores: sp.ema.map(r => r[1]), color: 'var(--hist)', d: 0 }, { tipo: 'linea', valores: sp.ema.map(r => r[2]), color: 'var(--ink-2)', dash: true, puntos: false }], anchoEt: 56 }];
  } else if (id === 'riego') {
    html = caja('Lámina de riego al final del ciclo (mm)', 'Promedio de las cosechas de cada mes; normal = 2022-25 (años con registro de riego)', leyMes);
    specs = [porMes('mm')];
  } else if (id === 'freatico') {
    html = caja('Área de Riopaila con el nivel freático a menos de 1 m (ha)', 'Cada lectura quincenal de los pozos de observación, interpolada a cada suerte') +
      caja('Nivel promedio del ciclo de las suertes cosechadas (m)', 'Promedio de las cosechas de cada mes; normal = 2022-25', leyMes);
    const t = sp.tiempo;
    specs = [{ x: t.map(r => fecha(r[0]).split(' ').slice(1).join(' ')), series: [{ valores: t.map(r => r[3]), color: 'var(--quita)', d: 0 }], anchoBarra: 0.9, anchoEt: 64, yfmt: v => nf(v, 0) },
      { ...porMes('m', 2), yfmt: v => nf(v, 1) }];
  } else if (id === 'variedades') {
    const leyHa = leyenda([['var(--quita)', '2026'], ['var(--hist)', 'Normal: abanico varietal de 2020-25 en la misma área de 2026']]);
    html = porQueVariedad(sp) + caja('Área cosechada por variedad (ha)', 'Enero a septiembre de 2026 frente al abanico varietal de 2020-25 llevado al área cosechada en 2026', leyHa);
    specs = [{ x: sp.v.map(r => r[0].replace('CC ', '')), series: [{ valores: sp.v.map(r => r[4]), color: 'var(--hist)', d: 0 }, { valores: sp.v.map(r => r[3]), color: 'var(--quita)', d: 0 }], anchoEt: 64, yfmt: v => nf(v, 0) }];
  } else if (id === 'corte-humedo') {
    html = caja('Área cuyo corte anterior se hizo con el suelo húmedo (ha)', `Mes del corte con 100 mm de lluvia o más · por año de cosecha (2026 = enero a septiembre). Lluvia promedio en el mes del corte anterior: 2026 ${nf(sp.mm[0], 0)} mm, normal ${nf(sp.mm[1], 0)} mm`);
    specs = [{ x: sp.ha.map(r => r[0]), series: [{ valores: sp.ha.map(r => r[1]), colores: sp.ha.map(r => r[0] === 2026 ? 'var(--quita)' : 'var(--hist)'), etiquetas: true, d: 0 }], destacarX: sp.ha.length - 1, yfmt: v => nf(v, 0), anchoEt: 40 }];
  } else if (id === 'corte') {
    const leyHa = leyenda([['var(--quita)', '2026'], ['var(--hist)', 'Normal: mezcla de 2020-25 en la misma área de 2026']]);
    html = porQueCorte(sp) +
      caja('Lo que pierde la soca en cada corte (TCH frente a la plantilla)', `Misma suerte; efecto medido en 7.433 cosechas 2011-2026, llevado a TCH con el TCH promedio de las plantillas 2020-25 (${nf(sp.plantilla_tch)} TCH)`) +
      caja('Área cosechada por número de corte (ha)', `Promedio: 2026 ${nf(sp.prom[0])} cortes · normal ${nf(sp.prom[1])} cortes. Más segundos cortes y menos socas de 6 o más.`, leyHa);
    specs = [{ x: sp.efecto.map(r => r[0]), series: [{ valores: sp.efecto.map(r => r[2]), color: 'var(--quita)', etiquetas: true, d: 1 }], yfmt: v => nf(v, 0), alto: 210 },
      { x: sp.mezcla.map(r => r[0]), series: [{ valores: sp.mezcla.map(r => r[4]), color: 'var(--hist)', d: 0 }, { valores: sp.mezcla.map(r => r[3]), color: 'var(--quita)', d: 0 }], anchoEt: 64, yfmt: v => nf(v, 0) }];
  } else if (id === 'edad') {
    const leyHa = leyenda([['var(--quita)', '2026'], ['var(--hist)', 'Normal: mezcla de 2020-25 en la misma área de 2026']]);
    html = caja('Área cosechada por edad (ha)', `Edad promedio: 2026 ${nf(sp.prom[0])} meses · normal ${nf(sp.prom[1])} meses`, leyHa);
    specs = [{ x: sp.e.map(r => r[0]), series: [{ valores: sp.e.map(r => r[4]), color: 'var(--hist)', d: 0 }, { valores: sp.e.map(r => r[3]), color: 'var(--quita)', d: 0 }], ejeX: 'meses', yfmt: v => nf(v, 0) }];
  }
  el.innerHTML = `<div class="pila">${html}</div>`;
  bloques.forEach((b, i) => specs[i] && grafico(document.getElementById(b), specs[i]));
  const ta = document.getElementById('t-alerta');
  if (ta) {
    const rows = sp.alerta2027.suertes.map(([ste, f2, edad, dn, dr]) => {
      const s = S.find(x => x.s === ste && x.tipo === 'Mecanizada') || S.find(x => x.s === ste);
      return { k: s ? s.k : ste, ste, h: s ? s.h : '', f2, edad, dn, dr, foto: !!(s && s.satB) };
    });
    tabla(ta, [{ t: 'Suerte', f: r => `<a href="${hrefS(r.k)}"><b>${esc(r.ste)}</b></a>`, v: r => r.ste, asc: true },
      { t: 'Hacienda', f: r => esc(r.h), v: r => r.h, asc: true },
      { t: 'Corte 2026 (satélite)', f: r => fecha(r.f2), v: r => r.f2, asc: true },
      { t: 'Edad comparada', n: true, f: r => r.edad + ' días', v: r => r.edad },
      { t: 'Cambio NDVI', n: true, f: r => `<span class="${r.dn < -0.03 ? 't-q' : ''}">${sg(r.dn, 2)}</span>`, v: r => r.dn, asc: true },
      { t: 'Cambio rebrote ralo', n: true, f: r => `<span class="${r.dr > 5 ? 't-q' : ''}">${sg(r.dr, 0)} pts</span>`, v: r => r.dr },
      { t: 'Imagen', f: r => r.foto ? 'sí' : '—', v: null }], rows, { pie: 'NDVI más bajo o rebrote más ralo que después del corte manual = peor' });
  }
}

// la sequía y el riego vistos con otra fuente: balance de Cenicaña desde 1993 y riegos en mm desde 2021 (pestaña de gerencia)
function balanceDoc() {
  if (!BL) return '';
  const pr = BL.pruebas, an = BL.anios.filter(r => r[0] >= 2015);
  const conf = x => x.p < 0.05 ? `sí (${x.p < 0.001 ? 'p < 0,001' : 'p = ' + nf(x.p, 3)})` : `no (p = ${nf(x.p, 2)})`;
  const tbl = (cab, filas, num) => `<div class="tabla"><table><thead><tr>${cab.map((c, i) => `<th class="${num.includes(i) ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${num.includes(i) ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  return `<p style="margin-top:10px"><b>Otra fuente lo confirma: el balance hídrico y el riego en milímetros.</b> Con el clima mensual de Cenicaña desde 1993
      (La Paila y Bugalagrande) se calculó, para ${nf(BL.cosechas, 0)} cosechas de 2011 a 2026, el agua que faltó del mes 8 del ciclo a la cosecha
      (lo que consume la caña, 0,8 × evaporación, menos la lluvia). Para ${nf(BL.cosechas_riego, 0)} cosechas se sumaron los mm de riego aplicados según el
      consolidado de riegos (${nf(BL.riegos, 0)} riegos de ${BL.riego_desde} a ${fecha(BL.riego_hasta)}). Cada suerte frente a sí misma, con los mismos controles del modelo:</p>
    ${tbl(['Prueba', 'Cosechas', 'Por cada 100 mm', '¿Confiable?'], pr.map(x => [esc(x.prueba), nf(x.n, 0),
      `<b class="${clsImp(x.tch)}">${sg(x.tch)} TCH</b> (${sg(x.pct)} %)`, conf(x)]), [1, 2])}
    ${tbl(['Año de cosecha', ...an.map(r => r[0])], [['Falta de agua al final del ciclo (mm)', ...an.map(r => nf(r[1], 0))],
      ['Riego aplicado al final del ciclo (mm)', ...an.map(r => r[2] == null ? '—' : nf(r[2], 0))]], an.map((_, i) => i + 1))}
    <p style="margin-top:8px">La falta de agua resta en todos los años desde 2011, regar recupera una parte pequeña por milímetro y lo que el riego no cubre es lo que más cuesta.
      Por eso el riego teórico tiene sentido, pero se debe medir en mm aplicados frente a la falta del balance: contando riegos (la hoja de riegos teóricos 2026)
      no aparece ningún efecto, porque un riego no es una cantidad fija de agua (de unos 25 a 60 mm según el año en este registro).
      Este balance es respaldo de la sequía y el riego, no una causa más: entrarlo al modelo contaría el agua dos veces.</p>
    <p class="sub" style="margin:4px 0 0">Lo que no demuestra: el balance es por estación y por mes (no por suerte), el consumo de la caña es un supuesto simple, el riego de 2026 llega
      hasta ${fecha(BL.riego_hasta)}, desde 2024 cada riego aparece con menos mm (posible cambio de registro, por confirmar con Recursos Hídricos) y se riega
      primero donde más falta hace, lo que puede hacer ver menor el efecto del riego. Efectos en TCH sobre el TCH normal 2020-25 (${nf(BL.tch_base)}).</p>`;
}

// por qué el número de corte sumó en 2026: cada suerte frente al corte promedio de su propia historia (lo usan la causa y la gerencia)
function porQueCorte(sp, enDoc) {
  if (!sp.grupos) return '';
  const tot = sp.grupos.reduce((x, g) => x + g[6], 0), ha = sp.grupos.reduce((x, g) => x + g[2], 0);
  const pl = sp.plantillas, e = sp.ejemplo, se = e && S.find(s => s.s === e[0]);
  const desde23 = pl.por_anio.reduce((x, r) => x + r[1], 0);
  const tabla = `<div class="tabla"><table><thead><tr><th>Cada suerte frente a su historia 2020-25</th><th class="n">Cosechas</th><th class="n">Área (ha)</th>
    <th class="n">Corte 2026</th><th class="n">Corte en su historia</th><th class="n">Le sumó o quitó (TCH)</th><th class="n">Toneladas</th></tr></thead><tbody>
    ${sp.grupos.map(g => `<tr><td>${esc(g[0])}</td><td class="n">${g[1]}</td><td class="n">${nf(g[2], 0)}</td><td class="n">${nf(g[3])}</td><td class="n">${nf(g[4])}</td>
      <td class="n"><b class="${clsImp(g[5])}">${sg(g[5])}</b></td><td class="n ${clsImp(g[6])}">${sg(g[6], 0)}</td></tr>`).join('')}
    <tr><td><b>Total</b></td><td class="n">${sp.grupos.reduce((x, g) => x + g[1], 0)}</td><td class="n">${nf(ha, 0)}</td><td></td><td></td>
      <td class="n"><b class="${clsImp(tot / ha)}">${sg(tot / ha)}</b></td><td class="n"><b class="${clsImp(tot)}">${sg(tot, 0)}</b></td></tr></tbody></table></div>`;
  const txt = `<p><b>Por qué sumó.</b> Cada suerte se compara consigo misma: su corte de 2026 frente al corte promedio que tuvo en 2020-25. Cada corte le quita TCH a la soca,
      así que una suerte que en 2026 está más joven que en su historia gana frente a su propio promedio, y una que está más vieja pierde.
      Las que envejecieron sí restaron, pero las renovadas sumaron más: el neto fue ${sg(tot, 0)} t, ${sg(tot / ha)} TCH en promedio.</p>
    ${tabla}
    <p style="margin-top:8px"><b>Por qué hubo tantas suertes jóvenes.</b> Por la renovación: de las ${pl.jovenes} cosechas más jóvenes que su historia, ${desde23} tuvieron una plantilla
      cosechada desde 2023 (${pl.por_anio.map(r => `${r[1]} en ${r[0]}`).join(', ')}). Por eso en 2026 se cosechó el doble de segundos cortes y la mitad de socas de 6º-7º que lo normal.</p>
    ${e ? `<p><b>Ejemplo:</b> la suerte ${se ? `<a href="${hrefS(se.k)}">${esc(e[0])}</a>` : esc(e[0])}${se && se.h ? ` (${esc(se.h)})` : ''} fue en 2020-25 una soca de ${e[1]} a ${e[2]} cortes
      con ${nf(e[3])} TCH en promedio; se renovó y en 2026 ${e[4] === 1 ? 'se cosechó la plantilla' : `se cosechó en ${e[4]}º corte`}: ${nf(e[5])} TCH. Solo por estar más joven, el modelo le atribuye ${sg(e[6])} TCH.</p>` : ''}
    <p${enDoc ? '' : ' class="nota" style="margin:0"'}><b>Lo que hay que leer.</b> Este ${sg(tot / ha)} TCH no es una mejora de manejo: es el ciclo de renovación, que rejuveneció el cañaduzal
      y tapó parte de la caída. Las suertes renovadas van a envejecer año tras año: si no se sigue renovando al mismo ritmo, este factor dejará de sumar y empezará a restar.</p>`;
  return enDoc ? txt : `<div class="pila"><h3 style="margin:0">Por qué el número de corte sumó en 2026</h3>${txt}</div>`;
}

// por qué restaron las variedades: cada suerte frente a su propia variedad de 2020-25; solo cuentan las que cambiaron de variedad
function porQueVariedad(sp, enDoc) {
  if (!sp.cambios) return '';
  const st = sp.sale_tot, cb = sp.cambiaron, misma = sp.grupos.find(g => g[0] === 'Mantuvieron su variedad');
  const nomV = v => v === 'VARIAS' ? 'varias variedades en la suerte' : v === 'otra' ? 'otras variedades de poca área' : esc(v);
  const fila = (et, n, ha, dif, ap) => `<tr><td>${et}</td><td class="n">${n}</td><td class="n">${nf(ha, 0)}</td>
    <td class="n">${dif == null ? '' : `<span class="${clsImp(dif)}">${sg(dif)} TCH</span>`}</td>
    <td class="n"><b class="${clsImp(ap)}">${sg(ap, 2)}</b></td><td class="n ${clsImp(ap)}">${sg(ap * R.ha, 0)}</td></tr>`;
  const tabla = `<div class="tabla"><table><thead><tr><th>Variedad en 2020-25 → variedad en 2026</th><th class="n">Cosechas</th><th class="n">Área (ha)</th>
    <th class="n">La nueva rinde frente a la anterior</th><th class="n">Le sumó o quitó (TCH)</th><th class="n">Toneladas</th></tr></thead><tbody>
    ${sp.cambios.map(r => { const [a, b] = r[0].split(' → '); return fila(`${esc(a)} → ${nomV(b)}`, r[1], r[2], r[3], r[4]); }).join('')}
    ${sp.grupos.map(g => fila(esc(g[0]), g[1], g[2], g[3], g[4])).join('')}
    <tr><td><b>Total de la causa</b></td><td></td><td></td><td></td><td class="n"><b class="${clsImp(sp.total)}">${sg(sp.total, 2)}</b></td>
      <td class="n"><b class="${clsImp(sp.total)}">${sg(sp.total * R.ha, 0)}</b></td></tr></tbody></table></div>`;
  const peor = sp.cambios[0];
  const txt = `<p><b>En una frase.</b> ${st[0]} cosechas (${nf(st[1], 0)} ha) que en 2020-25 eran ${esc(sp.sale)} se cosecharon en 2026 con otras variedades, y en esas mismas suertes
      las variedades nuevas rinden menos. Eso explica ${sg(st[2], 2)} TCH del promedio de Riopaila (${sg(st[2] * R.ha, 0)} t).</p>
    <p><b>Qué se compara.</b> Cada suerte contra sí misma: la variedad que se cosechó en 2026 frente a la que tuvo esa suerte en 2020-25. Cuánto rinde cada variedad
      se mide en la misma suerte a lo largo de los años, descontando edad, número de corte, clima y tipo de cosecha. Una suerte que mantuvo su variedad no suma ni resta por esta causa,
      aunque su variedad rinda menos que otras: eso ya está en su propia historia.</p>
    <p><b>Qué pasó.</b> ${cb[0]} de las ${cb[2]} cosechas con historia (${nf(cb[1], 0)} ha) cambiaron de variedad. Lo que pesa es la salida de ${esc(sp.sale)}:
      donde la reemplazaron ${nomV(peor[0].split(' → ')[1])}, la suerte rinde ${nf(Math.abs(peor[3]))} TCH menos que cuando era ${esc(sp.sale)}.
      Donde la reemplazó la CC 05-430 la diferencia es pequeña. Los demás cambios (de variedades viejas a CC 05-430, CC 11-595 y otras) casi se compensan.</p>
    ${tabla}
    <p${enDoc ? '' : ' class="nota" style="margin:0"'}><b>Lo que no demuestra.</b> Es una causa pequeña (${sg(sp.total, 2)} TCH). La diferencia entre dos variedades en una misma suerte
      tiene su margen de error, sobre todo en las de poca área. «Varias variedades» y «otras» son grupos, no una variedad. No dice que la CC 05-430 sea mala: donde reemplazó a la ${esc(sp.sale)}
      rinde casi lo mismo.${misma ? ` Las ${misma[1]} cosechas que mantuvieron su variedad aportan ${sg(misma[4], 2)} TCH porque en 2020-25 algunas tuvieron más de una variedad.` : ''}</p>`;
  return enDoc ? txt : `<div class="pila"><h3 style="margin:0">Por qué las variedades restaron en 2026</h3>${txt}</div>`;
}

// rebrote visto por el satélite: grupo frente a su control, a la misma edad de la soca
function satResumen(rows, etG, etC) {
  const nom = { ndvi: 'Vigor (NDVI)', ndmi: 'Humedad del follaje (NDMI)', rala: 'Rebrote ralo (% del área)' };
  const v = (k, x) => k === 'rala' ? sg(100 * x, 0) + ' pts' : sg(x, 2);
  const fs = rows.filter(r => nom[r[1]]);
  return `<div class="tabla"><table><thead><tr><th>Edad de la soca</th><th>Índice</th><th class="n">Suertes</th>
    <th class="n">${esc(etG)}</th><th class="n">${esc(etC)}</th><th class="n">Diferencia</th><th class="n">Empeoraron</th><th>Señal</th></tr></thead><tbody>
    ${fs.map(r => `<tr><td>${r[0]} días</td><td>${nom[r[1]]}</td><td class="n">${r[2]} · ${r[3]}</td><td class="n">${v(r[1], r[4])}</td>
      <td class="n">${v(r[1], r[5])}</td><td class="n"><b class="${(r[1] === 'rala' ? -r[6] : r[6]) < 0 ? 't-q' : 't-s'}">${v(r[1], r[6])}</b></td>
      <td class="n">${nf(r[8], 0)} % · ${nf(r[9], 0)} %</td><td>${Math.abs(r[7]) >= 2 ? 'clara' : 'débil'}</td></tr>`).join('')}
    </tbody></table></div>
    <p class="sub" style="margin:6px 0 0">Cambio = la soca después del corte nuevo menos la soca después del corte anterior, a la misma edad.
    Suertes y «Empeoraron»: grupo · control. NDVI y NDMI: negativo es peor. Rebrote ralo (área con NDVI menor de 0,6): positivo es peor.
    Señal clara = la diferencia supera dos errores estándar.</p>`;
}

function satCosecha(rows) {
  return `<div><h3>Toda la cosecha 2026: la soca después del corte manual y después del primer corte mecanizado</h3>
    <p class="sub" style="margin-bottom:8px">Suertes cosechadas en 2026 cuyo corte anterior fue el primero mecanizado. En cada una se compara la soca
    a la misma edad después del corte manual y después del mecanizado. El control son suertes con dos cortes manuales seguidos,
    para descontar el clima de cada año. Sentinel-2 con nubes filtradas (Cloud Score+).</p>
    ${satResumen(rows, 'Cambio: primer mecanizado', 'Cambio: manual seguido')}</div>`;
}

function satAlerta(a) {
  return `<div><h3>Alerta 2027: suertes cosechadas mecanizadas por primera vez en 2026</h3>
    <p class="sub" style="margin-bottom:8px">Su soca se cosecha en 2027. El satélite ya permite comparar su rebrote con el que tuvo después del
    último corte manual, a la misma edad. Control: suertes con corte manual en 2026 y en el corte anterior.</p>
    ${satResumen(a.resumen, 'Cambio: primer mecanizado', 'Cambio: manual seguido')}
    <h3 style="margin-top:14px">Suerte por suerte</h3>
    <p class="sub" style="margin-bottom:6px">${a.n ? `${a.suertes.length} de las ${a.n} ya tienen 60 días o más de rebrote para comparar; las demás se cosecharon hace poco. ` : ''}Ordenadas por la caída del vigor. Toque una suerte para ver su ficha con las dos imágenes.</p>
    <div id="t-alerta"></div></div>`;
}

// 2026 frente a la historia por grupo, en TCH: el % de la validación × el TCH histórico ponderado del grupo
function seg(dim) {
  const rows = V.segmentos.filter(r => r[0] === dim);
  const histG = g => { const L = S.filter(s => s.hist != null && (dim === 'Cosecha' ? s.tipo === g : true)), a = L.reduce((x, s) => x + s.a, 0);
    return a ? L.reduce((x, s) => x + s.hist * s.a, 0) / a : R.hist; };
  return `<div><h3>2026 frente a la historia, por tipo de cosecha (TCH)</h3>${divergentes(rows.map(r => { const h = histG(r[1]);
    return { et: `${r[1]} · ${r[2]} cosechas`, v: r[3] / 100 * h, dato: `el modelo sin ver 2026 predijo ${sg(r[4] / 100 * h)} TCH` }; }))}</div>`;
}

function ejemplo() {
  const e = Object.fromEntries(E.map(x => [x.escena, x]));
  const fig = (n, t) => `<figure><img src="img/bloque3501_${n}_ndvi.png" alt="NDVI del bloque 3501 el ${fecha(e[n].fecha)}" loading="lazy">
    <figcaption><b>${fecha(e[n].fecha)}</b> · ${esc(t)} · NDVI ${nf(e[n].ndvi, 2)} · NDMI ${nf(e[n].ndmi, 2)} · rebrote ralo ${nf(e[n].rala_pct, 0)} %</figcaption></figure>`;
  const sts = C.soporte['corte-anterior'].ejemplo.suertes;
  const filas = S.filter(s => sts.includes(s.s));
  return `<div><h3>Ejemplo: ${esc(C.soporte['corte-anterior'].ejemplo.titulo)}</h3>
    <p class="sub" style="margin-bottom:8px">Cosecha manual en julio de 2024, mecanizada por primera vez en julio de 2025 y otra vez mecanizada en julio de 2026.
    Imágenes Sentinel-2 (NDVI: café = suelo o caña rala, verde oscuro = caña cerrada) en la misma fecha del calendario, con la misma edad.</p>
    <div class="imgs">${fig('manual_100d', 'después del corte manual')}${fig('mecanica_100d', 'después del primer corte mecanizado')}
    ${fig('manual_150d', 'después del corte manual')}${fig('mecanica_150d', 'después del primer corte mecanizado')}</div>
    <p class="sub" style="margin-top:8px">Después del corte mecanizado la soca se ve más clara y con franjas a lo largo de los surcos, por donde pasan la cosechadora y los vagones.</p>
    <div id="ej-tabla"></div></div>`;
}

// el 100 % es la caída que se justifica (toneladas); las causas que sumaron TCH entran con % negativo.
// Lo usan la página de cada causa y la explicación para la gerencia.
function reparto100(actualId) {
  const tq = x => x.t_ha * R.ha, tSE = R.sin_explicar * R.ha;
  const base = C.causas.reduce((a, x) => a + tq(x), 0) + tSE, pc = t => 100 * t / base;
  const pcT = v => (v < -0.04 ? '−' : '') + nf(Math.abs(v), 1);
  const filas = [...C.causas].sort((a, b) => tq(b) - tq(a)).map(x => `<tr${x.id === actualId ? ' class="actual"' : ''}><td>${actualId === undefined ? esc(x.nombre) : `<a href="#causa/${x.id}">${esc(x.nombre)}</a>`}</td>
      <td class="n ${clsImp(-x.t_ha)}">${sg(-x.t_ha)}</td><td class="n">${sg(-tq(x), 0)}</td><td class="n"><b>${pcT(pc(tq(x)))} %</b></td></tr>`).join('') +
    `<tr><td>Sin explicar</td><td class="n">${sg(-R.sin_explicar)}</td><td class="n">${sg(-tSE, 0)}</td><td class="n"><b>${pcT(pc(tSE))} %</b></td></tr>
     <tr class="total"><td><b>Caída que se justifica</b></td><td class="n"><b>${sg(-R.caida)}</b></td><td class="n"><b>${sg(-R.t_caida, 0)}</b></td><td class="n"><b>100 %</b></td></tr>`;
  const actual = C.causas.find(x => x.id === actualId);
  return { pc: actual ? pc(tq(actual)) : null, filas,
    tabla: `<div class="tabla reparto"><table><thead><tr><th>Causa</th><th class="n">TCH</th><th class="n">Toneladas</th><th class="n">% de la caída</th></tr></thead><tbody>${filas}</tbody></table></div>` };
}

function vCausa(id) {
  const c = C.causas.find(x => x.id === id) || C.causas[0];
  const grupos = ['No controlable', 'Agronómico y operativo', 'Flujo de caja'];
  const lista = grupos.map(g => `<div class="g">${g}</div>` + C.causas.filter(x => x.grupo === g).sort((a, b) => b.t_ha - a.t_ha)
    .map(x => `<a href="#causa/${x.id}" ${x.id === c.id ? 'aria-current="true"' : ''}><span>${esc(x.nombre)}</span><span class="num ${clsImp(-x.t_ha)}">${sg(-x.t_ha, 2)}</span></a>`).join('')).join('');
  const conH = S.filter(s => s.hist != null);
  const mx = Math.max(0.5, ...conH.map(s => Math.abs(s.ap[c.id] || 0)));
  const nAf = conH.filter(s => (s.ap[c.id] || 0) > 0.5).length, nFa = conH.filter(s => (s.ap[c.id] || 0) < -0.5).length;
  const { pc: pcC, filas: reparto } = reparto100(c.id);
  $app.innerHTML = `<div class="causas"><nav class="lista-causas" aria-label="Causas">${lista}</nav>
    <section class="pila">
      <div class="caja"><span class="chip">${esc(c.grupo)}</span>
        <h2 style="margin-top:8px">${esc(c.nombre)}</h2>
        <div class="cifra num ${clsImp(-c.t_ha)}">${sg(-c.t_ha, 2)} TCH <span style="font-size:15px;font-weight:400;color:var(--muted)">en promedio · ${sg(-c.t_ha * R.ha, 0)} t en ${nf(R.ha, 0)} ha</span></div>
        <div class="peso100">${pcC >= 0 ? `Es el <b class="t-q">${nf(pcC, 1)} %</b> de la caída que se justifica`
          : `Compensó el <b class="t-s">${nf(-pcC, 1)} %</b> de la caída que se justifica`} (${nf(R.t_caida, 0)} t = 100 %)
          <div class="barra100" aria-hidden="true"><div style="width:${Math.min(100, Math.abs(pcC))}%;background:${pcC >= 0 ? 'var(--quita)' : 'var(--suma)'}"></div></div></div>
        <details class="reparto"><summary>Ver cómo se reparte el 100 % entre todas las causas</summary>
          <div class="tabla"><table><thead><tr><th>Causa</th><th class="n">TCH</th><th class="n">Toneladas</th><th class="n">% de la caída</th></tr></thead><tbody>${reparto}</tbody></table></div>
          <p class="sub" style="margin:6px 0 0">Las causas que restaron suman más del 100 % y las que sumaron TCH (en verde, con % negativo) lo compensan; con lo «sin explicar», el total da exacto el 100 %.</p></details>
        <p style="margin:10px 0 4px"><b>Qué mide.</b> ${esc(c.mide)}</p>
        <p style="margin:0"><b>Cuánto pesa.</b> ${esc(c.efecto)} Medido en 7.433 cosechas de 2011 a 2026, cada suerte frente a sí misma.</p>
        ${C.tch_base ? `<p class="sub" style="margin:4px 0 0">El efecto del modelo es un %; en TCH se calcula sobre el TCH normal 2020-25 de Riopaila (${nf(C.tch_base)} TCH), salvo que el texto diga otra base.</p>` : ''}
        <p class="sub" style="margin:8px 0 0">Le quitó más de 0,5 TCH a ${nAf} cosechas y le sumó más de 0,5 TCH a ${nFa}.</p></div>
      <div class="caja" id="soporte"></div>
      <div class="caja"><div class="cab"><h3 style="margin:0">Suertes y su dato</h3>
        <div class="filtros" style="margin:0"><button class="btn" id="f-af" aria-pressed="true">Solo las afectadas</button><button class="btn" id="f-to" aria-pressed="false">Todas</button></div></div>
        <p class="sub" style="margin:6px 0 10px">Ordenadas por lo que esta causa le quitó a cada una. Toque una suerte para ver su ficha completa.</p>
        <div id="t-causa"></div></div>
    </section></div>`;
  soporte(c.id, document.getElementById('soporte'));
  const cols = [...colSuerte, ...(COLS[c.id] || []), ...colReal,
    { t: 'Impacto (TCH)', n: true, f: s => barraImp(imp(s.ap[c.id]), mx), v: s => imp(s.ap[c.id]), asc: true }];
  const pintar = todas => {
    document.getElementById('f-af').setAttribute('aria-pressed', !todas);
    document.getElementById('f-to').setAttribute('aria-pressed', todas);
    const rows = todas ? conH : conH.filter(s => (s.ap[c.id] || 0) > 0.5);
    tabla(document.getElementById('t-causa'), cols, rows, { orden: cols.length - 1, dir: 1,
      pie: todas ? 'todas las cosechas con historia' : 'las que perdieron más de 0,5 TCH por esta causa' });
  };
  document.getElementById('f-af').onclick = () => pintar(false);
  document.getElementById('f-to').onclick = () => pintar(true);
  pintar(nAf === 0);
  const et = document.getElementById('ej-tabla');
  if (et) {
    const sts = C.soporte['corte-anterior'].ejemplo.suertes;
    tabla(et, [colSuerte[0], { t: 'TCH 2024 (manual)', n: true, f: s => nf(F[s.k].hist.find(h => h[0] === 2024)?.[4]), v: null },
      { t: 'TCH 2025 (mecanizado)', n: true, f: s => nf(s.ant_tch), v: null }, { t: 'TCH 2026 (mecanizado)', n: true, f: s => nf(s.real), v: null },
      { t: 'PPTO', n: true, f: s => nf(s.ppto), v: null }], S.filter(s => sts.includes(s.s)), {});
  }
}

// ---------------------------------------------------------------- desarrollo de la caña: aforo frente al óptimo de la variedad
const afo = s => AFO[s.s + '|' + s.m];
const pctO = (r, k) => 100 * r[k] / r['o' + k];
// peso de caña ∝ tallos × altura × diámetro² (volumen del tallo), frente al mismo producto del óptimo
const pesoO = r => 100 * (r.pob * r.alt * r.dia ** 2) / (r.opob * r.oalt * r.odia ** 2);
const clsO = v => Math.round(v) < 95 ? 't-q' : Math.round(v) > 105 ? 't-s' : '';   // con el valor redondeado que se muestra
const MEDO = { pob: 'Población', alt: 'Longitud', dia: 'Diámetro', peso: 'Peso de caña', kg: 'Peso por tallo' };
const UNI = { pob: 'tallos/m', alt: 'cm', dia: 'cm' };

// histórico 2023-25 contra 2026, ponderado por área: lo usan la pestaña y la explicación para la gerencia
function desarrolloHtml(enDoc) {
  const M = DV.mismas, T = DV.todas, K = ['pob', 'alt', 'dia', 'peso'];
  const pc = v => v == null ? '—' : `<span class="${clsO(v)}">${nf(v, 0)} %</span>`;
  const dp = (a, b, d = 0) => a == null || b == null ? '—' : `<b class="${clsImp(b - a)}">${sg(b - a, d)}</b>`;
  const fila = (et, x) => [et, x.cosechas, nf(x.ha, 0), ...K.map(k => pc(x[k])), nf(x.tch)];
  const tbl = (cab, filas, num) => `<div class="tabla"><table><thead><tr>${cab.map((c, i) => `<th class="${num.includes(i) ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${num.includes(i) ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const h = M.hist, n = M['2026'];
  const lead = `<p>En las mismas ${M.suertes} suertes, la caña de 2026 llegó a la cosecha con <b>${nf(h.peso - n.peso, 0)} puntos menos de peso de caña</b> frente al óptimo
      de su variedad que en su historia 2023-25 (${nf(n.peso, 0)} % contra ${nf(h.peso, 0)} %), sobre todo porque llegó <b>más corta</b> (longitud ${nf(n.alt, 0)} % contra ${nf(h.alt, 0)} %${h.v_alt != null ? `: ${nf(n.v_alt, 0)} cm contra ${nf(h.v_alt, 0)} cm` : ''}).
      La población bajó poco (${nf(n.pob, 0)} % contra ${nf(h.pob, 0)} %) y el diámetro quedó igual. En esas suertes el TCH pasó de ${nf(h.tch)} a ${nf(n.tch)}.</p>`;
  const resumen = tbl(['', 'Cosechas', 'Área (ha)', 'Población', 'Longitud', 'Diámetro', 'Peso de caña', 'TCH'], [
    fila(`<b>Mismas suertes</b> · histórico 2023-25`, h), fila('Mismas suertes · 2026', n),
    ['Diferencia', '', '', ...K.map(k => dp(h[k], n[k]) + ' pts'), dp(h.tch, n.tch, 1)],
    fila('Todas las cosechas · histórico 2023-25', T.hist), fila('Todas las cosechas · 2026', T['2026'])], [1, 2, 3, 4, 5, 6, 7]);
  // valores medidos ponderados por área (longitud = altura del tallo); el color dice si quedó a más de 5 % del óptimo
  const vm = (x, k, d, pk) => x[k] == null ? '—' : `<span class="${pk ? clsO(x[pk]) : ''}">${nf(x[k], d)}</span>`;
  const par = (a, b, k, d, pk) => `${vm(a, k, d, pk)} → <b>${vm(b, k, d, pk)}</b>`;
  const vari = tbl(['Variedad', 'Cosechas hist. · 2026', 'Longitud (cm)', 'Diámetro (cm)', 'Peso por tallo (kg)', 'Tallos por metro', 'Peso de caña frente al óptimo'],
    DV.variedades.map(([v, a, b]) => [esc(v), `${a.cosechas} · ${b.cosechas}`, par(a, b, 'v_alt', 0, 'alt'), par(a, b, 'v_dia', 2, 'dia'), par(a, b, 'v_kg', 2, 'kg'),
      par(a, b, 'v_pob', 1, 'pob'), `${pc(a.peso)} → <b>${pc(b.peso)}</b>`]), [1, 2, 3, 4, 5, 6]);
  const medido = h.v_alt == null ? '' : tbl(['Mismas suertes, valores medidos', 'Longitud (cm)', 'Diámetro (cm)', 'Peso por tallo (kg)', 'Tallos por metro', 'Peso medido en el aforo (kg)'], [
    ['Histórico 2023-25', nf(h.v_alt, 0), nf(h.v_dia, 2), nf(h.v_kg, 2), nf(h.v_pob, 1), nf(h.v_kgm, 2)], ['2026', nf(n.v_alt, 0), nf(n.v_dia, 2), nf(n.v_kg, 2), nf(n.v_pob, 1), nf(n.v_kgm, 2)],
    ['Diferencia', dp(h.v_alt, n.v_alt), dp(h.v_dia, n.v_dia, 2), dp(h.v_kg, n.v_kg, 2), dp(h.v_pob, n.v_pob, 1), dp(h.v_kgm, n.v_kgm, 2)]], [1, 2, 3, 4, 5]);
  const nota = `<p class="sub" style="margin:6px 0 0">% del óptimo de cada variedad (tabla de óptimos por variedad), ponderado por el área de cada cosecha; peso de caña = tallos × longitud × diámetro².
      A cada cosecha de enero a septiembre le toca el aforo de su suerte más cercano antes del corte (unos ${DV.dias_aforo} días antes). El histórico es 2023-25: antes casi no hay
      aforos cerca del corte, y en 2023 se aforó solo una parte. No es una causa más: es el camino por el que actúan el calor, la sequía o la cosecha mecanizada,
      por eso no se suma en las causas. Con esta base, la diferencia de aforo entre corte anterior mecanizado y manual no resultó confiable.</p>`;
  return enDoc ? `${lead}${resumen}${medido ? `<p style="margin-top:8px"><b>Valores medidos</b> (ponderados por área)</p>${medido}` : ''}<p style="margin-top:8px"><b>Por variedad</b> (las de más área en 2026; valores medidos ponderados por área, histórico → 2026)</p>${vari}${nota}`
    : `${lead}<div class="caja"><h3>Histórico 2023-25 contra 2026</h3>${resumen}${medido ? `<p class="sub" style="margin:12px 0 6px">Lo mismo en valores medidos, ponderados por el área de cada cosecha:</p>${medido}` : ''}</div><div class="caja"><h3>Por variedad</h3>
       <p class="sub" style="margin-bottom:8px">Las de más área en 2026. Valores medidos en el aforo, ponderados por el área de cada cosecha: histórico 2023-25 → 2026. Longitud = altura del tallo; peso por tallo = π × (diámetro ÷ 2)² × longitud × 1,04 (densidad) ÷ 1000, en kg; el del óptimo con la misma fórmula. Rojo: más de 5 % por debajo del óptimo de la variedad.</p>${vari}</div><div class="nota">${nota.replace('class="sub" ', '')}</div>`;
}

function vDesarrollo() {
  if (!DV || !DV.mismas) { $app.innerHTML = '<p>No están los datos del aforo (desarrollo.json).</p>'; return; }
  const M = DV.mismas, h = M.hist, n = M['2026'];
  const kpi = k => `<div class="kpi"><div class="et">${MEDO[k]} frente al óptimo</div><div class="v num ${clsO(n[k])}">${nf(n[k], 0)} <small>% en 2026</small></div>
    <div class="pie">histórico 2023-25: ${nf(h[k], 0)} % · <span class="${clsImp(n[k] - h[k])}">${sg(n[k] - h[k], 0)} pts</span></div></div>`;
  $app.innerHTML = `<div class="pila">
    <div><h2>¿La caña de 2026 llegó con menos desarrollo que en su historia?</h2>
      <p class="sub">Aforo antes de la cosecha frente al óptimo de cada variedad, ponderado por área: las mismas ${M.suertes} suertes en 2023-25 y en 2026.</p></div>
    <div class="kpis">${['peso', 'kg', 'alt', 'pob', 'dia'].map(kpi).join('')}</div>
    ${desarrolloHtml(false)}</div>`;
}

// recuadro de la ficha: el aforo de la suerte frente al óptimo de su variedad
function afoFicha(s) {
  const r = afo(s);
  if (!r) return DV ? `<div class="caja"><h3>Desarrollo de la caña frente al óptimo</h3><p class="sub" style="margin:0">Esta cosecha no tiene aforo en la base de aforos o su variedad no tiene óptimo.</p></div>` : '';
  const fila = k => `<tr><td>${MEDO[k]} (${UNI[k]})</td><td class="n">${nf(r[k], k === 'alt' ? 0 : k === 'dia' ? 2 : 1)}</td><td class="n">${nf(r['o' + k], k === 'alt' ? 0 : k === 'dia' ? 2 : 1)}</td>
    <td class="n"><b class="${clsO(pctO(r, k))}">${nf(pctO(r, k), 0)} %</b></td></tr>`;
  return `<div class="caja"><h3>Desarrollo de la caña frente al óptimo de ${esc(r.v)}</h3>
    <p class="sub" style="margin-bottom:8px">Aforo de la caña en pie antes de la cosecha. Rojo: más de 5 % por debajo del óptimo.</p>
    <div class="tabla"><table><thead><tr><th>Medida</th><th class="n">Aforo</th><th class="n">Óptimo</th><th class="n">% del óptimo</th></tr></thead><tbody>
      ${fila('pob')}${fila('alt')}${fila('dia')}
      ${r.kg != null ? `<tr><td>Peso por tallo (kg) · π × (diámetro ÷ 2)² × longitud × 1,04 ÷ 1000</td><td class="n">${nf(r.kg, 2)}</td><td class="n">${nf(r.okg, 2)}</td><td class="n"><b class="${clsO(100 * r.kg / r.okg)}">${nf(100 * r.kg / r.okg, 0)} %</b></td></tr>` : ''}
      ${r.kgm != null ? `<tr><td>Peso medido en el aforo (10 tallos ÷ 10, kg)</td><td class="n">${nf(r.kgm, 2)}</td><td class="n">—</td><td></td></tr>` : ''}
      <tr><td><b>Peso de caña</b> (tallos × longitud × diámetro²)</td><td></td><td></td><td class="n"><b class="${clsO(pesoO(r))}">${nf(pesoO(r), 0)} %</b></td></tr>
    </tbody></table></div><p class="sub" style="margin:6px 0 0"><a href="#desarrollo">Ver el histórico contra 2026 por variedad</a></p></div>`;
}

// ---------------------------------------------------------------- suelos: grupo de humedad (H0-H5) de lo cosechado ene-sep 2026 (suelos.json, suelos_humedad.py)
function suelosHtml(enDoc) {
  const G = SU.grupos, ha = G.reduce((x, g) => x + g.ha, 0) + (SU.sin_dato ? SU.sin_dato[1] : 0);
  const pHum = 100 * G.filter(g => ['H3', 'H4', 'H5'].includes(g.g)).reduce((x, g) => x + g.ha, 0) / ha;
  const lenta = 100 * G.filter(g => g.perm === 'lenta').reduce((x, g) => x + g.ha, 0) / ha;
  const gH = k => G.find(g => g.g === k);
  const seco = G[0], mojado = G[G.length - 1], masCae = G.reduce((a, g) => g.caida < a.caida ? g : a);
  const [pm, pmh, ph, phh] = SU.pruebas;
  const tbl = (cab, filas, num) => `<div class="tabla"><table><thead><tr>${cab.map((c, i) => `<th class="${num.includes(i) ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${num.includes(i) ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const lead = `<p>Lo cosechado de enero a septiembre de 2026 está <b>${nf(pHum, 0)} % en suelos con exceso de humedad</b> (H3-H4: les sobran 400 mm de agua al año o más)
      y ${nf(lenta, 0)} % en suelos de permeabilidad lenta, sobre todo Vertisoles. <b>A más humedad, menos TCH:</b> en 2020-25 esas mismas suertes daban ${nf(seco.historia)} TCH
      en ${seco.g} y ${nf(mojado.historia)} en ${mojado.g}. Pero en 2026 <b>no cayeron más los suelos húmedos</b>: la caída más grande fue en ${masCae.g} (${sg(masCae.caida)} TCH),
      donde hubo más cosecha mecanizada (${nf(masCae.mec, 0)} % del área).</p>`;
  const t1 = tbl(['Grupo', 'Qué es', 'Cosechas', 'Área (ha)', '% del área', 'Suelo', 'Historia 2020-25', 'PPTO 2026', 'Real 2026', 'Caída (TCH)', 'Toneladas'],
    G.map(g => [`<b>${g.g}</b>`, esc(g.def), g.cosechas, nf(g.ha, 0), nf(g.pct) + ' %', `${esc(g.orden || '')} · ${esc(g.regimen || '')} · permeabilidad ${esc(g.perm || '')}`,
      nf(g.historia), nf(g.ppto), nf(g.real), `<b class="${clsImp(g.caida)}">${sg(g.caida)}</b>`, `<span class="${clsImp(g.t)}">${sg(g.t, 0)}</span>`])
      .concat(SU.sin_dato ? [['Sin dato', 'La suerte no está en el estudio de suelos', SU.sin_dato[0], nf(SU.sin_dato[1], 0), nf(SU.sin_dato[2]) + ' %', '', '', '', '', '', '']] : []),
    [2, 3, 4, 6, 7, 8, 9, 10]);
  const CQ = [['cosecha mecanizada', 'Cosecha mecanizada (incluye el corte anterior)'], ['suelo húmedo', 'Cosecha con suelo húmedo'],
    ['calor y sequía', 'Calor y sequía al final del ciclo'], ['riego', 'Riego aplicado'], ['nivel freático', 'Nivel freático']];
  const t2 = tbl(['Lo que le quitó o sumó (TCH)', ...G.map(g => g.g)],
    CQ.map(([k, et]) => [et, ...G.map(g => `<span class="${clsImp(g.quito[k])}">${sg(g.quito[k])}</span>`)])
      .concat([['% del área con cosecha mecanizada', ...G.map(g => nf(g.mec, 0) + ' %')]]), G.map((_, i) => i + 1));
  const prueba = `<p><b>¿El tipo de suelo cambia el daño?</b> Con el mismo modelo de la caída, cada suerte frente a sí misma:</p>
    <ul><li><b>Cosecha mecanizada:</b> resta lo mismo en suelos secos y húmedos (${sg(pm[1])} % en H0-H2; en H3-H4 la diferencia es ${sg(pmh[1])} %, p ${nf(pmh[3], 2)}).
      El daño de la cosechadora no depende del grupo de humedad.</li>
    <li><b>Cosechar con el suelo húmedo</b> (lluvia en el mes del corte anterior): resta ${sg(ph[1])} % por cada 100 mm en H0-H2 y <b>${sg(phh[1])} % más en H3-H4</b>
      (p ${nf(phh[3], 2)}, casi significativo): unos ${sg(ph[1] + phh[1])} % en total. En los suelos con exceso de humedad y permeabilidad lenta, cortar con lluvia hace más daño;
      conviene programarlos en los meses secos.</li></ul>`;
  const h4 = gH('H4');
  const nota = `<p${enDoc ? '' : ' class="nota"'}><b>Lo que no demuestra.</b> El grupo de humedad no cambia dentro de una suerte, así que su efecto propio sobre el TCH
      no se puede separar de todo lo demás que tiene cada suerte: la comparación entre grupos es descriptiva.${h4 ? ` H4 son solo ${h4.cosechas} cosechas (${nf(h4.ha, 0)} ha),
      casi sin cosecha mecanizada; su subida de ${sg(h4.caida)} TCH no es una conclusión.` : ''} Grupos del estudio de suelos (exceso de humedad en mm/año y permeabilidad);
      coinciden con el código de la zona agroecológica del Maestro en el ${nf(SU.coinciden_za, 0)} % de las suertes.</p>`;
  return enDoc ? `${lead}${t1}<p style="margin-top:8px"><b>Qué le quitó cada causa en cada grupo</b></p>${t2}${prueba}${nota}`
    : `${lead}<div class="caja"><h3>Cada grupo de humedad: área, TCH y caída</h3>${t1}</div>
       <div class="caja"><h3>TCH por grupo de humedad</h3><p class="sub" style="margin-bottom:6px">Mismas suertes: historia 2020-25 frente a 2026 (enero a septiembre)</p><div id="gSuelo"></div>
         ${leyenda([['var(--hist)', 'Historia 2020-25'], ['var(--quita)', 'Real 2026'], ['var(--ppto)', 'PPTO 2026', true]])}</div>
       <div class="caja"><h3>Qué le quitó cada causa en cada grupo (TCH)</h3><p class="sub" style="margin-bottom:6px">Promedio de las cosechas 2026 del grupo; negativo = le quitó</p>${t2}</div>
       <div class="caja">${prueba}</div>${nota}`;
}

// ¿cada suerte se comportó como su grupo de humedad? Agua que sobró en el ciclo 2026 y nivel freático (humedad.json, humedad_comportamiento.py)
function humedadHtml() {
  if (!HU || !HU.grupos) return '';
  const tbl = (cab, filas, num) => `<div class="tabla"><table><thead><tr>${cab.map((c, i) => `<th class="${num.includes(i) ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${num.includes(i) ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const G = HU.grupos, GR = ['H0', 'H1', 'H2', 'H3', 'H4'];
  const e26 = G.reduce((x, g) => x + g[1], 0) / G.length, enor = G.reduce((x, g) => x + g[2], 0) / G.length;
  const h3 = G.find(g => g[0] === 'H3'), h01 = G.filter(g => g[0] === 'H0' || g[0] === 'H1'), h4 = G.find(g => g[0] === 'H4');
  const lt01 = h01.reduce((x, g) => x + g[3], 0) / h01.length;
  const [pGr, pExc, pNf] = HU.pruebas;
  const pc = v => v == null ? '—' : nf(v, 0) + ' %';
  const cruce = (c, et) => tbl([`Grupo designado → ${et}`, ...GR], c.map(r => [`<b>${r[0]}</b>`, ...r.slice(1).map((v, i) => v == null ? '' : GR[i] === r[0] ? `<b>${pc(v)}</b>` : pc(v))]), [1, 2, 3, 4, 5]);
  const comp = filas => tbl(['Cómo se comportó', 'Cosechas', 'Área (ha)', 'Exceso 2026 (mm/año)', 'Freático a menos de 1 m', 'Historia', 'Real 2026', 'Caída (TCH)', 'Cosecha mecanizada'],
    filas.map(r => [esc(r[0]), r[1], nf(r[2], 0), nf(r[3], 0), pc(r[4]), nf(r[5]), nf(r[6]), `<b class="${clsImp(r[7])}">${sg(r[7])}</b>`, pc(r[8])]), [1, 2, 3, 4, 5, 6, 7, 8]);
  const bal = HU.balance, seca = bal.find(r => r[0].startsWith('más seca')), hum = bal.find(r => r[0].startsWith('más húmeda'));
  return `<div class="caja"><h3>¿Cada suerte se comportó como su grupo de humedad?</h3>
      <p>Se midió el agua que de verdad le sobró a cada suerte en su ciclo 2026 (del corte anterior a la cosecha) de dos formas: el <b>balance</b>, lluvia de su pluviómetro
      menos la ETP de Cenicaña de su estación (solo los meses en que sobró, en mm por año), llevado a la misma tabla H0-H4 con la regla de permeabilidad;
      y el <b>nivel freático</b>, qué parte de las lecturas del ciclo tuvo el agua a menos de 1 m. Se compara con su grupo designado y con sus propios ciclos 2021-25.</p>
      ${tbl(['Grupo designado', 'Exceso 2026 (mm/año)', 'Exceso normal 2021-25 (mm/año)', 'Lecturas del freático a menos de 1 m'],
        G.map(g => [`<b>${g[0]}</b>`, nf(g[1], 0), nf(g[2], 0), pc(g[3])]), [1, 2, 3])}
      <ul style="margin-top:10px">
        <li><b>La lluvia no separa los grupos; el suelo sí.</b> A todos los grupos les sobró casi la misma agua de lluvia (${nf(Math.min(...G.map(g => g[1])), 0)} a ${nf(Math.max(...G.map(g => g[1])), 0)} mm/año en 2026).
          Lo que hace a un H3 distinto de un H1 es cuánto drena el suelo, y eso se ve en el freático: los H3 tuvieron el agua a menos de 1 m en el ${pc(h3[3])} de las lecturas,
          contra ${pc(lt01)} en H0-H1. <b>El H3 sí se comportó como suelo húmedo.</b>${h4 ? ` H4 no (${pc(h4[3])}, menos que H3), pero son pocas cosechas.` : ''}</li>
        <li><b>En 2026 los suelos se comportaron más secos que lo normal.</b> Les sobró en promedio ${nf(e26, 0)} mm/año, contra ${nf(enor, 0)} en sus ciclos 2021-25:
          casi un grupo más seco que lo de costumbre en todos los grupos. Coincide con la causa «Sequía al final del ciclo».</li>
      </ul></div>
    <div class="caja"><h3>En qué grupo se comportó cada grupo designado (% del área)</h3>
      <p class="sub" style="margin-bottom:6px">Por el balance de agua y la tabla del estudio de suelos (en permeabilidad lenta un escalón más húmedo). En negrilla, el área que se comportó como su grupo.</p>
      <p style="margin:0 0 4px"><b>2026</b></p>${cruce(HU.cruce, 'se comportó en 2026')}
      <p style="margin:10px 0 4px"><b>Sus ciclos normales 2021-25</b></p>${cruce(HU.cruce_normal, 'se comporta normalmente')}
      <p class="sub" style="margin:6px 0 0">Con la tabla al pie de la letra, casi todo suelo de permeabilidad lenta queda en H2 o más húmedo aun si está designado H1: el estudio de suelos debió usar
        otro balance para asignar los grupos. Por eso la señal más útil es el cambio frente a su propio normal y el freático.</p></div>
    <div class="caja"><h3>¿Cayó más donde el suelo se comportó más húmedo?</h3>
      <p style="margin-bottom:6px"><b>Según el balance de lluvia</b></p>${comp(HU.balance)}
      <p style="margin:10px 0 6px"><b>Según el nivel freático</b> (frente a lo típico de su grupo designado)</p>${comp(HU.freatico)}
      <ul style="margin-top:10px">
        <li><b>Por la lluvia, no se ve:</b> correrse a un grupo más húmedo no explica la caída (${sg(pGr[1])} % de TCH por grupo, p ${nf(pGr[2], 2)}).
          Las que se comportaron más secas cayeron menos (${sg(seca[7])} TCH contra ${sg(hum[7])}), pero tuvieron menos cosecha mecanizada (${pc(seca[8])} contra ${pc(hum[8])}): no se le puede atribuir al agua.</li>
        <li><b>Por el freático, sí (casi seguro):</b> donde el agua estuvo más alta que lo normal de esa misma suerte, el TCH cayó más:
          ${sg(pNf[1])} % por cada 10 puntos más de lecturas a menos de 1 m (p ${nf(pNf[2], 2)}). Coincide con la causa «Nivel freático» del modelo.</li>
      </ul>
      <p class="nota" style="margin:8px 0 0"><b>Lo que no demuestra.</b> El balance de lluvia no ve el agua que llega por escorrentía, canales o mal drenaje: ahí el freático es mejor señal.
        La tabla del estudio de suelos es un promedio de largo plazo, no de un año. Estas comparaciones son entre suertes, con la cosecha mecanizada como control; no son el modelo completo.
        En la ficha de cada suerte se ve cómo se comportó en 2026.</p></div>`;
}

function vSuelos() {
  if (!SU || !SU.grupos) { $app.innerHTML = '<p>No están los datos de suelos (suelos.json).</p>'; return; }
  const G = SU.grupos;
  $app.innerHTML = `<div class="pila">
    <div><h2>¿Cómo está el suelo de lo cosechado en 2026?</h2>
      <p class="sub">Grupo de humedad del estudio de suelos: cuánta agua le sobra al suelo en el año (H0 nada, H4 más de 600 mm) y qué tan rápido la deja pasar.</p></div>
    ${suelosHtml(false)}${humedadHtml()}</div>`;
  grafico(document.getElementById('gSuelo'), { x: G.map(g => g.g), series: [{ valores: G.map(g => g.historia), color: 'var(--hist)', d: 1 },
    { valores: G.map(g => g.real), color: 'var(--quita)', d: 1, etiquetas: true }, { tipo: 'linea', valores: G.map(g => g.ppto), color: 'var(--ppto)', dash: true }],
    ymin: 80, yfmt: v => nf(v, 0) });
}

// ---------------------------------------------------------------- satélite del ciclo: curva 2026 por edad frente a la normal propia y falta de agua (satciclo.json, satelite_ciclo.py)
// frase de la ficha: cuánto se alejó el NDRE de la suerte de su normal propia a los 5-7 meses (meses de edad 6 y 7)
// una ventana de edad es «firme» si el efecto en TCH tiene el mismo signo y p < 0,05 contando la edad desde el mes siguiente al corte y desde el mes del corte
const satFirme = x => x.tch_alt != null && Math.sign(x.tch) === Math.sign(x.tch_alt) && x.tch_p < 0.05 && x.tch_alt_p < 0.05;
const satRango = x => sg(x.tch) === sg(x.tch_alt) ? sg(x.tch) : `${sg(Math.max(x.tch, x.tch_alt))} a ${sg(Math.min(x.tch, x.tch_alt))}`;
// tabla de la prueba por año (normal y TCH histórico solo con cosechas anteriores a cada año)
function satValTabla(tb) {
  return tb(['Año', 'Cosechas', 'ha', 'TCH por cada 0,05 de NDRE por debajo de su normal', 'Rezagadas (≤ −0,02): cosechas', 'Rezagadas: caída (TCH)', 'Resto: caída (TCH)', 'Área rezagada que cayó más de 5 %'],
    SC.validacion.map(v => [`<b>${v.anio}</b>`, v.n, nf(v.ha, 0), `${sg(-v.ef)} % <small>(p ${v.p < 0.001 ? '< 0,001' : nf(v.p, 3)})</small>`, `${v.rez_n} (${nf(v.rez_ha, 0)} ha)`,
      `<b class="${clsImp(v.rez_caida)}">${sg(v.rez_caida)}</b>`, `<span class="${clsImp(v.resto_caida)}">${sg(v.resto_caida)}</span>`, `${nf(v.rez_cayo, 0)} % <small>(resto ${nf(v.resto_cayo, 0)} %)</small>`]),
    [1, 2, 3, 4, 5, 6, 7]);
}

// por qué la curva usa NDRE: la prueba por años repetida con cada índice en la misma muestra (SC.comparacion, prueba 5 de satelite_ciclo.py)
const satCv = (v, i) => (SC.comparacion || []).find(c => c.v === v && c.ind === i) || {};
function satComp(tb) {
  const A = [2022, 2023, 2024, 2025], pc = v => v == null ? '—' : nf(100 * v, 0) + ' %';
  const nom = { NDVI: 'NDVI (el de antes)', NDRE: '<b>NDRE (el que se usa)</b>', EVI: 'EVI', GNDVI: 'GNDVI', WDRVI: 'WDRVI (calculado del NDVI del mes)', NDMI: 'NDMI (humedad del follaje)' };
  const gana = i => ['3-5', '5-7', '7-10'].reduce((a, v) => a + A.filter(y => satCv(v, i)['t' + y] > satCv(v, 'NDVI')['t' + y]).length, 0);
  return tb(['Índice', 'Le gana al NDVI en 2022-25 (de 12: 4 años × 3 edades)', 'Para elegir: 2022-25, a los 5-7 meses', 'Sin ver 2026: 3-5 meses', '5-7 meses', '7-10 meses'],
    ['NDVI', 'NDRE', 'EVI', 'GNDVI', 'WDRVI', 'NDMI'].filter(i => satCv('5-7', i).ind).map(i => [nom[i], i === 'NDVI' ? '—' : gana(i), pc(satCv('5-7', i).loo),
      pc(satCv('3-5', i).r2), i === SC.ind ? `<b>${pc(satCv('5-7', i).r2)}</b>` : pc(satCv('5-7', i).r2), pc(satCv('7-10', i).r2)]), [1, 2, 3, 4, 5]);
}

// sección de «Para la gerencia»: lo que vio el satélite en el ciclo 2026 frente a la normal de cada suerte (satciclo.json)
function satDoc() {
  if (!SC || !SC.curva) return '';
  const K = SC.curva, Vn = SC.ventanas, Q = SC.quintiles, F = SC.fuera, vv = id => Vn.find(x => x.v === id), ck = k => K.find(x => x.k === k) || {};
  const medio = K.filter(x => x.k >= 2 && x.k <= 10), dMed = medio.reduce((a, x) => a + x.dif, 0) / medio.length;
  const q1 = Q[0], q5 = Q[Q.length - 1], v35 = vv('3-5'), v57 = vv('5-7'), v710 = vv('7-10');
  const tb = (cab, filas, num) => `<div class="tabla"><table><thead><tr>${cab.map((c, i) => `<th class="${num.includes(i) ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${num.includes(i) ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  return `<section><h3>Satélite: la caña de 2026 mes a mes desde el corte</h3>
      <p>Con Sentinel-2 se siguió el vigor del follaje (NDRE, con la banda del borde rojo) de ${SC.cosechas} cosechas de 2026 (${nf(SC.ha, 0)} ha), mes a mes de edad, frente a los ciclos de la misma suerte cosechados en 2020-25.</p>
      <ul style="margin:6px 0;padding-left:20px">
        <li><b>Las suertes cuya caña se quedó atrás a los 5-7 meses fueron las que cayeron, y no solo en 2026.</b> Se probó en cada año de 2022 a 2026 con la normal y la historia
          de cada suerte tomadas solo de años anteriores, descontando la cosecha mecanizada, la edad y cómo venía el corte anterior: en los cinco años la señal sale igual (p < 0,001).
          En 2026 el quinto más rezagado cayó ${sg(q1.caida)} TCH y el más adelantado subió ${sg(q5.caida)}. Con la relación medida en 2022-25, sin ver 2026, la curva anticipa el
          ${nf(100 * F.r2, 0)} % de las diferencias de caída entre suertes de 2026 (sin la curva, ${nf(100 * F.r2_sin, 0)} %).</li>
        <li><b>La soca del corte mecanizado arranca más despacio</b> (2019-2026, cada suerte frente a sí misma): tras el primer corte mecanizado el NDRE queda ${s3(vv('0-3').mec_ndre)} a los 0-3 meses
          y ${s3(v35.mec_ndre)} a los 3-5; a los 7 meses ya se igualó. El satélite confirma el golpe a la cepa; la pérdida en toneladas la mide la báscula.</li>
        <li><b>La falta de agua de los 3 a los 10 meses resta TCH</b> (${satRango(v35)} TCH por cada 100 mm de 3 a 5 meses, ${satRango(v57)} de 5 a 7 y ${satRango(v710)} de 7 a 10, según cómo se cuente la edad).
          De 3 a 5 meses se ve en el follaje; de 7 a 10 casi no: con la caña cerrada, el agua que falta le quita altura y peso, no verdor, como mostró el aforo. En 2026 sobró agua de los 3 a los 7 meses
          y faltó de los 7 a la cosecha.</li>
        <li><b>El promedio de 2026 no prueba nada por sí solo:</b> la caña estuvo ${dMed > 0.01 ? 'por encima de' : dMed < -0.01 ? 'por debajo de' : 'en'} su normal hasta el mes 10 (${s3(dMed)}) y quedó por debajo
          en los meses 11 y 12 (${s3(ck(11).dif)} y ${s3(ck(12).dif)}). Esa caída del final coincide con más falta de agua, pero antes del corte la caña también se seca por la maduración y el madurante; el satélite no separa una cosa de la otra.</li>
        <li><b>Se cambió el NDVI por el NDRE.</b> El NDVI se satura cuando la caña cierra (desde los 4-5 meses se queda cerca de su techo aunque la caña siga creciendo); el NDRE usa el borde rojo
          y se satura menos. Se repitió la misma prueba con seis índices y se escogió con 2022-25, sin mirar 2026: el NDRE le gana al NDVI en todos los años y edades.
          Después, en 2026, anticipa el ${nf(100 * satCv('5-7', 'NDRE').r2, 0)} % frente al ${nf(100 * satCv('5-7', 'NDVI').r2, 0)} % del NDVI.</li>
      </ul>
      ${satValTabla(tb)}
      <p class="sub" style="margin:10px 0 4px">La misma prueba con cada índice (mismas cosechas; % de las diferencias de caída entre suertes que anticipa)</p>${satComp(tb)}
      <p style="margin-top:8px"><b>Para qué sirve.</b> A los 7 meses faltan unos 5 para la cosecha: la curva frente a la normal de cada suerte es una alerta temprana para revisar en campo.
        <b>Lo que no demuestra:</b> el NDRE se satura menos que el NDVI, pero también mide el follaje, no altura ni peso; marca qué suertes cayeron, no por qué (cosechadora, agua, plagas o manejo). No entra al modelo de la caída.</p></section>`;
}

// índice con signo y 3 decimales (sg no pone signo por debajo de 0,005)
const s3 = v => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + nf(Math.abs(v), 3);
function satBrecha(s) {
  const c = SC && SC.fichas && SC.fichas[s.s + '|' + s.m];
  if (!c) return '';
  const g = [5, 6].map(i => c.v[i] != null && c.vn[i] != null ? c.v[i] - c.vn[i] : null).filter(v => v != null);
  if (!g.length) return '';
  const b = g.reduce((a, v) => a + v, 0) / g.length;
  return `. <b>A los 5-7 meses estuvo ${s3(b)} de NDRE ${b < 0 ? 'por debajo' : 'por encima'} de su normal</b> (${c.n} ciclos 2020-25)${b <= -0.02 ? ': rezagada, como las suertes que más cayeron' : ''}. <a href="#satelite">Ver todo Riopaila</a>`;
}

function vSatelite() {
  if (!SC || !SC.curva) { $app.innerHTML = '<p>No están los datos del satélite del ciclo (satciclo.json).</p>'; return; }
  const K = SC.curva, Vn = SC.ventanas, Q = SC.quintiles, F = SC.fuera, vv = id => Vn.find(x => x.v === id);
  const ck = k => K.find(x => x.k === k) || {};
  const medio = K.filter(x => x.k >= 2 && x.k <= 10), dMed = medio.reduce((a, x) => a + x.dif, 0) / medio.length;
  const dMedV = medio.reduce((a, x) => a + x.dif_ndvi, 0) / medio.length, enN = dMed > 0.01 ? 'por encima de' : dMed < -0.01 ? 'por debajo de' : 'en';
  const q1 = Q[0], q5 = Q[Q.length - 1], v57 = vv('5-7'), v710 = vv('7-10'), v35 = vv('3-5');
  const an = SC.anual, anOtros = Object.entries(an).filter(([y]) => +y < 2025).map(([, v]) => v);
  const pp = p => p < 0.001 ? 'p < 0,001' : 'p ' + nf(p, 3);
  const tbl = (cab, filas, num) => `<div class="tabla"><table><thead><tr>${cab.map((c, i) => `<th class="${num.includes(i) ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${num.includes(i) ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const seVe = x => !satFirme(x) ? 'No es firme: cambia según cómo se cuente la edad' : x.ndre_p < 0.01 && x.tch_p < 0.05 ? 'Se ve en la caña y en el TCH' : x.tch_p < 0.05 ? '<b>Resta TCH, pero el satélite casi no la ve</b> (caña cerrada)' :
    x.ndre_p < 0.01 ? 'Se ve en la caña; en el TCH no es confiable' : 'No es confiable';
  const t1 = tbl(['Edad de la caña', 'Falta de agua normal 2020-25 (mm)', 'Falta 2026 (mm)', 'TCH por cada 100 mm de falta', 'NDRE por cada 100 mm de falta', 'Lectura'],
    Vn.map(x => [`<b>${x.v === '10-cosecha' ? '10 meses a la cosecha' : x.v + ' meses'}</b>`, nf(x.falta_normal, 0), `<span class="${x.falta_2026 > x.falta_normal + 10 ? 't-q' : x.falta_2026 < x.falta_normal - 10 ? 't-s' : ''}">${nf(x.falta_2026, 0)}</span>`,
      satFirme(x) ? satRango(x) : '—', `${s3(x.ndre)} <small>(${pp(x.ndre_p)})</small>`, seVe(x)]), [1, 2, 3, 4]);
  const t2 = tbl(['Quinto de las cosechas 2026', 'Cosechas', 'ha', 'NDRE a los 5-7 meses frente a su normal', 'Historia 2020-25', 'Real 2026', 'Caída (TCH)', 'Cosecha mecanizada'],
    Q.map((x, i) => [i === 0 ? '<b>1 · las más rezagadas</b>' : i === Q.length - 1 ? `<b>${x.q} · las más adelantadas</b>` : String(x.q), x.n, nf(x.ha, 0), s3(x.brecha), nf(x.hist), nf(x.real),
      `<b class="${clsImp(x.caida)}">${sg(x.caida)}</b>`, nf(x.mec, 0) + ' %']), [1, 2, 3, 4, 5, 6, 7]);
  $app.innerHTML = `<div class="pila">
    <div><h2>¿Qué vio el satélite en la caña de 2026, mes a mes desde el corte?</h2>
      <p class="sub">Vigor del follaje (NDRE, con la banda del borde rojo) y humedad del follaje (NDMI) de Sentinel-2 de cada cosecha de enero a septiembre de 2026, por mes de edad, frente a los ciclos de la misma suerte
      cosechados en 2020-25 a la misma edad. ${SC.cosechas} de ${SC.cosechas_2026} cosechas (${nf(SC.ha, 0)} ha) tienen al menos dos ciclos propios para comparar.</p></div>
    <div class="kpis">
      <div class="kpi${dMed > 0.01 ? ' subio' : dMed < -0.01 ? ' caida' : ''}"><div class="et">Meses 2 a 10</div><div class="v num">${s3(dMed)} <small>NDRE</small></div><div class="pie">${enN} su normal propia</div></div>
      <div class="kpi caida"><div class="et">Mes 12, antes de cosechar</div><div class="v num">${s3(ck(12).dif)} <small>NDRE</small></div><div class="pie">por debajo de su normal (${nf(ck(12).bajo, 0)} % del área)</div></div>
      <div class="kpi caida"><div class="et">Las más rezagadas a los 5-7 meses</div><div class="v num">${sg(q1.caida)} <small>TCH</small></div><div class="pie">las más adelantadas: ${sg(q5.caida)} TCH</div></div>
      <div class="kpi"><div class="et">Probada en otros años</div><div class="v num">${SC.validacion.filter(v => v.p < 0.01).length} de ${SC.validacion.length} <small>años</small></div><div class="pie">sin ver 2026 anticipa el ${nf(100 * F.r2, 0)} % (sin la curva ${nf(100 * F.r2_sin, 0)} %)</div></div>
    </div>
    <div class="caja"><h3>La curva de 2026 frente a la normal de cada suerte</h3>
      <p><b>Hasta el mes 10 la caña de 2026 estuvo ${enN} su normal</b> (${s3(dMed)} de NDRE en promedio; el NDVI la mostraba más verde, ${s3(dMedV)}).
        En los meses 11 y 12 quedó por debajo (${s3(ck(11).dif)} y ${s3(ck(12).dif)}; la humedad del follaje, NDMI, también desde el mes 11), cuando la falta de agua de 2026 subió (mes 11: ${nf(ck(11).falta, 0)} mm frente a ${nf(ck(11).falta_n, 0)} normal; mes 12: ${nf(ck(12).falta, 0)} frente a ${nf(ck(12).falta_n, 0)}).
        Coincide con la causa <a href="#causa/clima">«Calor y sequía al final del ciclo»</a>, pero <b>no la prueba</b>: antes del corte la caña también se seca por la maduración y el madurante,
        y el satélite no separa una cosa de la otra. Con el NDVI, todo Riopaila se veía más verde en 2025-26; con el NDRE ${Math.max(an[2025], an[2026]) <= Math.max(...anOtros) ? 'no' : 'también'}
        (promedio ${nf(an[2025], 3)} y ${nf(an[2026], 3)} frente a ${nf(Math.min(...anOtros), 3)}-${nf(Math.max(...anOtros), 3)} en 2019-24). En todo caso, verde no es lo mismo que toneladas:
        lo firme está en las secciones siguientes.</p>
      <div id="gSatC"></div>${leyenda([['var(--quita)', 'NDRE 2026'], ['var(--hist)', 'NDRE normal propio (ciclos 2020-25)', 1]])}
      <p class="sub" style="margin:10px 0 4px">Falta de agua de cada mes de edad (0,8 × evaporación − lluvia, mm)</p>
      <div id="gSatF"></div>${leyenda([['var(--quita)', 'Falta 2026'], ['var(--hist)', 'Falta normal de esas suertes']])}</div>
    <div class="caja"><h3>¿En qué edad hace daño la falta de agua?</h3>
      <p>Cada suerte frente a sí misma: cuánto TCH resta cada 100 mm de falta de agua según la edad de la caña (${nf(SC.n_tch, 0)} cosechas 2011-2026, con los mismos controles del modelo)
        y cuánto baja el NDRE de esa edad (${nf(SC.ciclos_sat, 0)} ciclos con satélite desde 2019).</p>${t1}
      <p style="margin-top:8px">El TCH va como rango: se midió contando la edad desde el mes siguiente al corte y desde el mes del corte. De 0 a 3 meses y del mes 10 a la cosecha
        el resultado cambia con esa elección (de signo o de confiabilidad), así que no se toma como firme.
        De 3 a 5 meses la falta de agua <b>se ve en la caña y resta TCH</b> (${satRango(v35)} TCH por 100 mm): es cuando la caña está cerrando.
        De 7 a 10 meses <b>también resta (${satRango(v710)} TCH)</b>, pero el satélite apenas lo ve (${s3(v710.ndre)} de NDRE, ${pp(v710.ndre_p)}): con la caña cerrada, la falta de agua
        no le quita verdor sino altura y peso. Coincide con el aforo: en 2026 la caña llegó más baja que en su historia (<a href="#desarrollo">Desarrollo de la caña</a>).
        En 2026 la falta de los meses 3 a 7 fue <b>menor</b> que lo normal; la de más vino de los 7 meses a la cosecha.</p></div>
    <div class="caja"><h3>Las suertes cuya caña se quedó atrás a los 5-7 meses son las que cayeron</h3>
      <p>Se ordenaron las cosechas 2026 por cuánto se alejó su NDRE de su normal propia a los 5-7 meses y se partieron en cinco grupos del mismo tamaño.
        Las más rezagadas cayeron <b>${sg(q1.caida)} TCH</b>; las más adelantadas subieron ${sg(q5.caida)}. La cosecha mecanizada no cambia mucho entre los grupos
        (${nf(Math.min(...Q.map(x => x.mec)), 0)}-${nf(Math.max(...Q.map(x => x.mec)), 0)} %), así que la señal no es solo la cosechadora.</p>${t2}
      <p style="margin-top:12px"><b>¿Pasa solo en 2026? No: se probó en cada año de 2022 a 2026.</b> Para cada año, la normal satelital y la historia de TCH de cada suerte salen solo de años anteriores
        (nada de ese año ni de después), y se descuentan la cosecha mecanizada, la edad y cómo venía el corte anterior frente a su historia (para que una suerte que venía de un mal corte
        no parezca mejorar solo por volver a su nivel). En los cinco años la señal sale con el mismo sentido y p < 0,001, en años de mucha caída (2023) y de subida (2025):</p>${satValTabla(tbl)}
      <p style="margin-top:8px"><b>Predicción sin ver 2026:</b> con la relación medida en 2022-25 (${sg(-F.ef)} % de TCH por cada 0,05 de NDRE por debajo), aplicada a las cosechas de 2026, la curva anticipa el
        <b>${nf(100 * F.r2, 0)} %</b> de las diferencias de caída entre suertes; la cosecha mecanizada, la edad y el corte anterior solos anticipan el ${nf(100 * F.r2_sin, 0)} %.
        A los 7 meses todavía faltan unos 5 para la cosecha: <b>la curva sirve de alerta temprana</b> para revisar esas suertes en campo.</p></div>
    <div class="caja"><h3>¿Por qué NDRE y no NDVI?</h3>
      <p>El NDVI compara el rojo con el infrarrojo cercano. Cuando la caña cierra (desde los 4-5 meses), las hojas de arriba absorben casi todo el rojo y el NDVI se queda cerca de su techo
        aunque la caña siga creciendo: se <b>satura</b>. El NDRE usa en lugar del rojo la banda del <b>borde rojo</b> (Sentinel-2, banda 5), que entra más en el follaje cerrado y sigue marcando diferencias.</p>
      <p style="margin-top:6px">Se repitió la misma prueba por años con seis índices, en las mismas cosechas. <b>Para no escoger con 2026</b>, la elección se hizo solo con 2022-25: la fuerza de la señal en cada año
        y cuánto anticipa cada año cuando se lo deja por fuera. El NDRE le gana al NDVI en los 12 casos (4 años × 3 edades). Después, sin ver 2026, anticipa el
        <b>${nf(100 * satCv('5-7', 'NDRE').r2, 0)} %</b> de las diferencias de caída frente al ${nf(100 * satCv('5-7', 'NDVI').r2, 0)} % del NDVI, y la mejora es mayor de 7 a 10 meses,
        cuando la caña está más cerrada (${nf(100 * satCv('7-10', 'NDRE').r2, 0)} % frente a ${nf(100 * satCv('7-10', 'NDVI').r2, 0)} %).</p>${satComp(tbl)}
      <p style="margin-top:8px">El <b>EVI</b> era el mejor con 2022-25, pero en 2026 no mejoró al NDVI: usa la banda azul, sensible a la bruma, así que no se tomó.
        El <b>WDRVI</b> aquí sale del NDVI del mes (no de las bandas), por eso mejora poco. El <b>NDMI</b> empata con el NDRE en 2026, pero mide la humedad del follaje y ya se usa aparte.
        Las cosechas más rezagadas son casi las mismas con cualquier índice; el NDRE ordena mejor a las demás. El NDVI y los demás índices quedan en el Excel como comparación.</p></div>
    <div class="caja"><h3>La soca después del corte mecanizado arranca más despacio</h3>
      <p class="sub" style="margin-bottom:6px">Diferencia de NDRE frente a la normal propia, según cómo fue el corte anterior (${SC.por_ant.man} cosechas tras corte manual, ${SC.por_ant.new} tras el primero mecanizado, ${SC.por_ant.seg} tras dos mecanizados)</p>
      <div id="gSatA"></div>${leyenda([['var(--hist)', 'Corte anterior manual', 1], ['var(--quita)', 'Primer corte mecanizado'], ['var(--mec)', 'Dos cortes mecanizados seguidos']])}
      <p style="margin-top:8px"><b>Con todos los ciclos 2019-2026</b>, cada suerte frente a sí misma y descontando año, mes de inicio, falta de agua y etapa de la soca: tras el primer corte mecanizado
        el NDRE queda ${s3(vv('0-3').mec_ndre)} a los 0-3 meses, ${s3(vv('3-5').mec_ndre)} a los 3-5 y ${s3(vv('5-7').mec_ndre)} a los 5-7 (p < 0,05 en los tres); de los 7 meses en adelante ya no hay diferencia.
        En 2026 se ve igual: tras un corte manual la caña estuvo ${s3(ck(5).dif_man)} sobre su normal en los meses 3 a 6 y tras uno mecanizado ${ck(5).dif_new < -0.01 ? 'por debajo' : 'casi en su normal'} (${s3(ck(5).dif_new)}).
        El satélite confirma el golpe a la cepa en la primera mitad del ciclo; la pérdida en toneladas la mide la báscula.</p></div>
    <p class="nota"><b>Lo que no demuestra.</b> El NDRE se satura menos que el NDVI cuando la caña cierra, pero también mide el follaje: no mide altura ni peso, por eso no reemplaza la báscula ni el aforo.
      La curva marca <b>qué</b> suertes cayeron (probado en 2022-2026), pero no dice <b>por qué</b>: una caña rezagada puede venir de la cosechadora, del agua, de plagas o del manejo. La normal propia sale de 2 a 6 ciclos
      y la falta de agua es la de la EMA de la suerte, no la del pluviómetro. Respalda la cosecha mecanizada y el efecto de la falta de agua por edad; no entra al modelo de la caída. Programa: satelite_ciclo.py.</p>
  </div>`;
  const x = K.map(c => String(c.k));
  grafico(document.getElementById('gSatC'), { x, series: [{ tipo: 'linea', valores: K.map(c => c.ndre_n), color: 'var(--hist)', dash: true, d: 3 },
    { tipo: 'linea', valores: K.map(c => c.ndre), color: 'var(--quita)', grosor: 3, d: 3 }], ymin: 0.1, ymax: 0.65, nt: 5, yfmt: v => nf(v, 2), ejeX: 'meses de edad', alto: 230, anchoEt: 24 });
  grafico(document.getElementById('gSatF'), { x, series: [{ valores: K.map(c => c.falta), color: 'var(--quita)', d: 0 }, { valores: K.map(c => c.falta_n), color: 'var(--hist)', d: 0 }],
    ymin: 0, yfmt: v => nf(v, 0), ejeX: 'meses de edad', alto: 170, anchoEt: 24 });
  grafico(document.getElementById('gSatA'), { x, series: [{ tipo: 'linea', valores: K.map(c => c.dif_man), color: 'var(--hist)', dash: true, d: 3 },
    { tipo: 'linea', valores: K.map(c => c.dif_new), color: 'var(--quita)', d: 3 }, { tipo: 'linea', valores: K.map(c => c.dif_seg), color: 'var(--mec)', d: 3 }],
    yfmt: v => nf(v, 2), ejeX: 'meses de edad', alto: 210, anchoEt: 24 });
}

// qué tipo de análisis es: la regresión, cómo se lee un efecto y qué no demuestra (Método y fuentes y Para la gerencia)
function regresionHtml() {
  const ca = C.soporte['corte-anterior'];
  return `<p><b>Es una regresión.</b> Una regresión lineal múltiple con efectos fijos, sobre datos de panel: las mismas suertes medidas año tras año.
      Explica el TCH de cada cosecha (en logaritmo, por eso cada efecto sale en %) con 7.433 cosechas de Riopaila de 2011 a 2026.</p>
    <ul style="margin:6px 0;padding-left:20px">
      <li><b>Cada suerte frente a sí misma</b> (efecto fijo de suerte): cada suerte tiene su propio nivel, así que una suerte buena no se mezcla con una mala.</li>
      <li><b>Año y mes de cosecha</b> (efectos fijos): descuentan lo que le pasó a todo Riopaila ese año y la época de corte.</li>
      <li><b>Todas las causas juntas:</b> edad, número de corte y etapa de la soca, variedad, incendio, cosecha mecanizada, corte anterior mecanizado, calor, falta de agua y riego,
        lluvia, nivel freático, labores y renovación entran al mismo tiempo; el efecto de cada una ya descuenta a las demás, por eso no se cuentan dos veces.</li>
      <li><b>Ponderada por área:</b> una suerte de 10 ha pesa más que una de 2 ha. <b>Errores agrupados por suerte:</b> el p-valor tiene en cuenta que las cosechas de una misma suerte se parecen.</li>
    </ul>
    <p><b>Del efecto al aporte.</b> Aporte de una causa en una suerte = efecto × (su nivel en 2026 − el nivel normal). Los aportes de todas las causas más lo «sin explicar»
      suman exacto la caída de la suerte. El efecto en % se pasa a TCH con el TCH normal 2020-25 de Riopaila (${nf(C.tch_base || 118.4)} TCH).</p>
    ${ca && ca.efecto ? `<p><b>Ejemplo: corte anterior mecanizado.</b> ${esc(ca.efecto)} En 2026 hubo más área que salía de un corte mecanizado que lo normal; por eso esta parte
      de la causa «Cosecha mecanizada» le quitó ${sg(-ca.t_ha, 2)} TCH a la caída.</p>` : ''}
    <p class="nota" style="margin:6px 0 0"><b>Qué tan confiable es.</b> Se probó prediciendo 2026 sin haberlo visto (pestaña «Prueba del modelo»): acierta el promedio y los grupos,
      pero suerte por suerte explica poco (R² de 0,21 a 0,29). Es una asociación medida con muchos años y suertes, no un experimento: dice cuánto se mueve el TCH
      cuando cambia cada causa, descontando las demás, pero no reemplaza una prueba de campo.</p>`;
}

// ---------------------------------------------------------------- vista: explicación para la gerencia (documento completo, se descarga en PDF)
// Las cifras salen de los mismos datos del informe; las de análisis aparte (alerta 2027 en t) se citan del soporte.
function vGerencia() {
  const A = agregado(S), P = A.puente, brecha = P.ppto - P.real, sobre = P.ppto - P.hist, caidaP = P.hist - P.real;
  const top = C.causas.filter(c => Math.abs(c.t_ha) >= 0.3).sort((a, b) => b.t_ha - a.t_ha);
  const quitan = top.filter(c => c.t_ha > 0), suman = top.filter(c => c.t_ha < 0);
  const grupos = {};
  C.causas.forEach(c => grupos[c.grupo] = (grupos[c.grupo] || 0) - c.t_ha);
  const mec = C.soporte.mecanica, ca = C.soporte['corte-anterior'];
  const tablaCA = k => ca.tabla.find(r => r[0] === k) || [];
  const al = mec.alerta2027, alNdvi = al && al.resumen.find(r => r[0] === 60 && r[1] === 'ndvi');
  const p = prediccion(), causa = id => C.causas.find(c => c.id === id);
  const minus = t => t[0].toLowerCase() + t.slice(1);   // nombre de la causa dentro de una frase
  const lista = L => L.map(c => minus(c.nombre)).join(', ').replace(/, ([^,]*)$/, ' y $1');
  // tabla simple; num = índices de las columnas numéricas
  const tb = (cab, filas, num = []) => `<div class="tabla"><table><thead><tr>${cab.map((c, i) => `<th class="${num.includes(i) ? 'n' : ''}">${c}</th>`).join('')}</tr></thead>
    <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${num.includes(i) ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  const conH = S.filter(s => s.hist != null);
  const wS = k => { const L = conH.filter(s => s[k] != null), a = L.reduce((x, s) => x + s.a, 0); return a ? L.reduce((x, s) => x + s[k] * s.a, 0) / a : null; };
  const ap = id => sg(-(causa(id) || { t_ha: 0 }).t_ha);
  const haMec = y => (mec.ha.find(r => r[0] === y) || [])[1], haTot = y => (mec.ha.find(r => r[0] === y) || [])[2];
  const brT = y => (mec.brecha_tch.find(r => r[0] === y) || [])[1];
  const br20T = mec.brecha_tch.filter(r => r[0] >= 2020 && r[0] <= 2025).map(r => r[1]);
  const haArea = f => conH.filter(f).reduce((x, s) => x + s.a, 0);
  const histSeg = r => { const L = conH.filter(s => r[0] === 'Cosecha' ? s.tipo === r[1] : r[0] === 'Zona' ? 'Zona ' + s.z === r[1] : true),
    a = L.reduce((x, s) => x + s.a, 0); return a ? L.reduce((x, s) => x + s.hist * s.a, 0) / a : R.hist; };   // % de la validación → TCH
  // clima, agua y nivel freático: 2026 frente a lo normal de cada suerte en su mes (ponderado por área)
  const chA = C.soporte['corte-humedo'];
  const humHa2425 = chA && chA.ha ? (chA.ha.filter(r => r[0] === 2024 || r[0] === 2025).reduce((x, r) => x + r[1], 0) / 2) : null;
  const clima = [
    ['Calor: días con más de 32 °C en los 30 días antes del corte', nf(wS('d32')), nf(wS('d32n')), ''],
    ['Sequía: falta de agua sin riego del mes 8 a la cosecha (mm)', nf(wS('dsr'), 0), nf(wS('dsrn'), 0), ''],
    ['<b>Calor y sequía al final del ciclo (una causa)</b>', '', '', ap('clima')],
    ['Riego aplicado al final del ciclo (mm)', nf(wS('rie'), 0), nf(wS('rien'), 0), ap('riego')],
    ['Lluvia de los meses 0-3 del ciclo (mm)', nf(wS('llu'), 0), nf(wS('llun'), 0), ap('lluvia')],
    ['Nivel freático promedio del ciclo (m)', nf(wS('nf'), 2), nf(wS('nfn'), 2), ap('freatico')],
    ['Lluvia en el mes del corte anterior (mm)', chA ? nf(chA.mm[0], 0) : '—', chA ? nf(chA.mm[1], 0) : '—', ap('corte-humedo')]];
  const co = C.soporte.corte, ed = C.soporte.edad, va = C.soporte.variedades;
  // validación por grupos
  const segs = V.segmentos.filter(r => (r[0] === 'Cosecha' || r[0] === 'Zona') && r[1] !== 'nan' && r[1] !== 'sin dato');
  // lo que queda sin explicar suerte por suerte
  const expl = s => C.causas.reduce((x, c) => x + (s.ap[c.id] || 0), 0);
  const masSE = conH.filter(s => s.se != null && Math.abs(s.se) > Math.abs(expl(s))).length;
  const peor = [...conH].sort((a, b) => (b.hist - b.real) - (a.hist - a.real))[0];
  $app.innerHTML = `<article class="doc pila">
    <div class="no-print doc-acciones"><button type="button" class="btn" id="g-pdf">Descargar PDF</button>
      <span class="sub" style="margin:0">Abre la ventana de impresión: elija «Guardar como PDF».</span></div>
    <header class="doc-cab"><h2>Caída del TCH Riopaila 2026: qué pasó y por qué</h2>
      <p class="sub">Cosechas de ${R.periodo} · explicación para la gerencia · cifras vigentes del informe en línea</p></header>

    <p class="doc-lead">El TCH de lo cosechado de ${R.periodo} cayó <b>${nf(R.caida)} TCH (${nf(R.t_caida, 0)} t)</b> frente a lo que esas mismas suertes
      daban en 2020-25. Lo explican sobre todo ${lista(quitan.slice(0, 3))}.
      Todo está calculado con datos medidos y estadística propia, sin calificaciones subjetivas.</p>

    <section><h3>En cifras</h3>
      <div class="tabla"><table><tbody>
        <tr><td>Histórico 2020-25 de las mismas suertes</td><td class="n"><b>${nf(R.hist)}</b> TCH</td></tr>
        <tr><td>Presupuesto 2026 (Maestro de Suertes)</td><td class="n"><b>${nf(P.ppto)}</b> TCH</td></tr>
        <tr><td>Real 2026</td><td class="n"><b>${nf(R.real)}</b> TCH</td></tr>
        <tr><td>Toneladas perdidas frente al histórico</td><td class="n"><b class="t-q">${nf(R.t_caida, 0)}</b> t · ${sg(-R.caida)} TCH</td></tr>
        <tr><td>Toneladas perdidas frente al presupuesto</td><td class="n"><b class="t-q">${nf(P.t, 0)}</b> t · ${sg(P.real - P.ppto)} TCH</td></tr>
      </tbody></table></div>
      <p class="sub" style="margin:6px 0 0">${R.cosechas} cosechas con historia (${nf(R.ha, 0)} ha) de las ${R.cosechas_total} del periodo. Contra el presupuesto, las ${P.cosechas} que tienen PPTO.</p></section>

    <section><h3>Contra el presupuesto, la mayor parte no es caída</h3>
      <p>De los ${nf(brecha)} TCH de brecha contra el presupuesto, <b>${nf(sobre)} TCH (${nf(100 * sobre / brecha, 0)} %)</b> son presupuesto por encima de lo que esas suertes
        dieron en 2020-25: ninguna causa de campo lo explica, es cómo se armó el presupuesto. Solo <b>${nf(caidaP)} TCH (${nf(100 * caidaP / brecha, 0)} %)</b> son caída real.</p></section>

    <section><h3>Por qué cayó</h3>
      ${divergentes(top.map(c => ({ et: c.nombre, v: -c.t_ha })).concat([{ et: 'Sin explicar', v: -R.sin_explicar, color: 'var(--hist)' }]))}
      <p style="margin-top:8px">Por tipo de causa: ${Object.entries(grupos).sort((a, b) => a[1] - b[1]).map(([g, v]) => `<b>${g.toLowerCase()}</b> ${sg(v)} TCH`).join(' · ')}.
        ${suman.length ? `Sumaron ${lista(suman)} (entre paréntesis, por qué: en 2026 hubo menos de lo que resta o más de lo que ayuda que lo normal).` : ''}
        Las causas suman ${sg(-(R.caida - R.sin_explicar))} TCH frente a ${sg(-R.caida)} que cayó.</p>
      <p style="margin-top:10px"><b>Cuánto pesa cada causa en la caída</b> (las ${nf(R.t_caida, 0)} t que se justifican = 100 %)</p>
      ${reparto100().tabla}
      <p class="sub" style="margin:6px 0 0">Las causas que restaron suman más del 100 % y las que sumaron TCH (con % negativo) lo compensan; con lo «sin explicar», el total da exacto el 100 %.</p></section>

    <section><h3>Qué tipo de análisis es</h3>${regresionHtml()}</section>

    <section><h3>Qué se midió en cada causa</h3>
      <p>Cada causa es un dato medido en campo, en estaciones o por satélite, y su peso sale de 7.433 cosechas de Riopaila de 2011 a 2026, comparando cada suerte
        consigo misma. Ninguna causa usa una nota o calificación puesta a mano. El aporte de una causa = su efecto × (nivel de 2026 − nivel normal).</p>
      ${tb(['Causa', 'Qué se midió', 'Cuánto pesa', 'Aporte 2026 (TCH)'],
        [...C.causas].sort((a, b) => b.t_ha - a.t_ha).map(c => [`<b>${esc(c.nombre)}</b><br><span class="sub">${esc(c.grupo)}</span>`, esc(c.mide), esc(c.efecto),
          `<b class="${clsImp(-c.t_ha)}">${sg(-c.t_ha)}</b>`]), [3])}
      <p class="sub" style="margin:6px 0 0">Normal = promedio 2020-25 en los mismos meses de cosecha; para agua y nivel freático, 2022-25 (años con registro); para labores, 2024-25.</p></section>

    <section><h3>Cosecha mecanizada: la causa más grande que depende de nosotros</h3>
      ${mec.partes ? `<p><b>Le quitó ${ap('mecanica')} TCH a la caída</b>: ${sg(-mec.partes['este corte'])} por la cosecha mecanizada de 2026 y ${sg(-mec.partes['corte anterior'])}
        por la cepa que dejó el corte anterior mecanizado. El modelo mide las dos por separado; aquí se presentan como una sola causa.</p>` : ''}
      <p>La cosechadora daña la cepa y genera despoblación. El área con cosecha mecanizada pasó de ${nf(haMec(2023), 0)} ha en 2023 a <b>${nf(haMec(2026), 0)} ha en 2026</b> (de enero a septiembre, de ${nf(haTot(2026), 0)} ha cosechadas),
        y en 2026 una suerte cosechada a máquina dio ${nf(-brT(2026))} TCH menos que a mano (entre 2020 y 2025 la diferencia iba de ${sg(Math.max(...br20T))} a ${sg(Math.min(...br20T))} TCH).
        La soca también lo paga: las suertes que venían de un corte mecanizado cayeron ${nf(-tablaCA('mecánica tras manual')[4])} TCH (primera vez)
        y ${nf(-tablaCA('mecánica seguida')[4])} TCH (dos seguidos) frente a su historia, contra ${nf(-tablaCA('manual')[4])} TCH las de corte manual.</p>
      ${tb(['Año', ...mec.anios.filter(r => r[0] >= 2019).map(r => r[0])], [['Área con cosecha mecanizada (ha)', ...mec.anios.filter(r => r[0] >= 2019).map(r => nf(haMec(r[0]), 0))],
        ['Mecanizada frente a manual (TCH)', ...mec.anios.filter(r => r[0] >= 2019).map(r => brT(r[0]) == null ? '—' : sg(brT(r[0])))]],
        mec.anios.filter(r => r[0] >= 2019).map((_, i) => i + 1))}
      <p style="margin-top:10px"><b>La cepa que deja el corte anterior.</b> ${esc(ca.efecto)}</p>
      ${tb(['Cómo fue el corte anterior', 'Cosechas 2026', 'Área (ha)', 'Cambio del TCH frente a su historia (TCH)'],
        ca.tabla.map(r => [esc(ANT[r[0]] || r[0]), r[1], nf(r[2], 0), `<b class="${clsImp(r[4])}">${sg(r[4])}</b>`]), [1, 2, 3])}
      <p style="margin-top:10px"><b>El satélite lo ve.</b> Después del primer corte mecanizado la soca arranca con menos humedad en el follaje y más rebrote ralo.
        En el bloque 3501 de la hacienda Riopaila (suertes 3501-550, 551, 560 y 561), cosechado a mano en julio de 2024 y mecanizado en julio de 2025 y de 2026,
        se ve a simple vista: después del corte mecanizado la soca sale más clara y con franjas a lo largo de los surcos, por donde pasan la cosechadora y los vagones.
        En toda la cosecha 2026 se comparó la soca de cada suerte a la misma edad después del corte manual y después del primer mecanizado, frente a suertes con
        dos cortes manuales seguidos: a los 2 meses la humedad del follaje empeoró más (señal clara); a los 5 meses ya no se diferenciaba.
        El satélite ve el golpe en el arranque; lo que se pierde en toneladas lo mide la báscula.</p>
      ${al ? `<p><b>Alerta 2027.</b> ${al.n} suertes tuvieron en 2026 su primera cosecha mecanizada.${alNdvi ? ` A los 2 meses, su vigor (NDVI) bajó ${nf(-alNdvi[6], 2)} más que en las de corte manual (señal clara)` : ''};
        con el efecto medido del corte anterior mecanizado, darían en 2027 unas 1.800 t menos, sin contar lo que pierdan si se vuelven a cosechar con máquina.
        Parte de la señal temprana puede ser hojarasca: es una alerta para revisar en campo, no un pronóstico. La lista suerte por suerte, con sus imágenes,
        está en el informe en línea, en la causa «Cosecha mecanizada».</p>` : ''}</section>

    ${DV && DV.mismas ? `<section><h3>Desarrollo de la caña: histórico contra 2026, frente al óptimo de cada variedad</h3>
      <p>El aforo mide la caña en pie antes de la cosecha: tallos por metro (población), longitud, diámetro y peso por tallo. Comparado con el óptimo de su variedad, muestra cuánta caña había para cosechar.</p>
      ${desarrolloHtml(true)}</section>` : ''}
    ${SU && SU.grupos ? `<section><h3>Suelos: grupo de humedad de lo cosechado en 2026</h3>
      ${suelosHtml(true)}</section>` : ''}

    <section><h3>Clima, agua y nivel freático</h3>
      <p>Calor y sequía al final del ciclo, una sola causa, quitaron ${ap('clima')} TCH; el riego devolvió ${ap('riego')}.
        Cada suerte se compara con lo normal de su mes de cosecha.</p>
      ${tb(['Variable', '2026', 'Normal', 'Aporte (TCH)'], clima.map(r => [r[0], `<b>${r[1]}</b>`, r[2], `<b class="${clsImp(parseFloat(String(r[3]).replace('−', '-').replace(',', '.')))}">${r[3]}</b>`]), [1, 2, 3])}
      <p style="margin-top:10px"><b>Por qué van juntas.</b> El calor cuenta los días con más de 32 °C en los 30 días antes del corte: la caña transpira y respira más,
        pierde agua y peso, y no se compensa. La sequía cuenta el agua que faltó (evaporación menos lluvia) del mes 8 del ciclo a la cosecha: con poca agua la caña llena
        menos el tallo, y el riego lo compensa en parte. Las dos entran juntas en el modelo, así que un mes caliente y seco no se cuenta dos veces, y probada la combinación no resta más que la suma (p 0,35); por eso se muestran como una sola causa${causa('clima') && C.soporte.clima ? `, que le quitó más de 0,5 TCH a ${C.soporte.clima.area.unidas[0]} cosechas (${nf(C.soporte.clima.area.unidas[1], 0)} ha), cada una contada una vez` : ''}.
        Algo de estrés de agua al final se busca a propósito para madurar la caña; en 2026 el déficit fue mucho mayor que lo normal y eso ya resta.</p>
      <p><b>Nivel freático.</b> Medido en los 202 pozos del Registro de NF de Ingeniería Agrícola (lecturas cada 15 días), llevado a cada suerte. En promedio fue parecido
        a lo normal, pero ${nf(haArea(s => s.nf != null && s.nf < 1), 0)} ha cosechadas tuvieron el agua a menos de 1 m y ahí sí resta.</p>
      <p><b>Cosecha con suelo húmedo.</b> ${nf(chA && chA.ha ? (chA.ha.find(r => r[0] === 2026) || [])[1] : haArea(s => s.mmca != null && s.mmca >= 100), 0)} ha cosechadas en 2026 venían de un corte hecho en un mes con 100 mm de lluvia
        o más${humHa2425 != null ? `, contra ${nf(humHa2425, 0)} ha por año en 2024-25 (años completos)` : ''}. ${esc(causa('corte-humedo').efecto)}
        Roturar o fertilizar con el suelo húmedo (lluvia en los 5 días antes) se probó y no mostró un efecto confiable.</p>
      ${balanceDoc()}</section>

    ${satDoc()}

    <section><h3>Número de corte, edad de cosecha y variedades</h3>
      ${co ? `<p><b>Número de corte (${ap('corte')} TCH): cada corte resta, pero en 2026 se cosecharon socas más jóvenes.</b> Frente a la plantilla, en la misma suerte: ${co.efecto.map(r => `${r[0]} ${sg(r[2])} TCH`).join(', ')} (sobre el TCH de las plantillas 2020-25, ${nf(co.plantilla_tch)}).
        En 2026 el corte promedio fue ${nf(co.prom[0])} contra ${nf(co.prom[1])} normal.</p>
      ${porQueCorte(co, true)}
      ${tb(['Corte', ...co.mezcla.map(r => r[0])], [['Área 2026 (ha)', ...co.mezcla.map(r => nf(r[3], 0))], ['Normal (ha)', ...co.mezcla.map(r => nf(r[4], 0))]], co.mezcla.map((_, i) => i + 1))}` : ''}
      ${ed ? `<p style="margin-top:10px"><b>Edad de cosecha (${ap('edad')} TCH).</b> En 2026 se cortó con ${nf(ed.prom[0])} meses en promedio, contra ${nf(ed.prom[1])} normal:
        ${nf((ed.e.find(r => r[0] === '12-13') || [])[3], 0)} ha se cortaron entre 12 y 13 meses (normal ${nf((ed.e.find(r => r[0] === '12-13') || [])[4], 0)} ha). Cortar con más edad da más toneladas.</p>` : ''}
      ${va ? `<p style="margin-top:10px"><b>Variedades (${ap('variedades')} TCH): suertes que dejaron la ${esc(va.sale || "")} rinden menos con su nueva variedad.</b></p>${porQueVariedad(va, true)}` : ''}</section>

    <section><h3>Qué tan seguro es</h3>
      <p>Ajustado solo con 2011-2025, sin ver 2026, el modelo predijo el <b>${nf(p.pct, 0)} %</b> de la caída, y año por año desde 2013 se movió con lo real
        (correlación ${nf(V.corr, 2)}). Un modelo que solo se acomoda a los datos no predice nada fuera de ellos. Señala bien dónde cayó más, pero se queda corto en el tamaño:
        el resto es un golpe común del año que ninguna variable medida captura.</p>
      ${RF ? `<p><b>Suerte por suerte, comparado con el PPTO y el aforo.</b></p>${refR2Html()}` : ''}
      ${tb(['Grupo (sin ver 2026)', 'Cosechas', 'Pasó', 'Predijo'], segs.map(r => { const h = histSeg(r); return [r[1].startsWith(r[0]) ? esc(r[1]) : `${esc(r[0])}: ${esc(r[1])}`, r[2], `<span class="${clsImp(r[3])}">${sg(r[3] / 100 * h)} TCH</span>`, `${sg(r[4] / 100 * h)} TCH`]; }), [1, 2, 3])}
      <p style="margin-top:10px">${tb(['Año', ...V.anual.slice(-7).map(r => r[0])], [['Pasó (%)', ...V.anual.slice(-7).map(r => sg(r[1]) + ' %')], ['Predijo sin ver el año (%)', ...V.anual.slice(-7).map(r => sg(r[2]) + ' %')]],
        V.anual.slice(-7).map((_, i) => i + 1))}</p>
      <p class="sub" style="margin:6px 0 0">Cambio de cada año frente a los 6 años anteriores, predicho con un modelo que no vio ese año.</p></section>

    <section><h3>Lo que el modelo no explica</h3>
      <ul style="margin:0;padding-left:20px">
        <li><b>Suerte por suerte queda mucho sin explicar.</b> Entre suertes explica una parte de las diferencias (R² ${V.r2.map(r => nf(r[1], 2)).join(' a ')}).
          En ${masSE} de las ${conH.length} cosechas lo «sin explicar» pesa más que todas las causas medidas juntas.
          ${peor ? `La que más cayó, la ${esc(peor.s)} (${esc(peor.h)}), perdió ${nf(peor.hist - peor.real)} TCH frente a su historia: las variables medidas explican ${nf(expl(peor))} TCH
          y quedan ${nf(peor.se || 0)} TCH sin explicar.` : ''} Cada ficha del informe en línea lo muestra así, sin esconderlo.</li>
        <li><b>Las cifras de cada causa son efectos promedio</b> medidos en 7.433 cosechas, no un diagnóstico de campo de cada suerte.</li>
        <li><b>Falta medir el madurante</b> (dosis en cc por tonelada frente al presupuesto) y confirmar de dónde sale el óptimo de cada variedad.</li>
        <li><b>Lo que no medimos</b> (plagas, compactación, condiciones de la cosecha) cae dentro de lo «sin explicar».</li></ul></section>

    <section><h3>Qué proponemos</h3><ol style="margin:0;padding-left:20px">
      <li><b>Revisar la cosecha mecanizada:</b> el daño a la cepa, sobre todo donde se repite el corte mecanizado, y evitar cortar con el suelo húmedo. Revisar en campo,
        antes de la cosecha 2027, las suertes de la alerta que rebrotaron peor.</li>
      ${SC ? '<li><b>Usar la curva satelital como alerta temprana:</b> cada mes, marcar las suertes de 5 a 7 meses cuyo NDRE está por debajo de su propia normal y revisarlas en campo.</li>' : ''}
      <li><b>Armar el presupuesto 2027 desde el histórico de cada suerte</b>, ajustado por tipo de cosecha y edad.</li>
      <li><b>Seguir la caída mes a mes</b> con el mismo modelo y la misma prueba; medir el madurante y el desarrollo de la caña con el aforo de cada mes.</li>
      <li><b>Conectar el Registro de NF</b> como fuente fija para el nivel freático.</li>
      ${BL ? '<li><b>Evaluar el riego en milímetros</b> frente a la falta de agua del balance hídrico (no en número de riegos) y confirmar con Recursos Hídricos el registro de los riegos desde 2024.</li>' : ''}</ol></section>

    <section><h3>Cómo recorrer el informe en línea</h3><ol style="margin:0;padding-left:20px">
      <li><b>Resumen.</b> Histórico, presupuesto y real; las causas y el puente al presupuesto, con filtros por hacienda, zona, zona agroecológica, variedad, tipo de cosecha y mes.</li>
      <li><b>Causas.</b> Al tocar una causa salen su gráfica de soporte y la lista de suertes que afectó, con su dato.</li>
      <li><b>Desarrollo de la caña.</b> El aforo frente al óptimo de cada variedad: histórico 2023-25 contra 2026, en general y por variedad.</li>
      ${SC ? '<li><b>Satélite del ciclo.</b> La curva de 2026 mes a mes frente a la normal de cada suerte, la falta de agua por edad y las suertes que se quedaron atrás.</li>' : ''}
      <li><b>Suertes y ficha de cada suerte.</b> Cuánto le quitó cada causa y con qué dato, la historia de sus cortes, la lluvia, el calor, el pozo, el satélite y su aforo.</li>
      <li><b>Prueba del modelo.</b> La validación con datos que el modelo no vio.</li></ol></section>

    <section><h3>Fuentes y método</h3>
      ${tb(['Dato', 'Fuente', 'Desde'], [
        ['TCH, tipo de cosecha, corte, edad, variedad', 'ZQM histórico y G&amp;P Suertes 2026', '2011'],
        ['Corte anterior mecanizado', 'Corte anterior de la misma suerte en el ZQM', '2012'],
        ['Calor y lluvia', 'EMA La Paila y Bugalagrande, Meteoportal de Cenicaña y pluviómetros de Riopaila', '2011'],
        ['Déficit de agua y riego', 'Histórico de riego por suerte y evaporación de las EMA', '2022'],
        ['Nivel freático', 'Registro de NF de Ingeniería Agrícola, 202 pozos', 'oct-2020'],
        ['Roturación, herbicida, fertilización', 'Control de roturación, bases de aplicaciones y SimpleAgri', '2024'],
        ['NDVI, NDRE y NDMI', 'Sentinel-2 por Earth Engine, promedio mensual por suerte', '2019'],
        ['Balance hídrico (soporte)', 'Clima mensual de Cenicaña por estación: lluvia y evaporación', '1993'],
        ['Riego aplicado en mm (soporte)', 'Consolidado de riegos del balance hídrico', '2021'],
        ['Aforo (población, altura, diámetro)', 'Base de aforos y tabla de óptimos por variedad', '2023'],
        ['PPTO, zona, hacienda y fecha de corte', 'Maestro de Suertes 2026 (TCH PPTO, columna AG)', '2026']], [2])}
      <p style="margin-top:8px">El modelo es una regresión del TCH (en logaritmo) sobre 7.433 cosechas de Riopaila de 2011 a 2026, ponderada por área, con un nivel propio para
        cada suerte, cada año y cada mes de cosecha, y un efecto para cada variable medida. El aporte de una causa en una suerte es su efecto por la diferencia entre el nivel
        de 2026 y el normal; los aportes más lo «sin explicar» suman exacto la caída.</p></section>

    <p class="sub doc-pie">El detalle de cada causa y de cada suerte está en el informe en línea: <a href="https://caida-tch-yy76h1.vercel.app">caida-tch-yy76h1.vercel.app</a>.</p>
  </article>`;
  document.getElementById('g-pdf').onclick = () => {
    const t = document.title;
    document.title = 'Caida TCH Riopaila 2026 - explicacion para la gerencia';   // nombre del PDF
    window.print();
    document.title = t;
  };
}

// ---------------------------------------------------------------- vista: suertes
function vSuertes() {
  $app.innerHTML = `<div class="pila"><div><h2>Suertes cosechadas en 2026</h2>
    <p class="sub">${S.length} cosechas de enero a septiembre. Toque una para ver por qué cayó o subió.</p></div>
    ${filtrosHtml(FILTRO0)}<div id="t-s"></div></div>`;
  const principal = s => {
    const best = C.causas.map(c => [c, s.ap[c.id] || 0]).sort((a, b) => b[1] - a[1])[0];
    return best && best[1] > 0.5 ? `<a href="#causa/${best[0].id}">${esc(best[0].nombre)}</a> <span class="num t-q">${sg(-best[1])}</span>` : '—';
  };
  const cols = [...colSuerte, { t: 'Zona', f: s => s.z ?? '—', v: s => s.z, asc: true },
    { t: 'Cosecha', f: s => `<span class="chip ${s.tipo === 'Mecanizada' ? 'mec' : ''}">${esc(s.tipo)}</span>`, v: s => s.tipo }, ...colReal,
    { t: 'vs historia', n: true, f: s => `<span class="${clsImp(s.hist == null ? 0 : s.real - s.hist)}">${s.hist == null ? '—' : sg(s.real - s.hist)}</span>`, v: s => s.hist == null ? null : s.real - s.hist, asc: true },
    { t: 'vs PPTO', n: true, f: s => s.ppto == null ? '—' : `<span class="${clsImp(s.real - s.ppto)}">${sg(s.real - s.ppto)}</span>`, v: s => s.ppto == null ? null : s.real - s.ppto, asc: true },
    { t: 'Causa que más le quitó', f: principal, v: null },
    { t: 'Sin explicar', n: true, f: s => sg(imp(s.se)), v: s => imp(s.se), asc: true }];
  const pintar = () => tabla(document.getElementById('t-s'), cols, filtrar(leerFiltros()), { orden: 9, dir: 1 });
  escucharFiltros(pintar);
  pintar();
}

// ---------------------------------------------------------------- vista: ficha de una suerte
const satFoto = (x, t, sub) => `<div class="caja"><h3>${t}</h3><p class="sub" style="margin-bottom:8px">${sub}</p>
  <figure class="sat"><img src="${x.img}" alt="NDVI de la suerte a los ${x.edad} días: ${fecha(x.f1)} y ${fecha(x.f2)}">
  <figcaption>Sentinel-2, NDVI (café = suelo o caña rala, verde oscuro = caña cerrada) · a los ${x.edad} días de cada corte ·
  NDVI ${nf(x.ndvi1, 2)} → ${nf(x.ndvi2, 2)} · rebrote ralo ${nf(x.rala1, 0)} % → ${nf(x.rala2, 0)} %</figcaption></figure></div>`;

function vFicha(k) {
  const s = S.find(x => x.k === k), f = F[k];
  if (!s) { $app.innerHTML = '<p>No encontré esa suerte. <a href="#suertes">Ver todas</a></p>'; return; }
  const otras = S.filter(x => x.s === s.s && x.k !== k);
  const filas = C.causas.map(c => ({ et: c.nombre, v: imp(s.ap[c.id]), dato: dato(c.id, s), href: '#causa/' + c.id }))
    .filter(r => r.v != null && Math.abs(r.v) >= 0.05).sort((a, b) => a.v - b.v);
  const expl = filas.reduce((a, r) => a + r.v, 0);
  const caida = s.hist == null ? null : s.real - s.hist;
  if (s.se != null) filas.push({ et: 'Sin explicar', v: imp(s.se), color: 'var(--hist)', dato: 'Lo que no explica ninguna variable medida: algo que no medimos (madurante, plagas, compactación, manejo de la cosecha) o variación propia de la suerte.' });
  const ej = C.soporte['corte-anterior'].ejemplo.suertes.includes(s.s);
  $app.innerHTML = `<div class="pila">
    <a class="volver" href="#suertes">← Todas las suertes</a>
    <div class="cab"><div><h2>Suerte ${esc(s.s)}${s.k.includes('(') ? ' (segunda cosecha del mes)' : ''}</h2>
      <div class="datos">${[s.h, s.z ? 'Zona ' + s.z : '', s.za ? 'Zona agroecológica ' + s.za : '', SU && SU.suertes[s.s] ? `Suelo ${SU.suertes[s.s][0]} · permeabilidad ${SU.suertes[s.s][1]}` : '',
        HU && HU.cosechas[s.s + '|' + s.m] ? `En 2026 se comportó como ${HU.cosechas[s.s + '|' + s.m][0]}` : '', s.v, 'Corte ' + s.c, nf(s.a, 2) + ' ha', 'Edad ' + nf(s.ed) + ' meses']
        .filter(Boolean).map(t => `<span class="chip">${esc(t)}</span>`).join('')}
        <span class="chip ${s.tipo === 'Mecanizada' ? 'mec' : ''}">${esc(s.tipo)} · ${corteTxt(s)}</span></div></div>
      ${otras.length ? `<div class="sub">Otra cosecha en 2026: ${otras.map(o => `<a href="${hrefS(o.k)}">${esc(o.k)}</a>`).join(', ')}</div>` : ''}</div>
    <div class="caja"><div class="tres">
      <div class="r"><div class="et">Real 2026</div><div class="v num">${nf(s.real)}</div><div class="et">TCH</div></div>
      <div class="h"><div class="et">Historia 2020-25 de la suerte</div><div class="v num">${nf(s.hist)}</div><div class="et ${clsImp(caida)}">${caida == null ? 'sin historia' : sg(caida) + ' TCH frente a la real'}</div></div>
      <div class="p"><div class="et">PPTO 2026 (Maestro)</div><div class="v num">${nf(s.ppto)}</div><div class="et ${clsImp(s.ppto == null ? 0 : s.real - s.ppto)}">${s.ppto == null ? 'sin PPTO' : sg(s.real - s.ppto) + ' TCH frente a la real'}</div></div>
    </div></div>
    <div class="caja porque"><h3>Por qué ${caida == null || caida < 0 ? 'cayó' : 'subió'}: lo que le quitó o sumó cada causa (TCH)</h3>
      ${s.hist == null ? '<p class="sub">Esta suerte no tiene cosechas en 2020-25 para comparar (plantilla nueva o re-suerteo): se muestran sus datos, sin aportes.</p>' :
      `<p class="sub" style="margin-bottom:8px">De ${sg(caida)} TCH, las variables medidas explican ${sg(expl)} TCH${s.se != null ? ` y quedan ${sg(imp(s.se))} TCH sin explicar` : ''}. Toque una causa para ver las demás suertes con el mismo problema.</p>`}
      ${divergentes(filas.length ? filas : C.causas.map(c => ({ et: c.nombre, v: 0, dato: dato(c.id, s) })),
        { max: Math.max(1, ...filas.filter(r => r.et !== 'Sin explicar').map(r => Math.abs(r.v))) })}
      ${s.se != null && Math.abs(s.se) > Math.max(1, ...filas.filter(r => r.et !== 'Sin explicar').map(r => Math.abs(r.v))) ? '<p class="sub" style="margin:6px 0 0">La barra de «Sin explicar» está recortada para que se lean las demás.</p>' : ''}</div>
    <div class="grid2">
      <div class="caja"><h3>Historia de cortes (TCH)</h3><div id="g-hist"></div>
        ${leyenda([['var(--man)', 'Manual'], ['var(--mec)', 'Mecanizada'], ['var(--ink-2)', 'Historia 2020-25', 1], ['var(--ppto-fill)', 'PPTO 2026', 1]])}</div>
      <div class="caja"><h3>Lluvia y calor del ciclo</h3><p class="sub" style="margin-bottom:6px">Del corte anterior a la cosecha. EMA ${esc(s.ema)} (la que usa el modelo)${f.pluv ? ` y pluviómetro ${f.pluv.id}, a ${nf(f.pluv.dist, 0)} m de la suerte` : ''}; la línea es lo normal de la EMA en cada mes (2011-25)</p>
        <div id="g-llu"></div>${leyenda([['var(--hist)', 'Lluvia EMA (mm)'], ...(f.pluv ? [['var(--ink-2)', `Pluviómetro ${f.pluv.id} (mm)`]] : []), ['var(--ink-2)', 'Normal EMA', 1]])}<div id="g-cal"></div>
        ${leyenda([['var(--quita)', 'Días >32 °C'], ['var(--ink-2)', 'Normal', 1]])}</div>
      <div class="caja"><h3>Nivel freático (m de profundidad)</h3>
        <p class="sub" style="margin-bottom:6px">${f.fre && f.fre.l.length ? `Lecturas interpoladas a la suerte; pozo más cercano ${f.fre.pozo} a ${nf(f.fre.dist, 0)} m. Arriba = agua más superficial.` : 'Sin pozo de observación con lecturas cerca de esta suerte.'}</p>
        <div id="g-nf"></div></div>
      <div class="caja"><h3>Satélite: vigor del follaje (NDRE) por mes de edad</h3><p class="sub" style="margin-bottom:6px">Ciclo 2026 frente a los ciclos anteriores de la misma suerte (Sentinel-2, meses despejados)${satBrecha(s)}</p>
        <div id="g-ndvi"></div><div id="ley-sat"></div><h3 style="margin-top:10px">Humedad del follaje (NDMI)</h3><div id="g-ndmi"></div></div>
    </div>
    ${afoFicha(s)}
    ${s.satA ? satFoto(s.satA, 'Satélite: la soca después del corte manual y después del primer corte mecanizado',
       'El corte anterior de esta suerte fue el primero mecanizado. Las dos imágenes muestran la soca a la misma edad después de cada corte.') : ''}
    ${s.satB ? satFoto(s.satB, 'Alerta 2027: la soca que dejó la cosecha mecanizada de 2026',
       'Esta suerte se cosechó mecanizada por primera vez en 2026. Su soca se cosecha en 2027; aquí se compara con la que dejó el último corte manual, a la misma edad.') : ''}
    ${ej ? `<div class="caja">${ejemplo()}</div>` : ''}
  </div>`;
  enlazarFilas($app);
  // historia de cortes
  const h = f.hist;
  grafico(document.getElementById('g-hist'), { x: h.map(r => `${r[0]}`), series: [{ valores: h.map(r => r[4]), colores: h.map(r => r[0] === 2026 ? (r[3] === 'Mec' ? 'var(--quita)' : 'var(--ink-2)') : (r[3] === 'Mec' ? 'var(--mec)' : 'var(--man)')), d: 1 }],
    lineasH: [s.hist != null && { v: s.hist, color: 'var(--ink-2)', dash: true }, s.ppto != null && { v: s.ppto, color: 'var(--ppto-fill)' }].filter(Boolean),
    destacarX: h.length - 1, anchoEt: 40, ymin: 0 });
  // clima
  const L = f.lluvia;
  grafico(document.getElementById('g-llu'), { x: L.map(r => mesAnio(r[0])), series: [{ valores: L.map(r => r[1]), color: 'var(--hist)', d: 0 },
    ...(f.pluv ? [{ valores: L.map(r => r[5]), color: 'var(--ink-2)', d: 0 }] : []), { tipo: 'linea', valores: L.map(r => r[2]), color: 'var(--ink-2)', dash: true, puntos: false }], alto: 190, anchoEt: 56 });
  grafico(document.getElementById('g-cal'), { x: L.map(r => mesAnio(r[0])), series: [{ valores: L.map(r => r[3]), color: 'var(--quita)', d: 0 }, { tipo: 'linea', valores: L.map(r => r[4]), color: 'var(--ink-2)', dash: true, puntos: false }], alto: 150, anchoEt: 56 });
  // freático
  const el = document.getElementById('g-nf');
  if (f.fre && f.fre.l.length) {
    const l = f.fre.l, iIni = l.findIndex(r => r[0] >= f.ini);
    grafico(el, { x: l.map(r => fecha(r[0]).split(' ').slice(1).join(' ')), series: [{ tipo: 'linea', valores: l.map(r => r[1]), color: 'var(--ink)', d: 2 }],
      invertir: true, ymin: 0, ymax: 2, nt: 4, yfmt: v => nf(v, 1), anchoEt: 64, alto: 220,
      bandas: [{ desde: 0, hasta: 0.5, color: '#DC2626', et: 'crítico' }, { desde: 0.5, hasta: 1, color: '#F97316', et: 'subcrítico' },
        { desde: 1, hasta: 1.5, color: '#FEB811', et: 'regular' }, { desde: 1.5, hasta: 2, color: '#16A34A', et: 'bueno' }],
      marcasX: iIni >= 0 ? [{ i: iIni, et: 'corte anterior' }] : [] });
  }
  // satélite
  const ciclos = Object.keys(f.sat || {}).sort();
  if (ciclos.length) {
    const x = Array.from({ length: 14 }, (_, i) => String(i));
    const colorC = c => c === '2026' ? 'var(--quita)' : (f.sat_tipo[c] === 'Mec' ? 'var(--mec)' : 'var(--hist)');
    const serie = (c, j) => ({ tipo: 'linea', valores: x.map((_, i) => (f.sat[c].find(p => p[0] === i) || [])[j] ?? null), color: colorC(c), grosor: c === '2026' ? 3 : 1.6, dash: c !== '2026', d: 2 });
    grafico(document.getElementById('g-ndvi'), { x, series: ciclos.map(c => serie(c, 3)), ymin: 0, ymax: 0.7, nt: 5, yfmt: v => nf(v, 1), ejeX: 'meses de edad', alto: 190, anchoEt: 24 });
    grafico(document.getElementById('g-ndmi'), { x, series: ciclos.map(c => serie(c, 2)), ymin: -0.3, ymax: 0.6, nt: 5, yfmt: v => nf(v, 1), ejeX: 'meses de edad', alto: 170, anchoEt: 24 });
    document.getElementById('ley-sat').innerHTML = leyenda(ciclos.map(c => [colorC(c), c === '2026' ? 'Ciclo cosechado en 2026' : `Ciclo cosechado en ${c} (corte ${f.sat_tipo[c] === 'Mec' ? 'mecanizado' : 'manual'})`, 1]));
  } else document.getElementById('g-ndvi').innerHTML = '<p class="sub">Sin imágenes despejadas para esta suerte.</p>';
}

// ---------------------------------------------------------------- vista: prueba del modelo
// el R² suerte por suerte del modelo frente al del PPTO y el aforo de campo (misma medida); lo usan Prueba y gerencia
function refR2Html() {
  const md = V.r2.map(r => r[1]), ppto = RF.referencias[0], af = RF.referencias[1];
  const r2c = v => `<b class="${v < 0 ? 't-q' : ''}">${v < 0 ? '−' + nf(-v, 2) : nf(v, 2)}</b>`;
  const filas = [
    ['<b>Nuestro modelo</b>, sin haber visto esas suertes (sabe cómo le fue al año)', r2c(md[1] ?? md[0]), '—', '—'],
    ['<b>Nuestro modelo</b>, sin haber visto 2026', r2c(md[0]), '—', '—'],
    [`PPTO del Maestro de Suertes 2026 (${ppto.n} cosechas)`, r2c(ppto.r2), nf(ppto.corr2, 2), `${sg(ppto.sesgo_tch)} TCH`],
    [`Aforo de campo, unos ${af.dias} días antes del corte (${af.n} cosechas)`, r2c(af.r2), nf(af.corr2, 2), `${sg(af.sesgo_tch)} TCH`]];
  return `<p>El R² suerte por suerte mide qué tanto se acierta <b>cuánto cayó o subió cada suerte en 2026 frente a su propia historia</b> (por ejemplo, que una cayó
      40 TCH y la vecina subió 10). Es la prueba más difícil, y en ella el modelo, sin haber visto esas suertes, predice mejor que los dos pronósticos que ya existen:</p>
    <div class="tabla"><table><thead><tr><th>Predicción del cambio de cada suerte</th><th class="n">R²</th><th class="n">Ordena las suertes (r²)</th><th class="n">Sesgo frente a lo real</th></tr></thead>
      <tbody>${filas.map(f => `<tr>${f.map((c, i) => `<td class="${i ? 'n' : ''}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table></div>
    <p style="margin-top:8px">Un R² negativo quiere decir que acierta peor que suponer que todas las suertes cambian igual: el PPTO y el aforo quedaron en promedio
      ${nf(ppto.sesgo_tch)} y ${nf(af.sesgo_tch)} TCH por encima de lo real. Aun quitándoles ese sesgo y mirando solo si ordenan bien las suertes, llegan a ${nf(ppto.corr2, 2)} y ${nf(af.corr2, 2)}:
      ni midiendo la caña en pie unos ${af.dias} días antes del corte se pasa de ~0,3. El cambio de una suerte depende mucho de lo que no se mide (plagas, compactación,
      madurante, cómo se hizo la cosecha, la asignación de toneladas en la báscula); por eso cada ficha muestra lo «sin explicar».
      El modelo sirve para el promedio y los grupos (año por año, correlación ${nf(V.corr, 2)}), no para diagnosticar cada suerte por separado.</p>`;
}

function vPrueba() {
  const p = prediccion(), A = V.anual;
  const acierta = A.filter(r => Math.sign(r[1]) === Math.sign(r[2]) && Math.abs(r[2]) >= 0.05).length;
  const segs = ['Cosecha', 'Zona', 'Zona agroecológica', 'Mes'];
  $app.innerHTML = `<div class="pila"><div><h2>¿El modelo de verdad explica la caída?</h2>
    <p class="sub">Se prueba con datos que el modelo no vio. Si solo se ajustara a 2026, no serviría para predecir.</p></div>
    <div class="kpis">
      <div class="kpi"><div class="et">2026 sin ver 2026</div><div class="v num">${nf(p.pct, 0)} % <small>de la caída</small></div></div>
      <div class="kpi"><div class="et">Años 2013-2026</div><div class="v num">${nf(V.corr, 2)} <small>correlación</small></div></div>
      <div class="kpi"><div class="et">Sentido del año</div><div class="v num">${acierta} de ${A.length}</div></div>
      <div class="kpi"><div class="et">Suerte por suerte</div><div class="v num">R² ${nf(V.r2[1] ? V.r2[1][1] : V.r2[0][1], 2)}</div></div>
    </div>
    ${RF ? `<div class="caja"><h3>¿Es bajo un R² de ${nf(V.r2[1] ? V.r2[1][1] : V.r2[0][1], 2)} suerte por suerte? Comparado con el PPTO y el aforo</h3>${refR2Html()}</div>` : ''}
    <div class="caja"><h3>Cada año predicho con un modelo que no vio ese año (% frente a los 6 años anteriores)</h3><div id="g-anual"></div>
      ${leyenda([['var(--real)', 'Lo que pasó'], ['var(--quita)', 'Lo que predijo sin ver el año']])}
      <p class="sub" style="margin-top:6px">Acierta hacia dónde va el año, pero predice menos tamaño: los años muy buenos o muy malos traen un golpe común que las variables no capturan.</p></div>
    <div class="grid2">
      <div class="caja"><h3>2026 con el modelo ajustado solo con 2011-2025 (TCH)</h3>
        <p class="sub" style="margin-bottom:8px">Predijo ${nf(p.pred)} de ${nf(p.tot)} TCH; ${nf(p.se)} TCH quedan como golpe común del año y ruido.</p>
        ${divergentes([...p.fac.map(f => ({ et: f[0], v: -f[1] })).filter(f => Math.abs(f.v) >= 0.05).sort((a, b) => a.v - b.v), { et: 'Sin explicar', v: -p.se, color: 'var(--hist)' }])}</div>
      <div class="caja"><h3>¿Señala dónde cayó más? (%, sin ver 2026)</h3>
        ${segs.map(d => `<h3 style="margin-top:10px;font-size:14px">${d}</h3><div class="tabla"><table><thead><tr><th>${d}</th><th class="n">Cosechas</th><th class="n">Pasó</th><th class="n">Predijo</th></tr></thead><tbody>
          ${V.segmentos.filter(r => r[0] === d && r[1] !== 'nan' && r[1] !== 'sin dato').map(r => `<tr><td>${esc(r[1])}</td><td class="n">${r[2]}</td><td class="n ${clsImp(r[3])}">${sg(r[3])}</td><td class="n ${clsImp(r[4])}">${sg(r[4])}</td></tr>`).join('')}
          </tbody></table></div>`).join('')}</div>
    </div>
    <div class="nota"><b>Lo que esto no demuestra.</b> El modelo explica bien el promedio y señala los grupos donde cayó más, pero suerte por suerte
      explica una parte (R² ${V.r2.map(r => nf(r[1], 2)).join(' a ')}): cada ficha muestra cuánto queda sin explicar. Tampoco predice el tamaño completo
      de un año extremo. Las cifras de cada causa son efectos promedio medidos en 7.433 cosechas, no un diagnóstico de campo de cada suerte.</div>
  </div>`;
  grafico(document.getElementById('g-anual'), { x: A.map(r => String(r[0])), series: [{ valores: A.map(r => r[1]), color: 'var(--real)' }, { valores: A.map(r => r[2]), color: 'var(--quita)' }], yfmt: v => nf(v, 0), alto: 250, destacarX: A.length - 1 });
}

// ---------------------------------------------------------------- vista: método
function vMetodo() {
  $app.innerHTML = `<div class="pila" style="max-width:860px"><div><h2>Método y fuentes</h2>
    <p class="sub">Todo se calcula con variables medidas y con nuestra propia estadística. No se usa ninguna calificación 1-3-5.</p></div>
    <div class="caja"><h3>Qué se compara</h3><p>Cada suerte cosechada entre enero y septiembre de 2026 frente a su propio promedio de 2020-25
      (media geométrica). Así no se mezcla una suerte buena con una mala: la caída es de la misma suerte contra sí misma.
      El PPTO es el TCH PPTO del Maestro de Suertes 2026 (columna AG), por suerte.</p></div>
    <div class="caja"><h3>Qué tipo de análisis es</h3>${regresionHtml()}</div>
    <div class="caja"><h3>Variables y fuentes</h3><div class="tabla"><table><thead><tr><th>Variable</th><th>Fuente</th><th>Desde</th></tr></thead><tbody>
      <tr><td>TCH, tipo de cosecha, corte, edad, variedad</td><td>ZQM histórico + G&amp;P 2026</td><td>2011</td></tr>
      <tr><td>Corte anterior mecanizado</td><td>El corte anterior de la misma suerte en el ZQM</td><td>2012</td></tr>
      <tr><td>Calor y lluvia</td><td>EMA La Paila y Bugalagrande (+ Meteoportal de Cenicaña en 2026)</td><td>2011</td></tr>
      <tr><td>Balance hídrico y riego</td><td>Histórico de riego por suerte + evaporación y lluvia de las EMA</td><td>2022</td></tr>
      <tr><td>Nivel freático</td><td>Registro de NF de Ingeniería Agrícola: 202 pozos, lecturas quincenales, interpoladas a cada suerte (pozos a menos de 1,5 km)</td><td>oct-2020</td></tr>
      <tr><td>Roturación, herbicida, fertilización</td><td>Control de roturación, bases de aplicaciones y SimpleAgri</td><td>2024</td></tr>
      <tr><td>Renovación no hecha</td><td>Plan de renovación 2025</td><td>2025</td></tr>
      <tr><td>NDVI, NDRE y NDMI</td><td>Sentinel-2 (Earth Engine), promedio mensual de cada suerte</td><td>2019</td></tr>
      <tr><td>PPTO, zona, hacienda, fecha de corte</td><td>Maestro de Suertes 2026</td><td>—</td></tr>
    </tbody></table></div></div>
    <div class="caja"><h3>Qué cambió frente a la versión anterior</h3><ul style="margin:0;padding-left:20px">
      <li>Se quitaron todas las calificaciones 1-3-5 del AgroFactors: ninguna nota subjetiva entra en el cálculo.</li>
      <li>Se agregó el corte anterior mecanizado (la cepa que deja la cosechadora), con su soporte de satélite.</li>
      <li>Se agregó el nivel freático medido en los pozos, en metros, en lugar de una nota.</li>
      <li>El presupuesto es el del Maestro de Suertes 2026.</li></ul></div>
    <div class="caja"><h3>Pendiente</h3><p style="margin:0"><b>Madurante.</b> Se va a medir con la dosis aplicada en cc por tonelada frente a la base de 12 cc/t,
      cuando esté la fuente con las dosis por suerte.</p></div>
    <div class="caja"><h3>Cómo se actualiza</h3><p style="margin:0">Programas en <i>01 Estimados y TCH / Caida TCH 2026 - programas</i>, en este orden:
      factores_sep → freatico_suertes → riego, labores, roturación, malezas, no renovadas → caida_integrada_rio → tablero_datos →
      validacion_modelo → informe_datos. Luego se vuelve a publicar esta página.</p></div>
  </div>`;
}

// ---------------------------------------------------------------- rutas
function ruta(redibujo) {
  if (!R) return;  // los datos todavía no llegan
  const h =decodeURIComponent(location.hash.slice(1)) || 'resumen';
  const [v, ...resto] = h.split('/'), arg = resto.join('/');
  document.querySelectorAll('nav.tabs a').forEach(a => {
    const on = a.dataset.v === v || (a.dataset.v === 'suertes' && v === 'suerte');
    on ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current');
  });
  const titulo = { resumen: 'Resumen', gerencia: 'Para la gerencia', causa: 'Causas', desarrollo: 'Desarrollo de la caña', suelos: 'Suelos y humedad', satelite: 'Satélite del ciclo', suertes: 'Suertes', suerte: 'Suerte ' + arg.split(' ')[0], prueba: 'Prueba del modelo', metodo: 'Método' }[v];
  document.title = `${titulo ? titulo + ' · ' : ''}Caída del TCH Riopaila 2026`;
  if (v === 'causa') vCausa(arg);
  else if (v === 'gerencia') vGerencia();
  else if (v === 'desarrollo') vDesarrollo();
  else if (v === 'suelos') vSuelos();
  else if (v === 'satelite') vSatelite();
  else if (v === 'suertes') vSuertes();
  else if (v === 'suerte') vFicha(arg);
  else if (v === 'prueba') vPrueba();
  else if (v === 'metodo') vMetodo();
  else vResumen();
  if (!redibujo && h !== vistaActual) window.scrollTo(0, 0);
  vistaActual = h;
}

let tRes;
window.addEventListener('resize', () => { clearTimeout(tRes); tRes = setTimeout(() => { if (!document.activeElement || document.activeElement.tagName !== 'INPUT') ruta(true); }, 200); });
window.addEventListener('hashchange', () => ruta());

Promise.all(['resumen', 'causas', 'suertes', 'fichas', 'validacion', 'escenas_bloque3501'].map(n => fetch(`data/${n}.json`, { cache: 'no-cache' }).then(r => {
  if (!r.ok) throw new Error(`${n}.json: ${r.status}`); return r.json();
})).concat(['desarrollo', 'balance', 'referencias', 'suelos', 'humedad', 'satciclo'].map(n => fetch(`data/${n}.json`, { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null))))
  .then(([r, c, s, f, v, e, d, b, rf, su, hu, sc]) => {
    R = r; C = c; S = s; F = f; V = v; E = e; DV = d; BL = b; RF = rf; SU = su; HU = hu; SC = sc;
    if (DV) DV.filas.forEach(x => AFO[x.s + '|' + x.m] = x);
    ruta();
  })
  .catch(err => { $app.innerHTML = `<p>No se pudieron cargar los datos (${esc(err.message)}). Recargue la página.</p>`; });
