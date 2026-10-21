"""Prueba cada modelo gratuito de OpenRouter con una petición real del guionista y dice cuáles sirven.
Uso (con OPENROUTER_API_KEY): python scripts/check_models.py"""
import json
import os
import re
import time

import httpx

KEY = os.environ["OPENROUTER_API_KEY"]
SKIP = ("lyria", "content-safety", "-code", "embed")  # no son modelos de texto para guiones
PROMPT = (
    'Eres guionista de videos cortos. Responde SOLO con un JSON válido con las claves "title", "hook", "script" '
    '(narración de unas 60 palabras en español sobre un hecho curioso de los volcanes), "caption", "hashtags" (lista de 5) y "cta".'
)


def candidates() -> list[dict]:
    data = httpx.get("https://openrouter.ai/api/v1/models", timeout=30).json()["data"]
    free = [m for m in data if m["id"].endswith(":free") or m["id"] == "openrouter/free"]
    free = [m for m in free if not any(s in m["id"] for s in SKIP)]
    return sorted(free, key=lambda m: -(m.get("context_length") or 0))


def probe(model: str) -> dict:
    start = time.time()
    try:
        r = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {KEY}"},
            json={
                "model": model, "max_tokens": 3000, "reasoning": {"effort": "low"},
                "response_format": {"type": "json_object"},
                "messages": [{"role": "user", "content": PROMPT}],
            },
            timeout=120,
        )
    except httpx.HTTPError as e:
        return {"ok": False, "why": f"red: {e!r}"[:80], "s": time.time() - start}
    seconds = time.time() - start
    if r.status_code != 200:
        return {"ok": False, "why": f"HTTP {r.status_code}", "s": seconds}
    body = r.json()
    if "error" in body:
        return {"ok": False, "why": f"error {str(body['error'])[:60]}", "s": seconds}
    choice = body["choices"][0]
    text = (choice["message"].get("content") or "").strip()
    if not text:
        return {"ok": False, "why": f"vacío ({choice.get('finish_reason')})", "s": seconds}
    start_i, end_i = text.find("{"), text.rfind("}")
    try:
        data = json.loads(text[start_i : end_i + 1])
        words = len(str(data.get("script", "")).split())
        return {"ok": words >= 30 and bool(data.get("title")), "why": f"JSON ok, guion de {words} palabras", "s": seconds}
    except ValueError:
        return {"ok": False, "why": "no es JSON", "s": seconds}


working = []
for m in candidates():
    res = probe(m["id"])
    print(f"{'OK ' if res['ok'] else 'NO '} {m['id']:58} {res['s']:5.1f}s  {res['why']}", flush=True)
    if res["ok"]:
        working.append((res["s"], m["id"]))
    time.sleep(2)
print("FUNCIONAN (de más rápido a más lento):", ",".join(i for _, i in sorted(working)))
