"""Local pre-login safety readout. Does not access Flow Music or alter the DB."""
from __future__ import annotations
import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import profiles  # noqa: E402

DB = ROOT / "data" / "jobs.db"
LOCK = ROOT / "data" / "mvp" / "generation.lock"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-queued", action="store_true")
    args = parser.parse_args()
    unsafe = False
    print("=== Evydencia / diagnostico previo a segunda conta (OFFLINE) ===")
    print("Bloqueio de geracao:", "EXISTE - pare e revise" if LOCK.exists() else "ausente")
    unsafe |= LOCK.exists()
    if DB.exists():
        try:
            with closing(sqlite3.connect(DB, timeout=5)) as conn:
                conn.row_factory = sqlite3.Row
                check = conn.execute("PRAGMA quick_check").fetchone()[0]
                print("Integridade SQLite:", check)
                if check != "ok":
                    unsafe = True
                columns = {r[1] for r in conn.execute("PRAGMA table_info(jobs)")}
                print("Coluna de perfil normalizada:", "sim" if "account_profile" in columns else "nao - migra no primeiro start")
                if "run_mode" in columns:
                    pending = conn.execute(
                        "SELECT COUNT(*) FROM jobs WHERE run_mode='cli' AND state IN ('submitting','needs_review')"
                    ).fetchone()[0]
                    queued = conn.execute(
                        "SELECT COUNT(*) FROM jobs WHERE run_mode='cli' AND state='queued'"
                    ).fetchone()[0]
                    print("Geracoes pendentes de revisao:", pending)
                    print("Geracoes aprovadas na fila:", queued)
                    unsafe |= pending > 0 or (queued > 0 and not args.allow_queued)
        except sqlite3.Error:
            print("ERRO ao ler banco SQLite; nao alterar ou reiniciar a fila")
            unsafe = True
    else:
        print("SQLite ainda nao criado (primeira inicializacao).")
    for item in profiles.list_profiles():
        balance = item["credits_remaining"] if item["credits_remaining"] is not None else "indisponivel"
        print(f'Perfil={item["profile"]} sessao_arquivo={item["session_present"]} saldo_ultimo={balance} saldo_desatualizado={item["stale"]}')
    print("Nenhum login, refresh de token ou consumo de creditos foi realizado.")
    return 2 if unsafe else 0

if __name__ == "__main__":
    raise SystemExit(main())
