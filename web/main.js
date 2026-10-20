import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Food } from './food.js';
import { Props, SPOTS } from './props.js';
import { FlowEngine } from './flow-engine.js';
import * as Sim from './sim.js';

const $ = (sel) => document.querySelector(sel);
const esc = (v) => String(v ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const small = matchMedia('(max-width: 820px)').matches;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------- renderer, scene, post ----------
const canvas = $('#scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, small ? 1.5 : 2));
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color('#1b1815');
const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 20);
const sun = new THREE.DirectionalLight(new THREE.Color('#fff4e6'), 2.4);
sun.position.set(-0.9, 1.1, 0.4);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -1.3, right: 1.1, top: 0.8, bottom: -0.8, near: 0.2, far: 4 });
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.01;
scene.add(sun);

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
// No ambient-occlusion pass: it shaded the (transparent) steam sprites as solid squares.
composer.addPass(new SMAAPass(1, 1));
composer.addPass(new OutputPass());

function resize() {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  renderer.setSize(w, h, false);
  composer.setSize(w, h);
  camera.aspect = w / h;
  camera.fov = w / h < 0.8 ? 58 : 40;
  camera.updateProjectionMatrix();
}
addEventListener('resize', resize);

// ---------- camera views (names match the "Camera view" column in the flow sheet) ----------
const V = (p, l) => ({ pos: new THREE.Vector3(...p), look: new THREE.Vector3(...l) });
const VIEWS = {
  'Overview': V([0.05, 1.05, 1.35], [-0.05, 0, 0.02]),
  'Kitchen': V([-0.2, 1.75, 2.55], [-0.2, 0.0, -0.05]),
  'Counter': V([0.58, 0.5, 0.44], [0.64, 0.02, -0.06]),
  'Cutting board': V([0.66, 0.42, 0.42], [0.66, 0.02, 0.09]),
  'Stove': V([0.04, 0.5, 0.46], [0.01, 0.05, 0.0]),
  'Pot': V([-0.6, 0.5, 0.42], [-0.62, 0.07, -0.08]),
  'Stove wide': V([-0.3, 0.62, 0.62], [-0.3, 0.05, -0.04]),
  'Peek in the pan': V([0.06, 0.34, 0.19], [0, 0.06, 0.005]),
  'Sink': V([-0.84, 0.55, 0.52], [-0.84, 0.04, -0.06]),
  'Serving': V([0, 0.4, 0.82], [0, 0.04, 0.44]),
};
// Pasta-pot substeps use the Stove view in the sheet; the pot sits on its own burner, so frame that.
const CAMERA_OVERRIDE = { 'S1.1': 'Kitchen', 'S1.2': 'Kitchen', 'S1.3': 'Kitchen', 'S6.1': 'Pot', 'S6.2': 'Pot', 'S6.3': 'Pot', 'S7.1': 'Stove wide' };
const VIEW_BUTTONS = ['Kitchen', 'Counter', 'Cutting board', 'Pot', 'Stove', 'Peek in the pan', 'Sink', 'Serving'];
let view = 'Overview';
const camPos = VIEWS.Overview.pos.clone(), camLook = VIEWS.Overview.look.clone(), goal = new THREE.Vector3();
const lastShift = { x: -1, y: -1, w: 0, h: 0 };
$('#views').innerHTML = VIEW_BUTTONS.map((v) => `<button data-view="${esc(v)}" aria-pressed="false">${esc(v.replace('Peek in the pan', 'Pan').replace('Cutting board', 'Board'))}</button>`).join('');
function setView(v) {
  if (!VIEWS[v]) return;
  view = v;
  document.querySelectorAll('[data-view]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.view === v)));
}
$('#views').addEventListener('click', (e) => { const b = e.target.closest('[data-view]'); if (b) setView(b.dataset.view); });

// ---------- load the kitchen and the flow ----------
// The artifact host serves neither .glb files nor fetches of data: URLs, so the model
// ships as base64 text and is decoded here; its textures are plain .jpg files.
async function loadKitchen() {
  const res = await fetch('assets/kitchen.glb.b64.txt');
  if (!res.ok) throw new Error(`kitchen model: HTTP ${res.status}`);
  const bytes = Uint8Array.from(atob((await res.text()).trim()), (c) => c.charCodeAt(0));
  $('#load-bar').style.width = '70%';
  return new GLTFLoader().parseAsync(bytes.buffer, 'assets/');
}
async function loadFlow() {
  const res = await fetch('flow.json');
  if (!res.ok) throw new Error(`flow.json: HTTP ${res.status}`);
  return res.json();
}
const [gltf, FLOW] = await Promise.all([loadKitchen(), loadFlow()]).catch((err) => {
  $('#load-msg').textContent = `The kitchen couldn’t load. Refresh to try again. (${err?.message || err})`;
  throw err;
});

const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.03).texture;
scene.environmentIntensity = 0.7;

gltf.scene.traverse((o) => {
  if (!o.isMesh) return;
  o.castShadow = o.receiveShadow = true;
  if (o.material?.name === 'CastIron') {
    o.material.clearcoat = 0.25;
    o.material.color.set('#2a2826');
  }
});
scene.add(gltf.scene);
// Rearrange the Blender set for the flow: egg bowl on the prep side, eggs by the board.
const bowlObj = gltf.scene.getObjectByName('Bowl');
if (bowlObj) bowlObj.position.set(SPOTS.eggBowl.x, bowlObj.position.y, SPOTS.eggBowl.z);
['Sphere', 'Sphere001', 'Sphere002'].forEach((n) => { const o = gltf.scene.getObjectByName(n); if (o) o.visible = false; });
['Egg0', 'Egg1'].forEach((n, i) => { const o = gltf.scene.getObjectByName(n); if (o) o.position.set(SPOTS.eggs[i].x, o.position.y, SPOTS.eggs[i].z); });
const knob = gltf.scene.getObjectByName('HeatKnob');
const grip = gltf.scene.getObjectByName('HeatKnobGrip');
if (knob && grip) knob.attach(grip);

