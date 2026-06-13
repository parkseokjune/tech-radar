# -*- coding: utf-8 -*-
TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tech Radar — 동적 딥테크 트렌드 + 예측</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{--bg:#0a0e14;--panel:#121821;--panel2:#0f141c;--line:#1e2733;
    --txt:#e6edf3;--muted:#8b97a7;--accent:#4cc9f0;--accent2:#f72585;
    --up:#3ddc84;--down:#ff5d6c;--flat:#7d8aa0;--pred:#ffd166;}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--txt);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Apple SD Gothic Neo",sans-serif;}
  .wrap{max-width:1180px;margin:0 auto;padding:32px 20px 90px}
  h1{font-size:28px;margin:0 0 4px;letter-spacing:-.5px}
  h1 .dot{color:var(--accent)}
  .sub{color:var(--muted);font-size:13px}
  h2{font-size:16px;margin:38px 0 14px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  h2 .bar{width:4px;height:18px;background:var(--accent);border-radius:2px}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}
  .badges{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 4px}
  .badge{background:var(--panel);border:1px solid var(--line);border-radius:12px;
    padding:10px 16px;font-size:13px}
  .badge b{font-size:20px;display:block;color:var(--accent)}
  .badge.good b{color:var(--up)} .badge.warn b{color:var(--pred)}
  .pill{display:inline-block;font-size:11px;padding:2px 9px;border-radius:20px;
    border:1px solid var(--line);color:var(--muted)}
  /* 예측 카드 그리드 */
  .pgrid{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(270px,1fr))}
  .pcard{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px}
  .pcard .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
  .pcard .nm{font-weight:600;font-size:14px;line-height:1.3}
  .pcard .pg{font-weight:800;font-size:17px;font-variant-numeric:tabular-nums;white-space:nowrap}
  .pcard .meta{font-size:11px;color:var(--muted);margin:6px 0 8px}
  .pcard .mini{height:74px;position:relative}
  .up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--flat)}.pred{color:var(--pred)}
  /* 랭킹 */
  .rank{display:flex;align-items:center;gap:12px;padding:11px 4px;border-bottom:1px solid var(--line)}
  .rank:last-child{border-bottom:none}
  .rank .pos{width:22px;color:var(--muted);font-size:13px;text-align:right;font-variant-numeric:tabular-nums}
  .rank .sparkbox{width:84px;height:30px;flex:none;position:relative}
  .rank .meta{flex:1;min-width:0}
  .rank .name{font-weight:600;font-size:14px}
  .rank .stat{font-size:11px;color:var(--muted);margin-top:2px}
  .rank .mom{font-weight:700;font-size:15px;text-align:right;min-width:78px;font-variant-numeric:tabular-nums}
  .chartbox{position:relative;height:400px}
  .chartbox.tall{height:460px}
  .legend{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
  .lg{font-size:12px;color:var(--muted);cursor:pointer;display:flex;align-items:center;gap:6px;
    padding:3px 9px;border:1px solid var(--line);border-radius:20px;user-select:none}
  .lg.off{opacity:.35}
  .lg .sw{width:10px;height:10px;border-radius:3px}
  .q-note{font-size:12px;color:var(--muted);margin-top:10px;line-height:1.7}
  .q-note b{color:var(--txt)}
  .foot{margin-top:52px;color:var(--muted);font-size:12px;text-align:center;line-height:1.8}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Tech Radar<span class="dot">.</span> <span class="sub">동적 딥테크 트렌드 + 예측</span></h1>
    <div class="sub">고정 키워드 없음 — arXiv 최근 논문에서 기술용어를 직접 발견 · 생성 <span id="gen"></span></div>
    <div class="badges" id="badges"></div>
  </header>

  <h2><span class="bar"></span>🔮 다음 분기 부상 예측 <span class="sub" style="font-weight:400">(향후 3개월 예측 성장률 상위 · 점선=예측)</span></h2>
  <div class="pgrid" id="predGrid"></div>

  <h2><span class="bar"></span>🚀 현재 모멘텀 랭킹 <span class="sub" style="font-weight:400">(최근 3개월 vs 직전 3개월)</span></h2>
  <div class="panel"><div id="ranking"></div></div>

  <h2><span class="bar"></span>📈 모멘텀 × 볼륨 사분면</h2>
  <div class="panel">
    <div class="chartbox tall"><canvas id="quad"></canvas></div>
    <div class="q-note">
      <b>↗ 우상단</b> 크고 빠르게 성장(핫) · <b>↖ 좌상단</b> 작지만 급성장(떠오름) ·
      <b>↘ 우하단</b> 크나 둔화(성숙) · <b>↙ 좌하단</b> 작고 정체. 버블 크기=최근 논문량.
    </div>
  </div>

  <h2><span class="bar"></span>📊 발견된 용어별 월간 트렌드 <span class="sub" style="font-weight:400">(범례 클릭 토글)</span></h2>
  <div class="panel">
    <div class="chartbox"><canvas id="trend"></canvas></div>
    <div class="legend" id="trendLegend"></div>
  </div>

  <div class="foot">
    데이터: arXiv (submittedDate 기준 논문 수) · 용어 발견: 최근 <span id="hd"></span>편 n-gram 분석 ·
    예측: 감쇠 Holt 지수평활(다음 3개월) · 신뢰도: 최근 3개월 백테스트 MAPE<br>
    ⚠ 논문 수는 연구 활동의 대리지표이며 산업 채택/펀딩과 다를 수 있습니다. 예측은 추세 연장일 뿐 확정이 아닙니다.
  </div>
</div>

<script>
const DATA = __DATA__;
const PAL=["#4cc9f0","#f72585","#3ddc84","#ffd166","#b388ff","#ff7b54","#06d6a0",
 "#ef476f","#7ae582","#fca311","#8338ec","#00b4d8","#e07a5f","#90be6d","#f15bb5",
 "#48cae4","#ff8fab","#a0c4ff","#fdffb6","#caffbf","#9bf6ff","#bdb2ff","#ffc6ff",
 "#80ed99","#ffadad","#d0f4de"];
const COLOR={}; DATA.items.forEach((it,i)=>COLOR[it.term]=PAL[i%PAL.length]);
const ALLM=[...DATA.months, ...DATA.future];

document.getElementById("gen").textContent=DATA.generated;
document.getElementById("hd").textContent=DATA.n_corpus||"-";
Chart.defaults.color="#8b97a7";
Chart.defaults.font.family=getComputedStyle(document.body).fontFamily;
Chart.defaults.font.size=11;
const sign=v=>(v>0?"+":"")+v;
const cls=v=>v>3?"up":(v<-3?"down":"flat");
const arrow=v=>v>3?"▲":(v<-3?"▼":"▬");

// ── 배지 ──
const conf = DATA.median_mape==null?null:(DATA.median_mape<20?"높음":DATA.median_mape<40?"보통":"낮음");
const bcls = DATA.median_mape==null?"":(DATA.median_mape<20?"good":DATA.median_mape<40?"warn":"warn");
document.getElementById("badges").innerHTML=`
  <div class="badge"><b>${DATA.items.length}</b>발견된 기술용어</div>
  <div class="badge"><b>${DATA.n_corpus||"-"}</b>분석 논문(최근)</div>
  <div class="badge ${bcls}"><b>${DATA.median_mape==null?"-":DATA.median_mape+"%"}</b>예측 오차(백테스트)</div>
  <div class="badge ${bcls}"><b>${conf||"-"}</b>예측 신뢰도</div>`;

// ── 🔮 예측 카드 ──
const pg=document.getElementById("predGrid");
DATA.items_by_emergence.slice(0,8).forEach((it,idx)=>{
  const card=document.createElement("div");card.className="pcard";
  const conf = it.mape==null?"–":(it.mape<20?"신뢰 높음":it.mape<40?"신뢰 보통":"신뢰 낮음");
  card.innerHTML=`
    <div class="top"><div class="nm">${it.term}</div>
      <div class="pg ${cls(it.pred_growth)}">${sign(it.pred_growth)}%</div></div>
    <div class="meta">현재 ${it.avg_recent}편/월 · 가속도 ${sign(it.accel)} · ${conf}${it.mape!=null?" ("+it.mape+"%)":""}</div>
    <div class="mini"><canvas id="pm${idx}"></canvas></div>`;
  pg.appendChild(card);
  const hist=it.series.concat([null,null,null]);
  const fc=new Array(it.series.length-1).fill(null);
  fc.push(it.series[it.series.length-1], ...it.forecast);
  new Chart(document.getElementById("pm"+idx),{type:"line",
    data:{labels:ALLM,datasets:[
      {data:hist,borderColor:COLOR[it.term],borderWidth:2,pointRadius:0,tension:.3,
       fill:true,backgroundColor:(c)=>{const g=c.chart.ctx.createLinearGradient(0,0,0,74);
        g.addColorStop(0,COLOR[it.term]+"44");g.addColorStop(1,COLOR[it.term]+"00");return g;}},
      {data:fc,borderColor:"#ffd166",borderWidth:2,borderDash:[4,3],pointRadius:0,tension:.3}
    ]},
    options:{maintainAspectRatio:false,responsive:true,animation:false,
      plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{x:{display:false},y:{display:false}}}});
});

// ── 🚀 랭킹 ──
const rk=document.getElementById("ranking");
DATA.items_by_momentum.forEach((it,i)=>{
  const idx=DATA.items.indexOf(it);
  const row=document.createElement("div");row.className="rank";
  row.innerHTML=`<div class="pos">${i+1}</div><div class="sparkbox"><canvas id="sp${i}"></canvas></div>
    <div class="meta"><div class="name">${it.term}</div>
      <div class="stat">최근 ${it.avg_recent}편/월 · 12개월 ${it.volume}편 · 예측 <span class="${cls(it.pred_growth)}">${sign(it.pred_growth)}%</span></div></div>
    <div class="mom ${cls(it.momentum)}">${arrow(it.momentum)} ${sign(it.momentum)}%</div>`;
  rk.appendChild(row);
  new Chart(document.getElementById("sp"+i),{type:"line",
    data:{labels:it.series.map((_,j)=>j),datasets:[{data:it.series,
      borderColor:COLOR[it.term],borderWidth:1.6,pointRadius:0,tension:.35,fill:true,
      backgroundColor:(c)=>{const g=c.chart.ctx.createLinearGradient(0,0,0,30);
        g.addColorStop(0,COLOR[it.term]+"55");g.addColorStop(1,COLOR[it.term]+"00");return g;}}]},
    options:{plugins:{legend:{display:false},tooltip:{enabled:false}},
      scales:{x:{display:false},y:{display:false}},animation:false,
      maintainAspectRatio:false,responsive:true}});
});

// ── 사분면 ──
const maxR=Math.max(...DATA.items.map(i=>i.avg_recent))||1;
const _med=arr=>{const s=[...arr].sort((a,b)=>a-b);return s[Math.floor(s.length/2)]||0;};
const medMom=_med(DATA.items.map(i=>i.momentum));
const medVol=_med(DATA.items.map(i=>i.vol_norm));
new Chart(document.getElementById("quad"),{type:"bubble",
  data:{datasets:DATA.items.map(it=>({label:it.term,
    data:[{x:it.vol_norm,y:it.momentum,r:6+Math.sqrt(it.avg_recent/maxR)*26}],
    backgroundColor:COLOR[it.term]+"cc",borderColor:COLOR[it.term],borderWidth:1.5}))},
  options:{maintainAspectRatio:false,responsive:true,
    plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>{
      const it=DATA.items[c.datasetIndex];
      return ` ${it.term}: 모멘텀 ${sign(it.momentum)}%, 12개월 ${it.volume}편, 최근 ${it.avg_recent}편/월`;}}}},
    scales:{x:{title:{display:true,text:"← 작음   볼륨 순위(연구 규모)   큼 →"},min:-5,max:105,grid:{color:"#1e2733"}},
            y:{title:{display:true,text:"← 느린 상승   모멘텀(%)   빠른 상승 →"},grid:{color:"#1e2733"}}}},
  plugins:[{id:"qz",beforeDraw(ch){const{ctx,chartArea:a,scales}=ch;
    const xz=scales.x.getPixelForValue(medVol),yz=scales.y.getPixelForValue(medMom);
    ctx.save();ctx.strokeStyle="#2a3645";ctx.setLineDash([5,5]);
    ctx.beginPath();ctx.moveTo(xz,a.top);ctx.lineTo(xz,a.bottom);ctx.stroke();
    ctx.beginPath();ctx.moveTo(a.left,yz);ctx.lineTo(a.right,yz);ctx.stroke();
    ctx.setLineDash([]);ctx.fillStyle="#5a6b80";ctx.font="11px sans-serif";
    ctx.fillText("떠오름",a.left+8,a.top+16);ctx.textAlign="right";
    ctx.fillText("뜨는 주류",a.right-8,a.top+16);ctx.fillText("성숙·정체",a.right-8,a.bottom-8);
    ctx.textAlign="left";ctx.fillText("니치·쇠퇴",a.left+8,a.bottom-8);ctx.restore();}}]
});

