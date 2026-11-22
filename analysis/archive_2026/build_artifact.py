"""Build the self-contained artifact HTML with the presence-field data embedded."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, 'field.json')))

HTML = r"""<title>Why the Robots Are Blobs</title>
<style>
:root{
  --paper:#EAE7DE; --paper-2:#E1DDD2; --card:#F3F1EA;
  --ink:#151B1E; --ink-2:#3E484C; --ink-3:#6B7679;
  --rule:#C9C3B4; --rule-2:#D8D3C6;
  --teal:#17414E; --teal-2:#357F8B; --gold:#B0741C; --clay:#9E4E20;
  --line:#151B1E;            /* waterline stroke */
  --good:#3F6E4E; --warn:#96631A; --bad:#9A3B2A;
  --mono:ui-monospace,"SF Mono","Cascadia Mono",Menlo,Consolas,monospace;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#10161A; --paper-2:#161E22; --card:#182126;
    --ink:#E8E4DA; --ink-2:#B3AEA2; --ink-3:#7E8A8D;
    --rule:#2A363B; --rule-2:#222C31;
    --teal:#6FB3BE; --teal-2:#4E9DA8; --gold:#E0A344; --clay:#D2703A;
    --line:#F0ECE2;
    --good:#7FB98F; --warn:#D8A44A; --bad:#D9705C;
  }
}
:root[data-theme="dark"]{
  --paper:#10161A; --paper-2:#161E22; --card:#182126;
  --ink:#E8E4DA; --ink-2:#B3AEA2; --ink-3:#7E8A8D;
  --rule:#2A363B; --rule-2:#222C31;
  --teal:#6FB3BE; --teal-2:#4E9DA8; --gold:#E0A344; --clay:#D2703A;
  --line:#F0ECE2;
  --good:#7FB98F; --warn:#D8A44A; --bad:#D9705C;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:var(--serif); font-size:17px; line-height:1.62;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1060px; margin:0 auto; padding:0 28px 96px}
header.masthead{
  padding:56px 0 30px; border-bottom:2px solid var(--ink);
  display:flex; flex-direction:column; gap:14px;
}
.eyebrow{
  font-family:var(--mono); font-size:11px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-3); display:flex; gap:14px; flex-wrap:wrap;
}
h1{
  font-family:var(--serif); font-weight:600; font-size:clamp(34px,5.4vw,58px);
  line-height:1.04; margin:0; letter-spacing:-.015em; text-wrap:balance;
}
.standfirst{
  font-size:19px; color:var(--ink-2); margin:0; max-width:62ch; text-wrap:pretty;
}
h2{
  font-family:var(--serif); font-weight:600; font-size:26px; letter-spacing:-.01em;
  margin:0; text-wrap:balance;
}
h3{font-family:var(--sans); font-weight:650; font-size:14px; letter-spacing:.02em; margin:0}
section{padding-top:52px; display:flex; flex-direction:column; gap:18px}
p{margin:0; max-width:66ch; text-wrap:pretty}
.sec-head{display:flex; align-items:baseline; gap:14px; border-bottom:1px solid var(--rule); padding-bottom:9px}
.sec-num{font-family:var(--mono); font-size:12px; color:var(--ink-3); letter-spacing:.08em}
code{font-family:var(--mono); font-size:.88em; background:var(--paper-2); padding:1px 5px; border-radius:3px}
strong{font-weight:650}
a{color:var(--clay)}

