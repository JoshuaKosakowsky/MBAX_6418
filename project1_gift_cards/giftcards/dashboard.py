"""Build a single-file, dependency-free HTML dashboard from classified results.

The dashboard is a standalone `.html` file with the results embedded as JSON.
It renders on any browser with no server or internet connection. All charts
are pure CSS/JS.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from . import config

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Amazon Gift Card Review Sentiment &amp; Emotion Dashboard</title>
<style>
  :root{--bg:#0f1420;--card:#171e2e;--card2:#1d2740;--text:#e6ebf5;--muted:#8ca0c0;
        --pos:#2ecc71;--neu:#5b8def;--neg:#e74c3c;--accent:#b48cff;--border:#273349;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  header{padding:22px 28px;border-bottom:1px solid var(--border)}
  header h1{margin:0;font-size:22px}
  header p{margin:6px 0 0;color:var(--muted);font-size:13px}
  .wrap{padding:22px 28px;max-width:1180px;margin:0 auto}
  .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px;margin-bottom:22px}
  .kpi{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}
  .kpi .n{font-size:26px;font-weight:700}
  .kpi .l{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px;margin-top:4px}
  .charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin-bottom:22px}
  .panel{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px}
  .panel h3{margin:0 0 12px;font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px}
  .bar{margin:8px 0}
  .bar .row{display:flex;justify-content:space-between;font-size:13px;margin-bottom:3px}
  .bar .track{height:14px;background:var(--card2);border-radius:7px;overflow:hidden}
  .bar .fill{height:100%;border-radius:7px}
  .controls{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px;align-items:center}
  input[type=text],select{background:var(--card2);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:9px 12px;font-size:14px}
  input[type=text]{flex:1;min-width:220px}
  .chip{background:var(--card);border:1px solid var(--border);border-radius:20px;padding:7px 13px;font-size:13px;color:var(--muted)}
  .chip.on{color:#fff;border-color:var(--accent);background:var(--card2)}
  table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;font-size:13px}
  th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--border);vertical-align:top}
  th{color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.4px;background:var(--card2)}
  tr:hover td{background:var(--card2)}
  .badge{display:inline-block;padding:3px 9px;border-radius:20px;font-size:12px;font-weight:600;white-space:nowrap}
  .pos{background:var(--pos);color:#04230f}
  .neu{background:var(--neu);color:#041022}
  .neg{background:var(--neg);color:#2b0505}
  .txt{color:var(--text)}
  .muted{color:var(--muted)}
  .stars{color:#f5c542}
  .pager{display:flex;justify-content:center;gap:12px;margin-top:14px;align-items:center}
  button{padding:8px 14px;border-radius:8px;border:1px solid var(--border);background:var(--card2);color:var(--text);cursor:pointer;font-size:13px}
  button:hover{border-color:var(--accent)}
  button:disabled{opacity:.4;cursor:default}
  .empty{padding:60px 20px;text-align:center;color:var(--muted)}
</style>
</head>
<body>
<header>
  <h1>🎁 Amazon Gift Card Reviews — Sentiment &amp; Emotion</h1>
  <p>Text-only LLM classification | <span id="hdr-sent"></span></p>
</header>

<div class="wrap">
  <div id="kpis" class="kpis"></div>

  <div class="charts">
    <div class="panel"><h3>Sentiment distribution</h3><div id="senti"></div></div>
    <div class="panel"><h3>Primary emotion distribution</h3><div id="emo"></div></div>
    <div class="panel"><h3>Sentiment vs star rating (reference)</h3><div id="stars"></div></div>
  </div>

  <div class="controls">
    <input type="text" id="q" placeholder="Search reviews… (text / title / asin)"/>
    <select id="fSent"><option value="">All sentiments</option><option>positive</option><option>neutral</option><option>negative</option></select>
    <select id="fEmo"><option value="">All emotions</option></select>
    <span id="count" class="chip"></span>
  </div>

  <table>
    <thead><tr>
      <th>★</th><th>Sentiment</th><th>Emotion</th><th>Title / Text</th><th>Conf.</th><th>Evidence</th>
    </tr></thead>
    <tbody id="rows"></tbody>
  </table>
  <div class="pager">
    <button id="prev">‹ Prev</button>
    <span id="pg" class="muted"></span>
    <button id="next">Next ›</button>
  </div>
</div>

<script type="application/json" id="results">__DATA_JSON__</script>
<script>
(function(){
  const DATA = JSON.parse(document.getElementById('results').textContent);
  const EMO_COLORS = {joy:'#2ecc71',sadness:'#5b8def',anger:'#e74c3c',fear:'#9b59b6',
                      surprise:'#f5c542',disgust:'#16a085',neutral:'#7f8c9d'};
  const SENT_COLORS = {positive:'#2ecc71',neutral:'#5b8def',negative:'#e74c3c'};
  const SENT_LABEL = {positive:'Positive',neutral:'Neutral',negative:'Negative'};

  document.getElementById('hdr-sent').textContent =
    DATA.length + ' classified reviews (text-only)';

  function renderKpis(){
    const s = DATA.filter(d=>d.status!=='error');
    const sent = c=>Math.round(s.filter(d=>d.sentiment===c).length/s.length*100);
    document.getElementById('kpis').innerHTML =
      kpi('Total', s.length) + kpi('Positive', sent('positive')+'%', 'var(--pos)') +
      kpi('Neutral', sent('neutral')+'%', 'var(--neu)') + kpi('Negative', sent('negative')+'%', 'var(--neg)') +
      kpi('Top emotion', topEmotion(s), 'var(--accent)') +
      kpi('Avg. confidence', avgConfidence(s));
  }
  function kpi(n,l,c){return '<div class="kpi"><div class="n" '+(c?'style="color:'+c+'"':'')+'>'+esc(n)+'</div><div class="l">'+l+'</div></div>';}

  function counts(arr, key){const m={};arr.forEach(d=>{if(d[key])m[d[key]]=(m[d[key]]||0)+1;});return m;}

  // Integer percentages that sum to EXACTLY 100 via largest-remainder method
  // (each bar rounded independently would drift to 101%/102%).
  function distPcts(cmap, keys){
    const total = keys.reduce((a,k)=>a+(cmap[k]||0),0)||1;
    const raw = keys.map(k=>(cmap[k]||0)/total*100);
    const floors = raw.map(x=>Math.floor(x));
    let leftover = 100 - floors.reduce((a,b)=>a+b,0);
    const order = raw.map((x,i)=>i).sort((i,j)=>
      (raw[j]-Math.floor(raw[j]))-(raw[i]-Math.floor(raw[i])));
    for(let n=0;n<leftover;n++){ floors[order[n]]++; }
    return floors;
  }

  function bars(id, cmap, ordered){
    let el = document.getElementById(id); el.innerHTML='';
    const keys = ordered || Object.keys(cmap);
    const pctArr = distPcts(cmap, keys);
    keys.forEach((k,i)=>{
      const v = cmap[k]||0;
      const pct = pctArr[i];
      const color = (id==='emo'?EMO_COLORS[k]:SENT_COLORS[k]) || '#888';
      el.innerHTML += '<div class="bar"><div class="row"><span>'+esc(human(label(k)))+'</span><span>'+v+' ('+pct+'%)</span></div>'+
        '<div class="track"><div class="fill" style="width:'+pct+'%;background:'+color+'"></div></div></div>';
    });
  }
  function label(k){
    const map = {positive:'Positive',neutral:'Neutral',negative:'Negative',joy:'Joy',sadness:'Sadness',
      anger:'Anger',fear:'Fear',surprise:'Surprise',disgust:'Disgust'};
    return map[k] || k;
  }
  function human(s){return s;}

  // star-rating cross tab: proportion of each star falling into each sentiment
  function starsChart(){
    const el = document.getElementById('stars'); const rows=[1,2,3,4,5];
    const cells = {}; rows.forEach(r=>(cells[r]={positive:0,neutral:0,negative:0}));
    let counts = {}; rows.forEach(r=>counts[r]=0);
    DATA.forEach(d=>{
      const r = Math.round(Number(d.rating)); if(!rows.includes(r)) return;
      counts[r]++; if(SENT_LABEL[d.sentiment]) cells[r][d.sentiment]++;
    });
    el.innerHTML = '';
    rows.forEach(r=>{
      const t = counts[r]||1;
      const seg = ['negative','neutral','positive'].map(s=>
        '<span style="display:inline-block;background:'+SENT_COLORS[s]+';width:'+(cells[r][s]/t*100)+'%;height:16px" title="'+s+' '+cells[r][s]+'"></span>').join('');
      el.innerHTML += '<div class="bar"><div class="row"><span>'+r+' <span class="stars">★★★★★</span>'.slice(0, 2+r)+'</span><span class="muted">'+counts[r]+'</span></div>'+
        '<div class="track" style="display:flex">'+seg+'</div></div>';
    });
  }

  function topEmotion(s){const c=counts(s,'primary_emotion');return Object.keys(c).sort((a,b)=>c[b]-c[a])[0]||'—';}
  function avgConfidence(s){if(!s.length)return '—';return (s.reduce((a,d)=>a+(d.sentiment_confidence||0),0)/s.length*100).toFixed(1)+'%';}

  // table with pagination + filters
  const ROWS=100; let page=0;
  const $=id=>document.getElementById(id);
  function filtered(){
    const q=$('q').value.toLowerCase(), fs=$('fSent').value, fe=$('fEmo').value;
    return DATA.filter(d=>{
      if(d.status==='error') return false;
      if(fs && d.sentiment!==fs) return false;
      if(fe && d.primary_emotion!==fe) return false;
      if(q && !((d.text||'')+' '+(d.title||'')+' '+(d.asin||'')).toLowerCase().includes(q)) return false;
      return true;
    });
  }
  function renderRows(){
    const list = filtered();
    const pages = Math.max(1, Math.ceil(list.length/ROWS));
    if(page>pages-1) page=pages-1;
    const seg = list.slice(page*ROWS, page*ROWS+ROWS);
    $('count').textContent = list.length + ' reviews';
    $('pg').textContent = (page+1) + ' / ' + pages;
    $('prev').disabled = page===0; $('next').disabled = page>=pages-1;
    $('rows').innerHTML = seg.map(d=>{
      const stars = '★★★★★'.slice(0, Math.round(Number(d.rating)||0));
      const ev = d.evidence ? '<span class="muted">“'+esc(d.evidence)+'”</span>' : '<span class="muted">—</span>';
      const conf = d.sentiment_confidence!=null ? (d.sentiment_confidence*100).toFixed(0)+'%' : '—';
      return '<tr><td class="stars">'+stars+'</td>'+
        '<td><span class="badge '+d.sentiment+'">'+SENT_LABEL[d.sentiment]+'</span></td>'+
        '<td><span class="badge" style="background:'+(EMO_COLORS[d.primary_emotion]||'#888')+';color:#0b0b0b">'+esc(label(d.primary_emotion))+'</span></td>'+
        '<td><div class="txt">'+esc(d.title||'')+'</div><div class="muted">'+esc((d.text||'').slice(0,220))+'</div></td>'+
        '<td>'+conf+'</td><td>'+ev+'</td></tr>';
    }).join('') || '<tr><td colspan="6" class="empty">No reviews match.</td></tr>';
  }
  function esc(s){return String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

  // populate emotion filter
  Object.keys(EMO_COLORS).forEach(e=>{$('fEmo').innerHTML += '<option>'+e+'</option>';});
  ['q','fSent','fEmo'].forEach(id=>$(id).addEventListener('input',()=>{page=0;renderRows();}));
  $('prev').onclick=()=>{if(page>0){page--;renderRows();}};
  $('next').onclick=()=>{page++;renderRows();};

  renderKpis(); bars('senti', counts(DATA.filter(d=>d.status!=='error'),'sentiment'), ['positive','neutral','negative']);
  bars('emo', counts(DATA.filter(d=>d.status!=='error'),'primary_emotion')); starsChart(); renderRows();
})();
</script>
</body>
</html>
"""


def _clean(v) -> str:
    if v is None:
        return ""
    return str(v)


def build_dashboard(
    results: Iterable[dict],
    out_path: Path | None = None,
    max_rows: int | None = None,
    id_key: str = "asin",
) -> Path:
    """Write the dashboard HTML with results embedded as JSON."""
    rows = list(results)
    if max_rows is not None:
        rows = rows[:max_rows]
    data = []
    for r in rows:
        data.append(
            {
                "rating": r.get("rating"),
                "title": _clean(r.get("title")),
                "text": _clean(r.get("text")),
                "asin": _clean(r.get("asin")),
                "sentiment": r.get("sentiment"),
                "primary_emotion": r.get("primary_emotion"),
                "sentiment_confidence": r.get("sentiment_confidence"),
                "evidence": _clean(r.get("evidence")),
                "status": r.get("status"),
            }
        )
    payload = json.dumps(data, ensure_ascii=False)
    html = TEMPLATE.replace("__DATA_JSON__", payload)
    target = out_path or config.OUTPUT_DIR / "dashboard.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    print(f"Wrote dashboard to {target} ({target.stat().st_size/1024:.0f} KB, {len(data)} reviews embedded)")
    return target


def load_results_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows
