const encoder = new TextEncoder();

function hmacKey(secret: string, usage: ("sign" | "verify")[]): Promise<CryptoKey> {
  return crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, usage);
}

/** Firma idéntica a backend/app/core/signing.py: HMAC-SHA256(secret, "<key>\n<exp>") en hexadecimal. */
export async function sign(secret: string, key: string, exp: number): Promise<string> {
  const mac = await crypto.subtle.sign("HMAC", await hmacKey(secret, ["sign"]), encoder.encode(`${key}\n${exp}`));
  return [...new Uint8Array(mac)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/** Comparación en tiempo constante (crypto.subtle.verify) y rechazo de URLs caducadas. */
export async function verify(secret: string, key: string, exp: number, sig: string, nowSeconds: number): Promise<boolean> {
  if (!Number.isFinite(exp) || exp < nowSeconds || !/^[0-9a-f]{64}$/.test(sig)) return false;
  const bytes = Uint8Array.from(sig.match(/../g)!, (h) => parseInt(h, 16));
  return crypto.subtle.verify("HMAC", await hmacKey(secret, ["verify"]), bytes, encoder.encode(`${key}\n${exp}`));
}
