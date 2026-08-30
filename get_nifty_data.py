from openchart import NSEData
from datetime import datetime, timedelta

print("Starting NIFTY data download...")

nse = NSEData()

end = datetime.now()
start = end - timedelta(days=30)

print("Requesting NIFTY 50 data...")

data = nse.historical(
    "NIFTY 50",
    "IDX",
    start,
    end,
    "1d"
)

print("\nNIFTY 50 data:")
print(data)

data.to_csv("nifty_data.csv")

print("\nNIFTY data downloaded successfully!")
print(f"Rows downloaded: {len(data)}")
