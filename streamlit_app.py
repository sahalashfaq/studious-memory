# Google SERP Keyword Extractor (Selenium + Streamlit)
# Extracts People Also Ask + People Also Search For
# Updated 2026 version - with better waiting, error handling and live progress

import streamlit as st
import pandas as pd
import time
import random
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# Page configuration
st.set_page_config(
    page_title="Google SERP Keyword Extractor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ──── DRIVER SETUP ────────────────────────────────────────────────
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(40)
    return driver

# ──── URL BUILDER ─────────────────────────────────────────────────
def build_google_url(keyword, country_code, num_results=15):
    return (
        f"https://www.google.com/search?"
        f"q={quote_plus(keyword)}"
        f"&num={num_results}"
        f"&gl={country_code.lower()}"
        f"&hl=en"
        f"&pws=0"
    )

# ──── EXTRACTION FUNCTIONS ────────────────────────────────────────
def extract_paa(driver, limit):
    questions = []
    try:
        spans = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
        for span in spans:
            text = span.text.strip()
            if text and text not in questions:
                questions.append(text)
            if len(questions) >= limit:
                break
    except:
        pass
    return questions


def extract_pasf(driver, limit):
    terms = []
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
        for link in links:
            text = link.text.strip()
            if text and text not in terms:
                terms.append(text)
            if len(terms) >= limit:
                break
    except:
        pass
    return terms


# ──── MAIN INTERFACE ──────────────────────────────────────────────
st.title("🔍 Google SERP Keyword Extractor")
st.caption("Extracts People Also Ask & People Also Search For using Selenium")

# Upload file
uploaded_file = st.file_uploader(
    "Upload your keywords (CSV or Excel)",
    type=["csv", "xlsx"],
    help="File should contain at least 'Keyword' and 'Country' columns (e.g. PK, US, IN)"
)

if uploaded_file is not None:
    # Read file
    try:
        if uploaded_file.name.endswith(".csv"):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)

        st.success(f"Loaded {len(df_input)} keywords")

        col1, col2 = st.columns(2)
        with col1:
            keyword_col = st.selectbox("Keyword column", df_input.columns)
        with col2:
            country_col = st.selectbox("Country code column (US, PK, IN...)", df_input.columns)

        st.markdown("**Preview (first 5 rows)**")
        st.dataframe(df_input.head(), use_container_width=True)

    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

    # Settings
    st.subheader("Extraction Settings")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        max_items = st.number_input(
            "Max items per section", min_value=3, max_value=30, value=12, step=1
        )
    with col_b:
        wait_time = st.slider(
            "Wait time per page (seconds)", 2.5, 10.0, 4.5, 0.5,
            help="Longer wait helps with dynamic content loading"
        )
    with col_c:
        random_delay = st.checkbox("Add random delay between requests", value=True)

    # Start button
    if st.button("🚀 Start Extraction", type="primary", use_container_width=True):
        driver = get_driver()

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        result_table = st.empty()

        total = len(df_input)

        for idx, row in df_input.iterrows():
            keyword = str(row.get(keyword_col, "")).strip()
            country = str(row.get(country_col, "us")).strip().upper()

            if not keyword or not country:
                continue

            status_text.markdown(f"Processing **{keyword}**  ({country}) ...")

            url = build_google_url(keyword, country, 15)

            try:
                driver.get(url)

                # Wait for basic page load
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Additional wait for dynamic SERP features
                time.sleep(wait_time + random.uniform(0.5, 2.5) if random_delay else 0)

                paa = extract_paa(driver, max_items)
                pasf = extract_pasf(driver, max_items)

                results.append({
                    "Keyword": keyword,
                    "Country": country,
                    "Google URL": url,
                    "People Also Ask": " • ".join(paa) if paa else "(not found)",
                    "People Also Search For": " • ".join(pasf) if pasf else "(not found)",
                    "PAA count": len(paa),
                    "PASF count": len(pasf)
                })

            except (TimeoutException, WebDriverException) as e:
                results.append({
                    "Keyword": keyword,
                    "Country": country,
                    "Google URL": url,
                    "People Also Ask": f"(timeout/error: {str(e)[:60]})",
                    "People Also Search For": "(timeout/error)",
                    "PAA count": 0,
                    "PASF count": 0
                })

            # Live update
            current_results = pd.DataFrame(results)
            result_table.dataframe(
                current_results,
                column_config={
                    "Google URL": st.column_config.LinkColumn("Open in Google"),
                    "People Also Ask": st.column_config.TextColumn(width="large"),
                    "People Also Search For": st.column_config.TextColumn(width="large"),
                },
                use_container_width=True,
                hide_index=True
            )

            progress_bar.progress((idx + 1) / total)

        driver.quit()
        progress_bar.empty()
        status_text.success("Extraction completed!")

        # Final download buttons
        st.subheader("Download Results")
        col_download1, col_download2 = st.columns(2)

        with col_download1:
            csv = current_results.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="google_serp_results.csv",
                mime="text/csv"
            )

        with col_download2:
            excel_buffer = pd.ExcelWriter("temp_results.xlsx", engine='openpyxl')
            current_results.to_excel(excel_buffer, index=False)
            excel_buffer.close()

            with open("temp_results.xlsx", "rb") as f:
                st.download_button(
                    label="Download Excel",
                    data=f,
                    file_name="google_serp_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

else:
    st.info("Please upload a CSV or Excel file containing your keywords")
