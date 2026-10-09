// Cache-busting build token. Locally the literal "2026-10-08" is a harmless
// query string; at publish time webapp/publish-stamp.mjs rewrites every
// occurrence in index.html and app.js to the bundle build value.
const BUILD = "2026-10-09l";

const CODED_COLS = ["econ_eval_type", "design_basis", "model_label", "qaly_label",
  "oa_label", "geo_scope", "era", "topic_domain"];

// HTML-escapes a string for HTML sinks. Plotly renders hover `text` and
// hovertemplate output as HTML, so every data-derived string concatenated into
// hover text must pass through esc() first.
export function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// R-compatible round(x, digits) — half-to-even resolved on the EXACT binary
// value of the double, matching R >= 4.0.0 (DATA_CONTRACT.md §12). x is
// decomposed exactly into sign * m * 2^e from its IEEE-754 bits; |x| * 10^d is
// kept as the exact BigInt rational num/den; the half-to-even integer
// q = round(num/den) is computed with no floating-point error at all; the
// result is the correctly-rounded double q / 10^d.
// Proofs (verified against R 4.4.1): round(2.675, 2) = 2.67 (the stored double
// is BELOW the midpoint), round(0.125, 2) = 0.12 (exact in binary, tie -> even),
// round(0.135, 2) = 0.14 (the stored double is ABOVE the midpoint).
export function rRound(x, digits = 0) {
  if (x == null || !isFinite(x)) return x;
  if (x === 0) return x;
  const d = Math.trunc(digits);

  const dv = new DataView(new ArrayBuffer(8));
  dv.setFloat64(0, x);
  const hi = dv.getUint32(0), lo = dv.getUint32(4);
  const negative = (hi >>> 31) === 1;
  const biasedExp = (hi >>> 20) & 0x7ff;
  const frac = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo >>> 0);
  let m, e;
  if (biasedExp === 0) {
    m = frac; e = -1074;                                  // subnormal
  } else {
    m = (1n << 52n) | frac; e = biasedExp - 1023 - 52;    // normal: |x| = m * 2^e
  }

  // num/den = |x| * 10^d, exact
  let num = m, den = 1n;
  if (d >= 0) num *= 10n ** BigInt(d); else den *= 10n ** BigInt(-d);
  if (e >= 0) num *= 2n ** BigInt(e); else den *= 2n ** BigInt(-e);

  // half-to-even quotient
  let q = num / den;
  const twice = (num % den) * 2n;
  if (twice > den || (twice === den && q % 2n === 1n)) q += 1n;
  if (negative) q = -q;

  return Number(q) / Math.pow(10, d);
}

export function fmtNum(x) {
  if (x == null) return "";
  return Number(x).toLocaleString("en-US");
}

function num(v) {
  return (typeof v === "number" && isFinite(v)) ? v : null;
}

function ratio(n, d) {
  const dd = num(d);
  return (dd != null && dd > 0) ? n / dd : null;
}

function sortedYearObj(map) {
  const out = {};
  for (const y of [...map.keys()].sort((a, b) => a - b)) out[y] = map.get(y);
  return out;
}

// Builds the ordered label→column registries (DATA_CONTRACT.md §15.6) from
// content.json. Map preserves insertion order, so selector/legend order is the
// content.json array order. Replaces the previously hardcoded TREND_VARS /
// COMP_VARS / STACK_VARS / MAP_METRICS / SCAT_X / SCAT_Y / SIGNAL_METRICS.
export function buildRegistries(content) {
  if (!content || !content.registries) {
    throw new Error("buildRegistries: content.json with .registries is required");
  }
  const r = content.registries;
  const toMap = arr => new Map(arr.map(o => [o.label, o.column]));
  return {
    TREND_VARS: toMap(r.trend_vars),
    COMP_VARS: toMap(r.comp_vars),
    STACK_VARS: toMap(r.stack_vars),
    MAP_METRICS: toMap(r.map_metrics),
    SCAT_X: toMap(r.scat_x),
    SCAT_Y: toMap(r.scat_y),
    SIGNAL_METRICS: r.signal_metrics.slice()
  };
}

export function loadData({ dict, studies, geo, disease, countries, content }) {
  const levels = dict.levels;
  const codeOf = {};
  for (const col of CODED_COLS) {
    codeOf[col] = new Map(levels[col].map((lab, i) => [lab, i]));
  }
  const pal = dict.meta.pal_inc;
  const palInc = {};
  if (Array.isArray(pal)) dict.meta.inc_lv.forEach((lv, i) => { palInc[lv] = pal[i]; });
  else Object.assign(palInc, pal);
  Object.assign(palInc, LANDSCAPE_INCOME_COLORS);
  const diseaseSets = dict.disease_grps.map(() => new Set());
  for (let i = 0; i < disease.s.length; i++) diseaseSets[disease.g[i]].add(disease.s[i]);
  return {
    dict, levels, studies, geo, disease, countries,
    content,
    registries: buildRegistries(content),
    nStudies: studies.id.length,
    codeOf,
    palInc,
    incLv: dict.meta.inc_lv.slice(),
    incOrder: dict.meta.inc_lv.slice().reverse(),
    incomeOf: countries.map(r => r.income),
    regionOf: countries.map(r => r.un_region),
    disease_grps: dict.disease_grps,
    diseaseSets,
    years: dict.years
  };
}

export function normalizeFilter(filt, db) {
  const f = filt || {};
  const one = v => Array.isArray(v) ? (v.length ? v[0] : "All") : (v == null ? "All" : v);
  const arr = v => Array.isArray(v) ? v : (v == null ? [] : [v]);
  return {
    years: f.years ? [f.years[0], f.years[1]] : (db ? db.years.slice() : [2010, 2026]),
    income: arr(f.income),
    region: arr(f.region),
    disease: arr(f.disease),
    evaltype: arr(f.evaltype),
    design: arr(f.design),
    model: one(f.model),
    qaly: one(f.qaly),
    oa: one(f.oa),
    scope: one(f.scope)
  };
}

export function applyFilters(db, filt) {
  const f = normalizeFilter(filt, db);
  const st = db.studies;
  const n = db.nStudies;
  const [lo, hi] = f.years;
  const base = new Uint8Array(n);

  const evalCodes = f.evaltype.length
    ? new Set(f.evaltype.map(l => db.codeOf.econ_eval_type.get(l))) : null;
  const designCodes = f.design.length
    ? new Set(f.design.map(l => db.codeOf.design_basis.get(l))) : null;
  const modelCode = f.model !== "All" ? db.codeOf.model_label.get(f.model) : null;
  const qalyCode = f.qaly !== "All" ? db.codeOf.qaly_label.get(f.qaly) : null;
  const oaCode = f.oa !== "All" ? db.codeOf.oa_label.get(f.oa) : null;
  const scopeCode = f.scope !== "All" ? db.codeOf.geo_scope.get(f.scope) : null;
  let disSet = null;
  if (f.disease.length) {
    disSet = new Set();
    for (const g of f.disease) {
      const gi = db.disease_grps.indexOf(g);
      if (gi >= 0) for (const s of db.diseaseSets[gi]) disSet.add(s);
    }
  }

  for (let s = 0; s < n; s++) {
    const y = st.year[s];
    if (y < lo || y > hi) continue;
    if (evalCodes && !evalCodes.has(st.econ_eval_type[s])) continue;
    if (designCodes && !designCodes.has(st.design_basis[s])) continue;
    if (modelCode !== null && st.model_label[s] !== modelCode) continue;
    if (qalyCode !== null && st.qaly_label[s] !== qalyCode) continue;
    if (oaCode !== null && st.oa_label[s] !== oaCode) continue;
    if (scopeCode !== null && st.geo_scope[s] !== scopeCode) continue;
    if (disSet && !disSet.has(s)) continue;
    base[s] = 1;
  }

  const g = db.geo;
  const incSet = f.income.length ? new Set(f.income) : null;
  const regSet = f.region.length ? new Set(f.region) : null;
  const countryFilterActive = !!(incSet || regSet);
  const geoRows = [];
  const geoStudySet = countryFilterActive ? new Set() : null;
  for (let i = 0; i < g.s.length; i++) {
    const s = g.s[i];
    if (!base[s]) continue;
    const c = g.c[i];
    if (incSet && !incSet.has(db.incomeOf[c])) continue;
    if (regSet) {
      const r = db.regionOf[c];
      if (r == null || !regSet.has(r)) continue;
    }
    geoRows.push(i);
    if (geoStudySet) geoStudySet.add(s);
  }

  const studies = [];
  const mask = new Uint8Array(n);
  for (let s = 0; s < n; s++) {
    if (!base[s]) continue;
    if (geoStudySet && !geoStudySet.has(s)) continue;
    studies.push(s);
    mask[s] = 1;
  }

  const counts = new Int32Array(db.countries.length);
  for (const i of geoRows) counts[g.c[i]]++;
  const present = [];
  const rest = [];
  for (let c = 0; c < db.countries.length; c++) {
    if (counts[c] > 0) present.push(c); else rest.push(c);
  }
  present.sort((a, b) => db.countries[a].iso3 < db.countries[b].iso3 ? -1
    : db.countries[a].iso3 > db.countries[b].iso3 ? 1 : 0);
  const byCountry = present.concat(rest).map(c => {
    const r = db.countries[c];
    const dalys = num(r.dalys);
    const spend = num(r.total_spend_bn);
    const pop = num(r.pop);
    return {
      c,
      iso3: r.iso3,
      country: r.country,
      income: r.income,
      un_region: r.un_region,
      pop: pop,
      dalys: dalys,
      total_spend_bn: spend,
      studies: counts[c],
      per100k: ratio(counts[c], dalys == null ? null : dalys / 1e5),
      per_bn: ratio(counts[c], spend),
      per_million: ratio(counts[c], pop == null ? null : pop / 1e6)
    };
  });

  return { filt: f, mask, studies, geoRows, byCountry };
}

export function valueBoxes(db, flt) {
  const n = flt.studies.length;
  const cs = new Set();
  for (const i of flt.geoRows) cs.add(db.geo.c[i]);
  const mCode = db.codeOf.model_label.get("Model-based");
  const qCode = db.codeOf.qaly_label.get("Uses QALY");
  let m = 0, q = 0;
  for (const s of flt.studies) {
    if (db.studies.model_label[s] === mCode) m++;
    if (db.studies.qaly_label[s] === qCode) q++;
  }
  return {
    v_studies: n,
    v_countries: cs.size,
    v_model_pct: n ? rRound(100 * m / n) : null,
    v_qaly_pct: n ? rRound(100 * q / n) : null
  };
}

export function trendSeries(db, flt, varName) {
  if (varName === "none") {
    const counts = new Map();
    for (const s of flt.studies) {
      const y = db.studies.year[s];
      counts.set(y, (counts.get(y) || 0) + 1);
    }
    return sortedYearObj(counts);
  }
  const isGeo = varName === "income" || varName === "un_region";
  const counts = new Map();
  const bump = (y, cat) => {
    let m = counts.get(y);
    if (!m) { m = new Map(); counts.set(y, m); }
    m.set(cat, (m.get(cat) || 0) + 1);
  };
  if (isGeo) {
    const seen = new Set();
    for (const i of flt.geoRows) {
      const s = db.geo.s[i], y = db.geo.y[i], c = db.geo.c[i];
      const cat = varName === "income" ? db.incomeOf[c] : db.regionOf[c];
      if (cat == null) continue;
      const key = s + "|" + y + "|" + cat;
      if (seen.has(key)) continue;
      seen.add(key);
      bump(y, cat);
    }
  } else {
    const lv = db.levels[varName];
    for (const s of flt.studies) {
      bump(db.studies.year[s], lv[db.studies[varName][s]]);
    }
  }
  const out = {};
  for (const y of [...counts.keys()].sort((a, b) => a - b)) {
    out[y] = Object.fromEntries(counts.get(y));
  }
  return out;
}

function studyCatGetter(db, varName) {
  const st = db.studies;
  if (varName === "icer_label") return s => st.has_icer[s] === 1 ? "ICER reported" : "Not reported";
  if (varName === "thresh_label") return s => st.has_threshold[s] === 1 ? "Threshold reported" : "Not reported";
  const lv = db.levels[varName];
  const col = st[varName];
  return s => lv[col[s]];
}

