import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Food } from './food.js';
import { Props, SPOTS, SINK_HOLE, slab } from './props.js';
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
renderer.shadowMap.type = THREE.PCFShadowMap;      // with shadow.radius: soft, wide penumbrae

const scene = new THREE.Scene();
const ENV_INTENSITY = 0.9;
scene.background = new THREE.Color('#1b1815');
const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 20);
const sun = new THREE.DirectionalLight(new THREE.Color('#fff4e6'), 2.4);
sun.position.set(-0.9, 1.1, 0.4);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -1.3, right: 1.1, top: 0.8, bottom: -0.8, near: 0.2, far: 4 });
sun.shadow.bias = -0.0004;
sun.shadow.normalBias = 0.01;
sun.shadow.radius = 7;
sun.shadow.blurSamples = 16;
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
  'Stove': V([0.07, 0.55, 0.58], [0.04, 0.05, 0.05]),     // front knob and the tongs in frame, knob clear of the Continue button at 1280 px
  'Pot': V([-0.5, 0.82, 0.98], [-0.52, 0.04, 0.1]),       // hob, pot, its lid and the tongs
  'Stove wide': V([-0.3, 0.62, 0.62], [-0.3, 0.05, -0.04]),
  'Peek in the pan': V([0.06, 0.34, 0.19], [0, 0.06, 0.005]),
  'Sink': V([-0.84, 0.55, 0.52], [-0.84, 0.04, -0.06]),
  'Serving': V([-0.05, 0.55, 0.95], [-0.05, 0.04, 0.4]),   // resting plate on the left, both bowls
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
// The props (blender/export_props.py) carry their textures inside the file. If they fail to
// load, the kitchen keeps its simple stand-in shapes.
async function loadProps() {
  try {
    const res = await fetch('assets/props.glb.b64.txt');
    if (!res.ok) return null;
    const bytes = Uint8Array.from(atob((await res.text()).trim()), (c) => c.charCodeAt(0));
    return await new GLTFLoader().parseAsync(bytes.buffer, 'assets/');
  } catch (err) {
    console.warn('props failed to load', err);
    return null;
  }
}
async function loadFlow() {
  const res = await fetch('flow.json');
  if (!res.ok) throw new Error(`flow.json: HTTP ${res.status}`);
  return res.json();
}
const [gltf, FLOW, propsGltf] = await Promise.all([loadKitchen(), loadFlow(), loadProps()]).catch((err) => {
  $('#load-msg').textContent = `The kitchen couldn’t load. Refresh to try again. (${err?.message || err})`;
  throw err;
});

// Light the kitchen with the same studio HDRI the Blender renders (restaurant, item cards) use,
// so reflections and fill light match them. Shipped base64 like the model; RoomEnvironment
// is the fallback if it can't load.
const pmrem = new THREE.PMREMGenerator(renderer);
try {
  const res = await fetch('assets/env.hdr.b64.txt');
  const bin = Uint8Array.from(atob((await res.text()).trim()), (c) => c.charCodeAt(0));
  const d = new RGBELoader().parse(bin.buffer);
  const hdr = new THREE.DataTexture(d.data, d.width, d.height, THREE.RGBAFormat, d.type);
  Object.assign(hdr, { flipY: true, mapping: THREE.EquirectangularReflectionMapping, colorSpace: THREE.LinearSRGBColorSpace,
    minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false, needsUpdate: true });
  scene.environment = pmrem.fromEquirectangular(hdr).texture;
  hdr.dispose();
  scene.environmentIntensity = ENV_INTENSITY;
} catch (err) {
  console.warn('HDRI failed, using RoomEnvironment', err);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.03).texture;
  scene.environmentIntensity = 0.7;
}

// Wood grain, glue seams and tile grout relief, baked from the Blender bump (blender/bake_normals.py).
const NORMALS = { ButcherBlock: ['assets/Counter_normal.jpg', 1.0], SubwayTile: ['assets/Backsplash_normal.jpg', 1.4] };
const texLoader = new THREE.TextureLoader();
gltf.scene.traverse((o) => {
  if (!o.isMesh) return;
  o.castShadow = o.receiveShadow = true;
  const nm = NORMALS[o.material?.name];
  if (nm && !o.material.normalMap) {
    const t = texLoader.load(nm[0]);
    t.flipY = false;                         // glTF texture convention, same as the colour map
    t.anisotropy = renderer.capabilities.getMaxAnisotropy();
    o.material.normalMap = t;
    o.material.normalScale.setScalar(nm[1]);
    if (o.material.map) o.material.map.anisotropy = t.anisotropy;
    o.material.needsUpdate = true;
  }
  if (o.material?.name === 'BrushedSteel') o.material.roughness = 0.42;   // brushed, not mirror: blurs the room
  if (o.material?.name === 'CastIron') {
    o.material.clearcoat = 0.25;
    o.material.color.set('#2a2826');
  }
});
scene.add(gltf.scene);
// Cut the sink's opening into the counter: rebuild it as a slab with a hole, keeping its UVs
// (fitted from the original plane) so the wood texture and normal map land where they did.
{
  const counter = gltf.scene.getObjectByName('Counter');
  if (counter?.isMesh) {
    counter.updateWorldMatrix(true, false);
    const pos = counter.geometry.attributes.position, uv = counter.geometry.attributes.uv;
    const pts = Array.from({ length: pos.count }, (_, i) => ({
      p: new THREE.Vector3().fromBufferAttribute(pos, i).applyMatrix4(counter.matrixWorld), u: uv.getX(i), v: uv.getY(i) }));
    const xs = pts.map((q) => q.p.x), zs = pts.map((q) => q.p.z);
    const [x0, x1, z0, z1] = [Math.min(...xs), Math.max(...xs), Math.min(...zs), Math.max(...zs)];
    const a = pts.find((q) => q.p.x === x0 && q.p.z === z0), b = pts.find((q) => q.p.x === x1 && q.p.z === z1);
    const uvOf = (x, z) => [a.u + (b.u - a.u) * (x - x0) / (x1 - x0), a.v + (b.v - a.v) * (z - z0) / (z1 - z0)];
    const g = slab(x0, x1, z0, z1, SINK_HOLE, uvOf).translate(0, pts[0].p.y, 0);
    counter.geometry.dispose();
    counter.geometry = g;
    counter.position.set(0, 0, 0); counter.quaternion.identity(); counter.scale.set(1, 1, 1);   // geometry is in world space (its parent is the untransformed glTF root)
  }
}
// Rearrange the Blender set for the flow: egg bowl on the prep side, eggs by the board.
const bowlObj = gltf.scene.getObjectByName('Bowl');
if (bowlObj) bowlObj.position.set(SPOTS.eggBowl.x, bowlObj.position.y, SPOTS.eggBowl.z);
['Sphere', 'Sphere001', 'Sphere002'].forEach((n) => { const o = gltf.scene.getObjectByName(n); if (o) o.visible = false; });
// Five eggs: the set's two plus three copies.
const named = (...names) => names.map((n) => gltf.scene.getObjectByName(n)).filter(Boolean);
const eggObjs = named('Egg0', 'Egg1');
for (let i = 2; eggObjs[0] && i < 5; i++) { const e = eggObjs[0].clone(); e.name = 'Egg' + i; e.rotation.y += i * 0.9; eggObjs[0].parent.add(e); eggObjs.push(e); }
eggObjs.forEach((o, i) => o.position.set(SPOTS.eggs[i].x, o.position.y, SPOTS.eggs[i].z));
const knob = gltf.scene.getObjectByName('HeatKnob');
const grip = gltf.scene.getObjectByName('HeatKnobGrip');
if (knob && grip) knob.attach(grip);

