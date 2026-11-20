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
  if(!('Notification' in window&&'serviceWorker' in navigator&&'PushManager' in window)){if(ios&&navigator.standalone){h.textContent='📱 Pour recevoir les notifications, mets à jour ton iPhone (iOS 16.4 ou plus récent).'}if(ios)h.hidden=false;return}
  let OS=null,err='';
  const say=t=>{h.textContent=t;h.hidden=false};
  const upd=()=>{const on=!!(OS&&OS.User.PushSubscription.optedIn);const l=on?'Notifications activées (toucher pour couper)':'Activer les notifications';b.setAttribute('aria-label',l);b.title=l;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)};
  b.hidden=false;upd();
  b.onclick=async()=>{
    if(!OS){say(err?('Les notifications n’ont pas pu démarrer : '+err):'Les notifications ne se sont pas chargées. Un bloqueur de publicité peut les empêcher : autorise ce site, puis rouvre l’appli.');return}
    const sub=OS.User.PushSubscription;
    try{if(sub.optedIn){await sub.optOut();say('🔕 Notifications coupées. Touche la cloche pour les réactiver.')}else{await sub.optIn();if(sub.optedIn)say('🔔 Notifications activées. Touche la cloche pour les couper.');if(Notification.permission==='denied')say('Les notifications sont bloquées pour ce site dans les réglages du navigateur ou du téléphone.')}}catch(e){say('Erreur : '+(e&&e.message||e))}
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
# Aide à l'installation : bandeau en bas de l'écran tant que l'appli est ouverte dans le navigateur.
# Android / Chrome / Edge : bouton « Installer » (invite du navigateur). iPhone/iPad : les 2 gestes à faire dans Safari.
# Navigateur intégré (WhatsApp, Facebook, Instagram…) : il faut d'abord ouvrir le lien dans Safari ou Chrome.
install = """<div class="inst" id="instBar" role="dialog" aria-labelledby="instT" hidden>
<img src="apple-touch-icon.png" alt="" width="44" height="44">
<div class="inst-tx"><b id="instT">Installe l’appli du club</b><span id="instS"></span></div>
<button type="button" class="inst-go" id="instGo" hidden>Installer</button>
<button type="button" class="inst-x" id="instX" aria-label="Plus tard">✕</button>
</div>
<style>
.inst{position:fixed;left:max(10px,env(safe-area-inset-left,0px));right:max(10px,env(safe-area-inset-right,0px));bottom:calc(10px + env(safe-area-inset-bottom,0px));z-index:40;max-width:560px;margin:0 auto;display:flex;align-items:center;gap:12px;background:#0A0A0A;color:#fff;border-radius:16px;padding:12px 12px 12px 14px;box-shadow:0 8px 30px rgba(0,0,0,.35);font:14px/1.35 var(--body,system-ui)}
.inst img{border-radius:10px;flex:none}
.inst-tx{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.inst-tx b{font:800 1rem/1.15 var(--display,system-ui);text-transform:uppercase;letter-spacing:.03em}
.inst-tx span{opacity:.88;font-size:.85rem}
.inst-go{flex:none;border:0;border-radius:999px;background:var(--pink,#ED68A3);color:#0A0A0A;font:800 .9rem/1 var(--display,system-ui);text-transform:uppercase;letter-spacing:.04em;padding:11px 14px;cursor:pointer}
.inst-x{flex:none;align-self:flex-start;border:0;background:transparent;color:#fff;opacity:.7;font-size:1rem;width:32px;height:32px;margin:-6px -6px 0 0;cursor:pointer}
body.has-inst{padding-bottom:96px}
</style>
<script>
(function(){
  const bar=document.getElementById('instBar'),sub=document.getElementById('instS'),go=document.getElementById('instGo');
  const ua=navigator.userAgent;
  const standalone=navigator.standalone||matchMedia('(display-mode: standalone)').matches||matchMedia('(display-mode: fullscreen)').matches;
  if(standalone||!bar)return;
  try{const t=+localStorage.getItem('instLater');if(t&&Date.now()-t<7*864e5)return}catch(e){}
  const ios=/iphone|ipad|ipod/i.test(ua)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
  const inApp=/FBAN|FBAV|FB_IAB|Instagram|Line\\/|WhatsApp|Snapchat|LinkedInApp|Messenger|GSA\\//i.test(ua);
  const mobile=ios||/android/i.test(ua);
  const show=t=>{sub.textContent=t;bar.hidden=false;document.body.classList.add('has-inst')};
  const hide=()=>{bar.hidden=true;document.body.classList.remove('has-inst')};
  document.getElementById('instX').onclick=()=>{hide();try{localStorage.setItem('instLater',Date.now())}catch(e){}};
  let ev=null;
  addEventListener('beforeinstallprompt',e=>{e.preventDefault();ev=e;go.hidden=false;show('Une icône sur ton écran d’accueil, et le planning même sans réseau.')});
  go.onclick=async()=>{if(!ev)return;ev.prompt();try{const r=await ev.userChoice;if(r.outcome==='accepted')hide()}catch(e){}ev=null;go.hidden=true};
  addEventListener('appinstalled',hide);
  setTimeout(()=>{
    if(ev||!bar.hidden)return;
    if(inApp&&mobile)show(ios?'Ouvre d’abord ce lien dans Safari (menu ••• ou ⬆︎ puis « Ouvrir dans Safari »).':'Ouvre d’abord ce lien dans Chrome (menu ⋮ puis « Ouvrir dans Chrome »).');
    else if(ios)show('Touche ⬆︎ Partager (dans Safari : ••• puis Partager), puis « Sur l’écran d’accueil ».');
    else if(/android/i.test(ua))show('Ouvre le menu ⋮ du navigateur, puis « Installer l’application » ou « Ajouter à l’écran d’accueil ».');
  },2500);
})();
</script>
"""
doc = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
       '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
       '<meta name="theme-color" content="#0A0A0A">\n<meta name="apple-mobile-web-app-capable" content="yes">\n'
       '<meta name="mobile-web-app-capable" content="yes">\n'
       '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
       '<meta name="apple-mobile-web-app-title" content="Chambéry Tri">\n'
       '<link rel="manifest" href="manifest.webmanifest">\n<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
       '<link rel="icon" type="image/png" href="favicon-32.png">\n'
       + reset + head + '</head>\n<body>\n' + body.rstrip('\n') + '\n' + install + sw + '</body>\n</html>\n')
ver = hashlib.sha1(doc.encode()).hexdigest()[:8]  # toute la page : CSS et bandeau compris
open(out + '/index.html', 'w', encoding='utf-8').write(doc)
swjs = open(out + '/sw.js', encoding='utf-8').read()
swjs = re.sub(r"const VERSION='[^']*';", f"const VERSION='{ver}';", swjs)
open(out + '/sw.js', 'w', encoding='utf-8').write(swjs)
print('index.html écrit, version', ver)