export function compCounts(db, flt, xv, sv, mode) {
  const pct = mode === "pct";
  const stacked = !!(sv && sv !== xv);
  const counts = new Map();
  const add = (cat, stk) => {
    if (cat == null) return;
    if (!stacked) {
      counts.set(cat, (counts.get(cat) || 0) + 1);
    } else {
      if (stk == null) return;
      let m = counts.get(cat);
      if (!m) { m = new Map(); counts.set(cat, m); }
      m.set(stk, (m.get(stk) || 0) + 1);
    }
  };

  if (xv === "grp") {
    const stackOf = stacked ? studyCatGetter(db, sv) : null;
    const d = db.disease;
    for (let i = 0; i < d.s.length; i++) {
      const s = d.s[i];
      if (!flt.mask[s]) continue;
      add(db.disease_grps[d.g[i]], stacked ? stackOf(s) : null);
    }
  } else {
    const catOf = studyCatGetter(db, xv);
    const stackOf = stacked ? studyCatGetter(db, sv) : null;
    for (const s of flt.studies) add(catOf(s), stacked ? stackOf(s) : null);
  }

  const cmpStr = (a, b) => a < b ? -1 : a > b ? 1 : 0;

  if (!stacked) {
    const rows = [...counts.entries()].map(([x, nn]) => ({ x, n: nn }));
    rows.sort((a, b) => cmpStr(a.x, b.x));
    const total = rows.reduce((a, r) => a + r.n, 0);
    for (const r of rows) r.v = pct ? (total > 0 ? 100 * r.n / total : 0) : r.n;
    rows.sort((a, b) => b.v - a.v);
    return { type: "simple", rows, total, pct };
  }

  const cats = [...counts.keys()].sort(cmpStr);
  const totals = new Map();
  for (const c of cats) {
    let t = 0;
    for (const v of counts.get(c).values()) t += v;
    totals.set(c, t);
  }
  const catOrder = cats.slice()
    .sort((a, b) => (totals.get(a) - totals.get(b)) || cmpStr(a, b))
    .reverse();
  const stackSet = new Set();
  for (const c of cats) for (const k of counts.get(c).keys()) stackSet.add(k);
  const stacks = [...stackSet].sort(cmpStr);
  const rawCounts = {};
  const values = {};
  for (const c of cats) {
    rawCounts[c] = Object.fromEntries(counts.get(c));
    values[c] = {};
    for (const [k, nn] of counts.get(c)) {
      values[c][k] = pct ? (totals.get(c) > 0 ? 100 * nn / totals.get(c) : 0) : nn;
    }
  }
  return { type: "stacked", catOrder, stacks, counts: rawCounts, values, totals: Object.fromEntries(totals), pct };
}

export function byCountryTop(db, flt, k = 10) {
  const rows = flt.byCountry.filter(r => r.studies > 0);
  rows.sort((a, b) => b.studies - a.studies);
  return rows.slice(0, k).map(r => ({
    iso3: r.iso3,
    studies: r.studies,
    per100k: r.per100k,
    per_bn: r.per_bn,
    per_million: r.per_million
  }));
}

export function scatterPoints(db, flt, xv, yv) {
  return flt.byCountry.filter(r =>
    r.studies > 0 &&
    r[xv] != null && r[xv] > 0 &&
    r[yv] != null && r[yv] > 0 &&
    r.income != null);
}

export function tableRows(db, flt, k = 25) {
  const rows = flt.byCountry.filter(r => r.studies > 0);
  rows.sort((a, b) => b.studies - a.studies);
  return rows.slice(0, k).map(r => ({
    Country: r.country,
    Income: r.income,
    Region: r.un_region == null ? "" : r.un_region,
    Studies: r.studies,
    "Per 100k DALYs": r.per100k == null ? null : rRound(r.per100k, 2),
    "Per US$1bn": r.per_bn == null ? null : rRound(r.per_bn, 2),
    "Per million": r.per_million == null ? null : rRound(r.per_million, 2)
  }));
}

const cmpStr = (a, b) => a < b ? -1 : a > b ? 1 : 0;

function profileSets(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const income = db.countries[ci].income;
  const g = db.geo;
  const cs = new Set(), ps = new Set();
  for (let i = 0; i < g.s.length; i++) {
    const c = g.c[i], s = g.s[i];
    if (c === ci) cs.add(s);
    if (db.incomeOf[c] === income) ps.add(s);
  }
  return { ci, income, cs, ps };
}

function methodsMixSets(db, cs, ps) {
  const lv = db.levels.econ_eval_type;
  const col = db.studies.econ_eval_type;
  const cn = new Map(), pn = new Map();
  for (const s of cs) { const t = lv[col[s]]; cn.set(t, (cn.get(t) || 0) + 1); }
  for (const s of ps) { const t = lv[col[s]]; pn.set(t, (pn.get(t) || 0) + 1); }
  const nc = cs.size, np = ps.size;
  const rows = [...new Set([...cn.keys(), ...pn.keys()])].map(t => ({
    type: t,
    country_share: nc > 0 ? 100 * (cn.get(t) || 0) / nc : null,
    peer_share: np > 0 ? 100 * (pn.get(t) || 0) / np : null
  }));
  const y_order = rows.slice()
    .sort((a, b) => ((b.peer_share == null ? 0 : b.peer_share) -
                     (a.peer_share == null ? 0 : a.peer_share)) || cmpStr(a.type, b.type))
    .map(r => r.type);
  rows.sort((a, b) => y_order.indexOf(a.type) - y_order.indexOf(b.type));
  return { rows, y_order };
}

export function methodsMix(db, iso3) {
  const sets = profileSets(db, iso3);
  return sets ? methodsMixSets(db, sets.cs, sets.ps) : null;
}

function signalCounts(db, set) {
  const st = db.studies;
  const mCode = db.codeOf.model_label.get("Model-based");
  const qCode = db.codeOf.qaly_label.get("Uses QALY");
  const oaCode = db.codeOf.oa_label.get("Open access");
  const unkCode = db.codeOf.oa_label.get("Unknown");
  let m = 0, q = 0, ic = 0, th = 0, oaKnown = 0, oa = 0;
  for (const s of set) {
    if (st.model_label[s] === mCode) m++;
    if (st.qaly_label[s] === qCode) q++;
    if (st.has_icer[s] === 1) ic++;
    if (st.has_threshold[s] === 1) th++;
    const o = st.oa_label[s];
    if (o !== unkCode) { oaKnown++; if (o === oaCode) oa++; }
  }
  return { n: set.size, m, q, ic, th, oaKnown, oa };
}

function signalsSets(db, cs, ps) {
  const c = signalCounts(db, cs), p = signalCounts(db, ps);
  const whole = (k, cc) => cc.n > 0 ? 100 * cc[k] / cc.n : null;
  const oaPct = cc => cc.oaKnown > 0 ? 100 * cc.oa / cc.oaKnown : null;
  const val = (metric, cc) => {
    if (metric === "Model-based") return whole("m", cc);
    if (metric === "Uses QALY") return whole("q", cc);
    if (metric === "Reports ICER") return whole("ic", cc);
    if (metric === "Reports threshold") return whole("th", cc);
    return oaPct(cc);
  };
  const rows = db.registries.SIGNAL_METRICS.map(metric => ({
    metric, country_pct: val(metric, c), peer_pct: val(metric, p)
  }));
  return { rows, country_oa_n: c.oaKnown, peer_oa_n: p.oaKnown };
}

export function signals(db, iso3) {
  const sets = profileSets(db, iso3);
  return sets ? signalsSets(db, sets.cs, sets.ps) : null;
}

export function benchmark(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const income = db.countries[ci].income;
  const rows = [];
  for (const r of db.countries) {
    if (r.income !== income) continue;
    const dalys = num(r.dalys), per100k = num(r.per100k_dalys);
    if (dalys == null || per100k == null || dalys <= 0 || per100k <= 0) continue;
    rows.push({ iso3: r.iso3, country: r.country, studies: r.studies, dalys, per100k });
  }
  rows.sort((a, b) => cmpStr(a.iso3, b.iso3));
  const v = rows.map(r => r.per100k).sort((a, b) => a - b);
  const mid = v.length >> 1;
  const median_per100k = !v.length ? null
    : (v.length % 2 ? v[mid] : (v[mid - 1] + v[mid]) / 2);
  const selected = rows.some(r => r.iso3 === iso3) ? iso3 : null;
  return { rows, median_per100k, n_points: rows.length, selected };
}

export function countryProfile(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const r = db.countries[ci];
  const peers = db.countries.filter(x => x.income === r.income);
  const n_peer = peers.length;
  const median = vals => {
    const v = vals.map(num).filter(x => x != null).sort((a, b) => a - b);
    if (!v.length) return null;
    const m = v.length >> 1;
    return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
  };
  const medians = {
    m_daly: median(peers.map(x => x.per100k_dalys)),
    m_bn: median(peers.map(x => x.per_bn_usd)),
    m_mil: median(peers.map(x => x.per_million))
  };

  const g = db.geo;
  const cTrendCountry = new Map();
  const cTrendPeer = new Map();
  const mineSet = new Set();
  const peerSet = new Set();
  for (let i = 0; i < g.s.length; i++) {
    const c = g.c[i], y = g.y[i], s = g.s[i];
    if (c === ci) {
      cTrendCountry.set(y, (cTrendCountry.get(y) || 0) + 1);
      mineSet.add(s);
    }
    if (db.incomeOf[c] === r.income) {
      cTrendPeer.set(y, (cTrendPeer.get(y) || 0) + 1);
      peerSet.add(s);
    }
  }
  const peerTrend = {};
  for (const y of [...cTrendPeer.keys()].sort((a, b) => a - b)) {
    peerTrend[y] = cTrendPeer.get(y) / n_peer;
  }

  const mixC = {}, mixP = {};
  let totC = 0, totP = 0;
  const d = db.disease;
  for (let i = 0; i < d.s.length; i++) {
    const s = d.s[i];
    const grp = db.disease_grps[d.g[i]];
    if (mineSet.has(s)) { mixC[grp] = (mixC[grp] || 0) + 1; totC++; }
    if (peerSet.has(s)) { mixP[grp] = (mixP[grp] || 0) + 1; totP++; }
  }
  const shares = (o, t) => {
    const out = {};
    for (const k of Object.keys(o).sort()) out[k] = t > 0 ? 100 * o[k] / t : 0;
    return out;
  };

  const mm = methodsMixSets(db, mineSet, peerSet);
  const sg = signalsSets(db, mineSet, peerSet);
  const bm = benchmark(db, iso3);

  return {
    iso3: r.iso3,
    income: r.income,
    un_region: r.un_region,
    c_n: r.studies,
    c_daly: num(r.per100k_dalys),
    c_spend: num(r.per_bn_usd),
    c_percap: num(r.per_million),
    medians,
    n_peer,
    c_trend: { country: sortedYearObj(cTrendCountry), peer: peerTrend },
    c_mix: { country: shares(mixC, totC), peer: shares(mixP, totP) },
    c_methods: Object.assign(
      Object.fromEntries(mm.rows.map(x => [x.type,
        { country_share: x.country_share, peer_share: x.peer_share }])),
      { y_order: mm.y_order }),
    c_signals: Object.assign(
      Object.fromEntries(sg.rows.map(x => [x.metric,
        { country_pct: x.country_pct, peer_pct: x.peer_pct }])),
      { country_oa_n: sg.country_oa_n, peer_oa_n: sg.peer_oa_n }),
    c_benchmark: { median_per100k: bm.median_per100k, n_points: bm.n_points, rows: bm.rows }
  };
}

export function countryFacts(db, iso3) {
  const r = db.countries.find(x => x.iso3 === iso3);
  if (!r) return [];
  const pop = num(r.pop), dalys = num(r.dalys), spend = num(r.total_spend_bn);
  const pairs = [
    ["Income group", r.income],
    ["UN region", r.un_region == null ? "—" : r.un_region]
  ];
  if (pop != null) pairs.push(["Population", fmtNum(rRound(pop / 1e6)) + " M"]);
  if (dalys != null) pairs.push(["Disease burden", fmtNum(rRound(dalys / 1e6)) + " M DALYs (2023)"]);
  if (spend != null) pairs.push(["Health spending", "US$ " + fmtNum(rRound(spend)) + " bn (PPP 2022)"]);
  pairs.push(["Studies per million", rRound(num(r.per_million), 2)]);
  return pairs;
}

// ---- Country landscape tab (DATA_CONTRACT.md §16) --------------------------
// The interaction design is adapted from suvarnapande/hff-landscape @
// 6bc2b0c90349e78450fae45a70cfc4ac085a587d (reference-only; no code copied
// verbatim). The tab is UNFILTERED: it reads only the precomputed unfiltered
// countries.json columns and the raw geo/disease/studies tables, and never
// touches the Explorer filter state.

// Per-country bubble-scatter rows. Guard order mirrors §10.5: studies > 0,
// usable burden, usable per-100k intensity, non-null income.
export function landscapePoints(db) {
  const pts = [];
  for (let c = 0; c < db.countries.length; c++) {
    const r = db.countries[c];
    if (r.studies <= 0) continue;
    const dalys = num(r.dalys);
    const per100k = num(r.per100k_dalys);
    if (dalys == null || dalys <= 0) continue;
    if (per100k == null || per100k <= 0) continue;
    if (r.income == null) continue;
    const spend = num(r.total_spend_bn);
    const pop = num(r.pop);
    pts.push({
      c,
      iso3: r.iso3,
      country: r.country,
      income: r.income,
      studies: r.studies,
      dalys,
      per100k,
      per_bn: num(r.per_bn_usd),
      per_million: num(r.per_million),
      spend_per_person: (spend != null && pop != null && pop > 0) ? spend * 1e9 / pop : null
    });
  }
  return pts;
}

// Picker options for the landscape tab: every country with at least one study,
// name-ascending. Exported so the harness can assert the option set without a
// DOM. The tab stays unfiltered: this chooses which country's panels are shown,
// not which studies are counted.
export function landscapeCountries(db) {
  return db.countries
    .filter(r => r.studies > 0)
    .map(r => ({ iso3: r.iso3, country: r.country, studies: r.studies }))
    .sort((a, b) => a.country.localeCompare(b.country));
}

