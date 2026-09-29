# CALEB — Camera Assisted License Entry Barrier

Model parking-access gate: a camera reads a license plate, the plate is checked
against a MariaDB database, and the system grants or denies access and picks the
correct lot/gate. Every attempt is logged.

## Files

| File | Purpose |
|---|---|
| `plate_reader.py` | Computer vision + OCR (OpenCV, EasyOCR); calls the database |
| `caleb_db.py` | Database layer — `check_and_log(plate, confidence)` |
| `database/caleb_schema.sql` | Builds the `caleb` database with sample data |
| `test_images/` | Test photos (add `car3.jpg` here) |

## Setup

1. Install MariaDB, then build the database (from the repo root):
   ```
   sudo mariadb < database/caleb_schema.sql
   ```
   Windows/Mac: `mariadb -u root -p < database/caleb_schema.sql`

   ⚠️ This script drops and rebuilds the database — don't run it on a system
   whose logs you want to keep.

2. Install Python packages:
   ```
   pip install -r requirements.txt
   ```
   In GitHub Codespaces (no screen), use `opencv-python-headless` instead of
   `opencv-python`, and replace the `cv2.imshow` calls in STEP 10 with
   `cv2.imwrite`.

3. Run from the repo root:
   ```
   python plate_reader.py
   ```
   To test the database alone: `python caleb_db.py`

## Database design

- `parking_lots` — each lot and the gate number the controller opens
- `vehicles` — registered plates, authorization, assigned lot, user type
- `access_log` — every attempt (including unknown plates), with confidence,
  result, and the reason for any denial

Plates are stored uppercase with no spaces or dashes (e.g. `ABC1234`); both
Python files normalize OCR output to that format before querying.

The app connects as `caleb_app`, which can only read vehicles/lots and add log
entries. Change its password (`change_me`) in both the schema and `caleb_db.py`.

## Useful queries

```sql
-- recent events
SELECT * FROM caleb.access_log ORDER BY log_id DESC LIMIT 20;

-- register a plate
INSERT INTO caleb.vehicles (plate_number, authorized, lot_id, user_type)
VALUES ('ABC1234', TRUE, 2, 'student');
```
