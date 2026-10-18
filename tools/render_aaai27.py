from pathlib import Path
from datetime import date
import argparse, html, json

parser=argparse.ArgumentParser(description='Render the existing AAAI-27 workshop directory from its shared verified dataset.')
parser.add_argument('--data',type=Path,default=Path(__file__).resolve().parents[1]/'dorl/27AAAIworkshop/data.json')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'dorl/27AAAIworkshop/index.html')
args=parser.parse_args()
payload=json.loads(args.data.read_text(encoding='utf-8'))
rows=payload['workshops']
OFFICIAL='https://aaai.org/conference/aaai/aaai-27/aaai-27-workshop-program-list/'
PROGRAM='https://aaai.org/conference/aaai/aaai-27/aaai-27-workshop-program/'
TIMETABLE='https://aaai.org/conference/aaai/aaai-27/workshops-call/'
assert rows and len({r['id'] for r in rows})==len(rows)
assert len({r['title'] for r in rows})==len(rows)
for r in rows:
    for field in ['submission','notification']:
        assert r[field] is None or date.fromisoformat(r[field])
    assert r['website'].startswith('https://')
    assert r['source'].startswith('https://')
    r['exception']=bool((r['submission'] and r['submission']!='2026-11-20') or (r['notification'] and r['notification']!='2026-12-02'))
    r['incomplete']=not (r['submission'] and r['notification'])
    r['attention']=r['exception'] or r['incomplete'] or bool(r['flags'])
COUNT=len(rows)
COMPLETE=sum(not r['incomplete'] for r in rows)
EXCEPTION_COUNT=sum(r['exception'] for r in rows)
UNKNOWN_COUNT=sum(r['incomplete'] for r in rows)
TIME_COUNT=sum('time' in r['flags'] for r in rows)
CONFLICT_COUNT=sum('conflict' in r['flags'] for r in rows)
FAST_COUNT=sum(bool(r['fastTracks']) for r in rows)
checked=date.fromisoformat(payload['checkedDate'])
CHECKED_LONG=f"{checked.strftime('%B')} {checked.day}, {checked.year}"
CHECKED_ISO=checked.isoformat()
def esc(s): return html.escape(str(s), quote=True)
def fmt(s):
    if not s: return 'Unknown'
    d = date.fromisoformat(s)
    return d.strftime('%b') + f' {d.day:02d}, {d.year}'
def badge(label, cls=''):
    return f'<span class="badge {cls}">{esc(label)}</span>'
def datecell(r, field):
    val = r[field]
    if not val:
        return '<span class="date unknown">Unknown</span><span class="sub">Not confirmed on the workshop website</span>'
    prefix = 'By ' if field == 'notification' and r['notificationQualifier'] else ''
    s = f'<time class="date" datetime="{val}">{prefix}{fmt(val)}</time>'
    if field == 'submission':
        zone = r['submissionZone']
        meta = ' · '.join(t for t in [r['submissionTime'], zone if zone != 'Unknown' else 'Timezone: Unknown'] if t)
        s += f'<span class="sub">{esc(meta)}</span>'
    else:
        meta = ' · '.join(t for t in [r.get('notificationTime',''), r.get('notificationZone','')] if t and t != 'Unknown')
        if meta:
            s += f'<span class="sub">{esc(meta)}</span>'
    return s

