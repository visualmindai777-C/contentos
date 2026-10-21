// Utilidades de dibujo animado 3D (three.js, MIT): materiales toon, contorno de tinta, texturas procedurales y la cara parlante.
import * as THREE from "three";

export const NEON = "#3DDC84";
export const INK = 0x1b1420;

const gradient = new THREE.DataTexture(new Uint8Array([85, 160, 255]), 3, 1, THREE.RedFormat);
gradient.minFilter = gradient.magFilter = THREE.NearestFilter;
gradient.needsUpdate = true;

const inkMaterial = new THREE.MeshBasicMaterial({ color: INK, side: THREE.BackSide });

export const toon = (color, extra = {}) => new THREE.MeshToonMaterial({ color, gradientMap: gradient, ...extra });
export const flat = (color) => new THREE.MeshBasicMaterial({ color });
export const sphere = (r = 1) => new THREE.SphereGeometry(r, 40, 28);

/** Malla con contorno de tinta (casco invertido). `color` puede ser un color o un material. */
export function part(geometry, color, { outline = 1.04, pos, scale, rot } = {}) {
  const mesh = new THREE.Mesh(geometry, color?.isMaterial ? color : toon(color));
  if (outline) {
    const edge = new THREE.Mesh(geometry, inkMaterial);
    edge.scale.setScalar(outline);
    mesh.add(edge);
  }
  if (pos) mesh.position.set(...pos);
  if (scale) mesh.scale.set(...scale);
  if (rot) mesh.rotation.set(...rot);
  return mesh;
}

export function canvasTexture(width, height, draw, repeatX = 1) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  draw(canvas.getContext("2d"), width, height);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.RepeatWrapping;
  texture.repeat.set(repeatX, 1);
  texture.anisotropy = 4;
  return texture;
}

/** Cuerpo de revolución: `radius(t)` con t de 0 (abajo) a 1 (arriba), altura total 2*half. */
export function lathe(radius, half, steps = 48) {
  const points = [];
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    points.push(new THREE.Vector2(Math.max(0.001, radius(t)), -half + 2 * half * t));
  }
  return new THREE.LatheGeometry(points, 56);
}

/** Tubo curvo (brazos finos, vapor, tallos). */
export function tube(points, radius, color, { outline = 0, segments = 24 } = {}) {
  const curve = new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p)));
  return part(new THREE.TubeGeometry(curve, segments, radius, 10, false), color, { outline });
}

/** Brazo fino que sale del hombro y llega a `hand` (relativo al hombro); el grupo rota para gesticular. */
export function arm(color, from, hand, bend = [0, 0, 0.1], radius = 0.045) {
  const group = new THREE.Group();
  group.position.set(...from);
  const mid = [hand[0] * 0.5 + bend[0], hand[1] * 0.5 + bend[1], hand[2] * 0.5 + bend[2]];
  group.add(tube([[0, 0, 0], mid, hand], radius, color));
  group.add(part(sphere(radius * 1.25), color, { outline: 0, pos: hand }));
  return group;
}

export function legs(color, shoeColor, baseY, spread = 0.2, shoe = 0.2) {
  const group = new THREE.Group();
  for (const side of [-1, 1]) {
    group.add(part(new THREE.CapsuleGeometry(0.06, 0.28, 6, 10), color, { outline: 0, pos: [spread * side, baseY - 0.12, 0] }));
    group.add(part(sphere(shoe), shoeColor, { outline: 1.05, pos: [spread * side * 1.05, baseY - 0.36, 0.08], scale: [1.05, 0.5, 1.2] }));
  }
  return group;
}

/**
 * Cara parlante. Devuelve las piezas que animan las poses (parpadeo, cejas, boca).
 * o: z (superficie), eyeY, eyeX, eyeR, browY, browW, browColor, tilt [izq, der], browLift [izq, der],
 *    mouthY, mouthColor, rest ("smile" | "frown" | "flat" | "smirk"), lashes, narrow (0..1 ojos entrecerrados),
 *    glasses ("round" | "sun"), blush (bool), tear (bool)
 */
