#!/usr/bin/env python3
"""Rule-based document generator. Python 3.10+. No API key required."""
import argparse
import base64
import html
import json
import math
import mimetypes
import os
from pathlib import Path
import sys
import unicodedata

VERSION = '2.0.0'
ROOT = Path(__file__).resolve().parent
THEMES = {
    'neutral': {'background':'#FAFAF8', 'ink':'#292C30', 'muted':'#555B62', 'accent':'#3D566B', 'surface':'#EEF0EF'},
    'mono': {'background':'#FFFFFF', 'ink':'#292C30', 'muted':'#555B62', 'accent':'#34383C', 'surface':'#F0F0EE'},
    'red': {'background':'#FAFAF8', 'ink':'#292C30', 'muted':'#555B62', 'accent':'#A12D35', 'surface':'#F3EBEB'},
    'olive': {'background':'#FAFAF8', 'ink':'#292C30', 'muted':'#555B62', 'accent':'#53623A', 'surface':'#EEF0E9'},
}
SPEC = {
 'cover': (['subtitle'], ['meta']),
 'text': (['items'], []),
 'sections': (['groups'], []),
 'compare': (['columns'], []),
 'flow': (['steps','relation'], []),
 'cycle': (['steps','relation'], []),
 'hierarchy': (['root','children'], []),
 'table': (['headers','rows'], ['align','striped']),
 'image': (['image','alt','caption'], ['items','annotations']),
 'bar': (['labels','values','unit','source'], ['errors']),
 'line': (['labels','series','unit','source'], []),
 'pie': (['labels','values','unit','source'], []),
 'scatter': (['points','x_label','y_label','source'], []),
}

def fail(msg): raise ValueError(msg)
def keys(obj, required, optional=()):
    if not isinstance(obj,dict): fail('オブジェクトが必要です')
    missing=set(required)-obj.keys(); extra=obj.keys()-set(required)-set(optional)
    if missing or extra: fail(f'キー違反: 不足={sorted(missing)}, 未許可={sorted(extra)}')
def clean(s,limit=100):
    if not isinstance(s,str) or not s.strip() or len(s)>limit: fail(f'空でない文字列、最大{limit}文字が必要です')
    for c in s:
        n=ord(c)
        if unicodedata.category(c).startswith('C') or 0x1F000<=n<=0x1FAFF or 0x2600<=n<=0x27BF or n in (0xFE0F,0x20E3):
            fail('絵文字・装飾記号・制御文字は禁止です')
    return s

def seq(a,low,high):
    if not isinstance(a,list) or not low<=len(a)<=high: fail(f'要素数は{low}〜{high}です')
    return a

