"""Build a product-grade, single-file evaluation dashboard from scored results.

The page is entirely self-contained (embedded JSON, inline CSS/JS) and works
offline with no server. Numbers are computed with the SAME ``evaluate.score``
path used to report results, so the on-page figures always match the scoring.

Theme: a coherent palette driven entirely by CSS custom properties on ``:root``,
with a built-in dark/light toggle — recolourable by the host via one block.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import config, evaluate

CLASS_ORDER = ["NEGATIVE", "NEUTRAL", "POSITIVE"]

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Gift Card Sentiment — Model Evaluation</title>
<style>
/* ===== Theme token block — recolour the product here =======================
   Replace any value (or the whole light/dark pair) to re-skin the dashboard.
   The accent/good/bad/muted tokens drive every color on the page.             */
:root{
  --bg:#0d1117; --surface:#161b22; --surface-2:#1c2330; --surface-3:#232b3a;
  --border:#2a3140; --text:#e6edf3; --muted:#8b98a9; --accent:#58a6ff;
  --good:#3fb950; --bad:#f85149; --warn:#d29922;
  --radius:14px; --font-system:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Inter,Helvetica,Arial,sans-serif;
}
html[data-theme="light"]{
  --bg:#f6f8fa; --surface:#ffffff; --surface-2:#f0f3f6; --surface-3:#e6ebf1;
  --border:#d8dee4; --text:#1f2328; --muted:#57606a; --accent:#0969da;
  --good:#1a7f37; --bad:#cf222e; --warn:#9a6700;
}
/* ========================================================================= */
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:var(--font-system);
     font-size:15px;line-height:1.5;-webkit-font-smoothing:antialiased;transition:background .25s,color .25s}
.wrap{max-width:1180px;margin:0 auto;padding:28px 24px 64px}
/* header */
header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:26px}
.brand{display:flex;align-items:center;gap:12px}
.brand .mark{width:38px;height:38px;border-radius:11px;background:linear-gradient(135deg,var(--accent),var(--good));
             display:grid;place-items:center;font-size:19px;box-shadow:0 6px 18px -6px var(--accent)}
.brand h1{margin:0;font-size:20px;font-weight:700;letter-spacing:-.2px}
.brand .sub{margin:2px 0 0;color:var(--muted);font-size:13px}
.iconbtn{background:var(--surface);border:1px solid var(--border);color:var(--text);border-radius:10px;
         width:40px;height:40px;cursor:pointer;font-size:16px;display:grid;place-items:center}
.iconbtn:hover{border-color:var(--accent)}
/* hero verdict */
.hero{background:linear-gradient(180deg,var(--surface),var(--surface-2));border:1px solid var(--border);
      border-radius:calc(var(--radius) + 4px);padding:34px 32px;margin-bottom:22px;position:relative;overflow:hidden}
.hero::after{content:"";position:absolute;inset:auto -80px -120px auto;width:340px;height:340px;border-radius:50%;
             background:radial-gradient(circle,color-mix(in srgb,var(--accent) 22%,transparent),transparent 70%)}
.hero .kicker{text-transform:uppercase;letter-spacing:2.5px;font-size:12px;color:var(--accent);font-weight:600}
.hero .big{font-size:64px;font-weight:800;line-height:1;letter-spacing:-1.5px;margin:10px 0 6px;font-variant-numeric:tabular-nums}
.hero .big small{font-size:20px;color:var(--muted);font-weight:500;letter-spacing:0}
.hero p{position:relative;z-index:1;margin:0;max-width:640px;color:var(--muted);font-size:14.5px}
.hero .deliverables{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px;position:relative;z-index:1}
/* kpis */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:22px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px}
.kpi .l{color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
.kpi .v{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .v.good{color:var(--good)} .kpi .v.bad{color:var(--bad)}
.kpi .s{color:var(--muted);font-size:12px;margin-top:2px}
/* panels */
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:22px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.panel{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px}
.panel h2{margin:0 0 4px;font-size:15px;font-weight:650;letter-spacing:-.1px}
.panel .desc{margin:0 0 16px;color:var(--muted);font-size:13px}
/* confusion matrix */
.matrix{display:block}
.matrix .axis{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1px}
.cell{width:100%;border-radius:12px;padding:16px 10px;text-align:center;position:relative}
.cell .n{font-size:30px;font-weight:800;font-variant-numeric:tabular-nums}
.cell .lab{font-size:12px;color:inherit;opacity:.9}
.cell.ok{background:color-mix(in srgb,var(--good) 16%,var(--surface-2));color:var(--good)}
.cell.err{background:color-mix(in srgb,var(--bad) 16%,var(--surface-2));color:var(--bad)}
/* mistakes bars */
.bars{margin-top:6px}
.bars .bar{display:grid;grid-template-columns:110px 1fr 40px;gap:10px;align-items:center;margin-bottom:10px;font-size:13px}
.bars .track{height:22px;background:var(--surface-2);border-radius:6px;overflow:hidden}
.bars .fill{border-radius:6px}
.bars .cnt{font-variant-numeric:tabular-nums;color:var(--muted)}
/* descriptive view (Step 7) */
.descgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-top:6px}
.descgrid h3{font-size:12px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin:0 0 14px}
.dbars .row{display:flex;justify-content:space-between;font-size:12.5px;margin:0 0 4px}
.dbars .track{height:18px;background:var(--surface-2);border-radius:5px;overflow:hidden;margin-bottom:12px}
.dbars .fill{height:100%;border-radius:5px}
.grouped .grow{display:grid;grid-template-columns:64px 1fr;gap:10px;align-items:center;margin-bottom:14px}
.grouped .grow .lab{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.grouped .tracks{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grouped .sub{font-size:10.5px;color:var(--muted);margin-top:3px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:14px;color:var(--muted);font-size:12.5px}
.legend .sw{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
/* table */
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:0 0 14px}
.seg{display:flex;gap:4px;background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:3px}
.seg button{border:0;background:transparent;color:var(--muted);padding:7px 14px;border-radius:8px;cursor:pointer;font-size:13px}
.seg button.on{background:var(--surface-3);color:var(--text);font-weight:600}
input{background:var(--surface-2);border:1px solid var(--border);border-radius:10px;color:var(--text);
      padding:9px 12px;font-size:14px;flex:1;min-width:160px}
input:focus{outline:none;border-color:var(--accent)}
.tablebox{border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;background:var(--surface)}
table{width:100%;border-collapse:collapse;font-size:13.5px}
thead th{background:var(--surface-2);color:var(--muted);text-align:left;padding:11px 14px;font-size:11.5px;
         text-transform:uppercase;letter-spacing:.8px;position:sticky;top:0}
tbody td{padding:12px 14px;border-top:1px solid var(--border);vertical-align:top}
tbody tr:hover td{background:var(--surface-2)}
.pill{display:inline-block;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}
.pill.good{background:color-mix(in srgb,var(--good) 18%,transparent);color:var(--good)}
.pill.bad{background:color-mix(in srgb,var(--bad) 18%,transparent);color:var(--bad)}
.pill.neu{background:color-mix(in srgb,var(--accent) 18%,transparent);color:var(--accent)}
.stars{color:var(--warn);letter-spacing:1px}
.muted{color:var(--muted)}
.confbar{display:inline-block;width:52px;height:6px;background:var(--surface-3);border-radius:3px;overflow:hidden;vertical-align:middle;margin-right:6px}
.confbar i{display:block;height:100%}
.pager{display:flex;align-items:center;justify-content:center;gap:14px;padding:14px;background:var(--surface-2)}
.pager button{border:1px solid var(--border);background:var(--surface);color:var(--text);border-radius:9px;padding:7px 14px;cursor:pointer}
.pager button:disabled{opacity:.4;cursor:default}
.summarycount{color:var(--muted);font-size:13px;padding:12px 14px;background:var(--surface-2);border-top:1px solid var(--border)}
.foot{margin-top:26px;color:var(--muted);font-size:12.5px;line-height:1.6;border-top:1px solid var(--border);padding-top:16px}
@media(max-width:600px){.hero .big{font-size:48px}}
</style>
</head>
<body>
<div class="wrap">

<header>
  <div class="brand">
    <div class="mark">🎁</div>
    <div>
      <h1>Gift Card Review Sentiment — Model Evaluation</h1>
      <div class="sub" id="subtitle"></div>
    </div>
  </div>
  <button class="iconbtn" id="theme" title="Toggle theme" aria-label="Toggle theme">🌙</button>
</header>

<div class="hero">
  <div class="kicker">Agreement with star rating</div>
  <div class="big"><span id="bigpct">—</span><small>%</small></div>
  <p id="verdict"></p>
  <div class="deliverables" id="deltags"></div>
</div>

<div class="kpis" id="kpis"></div>

<div class="panel" style="margin-bottom:22px">
  <h2>Descriptive view</h2>
  <p class="desc">What's in the batch, and how far the model's calls drift from the reference labels by class.</p>
  <div class="descgrid">
    <div><h3>Star rating distribution</h3><div class="dbars" id="starDist"></div></div>
    <div><h3>Reference vs predicted (by class)</h3><div class="grouped" id="refPred"></div></div>
    <div><h3>Answered right per class</h3><div class="dbars" id="classRight"></div></div>
  </div>
</div>

<div class="grid2">
  <div class="panel">
    <h2>Right vs wrong</h2>
    <p class="desc">Rating-derived reference (rows) × model verdict (cols). Green = agree, red = disagree.</p>
    <div class="matrix" id="matrix"></div>
    <div class="legend">
      <span><span class="sw" style="background:var(--good)"></span>Agreement</span>
      <span><span class="sw" style="background:var(--bad)"></span>Disagreement</span>
    </div>
  </div>

  <div class="panel">
    <h2>Where the mistakes land</h2>
    <p class="desc">Dissagreements by star rating, and which class they fell in.</p>
    <div class="bars" id="mistakes"></div>
    <p class="muted" id="mistakenote"></p>
  </div>
</div>

<div class="panel" style="padding:20px">
  <h2>Review-by-review</h2>
  <p class="desc">Every classified review, with the rating it carried, the reference label, the model's call, and confidence.</p>
  <div class="toolbar">
    <div class="seg" id="filtSeg">
      <button data-f="all" class="on">All</button>
      <button data-f="ok">Correct</button>
      <button data-f="err">Wrong</button>
    </div>
    <select id="fStar" title="Filter by star rating" style="background:var(--surface-2);border:1px solid var(--border);color:var(--text);border-radius:10px;padding:9px 12px;font-size:14px">
      <option value="">All stars</option>
      <option value="1">★ 1</option>
      <option value="2">★ 2</option>
      <option value="3">★ 3</option>
      <option value="4">★ 4</option>
      <option value="5">★ 5</option>
    </select>
    <input id="q" placeholder="Search title or text…"/>
  </div>
  <div class="tablebox">
    <table>
      <thead><tr>
        <th>Rating</th><th>Reference</th><th>Model</th><th>Confidence</th><th>Review</th>
      </tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div class="summarycount" id="count"></div>
    <div class="pager">
      <button id="prev" disabled>← Prev</button>
      <span id="pg" class="muted"></span>
      <button id="next">Next →</button>
    </div>
  </div>
</div>

<div class="foot" id="foot"></div>
</div>

<script>window.__DATA__={summary:__SUMMARY_JSON__,rows:__ROWS_JSON__};</script>
<script>
(function(){
  const S = window.__DATA__.summary;
  const ROWS = window.__DATA__.rows;
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct = x => Math.round(x*100);
  const stars = n => '<span class="stars">'+'★★★★★'.slice(0, Math.max(1, Math.round(n||1)))+'</span>';

  // theme toggle
  const themeBtn = $('theme');
  themeBtn.onclick = () => {
    const cur = document.documentElement.getAttribute('data-theme');
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    themeBtn.textContent = next === 'dark' ? '🌙' : '☀️';
  };

  $('subtitle').textContent = `${S.model} · ${S.n} reviews · checked against the star rating`;
  $('bigpct').textContent = pct(S.overall_accuracy);
  $('verdict').textContent = S.insights[0];

  // deliverable tags
  $('deltags').innerHTML = [S.right+' correct', S.wrong+' wrong',
    S.balanced ? pct(S.balanced_accuracy)+'% balanced' : ''].filter(Boolean)
    .map(x => '<span class="pill '+ (x.includes('wrong') ? 'bad' : 'good') +'">'+esc(x)+'</span>').join(' ');

  // KPIs (class-generic over S.per_class)
  const cols = S.classes || ['NEGATIVE','NEUTRAL','POSITIVE'];
  const kpis = [
    ['Agreement', pct(S.overall_accuracy)+'%', 'good'],
    ['Correct', S.right, 'good'],
    ['Wrong', S.wrong, 'bad'],
    ['Balanced accuracy', pct(S.balanced_accuracy)+'%', ''],
    ['Avg confidence', pct(S.avg_confidence)+'%', ''],
  ];
  cols.forEach(c => {
    const m = S.per_class[c];
    kpis.push([c+' recall', pct(m.recall)+'%', ''],
              [c+' precision', pct(m.precision)+'%', '']);
  });
  $('kpis').innerHTML = kpis.map(([l,v,c])=>
    '<div class="kpi"><div class="l">'+l+'</div><div class="v '+(c||'')+'">'+v+'</div></div>').join('');

  // confusion matrix (N x N, class-generic)
  let mh = '<table style="width:100%;border-collapse:collapse;text-align:center">' +
    '<tr><th style="color:var(--muted);font-size:11px;text-transform:uppercase;text-align:left;padding-bottom:8px">ref →</th>' +
    cols.map(c=>'<th style="color:var(--muted);font-size:11px;text-transform:uppercase;padding-bottom:8px">'+c+'</th>').join('') + '</tr>';
  cols.forEach(t => {
    mh += '<tr><th style="color:var(--muted);font-size:11px;text-transform:uppercase;text-align:left">'+t+'</th>';
    cols.forEach(p => {
      const ok = t === p;
      mh += '<td style="padding:10px 6px;border-radius:10px;background:' +
        (ok ? 'color-mix(in srgb,var(--good) 16%,var(--surface-2))' : 'color-mix(in srgb,var(--bad) 16%,var(--surface-2))') +
        ';color:' + (ok ? 'var(--good)' : 'var(--bad)') + '"><div style="font-size:24px;font-weight:800">' +
        (S.confusion[t][p] || 0) + '</div></td>';
    });
    mh += '</tr>';
  });
  mh += '</table>';
  $('matrix').innerHTML = mh;

  // ---- Descriptive view (Step 7). Bars keep a fixed-height track so a 0
  // value never collapses the row; widths are finite pct of the max. ----
  const maxStar = Math.max(1, ...Object.values(S.stars||{}));
  $('starDist').innerHTML = [1,2,3,4,5].map(k => {
    const v = S.stars[k] || 0;
    const w = (v / maxStar * 100).toFixed(2);
    return '<div class="row"><span>'+k+' <span class="stars">'+'★★★★★'.slice(0,k)+'</span></span><span>'+v+'</span></div>'+
      '<div class="track"><div class="fill" style="width:'+w+'%;background:var(--accent)"></div></div>';
  }).join('');

  const maxRP = Math.max(1, ...cols.map(c => Math.max((S.ref_pred[c]||{}).ref||0, (S.ref_pred[c]||{}).pred||0)));
  $('refPred').innerHTML = cols.map(c => {
    const rp = S.ref_pred[c] || {ref:0,pred:0};
    const rw = (rp.ref / maxRP * 100).toFixed(2), pw = (rp.pred / maxRP * 100).toFixed(2);
    const predColor = rp.pred >= rp.ref ? 'var(--good)' : 'var(--bad)';
    return '<div class="grow"><span class="lab">'+c+'</span><div><div class="tracks">'+
      '<div><div class="track"><div class="fill" style="width:'+rw+'%;background:var(--accent)"></div></div><div class="sub">reference '+rp.ref+'</div></div>'+
      '<div><div class="track"><div class="fill" style="width:'+pw+'%;background:'+predColor+'"></div></div><div class="sub">predicted '+rp.pred+'</div></div>'+
      '</div></div></div>';
  }).join('');

  $('classRight').innerHTML = cols.map(c => {
    const cr = S.class_right[c] || {correct:0,total:0};
    const pct = cr.total ? Math.round(cr.correct / cr.total * 100) : 0;
    const color = pct >= 60 ? 'var(--good)' : (pct >= 30 ? 'var(--warn)' : 'var(--bad)');
    return '<div class="row"><span>'+c+'</span><span>'+cr.correct+' / '+cr.total+' ('+pct+'%)</span></div>'+
      '<div class="track"><div class="fill" style="width:'+pct+'%;background:'+color+'"></div></div>';
  }).join('');

  // mistakes by rating
  const mr = S.disagreement_ratings;
  const max = Math.max(1, ...Object.values(mr));
  $('mistakes').innerHTML = [1,2,3,4,5].map(r => {
    const v = mr[r] || 0;
    return '<div class="bar"><span>'+r+' <span class="stars">★★★★★'.slice(0, r)+'</span></span>'+
      '<div class="track"><div class="fill" style="width:'+(v/max*100)+'%;background:'+(v?'var(--bad)':'var(--border)')+'"></div></div>'+
      '<span class="cnt">'+v+'</span></div>';
  }).join('');
  /* removal of adj: bottom bar shows count, note explains clustering */
  var src = S.disagreement_series || {};
  $('mistakenote').textContent = S.insights[1] ? S.insights[1] : '';

  // table with filters + pagination
  const ROWS_PAGE = 12; let page = 0, filt = 'all', star = '';
  function visible(){
    const q = $('q').value.toLowerCase(); let list = ROWS;
    if (filt === 'ok') list = list.filter(r => r.correct);
    if (filt === 'err') list = list.filter(r => !r.correct);
    if (star) list = list.filter(r => (r.rating|0) === star);
    if (q) list = list.filter(r => ((r.title||'')+(r.text||'')).toLowerCase().includes(q));
    return list;
  }
  function render(){
    const list = visible();
    const pages = Math.max(1, Math.ceil(list.length/ROWS_PAGE));
    page = Math.min(page, pages-1);
    const seg = list.slice(page*ROWS_PAGE, page*ROWS_PAGE+ROWS_PAGE);
    const tag = (filt==='ok' ? ' · correct' : filt==='err' ? ' · wrong' : '') + (star ? ' · ★'+star : '');
    $('count').textContent = list.length + ' of ' + ROWS.length + ' review' +
      (list.length===1?'':'s') + tag;
    $('pg').textContent = (page+1)+' / '+pages;
    $('prev').disabled = page===0; $('next').disabled = page>=pages-1;
    $('rows').innerHTML = seg.map(r => {
      const conf = r.confidence!=null ? r.confidence : 0;
      return '<tr>'+
        '<td>'+stars(r.rating)+'</td>'+
        '<td><span class="pill neu">'+esc(r.truth)+'</span></td>'+
        '<td><span class="pill '+(r.correct?'good':'bad')+'">'+esc(r.pred)+'</span></td>'+
        '<td><span class="confbar"><i style="width:'+conf*100+'%;background:'+(r.correct?'var(--good)':'var(--bad)')+'"></i></span>'+pct(conf)+'%</td>'+
        '<td><div style="font-weight:600">'+esc(r.title||'')+'</div>'+
            '<div class="muted">'+esc((r.text||'').slice(0,180))+'</div>'+
            (r.correct?'':'<div class="bad" style="font-size:12px">disagrees with a '+esc(r.truth)+' rating</div>')+
        '</td></tr>';
    }).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:26px">No reviews match.</td></tr>';
  }
  document.querySelectorAll('#filtSeg button').forEach(b => b.onclick = () => {
    document.querySelectorAll('#filtSeg button').forEach(x => x.classList.remove('on'));
    b.classList.add('on'); filt = b.dataset.f; page = 0; render();
  });
  $('q').addEventListener('input', () => { page = 0; render(); });
  $('fStar').addEventListener('change', () => { star = Number($('fStar').value) || ''; page = 0; render(); });
  $('prev').onclick = () => { if (page>0){page--; render();} };
  $('next').onclick = () => { page++; render(); };

  $('foot').innerHTML = '<b>Method.</b> Reference label derived from the star rating (4–5★ = positive, else negative) and used only for checking — the model never saw it. ' +
    'The batch was balanced so the corpus’s 4–5★ skew cannot flatter the score; balanced accuracy is the mean of per-class recall. ' +
    'Numbers on this page come from the same scoring module used to report results.' +
    ' '+esc(S.model)+', '+S.generated_at+'.';

  render();
})();
</script>
</body>
</html>
"""


