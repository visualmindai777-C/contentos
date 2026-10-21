// Personajes 3D de dibujo animado, construidos desde cero con three.js (MIT). Sin modelos externos: no hay licencias que revisar.
import * as THREE from "three";

const gradient = new THREE.DataTexture(new Uint8Array([70, 150, 255]), 3, 1, THREE.RedFormat);
gradient.minFilter = gradient.magFilter = THREE.NearestFilter;
gradient.needsUpdate = true;

const toon = (color) => new THREE.MeshToonMaterial({ color, gradientMap: gradient });
const ink = new THREE.MeshBasicMaterial({ color: 0x1b1420, side: THREE.BackSide });

/** Malla con contorno de tinta (casco invertido): da el aspecto de dibujo animado. */
function part(geometry, color, { outline = 1.04, ...place } = {}) {
  const mesh = new THREE.Mesh(geometry, toon(color));
  if (outline) {
    const edge = new THREE.Mesh(geometry, ink);
    edge.scale.setScalar(outline);
    mesh.add(edge);
  }
  if (place.pos) mesh.position.set(...place.pos);
  if (place.scale) mesh.scale.set(...place.scale);
  if (place.rot) mesh.rotation.set(...place.rot);
  return mesh;
}

const sphere = (r = 1) => new THREE.SphereGeometry(r, 36, 24);

const FRUITS = {
  // color, forma (x, y, z), hoja/corona y cara: z de la superficie y altura de los ojos
  strawberry: { color: "#e8344c", scale: [0.92, 1.1, 0.92], face: [0.66, 0.0] },
  mango: { color: "#f7a823", scale: [0.9, 1.08, 0.84], face: [0.62, 0.0] },
  lemon: { color: "#f6e13f", scale: [1.05, 0.84, 0.84], face: [0.56, 0.0] },
  apple: { color: "#d83a3a", scale: [1.0, 0.92, 0.95], face: [0.64, 0.0] },
  grape: { color: "#7b3fa8", scale: [0.95, 1.0, 0.95], face: [0.64, 0.0] },
  banana: { color: "#f9dd4a", scale: [0.6, 1.35, 0.6], face: [0.4, 0.1] },
  broccoli: { color: "#7bbf4a", scale: [0.62, 1.1, 0.62], face: [0.4, -0.15] },
};

