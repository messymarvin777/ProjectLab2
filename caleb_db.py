"""
caleb_db.py — database layer for CALEB.
Your groupmate's camera code only needs to call:  check_and_log(plate, confidence)

Install:  pip install pymysql
"""
import re
import pymysql

DB_CONFIG = {
    "host": "localhost",
    "user": "caleb_app",
    "password": "change_me",
    "database": "caleb",
    "autocommit": True,
    "cursorclass": pymysql.cursors.DictCursor,
}

MIN_CONFIDENCE = 0.80  # tune with real OCR results


def normalize_plate(raw: str) -> str:
    """'abc-1234 ' -> 'ABC1234'. Must match how plates are stored."""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


def check_and_log(raw_plate: str, confidence: float | None) -> dict:
    """
    Returns: {"result": "granted"/"denied", "reason": ..., "lot_code": ..., "gate": ...}
    Every call writes exactly one row to access_log.
    """
    plate = normalize_plate(raw_plate)
    decision = {"result": "denied", "reason": None, "lot_id": None,
                "lot_code": None, "gate": None, "plate": plate}

    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            if confidence is not None and confidence < MIN_CONFIDENCE:
                decision["reason"] = "low_confidence"
            else:
                cur.execute(
                    """SELECT v.authorized, v.lot_id, l.lot_code, l.gate_number
                         FROM vehicles v
                         LEFT JOIN parking_lots l ON l.lot_id = v.lot_id
                        WHERE v.plate_number = %s""",
                    (plate,),
                )
                row = cur.fetchone()
                if row is None:
                    decision["reason"] = "not_found"
                elif not row["authorized"]:
                    decision["reason"] = "not_authorized"
                elif row["lot_id"] is None:
                    decision["reason"] = "no_lot"
                else:
                    decision.update(result="granted", lot_id=row["lot_id"],
                                    lot_code=row["lot_code"], gate=row["gate_number"])

            cur.execute(
                """INSERT INTO access_log
                       (plate_read, confidence, result, deny_reason, lot_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (plate or "UNREADABLE", confidence, decision["result"],
                 decision["reason"], decision["lot_id"]),
            )
    finally:
        conn.close()
    return decision


if __name__ == "__main__":
    for p, c in [("abc-1234", 0.95), ("TTU 2026", 0.91), ("BAN0001", 0.97),
                 ("ZZZ9999", 0.93), ("NOLOT01", 0.90), ("RDR5678", 0.42)]:
        print(p, "->", check_and_log(p, c))
