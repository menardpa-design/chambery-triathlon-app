#!/usr/bin/env python3
"""Génère le plan hebdo (HTML imprimable) à partir de chambery-tri.html.
Usage : python3 plan_pdf.py chambery-tri.html SEMAINE sortie.html [notes.json]  (puis impression PDF via Playwright)"""
import re, json, sys, datetime, html
src, week, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
# Notes libres par semaine (optionnel) : JSON {"46": ["<b>Titre :</b> texte", ...]}
NOTES = json.load(open(sys.argv[4], encoding='utf-8')) if len(sys.argv) > 4 else {}
t = open(src, encoding='utf-8').read()
W = json.loads(re.search(r'const WEEKS=(\{.*?\});', t).group(1))
CRS = json.loads(re.search(r'const CRSHEET=(\{.*?\});', t).group(1))
CH = json.loads(re.search(r'const CHANGES=(\[.*?\]);', t).group(1))
logo = re.search(r'<img class="logo"[^>]*src="(data:image/png;base64,[^"]+)"', t).group(1)
# Créneaux codés en dur dans la page (JS) puis surchargés par l'onglet Créneaux du Sheet
CR = {}
blk = re.search(r'const CRENEAUX=\{(.*?)\n\};', t, re.S).group(1)
for k, body in re.findall(r"'([^']+)':\{([^}]*)\}", blk):
    CR[k] = dict(re.findall(r"(\w+):'([^']*)'", body))
for k, v in CRS.items(): CR[k] = {**CR.get(k, {}), **v}
# Annonces affichées dans l'appli
anns = []
ab = re.search(r'const ANNONCES=\[(.*?)\n\];', t, re.S)
if ab:
    for m in re.finditer(r"\{id:'[^']*?(\d{4}-\d\d-\d\d)'.*?titre:'([^']*)'.*?items:\[(.*?)\]\}", ab.group(1), re.S):
        items = re.findall(r"\['([^']*)','([^']*)'\]", m.group(3))
        anns.append((datetime.date.fromisoformat(m.group(1)), m.group(2), items))
EXTRA = [{'d':4,'s':'other','slot':'','lvl':'all','x':'Renforcement et course'},
         {'d':6,'s':'swim','slot':'Matin','lvl':'all','x':'','from':45}]

mon = datetime.date.fromisocalendar(2026 if week >= 30 else 2027, week, 1)
days = [mon + datetime.timedelta(i) for i in range(7)]
MOIS = 'janvier février mars avril mai juin juillet août septembre octobre novembre décembre'.split()
JOURS = 'LUNDI MARDI MERCREDI JEUDI VENDREDI SAMEDI DIMANCHE'.split()
fd = lambda d: f"{'1er' if d.day == 1 else d.day} {MOIS[d.month-1]}"
e = html.escape
sess = [s for s in W[str(week)] if s['x'].strip() not in ('_', '\\_')]
for x in EXTRA:
    if (not x.get('from') or week >= x['from']) and not any(s['d']==x['d'] and s['s']==x['s'] and s['slot']==x['slot'] for s in sess):
        sess.append(x)

def lieu(s):
    if s['s'] != 'swim': return ''
    return 'Piscine du Stade' if week >= 45 and s['d'] in (2, 4) and s['slot'] == 'Matin' else 'Piscine de Buisson Rond'

def cell(s, date):
    key = f"{s['d']}-{s['s']}-{s['slot']}"
    ci = dict(CR.get(f"{key}-{s['lvl']}") or CR.get(key) or {})
    grp = (CR.get(f"{key}-{s['lvl']}") or {}).get('grp', '')
    ch = next((c for c in CH if c['date'] == date.isoformat() and c['s'] == s['s'] and (not c.get('slot') or c['slot'] == s['slot']) and (not c.get('grp') or not grp or c['grp'].lower() == grp.lower())), None)
    if ch and ch.get('off'): return '<span class="off">' + ('NATATION ANNULÉE' if s['s']=='swim' else 'SÉANCE ANNULÉE') + '</span>'
    if ch: ci.update({k: ch[k] for k in ('h', 'coach', 'lieu') if ch.get(k)})
    auto = s['s'] == 'bike' or (s['s'] == 'run' and s['d'] in (6, 0))
    lines = s['x'].split('\n')
    while lines and (not lines[0].strip() or (auto and re.fullmatch(r'(en )?autonomie', lines[0].strip(), re.I))): lines.pop(0)
    txt = '\n'.join(l.rstrip() for l in lines).strip()
    txt = re.sub(r'\n{2,}', '\n', txt)
    o = ''
    if ch and ch.get('msg'): o += f'<span class="msg">{e(ch["msg"].upper())}</span>'
    if grp: o += f'<div class="grp">{e(grp.upper())}</div>'
    if auto: o += '<span class="auto">EN AUTONOMIE</span>'
    else:
        h = re.sub(r'\s*·\s*Piste$', '', ci.get('h', ''))
        lv = ci.get('lieu') or ('Piste Mas Barral' if 'Piste' in ci.get('h', '') else lieu(s))
        info = ' · '.join(x for x in (h, ci.get('coach', ''), lv) if x)
        if info: o += f'<div class="info">{e(info)}</div>'
    if txt:
        first, _, rest = txt.partition('\n')
        o += f'<div class="t">{e(first)}</div>' + (f'<div class="x">{e(rest)}</div>' if rest else '')
    return o