function fruitDecor(kind, group, color) {
  const leaf = (x, y, z, rot, size = 1) => part(sphere(0.2 * size), "#3f9b3c", { scale: [1.5, 0.35, 0.7], pos: [x, y, z], rot: [0, 0, rot], outline: 1.08 });
  if (kind === "strawberry") {
    for (let i = 0; i < 6; i++) {
      const a = (i / 6) * Math.PI * 2;
      group.add(part(sphere(0.2), "#3f9b3c", { scale: [1.5, 0.35, 0.7], pos: [Math.cos(a) * 0.3, 0.74, Math.sin(a) * 0.3], rot: [0, -a, Math.cos(a) * 0.5], outline: 1.08 }));
    }
    group.add(part(new THREE.CylinderGeometry(0.04, 0.05, 0.22, 10), "#3f9b3c", { pos: [0, 0.86, 0] }));
    group.add(part(sphere(0.42), color, { scale: [0.75, 1.05, 0.75], pos: [0, -0.62, 0] }));
    for (let i = 0; i < 18; i++) {
      const az = (i / 18) * Math.PI * 2, y = -0.05 - ((i * 7) % 5) * 0.15;
      const r = 0.7 * 0.93 * Math.sqrt(Math.max(0.05, 1 - (y / 0.77) ** 2));
      const x = Math.sin(az) * r, z = Math.cos(az) * r;
      if (z > 0.35 * r) continue; // el frente es la cara
      group.add(part(sphere(0.028), "#ffe79a", { outline: 0, scale: [0.8, 1.3, 0.5], pos: [x * 1.02, y, z * 1.02] }));
    }
  }
  if (kind === "mango") {
    group.add(leaf(0.18, 0.84, 0, -0.5, 1.4));
    group.add(part(sphere(0.16), "#ee6a2c", { scale: [1, 1.6, 0.35], pos: [-0.5, 0.32, 0.38], outline: 0 }));
  }
  if (kind === "lemon") {
    group.add(part(sphere(0.1), color, { pos: [0.62, 0.02, 0], scale: [1.2, 0.8, 0.8] }));
    group.add(part(sphere(0.1), color, { pos: [-0.62, 0.02, 0], scale: [1.2, 0.8, 0.8] }));
    group.add(leaf(0.1, 0.62, 0, -0.4));
  }
  if (kind === "apple") {
    group.add(part(new THREE.CylinderGeometry(0.035, 0.04, 0.2, 8), "#6b4423", { pos: [0, 0.66, 0], rot: [0, 0, 0.2] }));
    group.add(leaf(0.18, 0.7, 0, -0.45));
  }
  if (kind === "grape") {
    for (const [x, y, z] of [[-0.4, 0.5, -0.1], [0.4, 0.5, -0.1], [-0.55, 0.15, -0.3], [0.55, 0.15, -0.3], [0, 0.7, -0.15]])
      group.add(part(sphere(0.3), "#8a4cbd", { pos: [x, y, z] }));
    group.add(part(new THREE.CylinderGeometry(0.04, 0.05, 0.3, 8), "#6b8f3a", { pos: [0, 1.02, -0.1] }));
  }
  if (kind === "banana") {
    group.add(part(new THREE.CylinderGeometry(0.09, 0.12, 0.2, 10), "#8a6a2a", { pos: [0, 0.88, 0] }));
    group.add(part(sphere(0.12), "#5a3f1c", { pos: [0, -0.84, 0] }));
  }
  if (kind === "broccoli") {
    for (const [x, y, z, r] of [[0, 0.8, 0, 0.5], [-0.4, 0.62, 0.05, 0.36], [0.4, 0.62, 0.05, 0.36], [-0.2, 0.95, -0.1, 0.32], [0.2, 0.95, 0.05, 0.32]])
      group.add(part(sphere(r), "#2f8a3a", { pos: [x, y, z] }));
  }
}

function buildFruit(spec) {
  const def = FRUITS[spec.kind];
  const root = new THREE.Group();
  const body = new THREE.Group();
  root.add(body);
  const head = new THREE.Group();
  body.add(head);
  const color = spec.color ?? def.color;
  head.add(part(sphere(0.7), color, { scale: def.scale }));
  fruitDecor(spec.kind, head, color);

  // Brazos cortos con guantes blancos (dan gesto al personaje)
  for (const side of [-1, 1]) {
    const arm = new THREE.Group();
    arm.position.set(0.78 * side * def.scale[0], -0.2, 0.1);
    arm.rotation.z = side * -0.5;
    arm.add(part(new THREE.CapsuleGeometry(0.07, 0.34, 6, 12), color, { pos: [0, -0.2, 0] }));
    arm.add(part(sphere(0.12), "#ffffff", { pos: [0, -0.46, 0] }));
    head.add(arm);
  }

  const [faceZ, faceY] = def.face;
  const eyes = [];
  for (const side of [-1, 1]) {
    const eye = new THREE.Group();
    eye.position.set(0.22 * side, 0.16 + faceY, faceZ);
    eye.add(part(sphere(0.15), "#ffffff", { scale: [1, 1.2, 0.55], outline: 1.1 }));
    const pupil = part(sphere(0.085), "#1d1218", { outline: 0, pos: [0, 0, 0.07] });
    eye.add(pupil);
    eye.add(part(sphere(0.025), "#ffffff", { outline: 0, pos: [0.03, 0.035, 0.125] }));
    head.add(eye);
    eyes.push({ eye, pupil });
  }
  const brows = [];
  for (const side of [-1, 1]) {
    const brow = part(new THREE.BoxGeometry(0.22, 0.05, 0.05), "#3a2418", { outline: 1.15 });
    brow.position.set(0.22 * side, 0.42 + faceY, faceZ + 0.02);
    head.add(brow);
    brows.push({ brow, side, base: 0.42 + faceY });
  }
  for (const side of [-1, 1]) head.add(part(sphere(0.08), "#ff8da1", { pos: [0.4 * side, -0.02 + faceY, faceZ - 0.04], scale: [1.2, 0.7, 0.3], outline: 0 }));
  const mouth = new THREE.Group();
  mouth.position.set(0, -0.22 + faceY, faceZ + 0.01);
  mouth.userData.baseY = -0.22 + faceY;
  const cavity = part(sphere(0.14), "#5a1620", { outline: 1.12, scale: [1, 0.2, 0.3] });
  const teeth = part(new THREE.BoxGeometry(0.18, 0.035, 0.03), "#fbf7f0", { outline: 0, pos: [0, 0.035, 0.035] });
  mouth.add(cavity, teeth);
  head.add(mouth);

  root.userData = { body, head, eyes, brows, mouth, cavity, teeth, focusY: -0.05, distance: 6.4, baseBrow: true };
  return root;
}

