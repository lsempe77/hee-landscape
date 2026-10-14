// Cache-busting build token. Locally the literal "2026-10-08" is a harmless
// query string; at publish time webapp/publish-stamp.mjs rewrites every
// occurrence in index.html and app.js to the bundle build value.
const BUILD = "2026-10-14-all-figures-reconciled";

const CODED_COLS = ["econ_eval_type", "design_basis", "model_label", "qaly_label",
  "oa_label", "geo_scope", "era", "topic_domain"];

// econ_eval_type level for reviews with no evaluation of their own
// (scripts/apply_review_eval_type.py). Type shares leave it out.
const REVIEW_TYPE = "Review (no evaluation type)";
// review_label levels offered as choices in the evaluation-type filter.
const REVIEW_CHOICES = ["Systematic review", "Other review"];

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

// Publication links and availability come from the same study-level fields.
export function publicationUrl(studies, index) {
  const candidate = studies.url?.[index];
  if (candidate) {
    try {
      const parsed = new URL(candidate);
      if (parsed.protocol === "https:" || parsed.protocol === "http:") return parsed.href;
    } catch { /* Invalid URLs are not rendered as links. */ }
  }
  const doi = studies.doi?.[index];
  return /^10\.\d{4,9}\/\S+$/i.test(doi || "") ? "https://doi.org/" + doi : null;
}

export function publicationAccessCounts(studies) {
  if (!Array.isArray(studies.doi) || !Array.isArray(studies.url)) return null;
  return studies.id.reduce((count, _, index) => count + (publicationUrl(studies, index) ? 1 : 0), 0);
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
// Plain-language names for selector options whose content.json labels are
// technical; the column each option reads is unchanged.
const PLAIN_LABELS = {
  "Nothing (total)": "All studies (total)",
  "Model vs measured": "Computer model or measured",
  "Era": "Period (2010–17 or 2018–26)",
  "Topic domain": "Research field",
  "Reports an ICER": "Reports a cost per health gained (ICER)",
  "Reports a threshold": "Compares with a value-for-money threshold",
  "Studies per 100k DALYs": "Studies per 100,000 healthy years lost (DALYs)",
  "Studies per US$1bn spending": "Studies per US$1bn of health spending",
  "Total DALYs (GBD 2023)": "Disease burden: healthy years lost (DALYs, 2023)",
  "Health spending, PPP US$bn (2022)": "Health spending, US$bn adjusted for prices (2022)"
};
export const plainLabel = label => PLAIN_LABELS[label] || label;

export function buildRegistries(content) {
  if (!content || !content.registries) {
    throw new Error("buildRegistries: content.json with .registries is required");
  }
  const r = content.registries;
  const toMap = arr => new Map(arr.map(o => [plainLabel(o.label), o.column]));
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

export function loadData({ dict, studies, geo, disease, countries, content, funders, languages }) {
  const levels = dict.levels;
  const codeOf = {};
  for (const col of CODED_COLS) {
    codeOf[col] = new Map(levels[col].map((lab, i) => [lab, i]));
  }
  // Optional: review_label (scripts/apply_review_eval_type.py) feeds the review
  // choices in the Explorer's evaluation-type filter.
  if (levels.review_label && studies.review_label) {
    codeOf.review_label = new Map(levels.review_label.map((lab, i) => [lab, i]));
  }
  const pal = dict.meta.pal_inc;
  const palInc = {};
  if (Array.isArray(pal)) dict.meta.inc_lv.forEach((lv, i) => { palInc[lv] = pal[i]; });
  else Object.assign(palInc, pal);
  Object.assign(palInc, LANDSCAPE_INCOME_COLORS);
  // GBD 2023 groups (disease_gbd.json, scripts/build_disease_gbd_data.py) carry
  // their own names; the older MeSH-based disease.json uses dict.disease_grps.
  const diseaseGrps = disease.grps || dict.disease_grps;
  const diseaseSets = diseaseGrps.map(() => new Set());
  for (let i = 0; i < disease.s.length; i++) diseaseSets[disease.g[i]].add(disease.s[i]);
  // Funders as reported (scripts/build_funder_filter.py); "any" also counts
  // funders too rare to list.
  const fund = funders || { names: [], n: [], s: [], f: [], any: [] };
  const funderSets = fund.names.map(() => new Set());
  for (let i = 0; i < fund.s.length; i++) funderSets[fund.f[i]].add(fund.s[i]);
  const fundedSet = new Set(fund.any);
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
    // Income group in force on 1 January of a publication year (World Bank
    // FY of that year); incomeOf is the current group, for country views.
    incomeAt: (c, y) => {
      const v = countries[c].income_y;
      return v ? (v[y - dict.meta.years[0]] ?? null) : countries[c].income;
    },
    regionOf: countries.map(r => r.who_region),
    disease_grps: diseaseGrps,
    diseaseSets,
    funders: fund, funderSets, fundedSet,
    // Publication language per study (scripts/build_language_filter.py).
    languages: languages || null,
    years: dict.years
  };
}

export const ANY_FUNDER = "Any funder reported";

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
    funder: arr(f.funder),
    language: arr(f.language),
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

  // The evaluation-type filter also offers review choices. Choosing a review
  // hides the four types, so the two never combine.
  const reviewMap = db.codeOf.review_label;
  const reviewSel = reviewMap ? f.evaltype.filter(l => REVIEW_CHOICES.includes(l)) : [];
  const typeSel = f.evaltype.filter(l => !REVIEW_CHOICES.includes(l));
  const reviewCodes = reviewSel.length ? new Set(reviewSel.map(l => reviewMap.get(l))) : null;
  const evalCodes = !reviewCodes && typeSel.length
    ? new Set(typeSel.map(l => db.codeOf.econ_eval_type.get(l))) : null;
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

  // Funder: a study passes if it reports any selected funder ("any" = any funder).
  let funSet = null;
  if (f.funder.length && db.funderSets) {
    funSet = new Set();
    for (const name of f.funder) {
      const src = name === ANY_FUNDER ? db.fundedSet : db.funderSets[db.funders.names.indexOf(name)];
      if (src) for (const s of src) funSet.add(s);
    }
  }

  const langCodes = f.language.length && db.languages
    ? new Set(f.language.map(l => db.languages.levels.indexOf(l))) : null;

  for (let s = 0; s < n; s++) {
    const y = st.year[s];
    if (y < lo || y > hi) continue;
    if (evalCodes && !evalCodes.has(st.econ_eval_type[s])) continue;
    if (reviewCodes && !reviewCodes.has(st.review_label[s])) continue;
    if (designCodes && !designCodes.has(st.design_basis[s])) continue;
    if (modelCode !== null && st.model_label[s] !== modelCode) continue;
    if (qalyCode !== null && st.qaly_label[s] !== qalyCode) continue;
    if (oaCode !== null && st.oa_label[s] !== oaCode) continue;
    if (scopeCode !== null && st.geo_scope[s] !== scopeCode) continue;
    if (disSet && !disSet.has(s)) continue;
    if (funSet && !funSet.has(s)) continue;
    if (langCodes && !langCodes.has(db.languages.code[s])) continue;
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
    if (incSet && !incSet.has(db.incomeAt(c, g.y[i]))) continue;
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
      who_region: r.who_region,
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
  const isGeo = varName === "income" || varName === "who_region";
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
      const cat = varName === "income" ? db.incomeAt(c, y) : db.regionOf[c];
      if (cat == null) continue;
      const key = s + "|" + y + "|" + cat;
      if (seen.has(key)) continue;
      seen.add(key);
      bump(y, cat);
    }
  } else {
    const catOf = studyCatGetter(db, varName, flt);
    for (const s of flt.studies) bump(db.studies.year[s], catOf(s));
  }
  const out = {};
  for (const y of [...counts.keys()].sort((a, b) => a - b)) {
    out[y] = Object.fromEntries(counts.get(y));
  }
  return out;
}

// With a review chosen in the evaluation-type filter, charts by evaluation type
// show each study's review label instead: reviews are not counted as a type.
function reviewsChosen(db, flt) {
  return !!(db.codeOf.review_label && flt && flt.filt &&
    flt.filt.evaltype.some(l => REVIEW_CHOICES.includes(l)));
}