const food = new Food(scene, { bundles: small ? 60 : 95 });
const props = new Props(scene, { pastaMaterial: food.pastaMat, tofuMaterial: food.tofuMaterial });
if (propsGltf) props.useModels(propsGltf.scene);
['Bowl', 'Cooktop'].forEach((n) => { const o = gltf.scene.getObjectByName(n); if (o) props.addContact(o, { opacity: 0.5 }); });
eggObjs.forEach((o) => props.addContact(o, { opacity: 0.5 }));
// Kitchen pieces from the Blender set that also only appear once brought to the counter.
props.items['T-SKILLET'] = named('Skillet', 'Handle', 'HelperHandle');
props.items['I-EGGS'] = eggObjs;
props.eggs = eggObjs;
props.items['T-BOWL'].push(...named('Bowl'));
props.bowlModel = bowlObj;
resize();

// ---------- state ----------
const engine = new FlowEngine(FLOW);
let s, w;
function freshState() {
  s = Sim.newState();
  s.tofuInPan = false;
  w = {
    tofuStage: 'none', towelBottom: false, towelTop: false, weight: false, weightLift: 0, pressDone: false, cutLevel: 0, cutAnim: null,
    potInSink: false, potOnHob: false, potFilled: false, tapOn: false, waterLevel: 0, lidOn: false, backHeat: 0, boil: 0, pastaInPot: false,
    oil: false, tossT: 0, flips: 0, season: 0, bowlStage: 'empty', wholeEggs: 0, yolks: 0, whitesN: 0, eggsUsed: 0, cheeseIn: false, mugFull: false,
    plated: 0, tongsPasta: false, peppered: false, pepperIn: false, served: false, bellT: 0,
    committed: new Set(),   // items brought to the counter in step 1 (flow item IDs)
    onCounter: new Set(),   // committed + whatever is ticked right now
  };
}
freshState();

