"""Met à jour les données de l'app Chambéry Triathlon depuis le Google Sheet "Plan adulte 2026-2027".
Usage : python3 -I update_planning.py plan.xlsx page.html      (relit le Sheet)
        python3 -I update_planning.py --refilter page.html     (sans Sheet : recalcule seulement les semaines visibles)
Remplace les lignes `const WEEKS=...;`, `const SEASON=...;`, `const CRSHEET=...;` et `const CHANGES=...;` de la page,
sans toucher au reste (CRENEAUX de base, EXTRA, RACES, lieux, etc.).
Onglet « Créneaux » (facultatif) : Jour | Sport | Moment | Horaire | Entraîneur | Lieu  → remplace l'horaire, l'entraîneur ou le lieu habituels.
Onglet « Changements » (facultatif) : Date | Sport | Moment | Statut | Entraîneur | Horaire | Lieu | Message
  → une ligne par séance d'une date précise ; Statut « Annulé » barre la séance, sinon les cases remplies remplacent celles du créneau.
Séances : seules la semaine en cours et la suivante sont publiées (demande de Paul, 2026-10-15) ;
toutes les semaines sont gardées dans weeks_full.json, à côté de ce script (hors dépôt public).
La planification annuelle (SEASON) reste complète."""
import sys, os, re, json, datetime
from zoneinfo import ZoneInfo

DAYS = {'LUNDI': 1, 'MARDI': 2, 'MERCREDI': 3, 'JEUDI': 4, 'VENDREDI': 5, 'SAMEDI': 6, 'DIMANCHE': 0}

FULL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weeks_full.json')
AHEAD = 1  # semaines visibles après la semaine en cours

def visible(weeks, now=None):
    now = now or datetime.datetime.now(ZoneInfo('Europe/Paris'))
    keys = [int(w) for w in weeks]
    def key(w): return (w < 36, w)
    cur = now.isocalendar()[1]
    if cur not in keys:
        past = [w for w in keys if key(w) <= key(cur)]
        cur = max(past, key=key) if past else min(keys, key=key)
    order = sorted(keys, key=key); i = order.index(cur)
    keep = set(order[:i + AHEAD + 1])
    return {w: v for w, v in weeks.items() if int(w) in keep}

def merged_map(ws):
    mr = {}
    for r in ws.merged_cells.ranges:
        for row in range(r.min_row, r.max_row + 1):
            for col in range(r.min_col, r.max_col + 1):
                mr[(row, col)] = r
    return mr

def sport(lbl):
    l = lbl.lower()
    if 'natation' in l:
        return 'swim', (lbl.split()[-1].capitalize() if len(lbl.split()) > 1 else '')
    if 'vélo' in l or 'velo' in l:
        return 'bike', ''
    if 'course' in l:
        return 'run', ''
    return 'other', ''

def weeks_from(wb):
    weeks = {}
    for n in wb.sheetnames:
        m = re.search(r'SEMAINE\s*(\d+)', n, re.I)
        if not m:
            continue
        w = int(m.group(1)); ws = wb[n]; mr = merged_map(ws)
        cols = []
        for c in range(3, ws.max_column + 1):
            v = ws.cell(2, c).value
            if v and str(v).strip().upper() in DAYS:
                r = mr.get((2, c)); span = (r.max_col - r.min_col + 1) if r else 1
                cols.append((DAYS[str(v).strip().upper()], c, span))
        sess = []
        for row in range(3, min(ws.max_row, 40) + 1):
            lbl = ws.cell(row, 2).value
            if not lbl or str(lbl).strip().upper() in ('AUTRE', 'SPORT / JOUR'):
                continue
            sp, slot = sport(str(lbl).strip())
            if sp == 'other':
                continue
            for d, c, span in cols:
                vals = []
                for k in range(span):
                    cc = c + k; r = mr.get((row, cc))
                    v = None if (r and (r.min_row, r.min_col) != (row, cc)) else ws.cell(row, cc).value
                    vals.append(((str(v).strip() if v is not None else ''), r))
                txt = [v for v, _ in vals]
                if span == 2:
                    a, b = txt; r0 = vals[0][1]
                    both = r0 is not None and r0.min_col == c and r0.max_col >= c + 1
                    if both or (a and a == b):
                        if a: sess.append({'d': d, 's': sp, 'slot': slot, 'lvl': 'all', 'x': a})
                    else:
                        if a: sess.append({'d': d, 's': sp, 'slot': slot, 'lvl': 'deb', 'x': a})
                        if b: sess.append({'d': d, 's': sp, 'slot': slot, 'lvl': 'av', 'x': b})
                elif txt[0]:
                    sess.append({'d': d, 's': sp, 'slot': slot, 'lvl': 'all', 'x': txt[0]})
        weeks[w] = [s for s in sess if s['x'].strip() not in ('_', '\\_')]
    cap = next((wb[n] for n in wb.sheetnames if 'CAP' in n.upper()), None)
    if cap is not None:
        for row in range(1, cap.max_row + 1):
            m = re.match(r'S(\d+)$', str(cap.cell(row, 3).value or '').strip())
            if not m:
                continue
            w = int(m.group(1))
            if w in weeks or w > 52:
                continue
            s = []
            for c, d in zip(range(4, 10), [1, 2, 3, 4, 5, 6]):
                x = cap.cell(row, c).value
                if x and not re.match(r'^[\d\- %.]+$', str(x)):
                    s.append({'d': d, 's': 'run', 'slot': '', 'lvl': 'all', 'x': str(x).strip()})
            if s:
                weeks[w] = s
    # Ordre de saison : S36..S52 puis S1..S35
    order = sorted(weeks, key=lambda w: (w < 36, w))
    return {str(k): weeks[k] for k in order}