const food = new Food(scene, { bundles: small ? 60 : 95 });
const props = new Props(scene, { pastaMaterial: food.pastaMat, tofuMaterial: food.tofuMaterial });
// Kitchen pieces from the Blender set that also only appear once brought to the counter.
const named = (...names) => names.map((n) => gltf.scene.getObjectByName(n)).filter(Boolean);
props.items['T-SKILLET'] = named('Skillet', 'Handle', 'HelperHandle');
props.items['I-EGGS'] = named('Egg0', 'Egg1');
props.items['T-BOWL'].push(...named('Bowl'));
resize();

// ---------- state ----------
const engine = new FlowEngine(FLOW);
let s, w;
function freshState() {
  s = Sim.newState();
  s.tofuInPan = false;
  w = {
    tofuStage: 'none', towelBottom: false, towelTop: false, weight: false, pressDone: false, cutLevel: 0,
    potOnHob: false, potFilled: false, tapOn: false, waterLevel: 0, lidOn: false, backHeat: 0, boil: 0, pastaInPot: false,
    oil: false, tossT: 0, flips: 0, bowlStage: 'empty', wholeEggs: 0, yolks: 0, cheeseIn: false, mugFull: false,
    plated: 0, peppered: false, served: false, bellT: 0,
    committed: new Set(),   // items brought to the counter in step 1 (flow item IDs)
    onCounter: new Set(),   // committed + whatever is ticked right now
  };
}
freshState();

let run = null;           // fast-forward: { remaining, speed, resolve }
let live = false;         // S7.4: sauce reacts in (sped-up) real time
let ui = { mode: 'none', source: null, pending: null, selected: new Set(), feedback: null, hint: null, locked: false };

// ---------- what each action does to the kitchen ----------
// Keyed by action ID from flow.json; values may be async (fast-forwarded cooking).
let jumping = false;      // internal step jump: cooking happens instantly
// Waits in the recipe are fast-forwarded (a few real seconds at most) behind a kitchen timer.
let ffLabel = '';
const ff = (seconds, speed = 30) => {
  if (jumping) { for (let t = 0; t < seconds; t += 0.5) Sim.stepModel(s, 0.5); return Promise.resolve(); }
  return new Promise((resolve) => {
    run = { total: seconds, remaining: seconds, speed: Math.max(speed, seconds / 3), resolve };
    $('#ff-label').textContent = ffLabel || 'Cooking';
    renderTimer();
    $('#ff').hidden = false;
  });
};
const mmss = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
function renderTimer() {
  const done = run.total - run.remaining;
  $('#ff-time').textContent = `${mmss(done)} / ${mmss(run.total)}`;
  $('#ff-ring').style.setProperty('--p', `${(done / run.total) * 360}deg`);
}
const VISUALS = {
  'A-2.1-01': async () => { w.tofuStage = 'draining'; await sleep(jumping ? 0 : 1600); w.tofuStage = 'block'; },
  'A-2.1-02': () => { w.towelBottom = true; },          // slides in under the tofu
  'A-2.1-03': () => { w.towelTop = true; },
  'A-2.1-04': () => { w.weight = true; w.tofuStage = 'pressing'; },
  'A-2.3-02': () => { w.cutLevel = 1; },
  'A-2.3-03': () => { w.cutLevel = 2; },
  'A-2.3-04': async () => { w.cutLevel = 3; await sleep(500); w.tofuStage = 'cubes'; },
  'A-2.3-05': () => { w.cutLevel = 3; w.tofuStage = 'cubes'; },
  'A-2.3-06': () => { w.tofuStage = 'cubes'; },
  'A-3.1-02': () => { w.tapOn = false; w.potFilled = true; },
  'A-3.1-03': () => { w.potOnHob = true; },
  'A-3.1-04': () => { w.backHeat = 3; },
  'A-3.1-05': () => { w.lidOn = true; },
  'A-4.2-01': () => { s.heat = 2; },
  'A-4.2-02': () => { w.oil = true; },
  'A-4.2-03': () => ff(60),
  'A-4.2-04': () => { w.tofuStage = 'pan'; s.tofuInPan = true; },
  'A-4.2-05': () => ff(180),
  'A-4.2-06': () => { w.tossT = 1; w.flips += 1; },
  'A-4.2-07': () => ff(210),
  'A-4.2-08': () => { w.tossT = 1; },
  'A-4.2-09': async () => { s.heat = 3; s.tofuInPan = true; w.tofuStage = 'pan'; await ff(300, 40); },
  'A-4.3-01': () => { s.heat = 0; },
  'A-4.3-03': () => { w.tofuStage = 'plate'; s.tofuInPan = false; s.guancialeDone = true; },
  'A-4.3-04': async () => { w.oil = false; await sleep(700); w.oil = true; },
  'A-5.2-02': () => { w.bowlStage = 'eggs'; w.wholeEggs = 2; },
  'A-5.2-03': () => { w.yolks = 3; },
  'A-5.4-01': () => { w.cheeseIn = true; },
  'A-5.4-03': () => { w.bowlStage = 'paste'; },
  'A-6.2-02': () => { w.pastaInPot = true; },
  'A-7.1-01': () => { w.mugFull = true; s.savedWater = true; },
  'A-7.1-02': () => { s.heat = 1; },
  'A-7.1-03': () => { w.pastaInPot = false; Sim.addPasta(s); },
  'A-7.1-04': () => { w.tossT = 0.6; },
  'A-7.1-05': () => { w.waterLevel = 0.01; },
  'A-7.2-03': () => { w.bowlStage = 'tempered'; },
  'A-7.4-01': () => { w.bowlStage = 'empty'; Sim.addEggs(s); live = true; },
  'A-7.4-04': () => { s.heat = s.heat > 0 ? 0 : 1; },
  'A-7.4-05': () => { Sim.splashWater(s); },
  'A-8.2-01': () => { w.tofuStage = 'pile'; },
  'A-8.2-02': () => { s.heat = 0; w.plated = 2; w.served = true; w.tofuStage = 'served'; },
  'A-8.2-03': () => { w.peppered = true; },
  'A-8.2-05': () => { w.bellT = 1.2; },
};
// Effects of MCQ answers that change the kitchen.
function applyOptionEffect(o) {
  const e = o.effect || '';
  if (/heat = off/.test(e)) s.heat = 0;
  if (/heat = low/.test(e)) s.heat = 1;
  if (/heat = medium/.test(e)) s.heat = 2;
}
// What the kitchen looks like when a substep starts (in case earlier steps were skipped or retried).
// Step 1 brings everything out; later steps add the resting plate and serving bowls.
function commitStep1() {
  FLOW.options.filter((o) => (o.sub === 'S1.2' || o.sub === 'S1.3') && o.correctness !== 'Incorrect' && o.item)
    .forEach((o) => w.committed.add(o.item));
  if (w.tofuStage === 'none') w.tofuStage = 'pack';
}
const ENTER = {
  'S2.1': () => commitStep1(),
  'S4.3': () => w.committed.add('PLATE'),
  'S8.1': () => w.committed.add('SERVING'),
  'S2.3': () => { w.pressDone = true; w.tofuStage = 'pressed'; },
  'S4.1': () => { w.boil = 0.3; },
  'S6.1': () => { w.lidOn = false; w.boil = 1; w.potOnHob = true; w.potFilled = true; },
  'S7.4': () => { s.heat = s.heat; },
};

