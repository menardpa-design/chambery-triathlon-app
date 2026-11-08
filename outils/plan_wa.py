#!/usr/bin/env python3
"""Planning hebdo « WhatsApp » (A4 portrait, 2 pages) à partir de chambery-tri.html.
Usage : python3 plan_wa.py chambery-tri.html SEMAINE sortie.html [extras.json]
extras.json (optionnel) : {"46": {"badge": ["SEMAINE DE DÉCHARGE", "Récup", "sous-titre"],
  "sub": "texte après les dates", "titles": {"1-swim-Midi": "Technique · respiration"},
  "days": {"3": "Férié : pas d'entraînement"}, "notes": {"6": "Après-midi et soir : bénévolat Chambérienne"},
  "callout": "texte du bandeau jaune", "timeline": {"46": "Décharge · La Chambérienne"}}}
Puis : node pdf.js sortie.html sortie.pdf"""
import re, json, sys, datetime, html
src, week, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
X = (json.load(open(sys.argv[4], encoding='utf-8')) if len(sys.argv) > 4 else {}).get(str(week), {})
t = open(src, encoding='utf-8').read()
W = json.loads(re.search(r'const WEEKS=(\{.*?\});', t).group(1))
CRS = json.loads(re.search(r'const CRSHEET=(\{.*?\});', t).group(1))
CH = json.loads(re.search(r'const CHANGES=(\[.*?\]);', t).group(1))
SEASON = json.loads(re.search(r'const SEASON=(\[.*?\]);', t).group(1))
logo = re.search(r'<img class="logo"[^>]*src="(data:image/png;base64,[^"]+)"', t).group(1)
CR = {}
for k, body in re.findall(r"'([^']+)':\{([^}]*)\}", re.search(r'const CRENEAUX=\{(.*?)\n\};', t, re.S).group(1)):
    CR[k] = dict(re.findall(r"(\w+):'([^']*)'", body))
for k, v in CRS.items(): CR[k] = {**CR.get(k, {}), **v}
e = html.escape
yr = 2026 if week >= 30 else 2027
mon = datetime.date.fromisocalendar(yr, week, 1)
days = [mon + datetime.timedelta(i) for i in range(7)]
MOIS = 'janvier février mars avril mai juin juillet août septembre octobre novembre décembre'.split()
JOURS = 'LUNDI MARDI MERCREDI JEUDI VENDREDI SAMEDI DIMANCHE'.split()
Jc = [j.capitalize() for j in JOURS]
fd = lambda d: f"{'1er' if d.day == 1 else d.day}"
SE = next((s for s in SEASON if s['w'] == week), {})

LIEUX = {'Piscine Buisson rond': 'BR', 'Piscine de Buisson Rond': 'BR', 'Piscine du Stade': 'ST', 'Piste Mas Barral': 'MB',
         'Stade Mas-Barral': 'MB', 'Stade de Mager': 'MG', 'Stade Mager': 'MG', 'Tennis de Chambéry': 'TC'}
NOMS = {'BR': 'Piscine Buisson Rond', 'ST': 'Piscine du Stade', 'MB': 'Stade Mas-Barral', 'MG': 'Stade Mager', 'TC': 'Tennis de Chambéry'}
def code(lieu):
    if not lieu: return ''
    for k, v in LIEUX.items():
        if k.lower() in lieu.lower(): return v
    if 'challes' in lieu.lower(): NOMS['CL'] = "Plan d'eau de Challes"; return 'CL'
    return ''

sess = [s for s in W[str(week)] if s['x'].strip() not in ('_', '\\_')]
if week >= 45 and not any(s['d'] == 6 and s['s'] == 'swim' for s in sess):
    sess.append({'d': 6, 's': 'swim', 'slot': 'Matin', 'lvl': 'all', 'x': ''})
if not any(s['d'] == 4 and s['s'] == 'other' for s in sess):
    sess.append({'d': 4, 's': 'other', 'slot': '', 'lvl': 'all', 'x': 'Renforcement'})