def season_from(wb):
    ws = next(wb[n] for n in wb.sheetnames if 'annuel' in n.lower())
    mr = merged_map(ws)
    def val(row, col):
        r = mr.get((row, col))
        v = ws.cell(r.min_row, r.min_col).value if r else ws.cell(row, col).value
        return str(v).strip() if v not in (None, '') else ''
    labels = {str(ws.cell(r, 2).value or '').strip().lower(): r for r in range(1, 20)}
    def rowof(*keys):
        for k, r in labels.items():
            if any(x in k for x in keys): return r
        return None
    R = {'w': rowof('semaine'), 'club': rowof('courses club'), 'info': rowof('info'), 'macro': rowof('macrocycle'),
         'meso': rowof('mésocycle', 'mesocycle'), 'nat': rowof('natation'), 'velo': rowof('vélo', 'velo'), 'cap': rowof('cap')}
    out = []
    for col in range(3, ws.max_column + 1):
        v = ws.cell(R['w'], col).value
        if v in (None, ''):
            continue
        w = int(float(v))
        out.append({'w': w, 'y': 2026 if w >= 36 else 2027, **{k: (val(R[k], col) if R[k] else '') for k in ('macro', 'meso', 'nat', 'velo', 'cap', 'info', 'club')}})
    return out

def norm(v):
    import unicodedata
    v = '' if v is None else str(v).strip()
    return ''.join(c for c in unicodedata.normalize('NFD', v.lower()) if unicodedata.category(c) != 'Mn')

def tab(wb, name):
    n = next((n for n in wb.sheetnames if norm(n).startswith(name)), None)
    if not n:
        return None
    rows = [[c for c in r] for r in wb[n].iter_rows(values_only=True)]
    hi = next((i for i, r in enumerate(rows) if sum(1 for c in r if norm(c)) >= 3), None)
    if hi is None:
        return []
    head = [norm(c) for c in rows[hi]]
    col = lambda *ks: next((i for i, h in enumerate(head) if any(h.startswith(k) for k in ks)), None)
    C = {k: col(*ks) for k, ks in {'jour': ('jour',), 'date': ('date',), 'sport': ('sport', 'seance', 'activite'), 'moment': ('moment', 'creneau'),
         'h': ('horaire', 'heure'), 'coach': ('entraineur', 'coach'), 'lieu': ('lieu',), 'statut': ('statut', 'etat'), 'msg': ('message', 'commentaire', 'info', 'remarque')}.items()}
    get = lambda r, k: (r[C[k]] if C[k] is not None and C[k] < len(r) else None)
    return [{k: get(r, k) for k in C} for r in rows[hi + 1:] if any(norm(c) for c in r)]

GRP = {'piste': ('deb', 'Piste'), 'trail': ('av', 'Trail')}

