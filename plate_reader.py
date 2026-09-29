import cv2
import easyocr
import re
from caleb_db import check_and_log

# Defaults so the database step works even if no plate is found
recognized_plate = ""
recognized_confidence = 0.0

# -----------------------------
# STEP 1: Load image
# -----------------------------

image = cv2.imread("test_images/car3.jpg")

if image is None:
    print("Error: test_images/car3.jpg could not be loaded.")
    exit()

# -----------------------------
# STEP 2: Preprocess full image
# -----------------------------

gray = cv2.cvtColor(
    image,
    cv2.COLOR_BGR2GRAY
)

blurred = cv2.GaussianBlur(
    gray,
    (5, 5),
    0
)

edges = cv2.Canny(
    blurred,
    50,
    150
)

# -----------------------------
# STEP 3: Find contours
# -----------------------------

contours, _ = cv2.findContours(
    edges,
    cv2.RETR_LIST,
    cv2.CHAIN_APPROX_SIMPLE
)

# Sort largest contours first
contours = sorted(
    contours,
    key=cv2.contourArea,
    reverse=True
)

result = image.copy()

plate = None
plate_gray = None
plate_processed = None

# -----------------------------
# STEP 4: Find license plate
# -----------------------------

for contour in contours[:30]:

    perimeter = cv2.arcLength(
        contour,
        True
    )

    approx = cv2.approxPolyDP(
        contour,
        0.02 * perimeter,
        True
    )

    # Look for rectangular shapes
    if len(approx) == 4:

        x, y, w, h = cv2.boundingRect(
            approx
        )

        aspect_ratio = w / float(h)

        # Filter for plate-like dimensions
        if (
            1.5 < aspect_ratio < 4.0
            and w > 200
            and h > 100
        ):

            # Draw rectangle around detected plate
            cv2.rectangle(
                result,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                3
            )

            # Automatically crop the plate
            plate = image[
                y:y + h,
                x:x + w
            ]

            print("\nPlate detected!")
            print("Width:", w)
            print("Height:", h)
            print(
                "Aspect ratio:",
                round(aspect_ratio, 2)
            )

            # -----------------------------
            # STEP 5: Prepare cropped plate
            # -----------------------------

            plate_gray = cv2.cvtColor(
                plate,
                cv2.COLOR_BGR2GRAY
            )

            plate_blurred = cv2.GaussianBlur(
                plate_gray,
                (5, 5),
                0
            )

            _, plate_processed = cv2.threshold(
                plate_blurred,
                0,
                255,
                cv2.THRESH_BINARY
                + cv2.THRESH_OTSU
            )

            break


# -----------------------------
# STEP 6: OCR
# -----------------------------

if plate_gray is not None:

    print("\nStarting OCR...")

    reader = easyocr.Reader(
        ['en']
    )

    # Only allow letters and numbers
    allowed_characters = (
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
    )

    results = reader.readtext(
        plate_gray,
        allowlist=allowed_characters
    )

    # -----------------------------
    # STEP 7: Show raw OCR results
    # -----------------------------

    print("\nRAW OCR RESULTS:")
    print("--------------------")

    for detection in results:

        text = detection[1]
        confidence = detection[2]

        print(
            "Text:",
            text
        )

        print(
            "Confidence:",
            round(confidence, 3)
        )

        print("--------------------")


    # -----------------------------
    # STEP 8: Filter plate candidates
    # -----------------------------

    plate_candidates = []

    for detection in results:

        text = detection[1].upper()
        confidence = detection[2]

        # Remove anything that is not A-Z or 0-9
        cleaned_text = re.sub(
            r"[^A-Z0-9]",
            "",
            text
        )

        # Check candidate rules
        valid_length = (
            5 <= len(cleaned_text) <= 8
        )

        contains_letter = any(
            char.isalpha()
            for char in cleaned_text
        )

        contains_number = any(
            char.isdigit()
            for char in cleaned_text
        )

        good_confidence = (
            confidence >= 0.30
        )

        # Candidate must pass all rules
        if (
            valid_length
            and contains_letter
            and contains_number
            and good_confidence
        ):

            plate_candidates.append(
                (
                    cleaned_text,
                    confidence
                )
            )


    # -----------------------------
    # STEP 9: Select best candidate
    # -----------------------------

    print("\nPLATE CANDIDATES:")
    print("--------------------")

    if len(plate_candidates) > 0:

        for candidate in plate_candidates:

            print(
                candidate[0],
                "- Confidence:",
                round(candidate[1], 3)
            )

        # Select candidate with highest confidence
        best_plate = max(
            plate_candidates,
            key=lambda candidate: candidate[1]
        )

        recognized_plate = best_plate[0]
        recognized_confidence = best_plate[1]

        print("\n==========================")
        print("RECOGNIZED LICENSE PLATE")
        print("==========================")
        print(
            "Plate:",
            recognized_plate
        )
        print(
            "Confidence:",
            round(
                recognized_confidence,
                3
            )
        )
        print("==========================")

    else:

        print(
            "No valid license plate "
            "candidate found."
        )


else:

    print(
        "No suitable license plate detected."
    )


# -----------------------------
# STEP 9.5: Check database and log
# -----------------------------

decision = check_and_log(
    recognized_plate,
    recognized_confidence
)

print("\nACCESS DECISION:", decision["result"].upper())

if decision["result"] == "granted":
    print("Open gate", decision["gate"], "- Lot", decision["lot_code"])
else:
    print("Denied:", decision["reason"], "- start guest/help process")


# -----------------------------
# STEP 10: Display results
# -----------------------------

result_small = cv2.resize(
    result,
    None,
    fx=0.5,
    fy=0.5
)

cv2.imshow(
    "1 - Plate Detection",
    result_small
)

if plate is not None:

    plate_small = cv2.resize(
        plate,
        None,
        fx=0.6,
        fy=0.6
    )

    gray_small = cv2.resize(
        plate_gray,
        None,
        fx=0.6,
        fy=0.6
    )

    processed_small = cv2.resize(
        plate_processed,
        None,
        fx=0.6,
        fy=0.6
    )

    cv2.imshow(
        "2 - Automatically Cropped Plate",
        plate_small
    )

    cv2.imshow(
        "3 - Grayscale Plate",
        gray_small
    )

    cv2.imshow(
        "4 - Otsu Comparison",
        processed_small
    )


cv2.waitKey(0)

cv2.destroyAllWindows()