def _trim_row(r: dict) -> dict:
    truth = evaluate.rating_score_label(r.get("rating"))
    pred = (r.get("label") or "").upper()
    correct = pred == truth
    return {
        "rating": r.get("rating"),
        "truth": truth,
        "pred": pred,
        "correct": correct,
        "confidence": r.get("confidence"),
        "title": (r.get("title") or "").strip(),
        "text": (r.get("text") or "").strip()[:240],
    }


def _insights(res: evaluate.ScoreResult) -> list[str]:
    lines = []
    agrees = round(res.overall_accuracy * 100)
    lines.append(
        f"The model matches the rating-derived label on {agrees}% of the {res.n} reviews."
    )
    neg = res.per_class.get("NEGATIVE")
    neu = res.per_class.get("NEUTRAL")
    pos = res.per_class.get("POSITIVE")
    if neg and pos:
        lines.append(
            f"It reads clearly positive reviews well ({round(pos.recall*100)}% recall), is careful "
            f"before calling something negative ({round(neg.precision*100)}% precision)"
            + (f", and its NEUTRAL class is a separate, mostly-underused tier "
               f"(recall {round(neu.recall*100)}%)." if neu else ".")
        )
    wrong = res.disagreements
    if wrong:
        from collections import Counter

        by_class = Counter(d["truth"] for d in wrong)
        by_rating = Counter(d["rating"] for d in wrong)
        worst = by_rating.most_common(1)[0] if by_rating else (None, 0)
        parts = ", ".join(f"{c}: {n} missed" for c, n in by_class.most_common())
        rating_hint = f"concentrated around ★{worst[0]}." if worst[0] else "."
        lines.append(f"Errors by reference class — {parts} — {rating_hint}")
        if neu and neu.support and by_class.get("NEUTRAL", 0) >= neu.support * 0.5:
            lines.append(
                "A large share of NEUTRAL (★3) reviews are mislabeled, i.e. the model tends to "
                "collapse ★3 into another class rather than treat it as its own tier."
            )
    return lines


