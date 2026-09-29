"""
app.py — simple web dashboard for CALEB.

Run:  streamlit run app.py
(Codespaces will pop up "Open in Browser" — click it.)
"""
import pymysql
import streamlit as st

from caleb_db import DB_CONFIG, MIN_CONFIDENCE, check_and_log

st.set_page_config(page_title="CALEB Gate Console", page_icon="🚗", layout="wide")

REASONS = {
    "not_found": "Plate is not in the database",
    "not_authorized": "Permit is not authorized",
    "no_lot": "No parking lot assigned",
    "low_confidence": "Camera wasn't confident enough in the read",
}


def query(sql):
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


# Stop early with a clear message if the database isn't running
try:
    query("SELECT 1")
except pymysql.err.OperationalError:
    st.error("Can't reach the database. In the terminal, run:  sudo service mariadb start")
    st.stop()

st.title("🚗 CALEB Gate Console")
st.caption("Camera Assisted License Entry Barrier — database test panel")

left, right = st.columns([1, 1.3], gap="large")

# ---------------- Simulated camera read ----------------
with left:
    st.subheader("Simulate a camera read")
    with st.form("scan"):
        plate = st.text_input("Plate as read by the camera", placeholder="e.g. ABC-1234")
        conf = st.slider("OCR confidence", 0.0, 1.0, 0.95, 0.01)
        submitted = st.form_submit_button("Scan plate", type="primary")
    st.caption(
        f"Reads below {MIN_CONFIDENCE:.2f} confidence are denied "
        "before the database is checked."
    )
    if submitted:
        if plate.strip():
            st.session_state.last = check_and_log(plate, conf)
        else:
            st.warning("Enter a plate first.")

# ---------------- Gate decision ----------------
with right:
    st.subheader("Gate decision")
    d = st.session_state.get("last")
    if d is None:
        st.info("No scan yet — enter a plate on the left.")
    elif d["result"] == "granted":
        st.success(
            f"### ✅ ACCESS GRANTED\n\n"
            f"**{d['plate']}** → Lot {d['lot_code']} · open **gate {d['gate']}**"
        )
    else:
        st.error(
            f"### ⛔ ACCESS DENIED\n\n"
            f"**{d['plate'] or 'UNREADABLE'}** — {REASONS.get(d['reason'], d['reason'])}\n\n"
            "Starting guest/help process."
        )

# ---------------- Totals ----------------
st.divider()
stats = query(
    "SELECT COUNT(*) AS total, COALESCE(SUM(result = 'granted'), 0) AS granted "
    "FROM access_log"
)[0]
total, granted = int(stats["total"]), int(stats["granted"])
c1, c2, c3 = st.columns(3)
c1.metric("Total attempts", total)
c2.metric("Granted", granted)
c3.metric("Denied", total - granted)

# ---------------- Tables ----------------
log_tab, veh_tab = st.tabs(["Access log", "Registered vehicles"])

with log_tab:
    rows = query(
        """SELECT a.log_id AS `#`, a.event_time AS `Time (server)`, a.plate_read AS Plate,
                  a.confidence AS Confidence, a.result AS Result,
                  a.deny_reason AS Reason, l.lot_code AS Lot
             FROM access_log a
             LEFT JOIN parking_lots l ON l.lot_id = a.lot_id
            ORDER BY a.log_id DESC
            LIMIT 25"""
    )
    for r in rows:
        if r["Confidence"] is not None:
            r["Confidence"] = float(r["Confidence"])
    if rows:
        st.dataframe(rows, hide_index=True)
        st.caption("Newest 25 attempts. Times are server time (UTC in Codespaces).")
    else:
        st.caption("No attempts logged yet.")

with veh_tab:
    rows = query(
        """SELECT v.plate_number AS Plate,
                  IF(v.authorized, 'Yes', 'No') AS Authorized,
                  v.user_type AS Type,
                  COALESCE(l.lot_code, '—') AS Lot,
                  l.gate_number AS Gate,
                  v.owner_name AS Owner
             FROM vehicles v
             LEFT JOIN parking_lots l ON l.lot_id = v.lot_id
            ORDER BY v.plate_number"""
    )
    st.dataframe(rows, hide_index=True)
    st.caption(
        "To register a plate, use the terminal as root — the app's account can only "
        "read vehicles, on purpose."
    )