let run = null;           // fast-forward: { total, remaining, dur (real seconds), t0, resolve }
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
    // Never more than 4 real seconds, however long the wait in the recipe.
    run = { total: seconds, remaining: seconds, dur: Math.min(4, seconds / speed), t0: performance.now(), resolve };
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
// The knife makes one set of cuts (props poses it from w.cutAnim), then the cut lines stay.
const cut = (level, ms) => async () => {
  if (!jumping) {
    const t0 = performance.now();
    w.cutAnim = { level, k: 0 };
    while (w.cutAnim.k < 1) {
      await sleep(16);
      w.cutAnim.k = Math.min(1, (performance.now() - t0) / ms);
    }
  }
  w.cutAnim = null;
  w.cutLevel = level;
};
const VISUALS = {
  'A-2.1-01': async () => { w.tofuStage = 'draining'; await sleep(jumping ? 0 : 1600); w.tofuStage = 'block'; },
  'A-2.2-01': () => { w.towelBottom = true; },          // slides in under the tofu
  'A-2.2-02': () => { w.towelTop = true; },
  'A-2.2-03': () => { w.weight = true; w.tofuStage = 'pressing'; },
  'A-2.4-01': cut(1, 1200),                                                          // slabs
  'A-2.4-02': cut(2, 1800),                                                          // strips
  'A-2.4-03': async () => { await cut(3, 2200)(); w.tofuStage = 'cubes'; },          // cubes
  'A-3.1-01': () => { w.potInSink = true; },
  'A-3.1-02': async () => { w.tapOn = true; await sleep(jumping ? 0 : 1800); w.tapOn = false; w.potFilled = true; },
  'A-3.2-01': () => { w.potOnHob = true; },
  'A-3.2-04': () => { w.backHeat = 3; },
  'A-3.2-05': () => { w.lidOn = true; },
  'A-4.2-02': () => { s.heat = 2; },
  'A-4.2-04': () => { w.oil = true; },
  'A-4.2-05': () => ff(60),
  'A-4.3-01': () => { w.tofuStage = 'pan'; s.tofuInPan = true; },
  'A-4.3-03': () => ff(180),
  'A-4.3-05': () => { w.tossT = 1; w.flips += 1; },
  'A-4.3-06': () => { w.tossT = 1; },
  'A-4.3-07': () => ff(180),
  'A-4.3-08': () => { w.season = 0.5; },
  'A-4.3-09': () => { w.season = 1; return ff(30); },
  'A-4.4-01': () => { s.heat = 0; },
  // The slotted spoon carries the tofu (TOOL_PATHS); on a step jump it just lands on the plate.
  'A-4.4-02': () => { if (jumping) w.tofuStage = 'plate'; s.tofuInPan = false; s.guancialeDone = true; },
  'A-4.4-03': async () => { w.oil = false; await sleep(700); w.oil = true; },
  // Eggs are cracked one by one (TOOL_PATHS crackEggs); on a step jump they're simply in.
  'A-5.2-01': () => { if (jumping) Object.assign(w, { bowlStage: 'eggs', wholeEggs: 2, eggsUsed: 2 }); },
  'A-5.2-02': () => { if (jumping) Object.assign(w, { bowlStage: 'eggs', yolks: 3, whitesN: 3, eggsUsed: 5 }); },
  'A-5.4-01': () => { if (jumping) w.cheeseIn = true; },   // otherwise once the grating is done (grate)
  'A-5.4-02': () => { if (jumping) w.pepperIn = true; },   // otherwise once the grains land (crackPepper)
  'A-5.4-03': () => { w.bowlStage = 'paste'; },
  // Salt: a shower of coarse grains falls into the boiling water.
  'A-6.2-01': () => {
    if (jumping) return;
    const r = () => Math.random() - 0.5;
    return Promise.all(Array.from({ length: 24 }, (_, n) => props.drop({
      from: [POT_C[0] + r() * 0.03, 0.34, POT_C[2] + r() * 0.03], to: [POT_C[0] + r() * 0.1, 0.15, POT_C[2] + r() * 0.1],
      shred: true, color: '#f7f7f2', delay: n * 0.03 })));
  },
  'A-6.2-02': () => { w.pastaInPot = true; },
  'A-7.1-01': () => { w.mugFull = true; s.savedWater = true; },
  'A-7.1-02': () => { s.heat = 1; },
  // The tongs grip the pasta in the pot and carry it to the pan (TOOL_PATHS); on a step jump it's just there.
  'A-7.1-03': () => { if (jumping) { w.pastaInPot = false; Sim.addPasta(s); } },
  'A-7.1-04': () => { w.tossT = 0.6; },
  'A-7.1-05': () => { w.waterLevel = 0.01; },
  'A-7.2-03': () => { w.bowlStage = 'tempered'; },
  'A-7.4-01': () => { w.bowlStage = 'empty'; Sim.addEggs(s); live = true; },
  'A-7.4-04': () => { s.heat = s.heat > 0 ? 0 : 1; },
  'A-7.4-05': () => { Sim.splashWater(s); },
  'A-8.2-01': () => { if (jumping) w.tofuStage = 'pile'; },   // otherwise the slotted spoon carries it (TOOL_PATHS)
  'A-8.2-02': () => { s.heat = 0; if (jumping) Object.assign(w, { plated: 2, served: true, tofuStage: 'served' }); },
  'A-8.2-03': () => { if (jumping) w.peppered = true; },
  'A-8.3-01': () => { w.bellT = 1.2; },
};
// Tools travel to where they're used, do their job and go home (props.useTool). The effect in
// VISUALS plays once the tool arrives.
const B = SPOTS.eggBowl;
const PAN_C = [0, 0.075, -0.03], POT_C = [-0.56, 0.17, -0.08], BOWL_L = [-0.14, 0.09, 0.5], BOWL_R = [0.14, 0.09, 0.5];
const tool = (id, ...stops) => () => props.useTool(id, stops);
// Eggs go one at a time to the vessel, tap twice on the rim and break open: the shell is gone and the
// contents fall in. Whole eggs drop into the bowl; for separated ones the white falls into the cup and
// the yolk is passed across to the bowl.
const CUP = SPOTS.whitesCup;
// Grating: the box grater is held over each spot while the pecorino is rubbed up and down its face,
// and strands of cheese fall in. spots are where the strands land.
const grate = (spots, { keep = false, onEnd } = {}) => () => {
  const r = () => Math.random() - 0.5;
  const g = props.useTool('T-GRATER', spots.map(([x, y, z]) => ({ at: [x, y + 0.11, z], dur: 1.5 })));
  const c = props.useTool('I-PECORINO', spots.map(([x, y, z], k) => ({
    at: [x + 0.052, y + 0.15, z], work: 'grate', dur: 1.4,   // pressed against the grater's face, mid-height
    before: () => {
      for (let n = 0; n < 18; n++) {
        props.drop({ from: [x + r() * 0.04, y + 0.11, z + r() * 0.03], to: [x + r() * 0.05, y, z + r() * 0.05],
          shred: true, keep, delay: 0.1 + n * 0.07 });
      }
    },
    after: k === spots.length - 1 ? onEnd : undefined,
  })));
  return { arrived: c.arrived, done: Promise.all([g.done, c.done]) };
};
// Cracking pepper: the mill twists over each spot and dark flecks fall from it; when the last spot is
// done the pepper shows on the food (onEnd).
const crackPepper = (spots, onEnd) => () => {
  const r = () => Math.random() - 0.5;
  return props.useTool('I-PEPPER', spots.map(([x, y, z], k) => ({
    at: [x, y + 0.14, z], work: 'twist', dur: 1.2,
    before: () => {
      for (let n = 0; n < 22; n++) {
        props.drop({ from: [x + r() * 0.01, y + 0.1, z + r() * 0.01], to: [x + r() * 0.06, y, z + r() * 0.06],
          shred: true, color: '#16100b', delay: 0.15 + n * 0.04 });
      }
    },
    after: k === spots.length - 1 ? onEnd : undefined,
  })));
};
const crackEggs = (first, n, separate) => () => {
  let arrivedRes;
  const arrived = new Promise((r) => { arrivedRes = r; });
  const done = (async () => {
    for (let i = first; i < first + n; i++) {
      const at = separate ? [CUP.x, 0.12, CUP.z] : [B.x + 0.03, 0.12, B.z];
      const landed = [];
      const spot = (j) => [B.x + Math.cos(j * 1.26) * 0.022, 0.026, B.z + Math.sin(j * 1.26) * 0.022];
      const open = () => {
        w.eggsUsed = Math.max(w.eggsUsed, i + 1);
        if (!separate) {
          landed.push(props.drop({ from: at, to: spot(w.wholeEggs) }).then(() => { w.bowlStage = 'eggs'; w.wholeEggs += 1; }));
        } else {
          landed.push(props.drop({ from: at, to: [CUP.x, 0.016, CUP.z], yolk: false }).then(() => { w.whitesN += 1; }));
          landed.push(props.drop({ from: at, to: spot(w.wholeEggs + w.yolks), white: false, arc: true, delay: 0.3 })
            .then(() => { w.bowlStage = 'eggs'; w.yolks += 1; }));
        }
      };
      const m = props.useTool('EGG' + i, [{ at, work: 'crack', dur: 0.6, hold: true, after: open }]);
      if (i === first) m.arrived.then(arrivedRes);
      await m.done;
      await Promise.all(landed);
    }
  })();
  return { arrived, done };
};
const TOOL_PATHS = {
  'A-4.3-05': tool('T-TONGS', { at: PAN_C, work: 'dip' }),
  'A-4.3-06': tool('T-TONGS', { at: PAN_C, work: 'stir' }),
  // Scoop: the tofu rides in the spoon; tip: it slides onto the resting plate.
  'A-4.4-02': tool('T-SLOTTED',
    { at: [0, 0.075, -0.03], work: 'dip', after: () => { w.spoonAt = props.items['T-SLOTTED'][0].position; w.tofuStage = 'spoon'; } },
    { at: [SPOTS.plate.x, 0.06, SPOTS.plate.z], work: 'tip', toward: [SPOTS.plate.x - 0.1, 0, SPOTS.plate.z], before: () => { w.tofuStage = 'plate'; } }),
  'A-5.2-01': crackEggs(0, 2, false),
  'A-5.2-02': crackEggs(2, 3, true),
  'A-5.4-01': grate([[B.x, 0.026, B.z]], { onEnd: () => { w.cheeseIn = true; } }),
  'A-5.4-02': crackPepper([[B.x, 0.03, B.z]], () => { w.pepperIn = true; }),
  'A-5.4-03': tool('WHISK', { at: [B.x, 0.02, B.z], work: 'stir', upright: true, dur: 1.4 }),
  'A-6.2-03': tool('T-TONGS', { at: POT_C, work: 'stir', dur: 1.2 }),
  'A-7.1-01': tool('T-MUG', { at: [POT_C[0], 0.12, POT_C[2]], work: 'dip' }),
  // Grip a bunch of pasta in the pot (it hangs from the tips), carry it over and let it go in the pan.
  'A-7.1-03': tool('T-TONGS',
    { at: POT_C, work: 'dip', after: () => { w.pastaInPot = false; w.tongsPasta = true; } },
    { at: PAN_C, work: 'dip', before: () => { w.tongsPasta = false; Sim.addPasta(s); } }),
  'A-7.1-04': tool('T-TONGS', { at: PAN_C, work: 'stir', dur: 1.2 }),
  'A-7.2-01': tool('T-MUG', { at: [B.x + 0.08, 0.1, B.z + 0.03], work: 'pour', toward: [B.x, 0, B.z], dur: 1.2 }),
  'A-7.2-02': tool('WHISK', { at: [B.x, 0.02, B.z], work: 'stir', upright: true, dur: 1.4 }),
  'A-7.2-04': tool('T-MUG', { at: [B.x + 0.08, 0.1, B.z + 0.03], work: 'pour', toward: [B.x, 0, B.z], dur: 0.6 }),
  'A-7.4-01': tool('T-BOWL', { at: [0.17, 0.12, 0.03], work: 'pour', toward: PAN_C, dur: 1.3 }),
  'A-7.4-05': tool('T-MUG', { at: [0.14, 0.13, 0.04], work: 'pour', toward: PAN_C, dur: 0.8 }),
  // Same as 4.4 in reverse: the slotted spoon scoops the tofu off the resting plate and tips it into the pasta.
  'A-8.2-01': tool('T-SLOTTED',
    { at: [SPOTS.plate.x, 0.06, SPOTS.plate.z], work: 'dip', after: () => { w.spoonAt = props.items['T-SLOTTED'][0].position; w.tofuStage = 'spoon'; } },
    { at: [PAN_C[0], 0.11, PAN_C[2]], work: 'tip', toward: [PAN_C[0] - 0.1, 0, PAN_C[2]], before: () => { w.tofuStage = 'pile'; } }),
  // Twice: grip pasta in the pan, carry it to a bowl and twirl it into a nest there.
  'A-8.2-02': tool('T-TONGS',
    { at: PAN_C, work: 'dip', after: () => { w.tongsPasta = true; } },
    { at: BOWL_L, work: 'twist', before: () => { w.tongsPasta = false; w.plated = 1; } },
    { at: PAN_C, work: 'dip', after: () => { w.tongsPasta = true; } },
    { at: BOWL_R, work: 'twist', before: () => { w.tongsPasta = false; w.plated = 2; Object.assign(w, { served: true, tofuStage: 'served' }); } }),
  'A-8.2-03': crackPepper([[BOWL_L[0], 0.06, BOWL_L[2]], [BOWL_R[0], 0.06, BOWL_R[2]]], () => { w.peppered = true; }),
  'A-8.2-04': grate([[BOWL_L[0], 0.05, BOWL_L[2]], [BOWL_R[0], 0.05, BOWL_R[2]]], { keep: true }),
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
  'S4.4': () => w.committed.add('PLATE'),
  'S8.1': () => w.committed.add('SERVING'),
  'S2.4': () => { w.pressDone = true; w.tofuStage = 'pressed'; },
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

// One task at a time. Merged tasks (storyboard) have one instruction for all their actions;
// older steps still list the next action on its own.
function taskList() {
  const sub = engine.sub;
  const req = engine.required();
  if (!req.some((a) => a.task)) {
    return `<div class="task-card" aria-live="polite">
      <span class="task-no">${esc(sub.id.slice(1))}</span><p class="task-now">${esc(sub.left)}</p>
    </div>`;
  }
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
    <h2>${esc(sub.stepTitle)}</h2>
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
// Chances left, tries before a hint, the hint itself: shown as smaller, quieter subtext under Nonna's words.
const SUBTEXT = /^(You have \d+ more chances?\.|One more wrong move|\d+ more tries|Hint:|Here’s the (right answer|full list))/;
// Nonna's avatar: a chef in a toque (drawn here so it matches in every popup).
const CHEF_SVG = `<svg viewBox="0 0 40 40" aria-hidden="true">
  <circle cx="20" cy="27" r="9.5" fill="#f2cba4"/>
  <path d="M11 17.5h18v3.2H11z" fill="#efe6d6"/>
  <circle cx="14" cy="12.5" r="4.6" fill="#fffaf0"/><circle cx="20" cy="9.6" r="5.4" fill="#fffaf0"/><circle cx="26" cy="12.5" r="4.6" fill="#fffaf0"/>
  <path d="M11.2 12.5h17.6v5.2H11.2z" fill="#fffaf0"/>
  <circle cx="16.6" cy="25.6" r="1.1" fill="#2a1b04"/><circle cx="23.4" cy="25.6" r="1.1" fill="#2a1b04"/>
  <path d="M15.4 29.6c1.6-1.3 3.2-1.3 4.6 0 1.4-1.3 3-1.3 4.6 0-1.4 1.6-3.2 1.7-4.6.6-1.4 1.1-3.2 1-4.6-.6z" fill="#7a5a3a"/>
  <path d="M10.5 40c1.2-3.6 4.8-5.4 9.5-5.4s8.3 1.8 9.5 5.4z" fill="#fffaf0"/>
</svg>`;
document.querySelectorAll('.chef-face').forEach((el) => { el.innerHTML = CHEF_SVG; });
function renderPop(fb) {
  const pop = $('#fb-pop');
  const sub = engine.sub;
  const ready = engine.ready;
  const lines = fb ? (Array.isArray(fb.text) ? fb.text : [fb.text]).filter(Boolean) : [];
  // A finished step with no line of its own still gets the correct-answer popup: "That's right!" heading.
  if (!lines.length && ready) {
    lines.push(sub.type === 'Procedure' ? 'All done here. Nicely worked.' : 'That’s it. On to the next one.');
    fb = { ...fb, outcome: 'Perfect', head: HEAD.right };
  }
  if (ui.hint) lines.push(`Hint: ${engine.item(ui.hint.source).name} → ${ui.hint.param}`);
  if (!lines.length || ui.locked) { pop.hidden = true; return; }
  const key = JSON.stringify([lines, fb?.outcome, fb?.head, ready]);
  if (key === popKey && !pop.hidden) return;          // unchanged: leave it (and its timer) alone
  popKey = key;
  pop.className = `fb-pop ${fb?.outcome || ''}`;
  pop.innerHTML = `
    <div class="chef-face" aria-hidden="true">${CHEF_SVG}</div>
    <div class="fb-bubble"><div class="fb-body">
      ${fb?.head ? `<p class="fb-head">${esc(fb.head)}</p>` : ''}
      ${lines.map((t) => (t.b ? `<p><b>${esc(t.b)}:</b><br>${esc(t.t)}</p>` : `<p${SUBTEXT.test(t) ? ' class="fb-sub"' : ''}>${esc(t)}</p>`)).join('')}
    </div></div>
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

// Options carry no type pills; only the ones you hold or tap repeatedly get a plain hint line.
function actHint() {
  return '';   // every option is a single click
}

// Verdict icons: drawn strokes rather than text glyphs, so they look the same on every system.
const ICON_X = '<svg class="vicon" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 3l6 6M9 3l-6 6"/></svg>';
const ICON_OK = '<svg class="vicon" viewBox="0 0 12 12" aria-hidden="true"><path d="M2.5 6.5l2.3 2.3L9.5 3.8"/></svg>';
const VERDICT = {
  right: `<span class="verdict ok">${ICON_OK}Correct</span>`,
  auto: `<span class="verdict auto">${ICON_OK}Autocorrected</span>`,   // filled in by the system after the last try
  wrong: `<span class="verdict bad">${ICON_X}Incorrect</span>`,
};

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
        // Lists: a wrong pick stays ticked so it can be unticked; confirmed picks are locked in.
        const locked = engine.ready || st === 'right' || st === 'auto' || (st === 'wrong' && !multi);
        return `<button class="card opt ${multi ? 'multi' : ''} ${tiles ? 'tile' : ''} ${st === 'auto' ? 'right' : st} ${sel ? 'selected' : ''}" data-opt="${esc(o.id)}" aria-pressed="${sel}"
          ${locked ? 'disabled' : ''}>
          ${tiles ? `<span class="tile-img">${img || '<span class="no-img" aria-hidden="true"></span>'}</span>` : ''}
          ${multi && !tiles ? `<span class="tick" aria-hidden="true">${sel ? '✓' : ''}</span>` : ''}
          <span class="card-label">${esc(o.label)}</span>${VERDICT[st] || ''}</button>`;
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
  } else if (ui.mode === 'multi') {
    const acts = engine.actions().filter((a) => a.source === ui.source && a.interaction === 'Click');
    const solo = soloMulti(sub);
    html = `${solo ? '' : '<button class="link" data-back>← All items</button>'}
      <span class="eyebrow">${solo ? 'Pick all that apply' : `${esc(engine.item(ui.source).name)}: pick all that apply`}</span><div class="cards">` +
      acts.map((a) => {
        const st = ui.optState?.[a.id] || '', sel = ui.selected.has(a.id);
        return `<button class="card opt multi ${st} ${sel ? 'selected' : ''}" data-pick="${esc(a.id)}" aria-pressed="${sel}" ${st ? 'disabled' : ''}>
          <span class="tick" aria-hidden="true">${sel || st === 'right' ? '✓' : ''}</span><span class="card-label">${esc(a.param)}</span>
          ${st === 'right' ? `<span class="verdict ok">${ICON_OK}Correct</span>` : st === 'wrong' ? `<span class="verdict bad">${ICON_X}Incorrect</span>` : ''}</button>`;
      }).join('') + '</div>';
  } else if (ui.mode === 'actions') {
    const acts = choices().filter((a) => a.source === ui.source);
    html = `<button class="link" data-back>← All items</button>
      <span class="eyebrow">${esc(engine.item(ui.source).name)}: what do you do?</span><div class="cards">` +
      acts.map((a) => `<button class="card act" data-act="${esc(a.id)}" data-kind="${esc(a.interaction)}" data-need="1">
        <span class="card-label">${esc(a.param)}</span>${actHint(a) ? `<span class="card-hint">${actHint(a)}</span>` : ''}<span class="fill" aria-hidden="true"></span></button>`).join('') +
      (acts.length ? '' : '<p class="muted">Nothing left to do with this.</p>') + '</div>';
  } else if (sub.type === 'Procedure' && !engine.ready) {
    // Things already in the kitchen are clicked there (pins); only the rest get cards.
    const sources = pickables().filter((id) => !onScreen(id) && !(PROMPTED[sub.id]?.includes(id) && !ui.dismissed?.has(id)));
    html = sources.length ? `<div class="cards grid">${sources.map((id) => itemCard(id)).join('')}</div>` : '';
  }
  right.innerHTML = html;
  right.hidden = !html;                     // nothing to pick here: no panel
  setHeld(ui.mode === 'target' && !ui.locked ? ui.pending[0].source : null);
  renderPins();
}

// While an item is picked up, the pointer becomes that item over the kitchen.
const held = $('#held');
function setHeld(id) {
  document.body.classList.toggle('holding', !!id);
  if (!id) { held.classList.add('off'); held.dataset.id = ''; return; }
  if (held.dataset.id !== id) {
    held.dataset.id = id;
    held.innerHTML = itemImg(id) || `<span class="held-name">${esc(engine.item(id).name)}</span>`;
  }
}
document.addEventListener('pointermove', (e) => {
  held.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
  const overKitchen = e.target === canvas || !!e.target.closest('#pins');
  held.classList.toggle('off', !document.body.classList.contains('holding') || !overKitchen);
});

// ---------- pins (clickable spots in the 3D kitchen) ----------
// Clickable in the kitchen: it has a pin spot and its model is showing (or, with no model
// to check, the sheet says it's used from the scene).
function onScreen(id) {
  if (!props.anchors[id]) return false;
  const shown = props.shown(id, w);
  return shown ?? (choices().some((a) => a.source === id && a.srcLoc === 'Scene') || engine.item(id).location === 'Scene');
}
let pinList = [];
function renderPins() {
  pinList = [];
  const sub = engine.sub;
  if (sub && sub.type === 'Procedure' && !engine.ready && !live && !ui.locked) {
    if (ui.mode === 'target') {
      const decoys = engine.sub.wrongDecoys?.[ui.pending[0].source] || [];   // wrong spots worth offering
      const targets = [...new Set([...engine.actions().map((a) => a.target), ...decoys].filter((t) => t && t !== ui.pending[0].source && props.anchors[t]))];
      targets.forEach((id) => pinList.push({ id, kind: 'target' }));
    } else if (ui.mode !== 'actions') {
      pickables().filter(onScreen).forEach((id) => pinList.push({ id, kind: 'source' }));
    }
  }
  pins.innerHTML = pinList.map((p) => `<button class="pin ${p.kind}" data-pin="${esc(p.id)}"><span>${esc(engine.item(p.id).name)}</span></button>`).join('');
}
const tmp = new THREE.Vector3();
// Screen furniture a hotspot must never sit under or be cut off by.
const PIN_OBSTACLES = ['#left', '#right', '#menu-btn', '#views', '#action-btn', '#fb-pop'];
function placePins() {
  const r = canvas.getBoundingClientRect();
  const M = 8;
  const blocks = PIN_OBSTACLES.map((q) => $(q)).filter((el) => el && !el.hidden && el.getClientRects().length)
    .map((el) => el.getBoundingClientRect()).filter((b) => b.width && b.height)
    .map((b) => ({ x0: b.left - r.left - M, y0: b.top - r.top - M, x1: b.right - r.left + M, y1: b.bottom - r.top + M }));
  pins.querySelectorAll('.pin').forEach((el) => {
    const a = props.anchors[el.dataset.pin];
    if (!a) return;
    tmp.copy(a).project(camera);
    const off = tmp.z > 1 || Math.abs(tmp.x) > 1.05 || Math.abs(tmp.y) > 1.05;
    el.hidden = off;
    if (off) return;
    // The ring sits on the spot: centred across the pin (label included), its middle 11px down.
    // Near an edge or a panel, the whole pin is nudged in so none of it is cut off or covered.
    const w = el.offsetWidth, h = el.offsetHeight;
    const clampX = (x) => Math.min(Math.max(x, M + w / 2), r.width - M - w / 2);
    const clampY = (y) => Math.min(Math.max(y, M + 11), r.height - M - h + 11);
    let x = clampX((tmp.x * 0.5 + 0.5) * r.width), y = clampY((-tmp.y * 0.5 + 0.5) * r.height);
    const hits = (px, py) => blocks.filter((b) => px + w / 2 > b.x0 + 0.5 && px - w / 2 < b.x1 - 0.5 && py - 11 + h > b.y0 + 0.5 && py - 11 < b.y1 - 0.5);
    if (hits(x, y).length) {
      // Candidates: just clear of each panel it touches, on every side; take the nearest that's clear of all of them.
      const cands = blocks.flatMap((b) => [[b.x1 + w / 2, y], [b.x0 - w / 2, y], [x, b.y1 + 11], [x, b.y0 - h + 11]])
        .map(([cx, cy]) => [clampX(cx), clampY(cy)])
        .filter(([cx, cy]) => !hits(cx, cy).length)
        .sort((p, q) => Math.hypot(p[0] - x, p[1] - y) - Math.hypot(q[0] - x, q[1] - y));
      if (cands.length) [x, y] = cands[0];
    }
    el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -11px)`;
  });
}