/* ---------- instrument ---------- */
.instrument{
  display:grid; grid-template-columns:minmax(0,1fr) 292px; gap:0;
  border:1px solid var(--rule); background:var(--card); margin-top:26px;
}
.stage{padding:22px; display:flex; flex-direction:column; gap:16px; min-width:0}
.canvas-row{display:flex; gap:20px; align-items:flex-start; flex-wrap:wrap}
.cwrap{display:flex; flex-direction:column; gap:7px; min-width:0}
.cwrap canvas{
  width:100%; max-width:340px; height:auto; display:block;
  border:1px solid var(--rule); background:var(--paper-2); image-rendering:pixelated;
}
.clabel{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.11em; text-transform:uppercase;
  color:var(--ink-3);
}
.panel{
  border-left:1px solid var(--rule); padding:22px; display:flex; flex-direction:column; gap:22px;
  background:var(--paper-2);
}
.ctrl{display:flex; flex-direction:column; gap:8px}
.ctrl-head{display:flex; justify-content:space-between; align-items:baseline; gap:10px}
.ctrl-head label{font-family:var(--sans); font-size:12.5px; font-weight:600}
.val{font-family:var(--mono); font-size:12.5px; color:var(--clay); font-variant-numeric:tabular-nums}
input[type=range]{width:100%; accent-color:var(--clay); cursor:pointer}
input[type=range]:focus-visible{outline:2px solid var(--clay); outline-offset:3px}
.hint{font-family:var(--sans); font-size:11.5px; color:var(--ink-3); line-height:1.45}
.readout{display:flex; flex-direction:column; gap:9px; border-top:1px solid var(--rule); padding-top:16px}
.rrow{display:flex; justify-content:space-between; align-items:baseline; gap:12px}
.rk{font-family:var(--sans); font-size:12px; color:var(--ink-2)}
.rv{font-family:var(--mono); font-size:13.5px; font-variant-numeric:tabular-nums; font-weight:600}
.rv.hot{color:var(--clay)}
.btn{
  font-family:var(--sans); font-size:12px; font-weight:600; padding:7px 11px;
  background:transparent; color:var(--ink); border:1px solid var(--rule); border-radius:2px; cursor:pointer;
}
.btn:hover{background:var(--card); border-color:var(--ink-3)}
.btn[aria-pressed="true"]{background:var(--ink); color:var(--paper); border-color:var(--ink)}
.btn:focus-visible{outline:2px solid var(--clay); outline-offset:2px}
.btnrow{display:flex; gap:7px; flex-wrap:wrap}
.scale{display:flex; flex-direction:column; gap:5px}
.ramp{height:11px; width:100%; border:1px solid var(--rule)}
.scale-ends{display:flex; justify-content:space-between; font-family:var(--mono); font-size:10px; color:var(--ink-3)}

/* ---------- pipeline ---------- */
.pipe{display:flex; flex-wrap:wrap; gap:9px; align-items:stretch; margin-top:4px}
.step{
  flex:1 1 168px; border:1px solid var(--rule); background:var(--card); padding:13px 14px;
  display:flex; flex-direction:column; gap:5px; position:relative;
}
.step .n{font-family:var(--mono); font-size:10px; color:var(--ink-3); letter-spacing:.1em}
.step .t{font-family:var(--sans); font-size:13px; font-weight:650; line-height:1.3}
.step .d{font-family:var(--sans); font-size:11.5px; color:var(--ink-2); line-height:1.45}
.step .num{font-family:var(--mono); font-size:11px; color:var(--clay); font-variant-numeric:tabular-nums}

/* ---------- table ---------- */
.tblwrap{overflow-x:auto; border:1px solid var(--rule); background:var(--card)}
table{border-collapse:collapse; width:100%; min-width:660px; font-family:var(--sans); font-size:13.5px}
th,td{text-align:left; padding:11px 14px; border-bottom:1px solid var(--rule-2); vertical-align:top}
thead th{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.11em; text-transform:uppercase;
  color:var(--ink-3); font-weight:500; border-bottom:1px solid var(--rule); white-space:nowrap;
}
tbody tr:last-child td{border-bottom:none}
td.us{color:var(--ink)}
.tag{
  display:inline-block; font-family:var(--mono); font-size:10px; letter-spacing:.06em;
  padding:2px 6px; border-radius:2px; text-transform:uppercase; white-space:nowrap;
}
.tag.gap{background:color-mix(in srgb,var(--bad) 15%,transparent); color:var(--bad)}
.tag.part{background:color-mix(in srgb,var(--warn) 18%,transparent); color:var(--warn)}
.tag.ok{background:color-mix(in srgb,var(--good) 16%,transparent); color:var(--good)}
.rowlab{font-family:var(--sans); font-weight:650; font-size:13px}