// ---------- panels ----------
const left = $('#left'), right = $('#right'), pins = $('#pins');

// In the live sauce step, the wrong-outcome rows (scrambled, runny, grainy) are decided by the
// temperature model when you plate, and tossing/plating have their own controls.
const LIVE_SUB = 'S7.4';
function choices() {
  const acts = engine.available();
  return engine.sub.id === LIVE_SUB ? acts.filter((a) => a.order === '1' || a.order === 'opt') : acts;
}

// Nonna's running commentary while the sauce comes together.
function liveLine() {
  const T = s.foodTemp;
  if (s.curds >= 0.3) return 'It’s scrambling! Off the heat, splash in water, toss fast!';
  if (T > 68) return `${Math.round(T)}°C. Close to scrambling. Off the heat, toss faster or add a splash of water.`;
  if (s.thicken >= 0.6 && s.curds < 0.08) return 'Look at that shine. It coats the strands. Plate it now!';
  if (T < 58) return 'Too cool to thicken. The yolks need about 62°C. A moment of gentle heat will help.';
  return 'Good, steady heat. Keep tossing. Starch, oil and yolk are coming together.';
}

function chip(text, kind = '') { return `<span class="chip ${esc(kind)}">${esc(text)}</span>`; }

// One task at a time: the next thing to do in this procedure.
function taskList() {
  const req = engine.required();
  const i = req.findIndex((a) => !engine.done.has(a.id));
  if (i < 0) return `<div class="task-card" aria-live="polite"><p class="task-now">All done. Press Continue.</p></div>`;
  return `<div class="task-card" aria-live="polite">
      <span class="task-no">${engine.stepIndex()}.${i + 1}</span><p class="task-now">${esc(req[i].task || req[i].param)}</p>
    </div>`;
}

function renderLeft() {
  const sub = engine.sub;
  const stepNo = engine.stepIndex();
  const isProc = sub.type === 'Procedure';
  const doneSteps = isProc ? engine.required().filter((a) => engine.done.has(a.id)) : [];
  const fb = ui.feedback;
  left.innerHTML = `
    <div class="stepbar">
      <span class="eyebrow">Step ${stepNo} of ${engine.steps.length}</span>
      <div id="progress" aria-hidden="true"></div>
      <span class="score">Score <b id="score">${engine.score}</b></span>
    </div>
    <h2>${esc(sub.title)}</h2>
    ${sub.required === 'No' ? `<div class="meta">${chip('Optional', 'type')}</div>` : ''}
    ${isProc ? '' : `<p class="instr">${esc(sub.left)}</p>`}
    ${isProc ? taskList() : ''}
    ${live ? `<div class="thermo" aria-label="Sauce thermometer">
        <div class="thermo-row"><span class="eyebrow">Sauce</span><b id="thermo-val">${Math.round(s.foodTemp)}°C</b><span id="sauce-state">${esc(Sim.sauceState(s))}</span></div>
        <div class="thermo-bar"><div id="thermo-fill"></div><i style="left:${((62 - 40) / 45) * 100}%"></i><i style="left:${((70 - 40) / 45) * 100}%"></i></div>
        <div class="thermo-scale"><span>40</span><span>62 thickens</span><span>70 scrambles</span><span>85</span></div>
        <p class="live-line" id="live-line">${esc(liveLine())}</p>
      </div>` : ''}
    `;
  if (doneSteps.length === 0 && isProc) left.querySelector('.task-card')?.classList.add('fresh');
  renderPop(fb);
}

// How many tries are left before Nonna shows the answer (MCQ) or gives a hint (procedure).
function chancesLine() {
  if (engine.ready) return '';
  const left = engine.sub.maxAttempts - engine.attempts;
  if (left <= 0) return '';
  return left === 1 ? 'You have 1 more chance.' : `You have ${left} more chances.`;
}
function missesLine() {
  const left = engine.sub.maxAttempts - engine.misses;
  if (left <= 0) return '';
  return left === 1 ? 'One more wrong move and I’ll give you a hint.' : `${left} more tries before I give you a hint.`;
}
// Feedback stays until you close it: the ×, or a click anywhere outside it. Popups that
// finish a substep only close through their Continue button.
document.addEventListener('click', (e) => {
  const pop = $('#fb-pop');
  if (pop.hidden || !pop.dataset.dismissable || pop.contains(e.target)) return;
  if (performance.now() - popOpenedAt < 120) return;   // the click that opened it
  pop.hidden = true;
});

// Nonna's feedback pops up at the top centre of the kitchen. When the substep is finished the
// popup holds the Continue button; otherwise it can be dismissed and fades on its own.
let popOpenedAt = 0;
let popKey = '';
function renderPop(fb) {
  const pop = $('#fb-pop');
  const sub = engine.sub;
  const ready = engine.ready;
  const lines = fb ? (Array.isArray(fb.text) ? fb.text : [fb.text]).filter(Boolean) : [];
  if (!lines.length && ready) lines.push(sub.type === 'Procedure' ? 'All done here. Nicely worked.' : 'That’s it. On to the next one.');
  if (ui.hint) lines.push(`Hint: ${engine.item(ui.hint.source).name} → ${ui.hint.param}`);
  if (!lines.length || ui.locked) { pop.hidden = true; return; }
  const key = JSON.stringify([lines, fb?.outcome, ready]);
  if (key === popKey && !pop.hidden) return;          // unchanged: leave it (and its timer) alone
  popKey = key;
  pop.className = `fb-pop ${fb?.outcome || ''}`;
  pop.innerHTML = `
    <div class="chef-face" aria-hidden="true">P</div>
    <div class="fb-body">
      <span class="chef-name">NONNA PINA ${fb?.outcome ? chip(fb.outcome, fb.outcome) : ''}</span>
      ${lines.map((t) => `<p>${esc(t)}</p>`).join('')}
    </div>
    <button class="pop-close" id="pop-close" aria-label="Dismiss">×</button>`;
  pop.hidden = false;
  pop.dataset.dismissable = '1';
  popOpenedAt = performance.now();
  $('#pop-close')?.addEventListener('click', () => { pop.hidden = true; });
}

