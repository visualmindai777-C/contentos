// Elenco de "Código Fresa": seis frutas con su cara, accesorios fijos y colores de la hoja de referencia.
import * as THREE from "three";
import { NEON, arm, canvasTexture, flat, legs, lathe, makeFace, part, sphere, toon, tube } from "./toon.js";

/** Cada personaje devuelve un Group con userData: { body, head, eyes, brows, mouth, cavity, teeth, restLine, mouthBase, arms, focusY, distance }. */
function finish(root, head, face, arms, extra) {
  root.userData = { body: root.children[0], head, ...face, arms, ...extra };
  return root;
}

function shieldShape(scale = 1) {
  const s = new THREE.Shape();
  s.moveTo(-0.11 * scale, 0.12 * scale);
  s.lineTo(0.11 * scale, 0.12 * scale);
  s.lineTo(0.11 * scale, -0.03 * scale);
  s.quadraticCurveTo(0.11 * scale, -0.11 * scale, 0, -0.16 * scale);
  s.quadraticCurveTo(-0.11 * scale, -0.11 * scale, -0.11 * scale, -0.03 * scale);
  s.closePath();
  return s;
}

function root() {
  const group = new THREE.Group();
  const body = new THREE.Group();
  group.add(body);
  const head = new THREE.Group();
  body.add(head);
  return { group, body, head };
}

// ---------------------------------------------------------------- 1. Fresa Valentina
function strawberry() {
  const { group, body, head } = root();
  const seeds = canvasTexture(512, 512, (g, w, h) => {
    g.fillStyle = "#E2344B";
    g.fillRect(0, 0, w, h);
    g.fillStyle = "#F7D154";
    const dot = (u, v) => { g.beginPath(); g.ellipse(u * w, v * h, 6, 9, 0, 0, Math.PI * 2); g.fill(); };
    for (let row = 0; row < 5; row++) for (let i = 0; i < 12; i++) dot(((i + (row % 2) * 0.5) / 12) % 1, 0.5 + row * 0.095);
    for (const u of [0.2, 0.3, 0.7, 0.8]) dot(u, 0.35);
  });
  const fruit = part(lathe((t) => 0.78 * Math.sin(Math.PI * Math.pow(t, 1.35)) * (0.9 + 0.1 * t), 0.95), toon("#ffffff", { map: seeds }), { outline: 1.03 });
  fruit.rotation.y = Math.PI;
  head.add(fruit);
  head.add(part(sphere(0.22), "#F0606F", { outline: 0, pos: [-0.42, 0.3, 0.55], scale: [0.9, 1.9, 0.35], rot: [0, 0, 0.35] }));

  // Capucha de hojas con borde festoneado
  head.add(part(new THREE.SphereGeometry(0.82, 56, 28, 0, Math.PI * 2, 0, 1.3), "#2FA65A", { outline: 1.035, pos: [0, 0.22, 0] }));
  for (const a of [-0.62, -0.2, 0.2, 0.62]) head.add(part(sphere(0.17), "#2FA65A", { pos: [Math.sin(a) * 0.76, 0.4, Math.cos(a) * 0.76], scale: [1, 0.8, 0.8] }));
  head.add(part(new THREE.CylinderGeometry(0.085, 0.1, 0.24, 16), "#1E7A42", { pos: [0, 1.12, 0] }));
  head.add(part(sphere(0.2), "#58C985", { outline: 0, pos: [-0.3, 0.88, 0.5], scale: [1.7, 0.22, 0.5], rot: [0, 0, 0.55] }));

  const face = makeFace(head, { z: 0.72, eyeX: 0.2, eyeY: 0.1, eyeR: 0.15, browY: 0.34, browW: 0.26, browColor: "#141418", tilt: [-0.3, 0.3], mouthY: -0.1, rest: "smile" });

  // Laptop con candado neón
  const laptop = new THREE.Group();
  laptop.position.set(0, -0.52, 0.74);
  laptop.rotation.x = -0.12;
  laptop.add(part(new THREE.BoxGeometry(0.7, 0.5, 0.04), flat(NEON), { outline: 0, pos: [0, 0, -0.012] }));
  laptop.add(part(new THREE.BoxGeometry(0.62, 0.42, 0.05), "#2A313B", { outline: 0 }));
  laptop.add(part(new THREE.TorusGeometry(0.05, 0.014, 8, 24, Math.PI), flat(NEON), { outline: 0, pos: [0, 0.05, 0.035] }));
  laptop.add(part(new THREE.BoxGeometry(0.11, 0.08, 0.02), flat(NEON), { outline: 0, pos: [0, -0.02, 0.035] }));
  head.add(laptop);

  const arms = [];
  for (const side of [-1, 1]) {
    const a = arm("#2A1A1F", [0.7 * side, -0.15, 0.25], [-0.36 * side, -0.32, 0.5], [0.12 * side, 0.0, 0.0]);
    head.add(a);
    arms.push({ group: a, base: 0, side });
  }
  body.add(legs("#2A1A1F", "#F2F4F7", -0.95));
  return finish(group, head, face, arms, { focusY: -0.05, distance: 6.4 });
}