// ---------- interaction ----------
// Each popup opens with a verdict line: "That's right!" for a good answer, "Not quite." for a miss, and
// "That's not it." when the tries run out and the right answer is filled in.
const HEAD = { right: 'That’s right!', wrong: 'Not quite.', auto: 'That’s not it.' };
function setFeedback(text, outcome, head) {
  ui.feedback = text ? { text, outcome, head: head ?? (['Perfect', 'Acceptable'].includes(outcome) ? HEAD.right : HEAD.wrong) } : null;
}

// The pressing time: the timer fast-forwards through it, then the pan lifts off before Nonna speaks.
async function finishPressing(minutes) {
  ui.locked = true;
  refresh();
  ffLabel = 'Pressing the tofu';
  if (minutes) await ff(minutes * 60);
  if (jumping) w.weightLift = 1;
  for (const t0 = performance.now(); w.weightLift < 1;) {
    w.weightLift = Math.min(1, (performance.now() - t0) / 900);
    await sleep(16);
  }
  ui.locked = false;
}

// Single-choice answers are judged as soon as they're picked; lists are judged by the Check button.
async function checkSingle(id) {
  const res = engine.choose(id);
  const o = res.row;
  ui.optState = ui.optState || {};
  ui.optState[id] = o.correctness === 'Incorrect' ? 'wrong' : 'right';
  if (ui.optState[id] === 'wrong') { ui.selected.delete(id); ui.checkLocked = true; } else ui.selected.add(id);
  const press = /press_minutes = (\d+)/.exec(o.effect || '');
  if (press) await finishPressing(Number(press[1]));
  applyOptionEffect(o);
  setFeedback([o.feedback, chancesLine()].filter(Boolean), o.outcome, o.correctness === 'Incorrect' ? HEAD.wrong : HEAD.right);
  if (res.reveal) {
    res.reveal.forEach((rid) => { ui.optState[rid] = 'auto'; ui.selected.add(rid); });   // shown as picked for the learner
    setFeedback(o.feedback, o.outcome, HEAD.auto);
  }
  if (res.gameOver) return gameOver();
  return refresh();
}