def info(s):
    key = f"{s['d']}-{s['s']}-{s['slot']}"
    ci = dict(CR.get(f"{key}-{s['lvl']}") or CR.get(key) or {})
    grp = ci.get('grp', '')
    date = days[(s['d'] - 1) % 7]
    ch = next((c for c in CH if c['date'] == date.isoformat() and c['s'] == s['s'] and (not c.get('slot') or c['slot'] == s['slot'])
               and (not c.get('grp') or not grp or c['grp'].lower() == grp.lower())), None)
    if ch: ci.update({k: ch[k] for k in ('h', 'coach', 'lieu') if ch.get(k)})
    ci['h'] = re.sub(r'(\d+)h00\b', r'\1h', re.sub(r'\s*·\s*Piste$', '', ci.get('h', ''))).replace(' - ', ' – ').replace('H', 'h')
    return ci, ch, grp

def lines(s):
    L = [l.rstrip() for l in s['x'].split('\n')]
    while L and (not L[0].strip() or re.fullmatch(r'(en )?autonomie', L[0].strip(), re.I)): L.pop(0)
    return L

def dist(L):
    for l in reversed(L):
        m = re.fullmatch(r'\s*(\d{4})\s*m?\s*', l)
        if m: return m.group(1) + ' m'
    return ''

def swim_meta(s):
    L = lines(s); key = f"{s['d']}-{s['s']}-{s['slot']}"
    title = X.get('titles', {}).get(key)
    first = L[0].strip() if L else ''
    if not title: title = first if first and not re.match(r'^\d', first) else 'Séance'
    sub = L[1].strip().strip('()') if len(L) > 1 and L[1].strip().startswith('(') else ''
    tl = (title + ' ' + sub).lower()
    kind = 'int' if re.search(r'test|intens|seuil|vo2|vma', tl) else 'tec' if re.search(r'techn|vitesse|respi|relâch', tl) else 'aer'
    txt = ' '.join(L).lower()
    eq = [n for n, rx in (('Palmes', r'palmes'), ('Pull-buoy', r'\bpull\b'), ('Plaquettes', r'plaq'), ('Tuba', r'tuba')) if re.search(rx, txt)]
    return title, sub, kind, dist(L), eq

def run_meta(s):
    L = [l for l in lines(s) if l.strip()]
    return L

off_days = {int(k): v for k, v in X.get('days', {}).items()}
notes = {int(k): v for k, v in X.get('notes', {}).items()}
used = set()

def swim_card(s):
    ci, ch, _ = info(s); c = code(ci.get('lieu') or ('Piscine du Stade' if week >= 45 and s['d'] in (2, 4, 6) and s['slot'] == 'Matin' else 'Piscine Buisson rond'))
    used.add(c)
    if s['d'] in off_days or (ch and ch.get('off')):
        msg = off_days.get(s['d']) or ch.get('msg') or 'Séance annulée'
        return f'<div class="card off"><div class="ch"><b>{e(ci["h"])}</b><i>{c}</i></div><div class="ti">Annulé</div><div class="nt">{e(msg)}</div></div>'
    title, sub, kind, d, eq = swim_meta(s)
    if not s['x'].strip(): title, kind = 'Séance en construction', 'aer'
    return (f'<div class="card {kind}"><div class="ch"><b>{e(ci["h"])}</b><i>{c}</i></div><div class="ti">{e(title)}</div>'
            + (f'<span class="m">{e(d)}</span>' if d else '') + (f'<div class="nt">{e(sub)}</div>' if sub else '') + '</div>')