// Country mixes and the disease-group × evaluation-type cross grid (§16.6).
// CS(c) = distinct geo.s with geo.c === c (equals countries[c].studies).
// cell(gi, ei) = | CS ∩ dSet(gi) ∩ eSet(ei) |, keyed by the string gi + "|" + ei
// with both 0-based integer codes. Mix rows sort count-descending, ties
// alphabetical; the cross grid follows those row/column orders.
export function countryMixes(db, iso3) {
  const ci = db.countries.findIndex(r => r.iso3 === iso3);
  if (ci < 0) return null;
  const g = db.geo;
  const cs = new Set();
  for (let i = 0; i < g.s.length; i++) if (g.c[i] === ci) cs.add(g.s[i]);

  const lv = db.levels.econ_eval_type;
  const evalCounts = new Map();
  for (const s of cs) {
    const t = lv[db.studies.econ_eval_type[s]];
    evalCounts.set(t, (evalCounts.get(t) || 0) + 1);
  }
  const evalMix = [...evalCounts.entries()]
    .map(([label, count]) => ({ label, code: lv.indexOf(label), count }))
    .sort((a, b) => (b.count - a.count) || cmpStr(a.label, b.label));

  const d = db.disease;
  const diseaseCounts = new Map();
  for (let i = 0; i < d.s.length; i++) {
    const s = d.s[i];
    if (!cs.has(s)) continue;
    diseaseCounts.set(d.g[i], (diseaseCounts.get(d.g[i]) || 0) + 1);
  }
  const diseaseMix = [...diseaseCounts.entries()]
    .map(([code, count]) => ({ label: db.disease_grps[code], code, count }))
    .sort((a, b) => (b.count - a.count) || cmpStr(a.label, b.label));

  const eSet = lv.map(() => new Set());
  for (let s = 0; s < db.nStudies; s++) eSet[db.studies.econ_eval_type[s]].add(s);

  const cross = {};
  for (const dr of diseaseMix) {
    const giSet = db.diseaseSets[dr.code];
    for (const er of evalMix) {
      const eiSet = eSet[er.code];
      const indices = [];
      for (const s of cs) if (giSet.has(s) && eiSet.has(s)) indices.push(s);
      indices.sort((a, b) => a - b);
      cross[dr.code + "|" + er.code] = {
        gi: dr.code, ei: er.code,
        disease: dr.label, eval: er.label,
        count: indices.length, indices
      };
    }
  }

  const r = db.countries[ci];
  return {
    iso3, country: r.country, income: r.income,
    n_studies: cs.size,
    evalMix, diseaseMix, cross
  };
}

// Rows for the drill-down modal from the lazily loaded shard on db.drill[iso3]
// (shape §16.2). `missing` marks an index absent from this country's file.
export function drillRecords(db, iso3, indices) {
  const payload = db.drill && db.drill[iso3];
  if (!payload) return [];
  const pos = new Map();
  for (let i = 0; i < payload.s.length; i++) pos.set(payload.s[i], i);
  return indices.map(s => {
    const i = pos.get(s);
    if (i == null) {
      return { s, title: null, abstract: null, truncated: false, missing: true };
    }
    return {
      s,
      title: payload.t[i],
      abstract: payload.a[i],
      truncated: payload.x[i] === 1,
      missing: false
    };
  });
}

// Registry constants (TREND_VARS / COMP_VARS / STACK_VARS / MAP_METRICS /
// SCAT_X / SCAT_Y / SIGNAL_METRICS) now come from content.json registries —
// see buildRegistries() and db.registries (DATA_CONTRACT.md §9, §15.6).

const OA_COLORS = { "Open access": "#1baf7a", "Not open": "#eb6834", "Unknown": "#adb5bd" };
const ACCENT = "#1f5fa8";
const GREY = "#adb5bd";
// Softer income colours, shared by every income-coloured chart.
const LANDSCAPE_INCOME_COLORS = {
  "Low income": "#c96a4a",
  "Lower middle income": "#d2a84a",
  "Upper middle income": "#3b9b84",
  "High income": "#356fa8"
};
// Country profile: light-to-strong ramps for the country bars, grey-blue for peers.
const PROFILE_BLUE = ["#c9ddef", "#9fc4df", "#70a7cf", "#4288bb", "#1f659f"];
const PROFILE_TEAL = ["#d8ebe4", "#add6c7", "#79bda6", "#48a087", "#217b68"];
const PROFILE_LAVENDER = ["#e5ddec", "#cab9da", "#ad91c4", "#8c69aa", "#6d4d8e"];
const PROFILE_PEER = ["#edf1f4", "#dfe6eb", "#ced9e1", "#bdcbd5", "#aabcc8"];
// Default series colours for interactive charts (same family as the figures).
const SOFT_COLORWAY = ["#1764C0", "#2F9B92", "#63B0BC", "#93A3D0", "#D2B06B", "#88B7A8",
  "#B79BCB", "#7E94B1", "#C98F7A", "#9FB7C8"];
// Light-to-strong blue-teal ramp used for single-series bars and maps.
const SOFT_RAMP = ["#dcecf3", "#bddbe7", "#8fc7cf", "#5eb2ba", "#2f8f9d", "#1f5fa8"];