def number(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1e12: fail('有限の数値（絶対値1兆以下）が必要です')
    return v

def strings(a,low,high,limit):
    for s in seq(a,low,high): clean(s,limit)

def luminance(c):
    rgb=[int(c[i:i+2],16)/255 for i in (1,3,5)]
    lin=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    return sum(x*y for x,y in zip(lin,[.2126,.7152,.0722]))

def contrast(a,b):
    x,y=sorted([luminance(a),luminance(b)])
    return (y+.05)/(x+.05)

def validate(data):
    keys(data,['title','slides'],['theme'])
    clean(data['title'],80)
    if data.get('theme','neutral') not in THEMES: fail('themeはneutral / mono / red / oliveです')
    for i,s in enumerate(seq(data['slides'],1,80),1):
        try:
            if not isinstance(s,dict) or s.get('type') not in SPEC: fail('未対応のtypeです')
            kind=s['type']; required,optional=SPEC[kind]
            keys(s,['type','title']+([] if kind=='cover' else ['message'])+required,optional+['source'])
            clean(s['title'],48 if kind=='cover' else 32)
            if kind!='cover': clean(s['message'],70)
            if 'source' in s: clean(s['source'],160)
            if kind=='cover':
                clean(s['subtitle'],80)
                if 'meta' in s: strings(s['meta'],1,4,60)
            elif kind=='text': strings(s['items'],1,5,80)
            elif kind in ('sections','compare'):
                groups=s['groups' if kind=='sections' else 'columns']
                for g in seq(groups,1 if kind=='sections' else 2,3 if kind=='sections' else 2):
                    keys(g,['heading','items']); clean(g['heading'],24)
                    strings(g['items'],1,2 if kind=='sections' else 4,65 if kind=='sections' else 45)
            elif kind in ('flow','cycle'):
                strings(s['steps'],2 if kind=='flow' else 3,4,36 if kind=='flow' else 14)
                if s['relation'] not in ('sequence','causal'): fail('relationはsequence / causalです')
                if s['relation']=='causal' and not s.get('source'): fail('因果関係にはsourceが必要です')
            elif kind=='hierarchy':
                clean(s['root'],30); strings(s['children'],2,4,36)
            elif kind=='table':
                strings(s['headers'],2,5,20); n=len(s['headers'])
                for r in seq(s['rows'],1,6):
                    for v in seq(r,n,n):
                        if isinstance(v,str): clean(v,40)
                        else: number(v)
                if 'align' in s:
                    for a in seq(s['align'],n,n):
                        if a not in ('left','right'): fail('alignはleft / rightです')
                if 'striped' in s and not isinstance(s['striped'],bool): fail('stripedは真偽値です')
            elif kind=='image':
                clean(s['image'],240); clean(s['alt'],200); clean(s['caption'],90)
                if 'items' in s: strings(s['items'],1,3,70)
                for a in s.get('annotations',[]):
                    keys(a,['x','y','label']); clean(a['label'],28)
                    for coord in ('x','y'):
                        if not 0<=number(a[coord])<=1: fail('注釈座標は0〜1です')
                if len(s.get('annotations',[]))>3: fail('注釈は3件までです')
            elif kind in ('bar','pie'):
                strings(s['labels'],1 if kind=='bar' else 2,8 if kind=='bar' else 5,10 if kind=='bar' else 14)
                n=len(s['labels']); clean(s['unit'],12)
                for v in seq(s['values'],n,n): number(v)
                if kind=='pie' and (min(s['values'])<=0 or sum(s['values'])<=0): fail('円グラフは正の構成値を指定してください')
                if 'errors' in s:
                    for v in seq(s['errors'],n,n):
                        if number(v)<0: fail('誤差は0以上です')
            elif kind=='line':
                strings(s['labels'],2,8,12); clean(s['unit'],12)
                for a in seq(s['series'],1,3):
                    keys(a,['name','values']); clean(a['name'],12)
                    for v in seq(a['values'],len(s['labels']),len(s['labels'])): number(v)
                if len({a['name'] for a in s['series']})!=len(s['series']): fail('系列名を重複させないでください')
            elif kind=='scatter':
                clean(s['x_label'],24); clean(s['y_label'],24)
                for p in seq(s['points'],2,16):
                    keys(p,['x','y','label']); number(p['x']); number(p['y']); clean(p['label'],10)
        except (ValueError,TypeError) as e: fail(f'{i}ページ目: {e}')
    theme=THEMES[data.get('theme','neutral')]
    for fg in ('ink','muted','accent'):
        for bg in ('background','surface'):
            if contrast(theme[fg],theme[bg])<4.5: fail('テーマの文字コントラスト不足')

E=lambda v: html.escape(str(v),quote=True)
def fmt(v): return format(v, ',') if isinstance(v,(int,float)) else v

def tagtext(x,y,value,anchor='start',size=20,fill='var(--ink)'):
    return f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" font-size="{size}" fill="{fill}">{E(value)}</text>'

def pathline(x1,y1,x2,y2,extra=''):
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="var(--muted)" stroke-width="1.5" {extra}/>'

def svgbody(body,label):
    return f'<svg class="chart" viewBox="0 0 1152 390" role="img" aria-label="{E(label)}">{body}</svg>'

def datatable(headers,rows):
    return '<table><thead><tr>'+''.join('<th scope="col">'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(fmt(v))+'</td>' for v in r)+'</tr>' for r in rows)+'</tbody></table>'