export function buildCharacter(spec) {
  if (spec.kind && FRUITS[spec.kind]) return buildFruit(spec);
  const root = new THREE.Group();
  const body = new THREE.Group();
  root.add(body);
  const female = spec.gender === "f";

  // Torso, cuello y cabeza
  body.add(part(sphere(1), spec.clothes, { pos: [0, -1.62, 0], scale: [female ? 0.74 : 0.9, 0.62, 0.5] }));
  body.add(part(new THREE.CylinderGeometry(female ? 0.42 : 0.5, female ? 0.62 : 0.74, 0.8, 28), spec.clothes, { pos: [0, -1.3, 0], scale: [1, 1, 0.62], outline: 1.03 }));
  if (spec.tie) body.add(part(new THREE.BoxGeometry(0.1, 0.62, 0.05), "#8b1c2b", { outline: 1.1, pos: [0, -1.18, 0.55] }));
  if (spec.tie) body.add(part(new THREE.BoxGeometry(0.36, 0.2, 0.06), "#f1efe8", { outline: 1.08, pos: [0, -0.88, 0.5] }));
  body.add(part(new THREE.CylinderGeometry(0.2, 0.24, 0.4, 20), spec.skin, { pos: [0, -0.7, 0] }));

  const head = new THREE.Group();
  body.add(head);
  head.add(part(sphere(0.64), spec.skin, { scale: [1, 1.08, 0.98] }));
  for (const side of [-1, 1]) head.add(part(sphere(0.12), spec.skin, { pos: [0.63 * side, 0, 0], scale: [0.6, 1, 0.8] }));

  // Ojos con parpadeo
  const eyes = [];
  for (const side of [-1, 1]) {
    const eye = new THREE.Group();
    eye.position.set(0.24 * side, 0.02, 0.56);
    eye.add(part(sphere(0.105), "#ffffff", { scale: [1, 1.2, 0.55], outline: 1.1 }));
    const pupil = part(sphere(0.058), "#1d1218", { outline: 0, pos: [0, 0, 0.05] });
    eye.add(pupil);
    eye.add(part(sphere(0.018), "#ffffff", { outline: 0, pos: [0.02, 0.025, 0.085] }));
    head.add(eye);
    eyes.push({ eye, pupil });
  }

  // Cejas
  const brows = [];
  for (const side of [-1, 1]) {
    const brow = part(new THREE.BoxGeometry(0.24, 0.055, 0.05), spec.style === "bald" ? spec.skin : spec.hair, { outline: 1.15 });
    brow.position.set(0.24 * side, 0.2, 0.585);
    head.add(brow);
    brows.push({ brow, side, base: 0.2 });
  }

  head.add(part(sphere(0.065), spec.skin, { pos: [0, -0.12, 0.645], scale: [1, 0.9, 0.9], outline: 1.15 }));
  for (const side of [-1, 1]) head.add(part(sphere(0.07), "#e08a7a", { pos: [0.34 * side, -0.14, 0.52], scale: [1.2, 0.7, 0.3], outline: 0 }));

  // Boca: abertura (jaw) y anchura (wide)
  const mouth = new THREE.Group();
  mouth.position.set(0, -0.36, 0.575);
  const cavity = part(sphere(0.13), "#5a1620", { outline: 1.12, scale: [1, 0.2, 0.3] });
  const teeth = part(new THREE.BoxGeometry(0.17, 0.035, 0.03), "#fbf7f0", { outline: 0, pos: [0, 0.035, 0.035] });
  mouth.add(cavity, teeth);
  head.add(mouth);
  if (spec.beard) head.add(part(sphere(0.65), spec.hair, { scale: [1, 1.05, 1], pos: [0, -0.07, 0.01] }));

  // Pelo
  const hair = spec.hair;
  const cap = (extra = 0) => new THREE.SphereGeometry(0.67 + extra, 40, 24, 0, Math.PI * 2, 0, Math.PI * 0.37);
  if (spec.style !== "bald") {
    head.add(part(cap(), hair, { scale: [1.03, 1.12, 1.02], pos: [0, 0.05, -0.05], rot: [-0.3, 0, 0] }));
  }
  if (spec.style === "long") {
    head.add(part(sphere(0.7), hair, { scale: [0.95, 1.3, 0.5], pos: [0, -0.42, -0.34] }));
    for (const side of [-1, 1]) head.add(part(sphere(0.2), hair, { scale: [0.6, 2.4, 0.9], pos: [0.62 * side, -0.32, -0.02] }));
  }
  if (spec.style === "bun") head.add(part(sphere(0.22), hair, { pos: [0, 0.78, -0.3] }));
  if (spec.style === "slick") head.add(part(cap(0.012), "#b9b9c2", { scale: [1.03, 1.12, 1.02], pos: [0.03, 0.07, -0.04], rot: [-0.5, 0, 0], outline: 0 }));

  root.userData = { body, head, eyes, brows, mouth, cavity, teeth };
  return root;
}

