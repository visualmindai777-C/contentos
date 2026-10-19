import assert from "node:assert/strict";
import { test } from "node:test";
import { basicAuthOk } from "./auth.ts";

const header = (user: string, pass: string) => `Basic ${Buffer.from(`${user}:${pass}`, "utf-8").toString("base64")}`;

test("acepta usuario y contraseña correctos", async () => {
  assert.equal(await basicAuthOk(header("admin", "s3creta-larga"), "admin", "s3creta-larga"), true);
});

test("rechaza contraseña o usuario incorrectos, aunque se parezcan", async () => {
  assert.equal(await basicAuthOk(header("admin", "s3creta-larga "), "admin", "s3creta-larga"), false);
  assert.equal(await basicAuthOk(header("admin", "otra"), "admin", "s3creta-larga"), false);
  assert.equal(await basicAuthOk(header("Admin", "s3creta-larga"), "admin", "s3creta-larga"), false);
});

test("rechaza cabeceras ausentes, de otro esquema o mal formadas", async () => {
  assert.equal(await basicAuthOk(null, "admin", "x"), false);
  assert.equal(await basicAuthOk("Bearer abc", "admin", "x"), false);
  assert.equal(await basicAuthOk("Basic %%%no-es-base64", "admin", "x"), false);
  assert.equal(await basicAuthOk(`Basic ${Buffer.from("sin-dos-puntos").toString("base64")}`, "admin", "x"), false);
});

test("la contraseña puede contener ':' y caracteres no ASCII (UTF-8)", async () => {
  assert.equal(await basicAuthOk(header("admin", "a:b:ñandú-€"), "admin", "a:b:ñandú-€"), true);
  assert.equal(await basicAuthOk(header("admin", "a:b"), "admin", "a:b:ñandú-€"), false);
});
