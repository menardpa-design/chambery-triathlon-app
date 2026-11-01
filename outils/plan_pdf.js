const {chromium}=require('playwright');
(async()=>{const p=process.env.HTTPS_PROXY;
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell',proxy:p?{server:p}:undefined,args:['--ignore-certificate-errors']});
const pg=await b.newPage();await pg.goto('file://'+process.argv[2],{waitUntil:'networkidle',timeout:30000}).catch(e=>console.log('nav',e.message));
await pg.evaluate(()=>document.fonts.ready);console.log(await pg.evaluate(()=>[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family+f.weight).join(',')));
await pg.pdf({path:process.argv[3],format:'A4',landscape:true,printBackground:true,preferCSSPageSize:true});await b.close()})();
