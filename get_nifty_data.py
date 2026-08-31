import requests
import pandas as pd

from io import StringIO
from datetime import datetime, timedelta
from google.cloud import bigquery


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "amiable-dragon-435412-v4"
DATASET_ID = "nifty_market"
TABLE_ID = "nifty_ohlcv"

TABLE_REF = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"{TABLE_ID}"
)

# Number of trading-day records we want
TARGET_TRADING_DAYS = 30

# Search this many calendar days backward
MAX_CALENDAR_DAYS = 60

NIFTY_NAME = "Nifty 50"

NSE_ARCHIVE_BASE = (
    "https://nsearchives.nseindia.com/"
    "content/indices/"
)


# ============================================================
# NSE HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/csv,"
        "application/json,"
        "text/plain,"
        "*/*"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}


# ============================================================
# START
# ============================================================

print("=" * 70)
print("NIFTY 50 → BIGQUERY DATA PIPELINE")
print("=" * 70)

print()
print("Project :", PROJECT_ID)
print("Dataset :", DATASET_ID)
print("Table   :", TABLE_ID)
print()
print("Target trading days :", TARGET_TRADING_DAYS)
print()


# ============================================================
# CREATE NSE SESSION
# ============================================================

print("=" * 70)
print("STEP 1: CREATE NSE SESSION")
print("=" * 70)

session = requests.Session()

session.headers.update(HEADERS)

print()
print("NSE session created.")


# ============================================================
# DOWNLOAD NIFTY DAILY SNAPSHOTS
# ============================================================

print()
print("=" * 70)
print("STEP 2: DOWNLOAD NIFTY 50 DAILY DATA")
print("=" * 70)


today = datetime.now()

records = []

dates_checked = 0
files_found = 0


for days_back in range(MAX_CALENDAR_DAYS + 1):

    # Stop once we have enough trading days
    if len(records) >= TARGET_TRADING_DAYS:
        break

    check_date = today - timedelta(days=days_back)

    date_string = check_date.strftime("%d%m%Y")

    filename = (
        f"ind_close_all_{date_string}.csv"
    )

    url = (
        NSE_ARCHIVE_BASE +
        filename
    )

    dates_checked += 1

    print()
    print("-" * 70)

    print(
        f"Checking: "
        f"{check_date.strftime('%d-%m-%Y')}"
    )

    print(
        f"File: {filename}"
    )

    try:

        response = session.get(
            url,
            timeout=30
        )

    except requests.exceptions.Timeout:

        print(
            "Request timed out. Skipping date."
        )

        continue

    except requests.exceptions.RequestException as e:

        print(
            "Request error:"
        )

        print(
            repr(e)
        )

        continue


    print(
        f"HTTP status: {response.status_code}"
    )


    # --------------------------------------------------------
    # FILE DOES NOT EXIST
    # --------------------------------------------------------

    if response.status_code == 404:

        print(
            "No archive for this date."
        )

        continue


    # --------------------------------------------------------
    # OTHER HTTP ERROR
    # --------------------------------------------------------

    if response.status_code != 200:

        print(
            "Unexpected HTTP status. Skipping."
        )

        continue


    # --------------------------------------------------------
    # PARSE CSV
    # --------------------------------------------------------

    try:

        df = pd.read_csv(
            StringIO(response.text)
        )

    except Exception as e:

        print(
            "CSV parsing failed:"
        )

        print(
            repr(e)
        )

        continue


    if df.empty:

        print(
            "CSV contains no rows."
        )

        continue


    files_found += 1

    print(
        f"CSV rows: {len(df)}"
    )


    # --------------------------------------------------------
    # FIND EXACT NIFTY 50 ROW
    # --------------------------------------------------------

    if "Index Name" not in df.columns:

        print(
            "ERROR: 'Index Name' column missing."
        )

        continue


    # Clean index name
    df["Index Name"] = (
        df["Index Name"]
        .astype(str)
        .str.strip()
    )


    nifty = df[
        df["Index Name"].str.lower()
        == NIFTY_NAME.lower()
    ].copy()


    # --------------------------------------------------------
    # NIFTY NOT FOUND
    # --------------------------------------------------------

    if nifty.empty:

        print(
            "Nifty 50 row not found."
        )

        continue


    # --------------------------------------------------------
    # EXTRACT NIFTY ROW
    # --------------------------------------------------------

    row = nifty.iloc[0]

    print()
    print("NIFTY 50 FOUND")

    print(
        "Index Date :",
        row["Index Date"]
    )

    print(
        "Open       :",
        row["Open Index Value"]
    )

    print(
        "High       :",
        row["High Index Value"]
    )

    print(
        "Low        :",
        row["Low Index Value"]
    )

    print(
        "Close      :",
        row["Closing Index Value"]
    )

    print(
        "Volume     :",
        row["Volume"]
    )


    # --------------------------------------------------------
    # SAVE RAW RECORD
    # --------------------------------------------------------

    records.append(
        {
            "index_date": row["Index Date"],
            "open": row["Open Index Value"],
            "high": row["High Index Value"],
            "low": row["Low Index Value"],
            "close": row["Closing Index Value"],
            "volume": row["Volume"],
        }
    )


