// Procedural kitchen props for the flow: cutting board and tofu, towels and weight, pasta pot on
// its own burner, sink and tap, egg bowl contents, mug, plates, serving bowls and the service bell.
// Each prop reads the shared `world` state every frame. `anchors` gives the 3D point where a
// clickable pin is drawn for each element ID used in flow.json.
import * as THREE from 'three';

const C = (hex) => new THREE.Color(hex);
const std = (color, roughness = 0.5, metalness = 0, extra = {}) =>
  new THREE.MeshPhysicalMaterial({ color: C(color), roughness, metalness, ...extra });
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const approach = (cur, target, rate, dt) => cur + (target - cur) * (1 - Math.exp(-dt * rate));

// Layout (metres, Y up). The stove and skillet sit at the origin.
export const SPOTS = {
  board: new THREE.Vector3(0.66, 0, 0.12),
  tofuBlock: new THREE.Vector3(0.66, 0.02, 0.12),       // centred on the board
  eggBowl: new THREE.Vector3(0.5, 0, -0.18),
  whitesCup: new THREE.Vector3(0.64, 0, -0.1),
  hob: new THREE.Vector3(-0.62, 0, -0.08),
  sink: new THREE.Vector3(-0.98, 0, 0.02),
  potCounter: new THREE.Vector3(-0.15, 0, 0.27),       // where the pasta pot waits before it's filled
  plate: new THREE.Vector3(-0.42, 0, 0.3),
  mug: new THREE.Vector3(0.42, 0, 0.3),
  bowls: [new THREE.Vector3(-0.14, 0, 0.5), new THREE.Vector3(0.14, 0, 0.5)],
  bell: new THREE.Vector3(0.62, 0, 0.45),
  eggs: [new THREE.Vector3(0.76, 0, -0.24), new THREE.Vector3(0.82, 0, -0.16)],
};

// The sink's opening (matches blender/export_props.py p_sink): centre, half-size, corner radius.
export const SINK_HOLE = { x: SPOTS.sink.x, z: SPOTS.sink.z, hx: 0.2, hz: 0.17, r: 0.035 };

// A flat horizontal slab (y = 0) spanning x0..x1, z0..z1, with a rounded-rectangle hole.
// uvOf(x, z) maps world position to texture coordinates (defaults to 1 m = 1 unit).
export function slab(x0, x1, z0, z1, hole, uvOf = (x, z) => [x, -z]) {
  const shape = new THREE.Shape();
  shape.moveTo(x0, -z0); shape.lineTo(x1, -z0); shape.lineTo(x1, -z1); shape.lineTo(x0, -z1); shape.lineTo(x0, -z0);
  if (hole) {
    const { x, z, hx, hz, r } = hole, h = new THREE.Path();
    const L = x - hx, R = x + hx, T = -z + hz, B = -z - hz;
    h.moveTo(L + r, B); h.lineTo(R - r, B); h.absarc(R - r, B + r, r, -Math.PI / 2, 0, false);
    h.lineTo(R, T - r); h.absarc(R - r, T - r, r, 0, Math.PI / 2, false);
    h.lineTo(L + r, T); h.absarc(L + r, T - r, r, Math.PI / 2, Math.PI, false);
    h.lineTo(L, B + r); h.absarc(L + r, B + r, r, Math.PI, Math.PI * 1.5, false);
    shape.holes.push(h);
  }
  const g = new THREE.ShapeGeometry(shape, 12).rotateX(-Math.PI / 2);   // shape y = -z
  const pos = g.attributes.position, uv = g.attributes.uv;
  for (let i = 0; i < pos.count; i++) uv.setXY(i, ...uvOf(pos.getX(i), pos.getZ(i)));
  return g;
}

// Per-material touch-ups so the models read in the real-time kitchen as they do on their cards
// (a heavy clear coat that's right under Cycles' soft lights turns pale under the room HDRI).
const MODEL_TUNING = {
  MugGlaze: { clearcoat: 0.25, clearcoatRoughness: 0.2 },
  HobGlass: { clearcoat: 0.6 },
  BellChrome: { roughness: 0.18 },
};

export class Props {
  constructor(scene, { pastaMaterial, tofuMaterial }) {
    this.root = new THREE.Group();
    scene.add(this.root);
    // The pan's pasta material uses per-strand vertex colours; these simpler meshes have none,
    // so they get their own copy that follows its colour every frame.
    this.sourcePasta = pastaMaterial;
    this.pastaMaterial = pastaMaterial.clone();
    this.pastaMaterial.vertexColors = false;
    // Things that only appear once they're brought to the counter (keys are flow item IDs,
    // plus PLATE and SERVING for the resting plate and serving bowls).
    this.items = {};
    this._room();
    this.tofuMaterial = tofuMaterial;
    this.steel = std('#c9ccd0', 0.28, 1);
    this.darkSteel = std('#6f7378', 0.35, 1);
    this.white = std('#f2efe8', 0.25, 0, { clearcoat: 0.6 });
    this._board();
    this._tofu();
    this._hobAndPot();
    this._sink();
    this._eggBowl();
    this._smallThings();
    this._serving();
    this.anchors = this._anchors();
    this.potPos = SPOTS.potCounter.clone();
  }

