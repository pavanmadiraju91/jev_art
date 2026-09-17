#!/usr/bin/env python3
"""Web UI: type a prompt -> Jev judges perceptual axes -> Three.js renders a 3D
scene that is a continuous function of that vector. Color via chroma.js.

    export TYPESAFE_API_KEY=...
    python3 serve.py            # open http://localhost:8000
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jev_art import ask_jev, params_from_answers

PAGE = r"""<!doctype html><html><head><meta charset=utf-8>
<title>Jev Art</title>
<style>
 html,body{margin:0;height:100%;background:#0b0b0d;color:#eee;font:15px system-ui;overflow:hidden}
 #ui{position:fixed;top:0;left:0;right:0;z-index:10;padding:16px;display:flex;gap:8px;
     background:linear-gradient(#0b0b0dcc,#0b0b0d00)}
 input{flex:1;padding:12px;border-radius:8px;border:1px solid #444;background:#1c1c1ecc;color:#eee}
 button{padding:12px 20px;border:0;border-radius:8px;background:#2e86ab;color:#fff;cursor:pointer}
 button:disabled{opacity:.5}
 #err{position:fixed;top:64px;left:16px;color:#ff5e6b;z-index:10}
 #params{position:fixed;bottom:12px;left:12px;z-index:10;margin:0;padding:10px 14px;font:12px ui-monospace;
         background:#000000aa;border-radius:8px;white-space:pre;display:none;max-height:45vh;overflow:auto}
 canvas{display:block}
</style>
<script type="importmap">
{"imports":{
 "three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
 "three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}
</script></head><body>
<form id=ui><input id=p placeholder="sunset over the sea" autofocus>
<button id=b>Generate</button></form>
<div id=err></div><pre id=params></pre>

<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import chroma from 'https://cdn.jsdelivr.net/npm/chroma-js@2.4.2/+esm';

const renderer=new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth,innerHeight); renderer.setPixelRatio(devicePixelRatio);
renderer.outputColorSpace=THREE.SRGBColorSpace; document.body.appendChild(renderer.domElement);
const scene=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(55,innerWidth/innerHeight,0.1,300);
const controls=new OrbitControls(camera,renderer.domElement);
controls.enableDamping=true; controls.autoRotate=true; controls.autoRotateSpeed=0.6;
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();
  renderer.setSize(innerWidth,innerHeight);});

let group=null, turb=0;
function clear(){ if(!group)return; group.traverse(o=>{o.geometry&&o.geometry.dispose();
  o.material&&o.material.dispose();}); scene.remove(group); group=null; }

function sky(topHex,botHex){
 const c=document.createElement('canvas'); c.width=2; c.height=512;
 const g=c.getContext('2d'); const grd=g.createLinearGradient(0,0,0,512);
 grd.addColorStop(0,topHex); grd.addColorStop(1,botHex); g.fillStyle=grd; g.fillRect(0,0,2,512);
 const t=new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; return t;
}

function build(p){
 clear(); group=new THREE.Group(); scene.add(group); turb=1-p.order;

 // --- color: a harmonious chroma scale from warmth/saturation/brightness/variety ---
 const baseHue=(240-p.warmth*225+360)%360;          // cool blue -> warm red
 const sat=0.15+p.saturation*0.85, light=0.07+p.brightness*0.72;
 const spread=p.hue_variety*150;
 const scale=chroma.scale([
   chroma.hsl((baseHue-spread/2+360)%360,sat,light),
   chroma.hsl(baseHue,sat,Math.min(0.9,light+0.1)),
   chroma.hsl((baseHue+spread/2)%360,sat,light)]).mode('lch');
 const at=t=>new THREE.Color(scale(t).hex());

 // --- background sky + fog: strength = horizon axis (flat when ~0) ---
 const bot=scale(0.5), top=chroma.mix(bot,'#05070d',0.55*p.horizon).hex();
 scene.background=sky(top,bot.hex());
 scene.fog=new THREE.Fog(bot.hex(),18,70);

 // --- lighting scales with brightness ---
 group.add(new THREE.AmbientLight(0xffffff,0.1+0.55*p.brightness));
 const dir=new THREE.DirectionalLight(0xffffff,0.25+0.9*p.brightness); dir.position.set(6,12,8);
 group.add(dir);

 // --- geometry from roundness: spiky low-poly -> smooth sphere ---
 const detail=Math.round(p.roundness*3);
 const geo=new THREE.IcosahedronGeometry(1,detail);
 const mat=new THREE.MeshStandardMaterial({roughness:1-0.65*p.saturation,metalness:0.05*p.saturation,
   flatShading:p.roundness<0.6,transparent:true,opacity:0.92});

 // --- instances: count=density, layout grid<->cloud by order, angular jitter by 1-order ---
 const R=9, count=Math.round(10+p.density*380);
 const mesh=new THREE.InstancedMesh(geo,mat,count);
 const gN=Math.max(1,Math.ceil(Math.cbrt(count))), step=2*R/gN, o=p.order, d=new THREE.Object3D();
 for(let i=0;i<count;i++){
  const u=Math.random(),v=Math.random(),th=2*Math.PI*u,ph=Math.acos(2*v-1),r=R*Math.cbrt(Math.random());
  const rx=r*Math.sin(ph)*Math.cos(th),ry=r*Math.sin(ph)*Math.sin(th),rz=r*Math.cos(ph);
  const gx=((i%gN)+0.5)*step-R,gy=((Math.floor(i/gN)%gN)+0.5)*step-R,gz=(Math.floor(i/(gN*gN))+0.5)*step-R;
  d.position.set(rx*(1-o)+gx*o,ry*(1-o)+gy*o,rz*(1-o)+gz*o);
  const s=(0.7-0.4*p.density)*(0.6+Math.random()*0.9)*(1+(1-o)*0.4);
  d.scale.setScalar(Math.max(0.08,s));
  d.rotation.set(Math.random()*6*(1-o),Math.random()*6,Math.random()*6*(1-o));
  d.updateMatrix(); mesh.setMatrixAt(i,d.matrix); mesh.setColorAt(i,at(Math.random()));
 }
 mesh.instanceColor.needsUpdate=true; group.add(mesh);

 // --- one dominant body ONLY when focal is genuinely high; colored by the palette,
 //     not blown out to white, so cold/dark prompts get a cold/dim body ---
 if(p.focal>0.5){
  const rr=1.2+2.3*p.focal, col=scale(0.82).hex(), y=p.horizon>0.3?1.2:0;
  const sun=new THREE.Mesh(new THREE.IcosahedronGeometry(rr,4),
    new THREE.MeshStandardMaterial({color:col,emissive:col,emissiveIntensity:0.35+0.5*p.focal}));
  sun.position.set(0,y,0); group.add(sun);
  const pl=new THREE.PointLight(new THREE.Color(col),1+2.5*p.focal,120); pl.position.set(0,y,0); group.add(pl);
 }

 // --- ground plane appears with horizon ---
 if(p.horizon>0.2){
  const plane=new THREE.Mesh(new THREE.PlaneGeometry(200,200),
    new THREE.MeshStandardMaterial({color:chroma.mix(bot,'#000',0.45).hex(),roughness:1}));
  plane.rotation.x=-Math.PI/2; plane.position.y=-R*0.7; group.add(plane);
 }

 // --- camera drops toward the horizon as horizon rises ---
 camera.position.set(0,8-6*p.horizon,20); controls.target.set(0,0,0); controls.update();
}

function animate(){ requestAnimationFrame(animate);
  if(group) group.rotation.y+=0.0015+turb*0.004; controls.update(); renderer.render(scene,camera); }
animate();

const p=document.getElementById('p'),b=document.getElementById('b'),err=document.getElementById('err'),
      pv=document.getElementById('params');
document.getElementById('ui').onsubmit=async e=>{
 e.preventDefault(); if(!p.value.trim())return;
 b.disabled=true; b.textContent='Asking Jev…'; err.textContent='';
 try{
  const r=await fetch('/generate',{method:'POST',body:JSON.stringify({prompt:p.value})});
  const dat=await r.json(); if(!r.ok)throw new Error(dat.error||'failed');
  build(dat.params);
  pv.style.display='block';
  pv.textContent=Object.entries(dat.params).map(([k,v])=>k.padEnd(11)+v.toFixed(2)).join('\n');
 }catch(x){err.textContent=x.message}
 b.disabled=false; b.textContent='Generate';
};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, PAGE, "text/html; charset=utf-8")

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            prompt = json.loads(self.rfile.read(n))["prompt"]
            self._send(200, json.dumps({"params": params_from_answers(ask_jev(prompt))}))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    print("http://localhost:8000")
    ThreadingHTTPServer(("", 8000), Handler).serve_forever()
