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

TABLE_REF = (
    f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
)


# ============================================================
# HEADER
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
# STEP 1: CREATE NSE SESSION
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
# STEP 2: DOWNLOAD NIFTY 50 DAILY DATA
# ============================================================

print("=" * 70)
print("STEP 2: DOWNLOAD NIFTY 50 DAILY DATA")
print("=" * 70)

records = []

today_ist = datetime.now().date()

current_date = today_ist

calendar_days_checked = 0
archive_files_found = 0


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

        print(f"CSV rows : {len(df)}")

    except Exception as e:

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
    # Extract NIFTY row
    # --------------------------------------------------------

    row = nifty.iloc[0]

    try:

        record = {
            "index_date": str(
                row["Index Date"]
            ).strip(),

            "open": float(
                str(
                    row["Open Index Value"]
                ).replace(",", "")
            ),

            "high": float(
                str(
                    row["High Index Value"]
                ).replace(",", "")
            ),

            "low": float(
                str(
                    row["Low Index Value"]
                ).replace(",", "")
            ),

            "close": float(
                str(
                    row["Closing Index Value"]
                ).replace(",", "")
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


    current_date -= timedelta(days=1)


# ============================================================
# STEP 3: VALIDATE
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


if len(records) != TARGET_TRADING_DAYS:

    print()
    print(
        f"ERROR: Expected "
        f"{TARGET_TRADING_DAYS} records but found "
        f"{len(records)}."
    )

    sys.exit(1)


data = pd.DataFrame(records)


print()
print("Raw collected data:")
print(
    data.to_string(index=False)
)


# ============================================================
# STEP 4: CLEAN DATA
# ============================================================

print()
print("=" * 70)
print("STEP 4: CLEAN DATA")
print("=" * 70)


# ------------------------------------------------------------
# Parse trading date
# ------------------------------------------------------------

try:

    data["trading_date"] = pd.to_datetime(
        data["index_date"],
        format="%d-%m-%Y"
    )

except Exception as e:

    print("ERROR parsing trading date:")
    print(repr(e))

    sys.exit(1)


# ------------------------------------------------------------
# Create market-close timestamp
#
# NSE trading close = 15:30 IST
#
# Example:
#
# 28-08-2026 15:30 IST
#       =
# 28-08-2026 10:00 UTC
# ------------------------------------------------------------

try:

    data["timestamp"] = (
        data["trading_date"]
        .dt.strftime("%Y-%m-%d")
        .astype(str)
        + " 15:30:00"
    )

    data["timestamp"] = pd.to_datetime(
        data["timestamp"]
    )

    data["timestamp"] = (
        data["timestamp"]
        .dt.tz_localize(IST)
        .dt.tz_convert("UTC")
    )

except Exception as e:

    print("ERROR creating timestamp:")
    print(repr(e))

    sys.exit(1)


# ------------------------------------------------------------
# Numeric conversion
# ------------------------------------------------------------

numeric_columns = [
    "open",
    "high",
    "low",
    "close",
    "volume"
]


for column in numeric_columns:

    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )


# ------------------------------------------------------------
# Remove invalid rows
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
# Sort oldest → newest
# ------------------------------------------------------------

data = data.sort_values(
    "trading_date"
).reset_index(drop=True)


print()
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

    print("ERROR: No valid records remain.")

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

    print("BigQuery connection successful.")

except Exception as e:

    print("ERROR connecting to BigQuery:")
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

    print("ERROR accessing BigQuery table:")
    print(repr(e))

    sys.exit(1)


# ============================================================
# STEP 7: CHECK EXISTING RECORDS
# ============================================================

print()
print("=" * 70)
print("STEP 7: CHECK EXISTING RECORDS")
print("=" * 70)


query = f"""
SELECT timestamp
FROM `{TABLE_REF}`
WHERE timestamp IS NOT NULL
"""


print("Checking existing timestamps...")


try:

    existing = client.query(
        query
    ).to_dataframe()

except Exception as e:

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

if data.empty:

    print()
    print("No new records to upload.")
    print("BigQuery is already up to date.")

else:

    print()
    print("=" * 70)
    print("STEP 9: UPLOAD TO BIGQUERY")
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


    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND"
    )


    try:

        job = client.load_table_from_dataframe(
            upload_data,
            TABLE_REF,
            job_config=job_config
        )

        print(
            f"BigQuery job ID : "
            f"{job.job_id}"
        )

        job.result()

        print("Upload completed.")

    except Exception as e:

        print("ERROR uploading to BigQuery:")
        print(repr(e))

        sys.exit(1)


# ============================================================
# STEP 10: VERIFY
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

    print("ERROR verifying table:")
    print(repr(e))

    sys.exit(1)


print(
    f"Table rows : "
    f"{table.num_rows}"
)


# ============================================================
# FINAL SUCCESS
# ============================================================

print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print(
    "NIFTY 50 daily data pipeline completed."
)

print(
    f"Valid records collected : "
    f"{len(data)}"
)

print(
    f"BigQuery table rows     : "
    f"{table.num_rows}"
)

print()
print("Latest records:")

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
