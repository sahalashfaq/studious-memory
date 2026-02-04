# Google SERP Keyword Extractor (Selenium + Streamlit)
# ---------------------------------------------------
# Updated with filtering for PAA and user-provided XPath for PASF

import streamlit as st
import pandas as pd
import time
from urllib.parse import quote_plus

from selenium import webdriver
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
# EXTRACTION (Updated with filtering and XPath)
# ---------------------------------------------------
def extract_paa(driver, limit):
    questions = []
    try:
        spans = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
        for s in spans:
            text = s.text.strip()
            # Filter for plausible questions: length > 15 chars and contains '?' or sentence-like
            if len(text) > 15 and ('?' in text or len(text.split()) > 5) and text not in questions:
                questions.append(text)
            if len(questions) >= limit:
                break
    except:
        pass
    return questions


def extract_pasp(driver, limit):
    results = []
    # Use the user-provided XPath for PASF container
    pasp_xpath = "/html/body/div[3]/div/div[12]/div/div[3]/div/div[3]/div/div/div/div/div[2]/div"
    try:
        container = driver.find_element(By.XPATH, pasp_xpath)
        # All spans inside <a> tags within the container
        spans_in_a = container.find_elements(By.CSS_SELECTOR, "a span")
        for span in spans_in_a:
            text = span.text.strip()
            if text and text not in results:
                results.append(text)
            if len(results) >= limit:
                break
    except TimeoutException:
        pass
    except Exception:
        pass
    return results


# ---------------------------------------------------
# UI
# ---------------------------------------------------
st.title("🔍 Google SERP Keyword Extractor (Updated)")
st.caption("People Also Ask + People Also Search For | Country Accurate | With Filtering and XPath")

uploaded_file = st.file_uploader(
    "Upload CSV or Excel File",
    type=["csv", "xlsx"]
)

if not uploaded_file:
    st.stop()

# ---------------------------------------------------
# LOAD FILE
# ---------------------------------------------------
if uploaded_file.name.endswith(".csv"):
    df_input = pd.read_csv(uploaded_file)
else:
    df_input = pd.read_excel(uploaded_file)

st.success(f"Loaded {len(df_input)} rows")

# ---------------------------------------------------
# COLUMN MAPPING
# ---------------------------------------------------
st.subheader("📌 Column Mapping")

keyword_col = st.selectbox("Keyword Column", df_input.columns)
country_col = st.selectbox("Country Column (US, PK, IN, etc.)", df_input.columns)

max_keywords = st.number_input(
    "Max keywords to extract per row",
    min_value=3,
    max_value=50,
    value=10
)

start = st.button("Start Extraction")

if not start:
    st.stop()

# ---------------------------------------------------
# PROCESS
# ---------------------------------------------------
driver = init_driver()

results = []
progress = st.progress(0)
status = st.empty()
live_table = st.empty()  # For live results

for i, row in df_input.iterrows():
    keyword = str(row[keyword_col]).strip()
    country = str(row[country_col]).strip().upper()

    if not keyword or not country:
        continue

    status.write(f"🔍 Processing **{keyword}** ({country})")

    url = build_google_url(keyword, country, max_keywords)

    try:
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        time.sleep(3.5 + random.uniform(0.5, 1.5))  # Allow JS to load SERP features

        paa = extract_paa(driver, max_keywords)
        pasp = extract_pasp(driver, max_keywords)

        results.append({
            "seed_keyword": keyword,
            "country": country,
            "google_url": url,
            "people_also_ask": ", ".join(paa),
            "people_also_search_for": ", ".join(pasp)
        })

    except Exception:
        results.append({
            "seed_keyword": keyword,
            "country": country,
            "google_url": url,
            "people_also_ask": "",
            "people_also_search_for": ""
        })

    # Live update table
    df_live = pd.DataFrame(results)
    live_table.dataframe(df_live, use_container_width=True)

    progress.progress((i + 1) / len(df_input))
    time.sleep(2.5 + random.uniform(0.5, 1.0))  # rate-limit protection

driver.quit()
progress.empty()
status.empty()

# ---------------------------------------------------
# RESULTS
# ---------------------------------------------------
df_results = pd.DataFrame(results)

st.subheader("✅ Extraction Results")
st.dataframe(df_results, use_container_width=True)

# ---------------------------------------------------
# EXPORT
# ---------------------------------------------------
csv = df_results.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download CSV",
    csv,
    "serp_keywords.csv",
    "text/csv"
)

excel_path = "serp_keywords.xlsx"
df_results.to_excel(excel_path, index=False)

with open(excel_path, "rb") as f:
    st.download_button(
        "⬇️ Download Excel",
        f,
        "serp_keywords.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

st.success("🎯 Extraction completed successfully")
