"""Step 1: download + clean the Bitext customer-support dataset.

  * placeholders like {{Order Number}} -> <order_number> so the model doesn't learn template syntax
  * exact duplicates (after normalisation) removed BEFORE splitting -> no train/test leakage
  * stratified train / val / test split (val is used to choose the auto-resolve threshold)
Run:  python -m src.data
"""
import io, re, zipfile
import pandas as pd
import requests
from sklearn.model_selection import train_test_split
from src.config import DATASET_ZIP, RAW_CSV, DATA_PROCESSED, RANDOM_STATE


def download(force=False):
    if RAW_CSV.exists() and not force:
        return RAW_CSV
    print("downloading Bitext dataset (~19 MB) ...")
    z = zipfile.ZipFile(io.BytesIO(requests.get(DATASET_ZIP, timeout=120).content))
    name = next(n for n in z.namelist() if n.endswith(".csv"))
    RAW_CSV.write_bytes(z.read(name))
    return RAW_CSV


def normalise(text: str) -> str:
    text = re.sub(r"\{\{\s*([^}]+?)\s*\}\}", lambda m: "<" + m.group(1).lower().replace(" ", "_") + ">", str(text))
    return re.sub(r"\s+", " ", text).strip()


def load_clean() -> pd.DataFrame:
    df = pd.read_csv(download())
    df = df.rename(columns={"instruction": "text"})
    df["text"] = df["text"].map(normalise)
    df["noisy"] = df["flags"].fillna("").str.contains("Z|Q")   # Z = typos, Q = colloquial
    n = len(df)
    df["_key"] = df["text"].str.lower()
    df = df.drop_duplicates("_key").drop(columns="_key").reset_index(drop=True)
    print(f"rows {n} -> {len(df)} after removing duplicates")
    return df[["text", "intent", "category", "flags", "noisy", "response"]]


def split(df):
    train, rest = train_test_split(df, test_size=0.3, stratify=df["intent"], random_state=RANDOM_STATE)
    val, test = train_test_split(rest, test_size=0.5, stratify=rest["intent"], random_state=RANDOM_STATE)
    return train, val, test


if __name__ == "__main__":
    df = load_clean()
    for name, part in zip(["train", "val", "test"], split(df)):
        part.to_csv(DATA_PROCESSED / f"{name}.csv", index=False)
        print(f"{name:5s}: {len(part)} rows")
    print(df["category"].value_counts().to_string())