def chart(s):
    kind=s['type']; b=[]; x0,x1=110,890; y0,y1=36,324
    if kind=='bar':
        vals=s['values']; err=s.get('errors',[0]*len(vals)); low=min(0,min(v-e for v,e in zip(vals,err))); high=max(0,max(v+e for v,e in zip(vals,err)))
        if low==high: high=1
        scale=lambda v: 235+(v-low)/(high-low)*680
        for k in range(5):
            v=low+(high-low)*k/4; x=scale(v)
            b += [pathline(x,28,x,342,'opacity="0.16"'),tagtext(x,370,format(v,'.4g'),'middle',17)]
        for i,(label,v) in enumerate(zip(s['labels'],vals)):
            y=40+i*300/len(vals); h=min(26,210/len(vals))
            a,z=sorted([scale(0),scale(v)])
            b += [tagtext(215,y+h*.8,label,'end',19),f'<rect x="{a}" y="{y}" width="{max(0,z-a)}" height="{h}" fill="var(--accent)"/>',tagtext(1115,y+h*.8,fmt(v),'end',18)]
            if err[i]:
                l,r=scale(v-err[i]),scale(v+err[i]); cy=y+h/2
                b += [pathline(l,cy,r,cy),pathline(l,cy-7,l,cy+7),pathline(r,cy-7,r,cy+7)]
        b += [pathline(scale(0),28,scale(0),342),tagtext(1115,370,s['unit'],'end',17)]
        rows=[[l,v]+([e] if 'errors' in s else []) for l,v,e in zip(s['labels'],vals,err)]
        headers=['項目',s['unit']]+(['誤差（±）'] if 'errors' in s else [])
    elif kind in ('line','scatter'):
        if kind=='line':
            xs=list(range(len(s['labels']))); ys=[v for a in s['series'] for v in a['values']]
        else: xs=[p['x'] for p in s['points']]; ys=[p['y'] for p in s['points']]
        xmin,xmax=min(xs),max(xs); ymin,ymax=min(0,min(ys)),max(0,max(ys))
        if xmax==xmin: xmin-=.5; xmax+=.5
        if ymax==ymin: ymax=ymin+1
        if kind=='scatter':
            pad=(xmax-xmin)*.06; xmin-=pad; xmax+=pad
            pad=(ymax-ymin)*.06; ymin-=pad; ymax+=pad
        X=lambda v:x0+(v-xmin)/(xmax-xmin)*(x1-x0)
        Y=lambda v:y1-(v-ymin)/(ymax-ymin)*(y1-y0)
        for k in range(5):
            v=ymin+(ymax-ymin)*k/4; y=Y(v)
            b += [pathline(x0,y,x1,y,'opacity="0.16"'),tagtext(x0-14,y+6,format(v,'.4g'),'end',16)]
        b += [pathline(x0,y1,x1,y1),tagtext(x0,20,s.get('unit',s.get('y_label')),'start',17)]
        if kind=='line':
            for i,l in enumerate(s['labels']): b.append(tagtext(X(i),355,l,'middle',17))
            ends=sorted([(Y(a['values'][-1]),j) for j,a in enumerate(s['series'])]); pos={}; last=-50
            for yy,j in ends: pos[j]=max(yy,last+30); last=pos[j]
            shift=max(0,last-335); pos={j:y-shift for j,y in pos.items()}
            for j,a in enumerate(s['series']):
                points=' '.join(f'{X(i)},{Y(v)}' for i,v in enumerate(a['values'])); dash=['','8 5','2 5'][j]
                b.append(f'<polyline points="{points}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-dasharray="{dash}"/>')
                for i,v in enumerate(a['values']):
                    x,y=X(i),Y(v)
                    if j==1: b.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="var(--background)" stroke="var(--accent)" stroke-width="2"/>')
                    else: b.append(f'<circle cx="{x}" cy="{y}" r="4" fill="'+('var(--accent)' if j==0 else 'var(--background)')+'" stroke="var(--accent)" stroke-width="2"/>')
                yy=Y(a['values'][-1]); ly=pos[j]
                b += [pathline(x1+8,yy,x1+26,ly),tagtext(x1+34,ly+6,a['name'],'start',18)]
            headers=['時点']+[a['name']+'（'+s['unit']+'）' for a in s['series']]
            rows=[[l]+[a['values'][i] for a in s['series']] for i,l in enumerate(s['labels'])]
        else:
            for k in range(5):
                v=xmin+(xmax-xmin)*k/4; b.append(tagtext(X(v),353,format(v,'.4g'),'middle',16))
            b.append(tagtext((x0+x1)/2,386,s['x_label'],'middle',18))
            for p in s['points']:
                x,y=X(p['x']),Y(p['y']); b += [f'<circle cx="{x}" cy="{y}" r="5" fill="var(--accent)"/>',tagtext(x+10,y-9,p['label'],'start',16)]
            headers=['項目',s['x_label'],s['y_label']]; rows=[[p['label'],p['x'],p['y']] for p in s['points']]
    else:
        total=sum(s['values']); angle=-math.pi/2; labels=[]
        for i,(label,v) in enumerate(zip(s['labels'],s['values'])):
            end=angle+v/total*math.tau; mid=(angle+end)/2; cx,cy,r=540,190,130
            a=(cx+r*math.cos(angle),cy+r*math.sin(angle)); z=(cx+r*math.cos(end),cy+r*math.sin(end))
            shade=['var(--accent)','#717B82','#929BA1','#B3BABD','#D3D8D9'][i]
            b.append(f'<path d="M{cx},{cy} L{a[0]},{a[1]} A{r},{r} 0 {int(end-angle>math.pi)} 1 {z[0]},{z[1]} Z" fill="{shade}" stroke="var(--background)" stroke-width="2"/>')
            right=math.cos(mid)>=0; yy=cy+165*math.sin(mid)
            labels.append(dict(y=yy,right=right,x=cx+r*math.cos(mid),py=cy+r*math.sin(mid),text=f'{label} {v/total*100:.1f}%'))
            angle=end
        for right in (False,True):
            group=sorted([a for a in labels if a['right']==right],key=lambda a:a['y']); last=10
            for a in group: a['y']=max(a['y'],last+34); last=a['y']
            shift=max(0,last-360)
            for a in group:
                y=a['y']-shift; x=720 if right else 360
                b += [pathline(a['x'],a['py'],x,y),tagtext(x+(10 if right else -10),y+6,a['text'],'start' if right else 'end',20)]
        headers=['項目',s['unit'],'構成比']; rows=[[l,v,f'{v/total*100:.1f}%'] for l,v in zip(s['labels'],s['values'])]
    return svgbody(''.join(b),s['title']),datatable(headers,rows)