// Ticked procedure actions (the knife's cuts): wrong picks are judged like any wrong move;
// with all the right ones ticked, they're performed and animated in order.
async function checkPicks() {
  const acts = engine.actions().filter((a) => a.source === ui.source && a.interaction === 'Click');
  const picked = acts.filter((a) => ui.selected.has(a.id));
  const wrong = picked.filter((a) => !/^\d+$/.test(a.order));
  const missing = acts.filter((a) => /^\d+$/.test(a.order) && !engine.done.has(a.id) && !ui.selected.has(a.id));
  ui.optState = ui.optState || {};
  if (wrong.length || missing.length) {
    const judged = [];
    let outcome = null;
    for (const a of wrong) {
      const res = engine.perform(a.id);
      ui.optState[a.id] = 'wrong';
      ui.selected.delete(a.id);
      judged.push({ label: a.param, feedback: res.feedback });
      outcome = res.outcome;
      if (res.gameOver) return gameOver();
    }
    if (missing.length) engine.misses += 1;
    ui.checkLocked = true;
    setFeedback(checkLines(engine.sub, judged, missing.length > 0), outcome || 'Recoverable');
    return refresh();
  }
  picked.forEach((a) => { ui.optState[a.id] = 'right'; });
  ui.locked = true;
  refresh();
  const order = picked.sort((x, y) => Number(x.order) - Number(y.order));
  let last = null;
  for (const a of order) {
    last = engine.perform(a.id);
    await VISUALS[a.id]?.();
  }
  ui.locked = false;
  ui.mode = 'items';
  ui.selected = new Set();
  setFeedback(last?.feedback || 'Nicely done.', 'Perfect');
  refresh();
}