// ---------------------------------------------------------------- 2. Piña Maximiliano
function pineapple() {
  const { group, body, head } = root();
  const grid = canvasTexture(512, 512, (g, w, h) => {
    g.fillStyle = "#F4B63C";
    g.fillRect(0, 0, w, h);
    g.strokeStyle = "#C98A1E";
    g.lineWidth = 7;
    for (let i = -10; i <= 10; i++) {
      g.beginPath(); g.moveTo(i * 64, 0); g.lineTo(i * 64 + h, h); g.stroke();
      g.beginPath(); g.moveTo(i * 64 + h, 0); g.lineTo(i * 64, h); g.stroke();
    }
  });
  const fruit = part(sphere(0.8), toon("#ffffff", { map: grid }), { outline: 1.03, scale: [0.95, 1.2, 0.9] });
  fruit.rotation.y = Math.PI;
  head.add(fruit);
  head.add(part(sphere(0.2), "#FFD37A", { outline: 0, pos: [-0.4, 0.4, 0.55], scale: [0.9, 1.7, 0.3], rot: [0, 0, 0.3] }));

  // Corona de hojas rígidas
  const crown = [[0, 0.9, 0.0, 0.2], [-0.3, 0.75, 0.35, 0.16], [0.3, 0.75, -0.35, 0.16], [-0.6, 0.55, 0.7, 0.13], [0.6, 0.55, -0.7, 0.13], [-0.18, 0.7, 0.18, 0.15], [0.18, 0.7, -0.18, 0.15]];
  crown.forEach(([x, h, rz, r], i) => {
    const cone = part(new THREE.ConeGeometry(r, h, 4), i === 0 ? "#4DBB7A" : "#2E8B57", { outline: 1.07 });
    cone.position.set(x * 0.55, 1.0 + h * 0.5 - 0.1, -0.02);
    cone.rotation.z = -rz * 0.55;
    head.add(cone);
  });

  const face = makeFace(head, { z: 0.72, eyeX: 0.2, eyeY: 0.17, eyeR: 0.12, browY: 0.34, browW: 0.26, browColor: "#3A2A14", tilt: [-0.14, 0.14], mouthY: -0.08, rest: "flat", blush: false });

  // Placa de seguridad y walkie-talkie
  const badge = new THREE.Group();
  badge.position.set(0.3, -0.4, 0.68);
  badge.rotation.set(-0.1, 0.25, 0);
  badge.add(part(new THREE.ExtrudeGeometry(shieldShape(1.25), { depth: 0.02, bevelEnabled: false }), flat(NEON), { outline: 0, pos: [0, 0, 0] }));
  badge.add(part(new THREE.ExtrudeGeometry(shieldShape(1.0), { depth: 0.03, bevelEnabled: false }), "#1B2128", { outline: 0, pos: [0, 0, 0.012] }));
  badge.add(part(sphere(0.032), flat(NEON), { outline: 0, pos: [0, 0, 0.05] }));
  head.add(badge);

  const arms = [];
  const left = arm("#3A2A14", [-0.78, -0.05, 0.0], [-0.12, -0.62, 0.15], [-0.12, 0, 0.0]);
  const right = arm("#3A2A14", [0.78, -0.05, 0.0], [0.1, -0.62, 0.2], [0.14, 0, 0.0]);
  const walkie = new THREE.Group();
  walkie.add(part(new THREE.BoxGeometry(0.13, 0.26, 0.08), "#1B2128", { outline: 1.05 }));
  walkie.add(part(new THREE.CylinderGeometry(0.014, 0.014, 0.14, 8), "#1B2128", { outline: 0, pos: [0.04, 0.2, 0] }));
  right.add(walkie);
  walkie.position.set(0.1, -0.7, 0.2);
  head.add(left, right);
  arms.push({ group: left, base: 0, side: -1 }, { group: right, base: 0, side: 1 });
  body.add(legs("#3A2A14", "#1B2128", -0.97, 0.22));
  return finish(group, head, face, arms, { focusY: 0.1, distance: 7.0 });
}