def run_card(s):
    ci, ch, grp = info(s); c = code(ci.get('lieu', '')); used.add(c)
    auto = s['s'] == 'bike' or (s['s'] == 'run' and s['d'] in (6, 0))
    L = run_meta(s)
    if s['d'] in off_days and not auto:
        return f'<div class="card rn off"><div class="ch"><b>{e(ci["h"])}</b><i>{c}</i></div><div class="ti">Annulé</div><div class="nt">{e(off_days[s["d"]])}</div></div>'
    if ch and ch.get('off'):
        return f'<div class="card rn off"><div class="ch"><b>{e(ci["h"])}</b><i>{c}</i></div><div class="ti">Annulé</div></div>'
    if auto:
        head = L[0] if L else ''
        more = [l.strip() for l in L[1:] if l.strip().lower() not in ('ou',) and not l.lower().startswith('echelle')]
        return f'<div class="auto"><small>EN AUTONOMIE</small><b>{e(head)}</b><span>{e(" · ".join(more[:2]))}</span></div>'
    title = X.get('titles', {}).get(f"{s['d']}-{s['s']}-{s['slot']}") or grp or ('Renforcement' if s['s'] == 'other' else (L[0] if L else ''))
    rest = L if grp or s['s'] == 'other' else L[1:]
    sub = ' · '.join(x for x in [ci.get('coach', ''), ci.get('lieu', '')] if x)
    return f'<div class="card rn"><div class="ch"><b>{e(ci["h"])}</b><i>{c}</i></div><div class="ti">{e(title)}</div><div class="nt">{e(sub)}</div></div>'

rows = ''
for i, date in enumerate(days):
    d = (i + 1) % 7
    sw = sorted([s for s in sess if s['d'] == d and s['s'] == 'swim'], key=lambda s: ['Matin', 'Midi', 'Soir'].index(s['slot']))
    bk = [s for s in sess if s['d'] == d and s['s'] == 'bike']
    rn = sorted([s for s in sess if s['d'] == d and s['s'] in ('run', 'other')], key=lambda s: (s['s'] == 'other', s['lvl'] != 'deb'))
    if d in off_days and not sw:
        sw_html = f'<div class="card off"><div class="ti">Férié</div><div class="nt">{e(off_days[d])}</div></div>'
    else:
        sw_html = ''.join(swim_card(s) for s in sw) or '<span class="dash">–</span>'
    bk_html = ''.join(run_card(s) for s in bk) or '<span class="dash">–</span>'
    rn_html = ''.join(run_card(s) for s in rn) or '<span class="dash">–</span>'
    nt = f'<div class="dnote">⚠ {e(notes[d])}</div>' if d in notes else ''
    rows += f'<tr class="{"alt" if i % 2 else ""}"><th>{JOURS[i]}<small>{date.day:02d}/{date.month:02d}</small></th><td>{sw_html}{nt}</td><td>{bk_html}</td><td>{rn_html}</td></tr>'

# Page 2 : détail
def short_day(s):
    ci, _, _ = info(s)
    h = ci['h'].split('–')[0].strip().replace('h', 'H')
    return f"{Jc[(s['d'] - 1) % 7].upper()} {h}"

sw_all = sorted([s for s in sess if s['s'] == 'swim' and s['x'].strip() and s['d'] not in off_days and not (info(s)[1] or {}).get('off')],
                key=lambda s: ((s['d'] - 1) % 7, ['Matin', 'Midi', 'Soir'].index(s['slot'])))
swc = ''
for s in sw_all:
    title, sub, kind, d, eq = swim_meta(s)
    swc += (f'<div class="dc {kind}"><div class="dh"><b>{e(short_day(s))}</b><span>{e(title)}</span></div>'
            + (f'<span class="m">{e(d)}</span>' if d else '') + '<div class="eq">' + ''.join(f'<i>{q}</i>' for q in eq) + '</div></div>')

def detail(s, label):
    L = lines(s)
    body = re.sub(r'\n{3,}', '\n\n', '\n'.join(L)).strip()
    ci, _, grp = info(s)
    right = 'En autonomie' if (s['s'] == 'bike' or s['d'] in (6, 0)) else ' · '.join(x for x in [ci.get('lieu', '')] if x)
    return f'<div class="dc rnd"><div class="dh"><b>{e(label)}</b><span>{e(right)}</span></div><pre>{e(body)}</pre></div>'