.callout{
  border-left:3px solid var(--clay); background:var(--card); padding:16px 20px;
  display:flex; flex-direction:column; gap:8px;
}
.callout .k{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.12em; text-transform:uppercase; color:var(--clay);
}
.figures{display:flex; gap:26px; flex-wrap:wrap; margin-top:2px}
.fig{display:flex; flex-direction:column; gap:2px}
.fig .fv{font-family:var(--mono); font-size:25px; font-weight:600; font-variant-numeric:tabular-nums; letter-spacing:-.02em}
.fig .fk{font-family:var(--sans); font-size:11.5px; color:var(--ink-3)}
footer{
  margin-top:64px; padding-top:20px; border-top:1px solid var(--rule);
  font-family:var(--mono); font-size:11px; color:var(--ink-3); line-height:1.7;
}
@media (max-width:820px){
  .instrument{grid-template-columns:1fr}
  .panel{border-left:none; border-top:1px solid var(--rule)}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important; animation:none!important}}
</style>

<div class="wrap">

<header class="masthead">
  <div class="eyebrow">
    <span>Soft-robot evolution</span><span>Morphology diagnostic</span><span>Champion 1.3201 BL</span>
  </div>
  <h1>Why the Robots Are Blobs</h1>
  <p class="standfirst">
    Every champion this project has evolved is an undifferentiated slab. The cause isn't the
    physics engine and it isn't a lack of compute — it's that a body is a <em>level set</em> of a
    smooth field, and the fitness function never asked for anything else.
  </p>
</header>

<section>
  <div class="sec-head"><span class="sec-num">01</span><h2>The instrument</h2></div>
  <p>
    A robot's body is not a list of voxels. It's a network (a CPPN) that answers, for each of the
    5832 grid positions, a single question: <em>how strongly should there be material here?</em>
    That produces a scalar landscape. The body is whatever stands above a waterline.
  </p>
  <p>
    Below is the actual presence field of the record champion. Move the waterline and watch the
    body form, thin, and break apart.
  </p>

  <div class="instrument">
    <div class="stage">
      <div class="canvas-row">
        <div class="cwrap" style="flex:1 1 300px">
          <canvas id="slice" width="360" height="360"></canvas>
          <div class="clabel">Horizontal slice &mdash; layer <span id="zlab">9</span> of 18</div>
        </div>
        <div class="cwrap" style="flex:0 1 220px">
          <canvas id="side" width="260" height="260"></canvas>
          <div class="clabel">Side elevation &mdash; all layers</div>
        </div>
      </div>
      <div class="scale">
        <div class="ramp" id="ramp"></div>
        <div class="scale-ends"><span>-1.00 &nbsp;empty</span><span>presence value</span><span>solid&nbsp; +1.00</span></div>
      </div>
    </div>

    <div class="panel">
      <div class="ctrl">
        <div class="ctrl-head"><label for="wl">Waterline</label><span class="val" id="wlv">0.736</span></div>
        <input type="range" id="wl" min="-1" max="0.92" step="0.005" value="0.7355">
        <div class="hint">The decoder doesn't pick a height &mdash; it lowers the waterline until exactly
          300 voxels stand above it. Drag to see what other budgets would have produced.</div>
      </div>
      <div class="ctrl">
        <div class="ctrl-head"><label for="z">Layer</label><span class="val" id="zv">9</span></div>
        <input type="range" id="z" min="0" max="17" step="1" value="9">
      </div>
      <div class="btnrow">
        <button class="btn" id="bField" aria-pressed="true">Field</button>
        <button class="btn" id="bBody" aria-pressed="true">Body</button>
        <button class="btn" id="bReset">Reset</button>
      </div>
      <div class="readout">
        <div class="rrow"><span class="rk">Voxels above line</span><span class="rv hot" id="rCount">300</span></div>
        <div class="rrow"><span class="rk">In this layer</span><span class="rv" id="rLayer">0</span></div>
        <div class="rrow"><span class="rk">Pass the gate (&gt;0)</span><span class="rv" id="rGate">1766</span></div>
        <div class="rrow"><span class="rk">Grid positions</span><span class="rv">5832</span></div>
      </div>
    </div>
  </div>