// ---------------------------------------------------------------- 3. Banana Esmeralda
function banana() {
  const { group, body, head } = root();
  const color = "#F6D33C";
  const spine = new THREE.CatmullRomCurve3([[-0.1, -0.95, 0], [0.0, -0.5, 0], [0.1, 0.2, 0], [0.0, 0.8, 0]].map((p) => new THREE.Vector3(...p)));
  head.add(part(new THREE.TubeGeometry(spine, 40, 0.43, 24, false), color, { outline: 1.04 }));
  head.add(part(sphere(0.43), color, { pos: [-0.1, -0.95, 0], outline: 1.04 }));
  head.add(part(new THREE.ConeGeometry(0.4, 0.5, 24), color, { pos: [0.0, 1.05, 0], outline: 1.04 }));
  head.add(part(new THREE.CylinderGeometry(0.09, 0.13, 0.25, 12), "#6B4A1E", { pos: [0.0, 1.38, 0], rot: [0, 0, -0.18] }));
  head.add(part(sphere(0.13), "#6B4A1E", { pos: [-0.1, -1.33, 0] }));
  head.add(part(sphere(0.12), "#FFE98A", { outline: 0, pos: [0.22, 0.2, 0.34], scale: [0.5, 3.2, 0.35] }));

  const face = makeFace(head, { z: 0.43, eyeX: 0.16, eyeY: 0.24, eyeR: 0.1, glasses: "sun", browY: 0.7, browW: 0.001, mouthY: 0.0, rest: "smirk", blush: false });
  face.brows.forEach((b) => (b.brow.visible = false));

  // Bufanda de seda morada
  const scarf = part(new THREE.TorusGeometry(0.44, 0.075, 12, 48), "#6B2D8F", { pos: [0.05, -0.38, 0.0], rot: [Math.PI / 2 + 0.1, 0, 0.12], outline: 1.1 });
  head.add(scarf);
  head.add(part(new THREE.BoxGeometry(0.16, 0.45, 0.045), "#6B2D8F", { outline: 1.08, pos: [0.3, -0.7, 0.4], rot: [0, 0, -0.2] }));

  // Teléfono con borde neón en la mano levantada
  const phone = new THREE.Group();
  phone.add(part(new THREE.BoxGeometry(0.24, 0.38, 0.03), flat(NEON), { outline: 0 }));
  phone.add(part(new THREE.BoxGeometry(0.2, 0.34, 0.04), "#1B2128", { outline: 0 }));
  const raised = arm("#3A2A14", [0.42, -0.1, 0.1], [0.4, 0.45, 0.25], [0.28, 0.1, 0.0]);
  phone.position.set(0.42, 0.62, 0.25);
  raised.add(phone);
  const hip = arm("#3A2A14", [-0.42, -0.1, 0.1], [-0.05, -0.55, 0.25], [-0.2, 0.0, 0.1]);
  head.add(raised, hip);
  body.add(legs("#3A2A14", "#6B2D8F", -1.2, 0.17, 0.17));
  return finish(group, head, face, [{ group: raised, base: 0, side: 1 }, { group: hip, base: 0, side: -1 }], { focusY: 0.1, distance: 7.0 });
}