def image_asset(value,base):
    p=(base/value).resolve()
    if not p.is_relative_to(base.resolve()): fail('画像は入力JSONと同じフォルダか配下に置いてください')
    if p.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'): fail('画像はPNG/JPEG/WebPのみ対応します')
    if p.stat().st_size>15*1024*1024: fail('画像は15MB以下にしてください')
    # Optional Pillow checks orientation and original dimensions. Never crop or distort.
    try:
        from PIL import Image, ImageOps
    except ImportError: fail('写真を使う場合は pip install Pillow を実行してください')
    import io
    with Image.open(p) as im:
        if im.width*im.height>40_000_000: fail('画像は4000万画素以下にしてください')
        im=ImageOps.exif_transpose(im); dimensions=im.size
        buf=io.BytesIO()
        if im.mode in ('RGBA','LA','P') or p.suffix.lower()=='.png':
            im.save(buf,format='PNG'); mime='image/png'
        else:
            im.convert('RGB').save(buf,format='JPEG',quality=94); mime='image/jpeg'
    return 'data:'+mime+';base64,'+base64.b64encode(buf.getvalue()).decode(),dimensions

def content(s,base,warnings,index):
    kind=s['type']; semantic=''
    items=lambda a:'<ul class="plain">'+''.join('<li>'+E(t)+'</li>' for t in a)+'</ul>'
    if kind=='cover': return '<p class="subtitle">'+E(s['subtitle'])+'</p><div class="meta">'+''.join('<p>'+E(t)+'</p>' for t in s.get('meta',[]))+'</div>', ''
    if kind=='text': return items(s['items']),''
    if kind in ('sections','compare'):
        gs=s['groups' if kind=='sections' else 'columns']
        return '<div class="'+kind+'">'+''.join('<div class="group"><h2>'+E(g['heading'])+'</h2>'+items(g['items'])+'</div>' for g in gs)+'</div>',''
    if kind=='flow':
        return '<ol class="flow">'+''.join('<li><span class="step">'+f'{i+1:02}'+'</span><p>'+E(t)+'</p></li>' for i,t in enumerate(s['steps']))+'</ol><p class="relation">'+('手順・時間の順序' if s['relation']=='sequence' else '因果関係：出典参照')+'</p>',''
    if kind=='cycle':
        b=['<defs><marker id="tip'+str(index)+'" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="var(--muted)"/></marker></defs>']
        n=len(s['steps']); coords=[(576+365*math.cos(-math.pi/2+i*math.tau/n),195+135*math.sin(-math.pi/2+i*math.tau/n)) for i in range(n)]
        for i,(x,y) in enumerate(coords):
            nx,ny=coords[(i+1)%n]; dx,dy=nx-x,ny-y; dist=math.hypot(dx,dy); a=min(.4,115/dist)
            b.append(pathline(x+dx*a,y+dy*a,nx-dx*a,ny-dy*a,f'marker-end="url(#tip{index})"'))
        for i,(x,y) in enumerate(coords):
            b += [f'<rect x="{x-155}" y="{y-29}" width="310" height="58" fill="var(--surface)"/>',tagtext(x,y+8,f'{i+1}. '+s['steps'][i],'middle',22)]
        return svgbody(''.join(b),s['title']),'<ol>'+''.join('<li>'+E(t)+'</li>' for t in s['steps'])+'</ol><p>最後の項目から最初の項目へ戻る循環。</p>'
    if kind=='hierarchy':
        edge=(1152-32*(len(s['children'])-1))/len(s['children'])/2
        return '<div class="tree"><h2>'+E(s['root'])+f'</h2><ul style="--edge:{edge}px">'+''.join('<li>'+E(t)+'</li>' for t in s['children'])+'</ul></div>',''
    if kind=='table':
        n=len(s['headers']); aligns=s.get('align',['right' if all(isinstance(r[j],(int,float)) for r in s['rows']) else 'left' for j in range(n)])
        def cell(v,j,tag): return f'<{tag} style="text-align:{aligns[j]}"'+(' scope="col"' if tag=='th' else '')+'>'+E(fmt(v))+f'</{tag}>'
        return '<table class="'+('striped' if s.get('striped',False) else '')+'"><thead><tr>'+''.join(cell(v,j,'th') for j,v in enumerate(s['headers']))+'</tr></thead><tbody>'+''.join('<tr>'+''.join(cell(v,j,'td') for j,v in enumerate(r))+'</tr>' for r in s['rows'])+'</tbody></table>',''
    if kind=='image':
        uri,(w,h)=image_asset(s['image'],base)
        if w<1000 or h<600: warnings.append(f'{index}ページ：画像 {w}×{h}px。表示・印刷サイズで鮮明さを確認してください。')
        annotations=s.get('annotations',[])
        # Markers positioned over a same-aspect-ratio wrapper, so coordinates target the image itself.
        marks=''.join(f'<span class="annotation" style="left:{a["x"]*100}%;top:{a["y"]*100}%">{i+1}</span>' for i,a in enumerate(annotations))
        display_w=min(660,340*w/h); display_h=display_w*h/w
        figure=f'<figure><div class="photo" style="aspect-ratio:{w}/{h};width:{display_w}px;height:{display_h}px"><img src="{uri}" alt="{E(s["alt"])}">{marks}</div><figcaption>{E(s["caption"])}</figcaption></figure>'
        notes=items(s.get('items',[]))+'<ol class="annotation-list">'+''.join('<li>'+E(a['label'])+'</li>' for a in annotations)+'</ol>'
        return '<div class="image-layout">'+figure+'<div>'+notes+'</div></div>',''
    return chart(s)