# ============================================================
# VALIDATE DOWNLOAD
# ============================================================

print()
print("=" * 70)
print("STEP 3: VALIDATE DOWNLOADED DATA")
print("=" * 70)

print()
print(
    "Calendar dates checked:",
    dates_checked
)

print(
    "Archive files found:",
    files_found
)

print(
    "NIFTY records collected:",
    len(records)
)


if not records:

    print()
    print(
        "ERROR: No NIFTY 50 records were collected."
    )

    raise SystemExit(1)


# ============================================================
# CREATE DATAFRAME
# ============================================================

data = pd.DataFrame(records)


print()
print("Raw collected data:")
print()

print(
    data.to_string(index=False)
)


# ============================================================
# CLEAN NUMERIC COLUMNS
# ============================================================

print()
print("=" * 70)
print("STEP 4: CLEAN DATA")
print("=" * 70)


numeric_columns = [
    "open",
    "high",
    "low",
    "close",
    "volume",
]


for column in numeric_columns:

    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )


# Volume should be integer
data["volume"] = (
    data["volume"]
    .fillna(0)
    .astype("int64")
)


# ============================================================
# CREATE TIMESTAMP
# ============================================================

data["timestamp"] = pd.to_datetime(
    data["index_date"],
    format="%d-%m-%Y",
    errors="coerce"
)


# Remove invalid timestamps
data = data.dropna(
    subset=["timestamp"]
)


# Convert India date to UTC timestamp
#
# Example:
# 28-08-2026 00:00 IST
# becomes
# 27-08-2026 18:30 UTC
#
# BigQuery TIMESTAMP stores UTC.
#

data["timestamp"] = (
    data["timestamp"]
    .dt.tz_localize("Asia/Kolkata")
    .dt.tz_convert("UTC")
)


# ============================================================
# SELECT FINAL COLUMNS
# ============================================================

data = data[
    [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]
].copy()


# ============================================================
# REMOVE INVALID OHLC ROWS
# ============================================================

data = data.dropna(
    subset=[
        "open",
        "high",
        "low",
        "close",
    ]
)


# ============================================================
# REMOVE DUPLICATES
# ============================================================

data = data.drop_duplicates(
    subset=["timestamp"]
)


# Sort oldest → newest
data = data.sort_values(
    "timestamp"
).reset_index(drop=True)


print()
print(
    f"Valid NIFTY records: {len(data)}"
)

print()
print(
    data.to_string(index=False)
)


if data.empty:

    print()
    print(
        "ERROR: No valid records remain."
    )

    raise SystemExit(1)


# ============================================================
# CONNECT TO BIGQUERY
# ============================================================

print()
print("=" * 70)
print("STEP 5: CONNECT TO BIGQUERY")
print("=" * 70)

print()
print(
    "Connecting to BigQuery..."
)

try:

    client = bigquery.Client(
        project=PROJECT_ID
    )

except Exception as e:

    print()
    print(
        "ERROR: BigQuery connection failed."
    )

    print(
        repr(e)
    )

    raise SystemExit(1)


