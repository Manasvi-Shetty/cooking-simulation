// The dining room shown behind the opening (title and Ana's order). Built from simple shapes;
// the page softens it slightly with a CSS blur so it reads as a background, not the stage.
import * as THREE from 'three';

const C = (hex) => new THREE.Color(hex);
const mat = (color, roughness = 0.6, extra = {}) => new THREE.MeshStandardMaterial({ color: C(color), roughness, ...extra });

export function buildRestaurant() {
  const scene = new THREE.Scene();
  scene.background = C('#1a1411');
  scene.fog = new THREE.Fog('#1a1411', 7, 14);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 40);
  const lookAt = new THREE.Vector3(-1.75, 0.95, 0.45);   // Table 6 sits right of centre, clear of Ana's bubble

  scene.add(new THREE.HemisphereLight(C('#ffd9a8'), C('#2a1c14'), 0.55));

  // Room: dark wood floor, deep green walls over a wood wainscot, tall dusk windows.
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 12).rotateX(-Math.PI / 2), mat('#4a2e1e', 0.55));
  floor.receiveShadow = true;
  scene.add(floor);
  const wall = new THREE.Mesh(new THREE.PlaneGeometry(14, 4.2), mat('#2e4639', 0.85));
  wall.position.set(0, 2.1, -4);
  scene.add(wall);
  const side = new THREE.Mesh(new THREE.PlaneGeometry(12, 4.2), mat('#2e4639', 0.85));
  side.rotation.y = Math.PI / 2;
  side.position.set(-5, 2.1, 1);
  scene.add(side);
  const wainscot = new THREE.Mesh(new THREE.BoxGeometry(14, 1.0, 0.06), mat('#5a3a26', 0.5));
  wainscot.position.set(0, 0.5, -3.97);
  scene.add(wainscot);
  for (let i = -2; i <= 2; i++) {
    const glow = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 2.1), new THREE.MeshBasicMaterial({ color: C('#33507e') }));
    glow.position.set(i * 2.4, 2.2, -3.95);   // in front of the frame: no shared depth, no flicker
    scene.add(glow);
    const frame = new THREE.Mesh(new THREE.BoxGeometry(1.2, 2.2, 0.02), mat('#1f1a16', 0.4));
    frame.position.set(i * 2.4, 2.2, -3.985);
    scene.add(frame);
    for (const [w, h, x, y] of [[0.04, 2.1, 0, 0], [1.1, 0.04, 0, 0.3]]) {
      const bar = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.03), mat('#1f1a16', 0.4));
      bar.position.set(i * 2.4 + x, 2.2 + y, -3.92);
      scene.add(bar);
    }
    // Brass wall sconce between windows.
    if (i < 2) {
      const sconce = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 12), new THREE.MeshBasicMaterial({ color: C('#ffd59a') }));
      sconce.position.set(i * 2.4 + 1.2, 1.9, -3.9);
      scene.add(sconce);
      const l = new THREE.PointLight(C('#ffbe73'), 0.9, 3, 2);
      l.position.copy(sconce.position).add(new THREE.Vector3(0, 0, 0.2));
      scene.add(l);
    }
  }

  // Tables with white cloths, bentwood chairs, a candle and two plates each.
  const cloth = mat('#f1ece2', 0.9);
  const wood = mat('#3a2418', 0.5);
  const tables = [[-1.25, 1.0, true], [1.4, 0.6], [-2.6, -1.2], [0.4, -1.6], [2.9, -1.0], [-0.9, -3.0], [2.0, -3.1]];
  tables.forEach(([x, z, ana]) => {
    const t = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.58, 0.74, 40), cloth);
    t.position.set(x, 0.37, z);
    t.castShadow = t.receiveShadow = true;
    scene.add(t);
    const candle = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.1, 12), mat('#f6efe0'));
    candle.position.set(x, 0.79, z);
    scene.add(candle);
    const flame = new THREE.Mesh(new THREE.SphereGeometry(0.016, 10, 8), new THREE.MeshBasicMaterial({ color: C('#ffcf7a') }));
    flame.position.set(x, 0.86, z);
    flame.scale.y = 1.6;
    scene.add(flame);
    const cl = new THREE.PointLight(C('#ffb35c'), 0.5, 1.6, 2);
    cl.position.set(x, 0.95, z);
    scene.add(cl);
    for (const [s, dz] of (ana ? [[0, -1], [1, 0]] : [[-1, 0], [1, 0]])) {
      const dx = s;
      const plate = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.11, 0.015, 32), mat('#ffffff', 0.3));
      plate.position.set(x + dx * 0.26, 0.748, z + dz * 0.26);
      scene.add(plate);
      const chair = new THREE.Group();
      const seat = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 0.04, 24), wood);
      seat.position.y = 0.46;
      const back = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.018, 8, 24, Math.PI), wood);
      back.position.set(0, 0.72, -0.2);
      chair.add(seat, back);
      for (const [lx, lz] of [[-0.15, -0.15], [0.15, -0.15], [-0.15, 0.15], [0.15, 0.15]]) {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.015, 0.015, 0.46, 8), wood);
        leg.position.set(lx, 0.23, lz);
        chair.add(leg);
      }
      chair.position.set(x + dx * 0.75, 0, z + dz * 0.75);
      chair.rotation.y = Math.atan2(-dx, -dz);               // chair back (local -z) away from the table
      chair.traverse((o) => { o.castShadow = true; });
      scene.add(chair);
    }
    if (ana) {
      // Table number card.
      const card = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.07, 0.005), mat('#f6efe0', 0.8));
      card.position.set(x + 0.15, 0.78, z + 0.3);
      card.rotation.x = -0.3;
      scene.add(card);
      // Ana sits behind the table, facing the room; her friend sits at the side.
      scene.add(person({ x, z, dx: 0, dz: -1, top: '#c8892c', hair: '#2b1a12', skin: '#c99b7c', tall: 1 }));
      scene.add(person({ x, z, dx: 1, dz: 0, top: '#3d5470', hair: '#6b4a2e', skin: '#e2b896', tall: 0.97 }));
    }
  });
  // A few other diners further back.
  [[1.4, 0.6, -1, '#7a3b3b'], [0.4, -1.6, 1, '#4a4a4a'], [2.9, -1.0, -1, '#567a5a']]
    .forEach(([x, z, dx, top]) => scene.add(person({ x, z, dx, dz: 0, top, hair: '#241812', skin: '#b98a6a', tall: 1 })));

  // Pendant lamps over the tables.
  tables.forEach(([x, z]) => {
    const cord = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 1.3, 6), mat('#111111'));
    cord.position.set(x, 3.45, z);
    const shade = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.18, 32, 1, true), mat('#b88a3e', 0.35, { metalness: 0.8, side: THREE.DoubleSide }));
    shade.position.set(x, 2.72, z);
    const bulb = new THREE.Mesh(new THREE.SphereGeometry(0.05, 12, 10), new THREE.MeshBasicMaterial({ color: C('#fff1d0') }));
    bulb.position.set(x, 2.64, z);
    const light = new THREE.PointLight(C('#ffcf91'), 2.2, 4.5, 1.6);
    light.position.set(x, 2.5, z);
    scene.add(cord, shade, bulb, light);
  });
  const key = new THREE.SpotLight(C('#ffd7a3'), 30, 9, 0.6, 0.6, 1.6);
  key.position.set(-1.25, 3.2, 2.4);
  key.target.position.set(-1.25, 0.8, 1.0);
  key.castShadow = true;
  scene.add(key, key.target);

  let t = 0;
  return {
    scene,
    camera,
    resize(w, h) { camera.aspect = w / h; camera.fov = w / h < 0.8 ? 60 : 42; camera.updateProjectionMatrix(); },
    update(dt) {
      // Slow, small drift so the room feels alive.
      t += dt;
      camera.position.set(-2.55 + Math.sin(t * 0.12) * 0.12, 1.5 + Math.sin(t * 0.09) * 0.03, 3.5);
      camera.lookAt(lookAt);
    },
  };
}

// A seated diner, kept simple and stylised.
function person({ x, z, dx, dz, top, hair, skin, tall }) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 0.32 * tall, 6, 16), mat(top, 0.8));
  body.position.y = 0.78;
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.11, 24, 18), mat(skin, 0.6));
  head.position.y = 1.16 * tall;
  const hairCap = new THREE.Mesh(new THREE.SphereGeometry(0.118, 24, 18, 0, Math.PI * 2, 0, Math.PI * 0.62), mat(hair, 0.7));
  hairCap.position.y = 1.17 * tall;
  hairCap.rotation.x = -0.25;
  const arm = (s) => {
    const a = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.3, 4, 10), mat(top, 0.8));
    a.position.set(0.17, 0.9, s * 0.17);
    a.rotation.z = 1.05;                                  // shoulder back and up, hand forward on the table
    return a;
  };
  g.add(body, head, hairCap, arm(1), arm(-1));
  g.traverse((o) => { o.castShadow = true; });
  g.position.set(x + dx * 0.75, 0, z + dz * 0.75);
  g.rotation.y = Math.atan2(dz, -dx);                    // local +x points at the table
  return g;
}