function rampColor(t) {
  const stops = SOFT_RAMP.map(h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)));
  const x = Math.min(1, Math.max(0, t)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x));
  const f = x - i;
  const c = stops[i].map((v, k) => Math.round(v + (stops[i + 1][k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// Cumulative-growth summary, same definitions as fig_growth: the half-way
// year is the latest year from which half of ALL studies (2026 included) were
// published; the reference continues the 2010–2012 average annual output and
// runs to the last complete year (the partial year is left off).
export function growthStats(years, annual, partialYear = 2026) {
  const cum = [];
  let running = 0;
  for (const n of annual) cum.push(running += n);
  const total = cum[cum.length - 1];
  let halfIdx = 0;
  for (let i = 0; i < years.length; i++) {
    if (total - (i > 0 ? cum[i - 1] : 0) >= total / 2) halfIdx = i;
  }
  const earlyN = Math.min(3, annual.length);
  const earlyRate = annual.slice(0, earlyN).reduce((a, b) => a + b, 0) / earlyN;
  const fullIdx = years.map((y, i) => i).filter(i => years[i] !== partialYear);
  const lastFull = fullIdx[fullIdx.length - 1];
  const ref = fullIdx.map(i => earlyRate * (i + 1));
  return {
    cum, total, halfIdx, halfYear: years[halfIdx],
    refYears: fullIdx.map(i => years[i]), ref, lastFull,
    growth: total / Math.max(1, cum[0]),
    vsRef: cum[lastFull] / ref[ref.length - 1],
    earlySpan: years[0] + "–" + String(years[earlyN - 1]).slice(2)
  };
}

// n colours spread evenly along a ramp (bar i of n gets colours[k]).
function spreadPalette(colors, n) {
  return Array.from({ length: n }, (_, i) => colors[Math.min(
    colors.length - 1,
    Math.round(i * (colors.length - 1) / Math.max(1, n - 1))
  )]);
}

// The gallery registry (section titles, blurbs, figure files/titles/captions,
// incl. the interpolated paper01 PRISMA caption) now ships in content.json
// (DATA_CONTRACT.md §15.1) and is consumed as db.content.gallery — the
// hardcoded galleryRegistry() duplicate was removed.

// Thematic analysis sections, regrouped from content.json gallery sections
// (content.json is unchanged): some sections are split into new ones by figure
// file, some figures move to another section, and the new sections are shown
// under group cards (SECTION_GROUPS). Every figure stays visible somewhere.
export function buildGallery(content) {
  const SECTION_SPLITS = {
    "Topics & diseases": [{
      title: "Topic clusters",
      blurb: "What studies are about, found from the text of their abstracts rather than from " +
        "predefined categories, alongside the kinds of intervention they evaluate in different " +
        "income settings.",
      files: ["fig_intervention_map.webp", "fig_theme_rank.webp", "fig_intervention_mix.webp"]
    }, {
      title: "Disease focus",
      blurb: "Which disease areas health economic evaluations address, how this differs between " +
        "richer and poorer countries, and how research about LMICs is shifting between disease areas.",
      files: ["fig_disease_circular.webp", "fig_transition.webp", "paper04.webp", "paper05.webp"]
    }],
    // Geography & authorship + Maps & regional charts are regrouped as
    // Geographic coverage / Research ownership & collaboration, with the
    // burden map and open-access map moved to their topic sections
    // (SECTION_APPENDS). Shown under the Geography and Authorship & access groups.
    "Geography & authorship": [{
      title: "Geographic coverage",
      blurb: "Where economic evaluations are about: which countries studies name, how that compares " +
        "with population, where the evidence is growing fastest, and how often it rests on decision " +
        "models in each region. Country counts use the geography extracted from each study.",
      files: ["fig_dotmap.webp", "fig_worldmap.webp", "paper03.webp", "fig_map_growth.webp", "fig_map_model.webp"]
    }, {
      title: "Research ownership & collaboration",
      blurb: "Who leads research about each setting: whether studies include an author based in the " +
        "country studied, how this differs by income group and region, and how authors collaborate " +
        "across income groups. Authorship figures use harvested affiliations and declare their denominator.",
      files: ["fig_authorship_pattern.webp", "fig_forest.webp", "paper06.webp", "fig_map_authorship.webp",
        "fig_collab_chord.webp"]
    }],
    "Maps & regional charts": [],
    // Open access stays under Authorship & access; every funder figure
    // (incl. the former Priority-setting for funders section) moves to one
    // standalone Research funding section.
    "Open access & funding": [{
      title: "Open access",
      blurb: "How much of the evidence is free to read, how this has changed over time, and how it " +
        "differs by country. Open-access status is known for 87% of studies.",
      files: ["fig_openaccess.webp", "fig_map_openaccess.webp"]
    }, {
      title: "Research funding",
      blurb: "Who funds health economic evaluations, and where new funding could fill the largest " +
        "evidence gaps relative to need. Funders are named in only about 27% of studies, so funder " +
        "counts are a floor, not a census; gaps are ranked by size, not by cost to close.",
      files: ["fig_funder_funders.webp", "fig_funder_opportunity.webp", "fig_funder_scorecard.webp",
        "fig_funder_capacity.webp", "fig_funder_trajectory.webp"]
    }],
    "Priority-setting for funders": []
  };
  // Figures moved to the end of an existing section.
  const SECTION_APPENDS = {
    "Gaps vs disease burden": ["fig_map_burden.webp"]
  };
  // A split part may take a figure from any section, so look figures up globally.
  const figOf = new Map();
  for (const sec of content.gallery) for (const f of sec.figs) if (!figOf.has(f.file)) figOf.set(f.file, f);
  const placed = new Set([
    ...Object.values(SECTION_SPLITS).flat().flatMap(p => p.files),
    ...Object.values(SECTION_APPENDS).flat()
  ]);
  const GALLERY = [];
  for (const sec of content.gallery) {
    const parts = SECTION_SPLITS[sec.title];
    if (!parts) {
      const own = new Set(sec.figs.map(f => f.file));
      const extra = (SECTION_APPENDS[sec.title] || [])
        .filter(file => !own.has(file)).map(file => figOf.get(file)).filter(Boolean);
      GALLERY.push({ ...sec, figs: sec.figs.concat(extra) });
      continue;
    }
    for (const p of parts) {
      const figs = p.files.map(file => figOf.get(file)).filter(Boolean);
      if (figs.length) GALLERY.push({ title: p.title, blurb: p.blurb, figs });
    }
    // A figure of a split section that no rule places stays visible: in the
    // section's last part, or in the original section if it has no parts.
    const rest = sec.figs.filter(f => !placed.has(f.file));
    if (rest.length) {
      if (parts.length) GALLERY[GALLERY.length - 1].figs.push(...rest);
      else GALLERY.push({ ...sec, figs: rest });
    }
  }
  return GALLERY;
}

if (typeof document !== "undefined") {

  const $ = id => document.getElementById(id);
  const PLOTLY_CFG = { responsive: true, displayModeBar: false };
  const BASE_FONT = { family: "Inter, sans-serif", size: 12, color: "#1c2733" };

  let db = null;
  let GALLERY = [];
  let FIG_INDEX = {};
  // Country landscape state: lazy drill shards cached per ISO3, and the fresh
  // index object read by the bound-once heatmap click handler (§16.6).
  const drillCache = {};
  let landCrossIndex = null;
  // TomSelect instance for the landscape country picker. Selecting a country
  // drives the same showCountryMix() as a bubble click; it never touches
  // Explorer state.
  let landSelect = null;
  const state = {
    filt: null,
    result: null,
    country: "IND",
    ts: {}
  };

  function debounce(fn, ms) {
    let t = null;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  }

  // TRUST BOUNDARY: el()'s `html` argument goes through innerHTML and must
  // ONLY receive developer-authored literals. Data-derived strings (anything
  // from data/*.json, user-influenced values, exception messages) must be set
  // with textContent, or escaped with esc() before being embedded in an HTML
  // string (Plotly hover text). content.json strings are developer-authored
  // (generated by our R build from R/app-content.R) and would be acceptable
  // here, but are rendered via textContent anyway.
  function el(tag, cls, html) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function fillSelect(sel, labels, selected) {
    sel.textContent = "";
    for (const lab of labels) {
      const o = document.createElement("option");
      o.value = lab;
      o.textContent = lab;
      if (selected && selected.includes(lab)) o.selected = true;
      sel.appendChild(o);
    }
  }

  let figureZoom = 1;

  function setFigureZoom(nextZoom) {
    figureZoom = Math.min(3, Math.max(0.5, nextZoom));
    $("fig-modal-img").style.width = (figureZoom * 100) + "%";
    $("fig-zoom-reset").textContent = Math.round(figureZoom * 100) + "%";
    $("fig-zoom-out").disabled = figureZoom <= 0.5;
    $("fig-zoom-in").disabled = figureZoom >= 3;
  }

  function openModal(file) {
    const f = FIG_INDEX[file];
    if (!f) return;
    $("fig-modal-title").textContent = f.title;
    const img = $("fig-modal-img");
    img.src = "figures/" + f.file;
    img.alt = f.title;
    $("fig-modal-caption").textContent = f.caption;
    setFigureZoom(1);
    $("fig-zoom-viewport").scrollTo(0, 0);
    $("fig-modal").classList.add("open");
  }

  function closeModal() {
    $("fig-modal").classList.remove("open");
    $("fig-modal-img").src = "";
    setFigureZoom(1);
  }

  function closeThematicMenu() {
    $("thematic-nav").classList.remove("open");
    $("thematic-toggle").setAttribute("aria-expanded", "false");
    $("thematic-menu").hidden = true;
  }

  // The "Countries" nav tab holds two panes (Country landscape / Country
  // profile) switched by the sub-tabs at the top of each pane.
  function showCountryView(view) {
    const pane = view === "profile" ? "country" : "landscape";
    for (const button of document.querySelectorAll("[data-country-view]")) {
      const active = button.dataset.countryView === view;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
    }
    switchTab(pane);
  }

  function switchTab(name) {
    if (name === "countries") {
      showCountryView("landscape");
      return;
    }
    if (name !== "gallery") closeThematicMenu();
    const navName = (name === "landscape" || name === "country") ? "countries" : name;
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      b.classList.toggle("active", b.dataset.tab === navName);
    }
    for (const p of document.querySelectorAll(".tab-pane")) {
      p.classList.toggle("active", p.id === "pane-" + name);
    }
    if (name === "overview" && window.Plotly && $("ov-trend").data) {
      window.Plotly.Plots.resize($("ov-trend"));
    }
    if (name === "explorer" && state.result) {
      for (const id of ["x-trend", "x-map", "x-comp", "x-scatter"]) {
        if (window.Plotly && $(id).data) window.Plotly.Plots.resize($(id));
      }
    }
    if (name === "country" && window.Plotly) {
      for (const id of ["c-trend", "c-mix", "c-methods", "c-signals", "c-benchmark"]) {
        if ($(id).data) window.Plotly.Plots.resize($(id));
      }
    }
    if (name === "landscape") {
      // Build the picker on first activation, while the pane is visible.
      // TomSelect measures the control when it is constructed; building it
      // while #pane-landscape is display:none yields a zero-width dropdown
      // that never opens.
      if (!landSelect) setupLandscapePicker();
      if (window.Plotly) {
        for (const id of ["land-scatter", "land-eval-mix", "land-disease-mix", "land-cross-heatmap"]) {
          if ($(id).data) window.Plotly.Plots.resize($(id));
        }
      }
    }
  }

  function sectionIndex(title) {
    return GALLERY.findIndex(sec => sec.title === title);
  }

  // Opens a Thematic analysis section from the Overview; its back link
  // returns to the Overview.
  function openOverviewTheme(title) {
    const i = sectionIndex(title);
    if (i < 0) return;
    switchTab("gallery");
    showSection(i, "overview");
  }

  // Overview "at a glance" tiles. Keys are content.json glance_tiles labels,
  // plus the two composite cards built in this file.
  const ACCESS_CARD = "__publication_access";
  const METRICS_CARD = "__outcome_metrics";
  const GEO_SCOPE_CARD = "__geo_scope";
  const FUNDERS_CARD = "__funders";
  const OVERVIEW_TILE_ORDER = [
    "Eligible full evaluations", "Years covered", ACCESS_CARD,
    "Journals", "Countries studied", GEO_SCOPE_CARD,
    METRICS_CARD, "Model-based", FUNDERS_CARD
  ];
  // Last row: two wide cards with a narrow Model-based card between them.
  const WIDE_TILES = new Set([METRICS_CARD, FUNDERS_CARD]);
  const NARROW_TILES = new Set(["Model-based"]);
  // Overview wording; values still come from content.json.
  const OVERVIEW_TILE_COPY = {
    "Eligible full evaluations": { label: "Full health economic evaluations captured in the map" },
    "Years covered": { label: "Publication years covered" },
    "Countries studied": { label: "Countries covered by studies", sub: "Across the global evidence base" },
    "Journals": { sub: "Among studies with journal details available" }
  };
  // Shown where the web data does not carry the figure yet.
  const PLACEHOLDER_PCT = "XX%";

  // Where each tile leads.
  const TILE_ACTIONS = {
    "Eligible full evaluations": () => openOverviewTheme("Size & growth"),
    "Years covered": () => showOverviewTrend("cumulative"),
    [ACCESS_CARD]: () => openOverviewTheme("Open access"),
    "Countries studied": () => openOverviewTheme("Geographic coverage"),
    "Journals": () => openOverviewTheme("Open access"),
    [GEO_SCOPE_CARD]: () => openOverviewTheme("Geographic coverage"),
    [METRICS_CARD]: () => openOverviewTheme("Methods & metrics"),
    "Model-based": () => openOverviewTheme("Methods & metrics"),
    [FUNDERS_CARD]: () => openOverviewTheme("Research funding")
  };

  function countLevel(col, label) {
    const code = db.codeOf[col] ? db.codeOf[col].get(label) : db.levels[col].indexOf(label);
    let n = 0;
    for (const v of db.studies[col]) if (v === code) n++;
    return n;
  }

  function fmtPct(x) {
    return x == null ? PLACEHOLDER_PCT : x.toFixed(1) + "%";
  }

  function placeholderize(node, text) {
    node.textContent = text;
    if (text === PLACEHOLDER_PCT) {
      node.classList.add("tile-placeholder");
      node.title = "Placeholder: not yet available in the web data";
    }
  }

  // "Publication access": DOI/URL availability (placeholder: not in the web
  // data) and the open-access share of studies with a known OA status.
  function publicationAccessCard() {
    const box = el("div", "value-box publication-access-card");
    const title = el("div", "value-box-title");
    title.textContent = "Publication access";
    const openN = countLevel("oa_label", "Open access");
    const knownN = openN + countLevel("oa_label", "Not open");
    const metrics = el("div", "publication-access-metrics");
    for (const [label, valueText, note] of [
      ["DOI or URL available", PLACEHOLDER_PCT, "Of all studies"],
      ["Available open access", fmtPct(knownN ? 100 * openN / knownN : null),
       "Of " + fmtNum(knownN) + " studies with a known open-access status"]
    ]) {
      const metric = el("div", "publication-access-metric");
      const metricLabel = el("span", "publication-access-label");
      metricLabel.textContent = label;
      if (label === "Available open access") {
        const help = el("button", "metric-help-button");
        help.type = "button";
        help.textContent = "?";
        help.title = "What does open access mean?";
        help.setAttribute("aria-label", "Explain what open access means");
        // Stop the click reaching the card, which would open its section.
        help.addEventListener("click", event => {
          event.stopPropagation();
          $("oa-help-modal").classList.add("open");
        });
        help.addEventListener("keydown", event => event.stopPropagation());
        metricLabel.appendChild(help);
      }
      const metricValue = el("strong");
      placeholderize(metricValue, valueText);
      const metricNote = el("small");
      metricNote.textContent = note;
      metric.append(metricLabel, metricValue, metricNote);
      metrics.appendChild(metric);
    }
    box.append(title, metrics);
    return box;
  }

  // "Geographic scope of studies": single-country share against everything
  // else (multi-country, region/global, no country stated), from geo_scope.
  function geoScopeCard() {
    const box = el("div", "value-box geo-scope-card");
    const title = el("div", "value-box-title");
    title.textContent = "Geographic scope of studies";
    const total = Math.max(1, db.nStudies);
    const pctOf = n => 100 * n / total;
    const singlePct = pctOf(countLevel("geo_scope", "Single country"));
    const otherPct = 100 - singlePct;
    const multiPct = pctOf(countLevel("geo_scope", "Multi-country") + countLevel("geo_scope", "Region/global"));
    const nonePct = pctOf(countLevel("geo_scope", "No country stated"));

    const bar = el("div", "geo-scope-bar");
    const single = el("div", "geo-scope-segment geo-scope-single");
    single.style.width = singlePct + "%";
    single.textContent = Math.round(singlePct) + "%";
    const other = el("div", "geo-scope-segment geo-scope-other");
    other.style.width = otherPct + "%";
    other.textContent = Math.round(otherPct) + "%";
    bar.append(single, other);

    const labels = el("div", "geo-scope-labels");
    for (const [head, text] of [
      ["Single-country", "One country examined"],
      ["Other geographic scope", multiPct.toFixed(1) + "% multi-country or regional/global; " +
        nonePct.toFixed(1) + "% no country stated"]
    ]) {
      const item = el("div");
      const strong = el("strong");
      strong.textContent = head;
      const span = el("span");
      span.textContent = text;
      item.append(strong, span);
      labels.appendChild(item);
    }
    box.append(title, bar, labels);
    return box;
  }

  // Horizontal-bar card shared by "Outcome metrics used" and "Who funds the
  // evidence?"; a null pct renders the placeholder and an empty track.
  function barRowsCard(cls, titleText, rows, noteText) {
    const box = el("div", "value-box metrics-overview-card " + cls);
    const title = el("div", "value-box-title");
    title.textContent = titleText;
    const chart = el("div", "metrics-overview-chart");
    for (const [label, pct] of rows) {
      const row = el("div", "metrics-overview-row");
      const labelEl = el("span", "metrics-overview-label");
      labelEl.textContent = label;
      const track = el("div", "metrics-overview-track");
      const fill = el("span", "metrics-overview-fill");
      fill.style.width = (pct == null ? 0 : pct) + "%";
      track.appendChild(fill);
      const value = el("strong");
      placeholderize(value, fmtPct(pct));
      row.append(labelEl, track, value);
      chart.appendChild(row);
    }
    const note = el("div", "metrics-overview-note");
    note.textContent = noteText;
    box.append(title, chart, note);
    return box;
  }

  // QALY share from the data; DALYs and other metrics are placeholders until
  // the web data carries them.
  function outcomeMetricsCard() {
    const qalyPct = 100 * countLevel("qaly_label", "Uses QALY") / Math.max(1, db.nStudies);
    return barRowsCard("", "Outcome metrics used in studies",
      [["QALYs", qalyPct], ["DALYs", null], ["Other metrics", null]],
      "Share of all studies. A study may report more than one metric.");
  }

  // Funder types are not in the web data yet: every share is a placeholder.
  function fundersCard() {
    return barRowsCard("funding-overview-card", "Who funds the evidence?",
      [["Government and multilateral", null], ["Academic and non-profit", null],
       ["Private companies", null], ["Unclassified", null]],
      "Among XX studies reporting a funder. Categories may overlap.");
  }

  function makeOverviewCardInteractive(box, key) {
    const action = TILE_ACTIONS[key];
    if (!action) return;
    const label = box.querySelector(".value-box-title").textContent;
    box.classList.add("overview-nav-card");
    box.tabIndex = 0;
    box.setAttribute("role", "link");
    box.setAttribute("aria-label", label + ": open related analysis");
    box.addEventListener("click", action);
    box.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        action();
      }
    });
  }

  function renderOverview() {
    const m = db.dict.meta;
    const built = $("nav-built");
    if (built) built.textContent = "bundle " + m.built;

    // Footer: study count and data build date ("2026-10-08" -> "8 October 2026").
    $("footer-n").textContent = fmtNum(db.nStudies);
    const [yy, mm, dd] = String(m.built).split("-").map(Number);
    if (yy && mm && dd) {
      $("footer-date").textContent = new Date(Date.UTC(yy, mm - 1, dd))
        .toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
    }

    // Hero paragraph: ordered segments from content.json (§15.2). Each segment
    // becomes a <span>/<strong>/<em> filled via textContent — no innerHTML.
    // HTML whitespace collapsing turns the source newlines/indent into spaces.
    const hero = $("ov-hero");
    hero.textContent = "";
    for (const seg of db.content.hero) {
      const node = document.createElement(seg.strong ? "strong" : seg.em ? "em" : "span");
      node.textContent = seg.text;
      hero.appendChild(node);
    }

    // Glance tiles: values from content.json (§15.3), shown with the Overview
    // wording in OVERVIEW_TILE_COPY and in OVERVIEW_TILE_ORDER; the two
    // composite cards (publication access, outcome metrics) are built here.
    const wrap = $("ov-tiles");
    wrap.textContent = "";
    const tileByLabel = new Map(db.content.glance_tiles.map(t => [t.label, t]));
    for (const key of OVERVIEW_TILE_ORDER) {
      let box;
      if (key === ACCESS_CARD) box = publicationAccessCard();
      else if (key === METRICS_CARD) box = outcomeMetricsCard();
      else if (key === GEO_SCOPE_CARD) box = geoScopeCard();
      else if (key === FUNDERS_CARD) box = fundersCard();
      else {
        const t = tileByLabel.get(key);
        if (!t) continue;
        const copy = OVERVIEW_TILE_COPY[key] || {};
        box = el("div", "value-box");
        const title = el("div", "value-box-title");
        title.textContent = copy.label || t.label;
        const value = el("div", "value-box-value");
        value.textContent = t.value;
        box.appendChild(title);
        box.appendChild(value);
        const subText = "sub" in copy ? copy.sub : t.sub;
        if (subText != null) {
          const sub = el("div", "value-box-sub");
          sub.textContent = subText;
          box.appendChild(sub);
        }
      }
      if (WIDE_TILES.has(key)) box.classList.add("tile-wide");
      if (NARROW_TILES.has(key)) box.classList.add("tile-narrow");
      makeOverviewCardInteractive(box, key);
      wrap.appendChild(box);
    }

    // Overview figure cards: header = the figure's content.json title, with a
    // "More on …" link to the Thematic analysis section that holds it.
    const heroes = [
      { file: "fig_dotmap.webp", alt: "Global dot map" },
      { file: "fig_burden.webp", alt: "Evidence vs burden" },
      { file: "fig_transition.webp", alt: "Epidemiological transition" }
    ];
    const hw = $("ov-hero-imgs");
    hw.textContent = "";
    for (const h of heroes) {
      const f = FIG_INDEX[h.file];
      const card = el("div", "card overview-analysis-card");
      const head = el("div", "card-header overview-card-head");
      const name = el("span");
      name.textContent = f ? f.title : h.alt;
      head.appendChild(name);
      if (f && f.sectionTitle) {
        const link = el("button", "card-header-link");
        link.type = "button";
        link.textContent = "More on " + f.sectionTitle.toLowerCase() + " →";
        link.addEventListener("click", () => openOverviewTheme(f.sectionTitle));
        head.appendChild(link);
      }
      const body = el("div", "card-body overview-analysis-body");
      const btn = el("button", "overview-figure-button");
      btn.type = "button";
      btn.setAttribute("aria-label", "Open figure: " + (f ? f.title : h.alt));
      const img = el("img", "overview-analysis-figure");
      img.src = "figures/" + h.file;
      img.alt = h.alt;
      img.loading = "lazy";
      btn.appendChild(img);
      btn.addEventListener("click", () => openModal(h.file));
      body.appendChild(btn);
      card.appendChild(head);
      card.appendChild(body);
      hw.appendChild(card);
    }
  }

  // Overview publication trend for the unfiltered corpus, with a
  // "Per year | Cumulative" switch.
  let overviewTrendMode = "annual";

  function showOverviewTrend(mode) {
    switchTab("overview");
    setOverviewTrendMode(mode);
    document.querySelector(".overview-trend-card").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function setOverviewTrendMode(mode) {
    overviewTrendMode = mode;
    for (const b of document.querySelectorAll("[data-trend-mode]")) {
      const on = b.dataset.trendMode === mode;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", String(on));
    }
    renderOverviewTrend();
  }

  function renderOverviewTrend() {
    const ser = trendSeries(db, applyFilters(db, {}), "none");
    const years = Object.keys(ser).map(Number).sort((a, b) => a - b);
    const annual = years.map(y => ser[y]);
    const cumulative = overviewTrendMode === "cumulative";
    let running = 0;
    const y = cumulative ? annual.map(n => (running += n)) : annual;
    // Light-to-strong blue across the years for the markers.
    const lerp = (a, b, t) => Math.round(a + (b - a) * t);
    const span = Math.max(1, years[years.length - 1] - years[0]);
    const markerColors = years.map(yr => {
      const t = (yr - years[0]) / span;
      return `rgb(${lerp(126, 26, t)},${lerp(166, 78, t)},${lerp(212, 138, t)})`;
    });
    const traces = [{
      x: years, y,
      mode: "lines+markers", type: "scatter", showlegend: false,
      line: { color: ACCENT, width: 3, shape: "spline", smoothing: 0.45 },
      marker: { color: markerColors, size: 7, line: { color: "white", width: 1 } },
      fill: "tozeroy", fillcolor: "rgba(31,95,168,.12)",
      fillgradient: {
        type: "horizontal",
        colorscale: [[0, "rgba(31,95,168,.04)"], [1, "rgba(31,95,168,.22)"]]
      },
      hovertemplate: (cumulative ? "By %{x}" : "%{x}") + ": %{y:,} studies<extra></extra>"
    }];
    // 2026 is a partial year: gold triangle plus a callout to its right.
    const partialIndex = years.indexOf(2026);
    const annotations = [];
    if (partialIndex >= 0) {
      traces.push({
        x: [2026], y: [y[partialIndex]],
        mode: "markers", type: "scatter", showlegend: false, cliponaxis: false,
        marker: { symbol: "triangle-up", color: "#b08d3e", size: 13, line: { color: "white", width: 1 } },
        hovertemplate: (cumulative ? "By 2026" : "2026") +
          ": %{y:,} studies<br>Partial year: searches were run in mid-2026<extra></extra>"
      });
      annotations.push({
        x: 2026, y: y[partialIndex], xref: "x", yref: "y",
        text: "<b>2026: partial year</b><br>searches run mid-2026",
        showarrow: true, arrowhead: 0, arrowwidth: 1.2, arrowcolor: "#c9a85f",
        ax: 22, ay: 0, xanchor: "left", align: "left",
        font: { color: "#6f5420", size: 12.5 },
        bgcolor: "#fbf5e6", bordercolor: "#dcc48f", borderwidth: 1, borderpad: 5
      });
    }
    const chips = $("ov-trend-chips");
    chips.textContent = "";
    chips.hidden = !cumulative;
    const shapes = [];
    if (cumulative) {
      const g = growthStats(years, annual);
      for (const [value, text] of [
        [g.growth.toFixed(1) + "×", "growth in cumulative studies since " + years[0]],
        [String(g.halfYear), "half of all " + fmtNum(g.total) + " studies were published in " +
          g.halfYear + " or later"],
        [g.vsRef.toFixed(1) + "×", "more studies by " + years[g.lastFull] +
          " than if output had stayed at its " + g.earlySpan + " rate"]
      ]) {
        const chip = el("div", "trend-chip");
        const v = el("strong");
        v.textContent = value;
        const t = el("span");
        t.textContent = text;
        chip.append(v, t);
        chips.appendChild(chip);
      }
      // Dashed reference drawn under the main line.
      traces.unshift({
        x: g.refYears, y: g.ref,
        mode: "lines", type: "scatter", showlegend: false,
        line: { color: "#8a93a0", width: 1.6, dash: "dash" },
        hovertemplate: "If output had stayed at the " + g.earlySpan + " rate: %{y:,.0f}<extra></extra>"
      });
      const refLabelIdx = Math.round(g.ref.length * 0.62);
      annotations.push({
        x: g.refYears[refLabelIdx], y: g.ref[refLabelIdx], xref: "x", yref: "y",
        text: "if output had stayed at its " + g.earlySpan + " rate",
        showarrow: false, yanchor: "bottom", yshift: 4, font: { color: "#6b7280", size: 11.5 }
      }, {
        x: g.halfYear, y: g.cum[g.halfIdx], xref: "x", yref: "y",
        text: "<b>Half of all studies</b><br>published " + g.halfYear + " or later",
        showarrow: true, arrowhead: 0, arrowwidth: 1.2, arrowcolor: "#1f5fa8",
        ax: -95, ay: -38, align: "left",
        font: { color: "#1a4e8a", size: 12 },
        bgcolor: "#f0f6fc", bordercolor: "#b9d0ea", borderwidth: 1, borderpad: 5
      });
      shapes.push({
        type: "line", xref: "x", yref: "y", x0: g.halfYear, x1: g.halfYear, y0: 0, y1: g.cum[g.halfIdx],
        line: { color: "#1f5fa8", width: 1, dash: "dot" }
      });
      $("ov-trend-note").textContent = "Running total of studies by publication year. Dashed line: " +
        "where the total would be if yearly output had stayed at its " + g.earlySpan + " average. " +
        "2026 is a partial year (searches were run in mid-2026).";
    } else {
      $("ov-trend-note").textContent = "Annual studies by publication year. 2026 is a partial year: " +
        "the literature searches were run in mid-2026, so only studies published before then are included.";
    }
    window.Plotly.react("ov-trend", traces, {
      font: BASE_FONT,
      margin: { t: 10, b: 40, l: 60, r: partialIndex >= 0 ? 175 : 20 },
      annotations,
      shapes,
      xaxis: { showgrid: false, range: [years[0] - 0.4, years[years.length - 1] + 0.3], dtick: 2 },
      yaxis: { title: cumulative ? "cumulative studies" : "studies", tickformat: ",d",
               gridcolor: "#eeebe3", zeroline: false, rangemode: "tozero" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  // Sections shown together under one card on the Thematic analysis index.
  // Members are section titles in GALLERY (see SECTION_SPLITS in boot()).
  const SECTION_GROUPS = [{
    title: "Topic clustering & disease focus",
    blurb: "The subjects studies deal with: topics found in the wording of their abstracts, " +
      "and the diseases they address.",
    members: ["Topic clusters", "Disease focus"]
  }, {
    title: "Geography",
    blurb: "Where health economic evidence is concentrated, and whether it is distributed in " +
      "proportion to the burden of disease.",
    members: ["Geographic coverage", "Gaps vs disease burden"]
  }, {
    title: "Authorship & access",
    blurb: "Who writes economic evaluations about different settings, how authors collaborate " +
      "across income groups, and how much of their work is freely available.",
    members: ["Research ownership & collaboration", "Open access"]
  }];

  function groupOf(sectionTitle) {
    return SECTION_GROUPS.find(g => g.members.includes(sectionTitle)) || null;
  }

  // A theme card (image, title, count, short description) for the index or a group view.
  function thematicCard(titleText, blurb, imageFile, countText, onClick) {
    const card = el("button", "thematic-card");
    card.type = "button";
    const img = el("img", "thematic-card-image");
    img.src = "figures/" + imageFile;
    img.alt = "";
    img.loading = "lazy";
    const body = el("div", "thematic-card-body");
    const title = el("h2", "thematic-card-title");
    title.textContent = titleText;
    const count = el("div", "thematic-card-count");
    count.textContent = countText;
    const description = el("p", "thematic-card-description");
    const fullBlurb = blurb.replace(/\s+/g, " ").trim();
    description.textContent = fullBlurb.length > 155 ? fullBlurb.slice(0, 152) + "..." : fullBlurb;
    const arrow = el("span", "thematic-card-arrow");
    arrow.textContent = "→";
    arrow.setAttribute("aria-hidden", "true");
    body.append(title, count, description, arrow);
    card.append(img, body);
    card.addEventListener("click", onClick);
    return card;
  }

  function navThemeLink(text, onClick) {
    const item = el("button", "nav-theme-link");
    item.type = "button";
    item.setAttribute("role", "menuitem");
    item.textContent = text;
    item.addEventListener("click", () => {
      closeThematicMenu();
      switchTab("gallery");
      onClick();
    });
    return item;
  }

  // Thematic analysis index: one card per gallery section, except grouped
  // sections, which share one card (at the first member's position); the
  // navbar dropdown lists the same entries.
  function renderGalleryIndex() {
    const idx = $("gal-section-index");
    const menu = $("thematic-menu");
    idx.textContent = "";
    menu.textContent = "";
    const shownGroups = new Set();
    GALLERY.forEach((sec, i) => {
      const group = groupOf(sec.title);
      if (group) {
        if (shownGroups.has(group)) return;
        shownGroups.add(group);
        const members = group.members.map(t => GALLERY.find(x => x.title === t)).filter(Boolean);
        const nFigs = members.reduce((n, m) => n + m.figs.length, 0);
        idx.appendChild(thematicCard(group.title, group.blurb, sec.figs[0].file,
          nFigs + " figures in " + members.length + " sections", () => showGroup(group)));
        menu.appendChild(navThemeLink(group.title, () => showGroup(group)));
        return;
      }
      idx.appendChild(thematicCard(sec.title, sec.blurb, sec.figs[0].file,
        sec.figs.length + " figures", () => showSection(i)));
      menu.appendChild(navThemeLink(sec.title, () => showSection(i)));
    });
  }

  // Group view: the group's sections as theme cards.
  function showGroup(group, returnTo = null) {
    sectionReturnTo = returnTo;
    $("gal-back").innerHTML = returnTo === "overview" ? "&larr; Back to Overview" : "&larr; All themes";
    $("gal-index").style.display = "none";
    $("gal-section").style.display = "block";
    $("gal-sec-title").textContent = group.title;
    $("gal-sec-blurb").textContent = group.blurb.replace(/\s+/g, " ").trim();
    $("gal-sec-extra").textContent = "";
    const grid = $("gal-sec-grid");
    grid.textContent = "";
    grid.classList.remove("fig-grid-single");
    grid.classList.add("group-grid");
    for (const title of group.members) {
      const i = GALLERY.findIndex(x => x.title === title);
      if (i < 0) continue;
      const sec = GALLERY[i];
      grid.appendChild(thematicCard(sec.title, sec.blurb, sec.figs[0].file, sec.figs.length + " figures",
        () => showSection(i, { group })));
    }
    window.scrollTo(0, 0);
  }

  // Plain-language "how this was done" notes shown at the top of a section.
  // Facts come from the figure captions and the methods text.
  const SECTION_METHOD_NOTES = {
    "Topic clusters": {
      summary: "How these topics were identified",
      paragraphs: [
        "<strong>Topic clusters</strong> were found from the studies themselves, not from a list of "
          + "categories decided in advance. A language model turned each study's abstract into a numerical "
          + "summary of its meaning, and studies with similar summaries were grouped together automatically "
          + "into 73 themes. The themes therefore describe what studies are about rather than official categories.",
        "<strong>Intervention types</strong> (for example vaccines, pharmaceuticals, devices or surgery) come "
          + "from a separate step: a language model recorded each study's main type of intervention. This was "
          + "checked against a keyword list, the topic clusters and a second model, but not by human reviewers."
      ]
    },
    "Disease focus": {
      summary: "How disease areas were identified",
      paragraphs: [
        "Disease areas come from <strong>Medical Subject Headings (MeSH)</strong>: the standard subject "
          + "terms that indexers at the US National Library of Medicine attach to articles in PubMed. Each "
          + "study's MeSH terms were matched to 14 broad disease groups, such as infectious diseases, "
          + "cancers and cardiovascular disease.",
        "Only studies with MeSH disease terms can be classified this way: 22,744 of the 41,657 studies "
          + "(about 55%). These figures therefore describe a subset of the evidence, not all studies in the map."
      ]
    }
  };

  // Where the section's back link leads: null = theme index, "overview" =
  // back to the Overview, { group } = back to that group's view.
  let sectionReturnTo = null;

  // Figures drawn at least this many pixels wide span two grid columns.
  const WIDE_FIGURE_MIN_PX = 2300;

  function showSection(i, returnTo = null) {
    const sec = GALLERY[i];
    // A grouped section opened from elsewhere still leads back to its group.
    if (returnTo == null && groupOf(sec.title)) returnTo = { group: groupOf(sec.title) };
    sectionReturnTo = returnTo;
    $("gal-back").innerHTML = returnTo === "overview" ? "&larr; Back to Overview"
      : returnTo && returnTo.group ? "&larr; " + returnTo.group.title
      : "&larr; All themes";
    $("gal-index").style.display = "none";
    $("gal-section").style.display = "block";
    $("gal-sec-title").textContent = sec.title;
    $("gal-sec-blurb").textContent = sec.blurb.replace(/\s+/g, " ").trim();
    const extra = $("gal-sec-extra");
    extra.textContent = "";
    const methodNote = SECTION_METHOD_NOTES[sec.title];
    if (methodNote) {
      const box = el("details", "method-note");
      const summary = el("summary");
      summary.textContent = methodNote.summary;
      box.appendChild(summary);
      // Paragraphs are developer-authored literals above (see el()'s trust note).
      for (const html of methodNote.paragraphs) box.appendChild(el("p", null, html));
      extra.appendChild(box);
    }
    const grid = $("gal-sec-grid");
    grid.textContent = "";
    grid.classList.remove("group-grid");
    grid.classList.toggle("fig-grid-single", sec.figs.length === 1);
    for (const f of sec.figs) {
      const card = el("div", "fig-card");
      const img = el("img");
      img.src = "figures/" + f.file;
      img.alt = f.title;
      img.loading = "lazy";
      img.addEventListener("click", () => openModal(f.file));
      img.addEventListener("load", () => {
        card.classList.toggle("fig-card-wide", img.naturalWidth >= WIDE_FIGURE_MIN_PX);
      }, { once: true });
      card.appendChild(img);
      const body = el("div", "fig-body");
      const ft = el("div", "fig-title");
      ft.textContent = f.title;
      const fc = el("div", "fig-caption");
      fc.textContent = f.caption.replace(/\s+/g, " ").trim();
      body.appendChild(ft);
      body.appendChild(fc);
      card.appendChild(body);
      grid.appendChild(card);
    }
    window.scrollTo(0, 0);
  }

  function hideSection() {
    $("gal-section").style.display = "none";
    $("gal-index").style.display = "block";
    sectionReturnTo = null;
    $("gal-back").innerHTML = "&larr; All themes";
  }

  function goBackFromSection() {
    const toOverview = sectionReturnTo === "overview";
    const toGroup = sectionReturnTo && sectionReturnTo.group;
    if (toGroup) {
      showGroup(toGroup);
      return;
    }
    hideSection();
    if (toOverview) {
      switchTab("overview");
      $("ov-tiles").scrollIntoView({ block: "center" });
    } else {
      window.scrollTo(0, 0);
    }
  }

  function makeRadios(containerId, name, choices) {
    const c = $(containerId);
    c.textContent = "";
    choices.forEach((ch, i) => {
      const lab = el("label");
      const inp = el("input");
      inp.type = "radio";
      inp.name = name;
      inp.value = ch;
      inp.checked = i === 0;
      inp.addEventListener("change", () => {
        state.filt[name.slice(2)] = ch;
        refreshExplorer();
      });
      lab.appendChild(inp);
      lab.appendChild(document.createTextNode(ch));
      c.appendChild(lab);
    });
  }

  function makeMultiSelect(id, options, placeholder, key) {
    const sel = $(id);
    for (const o of options) {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = o;
      sel.appendChild(opt);
    }
    state.ts[key] = new window.TomSelect(sel, {
      plugins: ["remove_button"],
      placeholder: placeholder,
      allowEmptyOption: false,
      onChange: vals => {
        state.filt[key] = Array.isArray(vals) ? vals.slice() : (vals ? [vals] : []);
        refreshExplorer();
      }
    });
  }

  function setupExplorerControls() {
    const m = db.dict.meta;
    state.filt = {
      years: db.years.slice(),
      income: [], region: [], disease: [], evaltype: [], design: [],
      model: "All", qaly: "All", oa: "All", scope: "All"
    };

    const slider = $("x-years");
    window.noUiSlider.create(slider, {
      start: db.years,
      connect: true,
      step: 1,
      range: { min: db.years[0], max: db.years[1] }
    });
    const readout = $("x-years-readout");
    const setReadout = () => {
      readout.textContent = state.filt.years[0] + " – " + state.filt.years[1];
    };
    setReadout();
    const debouncedYears = debounce(() => refreshExplorer(), 250);
    slider.noUiSlider.on("update", (values) => {
      state.filt.years = [Math.round(+values[0]), Math.round(+values[1])];
      setReadout();
      debouncedYears();
    });

    makeMultiSelect("x-income", db.incOrder, "All groups", "income");
    makeMultiSelect("x-region", db.dict.REGIONS, "All regions", "region");
    makeMultiSelect("x-disease", db.disease_grps, "All areas", "disease");
    makeMultiSelect("x-evaltype", db.levels.econ_eval_type, "All types", "evaltype");
    makeMultiSelect("x-design", db.levels.design_basis, "All designs", "design");

    makeRadios("x-model", "x_model", ["All", "Model-based", "Measured"]);
    makeRadios("x-qaly", "x_qaly", ["All", "Uses QALY", "No QALY"]);
    makeRadios("x-oa", "x_oa", ["All", "Open access", "Not open"]);

    const scope = $("x-scope");
    fillSelect(scope, ["All"].concat(db.levels.geo_scope));
    scope.addEventListener("change", () => {
      state.filt.scope = scope.value;
      refreshExplorer();
    });

    $("x-reset").addEventListener("click", () => {
      slider.noUiSlider.set(db.years);
      for (const k of ["income", "region", "disease", "evaltype", "design"]) state.ts[k].clear();
      for (const [cont, name] of [["x-model", "model"], ["x-qaly", "qaly"], ["x-oa", "oa"]]) {
        const first = $(cont).querySelector("input");
        first.checked = true;
        state.filt[name] = "All";
      }
      scope.value = "All";
      state.filt.scope = "All";
      state.filt.years = db.years.slice();
      setReadout();
      refreshExplorer();
    });

    const REG = db.registries;
    fillSelect($("x-trend-by"), [...REG.TREND_VARS.keys()], ["Income group"]);
    fillSelect($("x-map-metric"), [...REG.MAP_METRICS.keys()], ["Studies"]);
    fillSelect($("x-comp-var"), [...REG.COMP_VARS.keys()], ["Evaluation type"]);
    fillSelect($("x-comp-stack"), [...REG.STACK_VARS.keys()], ["None"]);
    const compMode = $("x-comp-mode");
    compMode.textContent = "";
    for (const [lab, val] of [["Count", "n"], ["Share (%)", "pct"]]) {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = lab;
      compMode.appendChild(o);
    }
    fillSelect($("x-scatter-x"), [...REG.SCAT_X.keys()], ["Total DALYs (GBD 2023)"]);
    fillSelect($("x-scatter-y"), [...REG.SCAT_Y.keys()], ["Studies per 100k DALYs"]);

    $("x-trend-by").addEventListener("change", renderTrend);
    $("x-map-metric").addEventListener("change", renderMap);
    $("x-comp-var").addEventListener("change", renderComp);
    $("x-comp-stack").addEventListener("change", renderComp);
    $("x-comp-mode").addEventListener("change", renderComp);
    $("x-scatter-x").addEventListener("change", renderScatter);
    $("x-scatter-y").addEventListener("change", renderScatter);
  }

  function refreshExplorer() {
    state.result = applyFilters(db, state.filt);
    renderValueBoxes();
    renderTrend();
    renderMap();
    renderComp();
    renderScatter();
    renderTable();
  }

  function renderValueBoxes() {
    const v = valueBoxes(db, state.result);
    $("v-studies").textContent = fmtNum(v.v_studies);
    $("v-countries").textContent = fmtNum(v.v_countries);
    $("v-model").textContent = v.v_model_pct == null ? "—" : v.v_model_pct + "%";
    $("v-qaly").textContent = v.v_qaly_pct == null ? "—" : v.v_qaly_pct + "%";
  }

  function hLegend(y) {
    return { orientation: "h", y: y, x: 0 };
  }

  function renderTrend() {
    const label = $("x-trend-by").value;
    const v = db.registries.TREND_VARS.get(label);
    const ser = trendSeries(db, state.result, v);
    const years = Object.keys(ser).map(Number);
    let traces;
    if (v === "none") {
      traces = [{
        x: years, y: years.map(y => ser[y]),
        mode: "lines", type: "scatter",
        line: { color: ACCENT, width: 3 },
        name: "studies", hovertemplate: "%{x}: %{y} studies<extra></extra>"
      }];
    } else {
      let cats;
      let colorMap = null;
      if (v === "income") {
        cats = db.incLv.slice();
        colorMap = db.palInc;
      } else if (v === "un_region") {
        cats = [...new Set(years.flatMap(y => Object.keys(ser[y])))].sort();
      } else {
        const lv = db.levels[v];
        if (v === "oa_label") {
          cats = lv.slice();
          colorMap = OA_COLORS;
        } else {
          cats = [...new Set(years.flatMap(y => Object.keys(ser[y])))].sort();
        }
      }
      traces = cats.map(cat => ({
        x: years,
        y: years.map(y => (ser[y] && ser[y][cat] != null) ? ser[y][cat] : null),
        mode: "lines", type: "scatter",
        name: cat,
        connectgaps: false,
        line: { width: 2.4, color: colorMap ? colorMap[cat] : undefined },
        // cat comes from dict levels (developer-curated); escaped anyway —
        // Plotly renders hovertemplate output as HTML.
        hovertemplate: "%{x} · " + esc(cat) + ": %{y} studies<extra></extra>"
      }));
    }
    window.Plotly.react("x-trend", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 60, r: 20 },
      legend: hLegend(-0.18),
      xaxis: { title: null, gridcolor: "#eeebe3" },
      yaxis: { title: "studies", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderMap() {
    const label = $("x-map-metric").value;
    const m = db.registries.MAP_METRICS.get(label);
    const rows = state.result.byCountry;
    const isCounts = m === "studies";
    const z = rows.map(r => isCounts ? Math.log10(r.studies + 1) : r[m]);
    // Plotly renders hover text as HTML — country names are data-derived and
    // must be escaped before concatenation.
    const text = rows.map(r => isCounts
      ? esc(r.country) + "<br>" + fmtNum(r.studies) + " studies"
      : esc(r.country) + "<br>" + fmtNum(r.studies) + " studies<br>" +
        (r[m] == null ? "NA" : rRound(r[m], 2)) + " " + esc(label.toLowerCase()));
    const colorscale = isCounts
      ? [[0, "#f1f3f5"], [0.0001, SOFT_RAMP[0]]].concat(SOFT_RAMP.slice(1).map((c, i) => [(i + 1) / (SOFT_RAMP.length - 1), c]))
      : SOFT_RAMP.map((c, i) => [i / (SOFT_RAMP.length - 1), c]);
    const colorbar = isCounts
      ? {
          title: "studies<br>(log)",
          tickvals: [0, 1, 10, 100, 1000].map(x => Math.log10(x + 1)),
          ticktext: ["0", "1", "10", "100", "1000"],
          thickness: 12, len: 0.8
        }
      : { title: label.split(" ").join("<br>"), thickness: 12, len: 0.8 };
    window.Plotly.react("x-map", [{
      type: "choropleth",
      locations: rows.map(r => r.iso3),
      z: z,
      text: text,
      hoverinfo: "text",
      colorscale: colorscale,
      marker: { line: { color: "#ffffff", width: 0.3 } },
      colorbar: colorbar
    }], {
      font: BASE_FONT,
      geo: {
        projection: { type: "robinson" },
        showframe: false,
        showcoastlines: false,
        bgcolor: "rgba(0,0,0,0)"
      },
      margin: { t: 0, b: 0, l: 0, r: 0 }
    }, PLOTLY_CFG);
  }

  function renderComp() {
    const label = $("x-comp-var").value;
    const xv = db.registries.COMP_VARS.get(label);
    const sv = db.registries.STACK_VARS.get($("x-comp-stack").value);
    const mode = $("x-comp-mode").value;
    const res = compCounts(db, state.result, xv, sv, mode);
    const note = xv === "grp" ? " · a study can sit in several disease groups" : "";
    const annotation = {
      text: label + note, xref: "paper", yref: "paper",
      x: 0, y: 1.06, xanchor: "left", showarrow: false,
      font: { size: 11, color: "#6b7280" }
    };
    let traces, layout;
    if (res.type === "simple") {
      const desc = res.rows;
      const bottomUp = desc.slice().reverse();
      const maxV = Math.max(1, ...desc.map(r => r.v));
      traces = [{
        type: "bar", orientation: "h",
        y: desc.map(r => r.x),
        x: desc.map(r => r.v),
        marker: { color: desc.map(r => rampColor(0.15 + 0.85 * Math.sqrt(r.v / maxV))) },
        hovertemplate: "%{y}: %{x}<extra></extra>"
      }];
      layout = {
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp.map(r => r.x),
          automargin: true
        },
        xaxis: {
          title: res.pct ? "share of filtered studies (%)" : "studies",
          gridcolor: "#eeebe3",
          ticksuffix: res.pct ? "%" : ""
        }
      };
    } else {
      const bottomUp = res.catOrder.slice().reverse();
      traces = res.stacks.map(k => ({
        type: "bar", orientation: "h",
        name: k,
        y: res.catOrder,
        x: res.catOrder.map(c => res.values[c][k] != null ? res.values[c][k] : 0),
        // k comes from dict levels (developer-curated); escaped anyway —
        // Plotly renders hovertemplate output as HTML.
        hovertemplate: "%{y} · " + esc(k) + ": %{x}<extra></extra>"
      }));
      layout = {
        barmode: "stack",
        yaxis: {
          categoryorder: "array",
          categoryarray: bottomUp,
          automargin: true
        },
        xaxis: {
          title: res.pct ? "share within category (%)" : "studies",
          gridcolor: "#eeebe3",
          range: res.pct ? [0, 100] : undefined,
          ticksuffix: res.pct ? "%" : ""
        }
      };
    }
    window.Plotly.react("x-comp", traces, Object.assign({
      font: BASE_FONT,
      margin: { t: 30, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)",
      annotations: [annotation]
    }, layout), PLOTLY_CFG);
  }

  function renderScatter() {
    const xLabel = $("x-scatter-x").value;
    const yLabel = $("x-scatter-y").value;
    const xv = db.registries.SCAT_X.get(xLabel);
    const yv = db.registries.SCAT_Y.get(yLabel);
    const pts = scatterPoints(db, state.result, xv, yv);
    const traces = db.incLv.map(inc => {
      const rows = pts.filter(r => r.income === inc);
      return {
        type: "scatter", mode: "markers",
        name: inc,
        x: rows.map(r => r[xv]),
        y: rows.map(r => r[yv]),
        // country names are data-derived; Plotly renders hover text as HTML.
        text: rows.map(r => esc(r.country) + "<br>" + fmtNum(r.studies) + " studies"),
        hoverinfo: "text",
        marker: { color: db.palInc[inc], size: 8, opacity: 0.75, line: { color: "white", width: 0.5 } }
      };
    });
    window.Plotly.react("x-scatter", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 70, l: 70, r: 20 },
      legend: hLegend(-0.2),
      xaxis: { type: "log", title: xLabel + " (log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: yLabel + " (log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderTable() {
    const rows = tableRows(db, state.result, 25);
    const cols = ["Country", "Income", "Region", "Studies", "Per 100k DALYs", "Per US$1bn", "Per million"];
    const numCols = new Set(["Studies", "Per 100k DALYs", "Per US$1bn", "Per million"]);
    // Country/Income/Region cells are data-derived strings: build the table
    // with createElement + textContent — never innerHTML string concat.
    const tbl = $("x-table");
    tbl.textContent = "";
    const thead = document.createElement("thead");
    const htr = document.createElement("tr");
    for (const c of cols) {
      const th = document.createElement("th");
      if (numCols.has(c)) th.className = "num";
      th.textContent = c;
      htr.appendChild(th);
    }
    thead.appendChild(htr);
    tbl.appendChild(thead);
    const tbody = document.createElement("tbody");
    for (const r of rows) {
      const tr = document.createElement("tr");
      for (const c of cols) {
        const v = r[c];
        const td = document.createElement("td");
        if (numCols.has(c)) td.className = "num";
        td.textContent = v == null ? "" : (c === "Studies" ? fmtNum(v) : String(v));
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    tbl.appendChild(tbody);
  }

  function setupCountryPane() {
    const sel = $("c-picker");
    for (const r of db.countries) {
      const o = document.createElement("option");
      o.value = r.iso3;
      o.textContent = r.country;
      if (r.iso3 === "IND") o.selected = true;
      sel.appendChild(o);
    }
    new window.TomSelect(sel, {
      placeholder: "Pick a country…",
      onChange: val => {
        if (!val) return;
        state.country = val;
        renderCountryAll();
      }
    });
    renderCountryAll();
  }

  function renderCountryAll() {
    const iso3 = state.country;
    const prof = countryProfile(db, iso3);
    if (!prof) return;

    const facts = $("c-facts");
    facts.textContent = "";
    // Fact keys/values are data-derived (country names, region names,
    // formatted numbers) — textContent only, never el()'s innerHTML path.
    for (const [k, v] of countryFacts(db, iso3)) {
      const dt = el("dt");
      dt.textContent = k;
      const dd = el("dd");
      dd.textContent = String(v);
      facts.appendChild(dt);
      facts.appendChild(dd);
    }

    $("c-n").textContent = fmtNum(prof.c_n);
    $("c-daly").textContent = prof.c_daly == null ? "no burden data"
      : rRound(prof.c_daly, 2) + "  (median " + rRound(prof.medians.m_daly, 2) + ")";
    $("c-spend").textContent = prof.c_spend == null ? "no spending data"
      : rRound(prof.c_spend, 2) + "  (median " + rRound(prof.medians.m_bn, 2) + ")";
    $("c-percap").textContent = rRound(prof.c_percap, 2) + "  (median " + rRound(prof.medians.m_mil, 2) + ")";

    const ct = prof.c_trend;
    const cYears = Object.keys(ct.country).map(Number);
    const pYears = Object.keys(ct.peer).map(Number);
    window.Plotly.react("c-trend", [
      {
        x: cYears, y: cYears.map(y => ct.country[y]),
        mode: "lines", type: "scatter", name: "country",
        line: { color: "#1f659f", width: 3 },
        hovertemplate: "%{x}: %{y} studies<extra>country</extra>"
      },
      {
        x: pYears, y: pYears.map(y => ct.peer[y]),
        mode: "lines", type: "scatter", name: "income-group mean",
        line: { color: "#88a6b8", width: 2.5, dash: "dash" },
        hovertemplate: "%{x}: %{y:.2f} per country<extra>income-group mean</extra>"
      }
    ], {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 60, r: 20 },
      legend: hLegend(-0.18),
      xaxis: { gridcolor: "#eeebe3" },
      yaxis: { title: "studies per year", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    const mix = prof.c_mix;
    const grps = [...new Set([...Object.keys(mix.country), ...Object.keys(mix.peer)])];
    const meanShare = g => {
      const vals = [];
      if (mix.country[g] != null) vals.push(mix.country[g]);
      if (mix.peer[g] != null) vals.push(mix.peer[g]);
      return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
    };
    grps.sort((a, b) => meanShare(a) - meanShare(b));
    window.Plotly.react("c-mix", [
      {
        type: "bar", orientation: "h", name: "country",
        y: grps, x: grps.map(g => mix.country[g] != null ? mix.country[g] : null),
        marker: { color: spreadPalette(PROFILE_BLUE, grps.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: grps, x: grps.map(g => mix.peer[g] != null ? mix.peer[g] : null),
        marker: { color: spreadPalette(PROFILE_PEER, grps.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "share of disease-coded studies (%)", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: grps, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Evaluation-method mix (§11.2). y_order = peer-share desc (ties alphabetical
    // asc). ggplot renders factor level 1 at the BOTTOM ("no display reversal"), so
    // the top-ranked type sits at the bottom of the chart. Plotly's categoryarray
    // also places its FIRST entry at the BOTTOM of a horizontal-bar y axis, so
    // categoryarray = y_order AS-IS reproduces the ggplot display exactly: reading
    // the chart top→bottom the types appear in REVERSE y_order (peer share ascending).
    const meth = prof.c_methods;
    const yOrder = meth.y_order;
    const methVal = (side, t) => meth[t] && meth[t][side] != null ? meth[t][side] : null;
    window.Plotly.react("c-methods", [
      {
        type: "bar", orientation: "h", name: "country",
        y: yOrder, x: yOrder.map(t => methVal("country_share", t)),
        marker: { color: spreadPalette(PROFILE_TEAL, yOrder.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: yOrder, x: yOrder.map(t => methVal("peer_share", t)),
        marker: { color: spreadPalette(PROFILE_PEER, yOrder.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "share of studies (%)", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: yOrder, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Approach & reporting (§11.3). Fixed metric order Model-based → Open access;
    // ggplot uses levels = rev(metrics) so Model-based renders ON TOP and Open
    // access at the bottom. Plotly categoryarray first entry = bottom, so the
    // category array is the listed order reversed. A null pct (empty OA-known
    // subset) leaves that series' bar omitted.
    const sig = prof.c_signals;
    const sigCats = db.registries.SIGNAL_METRICS.slice().reverse();
    const sigVal = (side, m) => sig[m] && sig[m][side] != null ? sig[m][side] : null;
    window.Plotly.react("c-signals", [
      {
        type: "bar", orientation: "h", name: "country",
        y: sigCats, x: sigCats.map(m => sigVal("country_pct", m)),
        marker: { color: spreadPalette(PROFILE_LAVENDER, sigCats.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>country</extra>"
      },
      {
        type: "bar", orientation: "h", name: "income group",
        y: sigCats, x: sigCats.map(m => sigVal("peer_pct", m)),
        marker: { color: spreadPalette(PROFILE_PEER, sigCats.length) },
        hovertemplate: "%{y}: %{x:.1f}%<extra>income group</extra>"
      }
    ], {
      barmode: "group",
      font: BASE_FONT,
      margin: { t: 10, b: 70, l: 170, r: 20 },
      legend: hLegend(-0.22),
      xaxis: { title: "% of studies", gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: sigCats, automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);

    // Peer benchmark (§11.4): log10×log10 scatter of the filtered income-group
    // rows; peers grey-blue, selected country gold, dashed type-7 median line with
    // a muted annotation. Rows without usable burden are visibly absent.
    const bm = prof.c_benchmark;
    // country names are data-derived; Plotly renders hover text as HTML.
    const hoverOf = x => esc(x.country) + " — " + fmtNum(x.studies) + " studies — " +
      rRound(x.per100k, 2) + " per 100k DALYs";
    const bmPeers = bm.rows.filter(x => x.iso3 !== prof.iso3);
    const bmSel = bm.rows.filter(x => x.iso3 === prof.iso3);
    const bmLayout = {
      font: BASE_FONT,
      margin: { t: 20, b: 60, l: 70, r: 20 },
      xaxis: { type: "log", title: "Total disease burden (DALYs, 2023, log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: "Studies per 100k DALYs (log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    };
    if (bm.median_per100k != null) {
      bmLayout.shapes = [{
        type: "line", xref: "paper", x0: 0, x1: 1,
        yref: "y", y0: bm.median_per100k, y1: bm.median_per100k,
        line: { color: "#b08d3e", width: 1.25, dash: "dash" }
      }];
      bmLayout.annotations = [{
        text: "income-group median", xref: "paper", x: 0.99, xanchor: "right",
        yref: "y", y: bm.median_per100k, yanchor: "bottom", showarrow: false,
        font: { size: 10, color: "#8f702d" }
      }];
    }
    window.Plotly.react("c-benchmark", [
      {
        type: "scatter", mode: "markers", name: "income group", showlegend: false,
        x: bmPeers.map(x => x.dalys), y: bmPeers.map(x => x.per100k),
        text: bmPeers.map(hoverOf), hoverinfo: "text",
        marker: { color: "#9fb7c8", size: 9, opacity: 0.72, line: { color: "white", width: 0.5 } }
      },
      {
        type: "scatter", mode: "markers", name: "country", showlegend: false,
        x: bmSel.map(x => x.dalys), y: bmSel.map(x => x.per100k),
        text: bmSel.map(hoverOf), hoverinfo: "text",
        marker: { color: "#2f9b92", size: 15, line: { color: "#ffffff", width: 1.2 } }
      }
    ], bmLayout, PLOTLY_CFG);
  }

  // ---- Country landscape tab ------------------------------------------------

  // Lazy per-country drill shard (§16.1/§16.2). Missing files (zero-study
  // countries such as MUS/ERI) resolve to null instead of throwing.
  async function loadDrill(iso3) {
    if (drillCache[iso3]) return drillCache[iso3];
    try {
      const r = await fetch("data/drill/" + iso3 + ".json?v=" + BUILD);
      if (!r.ok) return null;
      const payload = await r.json();
      drillCache[iso3] = payload;
      db.drill = db.drill || {};
      db.drill[iso3] = payload;
      return payload;
    } catch (e) {
      return null;
    }
  }

  function setupLandscapePicker() {
    const sel = $("land-country");
    for (const r of landscapeCountries(db)) {
      const o = document.createElement("option");
      o.value = r.iso3;
      o.textContent = r.country;
      sel.appendChild(o);
    }
    landSelect = new window.TomSelect(sel, {
      placeholder: "Pick a country…",
      // Render the list in <body> so card/tab overflow cannot clip it.
      dropdownParent: "body",
      onChange: val => { if (val) showCountryMix(val); }
    });
    if (landCrossIndex) landSelect.setValue(landCrossIndex.iso3, true);
  }

  function renderLandscape() {
    renderLandscapeScatter();
    // Seed the mix panels with the most-studied country so the tab never
    // opens empty (§2.6).
    let seed = null, best = -1;
    for (const r of db.countries) {
      if (r.studies > best) { best = r.studies; seed = r.iso3; }
    }
    if (seed) showCountryMix(seed);
  }

  function renderLandscapeScatter() {
    const pts = landscapePoints(db);
    const maxS = pts.reduce((a, p) => Math.max(a, p.studies), 1);
    const traces = db.incLv.map(inc => {
      const rows = pts.filter(p => p.income === inc);
      return {
        type: "scatter", mode: "markers", name: inc,
        x: rows.map(p => p.dalys),
        y: rows.map(p => p.spend_per_person),
        customdata: rows.map(p => p.iso3),
        // country names and formatted numbers are data-derived; Plotly renders
        // hover text as HTML, so names pass through esc().
        text: rows.map(p => {
          let t = esc(p.country) + "<br>" + fmtNum(p.studies) + " studies<br>" +
            "US$" + rRound(p.spend_per_person, 2) + " spending per person";
          t += "<br>" + rRound(p.per100k, 2) + " per 100k DALYs";
          if (p.per_bn != null) t += "<br>" + rRound(p.per_bn, 2) + " per US$1bn";
          return t;
        }),
        hoverinfo: "text",
        marker: {
          color: db.palInc[inc], opacity: 0.78,
          size: rows.map(p => 6 + 30 * Math.sqrt(p.studies / maxS)),
          line: { color: "rgba(255,255,255,.9)", width: 0.8 }
        }
      };
    });
    window.Plotly.react("land-scatter", traces, {
      font: BASE_FONT,
      margin: { t: 20, b: 70, l: 70, r: 20 },
      legend: hLegend(-0.16),
      xaxis: { type: "log", title: "Total disease burden (DALYs, 2023, log)", gridcolor: "#eeebe3" },
      yaxis: { type: "log", title: "Health spending per person (US$, log)", gridcolor: "#eeebe3" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
    const div = $("land-scatter");
    if (!div._mixClickBound) {
      div._mixClickBound = true;
      div.on("plotly_click", ev => {
        const p = ev.points && ev.points[0];
        if (!p || !p.customdata) return;
        showCountryMix(p.customdata);
      });
    }
  }

  function renderMixBar(id, rows, xTitle, colors) {
    const desc = rows.slice();
    const bottomUp = desc.slice().reverse();
    window.Plotly.react(id, [{
      type: "bar", orientation: "h",
      y: desc.map(r => r.label),
      x: desc.map(r => r.count),
      // Largest bar strongest: the ramp runs light→strong bottom-up.
      marker: {
        color: spreadPalette(colors, desc.length).reverse(),
        line: { color: "rgba(255,255,255,.75)", width: 0.5 }
      },
      hovertemplate: "%{y}: %{x}<extra></extra>"
    }], {
      font: BASE_FONT,
      margin: { t: 20, b: 50, l: 175, r: 20 },
      xaxis: { title: xTitle, gridcolor: "#eeebe3" },
      yaxis: { categoryorder: "array", categoryarray: bottomUp.map(r => r.label), automargin: true },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function renderCrossHeatmap(mix) {
    const rows = mix.diseaseMix;
    const cols = mix.evalMix;
    const z = rows.map(d => cols.map(e => {
      const cell = mix.cross[d.code + "|" + e.code];
      return (cell && d.count > 0) ? 100 * cell.count / d.count : 0;
    }));
    const text = rows.map((d, i) => cols.map((e, j) => {
      const cell = mix.cross[d.code + "|" + e.code];
      return cell && cell.count > 0 ? rRound(z[i][j], 1) + "% (n=" + cell.count + ")" : "";
    }));
    const keys = rows.map(d => cols.map(e => d.code + "|" + e.code));
    window.Plotly.react("land-cross-heatmap", [{
      type: "heatmap",
      x: cols.map(e => e.label),
      y: rows.map(d => d.label),
      z,
      customdata: keys,
      text,
      hovertemplate: "%{y} × %{x}<br>%{text}<extra></extra>",
      colorscale: [
        [0, "#f5f3ee"],
        [0.25, "#d7e8e5"],
        [0.55, "#78b7ad"],
        [0.78, "#347f86"],
        [1, "#163b5c"]
      ],
      zmin: 0, zmax: 100,
      colorbar: { title: "row<br>share (%)", thickness: 12, len: 0.8 },
      xgap: 2, ygap: 2
    }], {
      font: BASE_FONT,
      margin: { t: 20, b: 80, l: 175, r: 20 },
      xaxis: { title: "evaluation type", automargin: true },
      yaxis: { title: "disease group", automargin: true, autorange: "reversed" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
    const div = $("land-cross-heatmap");
    if (!div._cellClickBound) {
      div._cellClickBound = true;
      div.on("plotly_click", ev => {
        const p = ev.points && ev.points[0];
        if (!p || !landCrossIndex) return;
        const cell = landCrossIndex.cross[p.customdata];
        if (!cell || cell.count === 0) return;
        openStudiesModal(landCrossIndex.iso3, cell.disease, cell.eval, cell.indices);
      });
    }
  }

  function showCountryMix(iso3) {
    const mix = countryMixes(db, iso3);
    if (!mix) return;
    $("land-eval-mix-title").textContent = mix.country + " — " + fmtNum(mix.n_studies) + " studies";
    $("land-disease-mix-title").textContent = mix.country;
    $("land-cross-title").textContent = mix.country;
    renderMixBar("land-eval-mix", mix.evalMix, "studies",
      ["#c9ddef", "#a8c8e3", "#7faed3", "#568fc0", "#356fa8", "#1f5fa8"]);
    renderMixBar("land-disease-mix", mix.diseaseMix, "disease-group rows",
      ["#d8ebe4", "#b5d9ca", "#86c2ad", "#55a88f", "#2f8b73", "#176b58"]);
    renderCrossHeatmap(mix);
    landCrossIndex = { iso3, cross: mix.cross };
    // Keep the picker in step when a bubble click selected the country.
    if (landSelect && landSelect.getValue() !== iso3) landSelect.setValue(iso3, true);
  }

  async function openStudiesModal(iso3, diseaseLabel, evalLabel, indices) {
    const rec = db.countries.find(r => r.iso3 === iso3);
    $("study-modal-title").textContent =
      (rec ? rec.country : iso3) + " — " + diseaseLabel + " × " + evalLabel;
    $("study-modal-count").textContent =
      fmtNum(indices.length) + (indices.length === 1 ? " study" : " studies");
    const list = $("study-modal-list");
    list.textContent = "";
    const loading = el("div", "study-item study-loading");
    loading.textContent = "Loading study texts…";
    list.appendChild(loading);
    $("study-modal").classList.add("open");

    const payload = await loadDrill(iso3);
    list.textContent = "";
    if (!payload) {
      const miss = el("div", "study-item");
      miss.textContent = "Study texts are not available for this country.";
      list.appendChild(miss);
      return;
    }
    for (const r of drillRecords(db, iso3, indices)) {
      const item = el("div", "study-item");
      const title = el("div", "study-title");
      title.textContent = r.title != null ? r.title : "Title unavailable";
      const meta = el("div", "study-meta");
      meta.textContent = db.studies.year[r.s] + " · " +
        db.levels.econ_eval_type[db.studies.econ_eval_type[r.s]] + " · " + diseaseLabel;
      const abs = el("div", "study-abstract");
      if (r.abstract == null) {
        abs.textContent = "No abstract available.";
        abs.classList.add("study-abstract-missing");
      } else {
        abs.textContent = r.abstract + (r.truncated ? " …" : "");
        if (r.truncated) {
          const note = el("span", "study-note");
          note.textContent = " (abstract truncated)";
          abs.appendChild(note);
        }
      }
      item.appendChild(title);
      item.appendChild(meta);
      item.appendChild(abs);
      list.appendChild(item);
    }
  }

  function closeStudyModal() {
    $("study-modal").classList.remove("open");
    $("study-modal-list").textContent = "";
  }

  async function boot() {
    for (const b of document.querySelectorAll(".navbar .nav-link")) {
      if (b.id === "thematic-toggle") continue;
      b.addEventListener("click", () => switchTab(b.dataset.tab));
    }
    for (const button of document.querySelectorAll("[data-country-view]")) {
      button.addEventListener("click", () => showCountryView(button.dataset.countryView));
    }
    // "Thematic analysis" opens the theme index and toggles its dropdown menu.
    $("thematic-toggle").addEventListener("click", e => {
      e.stopPropagation();
      const shouldOpen = !$("thematic-nav").classList.contains("open");
      if (!$("pane-gallery").classList.contains("active")) {
        switchTab("gallery");
        hideSection();
      }
      $("thematic-nav").classList.toggle("open", shouldOpen);
      $("thematic-toggle").setAttribute("aria-expanded", String(shouldOpen));
      $("thematic-menu").hidden = !shouldOpen;
    });
    document.addEventListener("click", e => {
      if (!$("thematic-nav").contains(e.target)) closeThematicMenu();
    });
    $("fig-modal-close").addEventListener("click", closeModal);
    $("fig-modal").addEventListener("click", e => { if (e.target === $("fig-modal")) closeModal(); });
    $("fig-zoom-out").addEventListener("click", () => setFigureZoom(figureZoom - 0.25));
    $("fig-zoom-reset").addEventListener("click", () => setFigureZoom(1));
    $("fig-zoom-in").addEventListener("click", () => setFigureZoom(figureZoom + 0.25));
    $("study-modal-close").addEventListener("click", closeStudyModal);
    $("study-modal").addEventListener("click", e => { if (e.target === $("study-modal")) closeStudyModal(); });
    const closeOaHelp = () => $("oa-help-modal").classList.remove("open");
    $("oa-help-close").addEventListener("click", closeOaHelp);
    $("oa-help-modal").addEventListener("click", e => { if (e.target === $("oa-help-modal")) closeOaHelp(); });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") { closeModal(); closeStudyModal(); closeThematicMenu(); closeOaHelp(); }
    });
    $("gal-back").addEventListener("click", goBackFromSection);
    for (const b of document.querySelectorAll("[data-trend-mode]")) {
      b.addEventListener("click", () => setOverviewTrendMode(b.dataset.trendMode));
    }

    const get = async name => {
      // ?v=BUILD cache-buster; BUILD is stamped at publish time (see top).
      const r = await fetch("data/" + name + ".json?v=" + BUILD);
      if (!r.ok) throw new Error("failed to load data/" + name + ".json: " + r.status);
      return r.json();
    };
    const [dict, studies, geo, disease, countries, content] = await Promise.all(
      ["dict", "studies", "geo", "disease", "countries", "content"].map(get));
    db = loadData({ dict, studies, geo, disease, countries, content });

    // Gallery sections, figure entries and the interpolated paper01 PRISMA
    // caption come from content.json (§15.1), regrouped by buildGallery().
    GALLERY = buildGallery(db.content);
    FIG_INDEX = {};
    for (const sec of GALLERY) {
      for (const f of sec.figs) FIG_INDEX[f.file] = { ...f, sectionTitle: sec.title };
    }

    if (window.Plotly && !window.Plotly.__softColorway) {
      const react = window.Plotly.react;
      window.Plotly.react = (gd, data, layout = {}, cfg) =>
        react.call(window.Plotly, gd, data, Object.assign({ colorway: SOFT_COLORWAY }, layout), cfg);
      window.Plotly.__softColorway = true;
    }

    renderOverview();
    renderOverviewTrend();
    renderGalleryIndex();
    setupExplorerControls();
    refreshExplorer();
    setupCountryPane();
    renderLandscape();
  }

  // err.message can embed data-derived text (URLs, server responses) —
  // textContent only, never el()'s innerHTML path.
  function showBootError(err) {
    const box = el("div", "loading-wrap");
    box.textContent = "Failed to start: " + err.message;
    document.querySelector("main").prepend(box);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => boot().catch(showBootError));
  } else {
    boot().catch(showBootError);
  }
}