// Studio photos rendered in Blender (blender/item_cards.py), one per ingredient and tool.
const ITEM_IMAGES = new Set(['I-SPAGHETTI', 'I-TOFU', 'I-EGGS', 'I-PECORINO', 'I-PEPPER', 'I-SALT', 'I-OIL', 'I-SOY',
  'I-PAPRIKA', 'I-GUANCIALE', 'I-CREAM', 'I-GARLIC', 'I-BUTTER', 'I-PARSLEY', 'T-POT', 'T-SKILLET', 'T-KNIFE', 'T-TOWELS',
  'T-GRATER', 'T-BOWL', 'T-SLOTTED', 'T-TONGS', 'T-MUG', 'T-COLANDER', 'T-BLENDER', 'T-TRAY', 'E-WEIGHT', 'E-TIMER']);
const itemImg = (id, cls = '') => (ITEM_IMAGES.has(id) ? `<img class="${cls}" src="assets/items/${esc(id)}.jpg" alt="" loading="lazy">` : '');

// Item picker cards look like the Step 1 tiles: photo and a short name.
function itemCard(id, extra = '') {
  const it = engine.item(id);
  const label = FLOW.options.find((o) => o.item === id)?.label || it.name.replace(/,\s*\d.*$/, '');
  return `<button class="card tile" data-source="${esc(id)}" ${extra}>
    <span class="tile-img">${itemImg(id) || '<span class="no-img" aria-hidden="true"></span>'}</span>
    <span class="card-label">${esc(label)}</span></button>`;
}

function interactionLabel(a) {
  return { 'Hold': 'Hold', 'Repeat click': `Tap ×${repeatCount(a)}`, 'Timer': 'Wait', 'Slider / knob': 'Turn', 'Drag': 'Move', 'Click': 'Click' }[a.interaction] || a.interaction;
}
function repeatCount(a) {
  const m = /×\s?(\d+)/.exec(a.param);
  return m ? Number(m[1]) : 3;
}

function renderRight() {
  const sub = engine.sub;
  let html = '';
  if (ui.locked) {
    html = `<span class="eyebrow">Cooking</span><p class="muted">Time is passing in the kitchen…</p>`;
  } else if (sub.type === 'MCQ - Single select' || sub.type === 'MCQ - Multi select') {
    const multi = sub.type === 'MCQ - Multi select';
    // Multi-select lists of things you bring (ingredients, tools) show as photo tiles.
    const tiles = multi && engine.options().some((o) => ITEM_IMAGES.has(o.item));
    html = `<div class="cards ${tiles ? 'grid' : ''}">` +
      engine.options().map((o) => {
        const st = ui.optState?.[o.id] || '';
        const sel = ui.selected.has(o.id);
        const img = tiles ? itemImg(o.item) : '';
        return `<button class="card opt ${multi ? 'multi' : ''} ${tiles ? 'tile' : ''} ${st} ${sel ? 'selected' : ''}" data-opt="${esc(o.id)}" aria-pressed="${sel}"
          ${engine.ready || st === 'wrong' ? 'disabled' : ''}>
          ${tiles ? `<span class="tile-img">${img || '<span class="no-img" aria-hidden="true"></span>'}</span>` : ''}
          ${multi && !tiles ? `<span class="tick" aria-hidden="true">${sel ? '✓' : ''}</span>` : ''}
          <span class="card-label">${esc(o.label)}</span>${st === 'right' ? '<span class="verdict ok">✓ Correct</span>' : st === 'wrong' ? '<span class="verdict bad">✗ Wrong</span>' : ''}</button>`;
      }).join('') + '</div>' +
      '';
  } else if (live) {
    html = `<span class="eyebrow">Toss the pasta</span>
      <div class="segmented" role="group" aria-label="Tossing speed">
        ${Sim.TOSS.map((t, i) => `<button data-toss="${i}" aria-pressed="${s.toss === i}">${t}</button>`).join('')}
      </div>
      <div class="cards">
        <button class="card" data-live="heat"><span class="card-label">${s.heat > 0 ? 'Take it off the heat' : 'Back onto the lowest flame'}</span>
          <span class="card-hint">${s.heat > 0 ? 'Flame is on. The sauce will keep heating.' : 'Gentle heat thickens a runny sauce.'}</span></button>
        <button class="card" data-live="splash"><span class="card-label">Splash of pasta water</span>
          <span class="card-hint">${s.savedWater ? 'Loosens and cools the sauce' : 'You didn’t save any'}</span></button>
      </div>
      <button class="cta" data-live="plate">Plate it</button>`;
  } else if (ui.mode === 'target') {
    const one = ui.pending.length === 1 ? ui.pending[0] : null;
    html = `<span class="eyebrow">Where does it go?</span>
      <p><b>${esc(engine.item(ui.pending[0].source).name)}</b>${one ? `: ${esc(one.param)}` : ''}</p>
      <p class="muted">Click the spot in the kitchen.</p>
      <button class="link" data-back>Cancel</button>`;
  } else if (ui.mode === 'actions') {
    const acts = choices().filter((a) => a.source === ui.source);
    html = `<button class="link" data-back>← All items</button>
      <span class="eyebrow">${esc(engine.item(ui.source).name)}: what do you do?</span><div class="cards">` +
      acts.map((a) => `<button class="card act" data-act="${esc(a.id)}" data-kind="${esc(a.interaction)}" data-need="${a.interaction === 'Repeat click' ? repeatCount(a) : 1}">
        <span class="card-label">${esc(a.param)}</span><span class="badge">${esc(interactionLabel(a))}</span><span class="fill" aria-hidden="true"></span></button>`).join('') +
      (acts.length ? '' : '<p class="muted">Nothing left to do with this.</p>') + '</div>';
  } else if (sub.type === 'Procedure' && !engine.ready) {
    // Things already in the kitchen are clicked there (pins); only the rest get cards.
    const sources = [...new Set(choices().filter((a) => !onScreen(a.source)).map((a) => a.source))];
    html = sources.length ? `<div class="cards grid">${sources.map((id) => itemCard(id)).join('')}</div>` : '';
  }
  right.innerHTML = html;
  right.hidden = !html;                     // nothing to pick here: no panel
  renderPins();
}

