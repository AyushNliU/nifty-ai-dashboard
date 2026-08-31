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

TABLE_REF = (
    f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
)

NSE_ARCHIVE_URL = (
    "https://nsearchives.nseindia.com/content/indices/"
    "ind_close_all_{date}.csv"
)


# ============================================================
# NSE HTTP HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("NIFTY 50 -> BIGQUERY DATA PIPELINE")
print("=" * 70)

print()
print(f"Project              : {PROJECT_ID}")
print(f"Dataset              : {DATASET_ID}")
print(f"Table                : {TABLE_ID}")
print(f"Target trading days  : {TARGET_TRADING_DAYS}")
print()


# ============================================================
# STEP 1: CREATE NSE SESSION
# ============================================================

print("=" * 70)
print("STEP 1: CREATE NSE SESSION")
print("=" * 70)

session = requests.Session()
session.headers.update(HEADERS)

print("NSE session created.")
print()


# ============================================================
# STEP 2: DOWNLOAD NIFTY 50 DAILY DATA
# ============================================================

print("=" * 70)
print("STEP 2: DOWNLOAD NIFTY 50 DAILY DATA")
print("=" * 70)

records = []

current_date = datetime.now().date()

calendar_days_checked = 0
archive_files_found = 0


while len(records) < TARGET_TRADING_DAYS:

    calendar_days_checked += 1

    date_string = current_date.strftime("%d%m%Y")

    display_date = current_date.strftime("%d-%m-%Y")

    filename = (
        f"ind_close_all_{date_string}.csv"
    )

    url = NSE_ARCHIVE_URL.format(
        date=date_string
    )

    print("-" * 70)
    print(f"Checking : {display_date}")
    print(f"File    : {filename}")
    print(f"URL     : {url}")

    try:

        response = session.get(
            url,
            timeout=30
        )

        print(
            f"HTTP status : {response.status_code}"
        )

    except requests.RequestException as e:

        print("NSE request error:")
        print(repr(e))

        current_date -= timedelta(days=1)
        continue


    # --------------------------------------------------------
    # Archive not found
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

        print(
            f"CSV rows : {len(df)}"
        )

    except Exception as e:

        print("CSV parsing error:")
        print(repr(e))

        current_date -= timedelta(days=1)
        continue


    # --------------------------------------------------------
    # Validate required column
    # --------------------------------------------------------

    if "Index Name" not in df.columns:

        print(
            "ERROR: 'Index Name' column missing."
        )

        current_date -= timedelta(days=1)
        continue


    # --------------------------------------------------------
    # Find EXACT NIFTY 50 row
    # --------------------------------------------------------

    nifty = df[
        df["Index Name"]
        .astype(str)
        .str.strip()
        .str.upper()
        == "NIFTY 50"
    ].copy()


    if nifty.empty:

        print(
            "NIFTY 50 not found in archive."
        )

        current_date -= timedelta(days=1)
        continue


    # --------------------------------------------------------
    # Extract record
    # --------------------------------------------------------

    row = nifty.iloc[0]

    try:

        index_date = str(
            row["Index Date"]
        ).strip()

        open_value = float(
            str(
                row["Open Index Value"]
            ).replace(",", "")
        )

        high_value = float(
            str(
                row["High Index Value"]
            ).replace(",", "")
        )

        low_value = float(
            str(
                row["Low Index Value"]
            ).replace(",", "")
        )

        close_value = float(
            str(
                row["Closing Index Value"]
            ).replace(",", "")
        )

        volume_value = int(
            float(
                str(
                    row["Volume"]
                )
                .replace(",", "")
                .strip()
            )
        )

    except Exception as e:

        print(
            "ERROR extracting NIFTY record:"
        )

        print(repr(e))

        current_date -= timedelta(days=1)
        continue


    record = {
        "index_date": index_date,
        "open": open_value,
        "high": high_value,
        "low": low_value,
        "close": close_value,
        "volume": volume_value
    }

    records.append(record)

    archive_files_found += 1


    print()
    print("NIFTY 50 FOUND")

    print(
        f"Index Date : {index_date}"
    )

    print(
        f"Open       : {open_value}"
    )

    print(
        f"High       : {high_value}"
    )

    print(
        f"Low        : {low_value}"
    )

    print(
        f"Close      : {close_value}"
    )

    print(
        f"Volume     : {volume_value}"
    )


    current_date -= timedelta(days=1)


# ============================================================
# STEP 3: VALIDATE DOWNLOAD
# ============================================================

print()
print("=" * 70)
print("STEP 3: VALIDATE DOWNLOADED DATA")
print("=" * 70)

print(
    f"Calendar dates checked : "
    f"{calendar_days_checked}"
)

print(
    f"Archive files found    : "
    f"{archive_files_found}"
)

print(
    f"NIFTY records          : "
    f"{len(records)}"
)


if len(records) < TARGET_TRADING_DAYS:

    print()
    print(
        f"ERROR: Expected at least "
        f"{TARGET_TRADING_DAYS} records."
    )

    print(
        f"Only {len(records)} records found."
    )

    sys.exit(1)


data = pd.DataFrame(records)


# ============================================================
# STEP 4: CLEAN DATA
# ============================================================

print()
print("=" * 70)
print("STEP 4: CLEAN DATA")
print("=" * 70)


# ------------------------------------------------------------
# Parse NSE trading date
# ------------------------------------------------------------

