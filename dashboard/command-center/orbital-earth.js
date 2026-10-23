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
uniform vec2 uSize;
uniform float uAngle;
uniform float uCloud;
varying vec2 unusedVarying;

float rnd(vec2 p) {
  return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);
}
float noise2(vec2 p) {
  vec2 i=floor(p),f=fract(p);f=f*f*(3.0-2.0*f);
  return mix(mix(rnd(i),rnd(i+vec2(1.,0.)),f.x),
             mix(rnd(i+vec2(0.,1.)),rnd(i+vec2(1.,1.)),f.x),f.y);
}
vec4 globe(vec2 pixel,vec2 center,float radius,float nightDim) {
  vec2 p=(pixel-center)/radius;
  float r2=dot(p,p);
  if(r2>1.075) return vec4(0.);
  if(r2>=1.0) {
    float halo=(1.075-r2)/0.075;
    return vec4(vec3(0.05,0.27,0.75),0.16*halo);
  }
  vec3 n=vec3(p,sqrt(max(0.,1.-r2)));
  float lon=atan(n.x,n.z)/6.2831853 + 0.5 + uAngle/6.2831853;
  float lat=asin(clamp(n.y,-1.,1.))/3.1415926 + 0.5;
  vec3 base=texture2D(uMap,vec2(fract(lon),lat)).rgb;
  vec3 sun=normalize(vec3(-0.15,0.48,0.87));
  float diffuse=max(dot(n,sun),0.);
  float illumination=0.08+0.92*diffuse;
  float cloud=noise2(vec2(lon*77.+uCloud*0.15,lat*33.));
  cloud+=0.45*noise2(vec2(lon*172.+uCloud*0.29,lat*83.));
  cloud=smoothstep(0.83,1.20,cloud)*0.39;
  float limb=pow(1.0-max(0.,n.z),4.0);
  vec3 col=base*(illumination*(1.0-nightDim*0.28));
  col+=vec3(0.47,0.69,0.87)*cloud*illumination;
  col+=vec3(0.06,0.31,0.75)*limb*1.28;
  float blueRim=pow(1.-n.z,13.);
  col+=vec3(0.22,0.56,1.0)*blueRim*1.15;
  float edge=1.0-smoothstep(0.94,1.0,sqrt(r2));
  return vec4(min(col,vec3(1.0)),edge);
}
void main() {
  vec2 pix=gl_FragCoord.xy;
  float horizonRadius=min(uSize.x*0.98,uSize.y*0.75);
  vec4 horizon=globe(pix,vec2(uSize.x*0.50,-uSize.y*0.19),horizonRadius,0.38);
  float sphereRadius=min(uSize.x*0.315,uSize.y*0.275);
  vec4 planet=globe(pix,vec2(uSize.x*0.50,uSize.y*0.56),sphereRadius,0.);
  vec3 finalRgb=mix(horizon.rgb,planet.rgb,planet.a);
  float alpha=horizon.a+planet.a*(1.-horizon.a);
  gl_FragColor=vec4(finalRgb,alpha);
}`;
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
    const texture=gl.createTexture();gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,map);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    const sizeLoc=gl.getUniformLocation(program,'uSize');
    const angleLoc=gl.getUniformLocation(program,'uAngle');
    const cloudLoc=gl.getUniformLocation(program,'uCloud');
    gl.uniform1i(gl.getUniformLocation(program,'uMap'),0);
    let angle=0,cloud=0,lastTime=0,lastDraw=0,frame=0,speed=1,stopped=false,manualPause=false;
    const environment=options.environment||root;
    const motionQuery=environment.matchMedia&&environment.matchMedia('(prefers-reduced-motion: reduce)');
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
      stop(){stopped=true;environment.cancelAnimationFrame?.(frame);gl.deleteTexture(texture);gl.deleteProgram(program);gl.deleteBuffer(buffer);},
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