// ---------- pins (clickable spots in the 3D kitchen) ----------
// Clickable in the kitchen: it has a pin spot and its model is showing (or, with no model
// to check, the sheet says it's used from the scene).
function onScreen(id) {
  if (!props.anchors[id]) return false;
  const shown = props.shown(id, w);
  return shown ?? choices().some((a) => a.source === id && a.srcLoc === 'Scene');
}
let pinList = [];
function renderPins() {
  pinList = [];
  const sub = engine.sub;
  if (sub && sub.type === 'Procedure' && !engine.ready && !live && !ui.locked) {
    if (ui.mode === 'target') {
      const targets = [...new Set(engine.actions().map((a) => a.target).filter((t) => t && props.anchors[t]))];
      targets.forEach((id) => pinList.push({ id, kind: 'target' }));
    } else if (ui.mode !== 'actions') {
      [...new Set(choices().filter((a) => onScreen(a.source)).map((a) => a.source))]
        .forEach((id) => pinList.push({ id, kind: 'source' }));
    }
  }
  pins.innerHTML = pinList.map((p) => `<button class="pin ${p.kind}" data-pin="${esc(p.id)}"><span>${esc(engine.item(p.id).name)}</span></button>`).join('');
}
const tmp = new THREE.Vector3();
function placePins() {
  const r = canvas.getBoundingClientRect();
  pins.querySelectorAll('.pin').forEach((el) => {
    const a = props.anchors[el.dataset.pin];
    if (!a) return;
    tmp.copy(a).project(camera);
    const off = tmp.z > 1 || Math.abs(tmp.x) > 1.05 || Math.abs(tmp.y) > 1.05;
    el.hidden = off;
    el.style.transform = `translate(${(tmp.x * 0.5 + 0.5) * r.width}px, ${(-tmp.y * 0.5 + 0.5) * r.height}px)`;
  });
}

// ---------- interaction ----------
function setFeedback(text, outcome) { ui.feedback = text ? { text, outcome } : null; }

// Single-choice answers are judged as soon as they're picked; lists are judged by the Check button.
function checkSingle(id) {
  const res = engine.choose(id);
  const o = res.row;
  ui.optState = ui.optState || {};
  ui.optState[id] = o.correctness === 'Incorrect' ? 'wrong' : 'right';
  if (ui.optState[id] === 'wrong') { ui.selected.delete(id); ui.checkLocked = true; }
  applyOptionEffect(o);
  setFeedback([o.feedback, chancesLine()].filter(Boolean), o.outcome);
  if (res.reveal) {
    res.reveal.forEach((rid) => { ui.optState[rid] = 'right'; });
    setFeedback([o.feedback, 'Here’s the right answer. Let’s keep going.'], o.outcome);
  }
  if (res.gameOver) return gameOver();
  return refresh();
}

function doCheck() {
  const sub = engine.sub;
  const res = engine.check(ui.selected);
  ui.optState = ui.optState || {};
  if (res.pass) {
    engine.options().forEach((o) => { if (ui.selected.has(o.id)) { ui.optState[o.id] = 'right'; if (o.item) w.committed.add(o.item); } });
    setFeedback(['All there. Nicely done.', ...res.acceptable.map((o) => o.feedback)], 'Perfect');
  } else {
    res.wrong.forEach((o) => { ui.optState[o.id] = 'wrong'; ui.selected.delete(o.id); });
    const lines = res.wrong.map((o) => `${o.label}: ${o.feedback}`);
    if (res.missing.length) lines.push(sub.incomplete || 'Something is missing.');
    if (res.reveal) {
      engine.options().forEach((o) => { if (o.correctness !== 'Incorrect') { ui.optState[o.id] = 'right'; ui.selected.add(o.id); } });
      lines.push('Here’s the full list. Let’s keep going.');
    }
    if (!res.reveal) lines.push(chancesLine());
    setFeedback(lines.filter(Boolean), res.wrong.length ? 'Recoverable' : null);
  }
  ui.checkLocked = !res.pass;     // stays disabled until the picks change
  return refresh();
}

function renderAction() {
  const btn = $('#action-btn');
  const sub = engine.sub;
  if (!sub || ui.locked || live || $('#hud').hidden) { btn.hidden = true; return; }
  btn.hidden = false;
  if (sub.type === 'MCQ - Multi select' && !engine.ready) {
    // Lists: pick everything, then Check (disabled until something is picked, and after a wrong check).
    btn.textContent = 'Check';
    btn.disabled = !ui.selected.size || ui.checkLocked;
    btn.dataset.mode = 'check';
    return;
  }
  // Single choice and hands-on steps: no Check. Continue stays disabled until the substep is done.
  btn.textContent = sub.next === 'END' ? 'Finish' : 'Continue';
  btn.disabled = !engine.ready;
  btn.dataset.mode = 'continue';
}
$('#action-btn').addEventListener('click', () => {
  if ($('#action-btn').dataset.mode === 'continue') {
    $('#fb-pop').hidden = true;
    popKey = '';
    return next();
  }
  doCheck();
});

right.addEventListener('click', async (e) => {
  if (ui.locked) return;
  const sub = engine.sub;
  const opt = e.target.closest('[data-opt]');
  if (opt && !opt.disabled) {
    const id = opt.dataset.opt;
    if (sub.type === 'MCQ - Multi select') {
      ui.selected.has(id) ? ui.selected.delete(id) : ui.selected.add(id);
      ui.checkLocked = false;
      renderAction();
      return renderRight();
    }
    return checkSingle(id);                      // single select: answered as soon as it's picked
  }
  if (e.target.closest('[data-back]')) { ui.mode = 'items'; ui.pending = null; return renderRight(); }
  const src = e.target.closest('[data-source]');
  if (src) return pickSource(src.dataset.source);
  const act = e.target.closest('[data-act]');
  if (act) return handleActClick(act);
  const tossBtn = e.target.closest('[data-toss]');
  if (tossBtn) { s.toss = Number(tossBtn.dataset.toss); return renderRight(); }
  const liveBtn = e.target.closest('[data-live]');
  if (liveBtn) return liveAction(liveBtn.dataset.live);
});

