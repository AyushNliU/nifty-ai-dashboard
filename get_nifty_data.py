from openchart import NSEData
from datetime import datetime, timedelta
from google.cloud import bigquery
import pandas as pd

PROJECT_ID = "amiable-dragon-435412-v4"
DATASET_ID = "nifty_market"
TABLE_ID = "nifty_ohlcv"

print("Starting NIFTY data download...")

nse = NSEData()

end = datetime.now()
start = end - timedelta(days=30)

data = nse.historical(
    "NIFTY 50",
    "IDX",
    start,
    end,
    "1d"
)

print(f"Downloaded {len(data)} rows.")

# Make sure timestamp is a normal column
data = data.reset_index()

# Show column names for debugging
print("Columns received:", list(data.columns))

# Rename OpenChart columns to match BigQuery
rename_map = {
    "datetime": "timestamp",
    "date": "timestamp",
    "Datetime": "timestamp",
    "Date": "timestamp",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume"
}

data = data.rename(columns=rename_map)

# Keep only the BigQuery columns
data = data[
    ["timestamp", "open", "high", "low", "close", "volume"]
].copy()

data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)

# Convert volume safely
data["volume"] = pd.to_numeric(
    data["volume"],
    errors="coerce"
).fillna(0).astype("int64")

print(data.tail())

client = bigquery.Client(project=PROJECT_ID)

table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

job_config = bigquery.LoadJobConfig(
    write_disposition="WRITE_APPEND"
)

print(f"Uploading to {table_ref}...")

job = client.load_table_from_dataframe(
    data,
    table_ref,
    job_config=job_config
)

job.result()

table = client.get_table(table_ref)

print("BigQuery upload successful!")
print(f"Table now contains {table.num_rows} rows.")