def generate(data,base=None):
    validate(data); base=Path(base or '.'); warnings=[]; pages=[]
    for i,s in enumerate(data['slides'],1):
        try: body,semantic=content(s,base,warnings,i)
        except (ValueError,OSError) as e: fail(f'{i}ページ目: {e}')
        kind=s['type']
        if kind in ('scatter','pie'): warnings.append(f'{i}ページ：直接ラベルと図の対応・重なりを表示環境で確認してください。')
        source=s.get('source','')
        pages.append(f'<section class="slide {kind}" aria-label="{i}ページ"><header><h1>{E(s["title"])}</h1>'+('' if kind=='cover' else '<p class="message">'+E(s['message'])+'</p>')+'</header><div class="content">'+body+'</div><footer><span>'+E(source)+'</span><span>'+f'{i:02} / {len(data["slides"]):02}'+'</span></footer></section>'+('<div class="accessible-data"><h2>'+E(s['title'])+'：データ・読み順</h2>'+semantic+'</div>' if semantic else ''))
    theme=THEMES[data.get('theme','neutral')]; css=(ROOT/'style.css').read_text(); js=(ROOT/'viewer.js').read_text()
    font_path=ROOT/'assets/NotoSansJP.ttf'
    if font_path.exists():
        css="@font-face{font-family:'Noto Sans JP';font-style:normal;font-weight:100 900;src:url(data:font/ttf;base64,"+base64.b64encode(font_path.read_bytes()).decode()+") format('truetype');}"+css
    variables=':root{'+''.join('--'+k+':'+v+';' for k,v in theme.items())+'}'
    document='<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+E(data['title'])+'</title><style>'+variables+css+'</style></head><body><nav><strong>'+E(data['title'])+'</strong><button id="mode" type="button">読む表示</button><button id="print" type="button">印刷 / PDF</button><span id="status" role="status">表示を検査中</span></nav><main>'+''.join(pages)+'</main><script>'+js+'</script></body></html>'
    return document, {'version':VERSION,'pages':len(pages),'slides':len(data['slides']),'status':'structure_validated','browser_check':'open_html_required','warnings':warnings,'contrast':{k:round(contrast(theme[k],theme['background']),2) for k in ('ink','muted','accent')}}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path); parser.add_argument('-o','--output',type=Path,default=Path('slides.html'))
    parser.add_argument('--validate-only',action='store_true'); args=parser.parse_args()
    try:
        data=json.loads(args.input.read_text(encoding='utf-8')); document,report=generate(data,args.input.resolve().parent)
        if not args.validate_only:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            tmp=args.output.with_suffix(args.output.suffix+'.tmp'); tmp.write_text(document,encoding='utf-8'); os.replace(tmp,args.output)
            args.output.with_suffix('.report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2)); return 0
    except (ValueError,OSError) as e: print('生成を停止しました: '+str(e),file=sys.stderr); return 1
if __name__=='__main__': sys.exit(main())
