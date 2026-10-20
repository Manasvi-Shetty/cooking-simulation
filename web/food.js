// Real-time food for the carbonara slice. Everything here is generated in code and
// driven by the simulation state, so it can change live: guanciale renders and
// browns, the egg sauce goes from raw to silky (or scrambles into curds).
// Ported from the Blender look-tests in blender/food_test.py.
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { SimplexNoise } from 'three/addons/math/SimplexNoise.js';
import { SPOTS } from './props.js';

// Kitchen GLB is Y-up; the skillet's cooking surface sits on the grate.
export const PAN = { floorY: 0.053, pileR: 0.108, strandR: 0.0011 };

const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const smooth = (a, b, v) => { const t = clamp((v - a) / (b - a)); return t * t * (3 - 2 * t); };
const ease = (t) => 1 - Math.pow(1 - clamp(t), 3);

function makeRandom(seed) {
  let s = seed;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

const C = (hex) => new THREE.Color(hex);
const COLORS = {
  pasta: C('#e6c682'),
  pastaFat: C('#dfb05a'),
  rawYolk: C('#e88a12'),
  silky: C('#e8b23e'),
  scrambled: C('#e9cf7c'),
  poolRaw: C('#e9900f'),
  poolSilky: C('#ecb84a'),
  steam: C('#ffffff'),
  smoke: C('#6d6660'),
};

export class Food {
  constructor(scene, { bundles = 95 } = {}) {
    this.scene = scene;
    this.random = makeRandom(4);
    this.noise = new SimplexNoise({ random: this.random });
    this.root = new THREE.Group();
    scene.add(this.root);
    this._buildPasta(bundles);
    this._buildGuanciale();
    this._buildPools();
    this._buildCurds();
    this._buildToppings();
    this._buildFlames();
    this._buildSteam();
    this.reset();
  }

  reset() {
    this.pastaT = 0;
    this.pasta.visible = false;
    this.curdLevel = -1;
    this.toppings.visible = false;
    this.guanciale.forEach((g) => { g.mesh.position.copy(g.boardPos); g.mesh.scale.setScalar(1); });
  }

  // ---------- spaghetti: bundles dropped one by one onto a growing height map ----------
  _buildPasta(nBundles) {
    const R = PAN.strandR, CELL = 0.0015, GRID = Math.ceil(0.25 / CELL);
    const H = new Float32Array(GRID * GRID).fill(PAN.floorY);
    const cell = (x, z) => [
      Math.min(GRID - 1, Math.max(0, Math.floor((x + 0.125) / CELL))),
      Math.min(GRID - 1, Math.max(0, Math.floor((z + 0.125) / CELL))),
    ];
    const support = (x, z) => { const [i, j] = cell(x, z); return H[i * GRID + j]; };
    this.top = support;

    // Each strand settles on what is already there, bridges over bumps, sags into
    // gaps (bending stiffness), then raises the height map for later strands.
    const settle = (pts) => {
      const s = pts.map((p) => support(p.x, p.z) + R);
      let y = s.slice();
      for (let k = 0; k < 40; k++) {
        for (let i = 1; i < y.length - 1; i++) y[i] = Math.max(s[i], 0.5 * (y[i - 1] + y[i + 1]) - 0.0008);
      }
      for (let k = 0; k < 4; k++) {
        y = y.map((v, i) => (i === 0 || i === y.length - 1) ? v
          : Math.max(s[i] - 0.7 * R, (y[i - 1] + 2 * v + y[i + 1]) / 4));
      }
      const out = pts.map((p, i) => new THREE.Vector3(p.x, y[i], p.z));
      for (let i = 0; i < out.length - 1; i++) {
        for (const t of [0, 0.5]) {
          const q = out[i].clone().lerp(out[i + 1], t);
          const [ci, cj] = cell(q.x, q.z);
          for (const [di, dj] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) {
            const ii = Math.min(GRID - 1, Math.max(0, ci + di)), jj = Math.min(GRID - 1, Math.max(0, cj + dj));
            H[ii * GRID + jj] = Math.max(H[ii * GRID + jj], q.y + R);
          }
        }
      }
      return out;
    };

    const rnd = this.random, STEP = 0.004, PR = PAN.pileR;
    const strands = [];
    for (let b = 0; b < nBundles; b++) {
      // Tossing spreads pasta out: start each bundle at the lowest of a few spots.
      let best = null;
      for (let k = 0; k < 6; k++) {
        const a = rnd() * Math.PI * 2, r0 = PR * 0.85 * Math.pow(rnd(), 0.9);
        const x = r0 * Math.cos(a), z = r0 * Math.sin(a);
        const h = support(x, z) + 0.012 * (r0 / PR) ** 2;
        if (!best || h < best.h) best = { h, x, z };
      }
      let { x, z } = best;
      let heading = rnd() * Math.PI * 2, turn = (rnd() - 0.5) * 0.2;
      const path = [];
      const n = 60 + Math.floor(rnd() * 26);
      for (let i = 0; i < n; i++) {
        turn = 0.93 * turn + (rnd() - 0.5) * 0.12;   // loose loops and S-bends
        heading += turn;
        x += STEP * Math.cos(heading); z += STEP * Math.sin(heading);
        const r = Math.hypot(x, z);
        if (r > PR) {                                  // pan wall: steer back inside
          heading = Math.atan2(-z, -x) + (rnd() - 0.5) * 1.8;
          x *= PR / r; z *= PR / r;
        }
        path.push({ x, z, heading });
      }
      const count = [1, 1, 2, 2, 2, 3][Math.floor(rnd() * 6)];
      const twist0 = rnd() * Math.PI * 2, twistRate = (rnd() < 0.5 ? -1 : 1) * (0.06 + rnd() * 0.1);
      for (let k = 0; k < count; k++) {
        const ring = 2.15 * R * (k - (count - 1) / 2);
        const pts = path.map((p, i) => {
          const off = ring * Math.cos(twist0 + twistRate * i);   // strands swap sides = twist
          return { x: p.x - Math.sin(p.heading) * off, z: p.z + Math.cos(p.heading) * off };
        });
        const cut0 = Math.floor(rnd() * 10), cut1 = Math.floor(rnd() * 10);
        strands.push(settle(pts.slice(cut0, pts.length - cut1)));
      }
    }
    this.strands = strands;

    const geos = strands.map((pts) => {
      const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), pts.length * 2, R, 6, false);
      const shade = 0.92 + rnd() * 0.16;            // strand-to-strand variation
      const col = new Float32Array(g.attributes.position.count * 3).fill(shade);
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
      g.deleteAttribute('uv');
      return g;
    });
    const mat = new THREE.MeshPhysicalMaterial({
      color: COLORS.pasta.clone(), vertexColors: true, roughness: 0.45,
      clearcoat: 0.3, clearcoatRoughness: 0.15, sheen: 0.4, sheenColor: C('#fff2d0'), sheenRoughness: 0.5,
    });
    this.pastaMat = mat;
    const mesh = new THREE.Mesh(mergeGeometries(geos), mat);
    mesh.castShadow = mesh.receiveShadow = true;
    this.pasta = new THREE.Group();
    this.pasta.add(mesh);
    this.root.add(this.pasta);
  }

  // ---------- tofu cubes, browned by a shader (the texture's G channel gives uneven browning) ----------
  _buildGuanciale() {
    const N = 128, data = new Uint8Array(N * N * 4);
    for (let v = 0; v < N; v++) {
      for (let u = 0; u < N; u++) {
        // R = fat mask (wavy layers of fat and meat), G = noise for uneven browning.
        const w = Math.sin((v / N) * Math.PI * 2 * 2.3 + 1.6 * this.noise.noise(u / 18, v / 18));
        const i = (v * N + u) * 4;
        data[i] = w > 0.15 ? 255 : 0;
        data[i + 1] = 128 + 127 * this.noise.noise(u / 22 + 40, v / 22);   // broad patches, not speckle
        data[i + 2] = 0;
        data[i + 3] = 255;
      }
    }
    const tex = new THREE.DataTexture(data, N, N);
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.magFilter = THREE.LinearFilter;
    tex.needsUpdate = true;

    this.gU = {
      uRender: { value: 0 }, uBrown: { value: 0 }, uBurn: { value: 0 },
      // Tofu: pale cream raw, golden as it dries and fries, deep brown crust, black if burnt.
      cMeatRaw: { value: C('#ece3cc') }, cMeatCooked: { value: C('#dcb46a') },
      cFatRaw: { value: C('#f1e9d6') }, cFatCooked: { value: C('#e2bd72') },
      cBrown: { value: C('#b06a2a') }, cBurnt: { value: C('#1b120c') },
    };
    const mat = new THREE.MeshPhysicalMaterial({ map: tex, roughness: 0.5, clearcoat: 0.2 });
    mat.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.gU);
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', `#include <common>
          uniform float uRender, uBrown, uBurn;
          uniform vec3 cMeatRaw, cMeatCooked, cFatRaw, cFatCooked, cBrown, cBurnt;`)
        .replace('#include <map_fragment>', `
          vec4 gTex = texture2D( map, vMapUv );
          float fat = smoothstep( 0.4, 0.6, gTex.r );
          float edge = gTex.g;
          vec3 gcol = mix( mix( cMeatRaw, cMeatCooked, uRender ), mix( cFatRaw, cFatCooked, uRender ), fat );
          float b = clamp( uBrown * ( 0.55 + 0.9 * edge ), 0.0, 1.0 );
          gcol = mix( gcol, cBrown * ( 0.6 + 0.4 * fat ), b * 0.85 );
          gcol = mix( gcol, cBurnt, clamp( uBurn * ( 0.6 + 0.8 * edge ), 0.0, 1.0 ) );
          diffuseColor.rgb = gcol;`)
        .replace('#include <roughnessmap_fragment>', `
          float roughnessFactor = mix( 0.6, 0.22, fat * uRender ) + 0.2 * b * ( 1.0 - fat ) + 0.3 * uBurn;`);
    };

    this.tofuMaterial = mat;

    // 1 cm tofu cubes. Each has a spot on the board, in the pan, on the resting plate
    // and on top of the finished pasta; update() glides them between stages.
    const rnd = this.random;
    this.guanciale = [];
    const N_CUBES = 36;
    for (let i = 0; i < N_CUBES; i++) {
      const sz = 0.0095 + rnd() * 0.0012;
      const g = new THREE.BoxGeometry(sz, sz, sz, 3, 3, 3);
      const pos = g.attributes.position, seed = rnd() * 100;
      for (let k = 0; k < pos.count; k++) {
        const v = new THREE.Vector3().fromBufferAttribute(pos, k);
        const d = this.noise.noise3d(v.x * 400 + seed, v.y * 400, v.z * 400) * 0.0004;
        v.addScaledVector(v.clone().normalize(), d);
        pos.setXYZ(k, v.x, v.y, v.z);
      }
      g.computeVertexNormals();
      const uv = g.attributes.uv, ou = rnd(), ov = rnd();
      for (let k = 0; k < uv.count; k++) uv.setXY(k, uv.getX(k) * 0.4 + ou, uv.getY(k) * 0.4 + ov);
      const mesh = new THREE.Mesh(g, mat);
      mesh.castShadow = mesh.receiveShadow = true;
      const col = i % 9, row = Math.floor(i / 9);
      const boardPos = new THREE.Vector3(SPOTS.tofuBlock.x - 0.04 + col * 0.0102, 0.02 + sz / 2, SPOTS.tofuBlock.z - 0.016 + row * 0.0102);
      const a = rnd() * Math.PI * 2, r = 0.088 * Math.sqrt(rnd());
      const floorPos = new THREE.Vector3(r * Math.cos(a), PAN.floorY + sz / 2, r * Math.sin(a));
      const pa2 = rnd() * Math.PI * 2, pr2 = 0.045 * Math.sqrt(rnd());
      const platePos = new THREE.Vector3(SPOTS.plate.x + pr2 * Math.cos(pa2), 0.0105 + sz / 2 + (i % 3) * 0.004, SPOTS.plate.z + pr2 * Math.sin(pa2));
      const pa = rnd() * Math.PI * 2, pr = PAN.pileR * 0.9 * Math.pow(rnd(), 0.7);
      const px = pr * Math.cos(pa), pz = pr * Math.sin(pa);
      const pilePos = new THREE.Vector3(px, this.top(px, pz) - rnd() * 0.003, pz);
      const spin = rnd() * Math.PI;
      this.guanciale.push({ mesh, boardPos, floorPos, platePos, pilePos, spin,
        tilt: new THREE.Euler((rnd() - 0.5) * 1.4, spin, (rnd() - 0.5) * 1.4) });
      this.root.add(mesh);
    }
  }

  // ---------- liquid pools: rendered fat, then egg sauce ----------
  _buildPools() {
    const circle = (r) => new THREE.CircleGeometry(r, 72).rotateX(-Math.PI / 2);
    // Rendered fat: a thin, clear golden film you mostly see through to the iron.
    // (Plain transparency, not transmission: transmission turned the steam sprites into dark boxes.)
    this.fatPool = new THREE.Mesh(circle(0.1), new THREE.MeshPhysicalMaterial({
      color: C('#c98a2e'), roughness: 0.03, clearcoat: 1, clearcoatRoughness: 0.02,
      transparent: true, opacity: 0, depthWrite: false,
    }));
    this.fatPool.position.y = PAN.floorY + 0.0006;
    this.saucePool = new THREE.Mesh(circle(0.113), new THREE.MeshPhysicalMaterial({
      color: COLORS.poolRaw.clone(), transparent: true, opacity: 0, roughness: 0.12, clearcoat: 0.8,
    }));
    this.saucePool.receiveShadow = true;
    this.root.add(this.fatPool, this.saucePool);

    // Sizzle: tiny bubbles in the fat while the pan is hot.
    this.bubbles = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 8, 6), new THREE.MeshPhysicalMaterial({
      color: C('#f3d9a6'), roughness: 0.02, transparent: true, opacity: 0.28, clearcoat: 1, depthWrite: false,
    }), 110);
    this.bubbleSeeds = Array.from({ length: 110 }, () => {
      const g = this.guanciale[Math.floor(this.random() * this.guanciale.length)];
      const a = this.random() * Math.PI * 2, r = 0.006 + this.random() * 0.008;
      return { g, ox: Math.cos(a) * r, oz: Math.sin(a) * r, phase: this.random(), size: 0.0003 + this.random() * 0.0006 };
    });
    this.root.add(this.bubbles);
  }

  // ---------- scrambled-egg curds ----------
  _buildCurds() {
    const g = new THREE.IcosahedronGeometry(1, 2);
    const pos = g.attributes.position;
    for (let k = 0; k < pos.count; k++) {
      const v = new THREE.Vector3().fromBufferAttribute(pos, k);
      v.multiplyScalar(1 + 0.35 * this.noise.noise3d(v.x * 1.7, v.y * 1.7, v.z * 1.7));
      pos.setXYZ(k, v.x, v.y * 0.55, v.z);
    }
    g.computeVertexNormals();
    const n = 420;
    this.curds = new THREE.InstancedMesh(g, new THREE.MeshPhysicalMaterial({ color: C('#f1d27c'), roughness: 0.8 }), n);
    this.curds.castShadow = true;
    this.curdSeeds = Array.from({ length: n }, () => {
      const s = this.strands[Math.floor(this.random() * this.strands.length)];
      const p = s[Math.floor(this.random() * s.length)];
      return { p, thr: this.random() * 0.6, size: 0.0018 + this.random() * 0.003, rot: this.random() * 6 };
    });
    this.curds.count = 0;
    this.root.add(this.curds);
  }

  // ---------- black pepper and pecorino, added at plating ----------
  _buildToppings() {
    this.toppings = new THREE.Group();
    const scatter = (geo, mat, n, size) => {
      const im = new THREE.InstancedMesh(geo, mat, n), m = new THREE.Matrix4(), q = new THREE.Quaternion();
      for (let i = 0; i < n; i++) {
        const a = this.random() * Math.PI * 2, r = PAN.pileR * Math.pow(this.random(), 0.6);
        const x = r * Math.cos(a), z = r * Math.sin(a);
        q.setFromEuler(new THREE.Euler(this.random() * 6, this.random() * 6, this.random() * 6));
        const s = size[0] + this.random() * (size[1] - size[0]);
        m.compose(new THREE.Vector3(x, this.top(x, z) + 0.0004, z), q, new THREE.Vector3(s, s * 0.6, s * 0.8));
        im.setMatrixAt(i, m);
      }
      this.toppings.add(im);
    };
    scatter(new THREE.IcosahedronGeometry(1, 0), new THREE.MeshStandardMaterial({ color: C('#1c140e'), roughness: 0.55 }), 260, [0.0005, 0.0013]);
    scatter(new THREE.IcosahedronGeometry(1, 1), new THREE.MeshPhysicalMaterial({ color: C('#efe2bd'), roughness: 0.6 }), 220, [0.0003, 0.0008]);
    this.root.add(this.toppings);
  }

  // ---------- gas flame ----------
  _buildFlames() {
    this.flames = new THREE.Group();
    this.flames.position.y = 0.03;
    const outer = new THREE.MeshBasicMaterial({ color: C('#3f78ff'), transparent: true, opacity: 0.75, blending: THREE.AdditiveBlending, depthWrite: false });
    const inner = new THREE.MeshBasicMaterial({ color: C('#bfe0ff'), transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false });
    const cone = new THREE.ConeGeometry(0.0042, 0.016, 8, 1, true).translate(0, 0.008, 0);
    this.flameTongues = [];
    for (let i = 0; i < 28; i++) {
      const a = (i / 28) * Math.PI * 2;
      const pivot = new THREE.Group();
      pivot.position.set(Math.cos(a) * 0.043, 0, Math.sin(a) * 0.043);
      pivot.rotation.set(0, -a, 0);
      const tongue = new THREE.Group();
      tongue.rotation.z = -0.9;                       // lean outward from the burner
      tongue.add(new THREE.Mesh(cone, outer));
      const core = new THREE.Mesh(cone, inner);
      core.scale.set(0.5, 0.45, 0.5);
      tongue.add(core);
      pivot.add(tongue);
      this.flames.add(pivot);
      this.flameTongues.push({ tongue, phase: Math.random() * 10 });
    }
    this.flameLight = new THREE.PointLight(C('#6f9bff'), 0, 0.35, 2);
    this.flameLight.position.y = 0.035;
    this.root.add(this.flames, this.flameLight);
  }

  // ---------- steam and smoke ----------
  _buildSteam() {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const g = c.getContext('2d'), grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, 'rgba(255,255,255,1)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 64, 64);
    const tex = new THREE.CanvasTexture(c);
    this.puffs = Array.from({ length: 34 }, () => {
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0, depthWrite: false }));
      const a = this.random() * Math.PI * 2, r = 0.09 * Math.sqrt(this.random());
      sp.userData = { x: r * Math.cos(a), z: r * Math.sin(a), phase: this.random(), speed: 0.12 + this.random() * 0.1 };
      this.root.add(sp);
      return sp;
    });
  }

  // ---------- per-frame update from simulation state ----------
  // `w` is the scene state from main.js: where the tofu is, whether there's oil, toss jiggle, service.
  update(s, dt, t, w) {
    // Flame follows the knob.
    const heat = s.heat / 3;
    this.flames.visible = s.heat > 0;
    this.flameTongues.forEach(({ tongue, phase }) => {
      const f = 0.85 + 0.15 * Math.sin(t * 23 + phase) + 0.08 * Math.sin(t * 41 + phase * 2);
      tongue.scale.set(0.8 + heat * 0.4, (0.5 + heat * 1.1) * f, 0.8 + heat * 0.4);
    });
    this.flameLight.intensity = heat * 0.12;

    // Tofu: browning uniforms, then glide each cube to its spot for the current stage.
    this.gU.uRender.value = s.render;
    this.gU.uBrown.value = Math.min(1, s.brown);
    this.gU.uBurn.value = s.burn;
    if (s.pastaIn) this.pastaT = Math.min(1, this.pastaT + dt / 1.1);
    const k = ease(this.pastaT);
    const stage = w.tofuStage;
    const key = { cubes: 'boardPos', pan: 'floorPos', plate: 'platePos', pile: 'pilePos' }[stage];
    const follow = 1 - Math.exp(-dt * 6);
    w.tossT = Math.max(0, w.tossT - dt);
    this.guanciale.forEach((g, i) => {
      g.mesh.visible = !!key;
      if (!key) return;
      const target = g[key];
      const jump = stage === 'pan' && w.tossT > 0 ? Math.max(0, Math.sin((w.tossT * 2.5 + i * 0.07) * Math.PI)) * 0.025 : 0;
      g.mesh.position.x += (target.x - g.mesh.position.x) * follow;
      g.mesh.position.z += (target.z - g.mesh.position.z) * follow;
      g.mesh.position.y += (target.y + jump - g.mesh.position.y) * follow;
      if (stage === 'pile') g.mesh.rotation.set(g.tilt.x, g.tilt.y, g.tilt.z);
      else g.mesh.rotation.set(0, stage === 'cubes' ? 0 : g.spin + (w.flips || 0) * 1.57, 0);
    });

    // Oil: a thin clear film on the pan floor once it's poured, mostly soaked up by the pasta.
    this.fatPool.material.opacity = (w.oil ? 0.22 : 0) * (1 - 0.7 * k);

    // Sizzle bubbles around the tofu while the oil is hot.
    const sizzle = stage === 'pan' && w.oil ? smooth(105, 160, s.panTemp) : 0;
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), sc = new THREE.Vector3();
    this.bubbleSeeds.forEach((b, i) => {
      const life = (t * (1.5 + b.size * 900) + b.phase) % 1;
      const size = sizzle > 0 ? b.size * Math.sin(life * Math.PI) * (0.6 + sizzle) : 0;
      v.set(b.g.floorPos.x + b.ox, PAN.floorY + 0.0008, b.g.floorPos.z + b.oz);
      sc.set(size, size * 0.45, size);
      m.compose(v, q, sc);
      this.bubbles.setMatrixAt(i, m);
    });
    this.bubbles.instanceMatrix.needsUpdate = true;
    this.bubbles.visible = sizzle > 0.01;

    // Pasta drops in from above, and leaves the pan once it's plated.
    this.pasta.visible = s.pastaIn && !w.served;
    this.pasta.position.y = (1 - k) * 0.12;

    // Pasta and sauce colour: fat-glossed, then raw yolk, silky, or scrambled.
    const mat = this.pastaMat, pool = this.saucePool.material;
    if (!s.eggsIn) {
      mat.color.copy(COLORS.pasta).lerp(COLORS.pastaFat, s.pastaIn ? 0.5 : 0);
      mat.roughness = 0.42;
      mat.clearcoat = 0.35;
      pool.opacity = 0;
    } else {
      const silk = smooth(0.05, 0.7, s.thicken);
      mat.color.copy(COLORS.rawYolk).lerp(COLORS.silky, silk).lerp(COLORS.scrambled, smooth(0.05, 0.6, s.curds));
      mat.roughness = 0.3 - 0.15 * silk + 0.45 * s.curds;
      mat.clearcoat = 0.9 * (1 - s.curds);
      const level = clamp((1 - s.thicken) * 0.85 + s.fluid * 0.45 - s.curds * 0.6, 0.12, 1);
      pool.color.copy(COLORS.poolRaw).lerp(COLORS.poolSilky, silk);
      pool.opacity = 0.55 + 0.35 * level;
      pool.roughness = 0.08 + 0.4 * s.curds;
      this.saucePool.position.y = PAN.floorY + 0.001 + level * 0.0035;   // stays under most of the pile
    }

    // Curds appear progressively as the egg overheats.
    const curdLevel = Math.round(s.curds * 200) / 200;
    if (curdLevel !== this.curdLevel) {
      this.curdLevel = curdLevel;
      let n = 0;
      this.curdSeeds.forEach((c) => {
        const grow = smooth(c.thr, c.thr + 0.25, s.curds);
        if (grow <= 0) return;
        q.setFromEuler(new THREE.Euler(0, c.rot, 0));
        sc.setScalar(c.size * grow);
        m.compose(v.set(c.p.x, c.p.y + PAN.strandR, c.p.z), q, sc);
        this.curds.setMatrixAt(n++, m);
      });
      this.curds.count = n;
      this.curds.instanceMatrix.needsUpdate = true;
    }

    this.toppings.visible = false;              // toppings now go on the serving bowls (props.js)
    this.saucePool.visible = s.pastaIn && !w.served;
    this.curds.visible = !w.served;

    // Steam from hot food; smoke when the guanciale chars.
    const steam = w.served ? 0 : s.pastaIn ? smooth(55, 90, s.foodTemp) : (stage === 'pan' ? smooth(120, 200, s.panTemp) * 0.35 : 0);
    const smoke = smooth(0.12, 0.5, s.burn);
    this.puffs.forEach((p) => {
      const u = p.userData;
      u.phase = (u.phase + dt * u.speed) % 1;
      p.position.set(u.x + Math.sin(t * 0.7 + u.z * 40) * 0.01, PAN.floorY + 0.02 + u.phase * 0.28, u.z);
      p.scale.setScalar(0.04 + u.phase * 0.16);
      p.material.color.copy(COLORS.steam).lerp(COLORS.smoke, smoke);
      p.material.opacity = Math.sin(u.phase * Math.PI) * (0.16 * steam + 0.4 * smoke);
    });
  }
}