</section>

<section>
  <div class="sec-head"><span class="sec-num">02</span><h2>How a body is decoded</h2></div>
  <p>
    Four steps run every time a genome becomes a robot. Step three is where the shape is decided
    &mdash; and where the trouble starts.
  </p>
  <div class="pipe">
    <div class="step">
      <span class="n">STEP 1</span><span class="t">Query every position</span>
      <span class="d">The network is evaluated at each grid point, taking its coordinates and distance from centre.</span>
      <span class="num">5832 queries</span>
    </div>
    <div class="step">
      <span class="n">STEP 2</span><span class="t">Gate on presence</span>
      <span class="d">Positions whose presence value clears zero become candidates. Roughly 43% of the grid does.</span>
      <span class="num">1766 candidates</span>
    </div>
    <div class="step">
      <span class="n">STEP 3</span><span class="t">Keep the strongest</span>
      <span class="d">Only the highest-confidence candidates survive, up to the voxel budget. This is the waterline.</span>
      <span class="num">&rarr; 300 kept</span>
    </div>
    <div class="step">
      <span class="n">STEP 4</span><span class="t">Drop loose parts</span>
      <span class="d">Anything not face-connected to the main mass is deleted. Measured: this fires on 0&ndash;1% of bodies. It is not the constraint &mdash; limbs never form to begin with.</span>
      <span class="num">0&ndash;1% affected</span>
    </div>
  </div>
  <div class="callout">
    <span class="k">The consequence</span>
    <p>Because the surviving body is always the <em>top slice</em> of a smooth landscape, it is
      compact by construction. The waterline auto-adjusts to spend the entire budget, so thinning
      one region simply refills another. Until recently the budget was a fixed cap, which meant
      body size was not an evolvable trait at all &mdash; 98% of bodies came out at exactly the cap.</p>
  </div>
</section>

<section>
  <div class="sec-head"><span class="sec-num">03</span><h2>What the champion actually is</h2></div>
  <div class="figures">
    <div class="fig"><span class="fv">1.3201</span><span class="fk">body-lengths travelled</span></div>
    <div class="fig"><span class="fv">300</span><span class="fk">voxels (100% muscle)</span></div>
    <div class="fig"><span class="fv">6&times;11&times;11</span><span class="fk">bounding box</span></div>
    <div class="fig"><span class="fv">0.41</span><span class="fk">fill density</span></div>
    <div class="fig"><span class="fv">1.83</span><span class="fk">elongation</span></div>
  </div>
  <p>
    Not a sphere &mdash; a flattened slab, filling 41% of its own bounding box, with layer areas
    tapering <code>39 &rarr; 4</code> from base to top. A mound. There are no thin parts, no
    protrusions, and no functional regions: every voxel is the same material doing the same job.
    Legs would show the inverse profile, narrow at the bottom.
  </p>
</section>