// ---------------------------------------------------------------- 4. Limón Ricardo
function lemon() {
  const { group, body, head } = root();
  const pores = canvasTexture(256, 256, (g, w, h) => {
    g.fillStyle = "#E6E44A";
    g.fillRect(0, 0, w, h);
    g.fillStyle = "rgba(170,175,40,0.55)";
    for (let i = 0; i < 70; i++) { g.beginPath(); g.arc(((i * 97) % 256), ((i * 53) % 256), 2, 0, Math.PI * 2); g.fill(); }
  });
  const fruit = part(sphere(0.8), toon("#ffffff", { map: pores }), { outline: 1.03, scale: [1.0, 0.95, 0.92] });
  fruit.rotation.y = Math.PI;
  head.add(fruit);
  head.add(part(sphere(0.2), "#F1EE7C", { outline: 0, pos: [-0.4, 0.45, 0.55], scale: [1.3, 0.9, 0.3] }));
  for (const side of [-1, 1]) head.add(part(new THREE.ConeGeometry(0.1, 0.24, 6), "#C9C52E", { outline: 1.08, pos: [0.8 * side, 0.0, 0], rot: [0, 0, -side * Math.PI / 2] }));
  head.add(part(new THREE.ConeGeometry(0.05, 0.2, 8), "#A8B52A", { outline: 1.08, pos: [0, 0.82, 0] }));
  head.add(part(sphere(0.07), "#A8B52A", { pos: [0, 0.94, 0], scale: [1.3, 0.7, 1] }));

  const face = makeFace(head, { z: 0.73, eyeX: 0.2, eyeY: 0.08, eyeR: 0.13, glasses: "round", browY: 0.32, browW: 0.24, browColor: "#2F3A12", tilt: [0.1, -0.2], browLift: [0, 0.07], mouthY: -0.2, rest: "frown", blush: false, tear: true });

  // Taza de té humeante
  const cup = new THREE.Group();
  cup.position.set(0.58, -0.5, 0.48);
  cup.add(part(new THREE.CylinderGeometry(0.11, 0.08, 0.17, 24), "#E8EDF2", { outline: 1.06 }));
  cup.add(part(new THREE.TorusGeometry(0.05, 0.016, 8, 16, Math.PI * 1.4), "#E8EDF2", { outline: 0, pos: [0.12, 0, 0], rot: [0, 0, -0.7] }));
  for (const x of [-0.03, 0.03]) cup.add(tube([[x, 0.12, 0], [x + 0.03, 0.2, 0], [x - 0.02, 0.28, 0], [x + 0.02, 0.36, 0]], 0.009, "#9AA7B4"));
  head.add(cup);

  const left = arm("#2F3A12", [-0.78, -0.1, 0.1], [-0.15, -0.5, 0.3], [-0.2, 0, 0.0]);
  const right = arm("#2F3A12", [0.78, -0.1, 0.1], [-0.2, -0.38, 0.4], [0.15, 0, 0.0]);
  head.add(left, right);
  body.add(legs("#2F3A12", "#E8EDF2", -0.76, 0.22));
  return finish(group, head, face, [{ group: left, base: 0, side: -1 }, { group: right, base: 0, side: 1 }], { focusY: 0.05, distance: 6.6 });
}

// ---------------------------------------------------------------- 5. Doña Sandía
function watermelon() {
  const { group, body, head } = root();
  const stripes = canvasTexture(512, 256, (g, w, h) => {
    g.fillStyle = "#3E9B45";
    g.fillRect(0, 0, w, h);
    g.fillStyle = "#1F5F2A";
    const n = 10;
    for (let i = 0; i < n; i++) {
      const x = ((i + 0.5) / n) * w;
      g.beginPath();
      g.moveTo(x - 4, 0);
      for (let y = 0; y <= h; y += 16) g.lineTo(x - 22 + Math.sin(y * 0.08 + i) * 6 - Math.cos((y / h) * Math.PI) * 0, y);
      for (let y = h; y >= 0; y -= 16) g.lineTo(x + 22 + Math.sin(y * 0.08 + i) * 6, y);
      g.closePath();
      g.fill();
    }
  });
  const fruit = part(sphere(0.95), toon("#ffffff", { map: stripes }), { outline: 1.025, scale: [1.0, 0.92, 0.95] });
  fruit.rotation.y = Math.PI;
  head.add(fruit);
  head.add(part(sphere(0.2), "#5FA845", { outline: 0, pos: [-0.5, 0.5, 0.65], scale: [1.4, 0.8, 0.3] }));
  head.add(tube([[0, 0.86, 0], [0.02, 1.05, 0], [0.12, 1.14, 0], [0.2, 1.1, 0]], 0.04, "#6B4A1E", { outline: 1.4 }));

  const face = makeFace(head, { z: 0.88, eyeX: 0.2, eyeY: 0.12, eyeR: 0.13, narrow: 0.55, lashes: true, browY: 0.34, browW: 0.2, browColor: "#141418", tilt: [0.08, -0.08], mouthY: -0.12, mouthColor: "#C2416B", rest: "smile" });

  head.add(part(new THREE.CylinderGeometry(0.84, 0.95, 0.34, 56, 1, true), toon("#E86A92", { side: THREE.DoubleSide }), { outline: 0, pos: [0, -0.42, 0], rot: [0.04, 0, 0.02] }));
  for (const side of [-1, 1]) head.add(part(sphere(0.07), "#F4EFE6", { pos: [0.93 * side, -0.02, 0.1], outline: 1.1 }));

  const fan = new THREE.Group();
  fan.add(part(sphere(0.3), "#8FD46A", { outline: 1.05, scale: [0.8, 1.2, 0.1] }));
  fan.add(part(new THREE.BoxGeometry(0.02, 0.5, 0.01), "#5FA845", { outline: 0, pos: [0, 0, 0.03] }));
  const raised = arm("#1E3A1E", [0.9, -0.2, 0.2], [0.3, 0.55, 0.35], [0.3, 0.1, 0.0]);
  fan.position.set(0.3, 0.7, 0.35);
  fan.rotation.z = -0.25;
  raised.add(fan);
  const hip = arm("#1E3A1E", [-0.92, -0.2, 0.2], [-0.2, -0.45, 0.35], [-0.25, 0, 0.0]);
  head.add(raised, hip);
  body.add(legs("#1E3A1E", "#C2416B", -0.88, 0.3, 0.24));
  return finish(group, head, face, [{ group: raised, base: 0, side: 1 }, { group: hip, base: 0, side: -1 }], { focusY: 0.0, distance: 7.6 });
}