bkc = ''.join(detail(s, f"{Jc[(s['d']-1)%7].upper()} · {lines(s)[0].upper() if lines(s) else ''}"[:60]) for s in sorted([s for s in sess if s['s'] == 'bike'], key=lambda s: (s['d'] - 1) % 7))
rnl = sorted([s for s in sess if s['s'] == 'run'], key=lambda s: ((s['d'] - 1) % 7, s['lvl'] != 'deb'))
def rlabel(s):
    ci, _, grp = info(s)
    tt = X.get('titles', {}).get(f"{s['d']}-{s['s']}-{s['slot']}")
    return f"{short_day(s)} · {(grp or (tt.split(' · ')[0] if tt else '') or ('FOOTING' if s['d'] in (6,0) else 'SÉANCE')).upper()}"
rnc = ''.join(detail(s, rlabel(s)) for s in rnl)

# Frise saison
cyc = [('CYCLE 1 · PRÉPA GÉNÉRALE', 'Sept → déc', 37, 51), ('CYCLE 2 · PRÉPA SPÉCIFIQUE', 'Janv → avril', 1, 14), ('CYCLE 3 · COMPÉTITION', 'Avril → août', 15, 35)]
order = list(range(37, 53)) + list(range(1, 36))
pos = order.index(week) if week in order else 0
frise = '<div class="cy">' + ''.join(f'<div class="{"on" if (a <= week <= b) else ""}"><b>{n}</b><small>{s}</small></div>' for n, s, a, b in cyc) + '</div>'
ticks = ''.join(f'<i class="{"cur" if w == week else ("dc2" if any(x["w"]==w and x["meso"].lower().startswith("décharge") for x in SEASON) else "")}"></i>' for w in order)
nxt = []
for w in [week, week + 1, week + 2]:
    se = next((x for x in SEASON if x['w'] == w), None)
    if not se: continue
    lab = X.get('timeline', {}).get(str(w)) or (se['meso'] + (f" · {se['club']}" if se['club'] else ''))
    nxt.append(f'<span><b>S{w}</b> {e(lab)}</span>')

badge = X.get('badge') or (['SEMAINE DE DÉCHARGE', 'Récupération', ''] if SE.get('meso', '').lower().startswith('décharge') else None)
badge_html = f'<div class="badge"><small>{e(badge[0])}</small><b>{e(badge[1])}</b><small>{e(badge[2])}</small></div>' if badge else ''
chips = [('Cycle 1' if week >= 37 or week < 1 else 'Cycle', 'Préparation générale (sept → déc)'), ('Mésocycle', SE.get('meso', '')), ('Vélo', SE.get('velo', '')), ('CAP', SE.get('cap', '').split('\n')[0])]
chips_html = ''.join(f'<span><b>{e(a)}</b> · {e(b)}</span>' for a, b in chips if b)
leg_lieux = ''.join(f'<div><i>{k}</i>{e(NOMS[k])}</div>' for k in ['BR', 'MB', 'ST', 'MG', 'TC', 'CL'] if k in used and k in NOMS)
sub = X.get('sub', '')
title_dates = f"Du lundi {fd(days[0])} au dimanche {fd(days[6])} {MOIS[days[6].month-1]} {days[6].year}" + (f' · {sub}' if sub else '')
callout = X.get('callout', "Ces entraînements peuvent être modifiés en cours de semaine : suivez les groupes WhatsApp du club.")