def rowhtml(r):
    badges = []
    if r['exception']: badges.append(badge('Different dates','exception'))
    if 'time' in r['flags']: badges.append(badge('Custom cutoff','timebadge'))
    if 'conflict' in r['flags']: badges.append(badge('Source mismatch','warning'))
    if r['incomplete']: badges.append(badge('Unknown date','warning'))
    if r['fastTracks']: badges.append(badge('Fast track','fast'))
    source_link = f'<a href="{esc(r["source"])}" target="_blank" rel="noopener noreferrer">{esc(r["basis"])} ↗</a>'
    notes = ''.join(f'<p>{esc(n)}</p>' for n in r['notes'])
    for t in r['fastTracks']:
        notes += f'<div class="track"><strong>{esc(t["label"])}</strong><span>Submission: {fmt(t["submission"])} · Decision: {fmt(t["notification"])} · {esc(t["zone"])}</span><p>{esc(t["note"])}</p></div>'
    if notes:
        source_link += f'<details><summary>Evidence & notes</summary><div class="detailbody">{notes}<p class="evidence-links"><a href="{esc(r["website"])}" target="_blank" rel="noopener noreferrer">Workshop website ↗</a> · <a href="{OFFICIAL}" target="_blank" rel="noopener noreferrer">AAAI individual CFP ↗</a></p></div></details>'
    elif r['basis'] != 'AAAI individual CFP':
        source_link += f'<span class="sub"><a class="mutedlink" href="{OFFICIAL}" target="_blank" rel="noopener noreferrer">AAAI listing ↗</a></span>'
    return f'''<tr data-id="{r['id']}" class="{'attention-row' if r['attention'] else ''}">
      <td class="num">{r['id']:02d}</td>
      <td class="titlecell"><a class="workshop-title" href="{esc(r['website'])}" target="_blank" rel="noopener noreferrer">{esc(r['title'])}</a><div class="badges">{''.join(badges)}</div></td>
      <td>{datecell(r,'submission')}</td><td>{datecell(r,'notification')}</td>
      <td class="sourcecell">{source_link}</td>
    </tr>'''

TABLE = '\n'.join(rowhtml(r) for r in rows)
DATA = json.dumps(rows,ensure_ascii=False).replace('<', '\u003c').replace('>', '\u003e').replace('&', '\u0026')
EXCEPTIONS = ''.join(f'<a href="#workshops" class="exception-item" data-focus="{r["id"]}"><span>{esc({8:"AICS",13:"Embodied Meta-alignment",14:"EMC2",15:"EAIM / Music",18:"GSR-VLM",25:"NeuroAI 2.0",32:"SAFE",37:"Medical World Models",38:"NeusymBridge"}.get(r["id"],r["title"]))}</span><span>{fmt(r["submission"])} <b>→</b> {fmt(r["notification"])}</span></a>' for r in sorted((r for r in rows if r['exception']), key=lambda r:r['submission'] or '9999-12-31'))

