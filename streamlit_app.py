# Google SERP Keyword Extractor (Selenium + Streamlit)
# Updated: Uses your exact XPath for People Also Search For
# PAA: .related-question-pair span
# PASF: /html/body/div[3]/div/div[12]/div/div[3]/div/div[3]/div/div/div/div/div[2]/div → all <span> inside <a>

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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Page config
st.set_page_config(
    page_title="Google SERP Extractor (Custom XPath)",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google SERP Keyword Extractor")
st.caption("PAA: `.related-question-pair span` | PASF: Your XPath → all spans inside <a>")

# ──── DRIVER ─────────────────────────────────────────────────────
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    return driver

# ──── URL BUILDER ────────────────────────────────────────────────
def build_google_url(keyword, country, num=15):
    return f"https://www.google.com/search?q={quote_plus(keyword)}&num={num}&gl={country.lower()}&hl=en&pws=0"

# ──── PAA EXTRACTION (your original selector) ────────────────────
def extract_paa(driver, limit):
    questions = []
    try:
        spans = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
        for s in spans:
            text = s.text.strip()
            if text and text not in questions:
                questions.append(text)
            if len(questions) >= limit:
                break
    except:
        pass
    return questions

# ──── PASF EXTRACTION – YOUR EXACT XPATH APPROACH ─────────────────
def extract_pasf(driver, limit):
    results = []
    xpath = "/html/body/div[3]/div/div[12]/div/div[3]/div/div[3]/div/div/div/div/div[2]/div"
    try:
        container = driver.find_element(By.XPATH, xpath)
        links = container.find_elements(By.TAG_NAME, "a")
        for a in links:
            spans = a.find_elements(By.TAG_NAME, "span")
            for span in spans:
                text = span.text.strip()
                if text and text not in results:
                    results.append(text)
                if len(results) >= limit:
                    return results
            if len(results) >= limit:
                return results
    except (NoSuchElementException, Exception):
        pass
    return results

# ──── UI ─────────────────────────────────────────────────────────
uploaded_file = st.file_uploader("Upload CSV or Excel File", type=["csv", "xlsx"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df_input = pd.read_csv(uploaded_file)
    else:
        df_input = pd.read_excel(uploaded_file)

    st.success(f"Loaded {len(df_input)} rows")

    col1, col2 = st.columns(2)
    with col1:
        keyword_col = st.selectbox("Keyword Column", df_input.columns)
    with col2:
        country_col = st.selectbox("Country Column (US, PK, IN, etc.)", df_input.columns)

    st.markdown("**Preview**")
    st.dataframe(df_input.head(), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        max_items = st.number_input("Max items per section", 3, 30, 12)
    with col_b:
        delay_sec = st.slider("Delay between requests (seconds)", 3.0, 12.0, 5.5)

    if st.button("🚀 Start Extraction", type="primary", use_container_width=True):
        driver = get_driver()
        results = []
        progress = st.progress(0)
        status = st.empty()
        table = st.empty()

        total = len(df_input)

        for i, row in df_input.iterrows():
            keyword = str(row[keyword_col]).strip()
            country = str(row[country_col]).strip().upper()

            if not keyword or not country:
                continue

            status.markdown(f"Processing **{keyword}** ({country})")

            url = build_google_url(keyword, country)

            try:
                driver.get(url)
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(random.uniform(3.0, 6.5))  # Wait for dynamic content

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

            except Exception as e:
                results.append({
                    "Keyword": keyword,
                    "Country": country,
                    "Google URL": url,
                    "People Also Ask": "(error)",
                    "People Also Search For": "(error)",
                    "PAA count": 0,
                    "PASF count": 0
                })

            table.dataframe(pd.DataFrame(results), use_container_width=True)
            progress.progress((i + 1) / total)
            time.sleep(delay_sec)

        driver.quit()
        progress.empty()
        status.success("✅ Extraction completed!")

        csv = pd.DataFrame(results).to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, "serp_results.csv", "text/csv")

else:
    st.info("Please upload your keyword file to start.")
