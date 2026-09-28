const C='#00E5FF',G='#00FF88',R='#FF3B3B',GLD='#D4AF37';
const p2=v=>String(v).padStart(2,'0');
// Clock
setInterval(()=>{const n=new Date();const e=document.getElementById('clk');if(e)e.textContent=`${p2(n.getHours())}:${p2(n.getMinutes())}:${p2(n.getSeconds())}`;const d=document.getElementById('decTime');if(d)d.textContent=e.textContent;},1000);
(function(){const n=new Date();document.getElementById('clk').textContent=`${p2(n.getHours())}:${p2(n.getMinutes())}:${p2(n.getSeconds())}`;})();
// Uptime
let upS=9918;
setInterval(()=>{upS++;const h=Math.floor(upS/3600),m=Math.floor((upS%3600)/60),s=upS%60;const t=`${p2(h)}:${p2(m)}:${p2(s)}`;['upt','sbupt'].forEach(id=>{const e=document.getElementById(id);if(e)e.textContent=t;});},1000);
// Neutralize timer
let ntS=18;
setInterval(()=>{ntS=ntS>0?ntS-1:18;const e=document.getElementById('ntimer');if(e)e.textContent=p2(ntS);},1000);
// Alerts
const ALERTS=[{c:'red',m:'MULTIPLE TARGETS DETECTED'},{c:'red',m:'RF INTERFERENCE DETECTED'},{c:'gold',m:'AI AUTO-ENGAGE ENABLED'},{c:'green',m:'NEW TARGET ACQUIRED'},{c:'red',m:'HIGH THREAT DETECTED'},{c:'red',m:'GPS SPOOFING ATTEMPT'},{c:'red',m:'TARGET LOCK CONFIRMED'},{c:'gold',m:'INTERCEPT DRONE ARMED'},{c:'green',m:'COUNTERMEASURE ACTIVE'},{c:'red',m:'HOSTILE CLOSING IN'}];
let aIdx=0;
function addAl(msg,cls){const log=document.getElementById('alert-log');if(!log)return;const n=new Date();const row=document.createElement('div');row.className='al-row';row.innerHTML=`<span class="al-time">${p2(n.getHours())}:${p2(n.getMinutes())}:${p2(n.getSeconds())}</span><span class="al-msg ${cls}">${msg}</span>`;log.insertBefore(row,log.firstChild);if(log.children.length>8)log.removeChild(log.lastChild);}
// Seed alerts
setTimeout(()=>{[['red','MULTIPLE TARGETS DETECTED'],['red','RF INTERFERENCE DETECTED'],['gold','AI AUTO-ENGAGE ENABLED'],['green','NEW TARGET ACQUIRED'],['red','HIGH THREAT DETECTED'],['red','GPS SPOOFING ATTEMPT']].forEach(([c,m],i)=>{const n=new Date();n.setSeconds(n.getSeconds()-i*25);const log=document.getElementById('alert-log');if(!log)return;const row=document.createElement('div');row.className='al-row';row.innerHTML=`<span class="al-time">${p2(n.getHours())}:${p2(n.getMinutes())}:${p2(n.getSeconds())}</span><span class="al-msg ${c}">${m}</span>`;log.appendChild(row);});},50);
setInterval(()=>{const a=ALERTS[aIdx%ALERTS.length];aIdx++;addAl(a.m,a.c);},5000);
// Nav tabs
document.querySelectorAll('.ntab').forEach(t=>{t.addEventListener('click',function(){document.querySelectorAll('.ntab').forEach(x=>x.classList.remove('active'));this.classList.add('active');});});
// ===== CANVAS ANIMATIONS =====
// THREAT RING
function drawRing(id,pct,col){
  const cv=document.getElementById(id);if(!cv)return;
  const ctx=cv.getContext('2d'),cx=cv.width/2,cy=cv.height/2,r=48,lw=9;
  let cur=0;
  function f(){
    ctx.clearRect(0,0,cv.width,cv.height);
    for(let i=0;i<20;i++){const a=-Math.PI/2+Math.PI*2*(i/20);ctx.strokeStyle='#0A2030';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(cx+Math.cos(a)*(r+5),cy+Math.sin(a)*(r+5));ctx.lineTo(cx+Math.cos(a)*(r+9),cy+Math.sin(a)*(r+9));ctx.stroke();}
    ctx.strokeStyle='#091525';ctx.lineWidth=lw;ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);ctx.stroke();
    const ag=-Math.PI/2+Math.PI*2*(cur/100);
    const g=ctx.createLinearGradient(0,0,cv.width,0);g.addColorStop(0,col+'44');g.addColorStop(1,col);
    ctx.strokeStyle=g;ctx.lineWidth=lw;ctx.lineCap='round';ctx.shadowBlur=16;ctx.shadowColor=col;
    ctx.beginPath();ctx.arc(cx,cy,r,-Math.PI/2,ag);ctx.stroke();ctx.shadowBlur=0;
    if(cur<pct){cur=Math.min(cur+2,pct);requestAnimationFrame(f);}
  }
  f();
}
drawRing('threatRing',95,R);
drawRing('outcomeRing',97.6,G);