TEMPLATE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="All 45 named AAAI-27 workshops currently listed by AAAI, with paper submission deadlines, decision dates, source links, and discrepancies. Checked October 17, 2026.">
<meta name="robots" content="noindex, nofollow, noarchive"><meta name="referrer" content="no-referrer">
<link rel="canonical" href="https://chongyuzhu.com/dorl/27AAAIworkshop/"><title>AAAI-27 Workshop Deadlines | October 17, 2026</title>
<style>
:root{--ink:#172c3e;--muted:#60717b;--bg:#f6f6f1;--paper:#fff;--line:#dce2df;--teal:#0d605f;--teal-light:#e7f2ee;--coral:#b9432b;--coral-light:#fff0e9;--gold:#8b5c12;--gold-light:#fff6df;--blue-light:#e9f0fc;--blue:#365b91}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--bg);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:var(--teal);text-decoration:none}a:hover{text-decoration:underline}button,input,select{font:inherit}button,a,input,select,summary{outline-offset:4px}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid #ca6b38}button{cursor:pointer}.wrap{max-width:1536px;margin:auto;padding:0 48px}.topbar{border-bottom:1px solid var(--line);background:var(--paper)}.topinner{display:flex;justify-content:space-between;gap:20px;align-items:center;padding-top:17px;padding-bottom:17px}.brand{font-weight:750;letter-spacing:.02em;font-size:14px}.brand span{color:var(--teal);margin-right:9px}.toplinks{display:flex;gap:24px;font-size:12px;font-weight:650}.hero{padding-top:48px;padding-bottom:32px}.eyebrow{font-size:11px;letter-spacing:.16em;font-weight:750;text-transform:uppercase;color:var(--teal)}.hero-layout{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:48px;align-items:end}h1{font-size:clamp(36px,4.2vw,62px);line-height:1.08;letter-spacing:-.045em;font-weight:750;margin:13px 0 18px}h1 span{color:var(--teal)}.dek{max-width:770px;font-size:16px;color:var(--muted);margin:0}.event{border-left:3px solid var(--teal);padding:5px 0 5px 20px;margin-bottom:4px;font-size:14px}.event strong{display:block;font-size:17px;margin:5px 0}.event small{color:var(--muted)}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:0;background:var(--paper);border:1px solid var(--line);border-radius:13px;overflow:hidden;margin-top:30px}.stat{padding:20px 24px}.stat+.stat{border-left:1px solid var(--line)}.stat strong{font-size:33px;line-height:1.2;display:block;font-variant-numeric:tabular-nums;letter-spacing:-.04em}.stat span{font-size:12px;color:var(--muted)}.stat:nth-child(3) strong{color:var(--coral)}.stat:nth-child(4) strong{color:var(--gold)}.intro-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px}.panel{background:var(--paper);border:1px solid var(--line);padding:22px 24px;border-radius:12px}h2{font-size:21px;letter-spacing:-.025em;line-height:1.25;margin:0 0 10px}h3{font-size:15px;margin:14px 0 5px}.panel p{margin:8px 0;font-size:13px;color:var(--muted)}.baseline{display:flex;align-items:center;gap:20px;margin:18px 0}.baseline-item{font-size:11px;color:var(--muted)}.baseline-item strong{display:block;color:var(--ink);font-size:19px;letter-spacing:-.02em}.arrow{color:var(--teal);font-size:24px}.scope{border-top:1px solid var(--line);padding-top:12px}.tiny{font-size:11px!important}.exception-list{display:grid;grid-template-columns:1fr;gap:0;margin-top:12px}.exception-item{display:flex;justify-content:space-between;gap:12px;font-size:11px;padding:5px 0;border-bottom:1px solid #eef0ed}.exception-item:last-child{border:0}.exception-item>span:first-child{font-weight:650;color:var(--ink)}.exception-item>span:last-child{white-space:nowrap;color:var(--coral);font-variant-numeric:tabular-nums}.exception-item b{font-weight:400;padding:0 5px;color:var(--muted)}.cutoff-note{margin-top:12px!important;color:var(--ink)!important;background:#f1f6f6;padding:9px 11px;border-radius:6px}.sectionhead{display:flex;justify-content:space-between;align-items:center;gap:20px;margin:35px 0 15px}.sectionhead h2{font-size:27px;margin:0}.sectionhead p{font-size:12px;color:var(--muted);margin:4px 0 0}.actions{display:flex;gap:8px}.btn{border:1px solid #cbd7d2;background:var(--paper);padding:8px 13px;border-radius:7px;color:var(--teal);font-size:12px;font-weight:650}.btn:hover{background:var(--teal-light)}.toolbar{display:flex;align-items:end;gap:14px;padding:18px;background:var(--paper);border:1px solid var(--line);border-radius:12px 12px 0 0}.control{display:flex;flex-direction:column;gap:6px;min-width:180px}.control label{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-weight:750}.search{flex:1}.control input,.control select{height:42px;border:1px solid #cdd7d2;border-radius:7px;padding:8px 12px;background:#fff;color:var(--ink);min-width:0;width:100%}.control input::placeholder{color:#7d8a8f}.filters{display:flex;flex-wrap:wrap;gap:8px;background:#fbfcfa;border:1px solid var(--line);border-top:0;padding:12px 18px;align-items:center}.chip{border:1px solid var(--line);background:var(--paper);padding:6px 12px;border-radius:20px;font-size:11px;color:var(--muted);font-weight:650}.chip[aria-pressed="true"]{background:var(--teal);border-color:var(--teal);color:#fff}.results{font-size:11px;color:var(--muted);margin-left:auto}.tablebox{border:1px solid var(--line);border-top:0;border-radius:0 0 12px 12px;background:var(--paper);overflow-x:auto}table{border-collapse:collapse;width:100%;table-layout:fixed;min-width:1050px}col.idcol{width:45px}col.titlecol{width:35%}col.subcol{width:18%}col.notcol{width:17%}th{text-align:left;text-transform:uppercase;font-size:9px;letter-spacing:.09em;color:var(--muted);font-weight:750;background:#f0f3ef;padding:14px 13px;border-bottom:1px solid var(--line)}td{padding:19px 13px;vertical-align:top;border-bottom:1px solid #e8ece7;font-size:12px}tr:last-child td{border-bottom:0}tbody tr:hover{background:#fafcf9}tr.attention-row{background:#fffdf9}tr.spotlight{background:#e9f4ef!important;box-shadow:inset 4px 0 0 var(--teal)}.num{font-size:10px;color:#8a969a;font-variant-numeric:tabular-nums;padding-top:23px}.workshop-title{font-size:13px;font-weight:650;line-height:1.55;color:var(--ink);display:block}.badges{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}.badges:empty{display:none}.badge{display:inline-block;font-size:9px;line-height:1.5;letter-spacing:.01em;font-weight:700;padding:3px 7px;border-radius:4px;background:var(--teal-light);color:var(--teal)}.exception{background:var(--coral-light);color:var(--coral)}.warning{background:var(--gold-light);color:var(--gold)}.fast{background:var(--blue-light);color:var(--blue)}.timebadge{background:#e9f2f3;color:#256779}.date{font-weight:700;font-size:13px;font-variant-numeric:tabular-nums;white-space:nowrap;display:block}.unknown{color:var(--gold);font-size:12px}.sub{display:block;color:var(--muted);font-size:10px;line-height:1.5;margin-top:5px}.unconfirmed{font-size:9px;color:var(--gold)}.sourcecell>a{font-size:10px;font-weight:700}.mutedlink{color:#71847f;font-size:9px}details{margin-top:9px}summary{cursor:pointer;font-size:10px;color:var(--muted)}.detailbody{font-size:10px;color:#566870;line-height:1.65}.detailbody p{margin:8px 0}.detailbody .evidence-links{font-size:9px}.track{margin:10px 0;padding:9px;border:1px solid #dce5ed;border-radius:6px;background:#f6f8fc}.track strong{color:var(--blue);display:block;font-size:10px}.track>span{display:block;margin-top:6px}.empty{display:none;text-align:center;padding:40px;color:var(--muted)}.methodology{margin-top:25px;padding:22px 24px;border:1px solid var(--line);background:#f0f2ec;border-radius:12px}.methodology>summary{font-size:13px;font-weight:700;color:var(--ink)}.methodgrid{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-top:12px}.methodgrid p,.methodgrid li{font-size:12px;color:var(--muted)}.methodgrid ul{padding-left:18px}.footer{display:flex;justify-content:space-between;gap:20px;border-top:1px solid var(--line);padding-top:20px;padding-bottom:32px;margin-top:32px;color:var(--muted);font-size:10px}.footer strong{color:var(--teal)}.noscript{padding:12px;color:var(--gold);background:var(--gold-light);font-size:12px}[hidden]{display:none!important}
@media(min-width:1600px){.wrap{padding-left:60px;padding-right:60px}}@media(max-width:1000px){.wrap{padding:0 24px}.hero{padding-top:34px}.hero-layout{grid-template-columns:1fr;gap:20px}.event{margin:0;font-size:12px}.event strong{font-size:14px}.intro-grid{grid-template-columns:1fr}.stat{padding:17px}.toolbar{flex-wrap:wrap}.search{flex-basis:100%}.control{flex:1}.toplinks{gap:14px}.sectionhead{align-items:start}.exception-item{font-size:12px}.methodgrid{grid-template-columns:1fr;gap:8px}}@media(max-width:580px){.wrap{padding:0 16px}.toplinks a:first-child{display:none}.topinner{gap:10px}.brand{font-size:12px}.toplinks{font-size:10px}.stats{grid-template-columns:1fr 1fr}.stat:nth-child(3){border-left:0;border-top:1px solid var(--line)}.stat:nth-child(4){border-top:1px solid var(--line)}.stat strong{font-size:28px}.stat span{font-size:11px}.panel{padding:20px 16px}.exception-item{font-size:10px}.exception-item>span:last-child{font-size:9px}.sectionhead{flex-direction:column;gap:12px}.control{min-width:130px}.results{width:100%;margin-top:3px}.footer{flex-direction:column;gap:7px}.dek{font-size:14px}.methodology{padding:18px 16px}}
@media print{body{background:white;font-size:10px}.wrap{max-width:none;padding:0}.topbar,.toolbar,.filters,.actions,.toplinks,.exception-list{display:none}.hero{padding:0 0 12px}h1{font-size:28px}.hero-layout{grid-template-columns:1fr 220px;gap:20px}.event{font-size:10px}.event strong{font-size:12px}.stats{margin-top:15px}.stat{padding:9px 12px}.stat strong{font-size:22px}.intro-grid{display:block}.intro-grid .panel{margin-top:8px;padding:12px}.intro-grid .panel:last-child{display:none}.sectionhead{margin:15px 0 8px}.tablebox{overflow:visible;border:0}table{min-width:0;font-size:8px;table-layout:fixed}col.idcol{width:25px}col.titlecol{width:33%}col.subcol{width:18%}col.notcol{width:17%}td,th{padding:8px 5px;font-size:8px}.workshop-title,.date{font-size:9px;white-space:normal}.sub,.sourcecell>a{font-size:8px}.num{padding-top:9px;font-size:8px}.badge{font-size:7px;padding:1px 3px}.badges{gap:3px;margin-top:4px}tr{break-inside:avoid}thead{display:table-header-group}.methodology{display:none}details:not(.methodology){display:block}details>summary{display:none}.detailbody{font-size:8px}.track strong{font-size:8px}.footer{padding-bottom:0}a{color:inherit} @page{size:A4 landscape;margin:12mm}}
</style></head><body>
<div class="topbar"><div class="wrap topinner"><div class="brand"><span>AAAI—27</span> RESEARCH FIELD GUIDE</div><nav class="toplinks" aria-label="Primary"><a href="/">Chongyu Zhu ↗</a><a href="#workshops">All workshops</a><a href="#methodology">Sources & method</a><a href="__PROGRAM__" target="_blank" rel="noopener noreferrer">Official program ↗</a></nav></div></div>
<main class="wrap">
<header class="hero"><div class="hero-layout"><div><div class="eyebrow">Submission cycle 2026–2027 · Checked October 17, 2026</div><h1>Every workshop.<br><span>Every verified deadline.</span></h1><p class="dek">A source-linked directory of the 45 named workshops currently on AAAI’s official AAAI-27 list. Paper submission deadlines and acceptance notifications, with exceptions and missing dates made explicit.</p></div><div class="event"><small>THE 41ST AAAI CONFERENCE</small><strong>Montréal, Canada</strong>Workshops: February 22–23, 2027<br><small>Palais des congrès de Montréal</small></div></div>
<div class="stats" aria-label="Coverage statistics"><div class="stat"><strong>45</strong><span>Named workshops checked</span></div><div class="stat"><strong>38</strong><span>Both dates on workshop websites</span></div><div class="stat"><strong>9</strong><span>With nonstandard calendar dates</span></div><div class="stat"><strong>7</strong><span>With at least one Unknown date</span></div></div></header>
<section class="intro-grid" aria-label="Deadline findings"><div class="panel"><div class="eyebrow">The general timetable</div><h2 style="margin-top:8px">The dates are not uniform.</h2><p>AAAI’s program gives the following baseline, while explicitly allowing workshop-specific submission and notification dates:</p><div class="baseline"><div class="baseline-item">PAPER SUBMISSION<strong>Nov 20, 2026</strong></div><div class="arrow">→</div><div class="baseline-item">AUTHOR NOTIFICATION<strong>Dec 02, 2026</strong></div></div><p><a href="__PROGRAM__" target="_blank" rel="noopener noreferrer">Read the official date policy ↗</a></p><div class="scope"><h3>Coverage: 45 listed, 47 mentioned</h3><p>The official overview says “47 workshops,” but its detailed program currently provides 45 named entries. This report includes all 45. The remaining two cannot be identified from that list and are not invented or counted as checked.</p><p class="tiny">“Unknown” means the date is not explicitly published or could not be verified on the current workshop website. Unknown fields stay Unknown. The general AAAI dates are never substituted in individual rows.</p></div></div>
<div class="panel"><div class="eyebrow">Calendar exceptions · Regular tracks</div><h2 style="margin-top:8px">Dates to plan around</h2><div class="exception-list">__EXCEPTIONS__</div><p class="cutoff-note"><strong>Explicit custom cutoff:</strong> Eval AI Scientists closes Nov 20 at <strong>06:00 UTC</strong>. Other missing cutoff times or timezones remain <strong>Unknown</strong>.</p></div></section>
<section id="workshops" aria-labelledby="directory-title"><div class="sectionhead"><div><div class="eyebrow">THE COMPLETE PUBLISHED LIST</div><h2 id="directory-title">Workshop directory</h2><p>Dates include years. Expand evidence notes for source conflicts, fast tracks, and unavailable details.</p></div><div class="actions"><button class="btn" id="csvButton" type="button">Export CSV ↓</button><button class="btn" id="printButton" type="button">Print / Save PDF</button></div></div>
<noscript><div class="noscript">All 45 workshops are available below. Enable JavaScript to use search, filters, sorting, and CSV export.</div></noscript>
<div class="toolbar"><div class="control search"><label for="search">Find a workshop</label><input id="search" type="search" placeholder="Search title, acronym, or notes…" autocomplete="off"></div><div class="control"><label for="sort">Sort by</label><select id="sort"><option value="official">Official list order</option><option value="submission">Submission date · earliest first</option><option value="notification">Notification date · earliest first</option><option value="title">Title · A–Z</option></select></div><button class="btn" id="resetButton" type="button" style="height:42px">Reset</button></div>
<div class="filters" role="group" aria-label="Filter workshops"><button type="button" class="chip" data-filter="all" aria-pressed="true">All 45</button><button type="button" class="chip" data-filter="exception" aria-pressed="false">Different dates · 9</button><button type="button" class="chip" data-filter="time" aria-pressed="false">Custom cutoffs · 1</button><button type="button" class="chip" data-filter="incomplete" aria-pressed="false">Unknown dates · 7</button><button type="button" class="chip" data-filter="conflict" aria-pressed="false">Source mismatches · 2</button><button type="button" class="chip" data-filter="fasttrack" aria-pressed="false">Fast tracks · 2</button><span class="results" id="resultCount" role="status" aria-live="polite">Showing 45 of 45 workshops</span></div>
<div class="tablebox"><table aria-label="AAAI-27 workshop submission and notification dates"><colgroup><col class="idcol"><col class="titlecol"><col class="subcol"><col class="notcol"><col></colgroup><thead><tr><th scope="col">No.</th><th scope="col">Workshop title</th><th scope="col">Paper submission</th><th scope="col">Acceptance notification</th><th scope="col">Sources & evidence</th></tr></thead><tbody id="tableBody">__TABLE__</tbody></table><div class="empty" id="emptyState">No workshops match this search. Try another keyword or reset the filters.</div></div></section>
<details class="methodology" id="methodology" open><summary>Sources, interpretation & coverage</summary><div class="methodgrid"><div><h3>What was checked</h3><p>Checked on <strong>October 17, 2026</strong>. The inventory comes from the <a href="__OFFICIAL__" target="_blank" rel="noopener noreferrer">official AAAI-27 workshop program list</a>. Every listed workshop link was checked against the shared dataset. Edition-specific CFP pages were followed where available; Pages requiring JavaScript rendering are checked in a browser when needed. Missing, inaccessible, and unannounced workshop dates remain Unknown. General AAAI dates and reference-only dates are retained only in source notes; they never fill an Unknown field.</p><p>The <a href="__PROGRAM__" target="_blank" rel="noopener noreferrer">program overview</a> supplies the general November 20 / December 2 baseline and permits workshop exceptions. The <a href="__TIMETABLE__" target="_blank" rel="noopener noreferrer">organizer timetable</a> uses AoE (UTC−12), but individual sites may specify another zone or omit the cutoff. Per-workshop missing zones are marked Unknown.</p></div><div><h3>How to read the dates</h3><ul><li>Regular paper deadlines appear in the two main date columns. Separate fast tracks appear inside evidence notes.</li><li>Current workshop CFP dates take precedence over the general baseline. Social Simulation and EAIM conflict with their individual AAAI listings; both versions are recorded.</li><li>“Both dates on workshop websites” counts only dates explicitly found on the current workshop sites. Dates available only in AAAI’s list, missing dates, inaccessible sources, and unannounced dates are not treated as confirmed workshop dates.</li><li>Old-edition dates, reviewer deadlines, registration dates, and camera-ready dates are excluded from the main columns.</li><li>This is a dated research snapshot. Source links let you check for later changes before submitting.</li></ul></div></div></details>
<footer class="footer"><span><strong>AAAI-27 / Workshop deadline directory</strong> · DORL shared workshop directory · Checked every two days</span><span>45 named entries · Checked October 17, 2026 · All dates refer to the 2026–2027 submission cycle</span></footer>
</main>
<script id="workshopData" type="application/json">__DATA__</script>
<script>
'use strict';
const workshops=JSON.parse(document.getElementById('workshopData').textContent);
const body=document.getElementById('tableBody');
const rowNodes=new Map(Array.from(body.rows).map(r=>[Number(r.dataset.id),r]));
const search=document.getElementById('search'),sort=document.getElementById('sort');
let activeFilter='all',shown=workshops.slice();
const filters={all:()=>true,exception:r=>r.exception,time:r=>r.flags.includes('time'),incomplete:r=>r.incomplete,conflict:r=>r.flags.includes('conflict'),fasttrack:r=>r.fastTracks.length>0};
function render(){const q=search.value.trim().toLowerCase();shown=workshops.filter(r=>filters[activeFilter](r)&&(!q||[r.title,...r.notes,JSON.stringify(r.fastTracks)].join(' ').toLowerCase().includes(q)));const key=sort.value;shown.sort((a,b)=>key==='official'?a.id-b.id:key==='title'?a.title.localeCompare(b.title):(a[key]||'9999').localeCompare(b[key]||'9999')||a.id-b.id);rowNodes.forEach(node=>{node.hidden=true;node.classList.remove('spotlight')});shown.forEach(r=>{const node=rowNodes.get(r.id);node.hidden=false;body.appendChild(node)});document.getElementById('resultCount').textContent=`Showing ${shown.length} of ${workshops.length} workshops`;document.getElementById('emptyState').style.display=shown.length?'none':'block';document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===activeFilter)))}
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{activeFilter=b.dataset.filter;render()}));
search.addEventListener('input',render);sort.addEventListener('change',render);
document.getElementById('resetButton').addEventListener('click',()=>{search.value='';sort.value='official';activeFilter='all';render()});
document.querySelectorAll('[data-focus]').forEach(a=>a.addEventListener('click',()=>{search.value='';activeFilter='all';render();const row=rowNodes.get(Number(a.dataset.focus));row.classList.add('spotlight');setTimeout(()=>row.scrollIntoView({behavior:'smooth',block:'center'}),40)}));
document.getElementById('printButton').addEventListener('click',()=>{const openStates=Array.from(document.querySelectorAll('tbody details')).map(d=>[d,d.open]);openStates.forEach(([d])=>d.open=true);window.print();openStates.forEach(([d,v])=>d.open=v)});
document.getElementById('csvButton').addEventListener('click',()=>{const headers=['Official list number','Workshop title','Submission date (ISO)','Submission cutoff','Submission timezone','Notification date (ISO)','Notification qualifier','Date status','Source','Workshop website','Notes','Fast tracks','Checked date'];const cells=shown.map(r=>[r.id,r.title,r.submission||'Unknown',r.submissionTime,r.submissionZone,r.notification||'Unknown',r.notificationQualifier,r.incomplete?'Unknown date':r.exception?'Different dates':'Published',r.source,r.website,r.notes.join(' | '),r.fastTracks.map(t=>`${t.label}: submit ${t.submission||'Unknown'}, decision ${t.notification||'Unknown'}, ${t.zone}. ${t.note}`).join(' | '),r.checked]);const quote=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const csv='\ufeff'+[headers,...cells].map(r=>r.map(quote).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='aaai27-workshop-deadlines-2026-10-17.csv';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)});
</script></body></html>'''
for key,val in {'__PROGRAM__':PROGRAM,'__OFFICIAL__':OFFICIAL,'__TIMETABLE__':TIMETABLE,'__EXCEPTIONS__':EXCEPTIONS,'__TABLE__':TABLE,'__DATA__':DATA}.items():
    TEMPLATE=TEMPLATE.replace(key,val)

cutoffs=[]
for r in rows:
    if 'time' in r['flags'] and r['submission'] and r['submissionTime'] and r['submissionZone']!='Unknown':
        cutoffs.append(f'<strong>{esc(r.get("shortTitle",r["title"]))}</strong>: {fmt(r["submission"])} at <strong>{esc(r["submissionTime"])} {esc(r["submissionZone"])}</strong>')
start=TEMPLATE.index('<p class="cutoff-note">')
end=TEMPLATE.index('</p>',start)+4
cutoff_text='; '.join(cutoffs)+'. ' if cutoffs else ''
TEMPLATE=TEMPLATE[:start]+f'<p class="cutoff-note">{cutoff_text}Missing cutoff times or timezones remain <strong>Unknown</strong>.</p>'+TEMPLATE[end:]

for old,new in {
 'October 17, 2026':CHECKED_LONG,
 'OCTOBER 17, 2026':CHECKED_LONG.upper(),
 '2026-10-17':CHECKED_ISO,
 '<strong>45</strong>':f'<strong>{COUNT}</strong>',
 '<strong>38</strong>':f'<strong>{COMPLETE}</strong>',
 '<strong>9</strong>':f'<strong>{EXCEPTION_COUNT}</strong>',
 '<strong>7</strong>':f'<strong>{UNKNOWN_COUNT}</strong>',
 '45 named':f'{COUNT} named',
 'the 45':f'the {COUNT}',
 'all 45':f'all {COUNT}',
 'All 45':f'All {COUNT}',
 'All 45 workshops':f'All {COUNT} workshops',
 '45 of 45':f'{COUNT} of {COUNT}',
 'all 45.':f'all {COUNT}.',
 'includes all 45':f'includes all {COUNT}',
 'provides 45 named entries':f'provides {COUNT} named entries',
 'Different dates · 9':f'Different dates · {EXCEPTION_COUNT}',
 'Custom cutoffs · 1':f'Custom cutoffs · {TIME_COUNT}',
 'Unknown dates · 7':f'Unknown dates · {UNKNOWN_COUNT}',
 'Source mismatches · 2':f'Source mismatches · {CONFLICT_COUNT}',
 'Fast tracks · 2':f'Fast tracks · {FAST_COUNT}',
}.items():
    TEMPLATE=TEMPLATE.replace(old,new)
mentioned=payload.get('officialMentionedCount')
if mentioned==COUNT:
    start=TEMPLATE.index('<h3>Coverage:')
    end=TEMPLATE.index('<p class="tiny">',start)
    TEMPLATE=TEMPLATE[:start]+f'<h3>Coverage: {COUNT} named workshops</h3><p>All named entries in the official list are included.</p>'+TEMPLATE[end:]
elif mentioned is not None:
    TEMPLATE=TEMPLATE.replace('47 mentioned',f'{mentioned} mentioned').replace('“47 workshops”',f'“{mentioned} workshops”').replace('The remaining two cannot be identified from that list and are not invented or counted as checked.',f'The remaining {max(0,mentioned-COUNT)} cannot be identified from that list and are not counted as checked.')
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(TEMPLATE,encoding='utf-8')
print(json.dumps({'output':str(args.output),'workshops':COUNT,'complete':COMPLETE,'unknown':UNKNOWN_COUNT,'checked':CHECKED_ISO}))
