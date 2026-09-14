// Optional browser gate. Usage: node verify.cjs example.html [chromium-executable]
const fs=require('fs');const path=require('path');const {pathToFileURL}=require('url');
let lib;try{lib=require('playwright')}catch(e){lib=require(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright')}
(async()=>{
 const browser=await lib.chromium.launch({headless:true,...(process.argv[3]?{executablePath:process.argv[3]}:{}),args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1400,height:920}});
  const file=path.resolve(process.argv[2]||'example.html');
  await page.goto(pathToFileURL(file).href);await page.waitForFunction(()=>window.designReport,{timeout:30000});
  const report=await page.evaluate(()=>window.checkDesign());
  const shots=path.join(path.dirname(file),'previews');fs.mkdirSync(shots,{recursive:true});
  const slides=page.locator('.slide');for(let i=0;i<await slides.count();i++)await slides.nth(i).screenshot({path:path.join(shots,`page-${String(i+1).padStart(2,'0')}.png`)});
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>document.body.classList.add('reading'));
  const mobile=await page.evaluate(()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth}));
  report.mobile=mobile;
  if(mobile.scrollWidth>mobile.width){report.ok=false;report.errors.push('読む表示で横スクロールが発生');}
  fs.writeFileSync(file.replace(/\.html$/,'.browser-report.json'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));if(!report.ok)process.exitCode=1;
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