data["trading_date"] = pd.to_datetime(
    data["index_date"],
    format="%d-%m-%Y",
    errors="coerce"
)


# ------------------------------------------------------------
# IMPORTANT
#
# Keep the same timestamp convention as the existing
# BigQuery rows so this run does not create duplicate records.
#
# 28-08-2026 -> 2026-08-28 00:00:00 UTC
# ------------------------------------------------------------

data["timestamp"] = pd.to_datetime(
    data["trading_date"],
    utc=True
)


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
# Remove invalid OHLC records
# ------------------------------------------------------------

data = data.dropna(
    subset=[
        "trading_date",
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
# Remove duplicate trading dates
# ------------------------------------------------------------

data = data.drop_duplicates(
    subset=["trading_date"]
)


# ------------------------------------------------------------
# Sort
# ------------------------------------------------------------

data = data.sort_values(
    "trading_date"
).reset_index(drop=True)


print(
    f"Valid NIFTY records : "
    f"{len(data)}"
)

print()

print(
    data[
        [
            "trading_date",
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume"
        ]
    ].to_string(index=False)
)


if data.empty:

    print()
    print(
        "ERROR: No valid records remain."
    )

    sys.exit(1)


# ============================================================
# STEP 5: CONNECT TO BIGQUERY
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

    print(
        "BigQuery connection successful."
    )

except Exception as e:

    print(
        "ERROR connecting to BigQuery:"
    )

    print(repr(e))

    sys.exit(1)


print(
    f"Target table : {TABLE_REF}"
)


# ============================================================
# STEP 6: VERIFY TABLE
# ============================================================

print()
print("=" * 70)
print("STEP 6: VERIFY BIGQUERY TABLE")
print("=" * 70)


try:

    table = client.get_table(
        TABLE_REF
    )

    print("Table exists.")

    print(
        f"Current table rows : "
        f"{table.num_rows}"
    )

except Exception as e:

    print(
        "ERROR accessing BigQuery table:"
    )

    print(repr(e))

    sys.exit(1)


# ============================================================
# STEP 7: CHECK EXISTING RECORDS
# ============================================================

print()
print("=" * 70)
print("STEP 7: CHECK EXISTING RECORDS")
print("=" * 70)

print(
    "Checking existing timestamps..."
)


query = f"""
SELECT DISTINCT timestamp
FROM `{TABLE_REF}`
WHERE timestamp IS NOT NULL
"""


try:

    query_job = client.query(
        query
    )

    query_result = query_job.result()

    existing_timestamps = set()

    for row in query_result:

        timestamp = row["timestamp"]

        if timestamp is None:
            continue

        timestamp = pd.Timestamp(
            timestamp
        )

        if timestamp.tzinfo is None:

            timestamp = timestamp.tz_localize(
                "UTC"
            )

        else:

            timestamp = timestamp.tz_convert(
                "UTC"
            )

        existing_timestamps.add(
            timestamp
        )


except Exception as e:

    print()
    print(
        "ERROR querying BigQuery:"
    )

    print(repr(e))

    sys.exit(1)


print(
    f"Existing timestamps : "
    f"{len(existing_timestamps)}"
)


# ============================================================
# STEP 8: REMOVE DUPLICATES
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


print(
    f"Downloaded records : "
    f"{before_count}"
)

print(
    f"Already in table   : "
    f"{before_count - new_count}"
)

print(
    f"New records        : "
    f"{new_count}"
)


# ============================================================
# STEP 9: UPLOAD
# ============================================================

print()
print("=" * 70)
print("STEP 9: UPLOAD TO BIGQUERY")
print("=" * 70)


if data.empty:

    print()
    print(
        "No new NIFTY records to upload."
    )

    print(
        "BigQuery is already up to date."
    )

else:

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
    print(
        "Records ready for upload:"
    )

    print(
        upload_data.to_string(
            index=False
        )
    )


    job_config = bigquery.LoadJobConfig(
        write_disposition=(
            bigquery.WriteDisposition.WRITE_APPEND
        )
    )


    try:

        job = client.load_table_from_dataframe(
            upload_data,
            TABLE_REF,
            job_config=job_config
        )

        print()
        print(
            f"BigQuery job ID : "
            f"{job.job_id}"
        )

        job.result()

        print(
            "Upload completed successfully."
        )

    except Exception as e:

        print()
        print(
            "ERROR uploading to BigQuery:"
        )

        print(repr(e))

        sys.exit(1)


# ============================================================
# STEP 10: FINAL VERIFICATION
# ============================================================

print()
print("=" * 70)
print("STEP 10: VERIFY BIGQUERY")
print("=" * 70)


try:

    table = client.get_table(
        TABLE_REF
    )

except Exception as e:

    print(
        "ERROR verifying BigQuery:"
    )

    print(repr(e))

    sys.exit(1)


print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print(
    f"Final BigQuery rows : "
    f"{table.num_rows}"
)

print()

if data.empty:

    print(
        "No new records were added."
    )

else:

    print(
        f"New records uploaded : "
        f"{len(data)}"
    )

    print()
    print("Latest uploaded records:")

    print(
        data[
            [
                "trading_date",
                "timestamp",
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
        ]
        .sort_values("trading_date")
        .tail(10)
        .to_string(index=False)
    )

print()
print("=" * 70)
print("NIFTY DATA PIPELINE COMPLETED SUCCESSFULLY")
print("=" * 70)
