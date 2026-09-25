import pandas as pd
import requests
import time
from pathlib import Path

#ORIGINAL FILE - NEVER MODIFIED
INPUT_CSV = Path("../data/raw/all_states_training_centres.csv")

#NEW OUTPUT FILE
OUTPUT_CSV = Path("../data/processed/skill_india_final.csv")


START_ROW = 1

# Delay between Mappls requests
WAIT_SECONDS = 1.1

# Save after every N rows that are actually attempted
SAVE_EVERY = 20

# Mappls API
GEOCODE_URL = "https://search.mappls.com/search/address/geocode"

#HEADER

print("=" * 80)
print("MAPPLS GEOCODING")
print("=" * 80)

print(f"Input  : {INPUT_CSV}")
print(f"Output : {OUTPUT_CSV}")
print(f"Start  : Row {START_ROW}")
print("=" * 80)

#MAPPLS KEY

ACCESS_TOKEN = input("Mappls Static Key: ").strip()

if not ACCESS_TOKEN:
    print("ERROR: No API key entered.")
    raise SystemExit


#CHECK INPUT FILE

if not INPUT_CSV.exists():

    print()
    print("ERROR: Input CSV not found:")
    print(INPUT_CSV)

    raise SystemExit

#LOAD ORIGINAL CSV

print()
print("Loading original CSV...")

original_df = pd.read_csv(
    INPUT_CSV,
    dtype=str,
    keep_default_na=False
)

total_rows = len(original_df)

print(f"Total rows: {total_rows}")

if total_rows == 0:
    print("ERROR: CSV contains no rows.")
    raise SystemExit


#CHECK START ROW

if START_ROW < 1 or START_ROW > total_rows:

    print()
    print("ERROR: START_ROW is outside the CSV range.")
    print(f"START_ROW : {START_ROW}")
    print(f"Total rows: {total_rows}")

    raise SystemExit


#LOAD EXISTING OUTPUT


if OUTPUT_CSV.exists():

    print()
    print("Existing output file found.")
    print("Loading existing output...")

    df = pd.read_csv(
        OUTPUT_CSV,
        dtype=str,
        keep_default_na=False
    )

    if len(df) != total_rows:

        print()
        print("=" * 80)
        print("ERROR: OUTPUT ROW COUNT DOES NOT MATCH INPUT")
        print("=" * 80)

        print(f"Input rows : {total_rows}")
        print(f"Output rows: {len(df)}")

        print()
        print("Do NOT continue with this file.")
        print("Use a fresh output filename or fix the output first.")

        raise SystemExit

    print(f"Existing output contains {len(df)} rows.")

else:

    print()
    print("No existing output found.")
    print("Creating a new output file...")

    # COPY EVERYTHING
    df = original_df.copy()


MAPPLS_COLUMNS = [

    "mappls_eloc",
    "geocode_level"

]

FINAL_COLUMN_ORDER = [

    "state",
    "centre_name",
    "address",
    "email",
    "phone",
    "courses_offered",
    "district",
    "subdistrict",
    "mappls_eloc",
    "geocode_level"

]

# CREATE MAPPLS COLUMNS IF MISSING

for col in MAPPLS_COLUMNS:

    if col not in df.columns:

        df[col] = ""

    else:

        df[col] = df[col].astype(str)

#ENFORCE FINAL COLUMN ORDER (drops anything not in the list,
#but never crashes if the source file is missing a column)

existing_final_columns = [
    col for col in FINAL_COLUMN_ORDER
    if col in df.columns
]

df = df[existing_final_columns]

#INITIAL SAVE

if not OUTPUT_CSV.exists():

    df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig"
    )

    print()
    print("New output file created:")
    print(OUTPUT_CSV)



#CLEAN FUNCTION


def clean(value):

    if value is None:
        return ""

    return str(value).strip()

#BUILD MAPPLS QUERY

def build_query(row):

    centre = clean(
        row.get("centre_name", "")
    )

    address = clean(
        row.get("address", "")
    )

    state = clean(
        row.get("state", "")
    )

    parts = []

    if centre:
        parts.append(centre)

    if address:
        parts.append(address)

    if state:
        parts.append(state)

    parts.append("India")

    return ", ".join(parts)

# MAPPLS GEOCODING

def geocode(query):

    params = {

        "address": query,

        "itemCount": 1,

        "access_token": ACCESS_TOKEN

    }

    try:

        response = requests.get(
            GEOCODE_URL,
            params=params,
            timeout=30
        )

        if response.status_code != 200:

            print(
                f"HTTP ERROR {response.status_code}"
            )

            print(
                response.text[:300]
            )

            return None

        data = response.json()
        result = data.get("copResults")

        if not result:
            return None

        if isinstance(result, list):

            if len(result) == 0:
                return None

            result = result[0]

        if not isinstance(result, dict):
            return None

        return result

    except requests.exceptions.Timeout:

        print("Request timeout.")
        return None

    except requests.exceptions.RequestException as e:

        print(
            f"Request error: {e}"
        )

        return None

    except Exception as e:

        print(
            f"Unexpected error: {e}"
        )

        return None

