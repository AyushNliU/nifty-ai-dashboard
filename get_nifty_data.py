import requests
from datetime import datetime, timedelta
from io import StringIO
import sys

import pandas as pd
from google.cloud import bigquery


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "amiable-dragon-435412-v4"
DATASET_ID = "nifty_market"
TABLE_ID = "nifty_ohlcv"

TARGET_TRADING_DAYS = 30

NSE_ARCHIVE_URL = (
    "https://nsearchives.nseindia.com/content/indices/"
    "ind_close_all_{date}.csv"
)

IST = "Asia/Kolkata"


# ============================================================
# PRINT HEADER
# ============================================================

print("=" * 70)
print("NIFTY 50 → BIGQUERY DATA PIPELINE")
print("=" * 70)

print(f"Project              : {PROJECT_ID}")
print(f"Dataset              : {DATASET_ID}")
print(f"Table                : {TABLE_ID}")
print(f"Target trading days  : {TARGET_TRADING_DAYS}")

print()


# ============================================================
# 1. CREATE NSE SESSION
# ============================================================

print("=" * 70)
print("STEP 1: CREATE NSE SESSION")
print("=" * 70)

session = requests.Session()

session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
})

print("NSE session created.")
print()


# ============================================================
# 2. DOWNLOAD NIFTY 50 DAILY DATA
# ============================================================

print("=" * 70)
print("STEP 2: DOWNLOAD NIFTY 50 DAILY DATA")
print("=" * 70)

records = []

# Use Indian date because NSE trading dates are Indian dates.
today_ist = datetime.now().date()

current_date = today_ist

calendar_days_checked = 0
archive_files_found = 0

# Search backwards until we have TARGET_TRADING_DAYS records.
while len(records) < TARGET_TRADING_DAYS:

    calendar_days_checked += 1

    date_string = current_date.strftime("%d%m%Y")

    url = NSE_ARCHIVE_URL.format(
        date=date_string
    )

    display_date = current_date.strftime("%d-%m-%Y")

    print("-" * 70)
    print(f"Checking : {display_date}")
    print(f"File    : ind_close_all_{date_string}.csv")
    print(f"URL     : {url}")

    try:

        response = session.get(
            url,
            timeout=30
        )

        print(f"HTTP status : {response.status_code}")

    except requests.RequestException as e:

        print()
        print("NSE request error:")
        print(repr(e))

        current_date -= timedelta(days=1)
        continue

    # --------------------------------------------------------
    # Archive not available
    # --------------------------------------------------------

    if response.status_code != 200:

        print("No archive for this date.")

        current_date -= timedelta(days=1)
        continue

    # --------------------------------------------------------
    # Parse CSV
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            StringIO(response.text)
        )

        print(f"CSV rows : {len(df)}")

    except Exception as e:

        print()
        print("CSV parsing error:")
        print(repr(e))

        current_date -= timedelta(days=1)
        continue

    # --------------------------------------------------------
    # Find NIFTY 50
    # --------------------------------------------------------

    if "Index Name" not in df.columns:

        print("Index Name column missing.")

        current_date -= timedelta(days=1)
        continue

    nifty = df[
        df["Index Name"]
        .astype(str)
        .str.strip()
        .str.upper()
        == "NIFTY 50"
    ].copy()

    if nifty.empty:

        print("NIFTY 50 not found.")

        current_date -= timedelta(days=1)
        continue

    # --------------------------------------------------------
    # Extract record
    # --------------------------------------------------------

    row = nifty.iloc[0]

    try:

        record = {
            "index_date": str(row["Index Date"]).strip(),

            "open": float(
                str(row["Open Index Value"]).replace(",", "")
            ),

            "high": float(
                str(row["High Index Value"]).replace(",", "")
            ),

            "low": float(
                str(row["Low Index Value"]).replace(",", "")
            ),

            "close": float(
                str(row["Closing Index Value"]).replace(",", "")
            ),

            "volume": int(
                float(
                    str(row["Volume"])
                    .replace(",", "")
                    .strip()
                )
            )
        }

    except Exception as e:

        print()
        print("ERROR extracting NIFTY record:")
        print(repr(e))

        current_date -= timedelta(days=1)
        continue

    records.append(record)

    archive_files_found += 1

    print("NIFTY 50 FOUND")

    print(f"Index Date : {record['index_date']}")
    print(f"Open       : {record['open']}")
    print(f"High       : {record['high']}")
    print(f"Low        : {record['low']}")
    print(f"Close      : {record['close']}")
    print(f"Volume     : {record['volume']}")

    # Move backwards one day.
    current_date -= timedelta(days=1)


print()
print("=" * 70)
print("STEP 3: VALIDATE DOWNLOADED DATA")
print("=" * 70)

print(f"Calendar dates checked : {calendar_days_checked}")
print(f"Archive files found    : {archive_files_found}")
print(f"NIFTY records          : {len(records)}")


if len(records) == 0:

    print()
    print("ERROR: No NIFTY records collected.")

    sys.exit(1)


data = pd.DataFrame(records)

print()
print("Raw collected data:")
print(data.to_string(index=False))


# ============================================================
# 4. CLEAN DATA
# ============================================================

print()
print("=" * 70)
print("STEP 4: CLEAN DATA")
print("=" * 70)


# ------------------------------------------------------------
# Parse NSE date correctly
#
# IMPORTANT:
# NSE date is an Indian trading date.
# First localize it to Asia/Kolkata.
# Then convert to UTC.
#
# This prevents:
#
# 28-08-2026
#
# becoming
#
# 2026-08-27 18:30 UTC
# ------------------------------------------------------------

