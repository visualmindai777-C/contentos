import assert from "node:assert/strict";
import { test } from "node:test";
import { COOLDOWN_MS, decide, type Run } from "./decide.ts";

const NOW = Date.parse("2026-10-19T12:00:00Z");
const run = (status: string, conclusion: string | null, minutesAgo = 10): Run => ({
  status,
  conclusion,
  updated_at: new Date(NOW - minutesAgo * 60_000).toISOString(),
  html_url: "https://github.com/x/y/actions/runs/1",
});

test("cola vacía no lanza nada (cero minutos de Actions)", () => {
  assert.deepEqual(decide("queue", 0, [], NOW, 3), { dispatch: false, reason: "cola vacía" });
});

test("cola con contenidos lanza solo la cola, con tope por run", () => {
  assert.deepEqual(decide("queue", 2, [], NOW, 3).inputs, { limit: "2", queue_only: "true" });
  assert.deepEqual(decide("queue", 50, [run("completed", "success")], NOW, 3).inputs, { limit: "3", queue_only: "true" });
});

test("el cron de contenido nuevo lanza en modo completo", () => {
  assert.deepEqual(decide("fresh", 0, [], NOW, 4).inputs, { limit: "4", queue_only: "false" });
});

test("no se solapan runs", () => {
  for (const status of ["queued", "in_progress", "waiting"]) {
    assert.equal(decide("queue", 5, [run(status, null)], NOW, 3).dispatch, false);
    assert.equal(decide("fresh", 0, [run(status, null)], NOW, 3).dispatch, false);
  }
});

test("enfriamiento tras un run rojo, y se levanta pasado el plazo", () => {
  assert.equal(decide("queue", 5, [run("completed", "failure", 30)], NOW, 3).dispatch, false);
  assert.equal(decide("fresh", 0, [run("completed", "timed_out", 30)], NOW, 3).dispatch, false);
  const old = COOLDOWN_MS / 60_000 + 5;
  assert.equal(decide("queue", 5, [run("completed", "failure", old)], NOW, 3).dispatch, true);
});

test("un run cancelado a mano o exitoso no bloquea", () => {
  assert.equal(decide("queue", 1, [run("completed", "cancelled", 1)], NOW, 3).dispatch, true);
  assert.equal(decide("queue", 1, [run("completed", "success", 1)], NOW, 3).dispatch, true);
});