// Hold-to-act and tap-repeatedly interactions on action cards.
let holdTimer = null;
right.addEventListener('pointerdown', (e) => {
  const act = e.target.closest('[data-act][data-kind="Hold"]');
  if (!act || ui.locked) return;
  const a = FLOW.actions.find((x) => x.id === act.dataset.act);
  if (a.source === 'E-TAP') w.tapOn = true;
  act.classList.add('holding');
  holdTimer = setTimeout(() => { act.classList.remove('holding'); act.dataset.held = '1'; choose(a); }, 1100);
});
const cancelHold = () => {
  clearTimeout(holdTimer);
  document.querySelectorAll('.holding').forEach((el) => el.classList.remove('holding'));
  if (!engine.done.has('A-3.1-02')) w.tapOn = false;
};
right.addEventListener('pointerup', cancelHold);
right.addEventListener('pointerleave', cancelHold);

function handleActClick(el) {
  const a = FLOW.actions.find((x) => x.id === el.dataset.act);
  if (a.interaction === 'Hold') {
    if (el.dataset.held === '1') return;
    el.querySelector('.badge').textContent = 'Press and hold';
    return;
  }
  if (a.interaction === 'Repeat click') {
    const need = Number(el.dataset.need), n = Number(el.dataset.count || 0) + 1;
    el.dataset.count = n;
    el.querySelector('.badge').textContent = `${n} / ${need}`;
    el.querySelector('.fill').style.width = `${(n / need) * 100}%`;
    if (n < need) return;
  }
  choose(a);
}

const needsTarget = (a) => ['Drag', 'Click'].includes(a.interaction) && a.target && a.target !== a.source && props.anchors[a.target];

// Picking an item: if everything you can do with it is "put it somewhere", go straight to
// choosing the spot (towel → board, towel → tofu). Otherwise list what you can do with it.
function pickSource(id) {
  ui.source = id;
  const acts = choices().filter((a) => a.source === id);
  if (acts.length && acts.every(needsTarget)) {
    ui.mode = 'target';
    ui.pending = acts;
  } else {
    ui.mode = 'actions';
  }
  renderRight();
}

function choose(a) {
  if (needsTarget(a)) {
    ui.mode = 'target';
    ui.pending = [a];
    return renderRight();
  }
  return perform(a);
}

pins.addEventListener('click', (e) => {
  const p = e.target.closest('[data-pin]');
  if (!p || ui.locked) return;
  const id = p.dataset.pin;
  if (ui.mode === 'target') {
    // The action that puts this item on that spot (the next one due, if several).
    const fits = ui.pending.filter((a) => a.target === id);
    if (fits.length) return perform(fits.find((a) => a.id === engine.nextRequired()?.id) || fits[0]);
    setFeedback('Not there. Where would this go?', null);
    return renderPop(ui.feedback);
  }
  pickSource(id);
});

async function perform(a) {
  const res = engine.perform(a.id);
  ui.mode = 'items';
  ui.pending = null;
  ui.hint = res.hint || null;
  if (res.outOfOrder) {
    if (a.source === 'E-TAP') w.tapOn = false;
    setFeedback([res.feedback, res.hint ? '' : missesLine()].filter(Boolean), null);
    return refresh();
  }
  setFeedback(res.feedback, res.ok ? (res.feedback ? 'Perfect' : null) : res.outcome);
  const fx = VISUALS[a.id];
  ffLabel = a.task || a.param;
  if (fx) {
    ui.locked = true;
    refresh();
    await fx();
    ui.locked = false;
  }
  if (res.gameOver) return gameOver();
  refresh();
}

function liveAction(kind) {
  const acts = engine.actions();
  if (kind === 'heat') perform(acts.find((a) => a.order === 'opt' && a.interaction === 'Slider / knob'));
  if (kind === 'splash') {
    if (!s.savedWater) { setFeedback('You didn’t save any pasta water. Next time, fill that mug first.', 'Recoverable'); return refresh(); }
    perform(acts.find((a) => a.order === 'opt' && a.interaction === 'Drag'));
  }
  if (kind === 'plate') plateSauce();
}

// Plating ends the live sauce: the sim decides which row of the sheet applies.
function plateSauce(forcedFatal = false) {
  live = false;
  const acts = engine.actions();
  const pick = (re) => acts.find((a) => a.order === '-' && re.test(a.param));
  let row;
  if (forcedFatal || s.curds >= 0.65) row = acts.find((a) => a.outcome === 'Fatal');
  else if (s.curds >= 0.3) row = pick(/grainy/i);
  else if (s.thicken < 0.45) row = pick(/runny/i);
  if (row) {
    const res = engine.perform(row.id);
    if (res.gameOver) { setFeedback(res.feedback, 'Fatal'); return gameOver(); }
    // A non-fatal plating mistake still finishes the sauce.
    engine.required().forEach((a) => engine.done.add(a.id));
    engine.ready = true;
    setFeedback(res.feedback, res.outcome);
  } else {
    const ok = acts.find((a) => a.order === '3');
    engine.required().forEach((a) => { if (a.id !== ok.id) engine.done.add(a.id); });
    const res = engine.perform(ok.id);
    setFeedback(res.feedback || 'Silky!', 'Perfect');
  }
  s.heat = 0;
  refresh();
}

function refresh() { renderLeft(); renderRight(); updateTop(); renderAction(); }

function updateTop() {
  $('#score').textContent = engine.score;
  const n = engine.sub ? engine.stepIndex() : 0;
  $('#progress').innerHTML = engine.steps.map((_, i) => `<i class="${i + 1 < n ? 'done' : i + 1 === n ? 'now' : ''}"></i>`).join('');
}

// ---------- substep lifecycle ----------
function enter(id) {
  const sub = engine.enter(id);
  ui = { mode: 'items', source: null, pending: null, selected: new Set(), feedback: null, hint: null, locked: false, optState: {} };
  $('#fb-pop').hidden = true;
  popKey = '';
  ENTER[id]?.();
  setView(CAMERA_OVERRIDE[id] || sub.camera);
  refresh();
  const tip = engine.tip();
  if (tip) showTip(tip);
}