print(
    "BigQuery connection successful."
)

print(
    "Target table:",
    TABLE_REF
)


# ============================================================
# VERIFY TABLE EXISTS
# ============================================================

print()
print("=" * 70)
print("STEP 6: VERIFY BIGQUERY TABLE")
print("=" * 70)

try:

    table = client.get_table(
        TABLE_REF
    )

except Exception as e:

    print()
    print(
        "ERROR: Could not find BigQuery table."
    )

    print(
        repr(e)
    )

    print()
    print(
        "Expected table:"
    )

    print(
        TABLE_REF
    )

    raise SystemExit(1)


print()
print(
    "Table exists."
)

print(
    "Current table rows:",
    table.num_rows
)


# ============================================================
# GET EXISTING TIMESTAMPS
# ============================================================

print()
print("=" * 70)
print("STEP 7: CHECK EXISTING RECORDS")
print("=" * 70)


query = f"""
SELECT DISTINCT timestamp
FROM `{TABLE_REF}`
WHERE timestamp IS NOT NULL
"""


try:

    existing = (
        client
        .query(query)
        .to_dataframe()
    )

except Exception as e:

    print()
    print(
        "ERROR querying BigQuery:"
    )

    print(
        repr(e)
    )

    raise SystemExit(1)


if existing.empty:

    existing_timestamps = set()

    print()
    print(
        "No existing timestamps found."
    )

else:

    existing["timestamp"] = (
        pd.to_datetime(
            existing["timestamp"],
            utc=True
        )
    )

    existing_timestamps = set(
        existing["timestamp"]
    )

    print()
    print(
        "Existing timestamps:",
        len(existing_timestamps)
    )


# ============================================================
# REMOVE ALREADY UPLOADED DATA
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


print()
print(
    "Downloaded records:",
    before_count
)

print(
    "Already in BigQuery:",
    before_count - new_count
)

print(
    "New records:",
    new_count
)


# ============================================================
# NOTHING NEW
# ============================================================

if data.empty:

    print()
    print("=" * 70)
    print("BIGQUERY ALREADY UP TO DATE")
    print("=" * 70)

    print()
    print(
        "No new NIFTY records need to be uploaded."
    )

    raise SystemExit(0)


# ============================================================
# UPLOAD TO BIGQUERY
# ============================================================

print()
print("=" * 70)
print("STEP 9: UPLOAD TO BIGQUERY")
print("=" * 70)


print()
print(
    "Uploading records:"
)

print(
    data.to_string(index=False)
)


job_config = bigquery.LoadJobConfig(
    write_disposition=(
        bigquery.WriteDisposition.WRITE_APPEND
    )
)


try:

    job = client.load_table_from_dataframe(
        data,
        TABLE_REF,
        job_config=job_config
    )

    job.result()

except Exception as e:

    print()
    print(
        "ERROR: BigQuery upload failed."
    )

    print(
        repr(e)
    )

    raise SystemExit(1)


# ============================================================
# VERIFY UPLOAD
# ============================================================

print()
print("=" * 70)
print("STEP 10: VERIFY UPLOAD")
print("=" * 70)


try:

    table = client.get_table(
        TABLE_REF
    )

except Exception as e:

    print(
        "Could not refresh table metadata."
    )

    print(
        repr(e)
    )

    raise SystemExit(1)


print()
print(
    "Uploaded rows:",
    new_count
)

print(
    "BigQuery table rows:",
    table.num_rows
)


# ============================================================
# SHOW LATEST RECORDS
# ============================================================

print()
print("=" * 70)
print("LATEST NIFTY RECORDS")
print("=" * 70)

print()

print(
    data.sort_values(
        "timestamp"
    ).tail(10).to_string(index=False)
)


# ============================================================
# SUCCESS
# ============================================================

print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print()
print(
    "NSE → NIFTY 50 → BigQuery pipeline completed."
)

print()
print(
    f"New records uploaded: {new_count}"
)

print(
    f"Total BigQuery rows: {table.num_rows}"
)

print()
print("=" * 70)
