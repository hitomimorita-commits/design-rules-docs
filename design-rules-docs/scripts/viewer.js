/* Runtime checks use actual font metrics in the user's browser. No external network calls. */
(()=>{
const status=document.getElementById('status');
function check(){
 const wasReading=document.body.classList.contains('reading');
 document.body.classList.remove('reading');
 const problems=[];
 const box=(el)=>el.getBoundingClientRect();
 for(const [i,page] of [...document.querySelectorAll('.slide')].entries()){
  const content=page.querySelector('.content'), cb=box(content), header=box(page.querySelector('header')), footer=box(page.querySelector('footer'));
  const title=box(page.querySelector('h1'));
  if(footer.bottom>box(page).bottom-16)problems.push(`${i+1}ページ：ページ高の超過`);
  if(title.bottom>header.bottom+1)problems.push(`${i+1}ページ：見出しが領域を超えています`);
  const message=page.querySelector('.message');
  if(message && box(message).bottom>cb.top-8)problems.push(`${i+1}ページ：要旨と本文が近すぎます`);
  for(const el of content.querySelectorAll('p,li,td,th,h2,figure,svg')){
   const b=box(el);
   if(b.bottom>footer.top-12||b.right>cb.right+1||b.left<cb.left-1||b.top<cb.top-1)
    problems.push(`${i+1}ページ：本文が領域を超えています`);
   if(el.scrollWidth>el.clientWidth+2 && !['svg'].includes(el.tagName.toLowerCase()))problems.push(`${i+1}ページ：文字幅の超過`);
  }
  for(const svg of page.querySelectorAll('svg')){
   const bounds=box(svg), texts=[...svg.querySelectorAll('text')];
   for(const t of texts){const b=box(t);if(b.left<bounds.left||b.right>bounds.right||b.top<bounds.top||b.bottom>bounds.bottom)problems.push(`${i+1}ページ：図のラベルが領域外です`);}
   for(let a=0;a<texts.length;a++)for(let b=a+1;b<texts.length;b++){
    const x=box(texts[a]),y=box(texts[b]);
    if(Math.min(x.right,y.right)-Math.max(x.left,y.left)>1&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>1)problems.push(`${i+1}ページ：図のラベルが重なっています`);
   }
  }
 }
 if(wasReading)document.body.classList.add('reading');
 const errors=[...new Set(problems)];window.designReport={ok:errors.length===0,errors};
 document.body.classList.toggle('invalid',errors.length>0);
 status.textContent=errors.length?errors.join(' / '):'表示検査：問題なし';
 return window.designReport;
}
window.checkDesign=check;
document.getElementById('mode').onclick=()=>{document.body.classList.toggle('reading');document.getElementById('mode').textContent=document.body.classList.contains('reading')?'スライド表示':'読む表示';};
document.getElementById('print').onclick=()=>{if(check().ok){document.body.classList.remove('reading');window.print();}};
window.addEventListener('beforeprint',()=>{document.body.classList.remove('reading');check();});
window.addEventListener('resize',check);
Promise.all([document.fonts.ready,...[...document.images].map(im=>im.decode().catch(()=>{}))]).then(()=>{check();if(innerWidth<1320){document.body.classList.add('reading');document.getElementById('mode').textContent='スライド表示';}});
})();