rows = [('swim', 'Matin', 'NATATION', 'matin', 'sw'), ('swim', 'Midi', 'NATATION', 'midi', 'sw'), ('swim', 'Soir', 'NATATION', 'soir', 'sw'),
        ('bike', '', 'VÉLO', '', 'bk'), ('run', '', 'COURSE<br>À PIED', '', 'rn'), ('other', '', 'AUTRE', '', 'ot')]
body = ''
for sp, slot, lab, sub, cls in rows:
    tds = ''
    for i, date in enumerate(days):
        d = (i + 1) % 7
        cs = [s for s in sess if s['d'] == d and s['s'] == sp and (s['slot'] == slot or sp != 'swim')]
        tds += '<td>' + '<hr>'.join(cell(s, date) for s in cs) + '</td>'
    body += f'<tr class="{cls}"><th><b>{lab}</b>{"<br><small>"+sub+"</small>" if sub else ""}</th>{tds}</tr>\n'

notes = list(NOTES.get(str(week), []))
for dt, titre, items in anns:
    if mon <= dt <= days[-1]:
        notes.append(f"<b>{e(titre.replace('📣','').strip())} à partir du {fd(dt)} :</b> " + ' ; '.join(f"{e(a)} → {e(b)}" for a, b in items) + '.')
head = ''.join(f'<th>{j}<br><span>{d:%d/%m}</span></th>' for j, d in zip(JOURS, days))
doc = f'''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Plan semaine {week}</title>
<link href="https://fonts.googleapis.com/css2?family=Exo+2:wght@700;800&family=Barlow:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
@page{{size:A4 landscape;margin:8mm}}
*{{box-sizing:border-box}}body{{margin:0;font:400 7.4pt/1.32 Barlow,Inter,sans-serif;color:#111}}
.top{{background:#000;color:#fff;border-radius:7px;display:flex;align-items:center;justify-content:space-between;padding:7px 12px}}
.top img{{height:30px}}.top h1{{font:800 15pt/1 "Exo 2",Inter,sans-serif;margin:0;text-align:right}}
.top p{{margin:3px 0 0;color:#ED68A3;font-weight:700;font-size:8pt;text-align:right}}
.note{{background:#fde4ef;border-left:4px solid #ED68A3;border-radius:4px;padding:5px 9px;margin:6px 0;font-size:7.6pt}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:6px}}
thead{{display:table-header-group}}tr{{break-inside:avoid}}
thead th{{background:#000;color:#fff;font:800 8.5pt "Exo 2",Inter,sans-serif;padding:4px 2px;border:1px solid #999}}
thead th span{{color:#ED68A3;font-size:7pt}}thead th:first-child{{font-size:6.5pt;width:62px}}
td,tbody th{{border:1px solid #999;vertical-align:top;padding:4px 5px}}
tbody th{{text-align:left;vertical-align:middle;font:800 8pt "Exo 2",Inter,sans-serif}}tbody th small{{font:600 7pt Barlow,sans-serif}}
.sw td,.sw th{{background:#d6f3f9}}.bk td,.bk th{{background:#fdf6c3}}.rn td,.rn th{{background:#d9f5d6}}.ot td,.ot th{{background:#fbe3cc}}
.info{{font-weight:600;color:#444;font-size:6.9pt;margin-bottom:2px}}.t{{font-weight:600}}.x{{white-space:pre-line}}
.auto{{display:inline-block;background:#ED68A3;color:#111;font-weight:700;border-radius:3px;padding:1px 5px;margin-bottom:3px}}
.msg{{display:inline-block;border:1px solid #ED68A3;color:#111;font-weight:700;border-radius:3px;padding:1px 5px;margin-bottom:3px}}
.off{{display:inline-block;background:#111;color:#fff;font-weight:700;border-radius:3px;padding:3px 7px}}
.grp{{color:#c2185b;font-weight:800}}hr{{border:0;border-top:1px dashed #c2185b;margin:5px 0}}
</style>
<div class="top"><img src="{logo}" alt="Chambéry triathlon"><div><h1>PLAN DE LA SEMAINE {week}</h1>
<p>du lundi {fd(days[0])} au dimanche {fd(days[-1])} {days[-1].year}</p></div></div>
{''.join(f'<div class="note">⚠ {n}</div>' for n in notes)}
<table><thead><tr><th>SPORT /<br>JOUR</th>{head}</tr></thead><tbody>
{body}</tbody></table></html>'''
open(out, 'w', encoding='utf-8').write(doc)
print('ok', out, len(sess), 'séances')