start_index = START_ROW - 1

attempted = 0
skipped_success = 0
successful = 0
failed = 0


print()
print("=" * 80)
print(
    f"PROCESSING ROW {START_ROW} TO {total_rows}"
)
print("=" * 80)

for index in range(
    start_index,
    total_rows
):

    row_number = index + 1

    if len(df) != total_rows:

        print()
        print("CRITICAL ERROR: ROW COUNT CHANGED!")
        print(f"Expected: {total_rows}")
        print(f"Current : {len(df)}")

        raise SystemExit

    row = df.iloc[index]

    centre = clean(
        row.get(
            "centre_name",
            ""
        )
    )

    address = clean(
        row.get(
            "address",
            ""
        )
    )

    state = clean(
        row.get(
            "state",
            ""
        )
    )

    existing_eloc = clean(
        df.at[
            index,
            "mappls_eloc"
        ]
    )

    if existing_eloc:

        print()
        print("-" * 80)

        print(
            f"ROW {row_number}/{total_rows}"
        )

        print(
            "Already successfully geocoded."
        )

        print(
            f"Centre : {centre}"
        )

        print(
            f"eLoc   : {existing_eloc}"
        )

        print(
            f"Level  : "
            f"{clean(df.at[index, 'geocode_level'])}"
        )

        skipped_success += 1

        continue


    print()
    print("-" * 80)

    print(
        f"ROW {row_number}/{total_rows}"
    )

    print(
        f"Centre : {centre}"
    )

    print(
        f"Address: {address}"
    )

    print(
        f"State  : {state}"
    )

    query = build_query(row)

    print()
    print(
        f"Query: {query}"
    )
    result = geocode(query)

    if result is None:

        print()
        print(
            "STATUS: NOT FOUND"
        )

        failed += 1

    else:
        eloc = clean(
            result.get(
                "eLoc",
                ""
            )
        )

        #GEOCODE LEVEL
        geocode_level = clean(
            result.get(
                "geocodeLevel",
                ""
            )
        )

        df.at[
            index,
            "mappls_eloc"
        ] = eloc

        df.at[
            index,
            "geocode_level"
        ] = geocode_level


        if eloc:

            successful += 1

            print()
            print("SUCCESS")

            print(
                f"eLoc  : {eloc}"
            )

            print(
                f"Level : {geocode_level}"
            )

        else:

            failed += 1

            print()
            print(
                "Mappls returned a result "
                "but no eLoc."
            )

    attempted += 1

    if attempted % SAVE_EVERY == 0:

        print()
        print("=" * 80)
        print("CHECKPOINT SAVING...")
        print("=" * 80)

        # SAFETY CHECK
        if len(df) != total_rows:

            print(
                "CRITICAL ERROR: ROW COUNT CHANGED!"
            )

            raise SystemExit


        df.to_csv(
            OUTPUT_CSV,
            index=False,
            encoding="utf-8-sig"
        )


        print(
            "CHECKPOINT SAVED"
        )

        print(
            f"Rows in output : {len(df)}"
        )

        print(
            f"Rows attempted : {attempted}"
        )

        print(
            f"Current row    : {row_number}"
        )

        print("=" * 80)

    time.sleep(
        WAIT_SECONDS
    )

#FINAL SAFETY CHECK
print()
print("=" * 80)
print("FINAL SAFETY CHECK")
print("=" * 80)


if len(df) != total_rows:

    print(
        "ERROR: Final row count does not match!"
    )

    print(
        f"Original: {total_rows}"
    )

    print(
        f"Output:   {len(df)}"
    )

    raise SystemExit

df.to_csv(
    OUTPUT_CSV,
    index=False,
    encoding="utf-8-sig"
)

print()
print("=" * 80)
print("MAPPLS GEOCODING COMPLETED")
print("=" * 80)

print(
    f"Original rows          : {total_rows}"
)

print(
    f"Output rows            : {len(df)}"
)

print(
    f"Rows attempted         : {attempted}"
)

print(
    f"Successful (has eLoc)  : {successful}"
)

print(
    f"Failed / not found     : {failed}"
)

print(
    f"Already done / skipped : {skipped_success}"
)

print()
print("=" * 80)

print(
    "Original file was NOT modified."
)

print(
    f"Original : {INPUT_CSV}"
)

print(
    f"New file : {OUTPUT_CSV}"
)

print(
    f"Rows     : {len(df)}"
)

print("=" * 80)