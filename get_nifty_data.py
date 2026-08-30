import requests
import pandas as pd

url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"

params = {
    "range": "1mo",
    "interval": "1d"
}

response = requests.get(url, params=params)
data = response.json()

result = data["chart"]["result"][0]

timestamps = result["timestamp"]
quotes = result["indicators"]["quote"][0]

df = pd.DataFrame({
    "Date": pd.to_datetime(timestamps, unit="s"),
    "Open": quotes["open"],
    "High": quotes["high"],
    "Low": quotes["low"],
    "Close": quotes["close"],
    "Volume": quotes["volume"]
})

print(df)

df.to_csv("nifty_data.csv", index=False)

print("\nNIFTY data saved successfully!")