// ── 트렌드 ──
const top6=[...DATA.items].sort((a,b)=>b.volume-a.volume).slice(0,6).map(i=>i.term);
const trend=new Chart(document.getElementById("trend"),{type:"line",
  data:{labels:DATA.months,datasets:DATA.items.map(it=>({label:it.term,data:it.series,
    borderColor:COLOR[it.term],backgroundColor:COLOR[it.term],borderWidth:2,
    pointRadius:0,tension:.3,hidden:!top6.includes(it.term)}))},
  options:{maintainAspectRatio:false,responsive:true,interaction:{mode:"index",intersect:false},
    plugins:{legend:{display:false}},
    scales:{x:{grid:{color:"#161e29"}},y:{grid:{color:"#161e29"},title:{display:true,text:"월간 논문 수"}}}}});
const lg=document.getElementById("trendLegend");
DATA.items.forEach((it,i)=>{const el=document.createElement("div");
  el.className="lg"+(trend.data.datasets[i].hidden?" off":"");
  el.innerHTML=`<span class="sw" style="background:${COLOR[it.term]}"></span>${it.term}`;
  el.onclick=()=>{const ds=trend.data.datasets[i];ds.hidden=!ds.hidden;
    el.classList.toggle("off",ds.hidden);trend.update();};
  lg.appendChild(el);});
</script>
</body>
</html>
"""