export function createStage({ width, height, characters }) {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(width, height, false);
  renderer.setPixelRatio(1);
  renderer.setClearColor(0x000000, 0);
  document.body.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8fa0b8, 1.15));
  const key = new THREE.DirectionalLight(0xfff3e0, 1.7);
  key.position.set(2.5, 3, 5);
  scene.add(key);

  const camera = new THREE.PerspectiveCamera(30, width / height, 0.1, 50);
  const group = {};
  for (const [name, spec] of Object.entries(characters)) {
    group[name] = buildCharacter(spec);
    group[name].visible = false;
    scene.add(group[name]);
  }

  function apply(frame) {
    for (const [name, obj] of Object.entries(group)) obj.visible = name === frame.char;
    const obj = group[frame.char];
    if (!obj) return;
    const { body, head, eyes, brows, mouth, cavity, teeth } = obj.userData;
    body.position.y = frame.bob ?? 0;
    head.rotation.set(frame.pitch ?? 0, frame.yaw ?? 0, frame.roll ?? 0);
    const jaw = Math.max(0, Math.min(1, frame.jaw ?? 0));
    const wide = Math.max(0, Math.min(1, frame.wide ?? 0.5));
    cavity.scale.set(1 + (wide - 0.5) * 0.9, 0.2 + jaw * 1.35, 0.3 + jaw * 0.4);
    teeth.visible = jaw > 0.18;
    mouth.position.y = (mouth.userData.baseY ?? -0.36) - jaw * 0.04;
    const open = 1 - Math.max(0, Math.min(1, frame.blink ?? 0));
    for (const { eye, pupil } of eyes) {
      eye.scale.y = 0.12 + 0.88 * open;
      pupil.position.x = (frame.lookX ?? 0) * 0.05;
    }
    for (const { brow, side, base } of brows) {
      brow.position.y = base + (frame.brow ?? 0) * 0.07;
      brow.rotation.z = side * -((frame.brow ?? 0) * 0.18);
    }
    const focus = obj.userData.focusY ?? -0.5;
    const distance = (obj.userData.distance ?? 6.2) / (frame.zoom ?? 1);
    camera.position.set(0, focus + 0.15, distance);
    camera.lookAt(0, focus, 0);
    renderer.render(scene, camera);
  }

  window.applyFrame = apply;
  window.stageReady = true;
  return { renderer, apply };
}