<section>
  <div class="sec-head"><span class="sec-num">04</span><h2>The papers did not get blobs</h2></div>
  <p>
    Cheney et al. (2013), the paper this project re-implements, evolved robots their authors
    named and catalogued: <strong>L-Walker</strong>, <strong>Incher</strong>,
    <strong>Push-Pull</strong>, <strong>Jitter</strong>, <strong>Jumper</strong> and
    <strong>Wings</strong> &mdash; described with hind legs, necks, heads and arms. They reached
    3.5&ndash;4.0 body-lengths. Same encoding, same materials, same flat ground. The differences
    are in what evolution was <em>asked</em> for.
  </p>
  <div class="tblwrap">
    <table>
      <thead><tr><th>Constraint</th><th>This project</th><th>Cheney 2013 &middot; Corucci 2018</th><th>Status</th></tr></thead>
      <tbody>
        <tr>
          <td class="rowlab">Cost of material</td>
          <td class="us">None. Bodies are free to be maximally dense.</td>
          <td>Fitness multiplied by <code>1 &minus; voxels/max</code>. Corucci makes minimising voxels an explicit objective &ldquo;to favour interesting morphologies&rdquo;.</td>
          <td><span class="tag gap">missing</span></td>
        </tr>
        <tr>
          <td class="rowlab">Cost of muscle</td>
          <td class="us">None. All-muscle bodies pay nothing.</td>
          <td>A separate regime penalises actuated voxels &mdash; which pushed evolution to adopt inert support tissue instead.</td>
          <td><span class="tag part">added</span></td>
        </tr>
        <tr>
          <td class="rowlab">Actuation strength</td>
          <td class="us">8% tendon-length change.</td>
          <td>20% volumetric expansion &mdash; roughly 7&times; more ground covered per actuation cycle.</td>
          <td><span class="tag part">testing</span></td>
        </tr>
        <tr>
          <td class="rowlab">Leaving the ground</td>
          <td class="us">Penalised. Credit is zeroed above twice resting height.</td>
          <td>No height penalty at all &mdash; which is precisely why Jumper and Jitter exist as classes.</td>
          <td><span class="tag part">loosened</span></td>
        </tr>
        <tr>
          <td class="rowlab">Body size</td>
          <td class="us">Hard cap; 98% of bodies sit exactly on it.</td>
          <td>No cap. Size is shaped by penalty, so evolution genuinely chooses it.</td>
          <td><span class="tag ok">fixed</span></td>
        </tr>
        <tr>
          <td class="rowlab">Search diversity</td>
          <td class="us">Archive spans gait traits: height &times; bounce.</td>
          <td>Corucci measures morphology directly &mdash; symmetry and shape descriptors.</td>
          <td><span class="tag part">added</span></td>
        </tr>
        <tr>
          <td class="rowlab">Replication</td>
          <td class="us">1&ndash;3 seeds per treatment.</td>
          <td>35 independent runs per treatment.</td>
          <td><span class="tag gap">gap</span></td>
        </tr>
      </tbody>
    </table>
  </div>
  <div class="callout">
    <span class="k">The synthesis</span>
    <p>Blobs are not a physical inevitability. They are the optimal answer to the question this
      fitness function actually asks: travel forward, pay nothing for mass, pay nothing for
      muscle, fill the budget completely, and stay on the ground. A dense low slab wins that
      contest every time. The papers asked a different question and got animals.</p>
  </div>
</section>

<footer>
  Presence field sampled from the evolved champion of run <code>pvp_s1</code> &mdash; 300 voxels,
  1.3201 body-lengths, per-voxel evolved phase control.<br>
  References: Cheney, MacCurdy, Clune &amp; Lipson, <em>Unshackling Evolution</em>, GECCO 2013 &middot;
  Corucci et al., <em>Evolving Soft Locomotion in Aquatic and Terrestrial Environments</em>, 2018.
</footer>

</div>

