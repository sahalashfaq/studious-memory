# Google SERP Keyword Extractor (Selenium + Streamlit)
# ---------------------------------------------------

import streamlit as st
import pandas as pd
import time
import random
from urllib.parse import quote_plus

# ──── Selenium imports ────────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.chrome.service import Service               # ← THIS WAS MISSING
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Google SERP Keyword Extractor",
    layout="wide"
)

# ---------------------------------------------------
# SELENIUM DRIVER
# ---------------------------------------------------
def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    # This line now works because we imported Service
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(40)
    return driver


def build_google_url(keyword, country, num):
    return (
        "https://www.google.com/search?"
        f"q={quote_plus(keyword)}"
        f"&num={num}"
        f"&gl={country.lower()}"
        f"&hl=en"
        f"&pws=0"
    )


# ---------------------------------------------------
# EXTRACTION (with filtering for cleaner results)
# ---------------------------------------------------
def extract_paa(driver, limit):
    questions = []
    try:
        spans = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
        for s in spans:
            text = s.text.strip()
            # Filter out junk (icons, arrows, short text)
            if len(text) > 15 and ('?' in text or len(text.split()) > 5) and text not in questions:
                questions.append(text)
            if len(questions) >= limit:
                break
    except:
        pass
    return questions


def extract_pasp(driver, limit):
    results = []
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
        for a in links:
            text = a.text.strip()
            if text and text not in results:
                results.append(text)
            if len(results) >= limit:
                break
    except:
        pass
    return results


# ---------------------------------------------------
# UI
# ---------------------------------------------------
st.title("🔍 Google SERP Keyword Extractor")
st.caption("People Also Ask + People Also Search For | Country Accurate")

uploaded_file = st.file_uploader(
    "Upload CSV or Excel File",
    type=["csv", "xlsx"]
)

if not uploaded_file:
    st.info("Please upload a CSV or Excel file to start.")
    st.stop()

# ---------------------------------------------------
# LOAD FILE
# ---------------------------------------------------
try:
    if uploaded_file.name.endswith(".csv"):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)
    st.success(f"Loaded {len(df_input)} rows")
except Exception as e:
    st.error(f"Error reading file: {e}")
    st.stop()

# ---------------------------------------------------
# COLUMN MAPPING
# ---------------------------------------------------
st.subheader("📌 Column Mapping")

keyword_col = st.selectbox("Keyword Column", df_input.columns)
country_col = st.selectbox("Country Column (US, PK, IN, etc.)", df_input.columns)

max_keywords = st.number_input(
    "Max items per section",
    min_value=3,
    max_value=50,
    value=12
)

if st.button("🚀 Start Extraction", type="primary"):

    driver = init_driver()

    results = []
    progress = st.progress(0)
    status = st.empty()
    live_table = st.empty()

    for i, row in df_input.iterrows():
        keyword = str(row[keyword_col]).strip()
        country = str(row[country_col]).strip().upper()

        if not keyword or not country:
            continue

        status.markdown(f"🔍 Processing **{keyword}** ({country})")

        url = build_google_url(keyword, country, max_keywords)

        try:
            driver.get(url)

            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            time.sleep(3.0 + random.uniform(0.5, 2.0))  # Allow dynamic content

            paa = extract_paa(driver, max_keywords)
            pasp = extract_pasp(driver, max_keywords)

            results.append({
                "seed_keyword": keyword,
                "country": country,
                "google_url": url,
                "people_also_ask": ", ".join(paa) if paa else "(not found)",
                "people_also_search_for": ", ".join(pasp) if pasp else "(not found)"
            })

        except Exception as e:
            results.append({
                "seed_keyword": keyword,
                "country": country,
                "google_url": url,
                "people_also_ask": f"(error: {str(e)[:80]})",
                "people_also_search_for": ""
            })

        # Live preview
        df_live = pd.DataFrame(results)
        live_table.dataframe(df_live, use_container_width=True)

        progress.progress((i + 1) / len(df_input))

    driver.quit()
    progress.empty()
    status.success("Extraction completed!")

    # ---------------------------------------------------
    # FINAL RESULTS & DOWNLOAD
    # ---------------------------------------------------
    st.subheader("✅ Final Results")
    st.dataframe(df_live, use_container_width=True)

    csv = df_live.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Download CSV",
        csv,
        "serp_keywords.csv",
        "text/csv"
    )

    # Optional Excel download
    excel_buffer = pd.ExcelWriter("serp_keywords.xlsx", engine='openpyxl')
    df_live.to_excel(excel_buffer, index=False)
    excel_buffer.close()

    with open("serp_keywords.xlsx", "rb") as f:
        st.download_button(
            "⬇️ Download Excel",
            f,
            "serp_keywords.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