function studyCatGetter(db, varName, flt) {
  const st = db.studies;
  if (varName === "econ_eval_type" && reviewsChosen(db, flt)) {
    const rl = db.levels.review_label;
    return s => rl[st.review_label[s]];
  }
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
    const stackOf = stacked ? studyCatGetter(db, sv, flt) : null;
    const d = db.disease;
    for (let i = 0; i < d.s.length; i++) {
      const s = d.s[i];
      if (!flt.mask[s]) continue;
      add(db.disease_grps[d.g[i]], stacked ? stackOf(s) : null);
    }
  } else {
    const catOf = studyCatGetter(db, xv, flt);
    const stackOf = stacked ? studyCatGetter(db, sv, flt) : null;
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
    Region: r.who_region == null ? "" : r.who_region,
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
  let nc = 0, np = 0;
  for (const s of cs) { const t = lv[col[s]]; if (t === REVIEW_TYPE) continue; cn.set(t, (cn.get(t) || 0) + 1); nc++; }
  for (const s of ps) { const t = lv[col[s]]; if (t === REVIEW_TYPE) continue; pn.set(t, (pn.get(t) || 0) + 1); np++; }
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
    who_region: r.who_region,
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
    ["Income group (July 2026)", r.income],
    ["WHO region", r.who_region == null ? "—" : r.who_region]
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
// ALL_COUNTRIES pools every study that names at least one country (a study
// naming several countries counts once), as a global baseline.
export const ALL_COUNTRIES = "__ALL__";

export function countryMixes(db, iso3) {
  const all = iso3 === ALL_COUNTRIES;
  const ci = all ? -1 : db.countries.findIndex(r => r.iso3 === iso3);
  if (!all && ci < 0) return null;
  const g = db.geo;
  const cs = new Set();
  for (let i = 0; i < g.s.length; i++) if (all || g.c[i] === ci) cs.add(g.s[i]);

  const lv = db.levels.econ_eval_type;
  const evalCounts = new Map();
  for (const s of cs) {
    const t = lv[db.studies.econ_eval_type[s]];
    evalCounts.set(t, (evalCounts.get(t) || 0) + 1);
  }
  // Reviews with no evaluation type go last, after the four types.
  const evalMix = [...evalCounts.entries()]
    .map(([label, count]) => ({ label, code: lv.indexOf(label), count }))
    .sort((a, b) => ((a.label === REVIEW_TYPE) - (b.label === REVIEW_TYPE)) ||
      (b.count - a.count) || cmpStr(a.label, b.label));

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

  const r = all ? { country: "All countries", income: null } : db.countries[ci];
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

const OA_COLORS = { "Open access": "#62A89B", "Not open": "#D98F7A", "Unknown": "#B7BBC5" };
const ACCENT = "#1f5fa8";
const GREY = "#adb5bd";
// Softer income colours, shared by every income-coloured chart.
const LANDSCAPE_INCOME_COLORS = {
  "Low income": "#D98F7A",
  "Lower middle income": "#D6B264",
  "Upper middle income": "#62A89B",
  "High income": "#6D91BE"
};
// Country profile: light-to-strong ramps for the country bars, grey-blue for peers.
const PROFILE_BLUE = ["#c9ddef", "#9fc4df", "#70a7cf", "#4288bb", "#1f659f"];
const PROFILE_TEAL = ["#d8ebe4", "#add6c7", "#79bda6", "#48a087", "#217b68"];
const PROFILE_LAVENDER = ["#e5ddec", "#cab9da", "#ad91c4", "#8c69aa", "#6d4d8e"];
const PROFILE_PEER = ["#edf1f4", "#dfe6eb", "#ced9e1", "#bdcbd5", "#aabcc8"];
// Default series colours for interactive charts (same family as the figures).
const SOFT_COLORWAY = ["#6D91BE", "#62A89B", "#88B8C5", "#9B87B8", "#D6B264", "#88B7A8",
  "#B79BCB", "#7E94B1", "#D98F7A", "#9FB7C8"];
// Light-to-strong blue-teal ramp used for single-series bars and maps.
const SOFT_RAMP = ["#EAF1F5", "#D3E3EA", "#ACCED8", "#88B8C5", "#679AAC", "#476F94"];

function rampColor(t) {
  const stops = SOFT_RAMP.map(h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)));
  const x = Math.min(1, Math.max(0, t)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x));
  const f = x - i;
  const c = stops[i].map((v, k) => Math.round(v + (stops[i + 1][k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
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

if (typeof document !== "undefined") {

  const $ = id => document.getElementById(id);
  const PLOTLY_CFG = { responsive: true, displayModeBar: false };
  const BASE_FONT = { family: "Inter, sans-serif", size: 12, color: "#1c2733" };

  let db = null;
  let GALLERY = [];
  // Figures redrawn here with income at publication year (scripts/
  // build_income_pubyear_figures.py): original file -> { file, caption }.
  // The original stays the figure's key; only the image and caption change.
  let FIGURE_UPDATES = {};
  const figSrc = file => "figures/" + ((FIGURE_UPDATES[file] && FIGURE_UPDATES[file].file) || file);
  let FIG_INDEX = {};
  // Interactive figures: self-contained HTML pages built by scripts/ (here
  // scripts/build_glance_regions_who_v4.py), added on top of content.json's gallery
  // so the upstream content build stays untouched. Shown in an iframe.
  const EXTRA_FIGURES = [{
    section: "Geography",
    index: 0,
    fig: {
      file: "fig_glance_regions_who_v4.html",
      html: true,
      // No caption: the summary in figure_copy.json says it all, so no
      // "Technical details" toggle for this figure.
      title: "Health Economic Evaluations"
    }
  }];
  // Temporary placeholder section, shown last: replication of Schmallenbach et al.
  // (2025, Nature Medicine) Fig. 2a and Fig. 3 for health economic evaluations, with
  // sensitivity and supplementary versions (scripts/build_kld_replication_v2.py;
  // figures copied from exports/kld_replication_v2_2026-10-14).
  const KLD_DIR = "schmallenbach2025/";
  const KLD_NOTE = "Method. Research–disease divergence is the Kullback–Leibler divergence (KLD) of the research mix " +
    "from the burden mix across GBD level-2 causes: the sum over causes of p·ln(p/q), where p is a cause's share of " +
    "DALYs (GBD 2023) and q its share of studies (a study naming several causes counts for each). 0 = research spread " +
    "across diseases exactly as burden is. No smoothing, as in the paper's main analysis: no cause has zero studies in " +
    "any 3-year window of the 16-cause analysis. 3-year rolling windows; solid = 2010–2019, dashed = windows reaching " +
    "2020–23 (COVID-19). Shaded bands: 95% intervals from resampling studies within each year (1,000 draws); in 1.8% of " +
    "draws a cause was left with no study and was given 0.5 study. Geography: the paper's Fig. 2a and Fig. 3 compare " +
    "global research with global burden, so geography does not enter; our 'with high-income studies' panels do the same " +
    "(all studies vs global DALYs). The split by income is our extension. For it, studies are placed by the country " +
    "studied (the paper's regional analyses use first-author country). An economic evaluation is tied to its setting: " +
    "its costs, prices, health-care delivery and value-for-money threshold are those of the country it examines, so it " +
    "informs decisions there. Placing it by the country studied therefore tests whether the evidence available to each " +
    "setting matches that setting's burden, which is the question here. Placing it by author country would count a " +
    "high-income team's evaluation of a low-income country as high-income research, mixing up who produces evidence " +
    "(shown separately in the authorship figures) with whom it serves. Author locations are also known for only 85% of " +
    "studies. Income is the World Bank group in force at publication (studies) or in the burden year (DALYs). " +
    "Reference: Schmallenbach L et al. Nat Med 2025;31:3101–9, doi:10.1038/s41591-025-03923-0.";
  const KLD_CAVEATS = " Caveats. (1) Small numbers: 440 studies of low- and middle-income countries in 2010–12 and " +
    "965 in 2017–19 (all studies: 2,999 and 5,239), against 7.4–8.6 million articles in the paper. Intervals for " +
    "low- and middle-income countries are wide, and their changes cannot be told apart from zero. (2) KLD reacts " +
    "strongly to causes with few studies. The rise for low- and middle-income countries in 2016–18 comes mainly from " +
    "cardiovascular disease (9% of studies against 20% of burden, a gap that widened) and chronic respiratory disease, " +
    "which fell to 8 studies in that window (0.9% of studies against 4.7% of burden). Leaving out causes below 1% (the " +
    "paper's check; see the sensitivity figure) removes the sharp rise. (3) Levels are not comparable between panels, " +
    "because each panel uses a different burden reference (global or low- and middle-income DALYs): compare trends " +
    "within a panel. (4) The period is shorter than the paper's (2010–2023 against 1999–2019), and windows reaching " +
    "2020–23 are affected by COVID-19. (5) The research is health economic evaluations and reviews of them, not all " +
    "health research as in the paper; diseases are coded to GBD 2023 causes from each study's title and abstract. " +
    "(6) Research and burden are compared in the same years, without a time lag. (7) A study naming several causes, or " +
    "countries in both income groups, counts in each. Preliminary results, not peer reviewed.";
  const KLD_FIG3_NOTE = " Observed line against two scenarios fixed at 2010–12: research fixed (only DALYs change, " +
    "green) and DALYs fixed (only research changes, red). Box: the change in each line from 2010–12 to 2017–19, as % of " +
    "2010–12 divergence, with 95% intervals. As in the paper, the two scenarios need not add up to the observed change.";
  const KLD_FIG4_NOTE = " Shown as shares rather than the paper's per-cause KLD terms, which can be negative and so " +
    "misread single causes. 'Closer'/'further': whether the gap between a cause's research share and DALY share narrowed.";
  const KLD_20_NOTE = " 20-cause caveat: very few studies are coded to transport injuries (0–5 per 3-year window even " +
    "across all studies; none in 2010–12 and 2011–13 overall, and none in most windows for low- and middle-income or " +
    "high-income studies), and self-harm and violence has 0–1 low- and middle-income studies in early windows. An " +
    "empty cause is given 0.5 study, so the values in this version depend on that choice and should be read with caution.";
  const kldNotes = (scope, extra = "") => scope + extra + " " + KLD_NOTE + KLD_CAVEATS;
  // The paper's own figures, as tabs in the figure pop-up (CC BY 4.0; cropped from the published PDF).
  const KLD_CREDIT = " Reproduced from Schmallenbach L, Bley M, Bärnighausen TW, Sugimoto CR, Lerchenmüller C, " +
    "Lerchenmueller MJ. Global distribution of research efforts, disease burden, and impact of US public funding " +
    "withdrawal. Nat Med 2025;31:3101–9, doi:10.1038/s41591-025-03923-0, under a CC BY 4.0 licence " +
    "(https://creativecommons.org/licenses/by/4.0/). Changes: cropped from the published PDF; caption shortened.";
  const kldViews = (ours, original) => [
    { label: "Our replication (HEE map)", file: ours },
    { label: "Original (Schmallenbach et al. 2025)", ...original }];
  const EXTRA_SECTIONS = [{
    title: "Schmallenbach et al 2025",
    blurb: "Temporary placeholder. A replication of Schmallenbach et al. (2025, Nature Medicine; " +
      "https://doi.org/10.1038/s41591-025-03923-0) Fig. 2a and Fig. 3 for " +
      "health economic evaluations: is the mix of diseases studied moving closer to the mix of disease burden, and is " +
      "that because research changed or because burden changed? With and without high-income studies, plus " +
      "sensitivity and supplementary versions. Preliminary findings for discussion, not peer reviewed.",
    figs: [
      { file: KLD_DIR + "main_fig2a_16causes.png", title: "Evolution of research–disease divergence (Fig. 2a)",
        summary: "From 2010–12 to 2017–19, divergence for all studies changed by -20% (95% interval -32% to -6%). For studies of low- and middle-income countries, it changed by -5% (-34% to +25%): no clear change. Open the figure to compare it with the paper's original.",
        caption: kldNotes("The paper's 16 GBD level-2 causes."),
        views: kldViews(KLD_DIR + "main_fig2a_16causes.png", {
          file: KLD_DIR + "original_fig2a.png", title: "Original: evolution of research–disease divergence (Schmallenbach et al. 2025, Fig. 2a)",
          summary: "Across all life-science research, divergence between research and disease burden fell by about 48% " +
            "from 1999 to 2019, and about 60% to 2021 once the COVID-19 years are added.",
          caption: "Research–disease divergence (KLD) of global research share versus global DALY share for each disease " +
            "category and each year, 1999–2021, based on 8.6 million disease-specific research articles across 16 level-2 " +
            "disease causes; dashed line: 2020–21. Global research vs global DALYs, so geography does not enter; the sample " +
            "is limited to articles the authors could geolocate by first-author affiliation (about 89%)." + KLD_CREDIT }) },
      { file: KLD_DIR + "main_fig3_16causes.png",
        title: "Contributions of research and disease burden to changes in divergence (Fig. 3)",
        summary: "For all studies, burden changes alone changed divergence by -25%, while research changes alone changed it by +7% (-9% to +25%). For low- and middle-income settings, burden changes alone changed it by +10% (+3% to +16%), and research changes alone by -9% (-36% to +20%). These scenarios need not add up to the observed change.",
        caption: kldNotes("The paper's 16 GBD level-2 causes.", KLD_FIG3_NOTE),
        views: kldViews(KLD_DIR + "main_fig3_16causes.png", {
          file: KLD_DIR + "original_fig3.png",
          title: "Original: contributions of research and disease burden to changes in divergence (Schmallenbach et al. 2025, Fig. 3)",
          summary: "The observed fall in divergence (blue) follows the line where research is held at its 1999 mix (green), " +
            "while holding DALYs at 1999 (red) shows no fall: the paper concludes that changing disease burden, not " +
            "changing research, narrowed the divergence.",
          caption: "Research–disease divergence (KLD) of global research share versus global DALY share for each disease " +
            "and each year (1999–2019), with observed data (blue line) and simulated distributions assuming constant 1999 " +
            "research shares (green line) and constant 1999 DALY shares (red line), based on 7.4 million disease-specific " +
            "articles across 16 level-2 disease causes." + KLD_CREDIT }) },
      { file: KLD_DIR + "main_fig4_16causes.png", title: "Which diseases moved, 2010–12 to 2017–19",
        summary: "Each disease's share of studies and share of burden, at the start and end. Research on low- and " +
          "middle-income countries moved a lot: HIV/AIDS fell from 18% to 10% of studies and cancer rose from 15% to " +
          "23%, while cardiovascular disease stayed at about 9% of studies against about 20% of burden.",
        caption: kldNotes("The paper's 16 GBD level-2 causes.", KLD_FIG4_NOTE) },
      { file: KLD_DIR + "supp_fig2a_rare_causes_excluded_16causes.png", title: "Sensitivity: divergence without rare causes",
        summary: "The paper's check for causes with very few studies: divergence without causes whose share of studies or " +
          "burden is below 1%. The trends hold (with high-income studies −16%; low- and middle-income −19%, with a wide " +
          "interval), and the sharp low- and middle-income rise in 2016–18 disappears.",
        caption: kldNotes("The paper's 16 GBD level-2 causes, leaving out one fixed set per panel: causes below 1% of " +
          "studies or burden in any window (with high-income studies: nutritional deficiencies and substance use; low- " +
          "and middle-income: chronic respiratory, skin and substance use). A fixed set stops the line jumping when a " +
          "cause crosses 1%.") },
      { file: KLD_DIR + "supp_fig2a_20causes.png", title: "Sensitivity: divergence with mental disorders and injuries",
        summary: "The same as Fig. 2a with 20 causes: the paper's 16 plus mental disorders and the three injury groups, " +
          "which the paper leaves out and where research is far below burden. With high-income studies divergence fell " +
          "23%; for low- and middle-income countries it stayed flat (−4%).",
        caption: kldNotes("20 GBD level-2 causes.", KLD_20_NOTE) },
      { file: KLD_DIR + "supp_fig3_20causes.png", title: "Sensitivity: research and burden contributions, 20 causes",
        summary: "With mental disorders and injuries included, the fall with high-income studies is again mostly burden " +
          "(−14% with research fixed; research changes alone −8%, interval −20% to +7%), and divergence for low- and " +
          "middle-income countries stays flat.",
        caption: kldNotes("20 GBD level-2 causes.", KLD_FIG3_NOTE + KLD_20_NOTE) },
      { file: KLD_DIR + "supp_fig4_20causes.png", title: "Sensitivity: which diseases moved, 20 causes",
        summary: "Research and burden shares for 20 causes, including mental disorders and injuries.",
        caption: kldNotes("20 GBD level-2 causes.", KLD_FIG4_NOTE + KLD_20_NOTE) },
      { file: KLD_DIR + "supp_fig2a_hic_16causes.png", title: "Supplementary: divergence for high-income studies",
        summary: "Studies of high-income countries against high-income DALYs: divergence fell 21% from 2010–12 to " +
          "2017–19 (−38% to −1%).",
        caption: kldNotes("The paper's 16 GBD level-2 causes.") },
      { file: KLD_DIR + "supp_fig3_hic_16causes.png", title: "Supplementary: research and burden contributions, high-income studies",
        summary: "For high-income countries, research changes explain the fall: research changes alone lowered divergence " +
          "30% (−45% to −12%), while burden changes alone would have raised it 10%. This differs from the paper.",
        caption: kldNotes("The paper's 16 GBD level-2 causes.", KLD_FIG3_NOTE) },
      { file: KLD_DIR + "supp_fig4_hic_16causes.png", title: "Supplementary: which diseases moved, high-income studies",
        summary: "Research and burden shares for studies of high-income countries, 2010–12 and 2017–19.",
        caption: kldNotes("The paper's 16 GBD level-2 causes.", KLD_FIG4_NOTE) }
    ]
  }];
  // Thematic sections hidden from the site, and figures moved to one other
  // section (removed from every section they were in), so each appears once.
  // content.json is left as built. "Size & growth": its growth chart
  // duplicates the Overview's Publication trends; its QALY/DALY chart (also in
  // Trends over time) moves to Methods & metrics only.
  const HIDDEN_SECTIONS = new Set(["Size & growth", "Maps & regional charts"]);
  // The selection flow is opened from the Overview's study-count card.
  // The Schmallenbach "which diseases moved" charts are hidden until they show uncertainty (kept in EXTRA_SECTIONS).
  const HIDDEN_FIGURES = new Set(["paper01.webp", "schmallenbach2025/main_fig4_16causes.png",
    "schmallenbach2025/supp_fig4_20causes.png", "schmallenbach2025/supp_fig4_hic_16causes.png"]);
  // Shown only as the section's index thumbnail; its interactive view already
  // carries the same numbers, so the section page shows that view alone.
  const THUMBNAIL_ONLY_FIGURES = new Set(["fig_wellcome_priorities.svg"]);
  // Renamed sections (applied before the moves below, which use the new
  // names). Authorship figures join open access; funding figures get one
  // section, placed straight after it.
  const SECTION_RENAMES = {
    "Topics & diseases": {
      title: "Topics & diseases",
      blurb: "The main research topics and types of health care studied, which diseases the studies " +
        "cover, and how this differs by country income and over time."
    },
    "Geography & authorship": {
      title: "Geography",
      blurb: "Explore where health economic research exists and how its coverage and intensity " +
        "differ across countries, income groups and regions."
    },
    "Open access & funding": {
      title: "Authorship & access",
      blurb: "Whether studies include researchers based in the country they study, and whether " +
        "readers can get the papers free of charge. Where authors are based is known for most " +
        "studies; open-access status is known for 87%."
    },
    "Priority-setting for funders": {
      title: "Research funding",
      blurb: "Who funds the studies, and where evidence is thin compared with health needs. Only about " +
        "a quarter of studies name a funder, so counts are a minimum. There are no data on funding " +
        "amounts, so the gaps show where evidence is thin, not what it would cost to fill them."
    },
    "Methods & metrics": {
      title: "Methods & metrics",
      blurb: "How studies measure health benefits, how often they rely on computer models, and whether " +
        "their summaries report what decision-makers need."
    },
    "Gaps vs disease burden": {
      title: "Gaps vs disease burden",
      blurb: "How the amount of research compares with the burden of illness and early death in each " +
        "country and for each disease."
    },
    "Trends over time": {
      title: "Trends over time",
      blurb: "How the research has changed since 2010. Charts stop at 2025 because 2026 is incomplete."
    }
  };
  const SECTION_AFTER = { "Research funding": "Authorship & access", "Wellcome priority themes": "Trends over time" };
  // after: file to follow in the target section; first: true puts it first.
  const MOVED_FIGURES = [
    { file: "fig_method_stream_v2.svg", to: "Methods & metrics", after: "fig_metric.webp" },
    { file: "fig_authorship_pattern_v2.svg", to: "Authorship & access", first: true },
    { file: "fig_forest_v2.svg", to: "Authorship & access", after: "fig_authorship_pattern_v2.svg" },
    { file: "paper06_v2.svg", to: "Authorship & access", after: "fig_forest_v2.svg" },
    { file: "fig_collab_chord_v2.svg", to: "Authorship & access", after: "paper06_v2.svg" },
    { file: "fig_funder_funders.svg", to: "Research funding", first: true },
    { file: "fig_map_growth.webp", to: "Geography", after: "fig_worldmap.webp" },
    { file: "fig_map_burden.webp", to: "Geography", after: "paper03.webp" },
    { file: "fig_map_openaccess.webp", to: "Authorship & access", after: "fig_openaccess.webp" },
    { file: "fig_map_authorship_v2.svg", to: "Authorship & access", after: "fig_collab_chord_v2.svg" },
    { file: "fig_map_model.webp", to: "Methods & metrics", after: "paper02.webp" }
  ];
  const SECTION_GROUPS = {
    "Topics & diseases": [
      {
        title: "What the research covers",
        blurb: "The main research topics, the types of health care evaluated, and how they differ " +
          "by country income.",
        files: ["fig_intervention_map.webp", "fig_intervention_mix.webp", "fig_theme_rank.webp"]
      },
      {
        title: "Disease focus",
        blurb: "Which disease groups research focuses on, how this differs by income, " +
          "and how the disease mix is changing over time.",
        files: ["fig_disease_circular.webp", "fig_transition.webp", "paper04.webp", "paper05.webp"]
      }
    ],
    Geography: [
      {
        title: "Geographic coverage",
        blurb: "Where studies have been conducted, how many studies name each country, " +
          "and where the evidence base is growing.",
        files: ["fig_dotmap.svg", "fig_worldmap.webp", "fig_map_growth.webp"]
      },
      {
        title: "Geographic inequalities",
        blurb: "How research intensity differs across countries, income groups and regions, " +
          "including how the evidence compares with disease burden.",
        files: ["fig_glance_regions_who_v4.html", "fig_map_burden.webp", "paper03.webp"]
      }
    ]
  };
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
  let modalFigure = null;

  function setFigureZoom(nextZoom) {
    figureZoom = Math.min(3, Math.max(0.5, nextZoom));
    $("fig-modal-img").style.width = (figureZoom * 100) + "%";
    $("fig-zoom-reset").textContent = Math.round(figureZoom * 100) + "%";
    $("fig-zoom-out").disabled = figureZoom <= 0.5;
    $("fig-zoom-in").disabled = figureZoom >= 3;
  }

  function renderFigureNotes(container, figure) {
    container.textContent = "";
    const summary = el("p", "figure-summary");
    summary.textContent = (figure.summary || figure.caption || "").replace(/\s+/g, " ").trim();
    container.appendChild(summary);
    if (figure.summary && figure.caption) {
      const details = el("details", "figure-technical-details");
      const toggle = el("summary");
      toggle.textContent = "\u24d8 Technical details";
      const note = el("p");
      note.textContent = figure.caption.replace(/\s+/g, " ").trim();
      details.append(toggle, note);
      container.appendChild(details);
    }
  }

  function openModal(file) {
    const f = FIG_INDEX[file];
    if (!f) return;
    // Figures with alternative views (content.json `views`) get tabs; the first view is the default.
    const tabs = $("fig-modal-views");
    tabs.textContent = "";
    tabs.hidden = !f.views || f.views.length < 2;
    const show = (view, button) => {
      // A view inherits the figure's own copy and overrides what it sets itself.
      const shown = view ? { ...f, ...view, views: f.views } : f;
      modalFigure = shown;
      $("fig-modal-title").textContent = shown.title;
      const img = $("fig-modal-img");
      img.src = figSrc(shown.file);
      img.alt = shown.title;
      renderFigureNotes($("fig-modal-caption"), shown);
      setFigureZoom(1);
      $("fig-zoom-viewport").scrollTo(0, 0);
      for (const b of tabs.children) b.setAttribute("aria-selected", String(b === button));
    };
    if (!tabs.hidden) {
      f.views.forEach((view, i) => {
        const button = el("button", "figure-view-tab");
        button.type = "button";
        button.setAttribute("role", "tab");
        button.textContent = view.label;
        // The first view is the figure as published, so it keeps the figure's own title and copy.
        button.addEventListener("click", () => show(i === 0 ? null : view, button));
        tabs.appendChild(button);
      });
    }
    show(null, tabs.firstChild);
    $("fig-modal").classList.add("open");
  }

  // Citation printed under a downloaded figure; the date is the day of download.
  function figureCitation(f) {
    const year = String(db.dict.meta.built).slice(0, 4);
    const url = window.location.href.split("#")[0];
    const today = new Date().toLocaleDateString("en-GB",
      { day: "numeric", month: "long", year: "numeric" });
    return "Source: 3ie (" + year + "). Health Economic Evaluation (HEE) Evidence Map: " +
      f.title + ". " + url + ". Downloaded " + today + ".";
  }

  function wrapCanvasText(ctx, text, maxWidth) {
    const lines = [];
    let line = "";
    for (const word of text.split(" ")) {
      const next = line ? line + " " + word : word;
      if (line && ctx.measureText(next).width > maxWidth) {
        lines.push(line);
        line = word;
      } else {
        line = next;
      }
    }
    if (line) lines.push(line);
    return lines;
  }

  // Draws the figure at full resolution onto a canvas with the citation in a
  // strip underneath, then saves it as PNG (figures are same-origin, so the
  // canvas is not tainted).
  async function downloadFigure() {
    const f = modalFigure;
    if (!f) return;
    const img = new Image();
    img.src = figSrc(f.file);
    try { await img.decode(); } catch (e) { return; }
    const w = img.naturalWidth, h = img.naturalHeight;
    const fontSize = Math.max(14, Math.round(w * 0.011));
    const pad = Math.round(fontSize * 1.4);
    const lineHeight = Math.round(fontSize * 1.45);
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const font = fontSize + "px Inter, 'Segoe UI', Arial, sans-serif";
    ctx.font = font;
    const lines = wrapCanvasText(ctx, figureCitation(f), w - 2 * pad);
    canvas.width = w;
    canvas.height = h + 2 * pad + lines.length * lineHeight;
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, w, h);
    ctx.font = font;
    ctx.fillStyle = "#5b6472";
    ctx.textBaseline = "top";
    lines.forEach((l, i) => ctx.fillText(l, pad, h + pad + i * lineHeight));
    canvas.toBlob(blob => {
      if (!blob) return;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = f.file.replace(/\.[^.]+$/, "") + ".png";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    }, "image/png");
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

  // Overview "at a glance" tiles, including composite cards built from study data.
  const STUDIES_CARD = "__studies";
  const ACCESS_CARD = "__publication_access";
  const GEO_CARD = "__geography";
  const METRICS_CARD = "__outcome_metrics";
  const FUNDERS_CARD = "__funders";
  const OVERVIEW_TILE_ORDER = [
    STUDIES_CARD, ACCESS_CARD,
    GEO_CARD,
    METRICS_CARD, "Model-based", FUNDERS_CARD
  ];
  // Grid widths and colours per card (styles.css: .tile-*).
  const TILE_CLASS = {
    [STUDIES_CARD]: "tile-studies",
    [ACCESS_CARD]: "tile-access",
    [GEO_CARD]: "tile-geo",
    [METRICS_CARD]: "tile-metrics",
    "Model-based": "tile-model",
    [FUNDERS_CARD]: "tile-funders"
  };
  const OVERVIEW_TILE_COPY = {
    "Model-based": { sub: "Results estimated with a computer model rather than measured in patients" }
  };
  const PLACEHOLDER_PCT = "XX%";
  // The web data has no review-type field. Counts are from the team export
  // (hee_analysis_master_v2.csv `review_type`, 2026-10-12): an automated
  // title-and-abstract screen of the included studies. Update with the export.
  const REVIEW_COUNTS = { systematic: 1856, other: 797 };
  // paragraphs is a getter: it is read when the help opens, after the data
  // has loaded (db is still null while this block runs).
  const REVIEW_HELP = {
    title: "How are reviews counted?",
    get paragraphs() {
      const reviewOnly = (db && db.dict.meta.review_only) || 1986;
      return [
      "Reviews bring together the results of earlier studies. A systematic review searches for and appraises " +
      "studies using set, reported methods; other reviews (narrative, scoping or rapid reviews, or reviews that " +
      "do not describe themselves as systematic) are counted separately.",
      "These counts come from an automated screen of each study's title and abstract, so they are provisional. " +
      "Some reviews also include the authors' own evaluation. The selection diagram uses the same " +
      "current classification: 1,856 systematic and 796 non-systematic reviews.",
      "Charts of evaluation type (cost-benefit, cost-consequence, cost-effectiveness, cost-utility) do not count " +
      "the " + fmtNum(reviewOnly) + " reviews that report no evaluation of their own: they appear as a separate " +
      "“Review (no evaluation type)” group, and type percentages leave them out. Reviews that also report " +
      "the authors' own evaluation keep its type."
      ];
    }
  };

  const TILE_ACTIONS = {
    [STUDIES_CARD]: () => openModal("paper01.webp"),
    [ACCESS_CARD]: () => openOverviewTheme("Authorship & access"),
    [GEO_CARD]: () => openOverviewTheme("Geography"),
    [METRICS_CARD]: () => openOverviewTheme("Methods & metrics"),
    "Model-based": () => openOverviewTheme("Methods & metrics"),
    [FUNDERS_CARD]: () => openOverviewTheme("Research funding")
  };

  function countLevel(col, label) {
    const code = db.codeOf[col] ? db.codeOf[col].get(label) : db.levels[col].indexOf(label);
    let count = 0;
    for (const value of db.studies[col]) if (value === code) count++;
    return count;
  }

  function fmtPct(value) {
    return value == null ? PLACEHOLDER_PCT : value.toFixed(1) + "%";
  }

  function placeholderize(node, text) {
    node.textContent = text;
    if (text === PLACEHOLDER_PCT) {
      node.classList.add("tile-placeholder");
      node.title = "Not yet available";
    }
  }

  function publicationAccessCard() {
    const box = el("div", "value-box publication-access-card");
    const title = el("div", "value-box-title");
    title.textContent = "Publication access";
    const openCount = countLevel("oa_label", "Open access");
    const knownCount = openCount + countLevel("oa_label", "Not open");
    const totalCount = db.studies.id.length;
    const linkCount = publicationAccessCounts(db.studies);
    const metrics = el("div", "publication-access-metrics");

    for (const [label, valueText, note] of [
      ["DOI or URL available", fmtPct(totalCount && linkCount != null ? 100 * linkCount / totalCount : null),
        "Of all studies"],
      ["Available open access", fmtPct(knownCount ? 100 * openCount / knownCount : null),
        "Of " + fmtNum(knownCount) + " studies with a known open-access status"]
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
        help.addEventListener("click", event => {
          event.stopPropagation();
          $("oa-help-modal").classList.add("open");
        });
        help.addEventListener("keydown", event => event.stopPropagation());
        metricLabel.appendChild(help);
      }
      const value = el("strong");
      placeholderize(value, valueText);
      const metricNote = el("small");
      metricNote.textContent = note;
      metric.append(metricLabel, value, metricNote);
      metrics.appendChild(metric);
    }
    box.append(title, metrics);
    return box;
  }

  // Headline card: study count and years, with journals and reviews beneath.
  function studiesCard(tileByLabel) {
    const box = el("div", "value-box studies-overview-card");
    const title = el("div", "value-box-title");
    title.textContent = "Studies captured in the map";
    const head = el("div", "studies-overview-head");
    const value = el("span", "studies-overview-value");
    value.textContent = fmtNum(db.nStudies);
    const yearsTile = tileByLabel.get("Years covered");
    const years = el("strong");
    years.textContent = yearsTile ? yearsTile.value : db.years[0] + "–" + db.years[1];
    const text = el("span", "studies-overview-text");
    text.append("studies published ", years);
    head.append(value, text);

    const stats = el("div", "studies-overview-stats");
    const journalsTile = tileByLabel.get("Journals");
    const nReviews = REVIEW_COUNTS.systematic + REVIEW_COUNTS.other;
    for (const [label, valueText, note, help] of [
      ["Journals", journalsTile ? journalsTile.value : "—",
        "Publishing the studies, among those with journal details available"],
      ["Reviews", fmtNum(nReviews),
        fmtNum(REVIEW_COUNTS.systematic) + " systematic · " + fmtNum(REVIEW_COUNTS.other) +
        " other reviews of earlier studies", REVIEW_HELP]
    ]) {
      const stat = el("div", "studies-overview-stat");
      const statLabel = el("div", "studies-overview-label");
      statLabel.textContent = label;
      if (help) statLabel.appendChild(cardHelpButton(help));
      const row = el("div", "studies-overview-row");
      const statValue = el("strong");
      statValue.textContent = valueText;
      const statNote = el("span");
      statNote.textContent = note;
      row.append(statValue, statNote);
      stat.append(statLabel, row);
      stats.appendChild(stat);
    }
    box.append(title, head, stats);
    return box;
  }

  // Geography card: countries and geographic scope, studies by income group
  // (circles, area = studies) and by WHO region (lollipops). A multi-country
  // study counts once in each income group and region it examines.
  function geographyCard() {
    const box = el("div", "value-box geo-overview-card");
    const title = el("div", "value-box-title");
    title.textContent = "Geographic coverage of studies";
    const cols = el("div", "geo-overview-cols");

    const subhead = text => {
      const h = el("div", "geo-overview-subhead");
      h.textContent = text;
      return h;
    };

    // Column 1: countries named, then single / multi / none scope bar.
    const colCountries = el("div", "geo-overview-col");
    const countryHead = el("div", "studies-overview-head");
    const nCountries = el("span", "studies-overview-value");
    nCountries.textContent = fmtNum(db.countries.filter(r => r.studies > 0).length);
    const countryText = el("span", "studies-overview-text");
    countryText.textContent = "countries named by at least one study";
    countryHead.append(nCountries, countryText);
    const countryNote = el("div", "geo-overview-note");
    countryNote.textContent = "Of " + fmtNum(db.countries.length) +
      " countries with disease-burden and health-spending data";

    const total = Math.max(1, db.nStudies);
    const scopes = [
      ["Single country", countLevel("geo_scope", "Single country"), "geo-scope-single"],
      ["Multi-country or regional/global",
        countLevel("geo_scope", "Multi-country") + countLevel("geo_scope", "Region/global"), "geo-scope-other"],
      ["No country stated", countLevel("geo_scope", "No country stated"), "geo-scope-none"]
    ];
    // Shown shares in tenths of a percent, by largest remainder so they total exactly 100.0%.
    const tenths = scopes.map(([, n]) => 1000 * n / total);
    const shown = tenths.map(Math.floor);
    const order = tenths.map((x, i) => i).sort((a, b) => (tenths[b] - shown[b]) - (tenths[a] - shown[a]));
    for (const i of order.slice(0, 1000 - shown.reduce((a, b) => a + b, 0))) shown[i] += 1;
    const bar = el("div", "geo-scope-bar");
    const legend = el("div", "geo-scope-legend");
    scopes.forEach(([label, n, cls], i) => {
      const pct = 100 * n / total;
      const shownPct = (shown[i] / 10).toFixed(1) + "%";
      const seg = el("div", "geo-scope-segment " + cls);
      seg.style.width = pct + "%";
      seg.title = label + ": " + shownPct;
      bar.appendChild(seg);
      const item = el("div", "geo-scope-legend-row");
      const swatch = el("span", "geo-scope-swatch " + cls);
      const name = el("span");
      name.textContent = label;
      const value = el("strong");
      value.textContent = shownPct;
      item.append(swatch, name, value);
      legend.appendChild(item);
    });
    colCountries.append(subhead("Countries"), countryHead, countryNote,
      subhead("Geographic scope"), bar, legend);

    // Unique studies per income group (at publication year) and WHO region.
    const incSets = new Map(), regSets = new Map();
    const add = (map, key, s) => {
      if (key == null) return;
      let set = map.get(key);
      if (!set) { set = new Set(); map.set(key, set); }
      set.add(s);
    };
    for (let i = 0; i < db.geo.s.length; i++) {
      const s = db.geo.s[i], c = db.geo.c[i];
      add(incSets, db.incomeAt(c, db.geo.y[i]), s);
      add(regSets, db.regionOf[c], s);
    }

    // Column 2: income circles, low to high.
    const colIncome = el("div", "geo-overview-col");
    const circles = el("div", "geo-income-circles");
    const incCounts = db.incLv.map(lv => [lv, incSets.has(lv) ? incSets.get(lv).size : 0]);
    const maxInc = Math.max(1, ...incCounts.map(([, n]) => n));
    const shades = ["#cfe8dc", "#93cdb3", "#4fa889", "#1f7a5c"];
    incCounts.forEach(([lv, n], i) => {
      const item = el("div", "geo-income-item");
      const count = el("strong");
      count.textContent = fmtNum(n);
      const dot = el("span", "geo-income-dot");
      const d = Math.max(8, 104 * Math.sqrt(n / maxInc));
      dot.style.width = dot.style.height = d + "px";
      dot.style.background = shades[i] || shades[shades.length - 1];
      const name = el("span", "geo-income-name");
      name.textContent = lv.replace(/ income$/, "");
      item.title = lv + ": " + fmtNum(n) + " studies";
      item.append(count, dot, name);
      circles.appendChild(item);
    });
    colIncome.append(subhead("By income group of the country studied"), circles);

    // Column 3: WHO regions, most studied first.
    const colRegion = el("div", "geo-overview-col");
    const regions = el("div", "geo-region-rows");
    const regCounts = [...regSets].map(([r, set]) => [r, set.size]).sort((a, b) => b[1] - a[1]);
    const maxReg = Math.max(1, ...regCounts.map(([, n]) => n));
    for (const [r, n] of regCounts) {
      const row = el("div", "geo-region-row");
      const name = el("span", "geo-region-name");
      name.textContent = r.replace(/^Region of the /, "").replace(/ Region$/, "");
      const track = el("div", "geo-region-track");
      const stem = el("span", "geo-region-stem");
      stem.style.width = (100 * n / maxReg) + "%";
      track.appendChild(stem);
      const value = el("strong");
      value.textContent = fmtNum(n);
      row.title = r + ": " + fmtNum(n) + " studies";
      row.append(name, track, value);
      regions.appendChild(row);
    }
    colRegion.append(subhead("By WHO region"), regions);

    cols.append(colCountries, colIncome, colRegion);
    const note = el("div", "metrics-overview-note");
    note.textContent = "A multi-country study counts in every income group and region of the countries it " +
      "examines. Income groups are World Bank groups in the publication year; circle area = studies.";
    box.append(title, cols, note);
    return box;
  }

  // "?" button that opens the shared card-help dialog. `help` is
  // { title, paragraphs }; the card itself is clickable, so stop the click here.
  function cardHelpButton(help) {
    const button = el("button", "metric-help-button");
    button.type = "button";
    button.textContent = "?";
    button.title = help.title;
    button.setAttribute("aria-label", help.title);
    button.addEventListener("click", event => {
      event.stopPropagation();
      $("card-help-title").textContent = help.title;
      const body = $("card-help-body");
      body.textContent = "";
      for (const text of help.paragraphs) {
        const p = el("p");
        p.textContent = text;
        body.appendChild(p);
      }
      $("card-help-modal").classList.add("open");
    });
    button.addEventListener("keydown", event => event.stopPropagation());
    return button;
  }

  // rows: [label, pct, help?]; noteHelp: optional help for the note line.
  function barRowsCard(cls, titleText, rows, noteText, noteHelp) {
    const box = el("div", "value-box metrics-overview-card " + cls);
    const title = el("div", "value-box-title");
    title.textContent = titleText;
    const chart = el("div", "metrics-overview-chart");
    for (const [label, pct, help] of rows) {
      const row = el("div", "metrics-overview-row");
      const labelEl = el("span", "metrics-overview-label");
      labelEl.textContent = label;
      if (help) labelEl.appendChild(cardHelpButton(help));
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
    if (noteHelp) note.appendChild(cardHelpButton(noteHelp));
    box.append(title, chart, note);
    return box;
  }

  // The web data flags QALY use only. DALY and other-outcome counts are from the
  // v2 team export (hee_outcomes_long.csv `family`, included studies,
  // 2026-10-11): studies with at least one outcome in the DALYs family, and with
  // at least one outcome in any family other than QALYs or DALYs. Update with
  // the export; if the study count changes, those two rows show "XX%".
  const OUTCOME_STUDIES = 41610;
  const DALY_STUDIES = 1434;
  const OTHER_OUTCOME_STUDIES = 36288;

  function outcomeMetricsCard() {
    const n = Math.max(1, db.nStudies);
    const fromExport = count => db.nStudies === OUTCOME_STUDIES ? 100 * count / n : null;
    return barRowsCard("", "Outcome metrics used in studies",
      [["QALYs", 100 * countLevel("qaly_label", "Uses QALY") / n, {
         title: "What is a QALY?",
         paragraphs: ["A quality-adjusted life year: one year of life in full health. Years lived in poorer " +
           "health count as less than one. Studies use QALYs to compare health gains across diseases."]
       }],
       ["DALYs", fromExport(DALY_STUDIES), {
         title: "What is a DALY?",
         paragraphs: ["A disability-adjusted life year: one year of healthy life lost to illness, disability " +
           "or early death. Studies report DALYs averted; the measure is common in lower-income settings."]
       }],
       ["Other metrics", fromExport(OTHER_OUTCOME_STUDIES), {
         title: "What are other metrics?",
         paragraphs: [
           "Any health outcome a study reports other than QALYs (quality-adjusted life years) or DALYs (disability-adjusted life years).",
           "The most common are survival or deaths, side effects and complications, symptom and clinical scores, quality of life, " +
           "major clinical events such as heart attacks, life-years gained, cases detected or prevented, disease progression, " +
           "and test results such as blood pressure or blood sugar."
         ]
       }]],
      "Share of all studies. A study may report more than one metric.", {
        title: "Why do the percentages add up to more than 100%?",
        paragraphs: [
          "Each bar is the share of all studies that report that kind of outcome.",
          "Many studies report more than one kind, for example QALYs and survival, so they count in more than one bar. " +
          "The bars therefore add up to more than 100%."
        ]
      });
  }

  // Overview card: the four full-evaluation types, as shares of studies with a type
  // (reviews reporting no evaluation of their own are left out). Shown in place of
  // outcomeMetricsCard. Shares are rounded so they total exactly 100%.
  const EVAL_TYPES = [
    ["Cost-utility", "Cost-utility (CUA)", "Health gains measured in quality-adjusted or disability-adjusted life " +
      "years (QALYs or DALYs). Cost-effectiveness studies that report a QALY or DALY are classed here."],
    ["Cost-effectiveness", "Cost-effectiveness (CEA)", "Health gains measured in natural units, such as " +
      "life-years gained, cases prevented or cases detected."],
    ["Cost-consequence", "Cost-consequence (CCA)", "Costs and a range of outcomes reported side by side, " +
      "without combining them into a single measure."],
    ["Cost-benefit", "Cost-benefit (CBA)", "Health gains valued in money, so costs and benefits are compared " +
      "in the same unit."]
  ];

  function evalTypesCard() {
    const counts = EVAL_TYPES.map(([level]) => countLevel("econ_eval_type", level));
    const typed = Math.max(1, counts.reduce((a, b) => a + b, 0));
    const tenths = counts.map(n => 1000 * n / typed);
    const shown = tenths.map(Math.floor);
    const order = tenths.map((x, i) => i).sort((a, b) => (tenths[b] - shown[b]) - (tenths[a] - shown[a]));
    for (const i of order.slice(0, 1000 - shown.reduce((a, b) => a + b, 0))) shown[i] += 1;
    const rows = EVAL_TYPES.map(([, label, text], i) => [label, shown[i] / 10, {
      title: "What is a " + label.replace(/ \(.*/, "").toLowerCase() + " analysis?", paragraphs: [text] }]);
    rows.sort((a, b) => b[1] - a[1]);
    const reviews = countLevel("econ_eval_type", "Review (no evaluation type)");
    return barRowsCard("", "Types of economic evaluation", rows,
      "Share of the " + fmtNum(typed) + " studies with an evaluation type; " + fmtNum(reviews) +
      " reviews that report no evaluation of their own are left out.", {
        title: "How are the types counted?",
        paragraphs: [
          "Each study has one evaluation type, so the four bars add up to 100%.",
          "Cost-effectiveness studies that report a QALY or DALY are classed as cost-utility. Reviews that report no " +
          "evaluation of their own have no type and are left out; reviews that also report the authors' own " +
          "evaluation keep its type."
        ]
      });
  }

  // The web data has no funder field. Counts are from the v2 team export
  // (hee_analysis_master_v2.csv `funders`, 2026-10-11): included studies naming at
  // least one funder ("None"/"self-funded" entries dropped), and how many name
  // a funder of each type. Types follow OECD Frascati sectors: university
  // hospitals sit with universities; other public hospitals and health services
  // with government. A study can name funders of several types, so the shares
  // overlap. Update with the export.
  const FUNDER_STUDIES = 11150;
  const FUNDER_TYPE_COUNTS = [
    ["Government and multilateral", 6895],
    ["Academic and non-profit", 3506],
    ["Private companies", 2652],
    ["Unclassified", 292]
  ];

  function fundersCard() {
    return barRowsCard("funding-overview-card", "Who funds the evidence?",
      FUNDER_TYPE_COUNTS.map(([label, n]) => [label, 100 * n / FUNDER_STUDIES]),
      "Among " + fmtNum(FUNDER_STUDIES) + " studies reporting a funder. Categories may overlap.", {
        title: "Why do the percentages add up to more than 100%?",
        paragraphs: [
          "Each bar is the share of the " + fmtNum(FUNDER_STUDIES) + " studies that report at least one funder of that type.",
          "Many studies have more than one funder, for example a government grant and a company, so they count in more than one bar. " +
          "The bars therefore add up to more than 100%."
        ]
      });
  }

  function makeOverviewCardInteractive(box, key) {
    const action = TILE_ACTIONS[key];
    if (!action) return;
    const label = box.querySelector(".value-box-title").textContent;
    box.classList.add("overview-nav-card");
    box.tabIndex = 0;
    const opensSelection = key === STUDIES_CARD;
    box.setAttribute("role", opensSelection ? "button" : "link");
    box.setAttribute("aria-label", label + (opensSelection
      ? ": open study selection figure" : ": open related analysis"));
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
    // Plain-language hero (replaces content.json's, which names old tab labels).
    const HERO = [
      { text: "This map brings together " },
      { text: fmtNum(db.nStudies), strong: true },
      { text: " studies published 2010–2026 that weigh the costs of health care against its health " +
        "effects, including reviews of earlier studies. Use " },
      { text: "Thematic analysis", em: true }, { text: " for the main findings, " },
      { text: "Explorer", em: true }, { text: " to filter and compare studies, and " },
      { text: "Countries", em: true }, { text: " to see one country's evidence." }
    ];
    for (const seg of HERO) {
      const node = document.createElement(seg.strong ? "strong" : seg.em ? "em" : "span");
      node.textContent = seg.text;
      hero.appendChild(node);
    }

    // Simple values come from content.json; composite cards are calculated
    // from study data where available and explicitly marked where unavailable.
    const wrap = $("ov-tiles");
    wrap.textContent = "";
    const tileByLabel = new Map(db.content.glance_tiles.map(tile => [tile.label, tile]));
    for (const key of OVERVIEW_TILE_ORDER) {
      let box;
      if (key === STUDIES_CARD) box = studiesCard(tileByLabel);
      else if (key === ACCESS_CARD) box = publicationAccessCard();
      else if (key === GEO_CARD) box = geographyCard();
      else if (key === METRICS_CARD) box = evalTypesCard();
      else if (key === FUNDERS_CARD) box = fundersCard();
      else {
        const tile = tileByLabel.get(key);
        if (!tile) continue;
        const copy = OVERVIEW_TILE_COPY[key] || {};
        box = el("div", "value-box");
        const title = el("div", "value-box-title");
        title.textContent = copy.label || tile.label;
        const value = el("div", "value-box-value");
        value.textContent = tile.value;
        box.append(title, value);
        const subText = "sub" in copy ? copy.sub : tile.sub;
        if (subText != null) {
          const sub = el("div", "value-box-sub");
          sub.textContent = subText;
          box.appendChild(sub);
        }
      }
      if (TILE_CLASS[key]) box.classList.add(TILE_CLASS[key]);
      makeOverviewCardInteractive(box, key);
      wrap.appendChild(box);
    }

    // Overview figure cards: header = the figure's content.json title, with a
    // "More on …" link to the Thematic analysis section that holds it.
    const heroes = [
      {
        file: "fig_dotmap.svg",
        alt: "World map of economic evidence by country and income group",
        takeaway: "Most economic evidence is about high-income countries."
      },
      { file: "fig_research_burden_ratio.svg", alt: "Strip plot of country research-to-burden ratios by income group, with group medians and a proportional reference line" },
      { file: "fig_disease_circular.webp", alt: "Line of sight: disease groups studied in health economic evidence" },
      { file: "fig_intervention_mix.webp", alt: "What gets evaluated: intervention mix by income" },
      { file: "fig_funder_funders.svg", alt: "Top recorded funders by study count and setting, with equal styling for all funders" }
    ];
    const hw = $("ov-hero-imgs");
    hw.textContent = "";
    heroes.forEach(h => {
      const f = FIG_INDEX[h.file];
      const card = el("div", "card overview-analysis-card");
      if (h.takeaway) card.classList.add("overview-featured-card");
      const head = el("div", "card-header overview-card-head");
      const name = el("span");
      name.textContent = f ? f.title : h.alt;
      head.appendChild(name);
      if (h.takeaway) {
        const link = el("button", "card-header-link overview-explore-link");
        link.type = "button";
        link.textContent = "Explore geographic evidence \u2192";
        link.addEventListener("click", () => openModal(h.file));
        head.appendChild(link);
      } else if (f && f.sectionTitle) {
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
      img.src = figSrc(h.file);
      img.alt = h.alt;
      img.loading = "lazy";
      btn.appendChild(img);
      btn.addEventListener("click", () => openModal(h.file));
      body.appendChild(btn);
      card.appendChild(head);
      if (h.takeaway) {
        const takeaway = el("h3", "overview-featured-takeaway");
        takeaway.textContent = h.takeaway;
        card.appendChild(takeaway);
      }
      card.appendChild(body);
      if (f) {
        const notes = el("div", "fig-caption overview-figure-notes");
        renderFigureNotes(notes, f);
        card.appendChild(notes);
      }
      hw.appendChild(card);
    });
    const wellcomeCard = el("div", "card overview-wellcome-card");
    const wellcomeBadge = el("span", "overview-wellcome-badge");
    wellcomeBadge.textContent = "Funder-specific view";
    const wellcomeTitle = el("h3");
    wellcomeTitle.textContent = "Wellcome priority themes";
    const wellcomeCopy = el("p");
    wellcomeCopy.textContent = "Explore Infectious Diseases, Mental Health and Climate & Health, " +
      "including top funders within each theme and Wellcome-funded studies. Theme definitions " +
      "and funding coverage are shown in the separate view.";
    const wellcomeLink = el("button", "card-header-link overview-explore-link");
    wellcomeLink.type = "button";
    wellcomeLink.textContent = "Explore Wellcome priority themes \u2192";
    wellcomeLink.addEventListener("click", () => openOverviewTheme("Wellcome priority themes"));
    wellcomeCard.append(wellcomeBadge, wellcomeTitle, wellcomeCopy, wellcomeLink);
    hw.appendChild(wellcomeCard);
  }

  // Overview publication trend for the unfiltered corpus, with a
  // "Per year | Cumulative" switch.
  let overviewTrendMode = "annual";

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
    const cum = [];
    running = 0;
    for (const n of annual) cum.push(running += n);
    const total = cum[cum.length - 1];
    let halfIdx = 0;
    for (let i = 0; i < years.length; i++) {
      if (total - (i > 0 ? cum[i - 1] : 0) >= total / 2) halfIdx = i;
    }
    const earlyN = Math.min(3, annual.length);
    const earlyRate = annual.slice(0, earlyN).reduce((a, b) => a + b, 0) / earlyN;
    const fullIdx = years.map((year, i) => i).filter(i => years[i] !== 2026);
    const lastFull = fullIdx[fullIdx.length - 1];
    const ref = fullIdx.map(i => earlyRate * (i + 1));
    const growth = total / Math.max(1, cum[0]);
    const vsRef = cum[lastFull] / ref[ref.length - 1];
    const earlySpan = years[0] + "–" + String(years[earlyN - 1]).slice(2);
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
      hovertemplate: (cumulative ? "By %{x}" : "%{x}") + ": %{y:,} studies<extra></extra>"
    }];
    const partialIndex = years.indexOf(2026);
    const narrowTrend = $("ov-trend").clientWidth < 520;
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
        ax: narrowTrend ? -16 : 22, ay: narrowTrend ? -36 : 0,
        xanchor: narrowTrend ? "right" : "left", align: narrowTrend ? "right" : "left",
        font: { color: "#6f5420", size: 12.5 },
        bgcolor: "#fbf5e6", bordercolor: "#dcc48f", borderwidth: 1, borderpad: 5
      });
    }
    const chips = $("ov-trend-chips");
    chips.textContent = "";
    chips.hidden = !cumulative;
    const shapes = [];
    if (cumulative) {
      for (const [value, text] of [
        [growth.toFixed(1) + "×", "growth in cumulative studies since " + years[0]],
        [String(years[halfIdx]), "half of all " + fmtNum(total) + " studies were published in " +
          years[halfIdx] + " or later"],
        [vsRef.toFixed(1) + "×", "more studies by " + years[lastFull] +
          " than if output had stayed at its " + earlySpan + " rate"]
      ]) {
        const chip = el("div", "trend-chip");
        const valueNode = el("strong");
        valueNode.textContent = value;
        const textNode = el("span");
        textNode.textContent = text;
        chip.append(valueNode, textNode);
        chips.appendChild(chip);
      }
      traces.unshift({
        x: fullIdx.map(i => years[i]), y: ref,
        mode: "lines", type: "scatter", showlegend: false,
        line: { color: "#8a93a0", width: 1.6, dash: "dash" },
        hovertemplate: "If output had stayed at the " + earlySpan + " rate: %{y:,.0f}<extra></extra>"
      });
      const refLabelIdx = Math.round(ref.length * 0.62);
      annotations.push({
        x: years[fullIdx[refLabelIdx]], y: ref[refLabelIdx], xref: "x", yref: "y",
        text: "if output had stayed at its " + earlySpan + " rate",
        showarrow: false, yanchor: "bottom", yshift: 4, font: { color: "#6b7280", size: 11.5 }
      }, {
        x: years[halfIdx], y: cum[halfIdx], xref: "x", yref: "y",
        text: "<b>Half of all studies</b><br>published " + years[halfIdx] + " or later",
        showarrow: true, arrowhead: 0, arrowwidth: 1.2, arrowcolor: "#1f5fa8",
        ax: -95, ay: -38, align: "left",
        font: { color: "#1a4e8a", size: 12 },
        bgcolor: "#f0f6fc", bordercolor: "#b9d0ea", borderwidth: 1, borderpad: 5
      });
      shapes.push({
        type: "line", xref: "x", yref: "y", x0: years[halfIdx], x1: years[halfIdx],
        y0: 0, y1: cum[halfIdx], line: { color: "#1f5fa8", width: 1, dash: "dot" }
      });
      $("ov-trend-note").textContent = "Running total of studies by publication year. Dashed line: " +
        "where the total would be if yearly output had stayed at its " + earlySpan + " average. " +
        "2026 is a partial year (searches were run in mid-2026).";
    } else {
      $("ov-trend-note").textContent = "Annual studies by publication year. 2026 is a partial year: " +
        "the literature searches were run in mid-2026, so only studies published before then are included.";
    }
    window.Plotly.react("ov-trend", traces, {
      font: BASE_FONT,
      margin: { t: 10, b: 40, l: narrowTrend ? 48 : 60,
               r: partialIndex >= 0 && !narrowTrend ? 175 : 20 },
      annotations,
      shapes,
      xaxis: { showgrid: false, range: [years[0] - 0.4, years[years.length - 1] + 0.4], dtick: 2 },
      yaxis: { title: cumulative ? "cumulative studies" : "studies", tickformat: ",d",
               gridcolor: "#eeebe3", zeroline: false, rangemode: "tozero" },
      plot_bgcolor: "rgba(0,0,0,0)",
      paper_bgcolor: "rgba(0,0,0,0)"
    }, PLOTLY_CFG);
  }

  function thematicCard(sec, onClick) {
    const card = el("button", "thematic-card");
    card.type = "button";
    const img = el("img", "thematic-card-image");
    img.src = figSrc((sec.figs.find(f => !f.html) || sec.figs[0]).file);
    img.alt = "";
    img.loading = "lazy";
    const body = el("div", "thematic-card-body");
    const title = el("h2", "thematic-card-title");
    title.textContent = sec.title;
    const count = el("div", "thematic-card-count");
    count.textContent = (sec.groups ? sec.groups.length + " topics · " : "") + sec.figs.length + " figures";
    const description = el("p", "thematic-card-description");
    const fullBlurb = sec.blurb.replace(/\s+/g, " ").trim();
    description.textContent = fullBlurb.length > 155 ? fullBlurb.slice(0, 152) + "..." : fullBlurb;
    const arrow = el("span", "thematic-card-arrow");
    arrow.textContent = "→";
    arrow.setAttribute("aria-hidden", "true");
    body.append(title, count, description, arrow);
    card.append(img, body);
    card.addEventListener("click", onClick);
    return card;
  }

  // Thematic analysis index: one card per content.json gallery section, plus
  // the matching entries in the navbar dropdown.
  function renderGalleryIndex() {
    const idx = $("gal-section-index");
    const menu = $("thematic-menu");
    idx.textContent = "";
    menu.textContent = "";
    GALLERY.forEach((sec, i) => {
      idx.appendChild(thematicCard(sec, () => showSection(i)));

      const item = el("button", "nav-theme-link");
      item.type = "button";
      item.setAttribute("role", "menuitem");
      item.textContent = sec.title;
      item.addEventListener("click", () => {
        closeThematicMenu();
        switchTab("gallery");
        showSection(i);
      });
      menu.appendChild(item);
    });
  }

  // Where the section's back link leads: null = theme index, "overview" =
  // back to the Overview.
  let sectionReturnTo = null;
  let sectionGroup = null;
  let sectionParentIndex = null;

  // Figures drawn at least this many pixels wide span two grid columns.
  const WIDE_FIGURE_MIN_PX = 2300;

  // Plain text with any https:// URLs turned into links (text nodes only, never innerHTML).
  function setTextWithLinks(node, text) {
    node.textContent = "";
    for (const part of text.split(/(https:\/\/[^\s)]+)/)) {
      if (!part.startsWith("https://")) {
        node.appendChild(document.createTextNode(part));
        continue;
      }
      const a = el("a");
      a.href = part;
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = part;
      node.appendChild(a);
    }
  }

  function showSection(i, returnTo = null, groupIndex = null) {
    const sec = GALLERY[i];
    const group = groupIndex == null ? null : sec.groups[groupIndex];
    const view = group || sec;
    sectionReturnTo = returnTo;
    sectionGroup = groupIndex;
    sectionParentIndex = group ? i : null;
    $("gal-back").textContent = group ? "← Back to " + sec.title :
      returnTo === "overview" ? "← Back to Overview" : "← All themes";
    $("gal-index").style.display = "none";
    $("gal-section").style.display = "block";
    $("gal-sec-title").textContent = view.title;
    setTextWithLinks($("gal-sec-blurb"), view.blurb.replace(/\s+/g, " ").trim());
    const topics = $("gal-subsections");
    topics.textContent = "";
    topics.hidden = !sec.groups || !!group;
    const grid = $("gal-sec-grid");
    grid.textContent = "";
    grid.hidden = !!sec.groups && !group;
    if (sec.groups && !group) {
      sec.groups.forEach((topic, j) => topics.appendChild(thematicCard(topic,
        () => showSection(i, returnTo, j))));
      window.scrollTo(0, 0);
      return;
    }
    const figs = view.figs.filter(f => !THUMBNAIL_ONLY_FIGURES.has(f.file));
    grid.classList.toggle("fig-grid-single", figs.length === 1);
    for (const f of figs) {
      if (f.html) {
        grid.appendChild(htmlFigureCard(f));
        continue;
      }
      const card = el("div", "fig-card");
      const img = el("img");
      img.src = figSrc(f.file);
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
      renderFigureNotes(fc, f);
      body.appendChild(ft);
      body.appendChild(fc);
      card.appendChild(body);
      grid.appendChild(card);
    }
    window.scrollTo(0, 0);
  }

  // Card for an interactive HTML figure: the page in an iframe sized to its
  // content (same origin, so its height can be read), plus a full-page link.
  function htmlFigureCard(f) {
    const card = el("div", "fig-card fig-card-html");
    const frame = el("iframe");
    frame.src = "figures/" + f.file + "?v=" + BUILD;
    frame.title = f.title;
    frame.loading = "lazy";
    const fit = () => {
      const doc = frame.contentDocument;
      if (doc && doc.documentElement) frame.style.height = doc.documentElement.scrollHeight + "px";
    };
    frame.addEventListener("load", () => {
      fit();
      const doc = frame.contentDocument;
      if (doc && doc.body && window.ResizeObserver) new ResizeObserver(fit).observe(doc.body);
    });
    card.appendChild(frame);
    const body = el("div", "fig-body");
    const ft = el("div", "fig-title");
    ft.textContent = f.title;
    const fc = el("div", "fig-caption");
    renderFigureNotes(fc, f);
    const open = el("a", "fig-open-link");
    open.href = figSrc(f.file);
    open.target = "_blank";
    open.rel = "noopener";
    open.textContent = "Open full page ↗";
    body.append(ft, fc, open);
    card.appendChild(body);
    return card;
  }

  function hideSection() {
    $("gal-section").style.display = "none";
    $("gal-index").style.display = "block";
    sectionReturnTo = null;
    sectionGroup = null;
    sectionParentIndex = null;
    $("gal-back").innerHTML = "&larr; All themes";
  }

  function goBackFromSection() {
    if (sectionGroup != null) {
      showSection(sectionParentIndex, sectionReturnTo);
      return;
    }
    const toOverview = sectionReturnTo === "overview";
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

  function makeMultiSelect(id, options, placeholder, key, labelOf) {
    const sel = $(id);
    for (const o of options) {
      const opt = document.createElement("option");
      opt.value = o;
      opt.textContent = labelOf ? labelOf(o) : o;
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

  // Evaluation type: the four types plus, when the data has review_label,
  // "Systematic review" and "Other review". Choosing a review removes the four
  // types (reviews are not counted as a type); clearing it brings them back.
  function makeEvalTypeSelect() {
    const types = db.levels.econ_eval_type.filter(t => t !== REVIEW_TYPE);
    const hasReviews = !!db.codeOf.review_label;
    const reviews = hasReviews ? REVIEW_CHOICES : [];
    const count = new Map();
    const col = db.studies.econ_eval_type;
    for (let s = 0; s < db.nStudies; s++) {
      const t = db.levels.econ_eval_type[col[s]];
      count.set(t, (count.get(t) || 0) + 1);
      if (hasReviews) {
        const r = db.levels.review_label[db.studies.review_label[s]];
        count.set(r, (count.get(r) || 0) + 1);
      }
    }
    const option = (v, ord) => ({ value: v, text: v + " (" + fmtNum(count.get(v) || 0) + ")", ord });
    const typeOptions = types.map((t, i) => option(t, i));
    const ts = state.ts.evaltype = new window.TomSelect($("x-evaltype"), {
      plugins: ["remove_button"],
      placeholder: "All types",
      allowEmptyOption: false,
      options: typeOptions.concat(reviews.map((r, i) => option(r, types.length + i))),
      sortField: [{ field: "ord" }],
      onChange: vals => {
        let sel = Array.isArray(vals) ? vals.slice() : (vals ? [vals] : []);
        const reviewChosen = sel.some(v => REVIEW_CHOICES.includes(v));
        for (const o of typeOptions) {
          if (reviewChosen && ts.options[o.value]) ts.removeOption(o.value, true);
          else if (!reviewChosen && !ts.options[o.value]) ts.addOption(o);
        }
        if (reviewChosen) sel = sel.filter(v => REVIEW_CHOICES.includes(v));
        ts.refreshOptions(false);
        state.filt.evaltype = sel;
        refreshExplorer();
      }
    });
  }

  function setupExplorerControls() {
    const m = db.dict.meta;
    state.filt = {
      years: db.years.slice(),
      income: [], region: [], disease: [], evaltype: [], design: [], funder: [], language: [],
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
    makeEvalTypeSelect();
    makeMultiSelect("x-design", db.levels.design_basis, "All designs", "design");
    if (!db.funders.names.length) $("x-funder").closest(".control-group").hidden = true;
    const funderN = new Map(db.funders.names.map((nm, i) => [nm, db.funders.n[i]]));
    makeMultiSelect("x-funder", [ANY_FUNDER, ...db.funders.names], "All studies", "funder",
      nm => nm + " (" + fmtNum(nm === ANY_FUNDER ? db.funders.any.length : funderN.get(nm)) + ")");
    const lang = db.languages || { levels: [], n: [] };
    if (!lang.levels.length) $("x-language").closest(".control-group").hidden = true;
    const langN = new Map(lang.levels.map((l, i) => [l, lang.n[i]]));
    makeMultiSelect("x-language", lang.levels, "All languages", "language",
      l => l + " (" + fmtNum(langN.get(l)) + ")");

    makeRadios("x-model", "x_model", ["All", "Model-based", "Measured"]);
    makeRadios("x-qaly", "x_qaly", ["All", "Uses QALY", "No QALY"]);
    makeRadios("x-oa", "x_oa", ["All", "Open access", "Not open"]);

    const scope = $("x-scope");
    fillSelect(scope, ["All"].concat(db.levels.geo_scope));
    scope.addEventListener("change", () => {
      state.filt.scope = scope.value;
      refreshExplorer();
    });

    $("x-download").addEventListener("click", downloadFilteredStudies);
    $("x-reset").addEventListener("click", () => {
      slider.noUiSlider.set(db.years);
      for (const k of ["income", "region", "disease", "evaltype", "design", "funder", "language"]) state.ts[k].clear();
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
    fillSelect($("x-scatter-x"), [...REG.SCAT_X.keys()], [plainLabel("Total DALYs (GBD 2023)")]);
    fillSelect($("x-scatter-y"), [...REG.SCAT_Y.keys()], [plainLabel("Studies per 100k DALYs")]);

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

  // Explorer "Download filtered studies (CSV)": one row per study in view,
  // with its coded fields, every country and disease group it names, and its
  // title. Titles live in the per-country text shards, so only studies naming
  // a country have one; the shards needed are fetched on demand.
  async function downloadFilteredStudies() {
    const button = $("x-download");
    const status = $("x-download-status");
    const { studies, mask } = state.result;
    if (!studies.length) {
      status.textContent = "No studies match the current filters.";
      return;
    }
    button.disabled = true;
    status.textContent = "Preparing " + fmtNum(studies.length) + " studies…";
    try {
      const countriesOf = new Map();
      const g = db.geo;
      for (let i = 0; i < g.s.length; i++) {
        const s = g.s[i];
        if (!mask[s]) continue;
        if (!countriesOf.has(s)) countriesOf.set(s, []);
        countriesOf.get(s).push(Object.assign({ income_pub: db.incomeAt(g.c[i], g.y[i]) }, db.countries[g.c[i]]));
      }
      const fundersOf = new Map();
      for (let i = 0; i < db.funders.s.length; i++) {
        const s = db.funders.s[i];
        if (!mask[s]) continue;
        if (!fundersOf.has(s)) fundersOf.set(s, []);
        fundersOf.get(s).push(db.funders.names[db.funders.f[i]]);
      }
      const diseasesOf = new Map();
      const d = db.disease;
      for (let i = 0; i < d.s.length; i++) {
        const s = d.s[i];
        if (!mask[s]) continue;
        if (!diseasesOf.has(s)) diseasesOf.set(s, []);
        diseasesOf.get(s).push(db.disease_grps[d.g[i]]);
      }
      const isos = new Set(studies.map(firstIsoOf).filter(Boolean));
      status.textContent = "Loading study titles from " + fmtNum(isos.size) + " country files…";
      const shards = await Promise.all([...isos].map(loadDrill));
      const titleOf = new Map();
      for (const p of shards) {
        if (!p) continue;
        p.s.forEach((s, i) => { if (mask[s] && !titleOf.has(s)) titleOf.set(s, p.t[i]); });
      }

      const st = db.studies;
      const label = (col, s) => db.levels[col][st[col][s]] ?? "";
      const yesNo = v => v === 1 ? "Yes" : v === 0 ? "No" : "";
      const header = ["map_id", "year", "title", "countries", "income_groups", "income_groups_at_publication", "disease_groups", "funders", "publication_language",
        "evaluation_type", "design_basis", "approach", "qaly", "open_access", "geographic_scope",
        "topic_domain", "abstract_reports_icer", "abstract_reports_threshold",
        "record_id", "doi", "url", "url_source", "doi_source", "publication_link"];
      const rows = [header];
      for (const s of studies) {
        const cs = countriesOf.get(s) || [];
        rows.push([
          st.id[s], st.year[s], titleOf.get(s) || "",
          cs.map(c => c.country).join("; "),
          [...new Set(cs.map(c => c.income))].join("; "),
          [...new Set(cs.map(c => c.income_pub ?? "Not classified"))].join("; "),
          (diseasesOf.get(s) || []).join("; "),
          fundersOf.has(s) ? fundersOf.get(s).join("; ") : (db.fundedSet.has(s) ? "Other (fewer than 5 studies)" : ""),
          db.languages ? db.languages.levels[db.languages.code[s]] : "",
          label("econ_eval_type", s), label("design_basis", s), label("model_label", s),
          label("qaly_label", s), label("oa_label", s), label("geo_scope", s), label("topic_domain", s),
          yesNo(st.has_icer[s]), yesNo(st.has_threshold[s]),
          st.record_id?.[s] || "", st.doi?.[s] || "", st.url?.[s] || "",
          st.url_source?.[s] || "", st.doi_source?.[s] || "", publicationUrl(st, s) || ""
        ]);
      }
      const cell = v => {
        const t = String(v ?? "");
        return /[",\r\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
      };
      // UTF-8 BOM so Excel reads accented titles correctly.
      const csv = "﻿" + rows.map(r => r.map(cell).join(",")).join("\r\n") + "\r\n";
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      a.download = "hee_studies_" + fmtNum(studies.length).replace(/,/g, "") + "_" + db.dict.meta.built + ".csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      status.textContent = "Downloaded " + fmtNum(studies.length) + " studies. Titles are included for the " +
        fmtNum(titleOf.size) + " that name a country.";
    } catch (e) {
      status.textContent = "Download failed; please try again.";
    } finally {
      button.disabled = false;
    }
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
      } else if (v === "who_region") {
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
      // Header only: column names double as tableRows keys.
      th.textContent = c === "Studies" ? "Studies examining the country" : c;
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
    // Countries A–Z; the profile opens on the first one alphabetically.
    const sorted = db.countries.slice().sort((a, b) => a.country.localeCompare(b.country));
    state.country = sorted[0].iso3;
    for (const r of sorted) {
      const o = document.createElement("option");
      o.value = r.iso3;
      o.textContent = r.country;
      if (r.iso3 === state.country) o.selected = true;
      sel.appendChild(o);
    }
    new window.TomSelect(sel, {
      placeholder: "Pick a country…",
      // Tom Select lists only 50 options by default; show every country.
      maxOptions: null,
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
    const allOpt = document.createElement("option");
    allOpt.value = ALL_COUNTRIES;
    allOpt.textContent = "All countries";
    sel.appendChild(allOpt);
    for (const r of landscapeCountries(db)) {
      const o = document.createElement("option");
      o.value = r.iso3;
      o.textContent = r.country;
      sel.appendChild(o);
    }
    landSelect = new window.TomSelect(sel, {
      placeholder: "Pick a country…",
      // Tom Select lists only 50 options by default; show every country.
      maxOptions: null,
      // Render the list in <body> so card/tab overflow cannot clip it.
      dropdownParent: "body",
      onChange: val => { if (val) showCountryMix(val); }
    });
    if (landCrossIndex) landSelect.setValue(landCrossIndex.iso3, true);
  }

  function renderLandscape() {
    renderLandscapeScatter();
    // Open on all countries combined, a global baseline to compare each
    // country against, so the tab never opens empty (§2.6).
    showCountryMix(ALL_COUNTRIES);
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
        color: spreadPalette(colors, desc.length).reverse()
          .map((c, i) => desc[i].label === REVIEW_TYPE ? "#c5c2bb" : c),
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

  // Study texts live in per-country shards; for "All countries" each study is
  // read from the shard of the first country it names.
  let studyFirstIso = null;
  function firstIsoOf(s) {
    if (!studyFirstIso) {
      studyFirstIso = new Map();
      const g = db.geo;
      for (let i = 0; i < g.s.length; i++) {
        if (!studyFirstIso.has(g.s[i])) studyFirstIso.set(g.s[i], db.countries[g.c[i]].iso3);
      }
    }
    return studyFirstIso.get(s);
  }

  // Cap on "All countries" lists so a cell click never fetches every shard.
  const ALL_COUNTRIES_LIST_CAP = 100;

  async function openStudiesModal(iso3, diseaseLabel, evalLabel, indices) {
    const all = iso3 === ALL_COUNTRIES;
    const rec = all ? null : db.countries.find(r => r.iso3 === iso3);
    $("study-modal-title").textContent =
      (all ? "All countries" : rec ? rec.country : iso3) + " — " + diseaseLabel + " × " + evalLabel;
    const shown = all ? indices.slice(0, ALL_COUNTRIES_LIST_CAP) : indices;
    $("study-modal-count").textContent =
      fmtNum(indices.length) + (indices.length === 1 ? " study" : " studies") +
      (shown.length < indices.length
        ? " · showing the first " + fmtNum(shown.length) + "; pick a country to see all"
        : "");
    const list = $("study-modal-list");
    list.textContent = "";
    const loading = el("div", "study-item study-loading");
    loading.textContent = "Loading study texts…";
    list.appendChild(loading);
    $("study-modal").classList.add("open");

    let records;
    if (all) {
      const byIso = new Map();
      for (const s of shown) {
        const k = firstIsoOf(s);
        if (!byIso.has(k)) byIso.set(k, []);
        byIso.get(k).push(s);
      }
      const isos = [...byIso.keys()];
      await Promise.all(isos.map(loadDrill));
      const found = new Map();
      for (const k of isos) {
        for (const r of drillRecords(db, k, byIso.get(k))) found.set(r.s, r);
      }
      records = shown.map(s => found.get(s) ||
        { s, title: null, abstract: null, truncated: false, missing: true });
    } else {
      const payload = await loadDrill(iso3);
      records = payload ? drillRecords(db, iso3, indices) : null;
    }
    list.textContent = "";
    if (!records) {
      const miss = el("div", "study-item");
      miss.textContent = "Study texts are not available for this country.";
      list.appendChild(miss);
      return;
    }
    for (const r of records) {
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
      const publicationLink = publicationUrl(db.studies, r.s);
      if (publicationLink) {
        const link = el("a", "study-publication-link");
        link.href = publicationLink;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = "View publication";
        item.appendChild(link);
      }
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
    const closeCardHelp = () => $("card-help-modal").classList.remove("open");
    $("card-help-close").addEventListener("click", closeCardHelp);
    $("card-help-modal").addEventListener("click", e => {
      if (e.target === $("card-help-modal")) closeCardHelp();
    });
    const closeOaHelp = () => $("oa-help-modal").classList.remove("open");
    $("oa-help-close").addEventListener("click", closeOaHelp);
    $("oa-help-modal").addEventListener("click", e => {
      if (e.target === $("oa-help-modal")) closeOaHelp();
    });
    // "?" beside the country pickers: which countries the country views cover.
    const closeCountryHelp = () => $("country-help-modal").classList.remove("open");
    for (const b of document.querySelectorAll(".country-help-button")) {
      b.addEventListener("click", () => $("country-help-modal").classList.add("open"));
    }
    $("country-help-close").addEventListener("click", closeCountryHelp);
    $("country-help-modal").addEventListener("click", e => {
      if (e.target === $("country-help-modal")) closeCountryHelp();
    });
    $("fig-zoom-out").addEventListener("click", () => setFigureZoom(figureZoom - 0.25));
    $("fig-zoom-reset").addEventListener("click", () => setFigureZoom(1));
    $("fig-zoom-in").addEventListener("click", () => setFigureZoom(figureZoom + 0.25));
    $("fig-download").addEventListener("click", downloadFigure);
    $("study-modal-close").addEventListener("click", closeStudyModal);
    $("study-modal").addEventListener("click", e => { if (e.target === $("study-modal")) closeStudyModal(); });
    document.addEventListener("keydown", e => {
      if (e.key === "Escape") { closeModal(); closeStudyModal(); closeOaHelp(); closeCountryHelp(); closeThematicMenu(); }
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
    // Add-on files (redrawn figures, funder and language filters): if a copy of
    // the site lacks one, carry on without that feature instead of failing.
    const OPTIONAL_DATA = { figure_updates: {}, funders: null, languages: null };
    const load = name => name in OPTIONAL_DATA
      ? get(name).catch(err => { console.warn(err.message); return OPTIONAL_DATA[name]; })
      // GBD disease groups; a copy of the site without them falls back to the MeSH groups.
      : name === "disease_gbd" ? get(name).catch(err => { console.warn(err.message); return get("disease"); })
      : get(name);
    const [dict, studies, geo, disease, countries, content, figureCopy, figureUpdates, funders, languages] = await Promise.all(
      ["dict", "studies", "geo", "disease_gbd", "countries", "content", "figure_copy", "figure_updates", "funders", "languages"].map(load));
    FIGURE_UPDATES = figureUpdates;
    db = loadData({ dict, studies, geo, disease, countries, content, funders, languages });

    // Gallery sections, figure entries and the interpolated paper01 PRISMA
    // caption all come from content.json (§15.1) — nothing hardcoded.
    GALLERY = db.content.gallery.map(sec => ({ ...sec, ...SECTION_RENAMES[sec.title], figs: sec.figs.slice() }));
    for (const m of MOVED_FIGURES) {
      const fig = GALLERY.flatMap(s => s.figs).find(f => f.file === m.file);
      const sec = GALLERY.find(s => s.title === m.to);
      if (!fig || !sec) continue;
      for (const s of GALLERY) s.figs = s.figs.filter(f => f.file !== m.file);
      const after = m.first ? -1 : sec.figs.findIndex(f => f.file === m.after);
      sec.figs.splice(after < 0 && !m.first ? sec.figs.length : after + 1, 0, fig);
    }
    GALLERY = GALLERY.filter(sec => !HIDDEN_SECTIONS.has(sec.title));
    for (const [title, prev] of Object.entries(SECTION_AFTER)) {
      const i = GALLERY.findIndex(s => s.title === title);
      if (i < 0 || GALLERY.findIndex(s => s.title === prev) < 0) continue;
      const [sec] = GALLERY.splice(i, 1);
      GALLERY.splice(GALLERY.findIndex(s => s.title === prev) + 1, 0, sec);
    }
    for (const x of EXTRA_FIGURES) {
      const sec = GALLERY.find(s => s.title === x.section);
      if (sec) sec.figs.splice(x.index, 0, x.fig);
    }
    for (const s of EXTRA_SECTIONS) GALLERY.push({ ...s, figs: s.figs.slice() });
    for (const sec of GALLERY) {
      sec.figs = sec.figs.map(figure => ({ ...figure, ...figureCopy[figure.file],
        ...(FIGURE_UPDATES[figure.file] ? { caption: FIGURE_UPDATES[figure.file].caption } : {}) }));
      const groups = SECTION_GROUPS[sec.title];
      if (groups) sec.groups = groups.map(group => ({ ...group,
        figs: group.files.map(file => sec.figs.find(f => f.file === file)).filter(Boolean)
      }));
    }
    FIG_INDEX = {};
    for (const sec of GALLERY) {
      for (const f of sec.figs) FIG_INDEX[f.file] = { ...f, sectionTitle: sec.title };
      sec.figs = sec.figs.filter(f => !HIDDEN_FIGURES.has(f.file));
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
