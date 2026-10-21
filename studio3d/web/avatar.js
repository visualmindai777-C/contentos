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

export function buildCharacter(spec) {
  const root = new THREE.Group();
  const body = new THREE.Group();
  root.add(body);
  const female = spec.gender === "f";

  // Torso, cuello y cabeza
  body.add(part(sphere(1), spec.clothes, { pos: [0, -1.55, 0], scale: [female ? 0.82 : 0.98, 0.78, 0.6] }));
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
    eye.position.set(0.23 * side, 0.1, 0.55);
    eye.add(part(sphere(0.14), "#ffffff", { scale: [1, 1.18, 0.55], outline: 1.1 }));
    const pupil = part(sphere(0.075), "#1d1218", { outline: 0, pos: [0, 0, 0.07] });
    eye.add(pupil);
    eye.add(part(sphere(0.022), "#ffffff", { outline: 0, pos: [0.025, 0.03, 0.12] }));
    head.add(eye);
    eyes.push({ eye, pupil });
  }

  // Cejas
  const brows = [];
  for (const side of [-1, 1]) {
    const brow = part(new THREE.BoxGeometry(0.24, 0.055, 0.05), spec.style === "bald" ? spec.skin : spec.hair, { outline: 1.15 });
    brow.position.set(0.23 * side, 0.34, 0.56);
    head.add(brow);
    brows.push({ brow, side });
  }

  head.add(part(sphere(0.07), spec.skin, { pos: [0, -0.04, 0.64], scale: [1, 0.9, 0.9], outline: 1.15 }));

  // Boca: abertura (jaw) y anchura (wide)
  const mouth = new THREE.Group();
  mouth.position.set(0, -0.3, 0.57);
  const cavity = part(sphere(0.13), "#5a1620", { outline: 1.12, scale: [1, 0.2, 0.3] });
  const teeth = part(new THREE.BoxGeometry(0.17, 0.035, 0.03), "#fbf7f0", { outline: 0, pos: [0, 0.035, 0.035] });
  mouth.add(cavity, teeth);
  head.add(mouth);
  if (spec.beard) head.add(part(sphere(0.65), spec.hair, { scale: [1, 1.05, 1], pos: [0, -0.07, 0.01] }));

  // Pelo
  const hair = spec.hair;
  const cap = (extra = 0) => new THREE.SphereGeometry(0.67 + extra, 40, 24, 0, Math.PI * 2, 0, Math.PI * 0.5);
  if (spec.style !== "bald") {
    head.add(part(cap(), hair, { scale: [1.02, 1.1, 1.0], pos: [0, 0.04, -0.04], rot: [-0.18, 0, 0] }));
  }
  if (spec.style === "long") {
    head.add(part(sphere(0.7), hair, { scale: [0.95, 1.35, 0.55], pos: [0, -0.5, -0.32] }));
    for (const side of [-1, 1]) head.add(part(sphere(0.2), hair, { scale: [0.7, 2.2, 0.8], pos: [0.62 * side, -0.35, 0.0] }));
  }
  if (spec.style === "bun") head.add(part(sphere(0.22), hair, { pos: [0, 0.78, -0.3] }));
  if (spec.style === "slick") head.add(part(cap(0.01), "#b9b9c2", { scale: [1.02, 1.1, 1.0], pos: [0.02, 0.07, -0.02], rot: [-0.42, 0, 0], outline: 0 }));

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
    mouth.position.y = -0.3 - jaw * 0.04;
    const open = 1 - Math.max(0, Math.min(1, frame.blink ?? 0));
    for (const { eye, pupil } of eyes) {
      eye.scale.y = 0.12 + 0.88 * open;
      pupil.position.x = (frame.lookX ?? 0) * 0.05;
    }
    for (const { brow, side } of brows) {
      brow.position.y = 0.34 + (frame.brow ?? 0) * 0.07;
      brow.rotation.z = side * -((frame.brow ?? 0) * 0.18);
    }
    const distance = 6.2 / (frame.zoom ?? 1);
    camera.position.set(0, -0.35, distance);
    camera.lookAt(0, -0.55, 0);
    renderer.render(scene, camera);
  }

  window.applyFrame = apply;
  window.stageReady = true;
  return { renderer, apply };
}
