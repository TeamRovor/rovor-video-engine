/* ROVOR orbital Earth renderer. Self-contained WebGL1; no CDN, telemetry or image tracking. */
(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.RovorEarth = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const DEFAULT_REVOLUTION_SECONDS = 220;
  const VERTEX = [
    'attribute vec2 aPosition;',
    'void main() { gl_Position = vec4(aPosition,0.0,1.0); }'
  ].join('\n');
  const FRAGMENT = `
precision mediump float;
uniform sampler2D uMap;
uniform sampler2D uNightMap;
uniform vec2 uSize;
uniform float uAngle;
uniform float uCloud;
uniform float uHasNight;

float hash(vec2 p) {
  return fract(sin(dot(p,vec2(41.23,277.17)))*43758.5453);
}
float smoothNoise(vec2 p) {
  vec2 i=floor(p),f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash(i),hash(i+vec2(1.0,0.0)),f.x),
             mix(hash(i+vec2(0.0,1.0)),hash(i+vec2(1.0,1.0)),f.x),f.y);
}
vec4 globe(vec2 pixel,vec2 center,float radius,float darkness) {
  vec2 p=(pixel-center)/radius;
  float r=length(p);
  if(r>1.085) return vec4(0.0);

  // Thin, soft atmospheric halo instead of the previous oversized electric ring.
  if(r>=1.0) {
    float falloff=pow(clamp(1.0-(r-1.0)/0.085,0.0,1.0),4.0);
    return vec4(vec3(0.13,0.41,0.89)*falloff,falloff*0.48);
  }

  vec3 normal=vec3(p,sqrt(max(0.0,1.0-r*r)));
  float longitude=atan(normal.x,normal.z)/6.2831853 + 0.5 + uAngle/6.2831853;
  float latitude=asin(clamp(normal.y,-1.0,1.0))/3.1415926 + 0.5;
  vec2 coords=vec2(fract(longitude),latitude);
  vec3 day=texture2D(uMap,coords).rgb;
  vec3 night=texture2D(uNightMap,coords).rgb*uHasNight;

  float light=max(dot(normal,normalize(vec3(0.55,0.37,0.77))),0.0);
  // Low-key blue Earth, with real terrain and city lights where available.
  vec3 daySide=day*(0.23+0.52*light);
  vec3 nightSide=day*0.065 + night*(0.65+0.3*(1.0-light));
  vec3 color=mix(daySide+night*0.18*(1.0-light),nightSide,darkness);

  // Cloud wisps are subtle and secondary to NASA imagery.
  float cloud=smoothNoise(coords*vec2(68.0,31.0)+vec2(uCloud*0.12,0.0));
  cloud=smoothstep(0.70,0.88,cloud)*0.11;
  color+=vec3(0.41,0.59,0.76)*cloud*light*(1.0-darkness*0.6);

  float fresnel=pow(1.0-normal.z,5.0);
  color+=vec3(0.055,0.29,0.76)*fresnel*1.75;
  float rim=pow(1.0-normal.z,15.0);
  color+=vec3(0.26,0.62,1.0)*rim*0.7;
  float edge=1.0-smoothstep(0.987,1.0,r);
  return vec4(clamp(color,0.0,1.0),edge);
}
void main() {
  vec2 pix=gl_FragCoord.xy;

  // Horizon begins in the lower third, matching the reference composition.
  float horizonRadius=min(uSize.x*1.20,uSize.y*0.78);
  vec4 horizon=globe(pix,vec2(uSize.x*0.50,-uSize.y*0.39),horizonRadius,0.88);

  float sphereRadius=min(uSize.x*0.325,uSize.y*0.275);
  vec4 planet=globe(pix,vec2(uSize.x*0.50,uSize.y*0.56),sphereRadius,0.34);
  vec3 result=mix(horizon.rgb,planet.rgb,planet.a);
  gl_FragColor=vec4(result,horizon.a+planet.a*(1.0-horizon.a));
}
`;
  // A deterministic natural-color map with continent silhouettes; generated once,
  // moved as a real texture across a shader-projected 3D sphere every frame.
  const LAND = [
    [-112,46,52,31],[-92,22,33,17],[-73,8,16,13],
    [-66,-18,24,43],[-52,-43,15,18],[-41,70,20,15],
    [25,53,46,23],[79,53,66,27],[120,35,39,21],
    [18,4,26,39],[43,-8,17,23],[136,-25,23,16],
    [114,-3,22,15],[47,-21,10,12]
  ];
  const fract=x=>x-Math.floor(x);
  function hash(x,y) { return fract(Math.sin(x*127.1+y*311.7)*43758.5453); }
  function smoothNoise(x,y) {
    const ix=Math.floor(x),iy=Math.floor(y),fx=x-ix,fy=y-iy;
    const a=fx*fx*(3-2*fx),b=fy*fy*(3-2*fy);
    return (hash(ix,iy)*(1-a)+hash(ix+1,iy)*a)*(1-b)
      +(hash(ix,iy+1)*(1-a)+hash(ix+1,iy+1)*a)*b;
  }
  function isLand(lon,lat,n) {
    if (lat < -69 + n*9) return true;
    for(const [cx,cy,rx,ry] of LAND) {
      let dx=Math.abs(lon-cx); dx=Math.min(dx,360-dx);
      const dist=(dx/rx)**2+((lat-cy)/ry)**2;
      if(dist < 0.79+(n-0.5)*0.55) return true;
    }
    return false;
  }
  function createTexture(doc, width=512, height=256) {
    const canvas=doc.createElement('canvas');canvas.width=width;canvas.height=height;
    const ctx=canvas.getContext('2d');if(!ctx)return null;
    const img=ctx.createImageData(width,height);
    for(let y=0;y<height;y++) {
      const lat=(y/height)*180-90;
      for(let x=0;x<width;x++) {
        const lon=x/width*360-180;
        const bump=0.6*smoothNoise(lon*.15,lat*.15)+0.4*smoothNoise(lon*.33,lat*.33);
        const land=isLand(lon,lat,bump);
        const desert=lat>-4&&lat<34&&(lon>-18&&lon<65);
        const ice=Math.abs(lat)>72||(Math.abs(lat)>60&&bump>.72);
        const relief=smoothNoise(lon*.28+10,lat*.32+10);
        let rgb;
        if(ice) rgb=[173,199,212];
        else if(land) rgb=desert?[110+relief*35,102+relief*28,75+relief*18]:
          [38+relief*70,74+relief*58,54+relief*26];
        else rgb=[4+relief*12,25+relief*25,61+relief*47];
        const off=(y*width+x)*4;
        for(let j=0;j<3;j++)img.data[off+j]=Math.floor(rgb[j]);
        img.data[off+3]=255;
      }
    }
    ctx.putImageData(img,0,0);
    return canvas;
  }
  function compile(gl,type,source) {
    const shader=gl.createShader(type);
    gl.shaderSource(shader,source);gl.compileShader(shader);
    if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) {
      gl.deleteShader(shader);return null;
    }
    return shader;
  }
  function createRenderer(canvas, options={}) {
    if(!canvas || typeof canvas.getContext!=='function')return null;
    const gl=canvas.getContext('webgl',{alpha:true,antialias:false,depth:false,premultipliedAlpha:false,preserveDrawingBuffer:false});
    if(!gl)return null;
    const vs=compile(gl,gl.VERTEX_SHADER,VERTEX),fs=compile(gl,gl.FRAGMENT_SHADER,FRAGMENT);
    if(!vs||!fs)return null;
    const program=gl.createProgram();
    gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))return null;
    const pos=gl.getAttribLocation(program,'aPosition');
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,1,1]),gl.STATIC_DRAW);
    gl.useProgram(program);gl.enableVertexAttribArray(pos);
    gl.vertexAttribPointer(pos,2,gl.FLOAT,false,0,0);
    const doc=options.document||(typeof document!=='undefined'?document:null);
    const map=doc?createTexture(doc):null;
    if(!map)return null;
    // NASA Blue Marble and Earth-at-night maps are self-hosted with the Pages build.
    // The procedural map stays in place if assets fail to load (e.g. local preview).
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
    const texture=gl.createTexture();gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,map);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    const nightTexture=gl.createTexture();
    gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,nightTexture);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([0,0,0,255]));
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    const sizeLoc=gl.getUniformLocation(program,'uSize');
    const angleLoc=gl.getUniformLocation(program,'uAngle');
    const cloudLoc=gl.getUniformLocation(program,'uCloud');
    const nightLoc=gl.getUniformLocation(program,'uHasNight');
    gl.uniform1i(gl.getUniformLocation(program,'uMap'),0);
    gl.uniform1i(gl.getUniformLocation(program,'uNightMap'),1);
    gl.uniform1f(nightLoc,0);
    let angle=0,cloud=0,lastTime=0,lastDraw=0,frame=0,speed=1,stopped=false,manualPause=false;
    const environment=options.environment||root;
    const motionQuery=environment.matchMedia&&environment.matchMedia('(prefers-reduced-motion: reduce)');
    let hasNight=false;
    // URL paths are fixed local assets; never load arbitrary remote origins.
    function loadMap(path,unit,tex,ready) {
      const ImageType=options.ImageClass||environment.Image;
      if(typeof ImageType!=='function')return;
      const image=new ImageType();
      image.onload=()=>{
        if(stopped)return;
        const w=image.naturalWidth||image.width,h=image.naturalHeight||image.height;
        if(!w||!h||w>4096||h>2048)return;
        try {
          gl.activeTexture(gl.TEXTURE0+unit);
          gl.bindTexture(gl.TEXTURE_2D,tex);
          gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);
          gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);
          // Both published maps have power-of-two dimensions.
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
          gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
          ready();
          lastDraw=0;
        } catch (_) { /* Keep local fallback on image/texture error. */ }
      };
      image.onerror=()=>{/* Preserve fallback when developing without built assets. */};
      image.src=path;
    }
    loadMap('./earth-blue-marble.png',0,texture,()=>{
      if(canvas.dataset)canvas.dataset.texture='nasa-blue-marble';
    });
    loadMap('./earth-night.png',1,nightTexture,()=>{
      hasNight=true;
      if(canvas.dataset)canvas.dataset.nightLights='nasa-night';
    });
    const isStopped=()=>manualPause || !!motionQuery?.matches ||
      !!doc?.hidden || !!doc?.body?.classList?.contains('motion-paused');
    function resize() {
      const box=canvas.getBoundingClientRect();
      const ratio=Math.min(environment.devicePixelRatio||1,1.5);
      const factor=Math.min(1,960/Math.max(box.width*ratio,box.height*ratio,1));
      const width=Math.max(2,Math.floor(box.width*ratio*factor));
      const height=Math.max(2,Math.floor(box.height*ratio*factor));
      if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
      gl.viewport(0,0,width,height);
    }
    function draw(time) {
      if(stopped)return;
      const elapsed=lastTime?Math.min((time-lastTime)/1000,0.10):0;
      lastTime=time;
      const paused=isStopped();
      if(!paused) {
        angle=(angle+elapsed*2*Math.PI/(DEFAULT_REVOLUTION_SECONDS/Math.max(speed,0.1)))%(2*Math.PI);
        cloud+=elapsed*.07;
      }
      if((time-lastDraw>41 && (!paused||!lastDraw))||!frame) {
        resize();
        gl.useProgram(program);
        gl.uniform2f(sizeLoc,canvas.width,canvas.height);
        gl.uniform1f(angleLoc,angle);
        gl.uniform1f(cloudLoc,cloud);
        gl.uniform1f(nightLoc,hasNight?1:0);
        gl.drawArrays(gl.TRIANGLE_STRIP,0,4);
        lastDraw=time;
      }
      frame=environment.requestAnimationFrame(draw);
    }
    resize();
    frame=environment.requestAnimationFrame(draw);
    return {
      setSpeed(next) { if([0.5,1,2].includes(Number(next)))speed=Number(next);return speed; },
      getSpeed(){return speed;},
      setPaused(next){manualPause=!!next;lastDraw=0;return manualPause;},
      isPaused(){return isStopped();},
      nudge(degrees){angle=(angle+Number(degrees||0)*Math.PI/180)%(2*Math.PI);lastDraw=0;},
      reset(){angle=0;cloud=0;lastDraw=0;},
      stop(){stopped=true;environment.cancelAnimationFrame?.(frame);gl.deleteTexture(texture);gl.deleteTexture(nightTexture);gl.deleteProgram(program);gl.deleteBuffer(buffer);},
    };
  }
  function boot(doc,environment) {
    doc=doc||(typeof document!=='undefined'?document:null);
    const canvas=doc?.getElementById('earthCanvas');
    let renderer=null;
    try {renderer=canvas?createRenderer(canvas,{document:doc,environment:environment||root}):null;}
    catch (_) { renderer=null; } // Unsupported context must not block the dashboard.
    if(canvas) {
      canvas.dataset.renderer=renderer?'webgl':'css-fallback';
      canvas.addEventListener?.('webglcontextlost',event=>{
        event.preventDefault();
        renderer?.stop();
        canvas.dataset.renderer='css-fallback';
      },{once:true});
    }
    return renderer;
  }
  return {createTexture,isLand,createRenderer,boot,DEFAULT_REVOLUTION_SECONDS};
});