// Multi-select feedback (storyboard): one wrong pick gets its own message; several wrong picks get
// one message naming them; if something is also missing, a line is added after the wrong-pick part.
function checkLines(sub, wrong, missing) {
  const names = wrong.map((o) => o.label);
  const list = names.length > 1 ? `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}` : names[0];
  const extra = missing && wrong.length ? sub.mixedMissing : '';
  if (wrong.length > 1 && sub.multiWrong) return [[sub.multiWrong.replace('{items}', list), extra].filter(Boolean).join(' ')];
  const lines = wrong.map((o) => ({ b: o.label, t: o.feedback }));
  // A mixedMissing starting with "=" is the whole line for one wrong pick plus a gap (storyboard 2.4).
  if (extra && lines.length === 1) lines[0].t = extra.startsWith('=') ? extra.slice(1) : `${lines[0].t} ${extra}`;
  else if (missing) lines.push(sub.incomplete || 'Something is missing.');
  return lines;
}

function doCheck() {
  const sub = engine.sub;
  if (ui.mode === 'multi') return checkPicks();
  const res = engine.check(ui.selected);
  ui.optState = ui.optState || {};
  if (res.pass) {
    engine.options().forEach((o) => { if (ui.selected.has(o.id)) { ui.optState[o.id] = 'right'; if (o.item) w.committed.add(o.item); } });
    setFeedback(['All there. Nicely done.'], 'Perfect');
  } else {
    // Right picks are confirmed and brought out now; wrong ones stay ticked, marked, for the learner to untick.
    res.wrong.forEach((o) => { ui.optState[o.id] = 'wrong'; });
    engine.options().forEach((o) => {
      if (ui.selected.has(o.id) && o.correctness !== 'Incorrect') { ui.optState[o.id] = 'right'; if (o.item) w.committed.add(o.item); }
    });
    setFeedback(checkLines(sub, res.wrong, res.missing.length > 0), null);
    const lines = ui.feedback.text;
    if (res.reveal) {
      engine.options().forEach((o) => {
        if (o.correctness === 'Incorrect') { ui.selected.delete(o.id); return; }
        if (ui.optState[o.id] !== 'right') ui.optState[o.id] = 'auto';
        ui.selected.add(o.id);
        if (o.item) w.committed.add(o.item);
      });
      lines.push('Here’s the full list. Let’s keep going.');
    }
    if (!res.reveal) lines.push(chancesLine());
    setFeedback(lines.filter(Boolean), res.wrong.length ? 'Recoverable' : null, res.reveal ? HEAD.auto : HEAD.wrong);
  }
  ui.checkLocked = !res.pass;     // stays disabled until the picks change
  return refresh();
}