  _add(mesh, shadow = true) {
    mesh.castShadow = mesh.receiveShadow = shadow;
    this.root.add(mesh);
    return mesh;
  }

  _room() {
    // Counter front edge and cabinet, plus a wider worktop so wide views don't fall off the set.
    const lip = this._add(new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.04, 0.03), std('#7a4c2c', 0.5)));
    lip.position.set(0, -0.02, 0.715);
    const cabinet = this._add(new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.9, 0.02), std('#2c2723', 0.6)), false);
    cabinet.position.set(0, -0.49, 0.69);
    const worktop = this.worktop = this._add(new THREE.Mesh(slab(-2.3, 2.3, -1.1, 0.7, SINK_HOLE), std('#8a5a37', 0.5)), false);
    worktop.position.set(0, -0.0008, 0);
    worktop.receiveShadow = true;
    const wall = this._add(new THREE.Mesh(new THREE.PlaneGeometry(4.6, 1.4), std('#e9e6df', 0.4)), false);
    wall.position.set(0, 0.7, -0.551);
  }

  _board() {
    const b = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.36, 0.02, 0.25), std('#b98a5a', 0.6)));
    b.position.copy(SPOTS.board).setY(0.01);
    this.items['T-KNIFE'] = [b];
  }

  // The knife at rest beside the board, or mid-cut: level 1 slices flat through the side of the
  // block (slabs), 2 chops down along its length (strips), 3 chops across (cubes). k runs 0 -> 1
  // over the whole set of cuts; returns how many of that set's cut lines are done.
  _poseKnife(ca) {
    const knife = this.knife;
    if (!knife || !this.knifeRest) return 0;
    if (!ca) {
      knife.position.copy(this.knifeRest);
      knife.rotation.set(0, 1.45, 0);
      return 0;
    }
    const set = this.cutSets[ca.level - 1], n = set.length;
    const seg = Math.min(ca.k, 0.9999) * n, j = Math.floor(seg), f = seg - j;
    const m = set[j].position, c = this.cuts.position;
    const away = Math.abs(1 - 2 * f);                    // 1 = clear of the tofu, 0 = through it
    const half = this.bladeWidth / 2;
    if (ca.level === 1) {
      knife.rotation.set(0, 0, 0);
      knife.position.set(c.x, c.y + m.y, c.z + 0.01 + (0.07 + half) * away);
    } else {
      knife.rotation.set(Math.PI / 2, ca.level === 2 ? 0 : Math.PI / 2, 0);
      const y = 0.021 + half + 0.04 * away;                 // edge comes down onto the board
      if (ca.level === 2) knife.position.set(c.x + 0.02, y, c.z + m.z);
      else knife.position.set(c.x + m.x, y, c.z - 0.02);
    }
    return f >= 0.5 ? j + 1 : j;
  }

  _tofu() {
    const p = SPOTS.tofuBlock;
    this.pack = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.118, 0.04, 0.082),
      std('#dfe8ee', 0.1, 0, { transparent: true, opacity: 0.45, transmission: 0.4 })), false);
    this.pack.position.set(p.x, p.y + 0.02, p.z);
    // Packing water that spills out when the pack is opened, then runs off the board.
    this.puddle = this._add(new THREE.Mesh(new THREE.CircleGeometry(0.09, 40),
      std('#cfe0e8', 0.03, 0, { transparent: true, opacity: 0, depthWrite: false })), false);
    this.puddle.rotation.x = -Math.PI / 2;
    this.puddle.scale.set(1, 0.75, 1);
    this.puddle.position.set(p.x, 0.0205, p.z);
    this.block = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.03, 0.065, 4, 2, 3), std('#efe7d3', 0.55, 0, { sheen: 0.3 })));
    this.block.position.set(p.x, p.y + 0.015, p.z);
    const towelMat = std('#e9e4da', 0.9);
    this.towelBottom = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.17, 0.004, 0.12), towelMat));
    this.towelBottom.position.set(p.x, p.y + 0.002, p.z);
    this.towelTop = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.004, 0.11), towelMat));
    this.towelTop.position.set(p.x, p.y + 0.036, p.z);
    this.weight = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.08, 0.03, 40), std('#26231f', 0.45)));
    this.weight.position.set(p.x, p.y + 0.054, p.z);
    this.weightY = p.y + 0.054;
    // Cut lines appear on the block as each cut is made.
    this.cuts = new THREE.Group();
    const line = (w, d) => new THREE.Mesh(new THREE.BoxGeometry(w, 0.0008, d), std('#8c7f68', 0.8));
    this.cutSets = [[], [], []];
    for (let i = 1; i < 3; i++) {                        // slabs: two horizontal cuts on the side
      const m = line(0.101, 0.066); m.position.set(0, -0.015 + i * 0.01, 0); this.cutSets[0].push(m);
    }
    for (let i = 1; i < 7; i++) {                        // strips
      const m = line(0.101, 0.0012); m.position.set(0, 0.0155, -0.0325 + i * 0.0093); this.cutSets[1].push(m);
    }
    for (let i = 1; i < 10; i++) {                       // cubes
      const m = line(0.0012, 0.066); m.position.set(-0.05 + i * 0.01, 0.0155, 0); this.cutSets[2].push(m);
    }
    this.cutSets.flat().forEach((m) => this.cuts.add(m));
    this.cuts.position.copy(this.block.position);
    this.root.add(this.cuts);
  }

  _hobAndPot() {
    const h = SPOTS.hob;
    const pad = this.hobPad = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.012, 0.3), std('#121212', 0.15, 0, { clearcoat: 1 })));
    pad.position.set(h.x, 0.006, h.z);
    this.hobRing = this._add(new THREE.Mesh(new THREE.TorusGeometry(0.09, 0.003, 8, 64), new THREE.MeshBasicMaterial({ color: C('#5a5a5a') })), false);
    this.hobRing.rotation.x = -Math.PI / 2;
    this.hobRing.position.set(h.x, 0.0125, h.z);
    this.backKnob = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.018, 32), this.steel));
    this.backKnob.position.set(h.x, 0.021, h.z + 0.18);
    const grip = new THREE.Mesh(new THREE.BoxGeometry(0.028, 0.008, 0.007), this.steel);
    grip.position.y = 0.012;
    this.backKnob.add(grip);

    this.pot = new THREE.Group();
    const prof = [[0, 0], [0.105, 0], [0.11, 0.006], [0.11, 0.15], [0.114, 0.152], [0.104, 0.152], [0.104, 0.006], [0, 0.006]]
      .map(([x, y]) => new THREE.Vector2(x, y));
    const body = new THREE.Mesh(new THREE.LatheGeometry(prof, 64), this.steel);
    body.castShadow = body.receiveShadow = true;
    this.pot.add(body);
    this.potShell = [body];
    for (const s of [-1, 1]) {
      const handle = new THREE.Mesh(new THREE.TorusGeometry(0.018, 0.004, 8, 16, Math.PI), this.steel);
      handle.position.set(s * 0.118, 0.13, 0);
      handle.rotation.set(0, s > 0 ? Math.PI / 2 : -Math.PI / 2, 0);
      this.pot.add(handle);
      this.potShell.push(handle);
    }
    this.water = new THREE.Mesh(new THREE.CircleGeometry(0.103, 48).rotateX(-Math.PI / 2),
      std('#a9bcc4', 0.05, 0, { transmission: 0.6, transparent: true, opacity: 0.85 }));
    this.pot.add(this.water);
    // Spaghetti in the pot: a loose bundle of curved strands under the water line.
    const strands = [];
    for (let i = 0; i < 40; i++) {
      const a = (i / 40) * Math.PI * 2, r = 0.02 + (i % 5) * 0.012;
      const pts = [];
      for (let k = 0; k < 10; k++) {
        const t = k / 9, ang = a + t * 2.4;
        pts.push(new THREE.Vector3(Math.cos(ang) * (r + t * 0.05), 0.02 + t * 0.07, Math.sin(ang) * (r + t * 0.05)));
      }
      strands.push(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 16, 0.0011, 5, false));
    }
    this.potPasta = new THREE.Group();
    strands.forEach((g) => this.potPasta.add(new THREE.Mesh(g, this.pastaMaterial)));
    this.pot.add(this.potPasta);
    this.bubbles = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 8, 6),
      std('#ffffff', 0.05, 0, { transparent: true, opacity: 0.5 }), 80);
    this.bubbleSeeds = Array.from({ length: 80 }, () => ({ a: Math.random() * 6.28, r: Math.sqrt(Math.random()) * 0.095, p: Math.random() }));
    this.pot.add(this.bubbles);
    this.root.add(this.pot);

    this.lid = new THREE.Group();
    const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.115, 0.118, 0.006, 48), this.steel);
    const knob = new THREE.Mesh(new THREE.SphereGeometry(0.012, 16, 12), std('#1b1b1b', 0.4));
    knob.position.y = 0.01;
    this.lid.add(disc, knob);
    this.lidShell = [disc, knob];
    this.lid.traverse((o) => { o.castShadow = true; });
    this.root.add(this.lid);
    this.items['T-POT'] = [this.pot, this.lid];
  }

  _sink() {
    const s = SPOTS.sink;
    const rim = this.sinkRim = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.44, 0.006, 0.38), this.steel));
    rim.position.set(s.x, 0.003, s.z);
    const basin = this.sinkBasin = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.38, 0.0065, 0.32), std('#55595d', 0.3, 1)));
    basin.position.set(s.x, 0.0035, s.z);
    const drain = this.sinkDrain = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.0068, 24), std('#2a2c2e', 0.3, 1)));
    drain.position.set(s.x, 0.0036, s.z);
    const tapBase = this.tapBase = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.018, 0.24, 24), this.steel));
    tapBase.position.set(s.x, 0.12, s.z - 0.2);
    const arc = new THREE.CatmullRomCurve3([
      new THREE.Vector3(s.x, 0.24, s.z - 0.2), new THREE.Vector3(s.x, 0.3, s.z - 0.16),
      new THREE.Vector3(s.x, 0.29, s.z - 0.08), new THREE.Vector3(s.x, 0.25, s.z - 0.04)]);
    this.tapNeck = this._add(new THREE.Mesh(new THREE.TubeGeometry(arc, 24, 0.011, 12, false), this.steel));
    this.stream = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.005, 0.006, 0.2, 12),
      std('#d6e6ee', 0.02, 0, { transmission: 0.8, transparent: true, opacity: 0.7 })), false);
    this.stream.position.set(s.x, 0.15, s.z - 0.04);
  }

  _eggBowl() {
    const b = SPOTS.eggBowl;
    this.bowlFill = this._add(new THREE.Mesh(new THREE.CircleGeometry(0.052, 40).rotateX(-Math.PI / 2),
      std('#f0a02a', 0.12, 0, { clearcoat: 1 })), false);
    this.bowlFill.position.set(b.x, 0.02, b.z);
    this.yolks = [];
    for (let i = 0; i < 5; i++) {
      const y = this._add(new THREE.Mesh(new THREE.SphereGeometry(0.012, 24, 16), std('#f08a12', 0.08, 0, { clearcoat: 1 })));
      const a = i * 1.26;
      y.scale.y = 0.6;
      y.position.set(b.x + Math.cos(a) * 0.022, 0.024, b.z + Math.sin(a) * 0.022);
      this.yolks.push(y);
    }
    this.cheese = this._add(new THREE.Mesh(new THREE.SphereGeometry(0.03, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), std('#f4ecd2', 0.9)));
    this.cheese.scale.y = 0.45;
    this.cheese.position.set(b.x + 0.01, 0.022, b.z);
    const cup = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.032, 0.028, 0.05, 32, 1, true),
      std('#e8f1f4', 0.05, 0, { transmission: 0.9, transparent: true, opacity: 0.5, side: THREE.DoubleSide })), false);
    cup.position.copy(SPOTS.whitesCup).setY(0.025);
    this.items['T-BOWL'] = [cup];
    this.whites = this._add(new THREE.Mesh(new THREE.CircleGeometry(0.029, 32).rotateX(-Math.PI / 2),
      std('#f3f0e2', 0.1, 0, { transparent: true, opacity: 0.6 })), false);
    this.whites.position.copy(SPOTS.whitesCup).setY(0.012);
  }

  _smallThings() {
    const pl = SPOTS.plate;
    const plate = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.065, 0.01, 48), this.white));
    plate.position.set(pl.x, 0.005, pl.z);
    const paper = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.001, 0.08), std('#fbfaf5', 0.95)));
    paper.position.set(pl.x, 0.0105, pl.z);
    paper.rotation.y = 0.4;
    this.items['PLATE'] = [plate, paper];

    const m = SPOTS.mug;
    const mugProf = [[0, 0], [0.032, 0], [0.034, 0.075], [0.031, 0.075], [0.029, 0.006], [0, 0.006]].map(([x, y]) => new THREE.Vector2(x, y));
    const mugBody = this._add(new THREE.Mesh(new THREE.LatheGeometry(mugProf, 40), std('#3d5a6b', 0.3, 0, { clearcoat: 0.8 })));
    mugBody.position.copy(m);
    const handle = this._add(new THREE.Mesh(new THREE.TorusGeometry(0.018, 0.005, 10, 20, Math.PI), std('#3d5a6b', 0.3)));
    handle.position.set(m.x + 0.034, 0.04, m.z);
    handle.rotation.z = -Math.PI / 2;
    this.items['T-MUG'] = [mugBody, handle];
    this.mugWater = this._add(new THREE.Mesh(new THREE.CircleGeometry(0.029, 32).rotateX(-Math.PI / 2), std('#d9d2bd', 0.05, 0, { clearcoat: 1 })), false);
    this.mugWater.position.set(m.x, 0.06, m.z);

    const bell = SPOTS.bell;
    const base = this.bellBase = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.038, 0.01, 32), std('#2a2522', 0.4)));
    base.position.set(bell.x, 0.005, bell.z);
    this.bellDome = this._add(new THREE.Mesh(new THREE.SphereGeometry(0.03, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2), std('#c9a24a', 0.2, 1)));
    this.bellDome.position.set(bell.x, 0.01, bell.z);
    const plunger = new THREE.Mesh(new THREE.CylinderGeometry(0.003, 0.003, 0.012, 8), std('#c9a24a', 0.2, 1));
    plunger.position.y = 0.035;
    this.bellDome.add(plunger);

    // Grater, pecorino wedge and pepper mill beside the prep area.
    const grater = this._add(new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.11, 0.045), this.darkSteel));
    grater.position.set(0.9, 0.055, -0.02);
    const wedge = new THREE.Shape();
    wedge.moveTo(0, 0); wedge.lineTo(0.08, 0.02); wedge.lineTo(0.08, -0.02); wedge.lineTo(0, 0);
    const cheese = this._add(new THREE.Mesh(new THREE.ExtrudeGeometry(wedge, { depth: 0.035, bevelEnabled: false }), std('#efe2b8', 0.7)));
    cheese.rotation.x = -Math.PI / 2;
    cheese.position.set(0.86, 0, -0.14);
    const mill = this._add(new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.022, 0.13, 24), std('#5a3a22', 0.5)));
    mill.position.set(0.4, 0.065, -0.33);
    this.items['T-GRATER'] = [grater];
    this.items['I-PECORINO'] = [cheese];
    this.items['I-PEPPER'] = [mill];
  }

  _serving() {
    const prof = [[0, 0], [0.04, 0], [0.042, 0.006], [0.085, 0.035], [0.095, 0.05], [0.091, 0.051], [0.08, 0.038], [0.04, 0.012], [0, 0.012]]
      .map(([x, y]) => new THREE.Vector2(x, y));
    const geo = new THREE.LatheGeometry(prof, 64);
    this.nests = [];
    SPOTS.bowls.forEach((p) => {
      const servingBowl = this._add(new THREE.Mesh(geo, this.white));
      servingBowl.position.copy(p);
      (this.items['SERVING'] = this.items['SERVING'] || []).push(servingBowl);
      // A twirled nest of pasta: a tightening spiral of tubes rising in the middle.
      const nest = new THREE.Group();
      for (let k = 0; k < 14; k++) {
        const pts = [];
        const a0 = k * 0.45;
        for (let i = 0; i < 40; i++) {
          const t = i / 39, a = a0 + t * Math.PI * 4, r = 0.055 * (1 - t * 0.85);
          pts.push(new THREE.Vector3(Math.cos(a) * r, 0.016 + t * 0.03 + Math.sin(i + k) * 0.002, Math.sin(a) * r));
        }
        nest.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 80, 0.0013, 5, false), this.pastaMaterial));
      }
      for (let i = 0; i < 8; i++) {
        const cube = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.01, 0.01), this.tofuMaterial);
        cube.position.set(Math.cos(i * 0.8) * 0.02, 0.05, Math.sin(i * 1.7) * 0.02);
        cube.rotation.set(i, i * 2, 0);
        nest.add(cube);
      }
      const dust = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 0), std('#1c140e', 0.6), 60);
      const mtx = new THREE.Matrix4();
      for (let i = 0; i < 60; i++) {
        const a = Math.random() * 6.28, r = Math.random() * 0.04, s = 0.0008 + Math.random() * 0.0008;
        mtx.makeScale(s, s, s).setPosition(Math.cos(a) * r, 0.044 + Math.random() * 0.006, Math.sin(a) * r);
        dust.setMatrixAt(i, mtx);
      }
      nest.add(dust);
      nest.userData.dust = dust;
      nest.position.copy(p);
      nest.traverse((o) => { o.castShadow = true; });
      this.root.add(nest);
      this.nests.push(nest);
    });
  }

  // Contact shadow: a soft dark ellipse on the counter under an object, the "ambient
  // occlusion" that grounds it (the renders get this from path tracing). Follows the object
  // around and shows only while the object does and is sitting at counter height.
  addContact(obj, { spread = 1.25, opacity = 0.55 } = {}) {
    if (!Props.contactTex) {
      const c = document.createElement('canvas');
      c.width = c.height = 128;
      const g = c.getContext('2d');
      const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
      grd.addColorStop(0, 'rgba(0,0,0,1)'); grd.addColorStop(0.45, 'rgba(0,0,0,0.75)'); grd.addColorStop(1, 'rgba(0,0,0,0)');
      g.fillStyle = grd;
      g.fillRect(0, 0, 128, 128);
      Props.contactTex = new THREE.CanvasTexture(c);
    }
    obj.updateWorldMatrix(true, true);
    const size = new THREE.Box3().setFromObject(obj).getSize(new THREE.Vector3());
    const mat = new THREE.MeshBasicMaterial({ color: 0x000000, alphaMap: Props.contactTex, transparent: true, opacity,
      depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, toneMapped: false });
    const quad = new THREE.Mesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), mat);
    quad.scale.set(size.x * spread, 1, size.z * spread);
    quad.renderOrder = -1;
    this.root.add(quad);
    (this.contacts = this.contacts || []).push({ obj, quad, base: new THREE.Box3() });
    return quad;
  }

  _updateContacts() {
    const shown = (o) => { for (; o; o = o.parent) if (!o.visible) return false; return true; };
    const tmp = new THREE.Box3();
    for (const c of this.contacts || []) {
      tmp.setFromObject(c.obj, false);
      const onCounter = shown(c.obj) && !tmp.isEmpty() && Math.abs(tmp.min.y) < 0.03;
      c.quad.visible = onCounter;
      if (onCounter) c.quad.position.set((tmp.min.x + tmp.max.x) / 2, 0.0006, (tmp.min.z + tmp.max.z) / 2);
    }
  }

  // Swap the simple shapes for the Blender models (blender/export_props.py), the same ones the
  // item cards are rendered from. The shapes stay as invisible stand-ins: their visibility and
  // movement still drive everything, and each model follows its stand-in.
  useModels(gltfScene) {
    const hidden = new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false });
    const model = (name) => {
      const m = gltfScene.getObjectByName(`P-${name}`).clone(true);
      m.traverse((o) => {
        if (!o.isMesh) return;
        o.castShadow = o.receiveShadow = true;
        const tune = MODEL_TUNING[o.material.name];
        if (tune) Object.assign(o.material, tune);
      });
      return m;
    };
    const hide = (meshes) => meshes.forEach((o) => { o.material = hidden; o.castShadow = false; });
    // Model as a child of a stand-in mesh, sitting on the stand-in's base, fitted to its footprint.
    const onto = (stand, name, { fit = true, extra = [] } = {}) => {
      const m = model(name);
      stand.geometry.computeBoundingBox();
      const sb = stand.geometry.boundingBox, mb = new THREE.Box3().setFromObject(m);
      const ss = sb.getSize(new THREE.Vector3()), ms = mb.getSize(new THREE.Vector3());
      const k = fit ? Math.min(ss.x / ms.x, ss.z / ms.z) : 1;
      m.scale.setScalar(k);
      const c = mb.getCenter(new THREE.Vector3());
      m.position.set(-c.x * k, sb.min.y - mb.min.y * k, -c.z * k);
      stand.add(m);
      hide([stand, ...extra]);
      return m;
    };
    const board = onto(this.items['T-KNIFE'][0], 'board');
    // The board model comes with its knife lying across it: move the knife beside the board so it
    // stays clear of the tofu and towels.
    board.updateWorldMatrix(true, true);
    const knifeParts = ['Blade', 'KnifeHandle'].map((n) => board.getObjectByName(n)).filter(Boolean);
    const knife = this.knife = new THREE.Group();
    knife.rotation.order = 'YXZ';                          // yaw, then tip the blade up about its own length
    if (knifeParts.length) {
      const blade = knifeParts[0];
      const centre = new THREE.Box3().setFromObject(blade).getCenter(new THREE.Vector3());
      knife.position.copy(centre);
      this.root.add(knife);
      knife.updateWorldMatrix(true, false);
      const inner = new THREE.Group();
      knife.add(inner);
      knifeParts.forEach((o) => inner.attach(o));
      // Turn the parts so the blade runs along the knife's local x with the handle at -x.
      const pts = [], Y = new THREE.Vector3(0, 1, 0);
      const pa = blade.geometry.attributes.position;
      for (let k = 0; k < pa.count; k++) pts.push(new THREE.Vector3().fromBufferAttribute(pa, k).applyMatrix4(blade.matrixWorld).sub(centre));
      let best = 0, bestZ = Infinity;
      for (let a = 0; a < Math.PI; a += Math.PI / 360) {
        let lo = Infinity, hi = -Infinity;
        pts.forEach((v) => { const z = v.clone().applyAxisAngle(Y, -a).z; lo = Math.min(lo, z); hi = Math.max(hi, z); });
        if (hi - lo < bestZ) { bestZ = hi - lo; best = a; }
      }
      const handle = new THREE.Box3().setFromObject(knifeParts[1] || blade).getCenter(new THREE.Vector3()).sub(centre);
      if (handle.applyAxisAngle(Y, -best).x > 0) best += Math.PI;
      inner.rotation.y = -best;
      this.bladeWidth = bestZ;
      // Resting on the counter to the right of the board, handle towards the learner.
      knife.position.set(0.93, 0, 0.22);
      knife.rotation.set(0, 1.45, 0);
      knife.updateWorldMatrix(true, true);
      knife.position.y -= new THREE.Box3().setFromObject(knife).min.y;
      this.knifeRest = knife.position.clone();
    }
    onto(this.items['T-GRATER'][0], 'grater');
    onto(this.items['I-PEPPER'][0], 'mill', { fit: false });
    onto(this.items['T-BOWL'][0], 'cup', { fit: false });
    onto(this.items['T-MUG'][0], 'mug', { fit: false, extra: this.items['T-MUG'].slice(1) });
    onto(this.bellBase, 'bell', { fit: false, extra: [this.bellDome, ...this.bellDome.children] });
    onto(this.block, 'tofu', { fit: false });
    onto(this.towelBottom, 'towel');
    onto(this.towelTop, 'towel');
    onto(this.weight, 'weight', { fit: false });
    // The cheese stand-in is an extruded wedge lying on its side: place the model in world space.
    const cheese = this.items['I-PECORINO'][0];
    const pec = model('pecorino');
    pec.scale.setScalar(0.6);
    pec.position.set(0.86, 0, -0.16);
    pec.rotation.y = -0.5;
    this.root.add(pec);
    hide([cheese]);
    this.followers = [[pec, cheese], [knife, this.items['T-KNIFE'][0]]];
    // Sink (sunken through the opening cut in the counter) and the induction hob.
    const sink = model('sink');
    sink.position.copy(SPOTS.sink);
    this.root.add(sink);
    hide([this.sinkRim, this.sinkBasin, this.sinkDrain, this.tapBase, this.tapNeck]);
    const hob = model('hob');
    hob.position.set(SPOTS.hob.x, 0, SPOTS.hob.z);
    this.root.add(hob);
    hide([this.hobPad]);
    // Pot and lid: the models share the stand-ins' origin (pot base; lid sits 0.155 up).
    this.pot.add(model('pot'));
    hide(this.potShell);
    const lid = model('lid');
    lid.position.y = -0.155;
    this.lid.add(lid);
    hide(this.lidShell);
    for (const o of [this.items['T-KNIFE'][0], this.items['T-GRATER'][0], this.items['I-PEPPER'][0], this.items['T-BOWL'][0],
      this.items['T-MUG'][0], this.bellBase, pec, this.pot, this.lid, ...this.items['PLATE'].slice(0, 1), ...(this.items['SERVING'] || [])]) {
      this.addContact(o);
    }
    this.addContact(hob, { spread: 1.08, opacity: 0.4 });
  }

  _anchors() {
    const v = (x, y, z) => new THREE.Vector3(x, y, z);
    const t = SPOTS.tofuBlock, h = SPOTS.hob, s = SPOTS.sink, b = SPOTS.eggBowl;
    return {
      'E-BOARD': v(SPOTS.board.x + 0.1, 0.03, SPOTS.board.z + 0.08),
      'I-TOFU': v(t.x, 0.06, t.z),
      'E-CUT-GUIDES': v(t.x, 0.045, t.z),
      'E-SINK': v(s.x, 0.02, s.z + 0.08),
      'E-TAP': v(s.x, 0.3, s.z - 0.14),
      'E-BURNER-BACK': v(h.x, 0.03, h.z),
      'E-KNOB-BACK': v(h.x, 0.04, h.z + 0.18),
      'E-KNOB-FRONT': v(0.24, 0.06, 0.19),
      'E-PAN-OIL': v(-0.04, 0.07, 0.04),
      'T-SKILLET': v(0, 0.11, -0.03),
      'T-POT': v(0, 0, 0),                      // follows the pot; set in update()
      'T-LID': v(0, 0, 0),                      // follows the lid; set in update()
      'T-BOWL': v(b.x, 0.075, b.z),
      'E-COUNTER': v(b.x, 0.02, b.z + 0.08),
      'E-WHITES-CUP': v(SPOTS.whitesCup.x, 0.07, SPOTS.whitesCup.z),
      'E-PLATE': v(SPOTS.plate.x, 0.03, SPOTS.plate.z),
      'T-MUG': v(SPOTS.mug.x, 0.1, SPOTS.mug.z),
      'E-BOWLS': v(0, 0.07, SPOTS.bowls[0].z),
      'E-BELL': v(SPOTS.bell.x, 0.07, SPOTS.bell.z),
      'T-SLOTTED': v(-0.06, 0.09, 0.06),
      'T-TONGS': v(0.05, 0.09, 0.06),
    };
  }

  // Is this item's model in the kitchen right now (so it can be clicked there)? Read from the
  // world state rather than mesh visibility, which only catches up on the next frame.
  shown(id, w) {
    if (id === 'T-LID') return this.shown('T-POT', w);
    if (id === 'I-TOFU') return ['pack', 'draining', 'block', 'pressing', 'pressed', 'cubes'].includes(w.tofuStage);
    return this.items[id] ? w.committed.has(id) || w.onCounter.has(id) : null;   // null: no model to check
  }

  update(w, dt, t) {
    this.followers?.forEach(([m, stand]) => { m.visible = stand.visible; });
    this._updateContacts();
    this.pastaMaterial.color.copy(this.sourcePasta.color);
    this.pastaMaterial.roughness = this.sourcePasta.roughness;
    this.pastaMaterial.clearcoat = this.sourcePasta.clearcoat;
    if (!w.served) this.pastaMaterial.color.set('#e8cf98');   // plain cooked pasta in the pot
    // Tofu block stages.
    // Opening the pack: it lifts away and fades while the water spreads and drains off.
    const draining = w.tofuStage === 'draining';
    w.drain = draining ? Math.min(1, (w.drain || 0) + dt / 1.5) : 0;
    const d = w.drain, ease = d * d * (3 - 2 * d);
    this.pack.visible = w.tofuStage === 'pack' || (draining && d < 1);   // 'none' until the tofu is brought to the counter
    this.pack.position.y = SPOTS.tofuBlock.y + 0.02 + 0.09 * ease;
    this.pack.material.opacity = 0.45 * (1 - ease);
    this.puddle.visible = draining;
    const r = Math.min(1, d / 0.35);
    this.puddle.scale.set(0.4 + 0.6 * r, 0.3 + 0.45 * r, 1);
    this.puddle.material.opacity = 0.55 * Math.min(1, d / 0.15) * (1 - Math.max(0, (d - 0.45) / 0.55));
    this.block.visible = ['pack', 'draining', 'block', 'pressing', 'pressed'].includes(w.tofuStage);
    this.block.scale.y = w.tofuStage === 'pressed' ? 0.92 : 1;
    this.block.position.y = SPOTS.tofuBlock.y + 0.015 + (w.towelBottom && !w.pressDone ? 0.004 : 0);   // sits on the towel
    this.towelBottom.visible = w.towelBottom && w.tofuStage !== 'cubes' && !w.pressDone;
    this.towelTop.visible = w.towelTop && !w.pressDone;
    // Pressing over: the pan lifts off and fades out (w.weightLift 0 → 1).
    const wl = w.weightLift || 0, le = wl * wl * (3 - 2 * wl);
    this.weight.visible = w.weight && !w.pressDone && wl < 1;
    this.weight.position.y = this.weightY + 0.12 * le;
    if (wl !== this.weightFade) {
      this.weightFade = wl;
      this.weight.traverse((o) => {
        if (!o.material) return;
        if (!o.userData.ownMat) { o.material = o.material.clone(); o.material.transparent = true; o.userData.ownMat = true; }
        o.material.opacity = 1 - le;
      });
    }
    this.cuts.visible = this.block.visible && w.cutLevel > 0;
    // While a cut is being made (w.cutAnim = { level, k }), its lines appear as the knife passes them.
    const ca = w.cutAnim;
    const shown = this._poseKnife(ca);
    if (ca) this.cuts.visible = this.block.visible;
    this.cutSets.forEach((set, i) => set.forEach((m, j) => { m.visible = w.cutLevel > i || (!!ca && ca.level === i + 1 && j < shown); }));

    // Pot: counter -> sink -> hob, water level, lid, boil.
    const target = w.potOnHob ? SPOTS.hob : w.potInSink ? SPOTS.sink : SPOTS.potCounter;
    this.potPos.x = approach(this.potPos.x, target.x, 5, dt);
    this.potPos.z = approach(this.potPos.z, target.z, 5, dt);
    const lift = Math.min(Math.abs(this.potPos.x - target.x) * 2, 0.08);
    const SINK_FLOOR = -0.168;                            // the basin floor, 17 cm below the counter
    this.pot.position.set(this.potPos.x, (w.potOnHob ? 0.012 : w.potInSink ? SINK_FLOOR : 0) + lift, this.potPos.z);
    this.anchors['T-POT'].set(this.potPos.x, this.pot.position.y + 0.19, this.potPos.z);
    // The tap's stream runs from the aerator down to the water in the pot (or the basin floor).
    const top = 0.245, bottom = w.potOnHob ? SINK_FLOOR : this.pot.position.y + Math.max(w.waterLevel, 0.008);
    this.stream.scale.y = (top - bottom) / 0.2;
    this.stream.position.y = (top + bottom) / 2;
    w.waterLevel = approach(w.waterLevel, w.potFilled ? 0.11 : (w.tapOn ? 0.11 : 0), w.tapOn ? 0.8 : 3, dt);
    this.water.visible = w.waterLevel > 0.004;
    this.water.position.y = Math.max(0.007, w.waterLevel);
    this.stream.visible = w.tapOn;
    this.lid.position.set(w.lidOn ? this.potPos.x : -0.38, w.lidOn ? this.pot.position.y + 0.155 : 0.006, w.lidOn ? this.potPos.z : -0.32);
    this.lid.rotation.x = w.lidOn ? 0 : 0;
    this.anchors['T-LID'].set(this.lid.position.x, this.lid.position.y + 0.03, this.lid.position.z);
    this.potPasta.visible = w.pastaInPot;
    this.backKnob.rotation.y = -w.backHeat * 0.85;
    this.hobRing.material.color.set(w.backHeat > 0 ? '#ff5a2a' : '#5a5a5a');
    const boil = w.lidOn ? 0 : w.boil;
    const m = new THREE.Matrix4();
    this.bubbleSeeds.forEach((b, i) => {
      const life = (t * (0.8 + b.r * 10) + b.p) % 1;
      const s = boil * 0.004 * Math.sin(life * Math.PI);
      m.makeScale(s, s * 0.6, s).setPosition(Math.cos(b.a) * b.r, w.waterLevel + 0.001, Math.sin(b.a) * b.r);
      this.bubbles.setMatrixAt(i, m);
    });
    this.bubbles.instanceMatrix.needsUpdate = true;
    this.bubbles.visible = boil > 0.05 && this.water.visible;

    // Egg bowl contents.
    const stage = w.bowlStage;
    this.yolks.forEach((y, i) => { y.visible = stage === 'eggs' && i < w.wholeEggs + w.yolks; });
    this.bowlFill.visible = ['eggs', 'paste', 'tempered'].includes(stage) && (w.wholeEggs > 0 || stage !== 'eggs');
    const fillColor = stage === 'paste' ? '#e9b24a' : stage === 'tempered' ? '#f0c56a' : '#f2e3b8';
    this.bowlFill.material.color.set(fillColor);
    this.bowlFill.position.y = stage === 'tempered' ? 0.028 : 0.02;
    this.cheese.visible = stage === 'eggs' && w.cheeseIn;
    this.whites.visible = w.yolks > 0;

    this.mugWater.visible = w.mugFull;
    this.nests.forEach((n, i) => {
      n.visible = w.plated > i;
      n.userData.dust.visible = w.peppered;
    });
    this.bellDome.position.y = 0.01 - (w.bellT > 0 ? 0.004 * Math.sin(w.bellT * 30) : 0);
    w.bellT = Math.max(0, w.bellT - dt);

    // Only what has been brought to the counter is visible.
    for (const [id, objs] of Object.entries(this.items)) {
      const on = w.onCounter.has(id);
      objs.forEach((o) => { o.visible = on; });
    }
  }
}
