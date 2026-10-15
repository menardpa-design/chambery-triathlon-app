"""Génère pwa/traces.json et copie les GPX à partir d'un dossier local (copie du dossier Drive du club).
Structure attendue : <dossier>/Vélo/*.gpx et <dossier>/Trail/*.gpx (noms de sous-dossiers sans accents/casse indifférents).
Usage : python3 -I sync_traces.py <dossier_gpx> pwa/"""
import sys, os, re, json, math, shutil, unicodedata
import xml.etree.ElementTree as ET

def norm(s): return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
ID_SUFFIX = re.compile(r'(-\d{2,})+$')
def slug(s): return re.sub(r'[^a-z0-9]+', '-', norm(s)).strip('-') or 'trace'
def auto_cat(kind, km):
    if kind == 'bike': return '45' if km < 52.5 else '60' if km < 80 else '100'
    return 'court' if km < 15 else 'moyen' if km <= 30 else 'long'

def parse(path):
    root = ET.parse(path).getroot()
    ns = lambda t: [e for e in root.iter() if e.tag.split('}')[-1] == t]
    pts = ns('trkpt') or ns('rtept')
    P = []
    for p in pts:
        try: lat, lon = float(p.get('lat')), float(p.get('lon'))
        except (TypeError, ValueError): continue
        ele = next((c.text for c in p if c.tag.split('}')[-1] == 'ele'), None)
        P.append([lat, lon, float(ele) if ele not in (None, '') else None])
    if len(P) < 2: raise ValueError('pas de points')
    R, rad, dist, cum = 6371, math.pi / 180, 0.0, [0.0]
    for a, b in zip(P, P[1:]):
        dl, dn = (b[0] - a[0]) * rad, (b[1] - a[1]) * rad
        h = math.sin(dl / 2) ** 2 + math.cos(a[0] * rad) * math.cos(b[0] * rad) * math.sin(dn / 2) ** 2
        dist += 2 * R * math.asin(math.sqrt(h)); cum.append(dist)
    gain = loss = 0.0; ref = None
    for p in P:
        if p[2] is None: continue
        if ref is None: ref = p[2]; continue
        d = p[2] - ref
        if d >= 5: gain += d; ref = p[2]
        elif d <= -5: loss -= d; ref = p[2]
    eles = [p[2] for p in P if p[2] is not None]
    step = max(1, math.ceil(len(P) / 300)); idx = list(range(0, len(P), step))
    if idx[-1] != len(P) - 1: idx.append(len(P) - 1)
    simp = [[round(P[i][0], 5), round(P[i][1], 5), None if P[i][2] is None else round(P[i][2]), round(cum[i], 2)] for i in idx]
    nm = next((e.text for e in root.iter() if e.tag.split('}')[-1] == 'name' and e.text), '')
    return dict(km=round(dist, 1), gain=round(gain), loss=round(loss), maxEle=round(max(eles)) if eles else None,
                minEle=round(min(eles)) if eles else None, pts=simp, gpxName=(nm or '').strip())

if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2].rstrip('/')
    kinds = {}
    for d in os.listdir(src):
        k = norm(d)
        if k.startswith('velo'): kinds['bike'] = os.path.join(src, d)
        elif k.startswith('trail'): kinds['trail'] = os.path.join(src, d)
    shutil.rmtree(out + '/traces', ignore_errors=True)
    items, errors = [], []
    for kind, folder in kinds.items():
        os.makedirs(f'{out}/traces/{kind}', exist_ok=True)
        for f in sorted(os.listdir(folder)):
            if not f.lower().endswith('.gpx'): continue
            try: t = parse(os.path.join(folder, f))
            except Exception as e: errors.append(f'{f} : {e}'); continue
            name = os.path.splitext(f)[0].replace('_', ' ').strip()
            if ID_SUFFIX.search(name):  # nom exporté (Openrunner, Komoot…) : on préfère le nom interne du GPX
                name = ID_SUFFIX.sub('', t['gpxName'] or name).replace('_', ' ').strip()
            if name.isupper(): name = name.capitalize()
            name = name[:1].upper() + name[1:]
            fn = slug(name) + '.gpx'
            shutil.copyfile(os.path.join(folder, f), f'{out}/traces/{kind}/{fn}')
            items.append(dict(id=f'{kind}-{slug(name)}', kind=kind, cat=auto_cat(kind, t['km']), name=name, desc='',
                              file=f'traces/{kind}/{fn}', fileName=fn, **{k: v for k, v in t.items() if k != 'gpxName'}))
    json.dump(items, open(out + '/traces.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{len(items)} traces', '| erreurs : ' + '; '.join(errors) if errors else '')
