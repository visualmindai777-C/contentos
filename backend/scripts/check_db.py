"""Comprueba si la contraseña de Supabase es correcta, sin guardar nada.

Uso: python check_db.py <ref-del-proyecto> <host-del-pooler>   (pide la contraseña sin mostrarla)
"""

import asyncio
import getpass
import os
import sys

import asyncpg


async def main(ref: str, host: str) -> int:
    password = os.environ.get("DB_PASSWORD") or getpass.getpass("Contraseña de la base: ")
    try:
        conn = await asyncpg.connect(
            user=f"postgres.{ref}", password=password, host=host, port=6543, database="postgres",
            statement_cache_size=0, timeout=20,  # el pooler en modo transacción no admite prepared statements
        )
    except Exception as e:
        print(f"FALLO ({type(e).__name__}): {e}")
        return 1
    print(f"OK: la contraseña es correcta (conectado como {await conn.fetchval('select current_user')})")
    await conn.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2])))
