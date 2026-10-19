import assert from "node:assert/strict";
import { test } from "node:test";
import { sign, verify } from "./signing.ts";

// Mismo vector que backend/tests/test_signing.py: Python firma, el Worker verifica.
const [SECRET, KEY, EXP, SIG] = ["s3cret", "contents/abc/video.mp4", 1_700_000_000, "80b226bf9e5c1af0e7412ac4b9caf2e58401d5af7d9948ceab3ae56417cd71eb"] as const;

test("firma compatible con la del backend en Python", async () => {
  assert.equal(await sign(SECRET, KEY, EXP), SIG);
});

test("verify acepta la firma vigente", async () => {
  assert.equal(await verify(SECRET, KEY, EXP, SIG, EXP - 10), true);
});

test("verify rechaza caducadas, manipuladas, otra clave y firmas mal formadas", async () => {
  assert.equal(await verify(SECRET, KEY, EXP, SIG, EXP + 1), false);
  assert.equal(await verify(SECRET, "contents/otro/video.mp4", EXP, SIG, EXP - 10), false);
  assert.equal(await verify(SECRET, KEY, EXP + 60, SIG, EXP - 10), false);
  assert.equal(await verify("otro-secreto", KEY, EXP, SIG, EXP - 10), false);
  assert.equal(await verify(SECRET, KEY, EXP, "zz", EXP - 10), false);
  assert.equal(await verify(SECRET, KEY, Number.NaN, SIG, EXP - 10), false);
});