function next() {
  const sub = engine.sub;
  if (sub.next === 'END') return finish();
  enter(sub.next);
}

function showTip(tip) {
  $('#tip-title').textContent = tip.title;
  $('#tip-text').textContent = tip.text;
  $('#tip-ok').textContent = tip.button || 'Got it';
  $('#tip').hidden = false;
  $('#tip-ok').focus();
}
$('#tip-ok').addEventListener('click', () => { $('#tip').hidden = true; });

async function gameOver() {
  live = false;
  ui.locked = true;
  refresh();
  if (engine.ended === 'FATAL-SCRAMBLED' && !s.eggsIn) {
    if (!s.pastaIn) Sim.addPasta(s);
    Sim.addEggs(s);
    setView('Peek in the pan');
  }
  if (engine.ended === 'FATAL-SCRAMBLED') s.curds = 1;
  await sleep(1800);
  finish();
}

function finish() {
  const end = engine.ending();
  $('#end-eyebrow').textContent = end.fatal ? 'Dish ruined' : 'Table 6 has been served';
  $('#end-title').textContent = end.title;
  $('#end-score').textContent = end.fatal ? '' : `Score ${engine.score} · ${engine.mistakes} mistake${engine.mistakes === 1 ? '' : 's'} caught along the way`;
  $('#end-reaction').textContent = end.reaction;
  $('#end-nonna').textContent = end.nonna;
  $('#end-notes').innerHTML = engine.notes.length
    ? engine.notes.map((n) => `<li><span class="chip ${esc(n.outcome)}">${esc(n.outcome)}</span><div><b>${esc(n.title)}</b><p>${esc(n.feedback)}</p></div></li>`).join('')
    : '<li><div><b>Nothing to fix.</b><p>Every step landed. That’s a Roman carbonara, tofu and all.</p></div></li>';
  $('#end').hidden = false;
}

$('#again').addEventListener('click', () => {
  $('#end').hidden = true;
  freshState();
  engine.reset();
  food.reset();
  live = false;
  run = null;
  showOrder();
});

// ---------- opening: title + learning objectives, then Saumya orders in the restaurant ----------
let dining = true;                  // opening screens over the restaurant still (assets/restaurant.jpg)
function showOrder() {
  const o = FLOW.order;
  dining = true;
  document.body.classList.add('dining');
  setView('Overview');
  $('#intro-goals').innerHTML = Object.entries(o).filter(([k]) => /^Goal/.test(k)).map(([, v]) => `<li>${esc(v)}</li>`).join('');
  // Saumya's three lines from the Order tab, as one paragraph.
  const said = ['Customer line 1', 'Customer line 2', 'Customer line 3']
    .map((k) => (o[k] || '').trim().replace(/^["“]|["”]$/g, '')).filter(Boolean).join(' ');
  $('#ana-line').textContent = `“${said}”`;
  $('#start').textContent = o['Intro button'] || 'Start cooking';
  $('#order').hidden = true;
  $('#intro').hidden = false;
  $('#hud').hidden = true;
  $('#intro-next').focus();
}
$('#intro-next').addEventListener('click', () => {
  if (reviewing) return resumeKitchen();
  $('#intro').hidden = true;
  $('#order').hidden = false;
  $('#start').focus();
});
$('#order-back').addEventListener('click', () => {
  $('#order').hidden = true;
  $('#intro').hidden = false;
  $('#intro-next').focus();
});
$('#start').addEventListener('click', () => {
  if (reviewing) return resumeKitchen();
  $('#order').hidden = true;
  dining = false;
  document.body.classList.remove('dining');
  $('#hud').hidden = false;
  engine.start();
  enter(engine.sub.id);
});

// Came from the kitchen menu: close the screen and pick up exactly where you left off.
function resumeKitchen() {
  reviewing = false;
  $('#intro').hidden = $('#order').hidden = true;
  dining = false;
  document.body.classList.remove('dining');
  $('#hud').hidden = false;
  $('#start').textContent = FLOW.order['Intro button'] || 'Start cooking';
  $('#intro-next').textContent = 'Next';
  $('#order-back').hidden = false;
}

// ---------- kitchen menu: revisit the introduction or the order without losing progress ----------
let reviewing = false;
function revisit(screen) {
  closeMenu();
  reviewing = true;
  dining = true;
  document.body.classList.add('dining');
  $('#hud').hidden = true;
  $('#start').textContent = 'Back to the kitchen';
  $('#intro-next').textContent = 'Back to the kitchen';   // each screen returns straight to the kitchen
  $('#order-back').hidden = true;
  $('#intro').hidden = screen !== 'intro';
  $('#order').hidden = screen !== 'order';
  (screen === 'intro' ? $('#intro-next') : $('#start')).focus();
}
function closeMenu() {
  $('#menu').hidden = true;
  $('#menu-btn').setAttribute('aria-expanded', 'false');
}
$('#menu-btn').addEventListener('click', (e) => {
  e.stopPropagation();
  const open = $('#menu').hidden;
  $('#menu').hidden = !open;
  $('#menu-btn').setAttribute('aria-expanded', String(open));
  if (open) $('#menu button').focus();
});
$('#menu').addEventListener('click', (e) => {
  const item = e.target.closest('[data-goto]');
  if (item) revisit(item.dataset.goto);
});
document.addEventListener('click', (e) => { if (!e.target.closest('#menu, #menu-btn')) closeMenu(); });

