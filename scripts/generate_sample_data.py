"""
Generador de interfaces de ancho fijo SINTÉTICAS (datos 100% ficticios).

Produce dos archivos en data/sample/:
  * SAMPLE01_F20250404.FC  -> interfaz válida (debe pasar todas las expectativas)
  * SAMPLE01_F20250402.FC  -> interfaz con errores inyectados (para ver fallos
                              rojos en Allure)

Ejecutar:  python scripts/generate_sample_data.py
"""
from __future__ import annotations

import random
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "sample"

HEADER_LEN = 401
BODY_LEN = 271
FOOTER_LEN = 401


def _num(value: int, length: int) -> str:
    return str(value).zfill(length)[:length]


def build_header(date: str, process_type: str = "D") -> str:
    line = "HDR" + "SMP" + "ACC" + date + process_type + ("0" * 383)
    assert len(line) == HEADER_LEN, len(line)
    return line


def build_body_row(entry_id: int, amount: int, drcr: str, date: str,
                   month: str = "APR", office: str = "505",
                   currency: str = "999", txn: str = "DLY") -> str:
    line = (
        _num(entry_id, 16)
        + "FY2025   "          # FISCAL_PERIOD (9)
        + month                # PROCESS_MONTH (3)
        + office               # OFFICE_CODE (3)
        + currency             # CURRENCY_CODE (3)
        + _num(amount, 19)     # AMOUNT_LOCAL (19)
        + "000"                # DECIMALS (3)
        + ("0" * 20)           # ACCOUNT (20)
        + txn                  # TXN_CODE (3)
        + drcr                 # DRCR (1)
        + date                 # ACCOUNTING_DATE (8)
        + ("0" * 183)          # FILLER_B (183)
    )
    assert len(line) == BODY_LEN, len(line)
    return line


def build_footer(count: int, sum_dr: int, sum_cr: int) -> str:
    line = "TLR" + _num(count, 13) + _num(sum_dr, 17) + _num(sum_cr, 17) + ("0" * 351)
    assert len(line) == FOOTER_LEN, len(line)
    return line


def _random_rows(n: int, date: str) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "entry_id": i,
            "amount": random.randint(1_000, 5_000_000),
            "drcr": random.choice(["D", "C"]),
            "date": date,
        })
    return rows


def write_interface(path: Path, header: str, body_rows: list[str], footer: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="latin-1", newline="\n") as f:
        f.write(header + "\n")
        for row in body_rows:
            f.write(row + "\n")
        f.write(footer + "\n")
    print(f"  escrito: {path.name}  ({len(body_rows)} filas de detalle)")


def generate_valid(date: str = "20250404", n: int = 8) -> None:
    rows = _random_rows(n, date)
    body = [build_body_row(r["entry_id"], r["amount"], r["drcr"], r["date"]) for r in rows]
    sum_dr = sum(r["amount"] for r in rows if r["drcr"] == "D")
    sum_cr = sum(r["amount"] for r in rows if r["drcr"] == "C")
    header = build_header(date, "D")
    footer = build_footer(len(rows), sum_dr, sum_cr)
    write_interface(DATA_DIR / f"SAMPLE01_F{date}.FC", header, body, footer)


def generate_broken(date: str = "20250402", n: int = 6) -> None:
    """Interfaz con errores deliberados en varias secciones."""
    rows = _random_rows(n, date)
    body = [build_body_row(r["entry_id"], r["amount"], r["drcr"], r["date"]) for r in rows]

    # Error 1 (body, dominio): DRCR inválido en la primera fila.
    body[0] = build_body_row(rows[0]["entry_id"], rows[0]["amount"], "X", date)
    # Error 2 (body, unicidad): ENTRY_ID duplicado en la última fila.
    body[-1] = build_body_row(rows[0]["entry_id"], rows[-1]["amount"], rows[-1]["drcr"], date)

    # Error 3 (header, dominio): PROCESS_TYPE inválido.
    header = build_header(date, "X")

    # Error 4 (cross-section): totales del footer que NO cuadran con el body.
    footer = build_footer(len(rows) + 99, 1, 1)

    write_interface(DATA_DIR / f"SAMPLE01_F{date}.FC", header, body, footer)


# --------------------------------------------------------------------------- #
# SAMPLE02 — Saldos diarios de clientes (estructura distinta, marcadores HDR/EOF)
# --------------------------------------------------------------------------- #
S2_HEADER_LEN = 100
S2_BODY_LEN = 100
S2_FOOTER_LEN = 100

ACCOUNT_TYPES = ["CC", "CA", "PZ"]
CURRENCIES = ["CLP", "USD", "EUR"]


def s2_header(date: str) -> str:
    line = "HDR" + "POS" + date + "D" + ("0" * 85)
    assert len(line) == S2_HEADER_LEN, len(line)
    return line


def s2_body_row(client_id: int, acc_type: str, currency: str, balance: int,
                status: str, open_date: str) -> str:
    line = (
        _num(client_id, 12)    # CLIENT_ID (12)
        + acc_type             # ACCOUNT_TYPE (2)
        + currency             # CURRENCY (3)
        + _num(balance, 18)    # BALANCE (18)
        + status               # STATUS (1)
        + open_date            # OPEN_DATE (8)
        + ("0" * 56)           # FILLER_B (56)
    )
    assert len(line) == S2_BODY_LEN, len(line)
    return line


def s2_footer(count: int, sum_balance: int) -> str:
    line = "EOF" + _num(count, 12) + _num(sum_balance, 20) + ("0" * 65)
    assert len(line) == S2_FOOTER_LEN, len(line)
    return line


def generate_sample02(date: str = "20250404", n: int = 10) -> None:
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "client_id": 100000 + i,
            "acc_type": random.choice(ACCOUNT_TYPES),
            "currency": random.choice(CURRENCIES),
            "balance": random.randint(0, 9_000_000),
            "status": random.choice(["A", "I"]),
            "open_date": "20200115",
        })
    body = [s2_body_row(r["client_id"], r["acc_type"], r["currency"],
                        r["balance"], r["status"], r["open_date"]) for r in rows]
    header = s2_header(date)
    footer = s2_footer(len(rows), sum(r["balance"] for r in rows))
    write_interface(DATA_DIR / f"SAMPLE02_F{date}.FC", header, body, footer)


if __name__ == "__main__":
    print("Generando interfaces sintéticas en data/sample/ ...")
    generate_valid()
    generate_broken()
    generate_sample02()
    print("Listo.")