export function makeFace(parent, o) {
  const {
    z, eyeY = 0.15, eyeX = 0.22, eyeR = 0.14, browY = 0.38, browW = 0.22, browColor = "#2a1810", tilt = [0, 0], browLift = [0, 0],
    mouthY = -0.2, mouthColor = "#5a1620", rest = "smile", lashes = false, narrow = 1, glasses = null, blush = true, tear = false,
  } = o;
  const eyes = [];
  const brows = [];

  [-1, 1].forEach((side, index) => {
    const eye = new THREE.Group();
    eye.position.set(eyeX * side, eyeY, z);
    eye.add(part(sphere(eyeR), "#ffffff", { scale: [1, 1.18, 0.55], outline: 1.1 }));
    const pupil = part(sphere(eyeR * 0.55), "#1a1115", { outline: 0, pos: [0, -eyeR * 0.05, eyeR * 0.5] });
    eye.add(pupil);
    eye.add(part(sphere(eyeR * 0.17), "#ffffff", { outline: 0, pos: [eyeR * 0.2, eyeR * 0.22, eyeR * 0.88] }));
    if (lashes) {
      for (let k = 0; k < 3; k++) {
        const lash = part(new THREE.BoxGeometry(0.012, eyeR * 0.55, 0.012), "#1a1115", { outline: 0 });
        lash.position.set(side * (eyeR * (0.75 + k * 0.18)), eyeR * (1.05 + k * 0.02), 0.02);
        lash.rotation.z = side * -(0.5 + k * 0.45);
        eye.add(lash);
      }
    }
    parent.add(eye);
    eyes.push({ eye, pupil, narrow });

    const brow = part(new THREE.BoxGeometry(browW, 0.05, 0.05), browColor, { outline: 1.18 });
    brow.position.set(eyeX * side, browY + browLift[index], z + 0.02);
    parent.add(brow);
    brows.push({ brow, side, base: browY + browLift[index], tilt: tilt[index] });
  });

  if (glasses === "round") {
    for (const side of [-1, 1]) {
      const ring = part(new THREE.TorusGeometry(eyeR * 1.32, 0.032, 12, 40), "#2f3a12", { outline: 0, pos: [eyeX * side, eyeY, z + 0.04] });
      parent.add(ring);
    }
    parent.add(part(new THREE.BoxGeometry(eyeX * 2 - eyeR * 2.6, 0.03, 0.03), "#2f3a12", { outline: 0, pos: [0, eyeY + 0.01, z + 0.04] }));
  }
  if (glasses === "sun") {
    const lens = new THREE.Group();
    for (const side of [-1, 1]) {
      lens.add(part(new THREE.BoxGeometry(eyeR * 2.7, eyeR * 1.7, 0.08), "#141418", { outline: 1.06, pos: [eyeX * side, eyeY, z + 0.1] }));
      lens.add(part(new THREE.BoxGeometry(eyeR * 1.0, 0.018, 0.02), flat(NEON), { outline: 0, pos: [eyeX * side - side * eyeR * 0.25, eyeY + eyeR * 0.45, z + 0.15] }));
    }
    lens.add(part(new THREE.BoxGeometry(eyeX * 2 - eyeR * 2.7, 0.03, 0.03), "#141418", { outline: 0, pos: [0, eyeY, z + 0.1] }));
    parent.add(lens);
  }
  if (blush) {
    for (const side of [-1, 1]) {
      parent.add(part(sphere(0.075), "#ff8da1", { outline: 0, pos: [(eyeX + 0.17) * side, mouthY + 0.1, z - 0.03], scale: [1.35, 0.7, 0.3] }));
    }
  }
  if (tear) {
    parent.add(part(sphere(0.05), NEON, { outline: 1.1, pos: [-(eyeX + 0.02), eyeY - eyeR * 1.6, z + 0.03], scale: [0.7, 1.15, 0.6] }));
  }

  // Boca: forma de reposo (sonrisa, ceño, recta) y cavidad que se abre con la voz
  const mouth = new THREE.Group();
  mouth.position.set(0, mouthY, z + 0.01);
  const cavity = part(sphere(0.14), mouthColor, { outline: 1.12, scale: [1, 0.2, 0.3] });
  const teeth = part(new THREE.BoxGeometry(0.18, 0.035, 0.03), "#fbf7f0", { outline: 0, pos: [0, 0.035, 0.035] });
  mouth.add(cavity, teeth);
  const restLine = new THREE.Group();
  if (rest === "flat") restLine.add(part(new THREE.BoxGeometry(0.17, 0.025, 0.02), "#1a1115", { outline: 0, pos: [0, 0, 0.03] }));
  else {
    const arc = part(new THREE.TorusGeometry(0.1, 0.014, 8, 24, Math.PI), "#1a1115", { outline: 0, pos: [0, rest === "frown" ? -0.06 : 0.04, 0.03] });
    arc.rotation.z = rest === "frown" ? 0 : Math.PI;
    if (rest === "smirk") arc.rotation.z = Math.PI + 0.25;
    restLine.add(arc);
  }
  mouth.add(restLine);
  parent.add(mouth);

  return { eyes, brows, mouth, cavity, teeth, restLine, mouthBase: mouthY };
}