doc = f'''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Planning adultes S{week}</title>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700;800&family=Barlow:wght@400;500;600&display=swap" rel="stylesheet">
<style>
@page{{size:A4;margin:9mm 9mm}}*{{box-sizing:border-box}}
body{{margin:0;font:400 7.2pt/1.3 Barlow,sans-serif;color:#222;--p:#b8395f;--pl:#f6dde6}}
.hd{{display:flex;gap:10px;align-items:center;background:#f3f3f3;border-radius:10px;padding:10px 12px;border-bottom:3px solid var(--p)}}
.hd img{{height:42px;background:#111;border-radius:6px;padding:3px 5px}}.hd .tt{{flex:1}}
.hd .k{{font:600 6pt "Barlow Condensed";letter-spacing:.18em;color:#666}}
.hd h1{{margin:1px 0;font:800 19pt/1 "Barlow Condensed";letter-spacing:.01em;white-space:nowrap}}.hd h1 em{{font-style:normal;color:var(--p)}}
.hd .dt{{font:600 8.5pt "Barlow Condensed"}}
.badge{{border:1.5px solid var(--p);border-radius:6px;padding:5px 10px;text-align:center;background:#fff;min-width:118px}}
.badge small{{display:block;font:600 5.6pt "Barlow Condensed";letter-spacing:.14em;color:#555}}.badge b{{display:block;font:800 12pt "Barlow Condensed";color:var(--p)}}
.chips{{margin:6px 0 12px;display:flex;gap:5px;flex-wrap:wrap}}.chips span{{border:1px solid #ccc;border-radius:20px;padding:2px 8px;font-size:6.2pt;background:#fff}}
h2{{font:700 9pt "Barlow Condensed";letter-spacing:.06em;color:var(--p);margin:8px 0 5px}}
h3{{font:600 6pt "Barlow Condensed";letter-spacing:.16em;color:#555;margin:9px 0 4px;border-bottom:1px solid #ddd;padding-bottom:3px}}
table{{width:100%;border-collapse:collapse}}thead th{{background:var(--p);color:#fff;font:700 6.6pt "Barlow Condensed";letter-spacing:.1em;text-align:left;padding:5px 6px}}
tbody th{{width:58px;text-align:left;vertical-align:top;font:700 7pt "Barlow Condensed";padding:7px 6px}}tbody th small{{display:block;color:#999;font-weight:500}}
tbody td{{vertical-align:top;padding:5px 4px;width:33%;border-bottom:1px solid #e5e5e5}}tr.alt{{background:#fbf3f6}}
.card{{border-left:3px solid #2e9e61;background:#e3f4ea;border-radius:3px;padding:5px 7px;margin-bottom:4px}}
.card.tec{{border-color:#2f7fbf;background:#e1eef8}}.card.int{{border-color:#d9452f;background:#fbe4df}}.card.rn{{border-color:var(--p);background:var(--pl)}}
.card.off{{border-color:#222;background:#eee}}.card.off .ti{{color:#222}}
.ch{{display:flex;justify-content:space-between;align-items:center}}.ch b{{font:700 8pt "Barlow Condensed"}}
.ch i,.lg i{{font:600 5.4pt "Barlow Condensed";font-style:normal;border:1px solid #777;border-radius:3px;padding:0 3px;color:#444;background:#fff}}
.ti{{font:600 7pt "Barlow Condensed";color:#2e9e61}}.tec .ti{{color:#2f7fbf}}.int .ti{{color:#d9452f}}.rn .ti{{color:var(--p)}}
.m{{display:inline-block;background:#fff;border-radius:3px;padding:1px 5px;margin:3px 0 1px;font:700 6.6pt "Barlow Condensed"}}
.nt{{color:#666;font-size:6.2pt}}.dash{{color:#bbb}}
.auto{{border-left:2px solid #333;padding:2px 7px}}.auto small{{display:block;font:700 5.8pt "Barlow Condensed";letter-spacing:.06em}}.auto b{{font:700 7pt "Barlow Condensed";display:block}}.auto span{{color:#666;font-size:6.2pt}}
.dnote{{margin-top:3px;background:#fff6d6;border:1px solid #f1d27a;border-radius:3px;padding:3px 6px;font:600 6.6pt "Barlow Condensed"}}
.lg{{display:flex;gap:40px;margin-top:10px}}.lg h4{{margin:0 0 4px;font:600 5.6pt "Barlow Condensed";letter-spacing:.14em;color:#555}}.lg div div{{margin:2px 0;font-size:6.4pt}}
.sq{{display:inline-block;width:7px;height:7px;border-radius:2px;margin-right:5px;vertical-align:-1px}}.lg i{{margin-right:6px}}
.p2{{break-before:page}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:6px}}
.dc{{border:1px solid #ddd;border-top:3px solid #2e9e61;border-radius:4px;padding:6px 8px}}.dc.tec{{border-top-color:#2f7fbf}}.dc.int{{border-top-color:#d9452f}}.dc.rnd{{border-top-color:var(--p)}}
.dc:not(.rnd){{border-top-color:#2e9e61}}.dc.tec{{border-top-color:#2f7fbf}}.dc.int{{border-top-color:#d9452f}}
.dh{{display:flex;justify-content:space-between;align-items:baseline}}.dh b{{font:700 8pt "Barlow Condensed"}}.dh span{{color:#666;font-size:6.2pt}}
.dc .m{{border:1px solid #ccc}}.eq{{margin-top:3px}}.eq i{{font-style:normal;display:inline-block;border:1px solid #9fd3b3;background:#e3f4ea;border-radius:10px;padding:1px 7px;margin-right:3px;font-size:6.2pt}}
.dc.tec .eq i{{border-color:#a9cbe8;background:#e1eef8}}.dc.int .eq i{{border-color:#efb2a6;background:#fbe4df}}
pre{{font:400 6.6pt/1.35 Barlow;white-space:pre-wrap;margin:4px 0 0}}
.gl{{color:#777;font-size:5.8pt;margin:6px 0 10px}}
.cy{{display:grid;grid-template-columns:1fr 1fr 1fr;background:var(--pl);border-radius:4px;overflow:hidden}}.cy div{{padding:5px 7px}}.cy .on{{background:var(--p);color:#fff}}
.cy b{{display:block;font:700 6.4pt "Barlow Condensed"}}.cy small{{font-size:6pt}}
.tk{{display:flex;gap:1px;margin:3px 0 6px}}.tk i{{flex:1;height:5px;background:#ececec}}.tk i.dc2{{background:#999}}.tk i.cur{{background:var(--p);height:9px}}
.nx{{display:flex;gap:5px;flex-wrap:wrap}}.nx span{{border:1px solid #ddd;border-radius:4px;padding:3px 7px;font-size:6.4pt}}.nx b{{color:var(--p);margin-right:3px}}
.co{{margin-top:12px;background:#fff6d6;border-left:3px solid #e2a400;padding:7px 10px;font-size:6.6pt;border-radius:3px}}
</style>
<div class="hd"><img src="{logo}"><div class="tt"><div class="k">CHAMBÉRY TRIATHLON · GROUPE ADULTES</div>
<h1>ENTRAÎNEMENT ADULTES <em>SEMAINE {week}</em></h1><div class="dt">{e(title_dates)}</div></div>{badge_html}</div>
<div class="chips">{chips_html}</div>
<h2>PLANNING DE LA SEMAINE</h2>
<table><thead><tr><th>JOUR</th><th>NATATION</th><th>VÉLO</th><th>COURSE À PIED</th></tr></thead><tbody>{rows}</tbody></table>
<div class="lg"><div><h4>TYPE DE SÉANCE NATATION</h4><div><span class="sq" style="background:#2f7fbf"></span>Technique · vitesse</div><div><span class="sq" style="background:#2e9e61"></span>Aérobie · endurance</div><div><span class="sq" style="background:#d9452f"></span>Intensité · test</div></div>
<div><h4>LIEUX</h4>{leg_lieux}</div></div>
<div class="p2"><h2>SÉANCES DE LA SEMAINE</h2><h3>NATATION · MATÉRIEL À APPORTER</h3><div class="grid">{swc}</div>
<h3>VÉLO · EN AUTONOMIE</h3><div class="grid">{bkc}</div><h3>COURSE À PIED</h3><div class="grid">{rnc}</div>
<div class="gl">EF : endurance fondamentale · R : récupération · SV1 : seuil 1 · Z2 : endurance · RPE : effort perçu de 1 à 10. Tous les termes sont expliqués dans la fiche « Zones d'intensité &amp; lexique ».</div>
<h2>OÙ ON EN EST DANS LA SAISON</h2>{frise}<div class="tk">{ticks}</div><div class="nx">{"".join(nxt)}</div>
<div class="co">⚠ {e(callout)}</div></div>
</html>'''
open(out, 'w', encoding='utf-8').write(doc)
print('ok', out, len(sess), 'séances')
