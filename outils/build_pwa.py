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
# Service worker : un seul pour le hors-ligne et les notifications OneSignal (sw.js importe le SDK OneSignal).
# On n'enregistre sw.js que s'il n'y a encore rien : OneSignal le réenregistre avec ses paramètres et il ne faut pas se battre avec lui.
ONESIGNAL_APP_ID = '08efe86e-6964-415b-8658-16f9f82fc0d4'
sw = ("""<script>if('serviceWorker' in navigator){addEventListener('load',()=>navigator.serviceWorker.getRegistration().then(r=>{if(!r)return navigator.serviceWorker.register('sw.js')}).catch(()=>{}))}</script>\n"""
      """<script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>\n"""
      """<script>
(function(){
  const b=document.getElementById('notifBtn'),h=document.getElementById('notifHint');
  const ios=/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  if(!('Notification' in window&&'serviceWorker' in navigator&&'PushManager' in window)){if(ios&&!navigator.standalone)h.hidden=false;return}
  let OS=null,err='';
  const say=t=>{h.textContent=t;h.hidden=false};
  const upd=()=>{const on=!!(OS&&OS.User.PushSubscription.optedIn);b.textContent=on?'🔔 Notifications activées · Couper':'🔔 Activer les notifications';b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)};
  b.hidden=false;upd();
  b.onclick=async()=>{
    if(!OS){say(err?('Les notifications n’ont pas pu démarrer : '+err):'Les notifications ne se sont pas chargées. Un bloqueur de publicité peut les empêcher : autorise ce site, puis rouvre l’appli.');return}
    const sub=OS.User.PushSubscription;
    try{if(sub.optedIn)await sub.optOut();else{await sub.optIn();if(Notification.permission==='denied')say('Les notifications sont bloquées pour ce site dans les réglages du navigateur ou du téléphone.')}}catch(e){say('Erreur : '+(e&&e.message||e))}
    upd();
  };
  window.OneSignalDeferred=window.OneSignalDeferred||[];
  OneSignalDeferred.push(async function(OneSignal){
    try{
      await OneSignal.init({appId:'%s',serviceWorkerPath:'chambery-triathlon-app/sw.js',serviceWorkerUpdaterPath:'chambery-triathlon-app/sw.js',serviceWorkerParam:{scope:'/chambery-triathlon-app/'},notifyButton:{enable:false},welcomeNotification:{disable:true}});
      OS=OneSignal;OneSignal.User.PushSubscription.addEventListener('change',upd);upd();
    }catch(e){err=(e&&e.message)||String(e);console.warn('OneSignal',e)}
  });
})();
</script>\n""" % ONESIGNAL_APP_ID)
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
