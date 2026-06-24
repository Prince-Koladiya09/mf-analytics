import requests
import pandas as pd
import json
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR  = BASE_DIR / "data" / "raw"
PROC_DIR = BASE_DIR / "data" / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://api.mfapi.in/mf/{}"

SCHEMES = {
    125497: "HDFC Top 100 Direct",
    119551: "SBI Bluechip Direct",
    120503: "ICICI Bluechip Direct",
    118632: "Nippon Large Cap Direct",
    119092: "Axis Bluechip Direct",
    120841: "Kotak Bluechip Direct",
}

def fetch_scheme(amfi_code: int, scheme_name: str) -> dict | None:
    url = BASE_URL.format(amfi_code)
    print(f"\n GET {url}")
    print(f"   Scheme : {scheme_name} (AMFI: {amfi_code})")

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "UNKNOWN")
        meta   = data.get("meta", {})
        nav_records = data.get("data", [])

        print(f"   Status         : {status}")
        print(f"   Fund House     : {meta.get('fund_house', 'N/A')}")
        print(f"   Scheme Name    : {meta.get('scheme_name', 'N/A')}")
        print(f"   Scheme Type    : {meta.get('scheme_type', 'N/A')}")
        print(f"   Scheme Category: {meta.get('scheme_category', 'N/A')}")
        print(f"   NAV records    : {len(nav_records)}")

        if nav_records:
            latest = nav_records[0]
            print(f"   Latest NAV     : ₹{latest.get('nav', 'N/A')} on {latest.get('date', 'N/A')}")

        return {
            "amfi_code"  : amfi_code,
            "scheme_name": scheme_name,
            "meta"       : meta,
            "status"     : status,
            "nav_records": nav_records,
        }

    except requests.exceptions.Timeout:
        print(f"    Timeout after 15s — skipping {scheme_name}")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"    HTTP error: {e}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"    Connection error — check network / VPN")
        return None
    except Exception as e:
        print(f"    Unexpected error: {e}")
        return None

def save_scheme_csv(result: dict) -> pd.DataFrame | None:
    if not result or not result["nav_records"]:
        return None

    amfi_code   = result["amfi_code"]
    scheme_name = result["scheme_name"]
    meta        = result["meta"]
    records     = result["nav_records"]

    df = pd.DataFrame(records)
    df.columns = [c.lower() for c in df.columns]
    df["amfi_code"]   = amfi_code
    df["scheme_name"] = meta.get("scheme_name", scheme_name)
    df["fund_house"]  = meta.get("fund_house", "")
    df["scheme_type"] = meta.get("scheme_type", "")
    df["nav"]         = pd.to_numeric(df["nav"], errors="coerce")
    df["date"]        = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    fname = RAW_DIR / f"live_nav_{amfi_code}.csv"
    df.to_csv(fname, index=False)
    print(f"    Saved → {fname.name}  ({len(df):,} rows)")
    return df

def main():
    print("\n" + "█" * 70)
    print("  LIVE NAV FETCH — mfapi.in")
    print(f"  Run timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("█" * 70)

    all_dfs   = []
    summary   = []
    fetch_log = []

    for amfi_code, scheme_name in SCHEMES.items():
        result = fetch_scheme(amfi_code, scheme_name)

        log_entry = {
            "amfi_code"       : amfi_code,
            "scheme_name"     : scheme_name,
            "fetch_status"    : "SUCCESS" if result else "FAILED",
            "nav_records"     : len(result["nav_records"]) if result else 0,
            "latest_nav"      : None,
            "latest_nav_date" : None,
            "fetched_at"      : datetime.now().isoformat(),
        }

        if result:
            df = save_scheme_csv(result)
            if df is not None and not df.empty:
                all_dfs.append(df)
                latest = df.iloc[-1]
                log_entry["latest_nav"]      = float(latest["nav"])
                log_entry["latest_nav_date"] = str(latest["date"].date())

                summary.append({
                    "amfi_code"      : amfi_code,
                    "scheme_name"    : scheme_name,
                    "fund_house"     : df["fund_house"].iloc[0],
                    "latest_nav"     : float(latest["nav"]),
                    "latest_nav_date": str(latest["date"].date()),
                    "total_records"  : len(df),
                    "earliest_date"  : str(df["date"].min().date()),
                })

        fetch_log.append(log_entry)
        time.sleep(0.3)

    if all_dfs:
        merged = pd.concat(all_dfs, ignore_index=True)
        merged_path = PROC_DIR / "live_nav_all_schemes.csv"
        merged.to_csv(merged_path, index=False)
        print(f"\n Merged NAV saved → {merged_path.name}  ({len(merged):,} rows)")

    if summary:
        summary_df = pd.DataFrame(summary)
        summary_path = PROC_DIR / "live_nav_summary.csv"
        summary_df.to_csv(summary_path, index=False)

        print("\n" + "=" * 70)
        print("  LIVE NAV SUMMARY")
        print("=" * 70)
        print(summary_df.to_string(index=False))

    log_df = pd.DataFrame(fetch_log)
    log_path = PROC_DIR / "fetch_log.csv"
    log_df.to_csv(log_path, index=False)
    print(f"\n Fetch log saved → {log_path.name}")

    success = log_df["fetch_status"].eq("SUCCESS").sum()
    failed  = log_df["fetch_status"].eq("FAILED").sum()
    print(f"\n Fetch complete — {success} succeeded, {failed} failed.")

    if failed:
        print("   Failed schemes:")
        for _, row in log_df[log_df["fetch_status"] == "FAILED"].iterrows():
            print(f"     {row['scheme_name']} (AMFI: {row['amfi_code']})")

    return log_df

if __name__ == "__main__":
    main()