<script type="application/json" id="fielddata">__DATA__</script>
<script>
(function(){
  const D = JSON.parse(document.getElementById('fielddata').textContent);
  const N = D.n, F = D.field, B = D.body;
  const STOPS = [[15,48,56],[28,84,98],[53,127,139],[127,174,172],[207,196,158],[223,163,68],[176,95,28]];
  function ramp(t){
    t = Math.max(0, Math.min(1, t));
    const x = t * (STOPS.length - 1), i = Math.min(STOPS.length - 2, Math.floor(x)), f = x - i;
    const a = STOPS[i], b = STOPS[i+1];
    return 'rgb(' + Math.round(a[0]+(b[0]-a[0])*f) + ',' + Math.round(a[1]+(b[1]-a[1])*f) + ',' +
                    Math.round(a[2]+(b[2]-a[2])*f) + ')';
  }
  // legend
  (function(){
    const r = document.getElementById('ramp');
    let s = 'linear-gradient(to right';
    for (let i=0;i<=10;i++) s += ',' + ramp(i/10);
    r.style.background = s + ')';
  })();

  const cv = document.getElementById('slice'), cx = cv.getContext('2d');
  const sv = document.getElementById('side'),  sx = sv.getContext('2d');
  const elZ = document.getElementById('z'), elW = document.getElementById('wl');
  const showField = {on:true}, showBody = {on:true};

  function ink(){ return getComputedStyle(document.body).getPropertyValue('--line').trim() || '#000'; }

  function countAbove(w){
    let n = 0;
    for (let z=0;z<N;z++) for (let y=0;y<N;y++) for (let x=0;x<N;x++) if (F[z][y][x] >= w) n++;
    return n;
  }
  function draw(){
    const w = parseFloat(elW.value), z = parseInt(elZ.value,10);
    const cell = cv.width / N;
    cx.clearRect(0,0,cv.width,cv.height);
    let layer = 0;
    for (let y=0;y<N;y++){
      for (let x=0;x<N;x++){
        const v = F[z][y][x], px = x*cell, py = (N-1-y)*cell;
        if (showField.on){ cx.fillStyle = ramp((v+1)/2); cx.fillRect(px,py,cell+0.5,cell+0.5); }
        else { cx.fillStyle = 'rgba(0,0,0,0)'; cx.fillRect(px,py,cell+0.5,cell+0.5); }
        if (v >= w){
          layer++;
          if (showBody.on){
            cx.fillStyle = showField.on ? 'rgba(255,255,255,0.16)' : ramp((v+1)/2);
            cx.fillRect(px,py,cell+0.5,cell+0.5);
            cx.strokeStyle = ink(); cx.lineWidth = 1.1;
            cx.strokeRect(px+0.5,py+0.5,cell-1,cell-1);
          }
        }
      }
    }
    // side elevation: for each (x,z) show whether ANY y in that column is above the line
    const sc = sv.width / N;
    sx.clearRect(0,0,sv.width,sv.height);
    for (let z2=0; z2<N; z2++){
      for (let x=0; x<N; x++){
        let best = -1;
        for (let y=0;y<N;y++) best = Math.max(best, F[z2][y][x]);
        const px = x*sc, py = (N-1-z2)*sc;
        sx.fillStyle = ramp((best+1)/2); sx.globalAlpha = 0.35;
        sx.fillRect(px,py,sc+0.5,sc+0.5); sx.globalAlpha = 1;
        if (best >= w){
          sx.fillStyle = ramp((best+1)/2); sx.fillRect(px,py,sc+0.5,sc+0.5);
          sx.strokeStyle = ink(); sx.lineWidth = 0.9;
          sx.strokeRect(px+0.45,py+0.45,sc-0.9,sc-0.9);
        }
      }
    }
    // ground line
    sx.strokeStyle = ink(); sx.lineWidth = 1.5;
    sx.beginPath(); sx.moveTo(0, sv.height-0.75); sx.lineTo(sv.width, sv.height-0.75); sx.stroke();

    document.getElementById('wlv').textContent = w.toFixed(3);
    document.getElementById('zv').textContent  = z;
    document.getElementById('zlab').textContent = z;
    document.getElementById('rLayer').textContent = layer;
    const tot = countAbove(w);
    const rc = document.getElementById('rCount');
    rc.textContent = tot;
    rc.style.color = (tot === D.n_body) ? '' : 'var(--teal-2)';
  }
  elZ.addEventListener('input', draw);
  elW.addEventListener('input', draw);
  function toggle(btn, state){
    btn.addEventListener('click', function(){
      state.on = !state.on;
      btn.setAttribute('aria-pressed', state.on ? 'true' : 'false');
      draw();
    });
  }
  toggle(document.getElementById('bField'), showField);
  toggle(document.getElementById('bBody'),  showBody);
  document.getElementById('bReset').addEventListener('click', function(){
    elW.value = D.waterline; elZ.value = 9; draw();
  });
  document.getElementById('rGate').textContent = D.gate_pass;
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  if (mq.addEventListener) mq.addEventListener('change', draw);
  draw();
})();
</script>
"""

out = HTML.replace('__DATA__', json.dumps(DATA, separators=(',', ':')))
path = r'C:\SoftRobotEvolution\morphology_artifact.html'
with open(path, 'w', encoding='utf-8') as f:
    f.write(out)
print(f"wrote {path}  ({os.path.getsize(path)/1024:.0f} KB)")
