/* Original procedural motion sculpture. WebGL 1, no downloads or frame decoding. */
export function mountCinema(root){
 const story=root.querySelector('.film-story');let canvas=root.querySelector('.film-canvas');
 if(!story||!canvas)return ()=>{};
 const stage=canvas.parentElement, beats=[...story.querySelectorAll('.film-beat')],steps=[...story.querySelectorAll('.film-step')];
 const reduce=matchMedia('(prefers-reduced-motion: reduce)');
 const clamp=(x,a=0,b=1)=>Math.max(a,Math.min(b,x));
 const smooth=(a,b,x)=>{let t=clamp((x-a)/(b-a));return t*t*(3-2*t)};
 let gl,program,buffer,indices,raf=0,alive=true,target=0,p=0,mouseX=0,mouseY=0,mx=0,my=0,last=0,clock=0,visible=true,lastScene=-1,quality=1,slow=0,frames=0,rendering=false;
 const vertex=`
 precision highp float;
 attribute vec2 uv;
 uniform float uP,uT,uSide,uAspect,uMobile,uAtlas;
 uniform vec2 uMouse;
 varying vec3 vN,vPos;
 varying vec2 vUV;
 varying float vSide;
 const float PI=3.14159265359;
 mat2 rot(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}
 vec3 spine(float t,float k){
   float a=6.2831853*t;
   float b=mix(0.,1.,smoothstep(.03,.48,uP));
   float c=smoothstep(.55,1.,uP);
   float side=k*2.-1.;
   float phase=a+side*(.45+.65*b)+uT*.13;
   vec3 separated=vec3(1.26*cos(phase),1.48*sin(phase),.47*sin(2.*phase+side*.7)+side*.25);
   separated.x+=side*.74; separated.xy=rot(side*.22)*separated.xy;
   float r=1.05+.30*cos(3.*phase+side*.45)+side*.18;
   vec3 joined=vec3(r*cos(2.*phase),r*sin(2.*phase),.57*sin(3.*phase+side*.8)+side*.32);
   joined.xy=rot(.35)*joined.xy;
   vec3 opened=vec3(1.68*cos(a+side*.4),1.13*sin(a+side*.4),.64*sin(2.*a+side*.9)+side*.22);
   opened.x+=side*.42; opened.xy=rot(side*.42)*opened.xy;
   return mix(mix(separated,joined,b),opened,c);
 }
 vec3 surf(float t,float v,float k){
   vec3 center=spine(t,k),tangent=normalize(spine(t+.001,k)-spine(t-.001,k));
   vec3 normal=normalize(cross(tangent,vec3(0.,0.,1.)));
   vec3 binormal=normalize(cross(tangent,normal));
   float angle=6.2831853*t*2.+k*1.4+sin(t*6.2831853+uP*3.)*.72+uT*.11;
   vec3 across=normal*cos(angle)+binormal*sin(angle);
   vec3 up=normalize(cross(tangent,across));
   float width=(.32+.18*pow(.5+.5*sin(t*6.2831853*3.+k),1.4))*(1.-.18*sin(uP*PI));
   float rib=sin(t*6.2831853*12.+v*6.+k)*.025;
   return center+across*v*width+up*(.13*(1.-v*v)+rib*(1.-v*v)+.018*sin(v*14.+t*31.4159265));
 }
 vec3 camera(vec3 v){
   float r=uP*1.65-.36+uMouse.x*.13+sin(uT*.18)*.055;
   v.xz=rot(r)*v.xz;
   v.yz=rot(-.24+.36*sin(uP*PI)+uMouse.y*.12)*v.yz;
   v.xy=rot(-.12+uP*.28)*v.xy;
   return v;
 }
 void main(){
   float t=uv.x,v=uv.y*2.-1.;
   vec3 raw=surf(t,v,uSide);
   vec3 tang=surf(t+.001,v,uSide)-surf(t-.001,v,uSide);
   vec3 across=surf(t,v+.002,uSide)-surf(t,v-.002,uSide);
   vec3 pos=camera(raw);
   vN=normalize(camera(normalize(cross(tang,across))));vPos=pos;vUV=uv;vSide=uSide;
   float perspective=4.5/(4.5-pos.z);
   float mobile=uMobile;
   float zoom=mix(.85+.30*sin(uP*PI),.69+.06*sin(uP*PI),mobile);
   float shift=mix(.43-.86*smoothstep(.12,.60,uP)+.43*smoothstep(.66,.99,uP),0.,mobile);
   float yshift=mix(.02,.36,mobile);
   zoom=mix(zoom,.58,uAtlas);shift=mix(shift,0.,uAtlas);yshift=mix(yshift,0.,uAtlas);
   vec2 xy=pos.xy*perspective*zoom;
   xy.x/=max(1.,uAspect);xy.y*=min(1.,uAspect);
   gl_Position=vec4(xy*.51+vec2(shift,yshift),-pos.z*.14,1.);
 }`;
 const fragment=`
 precision highp float;
 varying vec3 vN,vPos;varying vec2 vUV;varying float vSide;
 uniform float uP,uT;
 void main(){
   vec3 n=normalize(vN);if(!gl_FrontFacing)n=-n;
   vec3 V=normalize(vec3(0.,0.,4.5)-vPos);
   vec3 L=normalize(vec3(-.8,1.25,1.8));vec3 R=normalize(vec3(1.,-.25,.4));
   float d=max(0.,dot(n,L)),d2=max(0.,dot(n,R));
   float spec=pow(max(0.,dot(n,normalize(L+V))),27.);
   float spec2=pow(max(0.,dot(n,normalize(R+V))),64.);
   float fres=pow(1.-max(0.,dot(n,V)),2.4);
   float filament=.5+.5*cos(vUV.y*310.+sin(vUV.x*50.)*1.4);
   float fine=.5+.5*cos(vUV.y*730.+vUV.x*7.);
   float edge=pow(abs(vUV.y*2.-1.),18.);
   vec3 copper=vec3(.83,.25,.13), pearl=vec3(.35,.64,.66);
   copper=mix(copper,vec3(.92,.52,.26),smoothstep(.6,1.,uP));
   pearl=mix(pearl,vec3(.85,.74,.51),smoothstep(.55,1.,uP));
   vec3 base=mix(copper,pearl,vSide);
   vec3 col=base*(.21+.77*d+.32*d2)*(.91+.075*filament+.015*fine);
   col+=vec3(1.,.87,.65)*(spec*.72+spec2*.54);
   col+=mix(vec3(.98,.38,.17),vec3(.50,.94,.91),vSide)*fres*.34;
   col+=mix(vec3(1.,.59,.31),vec3(.89,1.,.94),vSide)*edge*(.22+.28*d);
   gl_FragColor=vec4(col,1.);
 }`;
 function compile(type,src){const s=gl.createShader(type);gl.shaderSource(s,src);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
 function init(){
   if(reduce.matches)return false;
   try{gl=canvas.getContext('webgl',{alpha:true,antialias:true,depth:true,premultipliedAlpha:false,powerPreference:'high-performance'});if(!gl)return false;
   program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,vertex));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
   const U=innerWidth<700?160:230,V=innerWidth<700?24:36,verts=[],inds=[];for(let i=0;i<=U;i++)for(let j=0;j<=V;j++)verts.push(i/U,j/V);
   for(let i=0;i<U;i++)for(let j=0;j<V;j++){let a=i*(V+1)+j,b=a+V+1;inds.push(a,b,a+1,a+1,b,b+1);}
   buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(verts),gl.STATIC_DRAW);
   indices=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,indices);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(inds),gl.STATIC_DRAW);
   gl.useProgram(program);const a=gl.getAttribLocation(program,'uv');gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);
   gl.enable(gl.DEPTH_TEST);gl.clearColor(0,0,0,0);gl.disable(gl.CULL_FACE);
   const names=['uP','uT','uSide','uAspect','uMobile','uMouse','uAtlas'];const locations=Object.fromEntries(names.map(n=>[n,gl.getUniformLocation(program,n)]));
   const draw=()=>{let w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;let d=Math.min(devicePixelRatio||1,w<700?1.25:1.65)*quality;let cw=Math.round(w*d),ch=Math.round(h*d);if(canvas.width!==cw||canvas.height!==ch){canvas.width=cw;canvas.height=ch;gl.viewport(0,0,cw,ch);}gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.uniform1f(locations.uP,p);gl.uniform1f(locations.uT,clock);gl.uniform1f(locations.uAspect,w/h);gl.uniform1f(locations.uMobile,w<700?1:0);gl.uniform1f(locations.uAtlas,0);gl.uniform2f(locations.uMouse,mx,my);for(let k=0;k<2;k++){gl.uniform1f(locations.uSide,k);gl.drawElements(gl.TRIANGLES,inds.length,gl.UNSIGNED_SHORT,0);}canvas.dataset.renderer='webgl';canvas.classList.add('rendered');};
   return draw;
   }catch(e){console.warn('Between: static art fallback',e.message);return false;}
 }
  function initAtlas(){
   // Decode nine frames at once. Keep nearby atlases warm, interpolate adjacent
   // frames on the canvas, and never re-fetch a frame on every scroll event.
   let ctx=canvas.getContext('2d',{alpha:true});
   if(!ctx){const replacement=canvas.cloneNode(false);canvas.replaceWith(replacement);canvas=replacement;ctx=canvas.getContext('2d',{alpha:true});}
   if(!ctx)return false;
   const count=108,cell=768,cache=new Map();let last=null,lastW=0,lastH=0,lastD=0,lastKey="";
   function load(sheet){if(sheet<0||sheet>=12)return null;if(cache.has(sheet))return cache.get(sheet);const img=new Image();const data={img,ready:false,error:false};cache.set(sheet,data);img.decoding='async';img.onload=()=>{img.decode().then(()=>{data.ready=true;}).catch(()=>{data.ready=img.complete&&img.naturalWidth>0;});};img.onerror=()=>{data.error=true;};img.src=globalThis.BETWEEN_ATLASES?.[sheet]||`./atlases/${String(sheet).padStart(2,'0')}.webp`;return data;}
   function warm(index,goal=index){const i=Math.floor(index/9),g=Math.floor(goal/9),keep=new Set([i,i+1,i-1,g,g+(goal>=index?1:-1)]);for(const k of keep)load(k);for(const k of cache.keys())if(!keep.has(k))cache.delete(k);}
   function find(index){index=clamp(index,0,count-1);const sheet=Math.floor(index/9),data=load(sheet);if(!data?.ready)return null;const pos=index%9;return {img:data.img,x:(pos%3)*cell,y:Math.floor(pos/3)*cell};}
   warm(Math.round(target*(count-1)));canvas.dataset.renderer='atlas';
   return ()=>{const w=stage.clientWidth,h=stage.clientHeight;if(!w||!h)return;let d=Math.min(devicePixelRatio||1,w<700?1.3:1.65)*quality;
     if(w!==lastW||h!==lastH||d!==lastD){canvas.width=Math.round(w*d);canvas.height=Math.round(h*d);lastW=w;lastH=h;lastD=d;}
     const f=p*(count-1),i=Math.floor(f),mix=f-i;warm(i,Math.round(target*(count-1)));const a=find(i),b=find(i+1);if(a)last=a;else if(b)last=b;if(!last)return;
     const key=[f.toFixed(3),mx.toFixed(3),my.toFixed(3),w,h,d,Boolean(a),Boolean(b)].join('|');if(key===lastKey)return;lastKey=key;
     let mobile=w<700,zoom=mobile?.69+.06*Math.sin(p*Math.PI):.85+.30*Math.sin(p*Math.PI),shift=mobile?0:.43-.86*smooth(.12,.60,p)+.43*smooth(.66,.99,p),ys=mobile?.36:.02;
     const size=Math.min(w,h)*zoom/.58, x=w*(1+shift)/2-size/2+mx*7,y=h*(1-ys)/2-size/2+my*6;
     ctx.setTransform(d,0,0,d,0,0);ctx.clearRect(0,0,w,h);ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';
     const paint=(frame,alpha)=>{ctx.globalAlpha=alpha;ctx.drawImage(frame.img,frame.x,frame.y,cell,cell,x,y,size,size);};
     if(a&&b){ctx.globalCompositeOperation='lighter';paint(a,1-mix);paint(b,mix);}else{ctx.globalCompositeOperation='source-over';paint(a||b||last,1);}
     ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over';canvas.classList.add('rendered');
   };
 }
 let draw=init()||(!reduce.matches&&initAtlas());
 const resize=()=>{const r=story.getBoundingClientRect();target=clamp(-r.top/Math.max(1,story.offsetHeight-stage.offsetHeight));visible=r.bottom>0&&r.top<innerHeight;};
 const pointer=e=>{if(e.pointerType==='touch')return;mouseX=clamp((e.clientX/innerWidth-.5)*2,-1,1);mouseY=clamp((e.clientY/innerHeight-.5)*2,-1,1);};
 const resetPointer=()=>{mouseX=0;mouseY=0;};
 let previousP=-1;const update=()=>{if(Math.abs(previousP-p)<.00005&&lastScene!==-1)return;previousP=p;let weights=[1-smooth(.18,.39,p),smooth(.18,.39,p)*(1-smooth(.61,.82,p)),smooth(.61,.82,p)];let scene=p<.29?0:p<.72?1:2;story.style.setProperty('--final-shade', (smooth(.69,.94,p)*.55).toFixed(3));story.style.setProperty('--progress',p.toFixed(4));story.dataset.scene=scene;
   beats.forEach((el,i)=>{const v=weights[i];el.style.setProperty('--weight',v.toFixed(4));el.style.setProperty('--drift',`${(i===0?-1:i===1?1:-1)*(1-v)*24}px`);if(scene!==lastScene)el.setAttribute('aria-hidden',String(i!==scene));});
   if(scene!==lastScene){steps.forEach((el,i)=>el.classList.toggle('current',i===scene));lastScene=scene;}
 };
 function tick(now){if(!alive)return;raf=requestAnimationFrame(tick);const dt=last?Math.min((now-last)/1000,.25):.016;last=now;if(!visible||document.hidden||reduce.matches)return;
   const ease=1-Math.exp(-dt*12);p+= (target-p)*ease; if(Math.abs(target-p)<.0001)p=target;mx+=(mouseX-mx)*(1-Math.exp(-dt*4));my+=(mouseY-my)*(1-Math.exp(-dt*4));clock+=Math.min(dt,.05);update();
   if(draw){draw();frames++;if(dt>.026)slow++;if(frames===90){if(slow>45&&quality>.65)quality*=.85;frames=slow=0;}}
 }
 const revealed=[...root.querySelectorAll('.director-editorial-body,.director-product-intro,.director-book,.director-details>div,.director-end h2')];
 let observer=null;if(!reduce.matches&&'IntersectionObserver' in window){observer=new IntersectionObserver(records=>{for(const record of records)if(record.isIntersecting){record.target.classList.add('director-visible');observer.unobserve(record.target);}}, {threshold:.12});revealed.forEach(el=>{el.classList.add('director-reveal');observer.observe(el);});}
 const lost=e=>{e.preventDefault();canvas.classList.remove('rendered');draw=initAtlas();};
 canvas.addEventListener('webglcontextlost',lost);
 window.addEventListener('scroll',resize,{passive:true});window.addEventListener('resize',resize);window.addEventListener('pointermove',pointer,{passive:true});document.addEventListener('pointerleave',resetPointer);
 const onMotion=()=>{story.classList.toggle('motion-reduced',reduce.matches);if(reduce.matches){beats.forEach(el=>el.setAttribute('aria-hidden','false'));}else{if(!draw)draw=init()||initAtlas();lastScene=-1;resize();update();}};
 reduce.addEventListener('change',onMotion);resize();p=target;update();onMotion();raf=requestAnimationFrame(tick);
 return ()=>{alive=false;observer?.disconnect();cancelAnimationFrame(raf);window.removeEventListener('scroll',resize);window.removeEventListener('resize',resize);window.removeEventListener('pointermove',pointer);document.removeEventListener('pointerleave',resetPointer);reduce.removeEventListener('change',onMotion);canvas.removeEventListener('webglcontextlost',lost);if(gl){gl.deleteBuffer(buffer);gl.deleteBuffer(indices);gl.deleteProgram(program);gl.getExtension('WEBGL_lose_context')?.loseContext();}};
}
