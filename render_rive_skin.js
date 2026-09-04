const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

const [,, work, framesDir, widthRaw='720', heightRaw='720'] = process.argv;
if (!work || !framesDir) throw new Error('usage: node render_rive_skin.js WORK FRAMES [W] [H]');
const width=Number(widthRaw), height=Number(heightRaw);
fs.mkdirSync(framesDir,{recursive:true});
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.json':'application/json','.riv':'application/octet-stream'};
const server=http.createServer((req,res)=>{
  let rel=decodeURIComponent(req.url.split('?')[0]);
  if(rel==='/') rel='/renderer.html';
  const root=rel.startsWith('/runtime/')?path.join(__dirname,'node_modules/@rive-app/canvas-advanced'):work;
  const local=rel.startsWith('/runtime/')?rel.slice(9):rel.slice(1);
  const file=path.resolve(root,local);
  if(!file.startsWith(path.resolve(root))||!fs.existsSync(file)){res.writeHead(404);return res.end();}
  res.setHeader('Content-Type',mime[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res);
});

(async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const cache=path.join(os.homedir(),'.cache','ms-playwright');
  const installed=fs.existsSync(cache)?fs.readdirSync(cache).filter(x=>x.startsWith('chromium-')).sort().reverse():[];
  const executable=installed.map(x=>path.join(cache,x,'chrome-linux64','chrome')).find(fs.existsSync);
  const browser=await chromium.launch({headless:true,executablePath:executable,args:['--disable-dev-shm-usage']});
  const page=await browser.newPage({viewport:{width,height},deviceScaleFactor:1});
  await page.goto(`http://127.0.0.1:${server.address().port}/`,{waitUntil:'networkidle'});
  await page.waitForFunction(()=>window.kimodoReady===true);
  const count=await page.evaluate(()=>window.kimodoFrameCount);
  for(let i=0;i<count;i++){
    await page.evaluate(i=>window.renderKimodoFrame(i),i);
    await page.waitForTimeout(50);
    await page.screenshot({path:path.join(framesDir,`frame_${String(i+1).padStart(4,'0')}.png`)});
  }
  console.log(JSON.stringify({frames:count,width,height}));
  await browser.close();server.close();
})().catch(e=>{console.error(e);server.close();process.exit(1)});
