(function(){
  const F=[
    {id:'fightclub',t:'Fight Club',y:1999,dir:'Fincher',run:'2H19',mood:'excited',
      acc:"La Chine l'a <b>censuré et réécrit</b> : dans leur version, la police gagne à la fin."},
    {id:'shining',t:'The Shining',y:1980,dir:'Kubrick',run:'2H26',mood:'scared',
      acc:"Kubrick a fait refaire la scène de la porte <b>127 fois</b>. Nicholson a failli craquer."},
    {id:'parasite',t:'Parasite',y:2019,dir:'Bong Joon-ho',run:'2H12',mood:'excited',
      acc:"Premier film <b>non-anglophone</b> à rafler l'Oscar du meilleur film. 92 ans d'attente."},
    {id:'angry',t:'12 Angry Men',y:1957,dir:'Lumet',run:'1H36',mood:'brain',
      acc:"<b>Top 5 IMDb</b> depuis 60 ans. Budget : une pièce, douze chaises, zéro effet."},
    {id:'eternal',t:'Eternal Sunshine',y:2004,dir:'Gondry',run:'1H48',mood:'romantic',
      acc:"Kaufman l'a écrit <b>une nuit d'insomnie</b>. La plage qui s'efface : aucun effet numérique."},
    {id:'lost',t:'Lost in Translation',y:2003,dir:'Coppola',run:'1H42',mood:'sad',
      acc:"Tourné en <b>27 jours</b> à Tokyo. Le murmure final ? Personne ne sait ce qu'il dit."},
    {id:'lebowski',t:'The Big Lebowski',y:1998,dir:'Coen',run:'1H57',mood:'chill',
      acc:"Le Dude est basé sur un <b>vrai mec</b>. Il vit toujours à Los Angeles, tranquille."}
  ];
  // Typo variée : chaque film porte sa propre typo de titre (toujours rendue en 3D rouge).
  // guillemets SIMPLES : ces valeurs partent dans un attribut style="..." (double quotes)
  const FT={
    fightclub:"'Impact','Haettenschweiler','Arial Narrow',sans-serif",
    shining:  "'Didot','Bodoni 72','Playfair Display',Georgia,serif",
    parasite: "'Futura','Avenir Next','Century Gothic',sans-serif",
    angry:    "'American Typewriter','Courier New',monospace",
    eternal:  "'Baskerville','Iowan Old Style',Georgia,serif",
    lost:     "'Arial Narrow','Helvetica Neue',sans-serif",
    lebowski: "'Futura','Avenir Next',sans-serif"
  };
  F.forEach(f=>f.font=FT[f.id]||"var(--disp)");
  const MOODS=[{k:'chill',l:'POSÉ'},{k:'excited',l:'À FOND'},{k:'brain',l:'CÉRÉBRAL'},{k:'scared',l:'FRISSONS'},{k:'sad',l:'DOWN'},{k:'romantic',l:'LE CŒUR'}];

  // mood-drift : biais colorimétrique du dither + ambiance de fond (toujours sombre, punch rouge préservé)
  const THEME={
    ''      :{bias:[0,0,0],    page:'#07080B', scr:'#080a0e'},
    sad     :{bias:[-9,0,17],  page:'#05070E', scr:'#070A13'},
    brain   :{bias:[-7,2,13],  page:'#06080D', scr:'#080B12'},
    scared  :{bias:[-5,-4,15], page:'#07060E', scr:'#090814'},
    excited :{bias:[21,4,-11], page:'#0E0705', scr:'#130A08'},
    chill   :{bias:[19,11,-13],page:'#0D0A05', scr:'#120E08'},
    romantic:{bias:[17,-2,5],  page:'#0D0709', scr:'#12090C'}
  };

  const SIZE={
    fin:  {hero:[236,162], grid:[150,200], ban:[400,165]},
    moyen:{hero:[176,121], grid:[120,160], ban:[320,132]},
    gros: {hero:[116,80],  grid:[84,112],  ban:[176,73]}
  };

  const PAL_NIGHT=[[10,12,16],[20,28,40],[34,46,60],[52,74,84],[80,104,112],[120,110,72],[168,138,84],[208,178,120],[234,228,212],[150,58,58],[214,32,28]];
  const PAL_1BIT=[[9,11,15],[230,224,208]];
  const BAYER=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]];

  const IMG={};
  function nearest(pal,r,g,b){let bi=0,bd=1e9;for(let i=0;i<pal.length;i++){const p=pal[i],dr=r-p[0],dg=g-p[1],db=b-p[2],d=dr*dr+dg*dg+db*db;if(d<bd){bd=d;bi=i;}}return pal[bi];}
  function drawCover(ctx,img,w,h){
    const ar=w/h, iar=img.width/img.height; let sw,sh,sx,sy;
    if(iar>ar){sh=img.height;sw=sh*ar;sx=(img.width-sw)/2;sy=0;} else {sw=img.width;sh=sw/ar;sx=0;sy=(img.height-sh)/2;}
    ctx.drawImage(img,sx,sy,sw,sh,0,0,w,h);
  }
  function dither(cv,film,mode,phase,bias){
    const img=IMG[film.id]; if(!img||!img.complete) return;
    const w=cv.width,h=cv.height,ctx=cv.getContext('2d',{willReadFrequently:true});
    drawCover(ctx,img,w,h);
    const im=ctx.getImageData(0,0,w,h),d=im.data;
    const spread=mode==='onebit'?102:60, ph=(phase||0), bx=bias||[0,0,0];
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const i=(y*w+x)*4;
      let r=(d[i]-128)*1.14+128-14+bx[0], g=(d[i+1]-128)*1.14+128-12+bx[1], b=(d[i+2]-128)*1.10+128-2+bx[2];
      const t=(BAYER[(y+ph)&3][(x+ph*2)&3]/16-0.5)*spread;
      r+=t; g+=t; b+=t;
      if(mode==='onebit'){
        if(d[i]>140&&d[i+1]<86&&d[i+2]<86){d[i]=214;d[i+1]=30;d[i+2]=26;continue;}
        const lum=0.299*r+0.587*g+0.114*b, c=lum>128?PAL_1BIT[1]:PAL_1BIT[0];
        d[i]=c[0];d[i+1]=c[1];d[i+2]=c[2];
      }else{const c=nearest(PAL_NIGHT,r,g,b);d[i]=c[0];d[i+1]=c[1];d[i+2]=c[2];}
    }
    ctx.putImageData(im,0,0);
  }

  const stage=document.getElementById('stage'),screen=document.getElementById('screen');
  const heroEl=document.getElementById('hero'),gridEl=document.getElementById('grid'),moodsEl=document.getElementById('moods');
  let mode='night',size='moyen',mood='',phase=0,curBias=[0,0,0],targetBias=[0,0,0],driftRAF=null,hoverTimer=null;
  const reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion:reduce)').matches;

  moodsEl.innerHTML=MOODS.map(m=>`<span class="chip" data-mood="${m.k}">${m.l}</span>`).join('');
  function hero(){if(mood){const f=F.find(x=>x.mood===mood);if(f)return f;}return F[0];}
  function heroCanvas(){return heroEl.querySelector('.poster canvas');}

  function renderHero(){
    const f=hero(),s=SIZE[size].hero;
    heroEl.innerHTML=`<div class="poster"><canvas width="${s[0]}" height="${s[1]}"></canvas><span class="code">PIÈCE ${String(F.indexOf(f)+1).padStart(2,'0')}</span><span class="hint">survole — grain animé</span></div>
      <div class="body">
        <div class="film-title" style="font-family:${f.font}">${f.t}</div>
        <div class="metaline">${f.y} · ${f.run} · <span class="d">${f.dir}</span></div>
        <div class="why">L'accroche</div>
        <div class="accroche">${f.acc}</div>
        <span class="cta">Bande-annonce</span>
      </div>`;
    dither(heroCanvas(),f,mode,phase,curBias);
    dither(document.getElementById('banner'),f,mode,phase,curBias);
    renderSteps(f);
  }
  function renderGrid(){
    const list=F.filter(f=>f!==hero()).slice(0,4),s=SIZE[size].grid;
    gridEl.innerHTML=list.map(f=>{const dim=mood&&f.mood!==mood?' dim':'';
      return `<div class="film${dim}" data-id="${f.id}"><div class="art"><canvas width="${s[0]}" height="${s[1]}"></canvas></div><div class="cap"><div class="t" style="font-family:${f.font}">${f.t}</div><div class="y">${f.y} · ${f.dir}</div></div></div>`;
    }).join('');
    list.forEach(f=>dither(gridEl.querySelector(`[data-id="${f.id}"] canvas`),f,mode,0,curBias));
  }
  function renderSteps(f){
    const a=document.getElementById('stepA'); drawCover(a.getContext('2d'),IMG[f.id],a.width,a.height);
    dither(document.getElementById('stepB'),f,mode,phase,curBias);
  }
  function resizeBanner(){const b=document.getElementById('banner'),s=SIZE[size].ban;b.width=s[0];b.height=s[1];}
  function renderAll(){resizeBanner();renderHero();renderGrid();}

  // --- mood-drift : lerp du biais + ambiance CSS ---
  function applyMood(){
    const th=THEME[mood]||THEME[''];
    targetBias=th.bias.slice();
    stage.style.backgroundColor=th.page; screen.style.backgroundColor=th.scr;
    if(driftRAF)cancelAnimationFrame(driftRAF);
    if(reduce){curBias=targetBias.slice();renderHero();renderGrid();return;}
    (function step(){
      let done=true;
      for(let i=0;i<3;i++){const dd=targetBias[i]-curBias[i];if(Math.abs(dd)>0.4){curBias[i]+=dd*0.14;done=false;}else curBias[i]=targetBias[i];}
      dither(heroCanvas(),hero(),mode,phase,curBias);
      dither(document.getElementById('banner'),hero(),mode,phase,curBias);
      dither(document.getElementById('stepB'),hero(),mode,phase,curBias);
      if(!done)driftRAF=requestAnimationFrame(step); else renderGrid();
    })();
  }

  // --- grain animé au survol du poster seulement ---
  heroEl.addEventListener('mouseenter',e=>{
    if(reduce||!e.target.closest('.poster'))return;
    if(hoverTimer)clearInterval(hoverTimer);
    hoverTimer=setInterval(()=>{phase=(phase+1)&3;dither(heroCanvas(),hero(),mode,phase,curBias);dither(document.getElementById('banner'),hero(),mode,phase,curBias);},120);
  },true);
  heroEl.addEventListener('mouseleave',e=>{
    if(hoverTimer){clearInterval(hoverTimer);hoverTimer=null;}
    phase=0;dither(heroCanvas(),hero(),mode,phase,curBias);dither(document.getElementById('banner'),hero(),mode,phase,curBias);
  },true);

  document.querySelector('.controls').addEventListener('click',e=>{
    const b=e.target.closest('button'); if(!b)return;
    const k=b.dataset.k,v=b.dataset.v;
    b.parentElement.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',x===b));
    if(k==='mode'){mode=v;renderAll();}
    if(k==='size'){size=v;renderAll();}
  });
  moodsEl.addEventListener('click',e=>{const c=e.target.closest('.chip');if(!c)return;
    mood=(mood===c.dataset.mood)?'':c.dataset.mood;
    moodsEl.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',x.dataset.mood===mood));
    document.getElementById('moodPrompt').textContent=mood?'Ce qu\'il te faut':'Ce soir, tu es';
    renderHero();applyMood();
  });
  document.getElementById('times').addEventListener('click',e=>{const t=e.target.closest('.time');if(!t)return;
    document.querySelectorAll('#times .time').forEach(x=>x.classList.remove('on'));t.classList.add('on');});

  const ids=Object.keys(POSTERS);let n=0;
  ids.forEach(id=>{const im=new Image();im.onload=()=>{if(++n===ids.length)renderAll();};im.onerror=()=>{if(++n===ids.length)renderAll();};im.src=POSTERS[id];IMG[id]=im;});
})();
