// Personajes 3D de dibujo animado, construidos desde cero con three.js (MIT). Sin modelos externos: no hay licencias que revisar.
import * as THREE from "three";
import { CAST } from "./fruits.js";

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
    brows.push({ brow, side, base: 0.2, tilt: 0 });
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
    group[name] = spec.kind && CAST[spec.kind] ? CAST[spec.kind]() : buildCharacter(spec);
    group[name].visible = false;
    scene.add(group[name]);
  }

  function apply(frame) {
    for (const [name, obj] of Object.entries(group)) obj.visible = name === frame.char;
    const obj = group[frame.char];
    if (!obj) return;
    const { body, head, eyes, brows, mouth, cavity, teeth, restLine, mouthBase, arms } = obj.userData;
    body.position.y = frame.bob ?? 0;
    head.rotation.set(frame.pitch ?? 0, frame.yaw ?? 0, frame.roll ?? 0);

    const jaw = Math.max(0, Math.min(1, frame.jaw ?? 0));
    const wide = Math.max(0, Math.min(1, frame.wide ?? 0.5));
    const speaking = jaw > 0.1;
    cavity.visible = speaking || !restLine;
    teeth.visible = jaw > 0.3;
    if (restLine) restLine.visible = !speaking;
    cavity.scale.set(1 + (wide - 0.5) * 0.9, 0.2 + jaw * 1.35, 0.3 + jaw * 0.4);
    mouth.position.y = (mouthBase ?? -0.36) - jaw * 0.04;

    const open = 1 - Math.max(0, Math.min(1, frame.blink ?? 0));
    for (const { eye, pupil, narrow } of eyes) {
      eye.scale.y = (0.12 + 0.88 * open) * (narrow ?? 1);
      pupil.position.x = (frame.lookX ?? 0) * 0.05;
    }
    for (const { brow, side, base, tilt } of brows) {
      brow.position.y = base + (frame.brow ?? 0) * 0.07;
      brow.rotation.z = (tilt ?? 0) - side * ((frame.brow ?? 0) * 0.18);
    }
    for (const { group: g, base, side } of arms ?? []) g.rotation.z = (base ?? 0) + (frame.gesture ?? 0) * 0.28 * side;

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