// ---------------------------------------------------------------- 6. Kiwi
function kiwi() {
  const { group, body, head } = root();
  head.add(part(sphere(0.62), "#8A5A34", { outline: 1.04, scale: [1.05, 0.92, 0.95] }));
  for (let i = 0; i < 26; i++) {
    const a = i * 2.4, b = Math.acos(1 - ((i % 13) + 0.5) / 7);
    const x = Math.sin(b) * Math.cos(a), y = Math.cos(b), z = Math.sin(b) * Math.sin(a);
    if (z > 0.2 && y < 0.5) continue; // sin pelusa sobre la cara
    const hair = part(new THREE.ConeGeometry(0.018, 0.1, 5), "#B58A5C", { outline: 0, pos: [x * 0.66, y * 0.58, z * 0.62] });
    hair.lookAt(x * 2, y * 2, z * 2);
    hair.rotateX(Math.PI / 2);
    head.add(hair);
  }
  const cut = new THREE.Group();
  cut.position.set(0, 0.44, 0.1);
  cut.rotation.x = -0.5;
  cut.add(part(new THREE.CylinderGeometry(0.43, 0.43, 0.05, 40), "#7BC043", { outline: 1.04 }));
  cut.add(part(sphere(0.12), "#E9F5C9", { outline: 0, pos: [0, 0.03, 0], scale: [1.6, 0.3, 1.0] }));
  for (let i = 0; i < 9; i++) {
    const a = (i / 9) * Math.PI * 2;
    cut.add(part(sphere(0.022), "#141418", { outline: 0, pos: [Math.cos(a) * 0.22, 0.035, Math.sin(a) * 0.17], scale: [0.7, 0.4, 1.4] }));
  }
  head.add(cut);

  const face = makeFace(head, { z: 0.58, eyeX: 0.14, eyeY: 0.0, eyeR: 0.085, browY: 0.16, browW: 0.001, mouthY: -0.17, rest: "flat", blush: false });
  face.brows.forEach((b) => (b.brow.visible = false));

  // Credencial de becario con cordón neón
  head.add(tube([[-0.2, -0.1, 0.56], [-0.1, -0.28, 0.6], [0, -0.38, 0.62]], 0.012, flat(NEON)));
  head.add(tube([[0.2, -0.1, 0.56], [0.1, -0.28, 0.6], [0, -0.38, 0.62]], 0.012, flat(NEON)));
  const badge = new THREE.Group();
  badge.position.set(0, -0.5, 0.62);
  badge.add(part(new THREE.BoxGeometry(0.2, 0.14, 0.02), flat(NEON), { outline: 0 }));
  badge.add(part(new THREE.BoxGeometry(0.17, 0.11, 0.025), "#E9F5C9", { outline: 0 }));
  head.add(badge);

  const left = arm("#3A2614", [-0.6, -0.1, 0.1], [-0.1, -0.35, 0.1], [-0.12, 0, 0.0]);
  const right = arm("#3A2614", [0.6, -0.1, 0.1], [0.1, -0.35, 0.1], [0.12, 0, 0.0]);
  head.add(left, right);
  body.add(legs("#3A2614", "#E8EDF2", -0.56, 0.18, 0.2));
  return finish(group, head, face, [{ group: left, base: 0, side: -1 }, { group: right, base: 0, side: 1 }], { focusY: -0.05, distance: 5.0 });
}

export const CAST = { fresa: strawberry, pina: pineapple, banana, limon: lemon, sandia: watermelon, kiwi };
