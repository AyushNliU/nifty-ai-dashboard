from openchart import NSEData
from datetime import datetime, timedelta
from google.cloud import bigquery
import pandas as pd
import sys


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = "amiable-dragon-435412-v4"
DATASET_ID = "nifty_market"
TABLE_ID = "nifty_ohlcv"

NIFTY_TOKEN = "26000"

# How much historical data to request
DAYS_BACK = 30


# ============================================================
# 1. DOWNLOAD NIFTY DATA
# ============================================================

print("=" * 60)
print("NIFTY 50 DATA COLLECTION")
print("=" * 60)

end = datetime.now()
start = end - timedelta(days=DAYS_BACK)

print(f"Start date : {start}")
print(f"End date   : {end}")
print("Symbol     : NIFTY 50")
print("Token      : 26000")
print("Interval   : 1d")
print()


nse = NSEData()

try:

    print("Requesting NIFTY 50 historical data...")

    data = nse.historical_direct(
        token=NIFTY_TOKEN,
        symbol="NIFTY 50",
        symbol_type="Index",
        start=start,
        end=end,
        interval="1d"
    )

except Exception as e:

    print()
    print("ERROR: NIFTY API request failed")
    print(str(e))

    sys.exit(1)


# ============================================================
# 2. VALIDATE RESPONSE
# ============================================================

if data is None or data.empty:

    print()
    print("ERROR: NIFTY API returned ZERO rows.")
    print("The data source may be temporarily unavailable.")

    sys.exit(1)


print()
print(f"Rows received: {len(data)}")
print()
print("Raw data:")
print(data.tail())


# ============================================================
# 3. PREPARE DATAFRAME
# ============================================================

data = data.reset_index()

print()
print("Columns received:")
print(list(data.columns))


# Handle timestamp column
if "Timestamp" in data.columns:

    data = data.rename(columns={
        "Timestamp": "timestamp"
    })

elif "timestamp" not in data.columns:

    # In case the index has another name
    data = data.rename(
        columns={data.columns[0]: "timestamp"}
    )


# Rename OHLCV columns
data = data.rename(columns={
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume"
})


required_columns = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume"
]


missing = [
    col for col in required_columns
    if col not in data.columns
]


if missing:

    print()
    print("ERROR: Missing columns:")
    print(missing)

    print()
    print("Available columns:")
    print(list(data.columns))

    sys.exit(1)


data = data[required_columns].copy()


# ============================================================
# 4. CLEAN DATA TYPES
# ============================================================

data["timestamp"] = pd.to_datetime(
    data["timestamp"],
    utc=True
)

for column in [
    "open",
    "high",
    "low",
    "close"
]:

    data[column] = pd.to_numeric(
        data[column],
        errors="coerce"
    )


data["volume"] = pd.to_numeric(
    data["volume"],
    errors="coerce"
).fillna(0).astype("int64")


# Remove invalid rows
data = data.dropna(
    subset=[
        "timestamp",
        "open",
        "high",
        "low",
        "close"
    ]
)


# Remove duplicate timestamps inside downloaded data
data = data.drop_duplicates(
    subset=["timestamp"]
)


print()
print(f"Valid rows after cleaning: {len(data)}")


if data.empty:

    print("ERROR: No valid rows remain after cleaning.")

    sys.exit(1)


# ============================================================
# 5. CONNECT TO BIGQUERY
# ============================================================

print()
print("Connecting to BigQuery...")

client = bigquery.Client(
    project=PROJECT_ID
)

table_ref = (
    f"{PROJECT_ID}."
    f"{DATASET_ID}."
    f"{TABLE_ID}"
)

print(f"Target table: {table_ref}")


# ============================================================
# 6. CHECK EXISTING TIMESTAMPS
# ============================================================

print()
print("Checking existing BigQuery records...")


query = f"""
SELECT DISTINCT timestamp
FROM `{table_ref}`
WHERE timestamp IS NOT NULL
"""


try:

    existing = client.query(query).to_dataframe()

except Exception as e:

    print()
    print("ERROR: Could not query BigQuery.")
    print(str(e))

    sys.exit(1)


if not existing.empty:

    existing["timestamp"] = pd.to_datetime(
        existing["timestamp"],
        utc=True
    )

    existing_timestamps = set(
        existing["timestamp"]
    )

else:

    existing_timestamps = set()


print(
    f"Existing timestamps in BigQuery: "
    f"{len(existing_timestamps)}"
)


# ============================================================
# 7. REMOVE DUPLICATES
# ============================================================

data = data[
    ~data["timestamp"].isin(
        existing_timestamps
    )
].copy()


print(
    f"New rows to upload: {len(data)}"
)


if data.empty:

    print()
    print("No new NIFTY records to upload.")
    print("BigQuery is already up to date.")

    sys.exit(0)


# ============================================================
# 8. UPLOAD TO BIGQUERY
# ============================================================

print()
print("Uploading new records to BigQuery...")


job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_APPEND"
)


try:

    job = client.load_table_from_dataframe(
        data,
        table_ref,
        job_config=job_config
    )

    job.result()

except Exception as e:

    print()
    print("ERROR: BigQuery upload failed.")
    print(str(e))

    sys.exit(1)


# ============================================================
# 9. VERIFY
# ============================================================

table = client.get_table(table_ref)


print()
print("=" * 60)
print("SUCCESS")
print("=" * 60)

print(
    f"Uploaded rows : {len(data)}"
)

print(
    f"Table rows    : {table.num_rows}"
)

print()
print("Latest records uploaded:")

print(
    data.sort_values("timestamp").tail()
)

print()
print("NIFTY data pipeline completed successfully.")
