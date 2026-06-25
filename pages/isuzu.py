import streamlit as st
import pandas as pd
from auth import check_login

st.title("Last Update Monitoring")
check_login()
st.divider()

SHEET1_ID = "1TCjREKxsvnsGTpKpJ_hERzatSYZ5qM3ZN8CDIw2Yqjk" # sosmed fanpagekarma

SHEET1_NAME = "All Content"

@st.cache_data(ttl=60)
def load_data(sheet_id, sheet_name):
    
    encoded_name = sheet_name.replace(" ", "%20") 
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_name}"
    callbackURL = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    df = pd.read_csv(url)
    df.columns = df.columns.str.strip()

    st.caption(f"Menampilkan: {callbackURL}")
    return df

# =================== read data sosmed fanpagekarma
try:
    df1 = load_data(SHEET1_ID, SHEET1_NAME)
except Exception as e:
    st.error(f"❌ Gagal load data: {e}")
    st.stop()

st.divider()

# ==========================
# Data Sosmed Fanpagekarma
# ==========================

if "id" not in df1.columns:
    st.warning(f"⚠️ Kolom 'id' tidak ditemukan.")
    st.write("Kolom tersedia:", df1.columns.tolist())
    st.stop()

# ── Tambah kolom checker ──────────────────────────────────────────────────────
df1["checker"] = df1.duplicated(subset=["id"], keep=False).map({True: "Duplicate", False: "Unique"})

# ── Latest Update per Platform ────────────────────────────────────────────────
st.markdown("### 🕐 Latest Update per Platform")

required_cols = ["Date", "link", "Platform", "image"]

if all(c in df1.columns for c in required_cols):
    df1["Date"] = pd.to_datetime(df1["Date"], format="mixed", errors="coerce")  
    summary_content_rows = []
    summary_followers_rows = []
    summary_daily_account_rows = []

    for plat in sorted(df1["Platform"].dropna().unique()):
        df_plat = df1[df1["Platform"] == plat].copy()

        # Helper mask
        # ==========================
        image_filled = (
            df_plat["image"].notna()
            & (df_plat["image"].astype(str).str.strip() != "")
        )

        image_empty = (
            df_plat["image"].isna()
            | (df_plat["image"].astype(str).str.strip() == "")
        )

        account_filled = (
            df_plat["account_impression"].notna()
            & (df_plat["account_impression"].astype(str).str.strip() != "")
        )

        account_empty = (
            df_plat["account_impression"].isna()
            | (df_plat["account_impression"].astype(str).str.strip() == "")
        )

        # Klasifikasi data
        # ==========================
        # Content -> image ada
        df_content = df_plat[image_filled]

        # Followers -> image kosong & account_impression kosong
        df_followers = df_plat[image_empty & account_empty]

        df_followers["Growth"] = pd.to_numeric(
            df_followers["Growth"],
            errors="coerce"
        )

        # Daily Account -> image kosong & account_impression terisi
        df_daily_account = df_plat[image_empty & account_filled]

        df_daily_account["account_impression"] = pd.to_numeric(
            df_daily_account["account_impression"],
            errors="coerce"
        )

        # Field Rule
        # ==========================
        # Checker
        if "checker" in df_content.columns and not df_content["checker"].dropna().empty:
            content_field_rule = (
                "Duplicate"
                if (df_content["checker"] == "Duplicate").any()
                else "Unique"
            )
        else:
            content_field_rule = "-"

        # Latest Followers
        if not df_followers.empty and not df_followers["Date"].dropna().empty:
            idx = df_followers["Date"].idxmax()
            followers_field_rule = df_followers.loc[idx, "Followers"]   # atau "Followers"
        else:
            followers_field_rule = "-"

        # Latest Daily Account Impression
        if not df_daily_account.empty and not df_daily_account["Date"].dropna().empty:
            idx = df_daily_account["Date"].idxmax()
            daily_account_field_rule = df_daily_account.loc[idx, "account_impression"]
        else:
            daily_account_field_rule = "-"

        # Summary - Content
        # ==========================
        if not df_content.empty:
            latest_row = df_content.loc[df_content["Date"].idxmax()]

            summary_content_rows.append({
                "Platform": f"{plat} Content",
                "Last Update": (
                    latest_row["Date"]
                    if pd.notna(latest_row["Date"])
                    else "-"
                ),         
                "Checker": content_field_rule,
            })

        # Summary - Followers
        # ==========================
        if not df_followers.empty:
            latest_row = df_followers.loc[df_followers["Date"].idxmax()]

            summary_followers_rows.append({
                "Platform": f"{plat} Followers",
                "Last Update": (
                    latest_row["Date"]
                    if pd.notna(latest_row["Date"])
                    else "-"
                ),
                "Checker": "-",
            })

        # Summary - Daily Account
        # ==========================
        if not df_daily_account.empty:
            latest_row = df_daily_account.loc[
                df_daily_account["Date"].idxmax()
            ]

            summary_daily_account_rows.append({
                "Platform": f"{plat} Daily Account",
                "Last Update": (
                    latest_row["Date"]
                    if pd.notna(latest_row["Date"])
                    else "-"
                ),
                "Checker": "-",
            })

    # Final Summary Table
    # ==========================
    latest_per_platform = pd.DataFrame(
        summary_content_rows
        + summary_followers_rows
        + summary_daily_account_rows
    )

    st.dataframe(
        latest_per_platform,
        use_container_width=True,
        hide_index=True
    )

else:
    missing = [c for c in required_cols if c not in df1.columns]
    st.warning(f"⚠️ Kolom tidak ditemukan: {missing}")