def build(results: Iterable[dict], out_path: Path | None = None, model: str = "n/a") -> Path:
    """Write the evaluation dashboard HTML from scored result rows."""
    rows = list(results)
    ok = [r for r in rows if r.get("status") == "ok"]
    pairs = [(evaluate.rating_score_label(r.get("rating")), (r.get("label") or "").upper())
             for r in ok]
    res = evaluate.score(pairs)
    evaluate.attach_disagreements(res, ok)

    from collections import Counter

    wrong_by_rating = Counter(d["rating"] for d in res.disagreements)
    avg_conf = (sum((r.get("confidence") or 0) for r in ok) / len(ok)) if ok else 0.0

    # Descriptive aggregates (Step 7) for the at-a-glance visualizations.
    star_counter = Counter(int(round(float(r.get("rating") or 0))) for r in ok)
    ref_counts = Counter(evaluate.rating_score_label(r.get("rating")) for r in ok)
    pred_counts = Counter(
        (r.get("label") or "").upper() for r in ok
        if (r.get("label") or "").upper() in CLASS_ORDER
    )
    ref_pred = {
        c: {"ref": ref_counts.get(c, 0), "pred": pred_counts.get(c, 0)}
        for c in CLASS_ORDER
    }
    class_right = {
        c: {"correct": res.confusion.get((c, c), 0), "total": res.per_class[c].support}
        for c in CLASS_ORDER
    }

    summary = {
        "n": res.n,
        "classes": CLASS_ORDER,
        "right": res.n - len(res.disagreements),
        "wrong": len(res.disagreements),
        "overall_accuracy": res.overall_accuracy,
        "balanced_accuracy": res.balanced_accuracy,
        "avg_confidence": round(avg_conf, 3),
        "stars": {str(k): star_counter.get(k, 0) for k in [1, 2, 3, 4, 5]},
        "ref_pred": ref_pred,
        "class_right": class_right,
        "per_class": {
            c: {
                "precision": m.precision,
                "recall": m.recall,
                "f1": m.f1,
                "support": m.support,
            }
            for c, m in res.per_class.items()
        },
        "confusion": {
            t: {p: res.confusion.get((t, p), 0) for p in CLASS_ORDER}
            for t in CLASS_ORDER
        },
        "disagreement_ratings": {str(r): wrong_by_rating.get(float(r), 0) for r in [1, 2, 3, 4, 5]},
        "insights": _insights(res),
        "model": model or (ok[0].get("model") if ok else "n/a"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
    rows_json = [_trim_row(r) for r in ok]

    # Embed JSON by escaping "<" as \u003c (valid JSON escape). A real HTML
    # tokenizer mis-parses a <script> block whose raw text contains "<" sequences
    # (e.g. review text with "<br />"), which silently empties the element and
    # breaks JSON.parse. Escaping makes the data block tokenizer-proof.
    def _safe_json(dumps: str) -> str:
        return dumps.replace("<", "\\u003c")

    html = TEMPLATE.replace(
        "__SUMMARY_JSON__", _safe_json(json.dumps(summary, ensure_ascii=False))
    )
    html = html.replace(
        "__ROWS_JSON__", _safe_json(json.dumps(rows_json, ensure_ascii=False))
    )

    target = out_path or config.OUTPUT_DIR / "eval_dashboard.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    print(f"Wrote {target} ({target.stat().st_size/1024:.0f} KB, {len(rows_json)} reviews)")
    return target