function renderAction() {
  const btn = $('#action-btn');
  const sub = engine.sub;
  if (!sub || ui.locked || live || $('#hud').hidden) { btn.hidden = true; return; }
  btn.hidden = false;
  if ((sub.type === 'MCQ - Multi select' || ui.mode === 'multi') && !engine.ready) {
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
      if (ui.optState[id] === 'wrong') delete ui.optState[id];
      ui.selected.has(id) ? ui.selected.delete(id) : ui.selected.add(id);
      ui.checkLocked = false;
      renderAction();
      return renderRight();
    }
    return checkSingle(id);                      // single select: answered as soon as it's picked
  }
  const pick = e.target.closest('[data-pick]');
  if (pick && !pick.disabled) {
    const id = pick.dataset.pick;
    ui.selected.has(id) ? ui.selected.delete(id) : ui.selected.add(id);
    ui.checkLocked = false;
    renderAction();
    return renderRight();
  }
  if (e.target.closest('[data-back]')) {
    if (ui.mode === 'actions' && PROMPTED[sub.id]?.includes(ui.source)) (ui.dismissed ||= new Set()).add(ui.source);   // closed it: offer it as a card
    ui.mode = 'items'; ui.pending = null; ui.selected = new Set(); renderAction(); return renderRight(); }
  const src = e.target.closest('[data-source]');
  if (src) return pickSource(src.dataset.source);
  const act = e.target.closest('[data-act]');
  if (act) return handleActClick(act);
  const tossBtn = e.target.closest('[data-toss]');
  if (tossBtn) { s.toss = Number(tossBtn.dataset.toss); return renderRight(); }
  const liveBtn = e.target.closest('[data-live]');
  if (liveBtn) return liveAction(liveBtn.dataset.live);
});

