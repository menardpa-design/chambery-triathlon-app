"""Construit la version installable (PWA) de l'app Chambéry Triathlon à partir de la page Artifact.
Usage : python3 -I build_pwa.py chambery-tri.html pwa/
Produit pwa/index.html (manifest.webmanifest, sw.js et icônes sont déjà dans pwa/).
Les traces GPX viennent de pwa/traces.json (généré par sync_traces.py)."""
import sys, re, hashlib, time
src, out = sys.argv[1], sys.argv[2].rstrip('/')
s = open(src, encoding='utf-8').read()

head, body = s.split('</style>\n', 1)
head += '</style>\n'
head = head.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', '')
reset = ('<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);color-scheme:light}'
         'body{margin:0;font-size:14px}img{max-width:100%}[hidden]{display:none!important}</style>\n')

# Banque de traces : lecture de traces.json au lieu de la base claude.ai
init_old = re.search(r"\(async\(\)=>\{\n  const c=window\.claude;.*?\n\}\)\(\);\n", body, re.S)
assert init_old, 'bloc init GPX introuvable'
init_new = '''(async()=>{
  G.db={};G.canEdit=false;G.assets=null;
  G.downloads={save:async({filename,data})=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data],{type:'application/gpx+xml'}));a.download=filename;document.body.appendChild(a);a.click();a.remove();}};
  document.querySelectorAll('.add-btn').forEach(b=>b.hidden=true);
  try{const r=await fetch('traces.json',{cache:'no-cache'});G.traces=r.ok?await r.json():[]}catch(e){G.traces=[]}
  ['bike','trail'].forEach(renderTraces);
})();
'''
body = body.replace(init_old.group(0), init_new)
body = body.replace("const r=await fetch('/_blob/'+t.assetId);", "const r=await fetch(t.file);")
body = re.sub(r"// Sans capacité.*?\nsetTimeout\(.*?\);\n", "", body, flags=re.S)
body = body.replace("'Les traces ajoutées par le club apparaîtront ici.'", "'Les coachs ajoutent les traces dans le dossier Drive du club ; elles apparaissent ici à la mise à jour suivante.'")
assert "'/_blob/'" not in body and 'window.claude' not in body

ver = hashlib.sha1(body.encode()).hexdigest()[:8]
sw = '''<script>if('serviceWorker' in navigator){addEventListener('load',()=>navigator.serviceWorker.register('sw.js').catch(()=>{}))}</script>\n'''
doc = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
       '<meta name="theme-color" content="#0A0A0A">\n<meta name="apple-mobile-web-app-capable" content="yes">\n'
       '<meta name="mobile-web-app-capable" content="yes">\n'
       '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
       '<meta name="apple-mobile-web-app-title" content="Chambéry Tri">\n'
       '<link rel="manifest" href="manifest.webmanifest">\n<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
       '<link rel="icon" type="image/png" href="favicon-32.png">\n'
       + reset + head + '</head>\n<body>\n' + body.rstrip('\n') + '\n' + sw + '</body>\n</html>\n')
open(out + '/index.html', 'w', encoding='utf-8').write(doc)
swjs = open(out + '/sw.js', encoding='utf-8').read()
swjs = re.sub(r"const VERSION='[^']*';", f"const VERSION='{ver}';", swjs)
open(out + '/sw.js', 'w', encoding='utf-8').write(swjs)
print('index.html écrit, version', ver)