def sport_of(v):
    s = norm(v)
    for k, code in (('nat', 'swim'), ('vel', 'bike'), ('course', 'run'), ('cap', 'run'), ('piste', 'run'), ('trail', 'run'), ('renfo', 'other'), ('ppg', 'other')):
        if k in s:
            return code, next((g for g in GRP if g in s), None)
    return None, None

def moment_of(v):
    s = norm(v)
    return next((m.capitalize() for m in ('matin', 'midi', 'soir') if m in s), '')

def txt(v):
    if v is None: return ''
    if isinstance(v, datetime.time): return v.strftime('%Hh%M')
    return str(v).strip()

def creneaux_from(wb):
    rows = tab(wb, 'creneau')
    if rows is None:
        return None
    out = {}
    for r in rows:
        d = DAYS.get(norm(r['jour']).upper()); s, g = sport_of(r['sport'])
        if d is None or not s:
            continue
        key = f"{d}-{s}-{moment_of(r['moment']) if s == 'swim' else ''}" + (f"-{GRP[g][0]}" if g else '')
        v = {k: txt(r[k]) for k in ('h', 'coach', 'lieu') if txt(r[k])}
        if g: v['grp'] = GRP[g][1]
        if v: out[key] = v
    return out

def date_of(v, today):
    if isinstance(v, datetime.datetime): return v.date()
    if isinstance(v, datetime.date): return v
    m = re.match(r'\s*(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?', str(v or ''))
    if not m: return None
    d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
    y = (int(y) + 2000 if len(y) == 2 else int(y)) if y else (today.year if mo >= today.month - 6 else today.year + 1)
    try: return datetime.date(y, mo, d)
    except ValueError: return None

def changes_from(wb):
    rows = tab(wb, 'changement')
    if rows is None:
        return None
    today = datetime.datetime.now(ZoneInfo('Europe/Paris')).date(); out = []
    for r in rows:
        dt = date_of(r['date'], today); s, g = sport_of(r['sport'])
        if not dt or not s or dt < today - datetime.timedelta(days=7):
            continue
        c = {'date': dt.isoformat(), 's': s, 'slot': moment_of(r['moment']) if s == 'swim' else ''}
        if g: c['grp'] = GRP[g][1]
        if norm(r['statut']).startswith('annul'): c['off'] = 1
        c.update({k: txt(r[k]) for k in ('coach', 'h', 'lieu', 'msg') if txt(r[k])})
        out.append(c)
    return out

if __name__ == '__main__':
    if sys.argv[1] == '--refilter':
        html = sys.argv[2]; weeks = json.load(open(FULL, encoding='utf-8')); season = cren = chg = None
    else:
        import openpyxl
        xlsx, html = sys.argv[1], sys.argv[2]
        wb = openpyxl.load_workbook(xlsx, data_only=True)
        weeks, season = weeks_from(wb), season_from(wb)
        cren, chg = creneaux_from(wb) or {}, changes_from(wb) or []
        json.dump(weeks, open(FULL, 'w', encoding='utf-8'), ensure_ascii=False)
    shown = visible(weeks)
    s = open(html, encoding='utf-8').read()
    s, a = re.subn(r'^const WEEKS=.*;$', lambda m: 'const WEEKS=' + json.dumps(shown, ensure_ascii=False) + ';', s, count=1, flags=re.M)
    b = 1
    if season is not None:
        s, b = re.subn(r'^const SEASON=.*;$', lambda m: 'const SEASON=' + json.dumps(season, ensure_ascii=False) + ';', s, count=1, flags=re.M)
    if cren is not None:
        s, c1 = re.subn(r'^const CRSHEET=.*;$', lambda m: 'const CRSHEET=' + json.dumps(cren, ensure_ascii=False) + ';', s, count=1, flags=re.M)
        s, c2 = re.subn(r'^const CHANGES=.*;$', lambda m: 'const CHANGES=' + json.dumps(chg, ensure_ascii=False) + ';', s, count=1, flags=re.M)
        b = b and c1 and c2
    assert a == 1 and b == 1, 'lignes WEEKS/SEASON/CRSHEET/CHANGES introuvables'
    open(html, 'w', encoding='utf-8').write(s)
    print('semaines dans le Sheet :', ', '.join(weeks), '| publiées :', ', '.join(shown))
    if cren is not None:
        print('créneaux du Sheet :', len(cren), '| changements :', len(chg))