try:

    data["timestamp"] = pd.to_datetime(
        data["index_date"],
        format="%d-%m-%Y"
    )

    data["timestamp"] = (
        data["timestamp"]
        .dt.tz_localize(IST)
        .dt.tz_convert("UTC")
    )

except Exception as e:

    print()
    print("ERROR converting dates:")
    print(repr(e))

    sys.exit(1)


# ------------------------------------------------------------
# Numeric conversion
# ------------------------------------------------------------

for column in [
    "open",
    "high",
    "low",
    "close",
    "volume"
]:

    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )


# ------------------------------------------------------------
# Remove invalid records
# ------------------------------------------------------------

data = data.dropna(
    subset=[
        "timestamp",
        "open",
        "high",
        "low",
        "close"
    ]
)


# ------------------------------------------------------------
# Volume
# ------------------------------------------------------------

data["volume"] = (
    data["volume"]
    .fillna(0)
    .astype("int64")
)


# ------------------------------------------------------------
# Remove duplicate dates
# ------------------------------------------------------------

data = data.drop_duplicates(
    subset=["timestamp"]
)


# ------------------------------------------------------------
# Sort oldest → newest
# ------------------------------------------------------------

data = data.sort_values(
    "timestamp"
).reset_index(drop=True)


print()
print(f"Valid NIFTY records : {len(data)}")

print()
print(data[
    [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]
].to_string(index=False))


if data.empty:

    print()
    print("ERROR: No valid records remain.")

    sys.exit(1)


# ============================================================
# 5. CONNECT TO BIGQUERY
# ============================================================

print()
print("=" * 70)
print("STEP 5: CONNECT TO BIGQUERY")
print("=" * 70)

print("Connecting to BigQuery...")

try:

    client = bigquery.Client(
        project=PROJECT_ID
    )

    print("BigQuery connection successful.")

except Exception as e:

    print()
    print("ERROR connecting to BigQuery:")
    print(repr(e))

    sys.exit(1)


table_ref = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"{TABLE_ID}"
)

print(f"Target table : {table_ref}")


# ============================================================
# 6. VERIFY TABLE
# ============================================================

print()
print("=" * 70)
print("STEP 6: VERIFY BIGQUERY TABLE")
print("=" * 70)

try:

    table = client.get_table(
        table_ref
    )

    print("Table exists.")
    print(f"Current table rows : {table.num_rows}")

except Exception as e:

    print()
    print("ERROR accessing BigQuery table:")
    print(repr(e))

    sys.exit(1)


# ============================================================
# 7. CHECK EXISTING RECORDS
# ============================================================

print()
print("=" * 70)
print("STEP 7: CHECK EXISTING RECORDS")
print("=" * 70)

query = f"""
SELECT timestamp
FROM `{table_ref}`
WHERE timestamp IS NOT NULL
"""

print("Checking existing timestamps...")

try:

    # IMPORTANT:
    # Use db-dtypes package in the YAML so
    # to_dataframe() can correctly handle BigQuery
    # timestamp/date types.

    existing = client.query(
        query
    ).to_dataframe()

except Exception as e:

    print()
    print("ERROR querying BigQuery:")
    print(repr(e))

    sys.exit(1)


if existing.empty:

    existing_timestamps = set()

    print("No existing records found.")

else:

    existing["timestamp"] = pd.to_datetime(
        existing["timestamp"],
        utc=True
    )

    existing_timestamps = set(
        existing["timestamp"]
    )

    print(
        f"Existing timestamps : "
        f"{len(existing_timestamps)}"
    )


# ============================================================
# 8. REMOVE DUPLICATES
# ============================================================

print()
print("=" * 70)
print("STEP 8: REMOVE DUPLICATES")
print("=" * 70)

before_count = len(data)

data = data[
    ~data["timestamp"].isin(
        existing_timestamps
    )
].copy()

new_count = len(data)

print(f"Downloaded records : {before_count}")
print(f"Already in table   : {before_count - new_count}")
print(f"New records        : {new_count}")


if data.empty:

    print()
    print("No new records to upload.")
    print("BigQuery is already up to date.")

    sys.exit(0)


# ============================================================
# 9. PREPARE UPLOAD DATA
# ============================================================

print()
print("=" * 70)
print("STEP 9: PREPARE BIGQUERY UPLOAD")
print("=" * 70)

upload_data = data[
    [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]
].copy()


print()
print("Records ready for upload:")
print(
    upload_data.to_string(index=False)
)


# ============================================================
# 10. UPLOAD TO BIGQUERY
# ============================================================

print()
print("=" * 70)
print("STEP 10: UPLOAD TO BIGQUERY")
print("=" * 70)

job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_APPEND"
)

try:

    job = client.load_table_from_dataframe(
        upload_data,
        table_ref,
        job_config=job_config
    )

    print(f"BigQuery job ID : {job.job_id}")

    job.result()

    print("Upload completed.")

except Exception as e:

    print()
    print("ERROR uploading to BigQuery:")
    print(repr(e))

    sys.exit(1)


# ============================================================
# 11. VERIFY UPLOAD
# ============================================================

print()
print("=" * 70)
print("STEP 11: VERIFY UPLOAD")
print("=" * 70)

try:

    table = client.get_table(
        table_ref
    )

except Exception as e:

    print()
    print("ERROR verifying table:")
    print(repr(e))

    sys.exit(1)


print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print(f"Uploaded rows : {len(upload_data)}")
print(f"Table rows    : {table.num_rows}")

print()
print("Latest records:")

print(
    upload_data
    .sort_values("timestamp")
    .tail(10)
    .to_string(index=False)
)

print()
print("=" * 70)
print("NIFTY DATA PIPELINE COMPLETED SUCCESSFULLY")
print("=" * 70)