// ---------- internal: jump straight to any substep ----------
// Everything before the chosen substep is played through with the right answers, so the
// kitchen (tofu, pot, bowl, sauce…) is in the state a learner would have reached.
function openJump() {
  closeMenu();
  let html = '', step = '';
  FLOW.substeps.forEach((sub) => {
    if (sub.stepTitle !== step) { step = sub.stepTitle; html += `<h3>Step ${sub.step} · ${esc(step)}</h3>`; }
    html += `<button data-jump-to="${esc(sub.id)}"><b>${esc(sub.id.slice(1))}</b>${esc(sub.title)}</button>`;
  });
  $('#jump-list').innerHTML = html;
  $('#jump').hidden = false;
}
async function jumpTo(target) {
  $('#jump').hidden = true;
  run = null; live = false; reviewing = false; dining = false;
  document.body.classList.remove('dining');
  $('#intro').hidden = $('#order').hidden = $('#tip').hidden = $('#fb-pop').hidden = true;
  $('#hud').hidden = false;
  resumeKitchen();
  freshState();
  engine.start();
  jumping = true;
  try {
    for (let guard = 0; engine.sub.id !== target && guard < 60; guard++) {
      const sub = engine.sub;
      ENTER[sub.id]?.();
      if (sub.type === 'MCQ - Single select') {
        const opts = engine.options();
        const o = opts.find((x) => x.correctness === 'Correct') || opts.find((x) => x.correctness !== 'Incorrect');
        engine.choose(o.id);
        applyOptionEffect(o);
      } else if (sub.type === 'MCQ - Multi select') {
        const pick = engine.options().filter((o) => o.correctness !== 'Incorrect');
        engine.check(new Set(pick.map((o) => o.id)));
        pick.forEach((o) => { if (o.item) w.committed.add(o.item); });
      } else if (sub.id === LIVE_SUB) {
        // The live sauce: pour the eggs, then land it silky and plated.
        const pour = engine.required()[0];
        engine.perform(pour.id);
        await VISUALS[pour.id]?.();
        live = false;
        Object.assign(s, { foodTemp: 65, thicken: 0.7, curds: 0, heat: 0 });
        engine.required().forEach((a) => engine.done.add(a.id));
        engine.ready = true;
      } else {
        for (const a of engine.required()) {
          engine.perform(a.id);
          await VISUALS[a.id]?.();
        }
      }
      if (sub.next === 'END') break;
      engine.enter(sub.next);
    }
  } finally {
    jumping = false;
  }
  enter(engine.sub.id);
}
$('#menu').addEventListener('click', (e) => { if (e.target.closest('[data-jump]')) openJump(); });
$('#jump-list').addEventListener('click', (e) => { const b = e.target.closest('[data-jump-to]'); if (b) jumpTo(b.dataset.jumpTo); });
$('#jump-close').addEventListener('click', () => { $('#jump').hidden = true; });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeMenu(); });

// ---------- loop ----------
$('#loading').hidden = true;
showOrder();
const clock = new THREE.Clock();
let liveUiT = 0;
renderer.setAnimationLoop(() => {
  const dt = Math.min(clock.getDelta(), 0.1), t = clock.elapsedTime;
  if (dining) return;                // the opening shows a still image of the restaurant

  if (run) {
    const simDt = Math.min(dt * run.speed, run.remaining);
    for (let left2 = simDt; left2 > 0; left2 -= 0.5) Sim.stepModel(s, Math.min(0.5, left2));
    run.remaining -= simDt;
    renderTimer();
    if (run.remaining <= 0) { const r = run; run = null; setTimeout(() => { if (!run) $('#ff').hidden = true; }, 600); r.resolve(); }
  } else if (live) {
    for (let left2 = dt * 3; left2 > 0; left2 -= 0.5) Sim.stepModel(s, Math.min(0.5, left2));
    if (s.curds >= 0.65) plateSauce(true);
    liveUiT -= dt;
    if (liveUiT <= 0) {
      liveUiT = 0.25;
      const pct = Math.min(100, Math.max(0, ((s.foodTemp - 40) / 45) * 100));
      const fill = $('#thermo-fill');
      if (fill) {
        fill.style.width = `${pct}%`;
        fill.dataset.zone = s.foodTemp >= Sim.YOLK_SCRAMBLES ? 'hot' : s.foodTemp >= Sim.YOLK_THICKENS - 2 ? 'good' : 'cool';
        $('#thermo-val').textContent = `${Math.round(s.foodTemp)}°C`;
        $('#sauce-state').textContent = Sim.sauceState(s);
        $('#live-line').textContent = liveLine();
      }
    }
  } else if (engine.sub) {
    Sim.stepModel(s, dt);
  }
  w.boil = w.backHeat > 0 && w.potFilled && w.potOnHob ? Math.min(1, w.boil + dt * 0.02) : Math.max(0, w.boil - dt * 0.1);

  // Picks only reach the counter once the list passes the check, all at once.
  w.onCounter = new Set(w.committed);
  if (engine.ready && engine.sub?.type === 'MCQ - Multi select') {
    engine.options().forEach((o) => { if (ui.selected.has(o.id) && o.item) w.committed.add(o.item); });
  }
  if (w.tofuStage === 'none' && w.onCounter.has('I-TOFU')) w.tofuStage = 'pack';
  if (w.tofuStage === 'pack' && !w.onCounter.has('I-TOFU')) w.tofuStage = 'none';

  if (knob) knob.rotation.y = -s.heat * 0.85;
  food.update(s, dt, t, w);
  props.update(w, dt, t);

  // Pull the camera back when the side panels leave only a narrow strip of kitchen visible.
  const target = VIEWS[view];
  const W = canvas.clientWidth, H = canvas.clientHeight;
  // The panel column sits on the left (bottom on phones): centre the kitchen in the space
  // that's left, and pull back when that space is narrow.
  let pull = 1, shiftX = 0, shiftY = 0;
  if (!$('#hud').hidden) {
    const side = $('#side');
    if (W > 820) {
      shiftX = (side.offsetWidth + 16) / 2;
      pull = Math.min(1.8, Math.max(1, (W * 0.62) / Math.max(W - side.offsetWidth - 48, 1)));
    } else {
      shiftY = (side.offsetHeight + 54) / 2;
      pull = Math.min(1.8, Math.max(1, (H * 0.6) / Math.max(H - side.offsetHeight - 110, 1)));
    }
  }
  if (shiftX !== lastShift.x || shiftY !== lastShift.y || W !== lastShift.w || H !== lastShift.h) {
    camera.setViewOffset(W, H, -shiftX, shiftY, W, H);
    Object.assign(lastShift, { x: shiftX, y: shiftY, w: W, h: H });
  }
  goal.copy(target.pos).sub(target.look).multiplyScalar(pull).add(target.look);
  camPos.lerp(goal, 1 - Math.exp(-dt * 3));
  camLook.lerp(target.look, 1 - Math.exp(-dt * 3));
  camera.position.copy(camPos);
  camera.lookAt(camLook);
  composer.render(dt);
  placePins();
});