function handleActClick(el) {
  const a = FLOW.actions.find((x) => x.id === el.dataset.act);
  choose(a);   // every option is a single click
}

const needsTarget = (a) => ['Drag', 'Click'].includes(a.interaction) && a.target && a.target !== a.source && props.anchors[a.target];

// Picking an item: if everything you can do with it is "put it somewhere", go straight to
// choosing the spot (towel → board, towel → tofu). Otherwise list what you can do with it.
// Everything the learner can pick up now, plus items the storyboard lists as there but not usable yet.
function pickables() {
  return [...new Set([...choices().map((a) => a.source), ...(engine.sub.tooEarly?.items || [])])];
}
// A task that is nothing but one pick-all-that-apply list (the tofu cuts) opens straight on the list.
function soloMulti(sub) {
  const acts = engine.actions(sub);
  return sub.type === 'Procedure' && acts.length > 1 &&
    acts.every((a) => a.interaction === 'Click' && a.source === acts[0].source && a.target && a.target === acts[0].target);
}
function missFeedback(text) {
  engine.misses += 1;
  ui.hint = engine.misses >= engine.sub.maxAttempts ? engine.nextRequired() : null;
  setFeedback([text, ui.hint ? '' : missesLine()].filter(Boolean), null);
}

function pickSource(id) {
  const early = engine.sub.tooEarly;
  if (early?.items.includes(id) && !choices().some((a) => a.source === id)) {
    missFeedback(early.texts[id]);
    return refresh();
  }
  // Merged tasks: an item whose turn hasn't come yet (the tap before the pot is in the sink) says
  // what comes first instead of offering its options.
  const req = engine.required(), next = engine.nextRequired();
  const mine = req.filter((a) => a.source === id && !engine.done.has(a.id));
  // An item with a wrong move of its own can make it: one done on the spot (skip tempering) any time,
  // one that goes somewhere (tongs that toss too soon) once the task is under way.
  const errs = choices().filter((a) => a.source === id && a.order === '-');
  const canErr = errs.some((a) => !a.target) || (errs.length > 0 && req.some((a) => engine.done.has(a.id)));
  if (!req.some((a) => a.task) && next && mine.length && !mine.some((a) => a.id === next.id) && !canErr) {
    missFeedback(mine[0].badFb || 'Not yet. Something else comes first.');
    return refresh();
  }
  ui.source = id;
  const acts = choices().filter((a) => a.source === id);
  if (acts.length === 1 && acts[0].interaction === 'Click' && !needsTarget(acts[0]) && acts[0].order !== '-') {
    return perform(acts[0]);                   // only one thing to do with it (open the tofu pack): just do it
  }
  if (acts.length > 1 && acts.every((a) => a.interaction === 'Click' && a.target && a.target === acts[0].target)) {
    ui.mode = 'multi';                         // e.g. knife: tick the cuts, then Check
    ui.selected = new Set();
    ui.checkLocked = false;
    renderAction();
  } else if (acts.length && acts.every(needsTarget)) {
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
    // Not its turn yet: the wrong move for that spot if there is one (paprika too early), else out of order.
    const fits = ui.pending.filter((a) => a.target === id);
    if (fits.length) return perform(fits.find((a) => a.id === engine.nextRequired()?.id) || fits.find((a) => a.order === '-') || fits[0]);
    const spot = engine.sub.wrongSpot?.[ui.pending[0].source];
    if (spot) { missFeedback(spot); ui.mode = 'items'; ui.pending = null; return refresh(); }
    setFeedback('Not there. Where would this go?', null);
    return renderPop(ui.feedback);
  }
  pickSource(id);
});

// Options the kitchen offers by itself when they're due (storyboard: "Options for the timer appear"):
// the shimmer wait once the oil is in, the timer once the tofu is in and again after the flip.
// The timer isn't a panel card in those tasks unless the learner closes its options.
const PROMPTED = { 'S4.2': ['E-PAN-OIL'], 'S4.3': ['E-TIMER'] };
// Moves that leave the tool in hand for its next drop.
const KEEP_HELD = new Set();
function promptNext(a) {
  const nx = engine.nextRequired();
  if (engine.ready || !nx) return;
  if (PROMPTED[engine.sub.id]?.includes(nx.source)) Object.assign(ui, { mode: 'actions', source: nx.source });
  else if (KEEP_HELD.has(a?.id) && nx.source === a.source && needsTarget(nx)) Object.assign(ui, { mode: 'target', pending: [nx] });
}

async function perform(a) {
  const res = engine.perform(a.id);
  ui.mode = 'items';
  ui.pending = null;
  ui.hint = res.hint || null;
  if (res.outOfOrder) {
    if (a.source === 'E-TAP') w.tapOn = false;
    setFeedback([res.feedback, res.hint ? '' : missesLine()].filter(Boolean), null);
    promptNext();
    return refresh();
  }
  setFeedback(res.feedback, res.ok ? (res.feedback ? 'Perfect' : null) : res.outcome);
  const fx = VISUALS[a.id];
  const moving = TOOL_PATHS[a.id]?.();
  ffLabel = a.task || a.param;
  if (fx || moving) {
    ui.locked = true;
    refresh();
    if (moving) await moving.arrived;
    await fx?.();
    if (moving) await moving.done;
    ui.locked = false;
  }
  if (res.gameOver) return gameOver();
  promptNext(a);
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
  props.resetTools();   // every tool starts a substep at home
  ui = { mode: 'items', source: null, pending: null, selected: new Set(), feedback: null, hint: null, locked: false, optState: {} };
  $('#fb-pop').hidden = true;
  popKey = '';
  ENTER[id]?.();
  setView(CAMERA_OVERRIDE[id] || sub.camera);
  if (soloMulti(sub)) Object.assign(ui, { mode: 'multi', source: engine.actions()[0].source, checkLocked: false });
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
  $('#tip-ok').textContent = 'OK';                     // every coach tip closes with OK
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
    const due = run.total * Math.min(1, (performance.now() - run.t0) / 1000 / run.dur);
    const simDt = Math.min(due - (run.total - run.remaining), run.remaining);
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
