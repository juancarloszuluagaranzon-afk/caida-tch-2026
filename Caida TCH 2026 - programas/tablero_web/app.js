/* Informe navegable «Caída del TCH Riopaila 2026».
   Datos en data/*.json (informe_datos.py). Rutas: #resumen · #causa/<id> · #suertes · #suerte/<clave> · #prueba · #metodo */
'use strict';

const $app = document.getElementById('app');
let R, C, S, F, V, E, CAUSA, SUERTE;
let DV = null, AFO = {};   // aforo frente al óptimo de la variedad (desarrollo.json, desarrollo_optimo.py); opcional
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
    case 'mecanica': return s.tipo === 'Mecanizada' ? `Cosecha mecanizada${s.f ? ' el ' + fecha(s.f) : ''}` : 'Cosecha manual';
    case 'corte-anterior': return `Corte anterior: ${ANT[s.ant] || s.ant}${s.ant_f ? ` (${mesAnio(s.ant_f)}${s.ant_tch ? ', ' + nf(s.ant_tch) + ' TCH' : ''})` : ''}`;
    case 'corte-humedo': return s.mmca == null ? 'Sin dato de lluvia del corte anterior' : `${nf(s.mmca, 0)} mm de lluvia en el mes del corte anterior${s.ant_f ? ' (' + mesAnio(s.ant_f) + ')' : ''}: suelo ${s.mmca >= 100 ? 'húmedo' : 'seco'} · EMA ${s.ema}`;
    case 'calor': return `${nf(s.d32, 0)} días >32 °C en los 30 días antes del corte (normal en ${mesN}: ${nf(s.d32n, 0)}) · EMA ${s.ema}`;
    case 'sequia': return s.dsr == null ? 'Sin dato de riego en ese ciclo' : `Déficit sin riego ${nf(s.dsr, 0)} mm (normal en ${mesN}: ${nf(s.dsrn, 0)}); riego ${nf(s.rie, 0)} mm`;
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
  'calor': [{ t: 'Días >32 °C', n: true, f: s => nf(s.d32, 0), v: s => s.d32 }, { t: 'Normal del mes', n: true, f: s => nf(s.d32n, 0), v: s => s.d32n },
    { t: 'EMA', f: s => esc(s.ema), v: s => s.ema }],
  'sequia': [{ t: 'Déficit sin riego (mm)', n: true, f: s => nf(s.dsr, 0), v: s => s.dsr }, { t: 'Normal', n: true, f: s => nf(s.dsrn, 0), v: s => s.dsrn },
    { t: 'Riego (mm)', n: true, f: s => nf(s.rie, 0), v: s => s.rie }],
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
    html = caja('Área con cosecha mecanizada (%)', 'Riopaila, por año de cosecha (2026 = enero a septiembre)') +
      caja('Cuánto rindió la cosecha mecanizada frente a la manual (% de TCH)', 'Misma suerte, mismo año; efecto estimado por el modelo') + seg('Cosecha') +
      (sp.alerta2027 ? satAlerta(sp.alerta2027) : '');
    specs = [{ x: sp.anios.map(r => r[0]), series: [{ valores: sp.anios.map(r => r[1]), colores: sp.anios.map(r => r[0] === 2026 ? 'var(--quita)' : 'var(--hist)'), etiquetas: true, d: 0 }], destacarX: sp.anios.length - 1, yfmt: v => nf(v, 0) },
      { x: sp.brecha.map(r => r[0]), series: [{ valores: sp.brecha.map(r => r[1]), colores: sp.brecha.map(r => r[0] === 2026 ? 'var(--quita)' : 'var(--hist)'), etiquetas: true, d: 1 }], alto: 200 }];
  } else if (id === 'corte-anterior') {
    const mx = Math.max(...sp.tabla.map(r => Math.abs(r[3])));
    html = `<div><h3>Suertes cosechadas en 2026 frente a su propia historia 2015-25, según cómo fue el corte anterior</h3>
      ${divergentes(sp.tabla.map(r => ({ et: `${ANT[r[0]] || r[0]} · ${r[1]} cosechas`, v: r[3], color: r[0].startsWith('mec') ? 'var(--quita)' : r[3] < 0 ? 'var(--hist)' : 'var(--suma)' })), { max: mx })}
      <p class="sub" style="margin-top:6px">Cambio del TCH en %. Las que venían de un corte mecanizado cayeron casi el doble.</p></div>` + afoCorte() +
      caja('El satélite lo ve: NDVI de la soca frente a la que salió de corte manual', 'Diferencia por mes de edad, misma suerte y mismo mes del año (3.500 ciclos 2019-2026)',
        leyenda([['var(--quita)', 'Corte anterior mecanizado, primera vez', 1], ['var(--mec)', 'Mecanizado repetido', 1]])) +
      caja('NDMI (humedad del follaje), igual', '', leyenda([['var(--quita)', 'Primera vez', 1], ['var(--mec)', 'Repetido', 1]])) +
      (sp.cosecha2026 ? satCosecha(sp.cosecha2026) : '') + ejemplo();
    const x = sp.sat.map(r => r[0] + ' m');
    specs = [{ x, series: [{ tipo: 'linea', valores: sp.sat.map(r => r[1]), color: 'var(--quita)', d: 3 }, { tipo: 'linea', valores: sp.sat.map(r => r[2]), color: 'var(--mec)', dash: true, d: 3 }], yfmt: v => nf(v, 2), ejeX: 'meses de edad de la soca', alto: 210 },
      { x, series: [{ tipo: 'linea', valores: sp.sat.map(r => r[3]), color: 'var(--quita)', d: 3 }, { tipo: 'linea', valores: sp.sat.map(r => r[4]), color: 'var(--mec)', dash: true, d: 3 }], yfmt: v => nf(v, 2), ejeX: 'meses de edad de la soca', alto: 210 }];
  } else if (id === 'calor') {
    html = caja('Días con más de 32 °C en los 30 días antes del corte', 'Promedio de las cosechas de cada mes', leyMes) +
      caja('Días con más de 32 °C por mes · EMA La Paila', 'Desde julio de 2024; la línea es el promedio 2011-25 de ese mes', leyenda([['var(--quita)', 'Ese mes'], ['var(--ink-2)', 'Normal', 1]]));
    specs = [porMes('días'), { x: sp.ema.map(r => mesAnio(r[0])), series: [{ valores: sp.ema.map(r => r[1]), color: 'var(--quita)', d: 0 }, { tipo: 'linea', valores: sp.ema.map(r => r[2]), color: 'var(--ink-2)', dash: true, puntos: false }], anchoEt: 56 }];
  } else if (id === 'lluvia') {
    html = caja('Lluvia de los meses 0-3 del ciclo (mm)', 'Promedio de las cosechas de cada mes', leyMes) +
      caja('Lluvia por mes · EMA La Paila (mm)', 'Desde julio de 2024; la línea es el promedio 2011-25 de ese mes', leyenda([['var(--hist)', 'Ese mes'], ['var(--ink-2)', 'Normal', 1]]));
    specs = [porMes('mm'), { x: sp.ema.map(r => mesAnio(r[0])), series: [{ valores: sp.ema.map(r => r[1]), color: 'var(--hist)', d: 0 }, { tipo: 'linea', valores: sp.ema.map(r => r[2]), color: 'var(--ink-2)', dash: true, puntos: false }], anchoEt: 56 }];
  } else if (id === 'sequia' || id === 'riego') {
    html = caja(id === 'sequia' ? 'Déficit de agua sin riego al final del ciclo (mm)' : 'Lámina de riego al final del ciclo (mm)', 'Promedio de las cosechas de cada mes; normal = 2022-25 (años con registro de riego)', leyMes);
    specs = [porMes('mm')];
  } else if (id === 'freatico') {
    html = caja('Área de Riopaila con el nivel freático a menos de 1 m (%)', 'Cada lectura quincenal de los pozos de observación, interpolada a cada suerte') +
      caja('Nivel promedio del ciclo de las suertes cosechadas (m)', 'Promedio de las cosechas de cada mes; normal = 2022-25', leyMes);
    const t = sp.tiempo;
    specs = [{ x: t.map(r => fecha(r[0]).split(' ').slice(1).join(' ')), series: [{ valores: t.map(r => r[1]), color: 'var(--quita)', d: 0 }], anchoBarra: 0.9, anchoEt: 64, yfmt: v => nf(v, 0) },
      { ...porMes('m', 2), yfmt: v => nf(v, 1) }];
  } else if (id === 'variedades') {
    html = caja('Área cosechada por variedad (%)', '2026 frente a 2020-25 (mismos meses)', leyMes);
    specs = [{ x: sp.v.map(r => r[0].replace('CC ', '')), series: [{ valores: sp.v.map(r => r[2]), color: 'var(--hist)' }, { valores: sp.v.map(r => r[1]), color: 'var(--quita)' }], anchoEt: 64 }];
  } else if (id === 'corte-humedo') {
    html = caja('Área cuyo corte anterior se hizo con el suelo húmedo (%)', `Mes del corte con 100 mm de lluvia o más · por año de cosecha. Lluvia promedio en el mes del corte anterior: 2026 ${nf(sp.mm[0], 0)} mm, normal ${nf(sp.mm[1], 0)} mm`);
    specs = [{ x: sp.anios.map(r => r[0]), series: [{ valores: sp.anios.map(r => r[1]), colores: sp.anios.map(r => r[0] === 2026 ? 'var(--quita)' : 'var(--hist)'), etiquetas: true, d: 0 }], destacarX: sp.anios.length - 1, yfmt: v => nf(v, 0) }];
  } else if (id === 'corte') {
    html = caja('Lo que pierde la soca en cada corte (% de TCH frente a la plantilla)', 'Misma suerte; efecto medido en 7.433 cosechas 2011-2026') +
      caja('Área cosechada por número de corte (%)', `Promedio: 2026 ${nf(sp.prom[0])} cortes · normal ${nf(sp.prom[1])} cortes. Más segundos cortes y menos socas de 6 o más.`, leyMes);
    specs = [{ x: sp.efecto.map(r => r[0]), series: [{ valores: sp.efecto.map(r => r[1]), color: 'var(--quita)', etiquetas: true, d: 1 }], yfmt: v => nf(v, 0), alto: 210 },
      { x: sp.mezcla.map(r => r[0]), series: [{ valores: sp.mezcla.map(r => r[2]), color: 'var(--hist)' }, { valores: sp.mezcla.map(r => r[1]), color: 'var(--quita)' }], anchoEt: 64, yfmt: v => nf(v, 0) }];
  } else if (id === 'edad') {
    html = caja('Área cosechada por edad (%)', `Edad promedio: 2026 ${nf(sp.prom[0])} meses · normal ${nf(sp.prom[1])} meses`, leyMes);
    specs = [{ x: sp.e.map(r => r[0]), series: [{ valores: sp.e.map(r => r[2]), color: 'var(--hist)' }, { valores: sp.e.map(r => r[1]), color: 'var(--quita)' }], ejeX: 'meses' }];
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

function seg(dim) {
  const rows = V.segmentos.filter(r => r[0] === dim);
  return `<div><h3>2026 frente a la historia, por tipo de cosecha (%)</h3>${divergentes(rows.map(r => ({ et: `${r[1]} · ${r[2]} cosechas`, v: r[3], dato: `el modelo sin ver 2026 predijo ${sg(r[4])} %` })))}</div>`;
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

function vCausa(id) {
  const c = C.causas.find(x => x.id === id) || C.causas[0];
  const grupos = ['No controlable', 'Agronómico y operativo', 'Flujo de caja'];
  const lista = grupos.map(g => `<div class="g">${g}</div>` + C.causas.filter(x => x.grupo === g).sort((a, b) => b.t_ha - a.t_ha)
    .map(x => `<a href="#causa/${x.id}" ${x.id === c.id ? 'aria-current="true"' : ''}><span>${esc(x.nombre)}</span><span class="num ${clsImp(-x.t_ha)}">${sg(-x.t_ha, 2)}</span></a>`).join('')).join('');
  const conH = S.filter(s => s.hist != null);
  const mx = Math.max(0.5, ...conH.map(s => Math.abs(s.ap[c.id] || 0)));
  const nAf = conH.filter(s => (s.ap[c.id] || 0) > 0.5).length, nFa = conH.filter(s => (s.ap[c.id] || 0) < -0.5).length;
  $app.innerHTML = `<div class="causas"><nav class="lista-causas" aria-label="Causas">${lista}</nav>
    <section class="pila">
      <div class="caja"><span class="chip">${esc(c.grupo)}</span>
        <h2 style="margin-top:8px">${esc(c.nombre)}</h2>
        <div class="cifra num ${clsImp(-c.t_ha)}">${sg(-c.t_ha, 2)} TCH <span style="font-size:15px;font-weight:400;color:var(--muted)">en promedio · ${sg(-c.t_ha * R.ha, 0)} t en ${nf(R.ha, 0)} ha</span></div>
        <p style="margin:10px 0 4px"><b>Qué mide.</b> ${esc(c.mide)}</p>
        <p style="margin:0"><b>Cuánto pesa.</b> ${esc(c.efecto)} Medido en 7.433 cosechas de 2011 a 2026, cada suerte frente a sí misma.</p>
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
const MEDO = { pob: 'Población', alt: 'Altura', dia: 'Diámetro', peso: 'Peso de caña' };
const UNI = { pob: 'tallos/m', alt: 'cm', dia: 'cm' };

let filtroDes = { ...FILTRO0 };
function vDesarrollo() {
  if (!DV) { $app.innerHTML = '<p>No están los datos del aforo (desarrollo.json).</p>'; return; }
  $app.innerHTML = `<div class="pila">
    <div><h2>¿La caña tuvo el desarrollo óptimo de su variedad?</h2>
      <p class="sub" id="des-sub"></p></div>
    ${filtrosHtml(filtroDes)}<div id="des-cuerpo" class="pila"></div></div>`;
  escucharFiltros(() => { filtroDes = leerFiltros(); pintarDesarrollo(filtroDes); });
  pintarDesarrollo(filtroDes);
}

function pintarDesarrollo(f) {
  const filtrado = textoFiltro(f), base = filtrar(f), rows = base.filter(afo).map(s => ({ s, r: afo(s) }));
  const ha = rows.reduce((x, o) => x + o.s.a, 0);
  const pond = (L, fn) => { const a = L.reduce((x, o) => x + o.s.a, 0); return a ? L.reduce((x, o) => x + fn(o) * o.s.a, 0) / a : null; };
  const bajo = (L, k) => 100 * L.filter(o => pctO(o.r, k) < 95).reduce((x, o) => x + o.s.a, 0) / L.reduce((x, o) => x + o.s.a, 0);
  document.getElementById('des-sub').innerHTML = `${filtrado ? `Filtro: <b>${esc(filtrado)}</b> · ` : ''}${rows.length} de ${base.length} cosechas con aforo y óptimo de su variedad (${nf(ha, 0)} ha).
    Aforo de la caña en pie antes de la cosecha, frente al óptimo de su variedad.${filtrado ? ' <button type="button" id="des-limpiar" class="limpiar">Quitar filtros</button>' : ''}`;
  const lim = document.getElementById('des-limpiar');
  if (lim) lim.onclick = () => { filtroDes = { ...FILTRO0 }; vDesarrollo(); };
  const $c = document.getElementById('des-cuerpo');
  if (!rows.length) { $c.innerHTML = '<div class="nota">Ninguna cosecha con aforo cumple el filtro.</div>'; return; }
  const kpi = (k, sub) => { const v = pond(rows, o => k === 'peso' ? pesoO(o.r) : pctO(o.r, k));
    return `<div class="kpi"><div class="et">${MEDO[k]} frente al óptimo</div><div class="v num ${clsO(v)}">${nf(v, 0)} <small>%</small></div><div class="pie">${sub}</div></div>`; };
  // peso de caña frente al óptimo y cambio del TCH frente a la historia
  const G = [['Menos de 80 %', 0, 80], ['80-90 %', 80, 90], ['90-100 %', 90, 100], ['100-110 %', 100, 110], ['110 % o más', 110, 1e9]];
  const conH = rows.filter(o => o.s.hist != null);
  const grupos = G.map(([et, lo, hi]) => { const L = conH.filter(o => pesoO(o.r) >= lo && pesoO(o.r) < hi);
    return L.length ? { et: `${et} · ${L.length} cosechas`, v: 100 * (pond(L, o => o.s.real) / pond(L, o => o.s.hist) - 1),
      dato: `${nf(L.reduce((x, o) => x + o.s.a, 0), 0)} ha · historia ${nf(pond(L, o => o.s.hist))} → real ${nf(pond(L, o => o.s.real))} TCH` } : null; }).filter(Boolean);
  // por variedad
  const vars = {};
  rows.forEach(o => (vars[o.r.v] = vars[o.r.v] || []).push(o));
  const tv = Object.entries(vars).sort((a, b) => b[1].reduce((x, o) => x + o.s.a, 0) - a[1].reduce((x, o) => x + o.s.a, 0));
  const celda = v => `<td class="n"><span class="${clsO(v)}">${nf(v, 0)} %</span></td>`;
  // corte anterior (modelo con todas las suertes)
  const pr = (k, ant) => DV.pruebas.find(x => x.k === k && x.ant === ant);
  const celdaP = x => `<td class="n"><span class="${x.p < 0.05 ? clsImp(x.dif) : ''}">${sg(x.dif)} pts</span> <span class="sub">(${x.p < 0.05 ? 'p = ' + nf(x.p, 2) : 'no confiable'})</span></td>`;
  const tc = k => DV.tch.find(x => x.y === 'y_hist' && x.k === k);
  $c.innerHTML = `${rows.length < 20 ? `<div class="nota"><b>Pocas cosechas.</b> Son ${rows.length} cosechas con aforo: los promedios dependen de unas pocas suertes.</div>` : ''}
    <div class="kpis">${kpi('pob', `${nf(bajo(rows, 'pob'), 0)} % del área por debajo de 95 %`)}${kpi('alt', `${nf(bajo(rows, 'alt'), 0)} % del área por debajo de 95 %`)}
      ${kpi('dia', `${nf(bajo(rows, 'dia'), 0)} % del área por debajo de 95 %`)}${kpi('peso', 'tallos × altura × diámetro²')}</div>
    <div class="grid2">
      <div class="caja"><h3>Menos caña que el óptimo, más caída del TCH</h3>
        <p class="sub" style="margin-bottom:8px">Cosechas agrupadas por su peso de caña frente al óptimo de su variedad · cambio del TCH real frente a su historia 2020-25 (%)</p>
        ${divergentes(grupos)}
        <p class="sub" style="margin:10px 0 0">En la misma variedad, cada 1 % de población por debajo del óptimo va con ${nf(tc('pob').coef, 1)} % menos de TCH;
          altura ${nf(tc('alt').coef, 1)} % y diámetro ${nf(tc('dia').coef, 1)} % (todas las suertes, sin filtro).</p></div>
      <div class="caja"><h3>Según el corte anterior</h3>
        <p class="sub" style="margin-bottom:8px">Diferencia frente a las que venían de corte manual, en puntos de % del óptimo, misma variedad y zona (todas las suertes, sin filtro).
          El aforo se mide antes de la cosecha de 2026: la población que encuentra la dejó el corte anterior.</p>
        <div class="tabla"><table><thead><tr><th>Medida</th><th class="n">Mecanizado, primera vez</th><th class="n">Mecanizado, repetido</th></tr></thead><tbody>
          ${['p_pob', 'p_alt', 'p_dia', 'p_peso'].map(k => `<tr><td>${MEDO[k.slice(2)]}</td>${celdaP(pr(k, 'mecánica tras manual'))}${celdaP(pr(k, 'mecánica seguida'))}</tr>`).join('')}
        </tbody></table></div></div>
    </div>
    <div class="caja"><h3>Por variedad</h3>
      <p class="sub" style="margin-bottom:8px">% del óptimo de cada variedad, ponderado por área. Rojo: más de 5 % por debajo; verde: más de 5 % por encima.</p>
      <div class="tabla"><table><thead><tr><th>Variedad</th><th class="n">Cosechas</th><th class="n">Área (ha)</th><th class="n">Población</th><th class="n">Altura</th><th class="n">Diámetro</th><th class="n">Peso de caña</th><th class="n">Óptimo (tallos/m · cm · cm)</th></tr></thead><tbody>
        ${tv.map(([v, L]) => `<tr><td>${esc(v)}</td><td class="n">${L.length}</td><td class="n">${nf(L.reduce((x, o) => x + o.s.a, 0), 0)}</td>
          ${celda(pond(L, o => pctO(o.r, 'pob')))}${celda(pond(L, o => pctO(o.r, 'alt')))}${celda(pond(L, o => pctO(o.r, 'dia')))}${celda(pond(L, o => pesoO(o.r)))}
          <td class="n sub">${nf(L[0].r.opob)} · ${nf(L[0].r.oalt, 0)} · ${nf(L[0].r.odia, 2)}</td></tr>`).join('')}
      </tbody></table></div></div>
    <div class="caja"><h3>Suertes</h3><p class="sub" style="margin-bottom:8px">Ordenadas de menos a más caña frente al óptimo. Toque una para ver su ficha.</p><div id="t-des"></div></div>
    <div class="nota"><b>Lo que esto no demuestra.</b> El desarrollo de la caña no es una causa más: es el camino por el que actúan el calor, la sequía
      o la cosecha mecanizada, por eso no entra en la gráfica de causas (se contaría dos veces). La relación con el TCH es en parte obvia, porque el aforo
      estima las toneladas. El óptimo de cada variedad viene de la tabla de óptimos (columnas de promedio: si es un promedio y no un máximo, 95 % está cerca de lo normal).
      La matriz no trae la edad de cada aforo. Sin aforo: ${DV.sin_aforo} cosechas; sin óptimo de su variedad: ${esc(DV.sin_optimo.join(', '))}.</div>`;
  enlazarFilas($c);
  tabla(document.getElementById('t-des'), [...colSuerte, { t: 'Variedad', f: s => esc(afo(s).v), v: s => afo(s).v, asc: true },
    { t: 'Corte anterior', f: s => esc(ANT[s.ant] || s.ant), v: s => s.ant },
    ...['pob', 'alt', 'dia'].map(k => ({ t: MEDO[k], n: true, f: s => `<span class="${clsO(pctO(afo(s), k))}">${nf(pctO(afo(s), k), 0)} %</span>`, v: s => pctO(afo(s), k), asc: true })),
    { t: 'Peso de caña', n: true, f: s => `<b class="${clsO(pesoO(afo(s)))}">${nf(pesoO(afo(s)), 0)} %</b>`, v: s => pesoO(afo(s)), asc: true },
    { t: 'TCH real', n: true, f: s => nf(s.real), v: s => s.real },
    { t: 'vs historia', n: true, f: s => s.hist == null ? '—' : `<span class="${clsImp(s.real - s.hist)}">${sg(s.real - s.hist)}</span>`, v: s => s.hist == null ? null : s.real - s.hist, asc: true }],
    rows.map(o => o.s), { orden: 8, dir: 1 });
}

// recuadro de la ficha: el aforo de la suerte frente al óptimo de su variedad
function afoFicha(s) {
  const r = afo(s);
  if (!r) return DV ? `<div class="caja"><h3>Desarrollo de la caña frente al óptimo</h3><p class="sub" style="margin:0">Esta cosecha no tiene aforo en la matriz o su variedad no tiene óptimo.</p></div>` : '';
  const fila = k => `<tr><td>${MEDO[k]} (${UNI[k]})</td><td class="n">${nf(r[k], k === 'alt' ? 0 : k === 'dia' ? 2 : 1)}</td><td class="n">${nf(r['o' + k], k === 'alt' ? 0 : k === 'dia' ? 2 : 1)}</td>
    <td class="n"><b class="${clsO(pctO(r, k))}">${nf(pctO(r, k), 0)} %</b></td></tr>`;
  return `<div class="caja"><h3>Desarrollo de la caña frente al óptimo de ${esc(r.v)}</h3>
    <p class="sub" style="margin-bottom:8px">Aforo de la caña en pie antes de la cosecha. Rojo: más de 5 % por debajo del óptimo.</p>
    <div class="tabla"><table><thead><tr><th>Medida</th><th class="n">Aforo</th><th class="n">Óptimo</th><th class="n">% del óptimo</th></tr></thead><tbody>
      ${fila('pob')}${fila('alt')}${fila('dia')}
      <tr><td><b>Peso de caña</b> (tallos × altura × diámetro²)</td><td></td><td></td><td class="n"><b class="${clsO(pesoO(r))}">${nf(pesoO(r), 0)} %</b></td></tr>
    </tbody></table></div><p class="sub" style="margin:6px 0 0"><a href="#desarrollo">Ver todas las suertes y variedades</a></p></div>`;
}

// recuadro de la causa «Corte anterior mecanizado»: lo que encontró el aforo
function afoCorte() {
  if (!DV) return '';
  const pr = (k, ant) => DV.pruebas.find(x => x.k === k && x.ant === ant);
  const filas = [['p_peso', 'Peso de caña'], ['p_alt', 'Altura'], ['p_pob', 'Población'], ['p_dia', 'Diámetro']];
  return `<div><h3>El aforo también lo ve: menos caña donde el corte anterior fue mecanizado</h3>
    <p class="sub" style="margin-bottom:8px">Aforo de la caña en pie de ${DV.filas.length} cosechas 2026, como % del óptimo de su variedad; diferencia frente a las que
      venían de corte manual, misma variedad y zona (puntos de %).</p>
    ${divergentes(filas.flatMap(([k, et]) => [['mecánica tras manual', 'primera vez'], ['mecánica seguida', 'repetido']].map(([a, t]) => {
      const x = pr(k, a); return { et: `${et} · ${t}`, v: x.dif, color: x.p < 0.05 ? (x.dif < 0 ? 'var(--quita)' : 'var(--suma)') : 'var(--hist)',
        dato: x.p < 0.05 ? `confiable (p = ${nf(x.p, 2)})` : `no confiable (p = ${nf(x.p, 2)})` }; })), { max: 10 })}
    <p class="sub" style="margin-top:6px">Gris = la diferencia no es confiable. Tres mediciones distintas (báscula, satélite y aforo) apuntan en la misma dirección.
      <a href="#desarrollo">Ver el desarrollo de la caña</a></p></div>`;
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
      <div class="datos">${[s.h, s.z ? 'Zona ' + s.z : '', s.za ? 'Zona agroecológica ' + s.za : '', s.v, 'Corte ' + s.c, nf(s.a, 2) + ' ha', 'Edad ' + nf(s.ed) + ' meses']
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
      <div class="caja"><h3>Satélite: vigor (NDVI) por mes de edad</h3><p class="sub" style="margin-bottom:6px">Ciclo 2026 frente a los ciclos anteriores de la misma suerte (Sentinel-2, meses despejados)</p>
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
    grafico(document.getElementById('g-ndvi'), { x, series: ciclos.map(c => serie(c, 1)), ymin: 0, ymax: 1, nt: 5, yfmt: v => nf(v, 1), ejeX: 'meses de edad', alto: 190, anchoEt: 24 });
    grafico(document.getElementById('g-ndmi'), { x, series: ciclos.map(c => serie(c, 2)), ymin: -0.3, ymax: 0.6, nt: 5, yfmt: v => nf(v, 1), ejeX: 'meses de edad', alto: 170, anchoEt: 24 });
    document.getElementById('ley-sat').innerHTML = leyenda(ciclos.map(c => [colorC(c), c === '2026' ? 'Ciclo cosechado en 2026' : `Ciclo cosechado en ${c} (corte ${f.sat_tipo[c] === 'Mec' ? 'mecanizado' : 'manual'})`, 1]));
  } else document.getElementById('g-ndvi').innerHTML = '<p class="sub">Sin imágenes despejadas para esta suerte.</p>';
}

// ---------------------------------------------------------------- vista: prueba del modelo
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
    <div class="caja"><h3>El modelo</h3><p>Una regresión del logaritmo del TCH sobre 7.433 cosechas de Riopaila de 2011 a 2026, ponderada por área,
      con un efecto fijo para cada suerte (su nivel propio), para cada año y para cada mes de cosecha. Sobre eso, cada variable medida tiene su efecto.
      El aporte de una causa en una suerte = efecto × (su nivel en 2026 − el nivel normal). Los aportes de todas las causas más lo «sin explicar» suman exacto la caída de la suerte.</p></div>
    <div class="caja"><h3>Variables y fuentes</h3><div class="tabla"><table><thead><tr><th>Variable</th><th>Fuente</th><th>Desde</th></tr></thead><tbody>
      <tr><td>TCH, tipo de cosecha, corte, edad, variedad</td><td>ZQM histórico + G&amp;P 2026</td><td>2011</td></tr>
      <tr><td>Corte anterior mecanizado</td><td>El corte anterior de la misma suerte en el ZQM</td><td>2012</td></tr>
      <tr><td>Calor y lluvia</td><td>EMA La Paila y Bugalagrande (+ Meteoportal de Cenicaña en 2026)</td><td>2011</td></tr>
      <tr><td>Balance hídrico y riego</td><td>Histórico de riego por suerte + evaporación y lluvia de las EMA</td><td>2022</td></tr>
      <tr><td>Nivel freático</td><td>Registro de NF de Ingeniería Agrícola: 202 pozos, lecturas quincenales, interpoladas a cada suerte (pozos a menos de 1,5 km)</td><td>oct-2020</td></tr>
      <tr><td>Roturación, herbicida, fertilización</td><td>Control de roturación, bases de aplicaciones y SimpleAgri</td><td>2024</td></tr>
      <tr><td>Renovación no hecha</td><td>Plan de renovación 2025</td><td>2025</td></tr>
      <tr><td>NDVI y NDMI</td><td>Sentinel-2 (Earth Engine), promedio mensual de cada suerte</td><td>2019</td></tr>
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
  const titulo = { resumen: 'Resumen', causa: 'Causas', desarrollo: 'Desarrollo de la caña', suertes: 'Suertes', suerte: 'Suerte ' + arg.split(' ')[0], prueba: 'Prueba del modelo', metodo: 'Método' }[v];
  document.title = `${titulo ? titulo + ' · ' : ''}Caída del TCH Riopaila 2026`;
  if (v === 'causa') vCausa(arg);
  else if (v === 'desarrollo') vDesarrollo();
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
})).concat(fetch('data/desarrollo.json', { cache: 'no-cache' }).then(r => r.ok ? r.json() : null).catch(() => null)))
  .then(([r, c, s, f, v, e, d]) => {
    R = r; C = c; S = s; F = f; V = v; E = e; DV = d;
    if (DV) DV.filas.forEach(x => AFO[x.s + '|' + x.m] = x);
    ruta();
  })
  .catch(err => { $app.innerHTML = `<p>No se pudieron cargar los datos (${esc(err.message)}). Recargue la página.</p>`; });
