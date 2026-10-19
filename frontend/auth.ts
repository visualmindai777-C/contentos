const encoder = new TextEncoder();

const sha256 = async (value: string) => new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(value)));

/** Comparación en tiempo constante: se comparan hashes (misma longitud siempre), sin cortocircuito. */
function sameBytes(a: Uint8Array, b: Uint8Array): boolean {
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.min(a.length, b.length); i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

/** Valida una cabecera `Authorization: Basic …` contra usuario y contraseña esperados. */
export async function basicAuthOk(header: string | null, user: string, password: string): Promise<boolean> {
  if (!header?.startsWith("Basic ")) return false;
  let decoded: string;
  try {
    // atob devuelve bytes como caracteres Latin-1; los navegadores envían las credenciales en UTF-8
    decoded = new TextDecoder().decode(Uint8Array.from(atob(header.slice(6).trim()), (c) => c.charCodeAt(0)));
  } catch {
    return false;
  }
  const split = decoded.indexOf(":");
  if (split < 0) return false;
  const [userOk, passOk] = await Promise.all([
    sameHash(decoded.slice(0, split), user),
    sameHash(decoded.slice(split + 1), password),
  ]);
  return userOk && passOk;
}

async function sameHash(given: string, expected: string): Promise<boolean> {
  return sameBytes(await sha256(given), await sha256(expected));
}
