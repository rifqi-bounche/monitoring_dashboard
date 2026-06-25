import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
from auth import check_login

st.title("Last Update Monitoring")
check_login()

SHEET1_ID = "13q8avPIV2RjBg1tIUeJsd6U23wfOAann30S-d6moQ84" # sosmed fanpagekarma
SHEET2_ID = "1NQgDn4nylze5FqE7LiPbiW7de9F9BITx8T3FveX1Azc" # data windsor

SHEET1_NAME = "All Content"
SHEET2_NAME = "Master Data Ads"

@st.cache_data(ttl=60)
def load_dealer_bq():

    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )

    client = bigquery.Client(
        credentials=credentials,
        project=credentials.project_id
    )

    query = """
    SELECT
        'Dealer Leads' AS Source,
        MAX(
            COALESCE(
                SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', created_at),
                SAFE.PARSE_DATETIME('%m/%e/%Y %H:%M:%S', created_at)
            )
        ) AS Last_Update
    FROM `bigquery-499207.leads.dealer_leads`

    UNION ALL

    SELECT
        'Events' AS Source,
        MAX(
            COALESCE(
                SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', created_at),
                SAFE.PARSE_DATETIME('%m/%e/%Y %H:%M:%S', created_at)
            )
        ) AS Last_Update
    FROM `bigquery-499207.leads.events`

    UNION ALL

    SELECT
        'Online Leads' AS Source,
        MAX(
            COALESCE(
                SAFE.PARSE_DATETIME('%Y-%m-%d %H:%M:%S', create_time),
                SAFE.PARSE_DATETIME('%m/%e/%Y %H:%M:%S', create_time)
            )
        ) AS Last_Update
    FROM `bigquery-499207.leads.online_leads`
    """

    rows = client.query(query).result()
    return pd.DataFrame([dict(row.items()) for row in rows])
st.divider()

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

# =================== read data windsor
try:
    df2 = load_data(SHEET2_ID, SHEET2_NAME)
except Exception as e:
    st.error(f"❌ Gagal load data: {e}")
    st.stop()
try:
    df3 = load_dealer_bq()
except Exception as e:
    st.error(f"❌ Gagal load dealer dari BigQuery: {e}")
    st.stop()


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
st.markdown("### 🕐 Latest Update per Platform (fanpagekarma)")

required_cols = ["Date", "link", "Platform", "image"]

if all(c in df1.columns for c in required_cols):
    df1["Date"] = pd.to_datetime(df1["Date"], errors="coerce")

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

st.divider()

# ==========================
# Data Windsor
# ==========================

st.markdown("### 🕐 Latest Update per  Platform (Windsor)")
 
required_cols_2 = ["Date", "Platform"]
 
if all(c in df2.columns for c in required_cols_2):
    df2["Date"] = pd.to_datetime(df2["Date"], errors="coerce")
 
    summary_windsor_rows = []
 
    for pub_plat in sorted(df2["Platform"].dropna().unique()):
        df_pub = df2[df2["Platform"] == pub_plat].copy()
 
        if df_pub["Date"].dropna().empty:
            continue
 
        latest_row = df_pub.iloc[-1]
 
        # Checker
        checker_val = (
            "Duplicate" if (df_pub["checker"] == "Duplicate").any() else "Unique"
        ) if "checker" in df_pub.columns else "-"
 
        # Link (opsional, jika ada)
        if "Media URL" not in df_pub.columns or pub_plat == "google":
            link_val = latest_row["Landing Page"] if "Landing Page" in df_pub.columns and pd.notna(latest_row["Landing Page"]) else "-"
        else:
            link_val = latest_row["Media URL"] if pd.notna(latest_row["Media URL"]) else "-"
 
        summary_windsor_rows.append({
            "Platform": pub_plat,
            "Last Update": latest_row["Date"] if pd.notna(latest_row["Date"]) else "-",
        })
 
    latest_windsor = pd.DataFrame(summary_windsor_rows)
    st.dataframe(latest_windsor, use_container_width=True, hide_index=True)
 
else:
    missing = [c for c in required_cols_2 if c not in df2.columns]
    st.warning(f"⚠️ Kolom tidak ditemukan di Sheet2: {missing}")
    st.write("Kolom tersedia:", df2.columns.tolist())
 
st.divider()

st.markdown("## 🏬 Dealer")
st.dataframe(
    df3,
    use_container_width=True,
    hide_index=True
)