import pandas as pd
import os

def split_data():
    if os.path.exists("data/processed/onset_set.parquet") and os.path.exists("data/processed/continuation_set.parquet"):
        print("Cache hit: split already done")
        return
    
    # Load master parquet
    df = pd.read_parquet("data/processed/sentinel_v2_features.parquet")

    # Create label
    # - Shift label by 1 day (Using Jan 1 to predict conflict Jan 2)
    df = df.sort_values(["h3_id", "date"])
    df["label"] = df.groupby("h3_id")["event_count_x"].shift(-1).fillna(0).astype(int)
    df["label"] = (df["label"] > 0).astype(int)

    # Split data
    # Onset: Peaceful last 14 days
    # Continuation: Atleast 1 event in last 14 days
    onset = df[df["dangerous_roll14d"] == 0]
    continuation = df[df["dangerous_roll14d"] > 0]

    # Save file
    os.makedirs("data/processed", exist_ok=True)
    onset.to_parquet("data/processed/onset_set.parquet", index=False)
    continuation.to_parquet("data/processed/continuation_set.parquet", index=False)
    print(f"Onset: {len(onset)} rows, Continuation: {len(continuation)} rows") 

if __name__ == "__main__":
    split_data()