// RADAR
(function(){
  const cv=document.getElementById('radarCanvas');if(!cv)return;
  const ctx=cv.getContext('2d'),cx=cv.width/2,cy=cv.height/2,r=110;
  let ang=0;
  const tgts=[{a:0.8,d:.55},{a:2.1,d:.4},{a:4.5,d:.72},{a:3.3,d:.5}];
  function draw(){
    ctx.fillStyle='rgba(5,7,10,.22)';ctx.fillRect(0,0,cv.width,cv.height);
    [.25,.5,.75,1].forEach(f=>{ctx.strokeStyle='#00FF2210';ctx.lineWidth=1;ctx.beginPath();ctx.arc(cx,cy,r*f,0,Math.PI*2);ctx.stroke();});
    ctx.strokeStyle='#00FF2210';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(cx,cy-r);ctx.lineTo(cx,cy+r);ctx.stroke();
    ctx.beginPath();ctx.moveTo(cx-r,cy);ctx.lineTo(cx+r,cy);ctx.stroke();
    ctx.fillStyle='#4A6A7A';ctx.font='7px Orbitron';ctx.textAlign='center';
    ctx.fillText('N',cx,cy-r-4);ctx.fillText('S',cx,cy+r+10);ctx.fillText('W',cx-r-8,cy+3);ctx.fillText('E',cx+r+8,cy+3);
    ctx.save();ctx.translate(cx,cy);ctx.rotate(ang);
    const sg=ctx.createLinearGradient(0,0,r,0);sg.addColorStop(0,'rgba(0,255,136,.5)');sg.addColorStop(1,'rgba(0,255,136,0)');
    ctx.fillStyle=sg;ctx.beginPath();ctx.moveTo(0,0);ctx.arc(0,0,r,-.4,0);ctx.closePath();ctx.fill();
    ctx.strokeStyle=G;ctx.lineWidth=1.5;ctx.shadowBlur=5;ctx.shadowColor=G;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(r,0);ctx.stroke();ctx.shadowBlur=0;ctx.restore();
    tgts.forEach(t=>{const da=((t.a-ang)%(Math.PI*2)+Math.PI*2)%(Math.PI*2);const fade=da<.4?1:Math.max(0,1-da/(Math.PI*1.5));if(fade>.04){const tx=cx+Math.cos(t.a)*r*t.d,ty=cy+Math.sin(t.a)*r*t.d;ctx.fillStyle=`rgba(255,59,59,${fade})`;ctx.shadowBlur=8;ctx.shadowColor=R;ctx.beginPath();ctx.arc(tx,ty,3.5,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;}});
    ang=(ang+.04)%(Math.PI*2);requestAnimationFrame(draw);
  }
  draw();
})();

// VIDEO CANVAS (sky simulation - user will replace with video later)
(function(){
  const cv=document.getElementById('videoCanvas');if(!cv)return;
  const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;
  let f=0;
  const stars=Array.from({length:100},()=>({x:Math.random()*W,y:Math.random()*H*.5,r:Math.random()*1.5,b:Math.random()*10}));
  function draw(){
    const sky=ctx.createLinearGradient(0,0,0,H);
    sky.addColorStop(0,'#040912');sky.addColorStop(.3,'#091622');sky.addColorStop(.55,'#182840');sky.addColorStop(.7,'#604020');sky.addColorStop(.8,'#804810');sky.addColorStop(1,'#0A1020');
    ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);
    const hg=ctx.createRadialGradient(W*.55,H*.7,10,W*.55,H*.7,W*.45);
    hg.addColorStop(0,'rgba(255,120,30,.35)');hg.addColorStop(.5,'rgba(200,80,15,.12)');hg.addColorStop(1,'transparent');
    ctx.fillStyle=hg;ctx.fillRect(0,0,W,H);
    stars.forEach(s=>{const b=.2+.8*Math.abs(Math.sin(f*.02+s.b));ctx.fillStyle=`rgba(200,220,255,${b*.6})`;ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);ctx.fill();});
    for(let i=0;i<8;i++){const cx2=(W*.03+W*.94*(i/7)+(f*.06*(i%2?1:-1))+W*3)%W;const cy2=H*.2+i*22;const cg=ctx.createRadialGradient(cx2,cy2,3,cx2,cy2,60);cg.addColorStop(0,'rgba(25,40,65,.55)');cg.addColorStop(1,'transparent');ctx.fillStyle=cg;ctx.fillRect(0,0,W,H);}
    const cg2=ctx.createLinearGradient(0,H*.78,0,H);cg2.addColorStop(0,'transparent');cg2.addColorStop(1,'rgba(6,16,38,.9)');ctx.fillStyle=cg2;ctx.fillRect(0,0,W,H);
    for(let i=0;i<200;i++){const lx=(i*15+f*.03)%W;const ly=H*.85+Math.sin(i*2.7)*H*.04;const lb=.2+.5*Math.abs(Math.sin(f*.05+i*.4));ctx.fillStyle=`rgba(255,200,80,${lb*.45})`;ctx.fillRect(lx,ly,1,1);}
    const dx=W/2+Math.sin(f*.012)*30,dy=H*.38+Math.cos(f*.01)*10;
    ctx.save();ctx.translate(dx,dy);
    ctx.fillStyle='#141E28';ctx.strokeStyle='#2A4060';ctx.lineWidth=1;ctx.beginPath();ctx.rect(-16,-8,32,16);ctx.fill();ctx.stroke();
    ctx.fillStyle='#1A2838';ctx.fillRect(-10,-5,20,10);
    [[-28,-20],[28,-20],[-28,20],[28,20]].forEach(([ax,ay])=>{ctx.strokeStyle='#1E3040';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(ax/2.2,ay/2.2);ctx.stroke();ctx.save();ctx.translate(ax/2.2,ay/2.2);ctx.rotate(f*.5);ctx.strokeStyle=`rgba(60,120,180,${.4+.3*Math.abs(Math.sin(f*.3))})`;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(-8,0);ctx.lineTo(8,0);ctx.stroke();ctx.beginPath();ctx.moveTo(0,-8);ctx.lineTo(0,8);ctx.stroke();ctx.restore();});
    ctx.restore();
    // Altitude scale left
    ctx.strokeStyle='rgba(0,229,255,.2)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(45,15);ctx.lineTo(45,H-15);ctx.stroke();
    for(let i=0;i<=5;i++){const y=15+(H-30)*i/5;ctx.fillStyle='rgba(0,229,255,.4)';ctx.font='8px Share Tech Mono';ctx.textAlign='right';ctx.fillText(150-i*30,40,y+3);ctx.beginPath();ctx.moveTo(40,y);ctx.lineTo(45,y);ctx.stroke();}
    // Speed scale right
    ctx.strokeStyle='rgba(0,229,255,.2)';ctx.beginPath();ctx.moveTo(W-45,15);ctx.lineTo(W-45,H-15);ctx.stroke();
    for(let i=0;i<=5;i++){const y=15+(H-30)*i/5;ctx.fillStyle='rgba(0,229,255,.4)';ctx.font='8px Share Tech Mono';ctx.textAlign='left';ctx.fillText(60-i*12,W-40,y+3);ctx.beginPath();ctx.moveTo(W-45,y);ctx.lineTo(W-40,y);ctx.stroke();}
    // Grid
    ctx.strokeStyle='rgba(0,229,255,.025)';for(let x=0;x<W;x+=45){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke();}
    for(let y=0;y<H;y+=45){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}
    f++;requestAnimationFrame(draw);
  }
  draw();
})();
// THERMAL
(function(){const cv=document.getElementById('thermalC');if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;let f=0;function draw(){const id=ctx.createImageData(W,H);for(let y=0;y<H;y++)for(let x=0;x<W;x++){const n=(Math.sin(x*.12+f*.04)+Math.sin(y*.12+f*.035)+Math.sin((x+y)*.08+f*.025))/3;const t=(n+1)/2;const r2=Math.floor(t>.5?(t-.5)*2*255:0);const g2=Math.floor(t<.5?t*2*190:Math.max(0,(1-t)*2*190));const b2=Math.floor(t<.3?(.3-t)*3.3*255:0);const i=(y*W+x)*4;id.data[i]=r2;id.data[i+1]=g2;id.data[i+2]=b2;id.data[i+3]=230;}ctx.putImageData(id,0,0);f++;requestAnimationFrame(draw);}draw();})();
// RF SPECTRUM
(function(){const cv=document.getElementById('rfC');if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;let f=0;const N=60;function draw(){ctx.fillStyle='#040810';ctx.fillRect(0,0,W,H);ctx.strokeStyle='rgba(0,255,136,.15)';ctx.lineWidth=1;for(let y=H*.25;y<H;y+=H*.25){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke();}ctx.strokeStyle=G;ctx.lineWidth=1.5;ctx.shadowBlur=4;ctx.shadowColor=G;ctx.beginPath();for(let i=0;i<N;i++){const x=i*(W/N);const sp=i===20||i===21?.85+.1*Math.sin(f*.1):i===35||i===36?.6+.1*Math.sin(f*.08+1):0;const v=Math.max(.04+Math.random()*.06,sp);const y=H-(v*H*.85)-2;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();ctx.shadowBlur=0;f++;requestAnimationFrame(draw);}draw();})();
// ACOUSTIC
(function(){const cv=document.getElementById('acousticC');if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;let f=0;function draw(){ctx.fillStyle='#040810';ctx.fillRect(0,0,W,H);ctx.strokeStyle='rgba(255,59,59,.12)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(0,H/2);ctx.lineTo(W,H/2);ctx.stroke();ctx.strokeStyle=R;ctx.lineWidth=1.5;ctx.shadowBlur=4;ctx.shadowColor=R;ctx.beginPath();for(let x=0;x<W;x++){const t=x/W;const v=Math.sin(t*22+f*.14)*.28+Math.sin(t*8+f*.09)*.18+Math.random()*.05;const y=H/2-v*H*.4;x===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.stroke();ctx.shadowBlur=0;f++;requestAnimationFrame(draw);}draw();})();
// SIGNAL
(function(){const cv=document.getElementById('signalC');if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;const pts=Array(W).fill(H/2);let f=0;function draw(){ctx.fillStyle='#040810';ctx.fillRect(0,0,W,H);pts.shift();const v=.45+.4*Math.sin(f*.07)+.1*Math.sin(f*.15)+.08*Math.random();pts.push(H-v*H*.85-3);ctx.strokeStyle=C;ctx.lineWidth=1.5;ctx.shadowBlur=4;ctx.shadowColor=C;ctx.beginPath();pts.forEach((y,x)=>x===0?ctx.moveTo(x,y):ctx.lineTo(x,y));ctx.stroke();ctx.shadowBlur=0;f++;requestAnimationFrame(draw);}draw();})();
// EOIR
(function(){const cv=document.getElementById('eoirC');if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;let f=0;function draw(){ctx.fillStyle='#080C14';ctx.fillRect(0,0,W,H);const x2=W*.72,y2=H*.38;const sg=ctx.createRadialGradient(x2,y2,0,x2,y2,42);sg.addColorStop(0,'rgba(255,255,220,.9)');sg.addColorStop(.15,'rgba(220,230,255,.4)');sg.addColorStop(.4,'rgba(100,150,200,.1)');sg.addColorStop(1,'transparent');ctx.fillStyle=sg;ctx.fillRect(0,0,W,H);ctx.strokeStyle='rgba(0,229,255,.2)';ctx.lineWidth=1;ctx.strokeRect(W*.28,H*.18,W*.44,H*.52);ctx.fillStyle='rgba(0,229,255,.5)';ctx.font='6px Orbitron';ctx.fillText('ZOOM: 4X',3,10);f++;requestAnimationFrame(draw);}draw();})();
// TARGET IMAGE
(function(){const cv=document.getElementById('targetImgC');if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;let f=0;function draw(){ctx.fillStyle='#060A14';ctx.fillRect(0,0,W,H);ctx.strokeStyle='rgba(0,229,255,.06)';ctx.lineWidth=1;for(let x=0;x<W;x+=12)for(let y=0;y<H;y+=12)ctx.strokeRect(x,y,12,12);const dx=W/2+Math.sin(f*.04)*4,dy=H/2+Math.cos(f*.03)*3;ctx.fillStyle='#141E28';ctx.strokeStyle='#2A4060';ctx.lineWidth=1;ctx.save();ctx.translate(dx,dy);ctx.beginPath();ctx.rect(-12,-6,24,12);ctx.fill();ctx.stroke();[[-18,-14],[18,-14],[-18,14],[18,14]].forEach(([ax,ay])=>{ctx.strokeStyle='#1E3040';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(ax/2,ay/2);ctx.stroke();ctx.strokeStyle='rgba(60,120,180,.5)';ctx.lineWidth=1;ctx.beginPath();ctx.arc(ax/2,ay/2,5,0,Math.PI*2);ctx.stroke();});ctx.restore();ctx.strokeStyle='rgba(255,59,59,.6)';ctx.lineWidth=1.5;ctx.strokeRect(dx-22,dy-18,44,36);f++;requestAnimationFrame(draw);}draw();})();
// CAPTURED
['cap1','cap2','cap3'].forEach((id,i)=>{const cv=document.getElementById(id);if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;ctx.fillStyle='#060A14';ctx.fillRect(0,0,W,H);ctx.fillStyle='#141E28';ctx.strokeStyle='#2A4060';ctx.lineWidth=1;ctx.beginPath();ctx.rect(W/2-8,H/2-5,16,10);ctx.fill();ctx.stroke();const arms=i===1?[[-16,0],[16,0],[0,-10],[0,10]]:[[-12,-10],[12,-10],[-12,10],[12,10]];arms.forEach(([ax,ay])=>{ctx.strokeStyle='#1E3040';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(W/2,H/2);ctx.lineTo(W/2+ax,H/2+ay);ctx.stroke();ctx.strokeStyle='rgba(60,120,180,.45)';ctx.lineWidth=1;ctx.beginPath();ctx.arc(W/2+ax,H/2+ay,4,0,Math.PI*2);ctx.stroke();});ctx.strokeStyle='rgba(255,59,59,.35)';ctx.lineWidth=1;ctx.strokeRect(1,1,W-2,H-2);});
// DRONE AI CANVAS
(function(){const cv=document.getElementById('droneAiC');if(!cv)return;const ctx=cv.getContext('2d'),W=cv.width,H=cv.height;let f=0;function draw(){ctx.clearRect(0,0,W,H);const cx=W/2,cy=H/2;ctx.fillStyle='#141E28';ctx.strokeStyle='#2A4060';ctx.lineWidth=1;ctx.save();ctx.translate(cx,cy);ctx.beginPath();ctx.rect(-12,-6,24,12);ctx.fill();ctx.stroke();[[-18,-14],[18,-14],[-18,14],[18,14]].forEach(([ax,ay])=>{ctx.strokeStyle='#1E3040';ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(ax/2.2,ay/2.2);ctx.stroke();ctx.strokeStyle=`rgba(0,229,255,${.35+.35*Math.abs(Math.sin(f*.2))})`;ctx.lineWidth=1;ctx.beginPath();ctx.arc(ax/2.2,ay/2.2,7,0,Math.PI*2);ctx.stroke();});ctx.restore();ctx.strokeStyle='rgba(255,59,59,.5)';ctx.lineWidth=1;ctx.strokeRect(cx-22,cy-18,44,36);f++;requestAnimationFrame(draw);}draw();})();
console.log('%cHORUS SYSTEM ONLINE','color:#00E5FF;font-size:18px;font-weight:900');

// ===== REPORT SYSTEM =====
function toggleReport(){
  const m=document.getElementById('report-modal');
  m.classList.toggle('hidden');
  if(!m.classList.contains('hidden')){
    const n=new Date();
    const ts=`${n.getFullYear()}-${p2(n.getMonth()+1)}-${p2(n.getDate())} ${p2(n.getHours())}:${p2(n.getMinutes())}:${p2(n.getSeconds())}`;
    const rid=`RPT-${n.getFullYear()}${p2(n.getMonth()+1)}${p2(n.getDate())}_${p2(n.getHours())}${p2(n.getMinutes())}${p2(n.getSeconds())}`;
    document.getElementById('rptTime').textContent=ts;
    document.getElementById('rptId').textContent=rid;
    const times=['rptT1','rptT2','rptT3','rptT4'];
    times.forEach((id,i)=>{const t=new Date(n.getTime()-i*180000);document.getElementById(id).textContent=`${p2(t.getHours())}:${p2(t.getMinutes())}:${p2(t.getSeconds())}`;});
  }
}
window.toggleReport=toggleReport;

function generateReport(){
  const st=document.getElementById('rpt-status');
  st.innerHTML='<span class="cyan">⏳ GENERATING TACTICAL INTELLIGENCE REPORT...</span>';
  setTimeout(()=>{
    st.innerHTML='<span class="green">✅ REPORT GENERATED: MCDIS_TACTICAL_INTELLIGENCE_'+new Date().toISOString().replace(/[:.]/g,'').slice(0,15)+'.pdf</span>';
    setTimeout(()=>{
      st.innerHTML='<span class="gold">📋 Report saved to /static/reports/ directory</span>';
    },3000);
  },2000);
}
window.generateReport=generateReport;

function openHTMLReport(){
  window.open('mcdis_report.html','_blank');
}
window.openHTMLReport=openHTMLReport;

// ═══════════════════════════════════════════════════════════
//  SOCKET.IO — LIVE BACKEND CONNECTION
// ═══════════════════════════════════════════════════════════
let _socket = null;
let _liveMode = false;

function initSocket(){
  if(_socket) return;
  try {
    _socket = io();
    _liveMode = true;
    console.log('%c[HORUS] Socket.IO CONNECTED','color:#00FF88;font-size:12px');

    // ── FULL UPDATE (new detections) ──
    _socket.on('full_update', d => {
      updateFromBackend(d);
    });

    // ── HEARTBEAT (every second) ──
    _socket.on('system_heartbeat', d => {
      updateFromBackend(d);
    });

    // ── VISION DETECTION (real-time target from camera) ──
    _socket.on('vision_detection', d => {
      updateTargetInfo(d);
      updateAIEngine(d);
    });

    // ── COUNTERMEASURE STATUS ──
    _socket.on('countermeasure_status', d => {
      updateCMStatus(d);
      addAl(d.system + ' → ' + d.target + ' [' + d.status + ']', d.status === 'NEUTRALIZED' ? 'green' : 'red');
    });

    // ── RADAR BLIPS ──
    _socket.on('radar_update', d => {
      if(d.blips) _liveRadarBlips = d.blips;
    });

    // ── ENGAGEMENT RESULT ──
    _socket.on('engagement_result', d => {
      addAl('ENGAGEMENT: ' + d.weapon + ' on ' + d.target + ' → ' + d.status, d.status === 'SUCCESS' ? 'green' : 'gold');
    });

    // ── ISR RESULT ──
    _socket.on('isr_result', d => {
      const m = document.querySelector('.eo-meta');
      if(m) m.innerHTML = `<span>ISR <span class="eo-v ${d.go_nogo==='GO'?'green':'red'}">${d.isr_pct?.toFixed(1)||'--'}%</span></span><span>RECOMMENDED <span class="eo-v cyan">${d.recommended||'--'}</span></span><span>CONFIDENCE <span class="eo-v green">${d.confidence?.toFixed(1)||'97.6'}%</span></span><span>FUZZYING <span class="eo-v gold">LOW</span></span>`;
    });

    // Replace video canvas with live feed
    const vc = document.getElementById('videoCanvas');
    if(vc) {
      const img = document.createElement('img');
      img.src = '/video_feed';
      img.style.cssText = 'width:100%;height:100%;display:block;object-fit:cover';
      img.id = 'liveVideoFeed';
      vc.parentNode.replaceChild(img, vc);
    }

  } catch(e) {
    console.log('[HORUS] Socket.IO not available — standalone mode');
  }
}

let _liveRadarBlips = [];

function updateFromBackend(d){
  // Uptime
  if(d.uptime){
    const h=Math.floor(d.uptime/3600),m2=Math.floor((d.uptime%3600)/60),s2=d.uptime%60;
    const ut=`${p2(h)}:${p2(m2)}:${p2(s2)}`;
    ['upt','sbupt'].forEach(id=>{const e=document.getElementById(id);if(e)e.textContent=ut;});
  }
  // Threat level
  if(d.threat_level){
    const tl=d.threat_level;
    const tpct = tl.pct || 95;
    const ring = document.querySelector('.ta-pct');
    if(ring) ring.textContent = tpct + '%';
    const label = document.querySelector('.ta-label');
    if(label) label.textContent = tl.level || 'CRITICAL';
    const tbThreat = document.querySelector('.tbs-v.red');
    if(tbThreat) tbThreat.textContent = '⚠ ' + (tl.level||'CRITICAL') + ' ' + tpct + '%';
  }
  // Stats
  if(d.stats){
    const aiConf = document.querySelectorAll('.tbs-v.green');
    if(aiConf[1]) aiConf[1].textContent = (d.stats.avg_confidence||97.6).toFixed(1)+'%';
  }
  // Health bars
  if(d.health){
    const bars = document.querySelectorAll('.sh-row');
    const keys = Object.keys(d.health);
    bars.forEach((row,i)=>{
      if(keys[i]){
        const fill = row.querySelector('.sh-fill');
        const pct = row.querySelector('.sh-pct');
        if(fill) fill.style.width = d.health[keys[i]] + '%';
        if(pct) pct.textContent = d.health[keys[i]] + '%';
      }
    });
  }
  // Alerts from DB
  if(d.alerts && d.alerts.length){
    const log = document.getElementById('alert-log');
    if(log && d.alerts[0]){
      const a = d.alerts[0];
      const cls = a.threat_level === 'CRITICAL' ? 'red' : a.threat_level === 'HIGH' ? 'gold' : 'green';
      const ts = a.timestamp ? a.timestamp.split(' ').pop() : '';
      // Only add if not duplicate
      if(!log.firstChild || !log.firstChild.textContent.includes(a.target_id)){
        addAl(`${a.target_id} — ${a.details||a.sensor_type}`, cls);
      }
    }
  }
  // Target info
  if(d.target && d.target.target_id) updateTargetInfo(d.target);
}

function updateTargetInfo(d){
  const tids = document.querySelectorAll('.tid');
  if(!tids.length) return;
  const vals = [
    d.target_id||'--', d.category||'QUADCOPTER', d.model_name||'COMMERCIAL',
    (d.distance_km||1.2).toFixed(1)+' km', (d.altitude||120).toFixed(0)+' m',
    (d.speed||45).toFixed(0)+' km/h', (d.bearing||270)+'°', d.threat_level||'CRITICAL'
  ];
  tids.forEach((t,i)=>{
    const v = t.querySelector('span:last-child');
    if(v && vals[i]) v.textContent = vals[i];
  });
  // Target image from crop
  if(d.crop_b64){
    const cv = document.getElementById('targetImgC');
    if(cv){
      const img = new Image();
      img.onload = ()=>{
        const ctx = cv.getContext('2d');
        ctx.clearRect(0,0,cv.width,cv.height);
        ctx.drawImage(img,0,0,cv.width,cv.height);
        ctx.strokeStyle='rgba(255,59,59,.6)';ctx.lineWidth=2;
        ctx.strokeRect(2,2,cv.width-4,cv.height-4);
      };
      img.src = 'data:image/jpeg;base64,'+d.crop_b64;
    }
  }
  // Update HUD
  const altEl = document.querySelector('.hud-alt .hv');
  if(altEl) altEl.textContent = (d.altitude||120).toFixed(0)+' m';
  const spdEl = document.querySelector('.hud-spd .hv');
  if(spdEl) spdEl.textContent = (d.speed||45).toFixed(0)+' km/h';
}

function updateAIEngine(d){
  const threatV = document.querySelector('#ai-engine .ai-c:first-child .ai-v.red');
  if(threatV) threatV.textContent = (d.threat_level||'CRITICAL') + ' ' + (d.confidence||95).toFixed(0)+'%';
  
  const modelV = document.querySelector('#ai-engine .ai-vb');
  if(modelV) modelV.textContent = d.model_name || d.category || 'UNKNOWN';
  
  const behaviorV = document.querySelector('#ai-engine .ai-c:first-child .ai-r:nth-child(4) .ai-v');
  if(behaviorV) behaviorV.textContent = d.threat_level === 'CRITICAL' ? 'HOSTILE' : 'SUSPICIOUS';

  const confV = document.querySelector('#ai-engine .ai-v.green');
  if(confV) confV.textContent = (d.confidence||97.6).toFixed(1)+'%';
  
  // Highlight engagement recommendation
  const recV = document.querySelector('.ai-highlight');
  if(recV) {
    recV.textContent = d.threat_level === 'CRITICAL' ? 'NEUTRALIZE THREAT' : 'MONITOR TARGET';
    recV.style.borderColor = d.threat_level === 'CRITICAL' ? 'var(--r)' : 'var(--gld)';
    recV.className = 'ai-highlight ' + (d.threat_level === 'CRITICAL' ? 'red' : 'gold');
  }
}

function updateCMStatus(d){
  const rows = document.querySelectorAll('.cm-tbl tr');
  const sysMap = {'RF_JAMMER':1,'GPS_SPOOFER':2,'ACOUSTIC':3,'LASER':4,'ACOUSTIC_ARRAY':3,'DEW_LASER':4};
  const idx = sysMap[d.system];
  if(idx && rows[idx]){
    const tds = rows[idx].querySelectorAll('td');
    if(tds[1]){
      tds[1].textContent = d.status;
      tds[1].className = d.status==='NEUTRALIZED'?'green':d.status==='ENGAGING'?'red':'gold';
    }
    if(d.status==='ENGAGING'){
      if(tds[2]) tds[2].textContent = '80%';
      if(tds[3]){ tds[3].textContent = '92%'; tds[3].className='green'; }
    }
  }
}

// ── REPORT — connect to real backend ──
window.generateReport = function(){
  const st = document.getElementById('rpt-status');
  st.innerHTML = '<span class="cyan">⏳ GENERATING TACTICAL INTELLIGENCE REPORT...</span>';
  fetch('/api/generate_report').then(r=>r.json()).then(d=>{
    if(d.status==='SUCCESS'){
      st.innerHTML = '<span class="green">✅ REPORT GENERATED — <a href="'+d.report_url+'" target="_blank" style="color:#00FF88">DOWNLOAD PDF</a></span>';
    } else {
      st.innerHTML = '<span class="red">❌ '+d.message+'</span>';
    }
  }).catch(()=>{
    st.innerHTML = '<span class="gold">📋 Standalone mode — PDF requires backend</span>';
  });
};

// ── ENGAGEMENT BUTTONS ──
document.querySelectorAll('.eb').forEach(btn=>{
  btn.addEventListener('click', function(){
    const name = this.querySelector('.eb-n')?.textContent||'';
    const wMap = {'RF JAMMER':'RF_JAMMING','GPS SPOOFER':'GPS_SPOOFING','ACOUSTIC':'ACOUSTIC_ARRAY','LASER':'DEW_LASER',
                  'NET-GUN':'KINETIC_NET','HPM EMP':'HPM_EMP','LASER DEW':'DEW_LASER','INTERCEPTOR CHAIN':'INTERCEPTOR',
                  'CYBER TAKEOVER':'CYBER_TAKEOVER','QUANTUM JAM':'QUANTUM_JAM','ADVERSARIAL':'ADVERSARIAL_AI',
                  'COLLAB SWARM':'SWARM_DECOY','ISR PRE-CHECK':'ISR_PRECHECK','STANDBY':'STANDBY'};
    const wtype = wMap[name]||'RF_JAMMING';
    const tid = document.querySelector('.tid .cyan')?.textContent||'T-000';
    
    this.querySelector('.eb-s').textContent = 'FIRING';
    this.querySelector('.eb-s').className = 'eb-s red';
    addAl('MANUAL ENGAGE: '+name+' → '+tid, 'gold');
    
    if(_socket){
      _socket.emit('trigger_engagement', {mode:wtype, target:tid});
    }
    fetch('/api/engage_advanced',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({weapon_type:wtype,target_id:tid,distance_m:2000,speed_kmh:80,bearing:45})
    }).catch(()=>{});
    
    setTimeout(()=>{
      this.querySelector('.eb-s').textContent = 'READY';
      this.querySelector('.eb-s').className = 'eb-s green';
    },4000);
  });
});

// ── AUTO-ENGAGE BUTTON ──
document.getElementById('auto-engage')?.addEventListener('click', function(){
  const active = this.querySelector('.ae-s').textContent.includes('ACTIVE');
  if(active){
    this.querySelector('.ae-s').textContent = '●● DISABLED ●●';
    this.querySelector('.ae-n').textContent = 'AI DECISION MAKING DISABLED';
    this.style.borderColor = '#4A6A7A';
    if(_socket) _socket.emit('toggle_auto_engage',{enabled:false});
  } else {
    this.querySelector('.ae-s').textContent = '●● ACTIVE ●●';
    this.querySelector('.ae-n').textContent = 'AI DECISION MAKING ENABLED';
    this.style.borderColor = '';
    if(_socket) _socket.emit('toggle_auto_engage',{enabled:true});
  }
});

// Try to connect
if(typeof io !== 'undefined') initSocket();
else {
  const sc = document.createElement('script');
  sc.src = '/socket.io/socket.io.js';
  sc.onload = ()=> initSocket();
  sc.onerror = ()=> console.log('[HORUS] Standalone mode — no backend');
  document.head.appendChild(sc);
}
