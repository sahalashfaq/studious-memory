import streamlit as st
import pandas as pd
import time
import random
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Google SERP – PAA + Related Searches",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🔍 Google SERP Extractor")
st.caption("People Also Ask + People Also Search For • Using .related-question-pair span & a.ggLgoc")

# ────────────────────────────────────────────────
# DRIVER SETUP
# ────────────────────────────────────────────────
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.set_page_load_timeout(40)
    return driver

# ────────────────────────────────────────────────
# URL BUILDER
# ────────────────────────────────────────────────
def build_google_url(keyword, country_code, num_results=15):
    return (
        f"https://www.google.com/search?"
        f"q={quote_plus(keyword)}"
        f"&num={num_results}"
        f"&gl={country_code.lower()}"
        f"&hl=en"
        f"&pws=0"
    )

# ────────────────────────────────────────────────
# EXTRACTION FUNCTIONS (your exact selectors)
# ────────────────────────────────────────────────
def extract_paa(driver, limit):
    questions = []
    try:
        spans = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
        # st.write(f"DEBUG: found {len(spans)} .related-question-pair spans")  # ← uncomment to debug
        for s in spans:
            text = s.text.strip()
            if text and text not in questions:
                questions.append(text)
            if len(questions) >= limit:
                break
    except:
        pass
    return questions

def extract_pasp(driver, limit):
    terms = []
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
        # st.write(f"DEBUG: found {len(links)} a.ggLgoc links")  # ← uncomment to debug
        for a in links:
            text = a.text.strip()
            if text and text not in terms:
                terms.append(text)
            if len(terms) >= limit:
                break
    except:
        pass
    return terms

# ────────────────────────────────────────────────
# SIDEBAR CONTROLS (optional – can be removed)
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")
    max_paa = st.slider("Max People Also Ask", 4, 25, 12)
    max_pasf = st.slider("Max People Also Search For", 4, 20, 10)
    delay_base = st.slider("Base delay (seconds)", 2.0, 8.0, 4.0, help="Higher = safer")

# ────────────────────────────────────────────────
# MAIN UI
# ────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload CSV or Excel (Keyword + Country columns)",
    type=["csv", "xlsx"]
)

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)

        st.success(f"Loaded {len(df_input)} rows")

        col1, col2 = st.columns(2)
        with col1:
            keyword_col = st.selectbox("Keyword column", df_input.columns)
        with col2:
            country_col = st.selectbox("Country code column (PK, US, IN...)", df_input.columns)

        st.markdown("**Preview (first 5 rows)**")
        st.dataframe(df_input.head(5), use_container_width=True)

        if st.button("🚀 Start Extraction", type="primary"):
            driver = get_driver()

            results = []
            live_table = st.empty()
            progress = st.progress(0)
            status = st.empty()

            total = len(df_input)

            for i, row in df_input.iterrows():
                keyword = str(row.get(keyword_col, "")).strip()
                country = str(row.get(country_col, "pk")).strip().upper()

                if not keyword or not country:
                    continue

                status.markdown(f"🔍 **{i+1}/{total}** – {keyword} ({country})")

                url = build_google_url(keyword, country, max_paa + max_pasf)

                try:
                    driver.get(url)

                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
                    )

                    time.sleep(random.uniform(2.5, 5.0))  # let dynamic content load

                    paa_list = extract_paa(driver, max_paa)
                    pasf_list = extract_pasp(driver, max_pasf)

                    results.append({
                        "Keyword": keyword,
                        "Country": country,
                        "Google URL": url,
                        "People Also Ask": " • ".join(paa_list) if paa_list else "(none found)",
                        "People Also Search For": " • ".join(pasf_list) if pasf_list else "(none found)",
                        "PAA count": len(paa_list),
                        "PASF count": len(pasf_list)
                    })

                except Exception as e:
                    results.append({
                        "Keyword": keyword,
                        "Country": country,
                        "Google URL": url,
                        "People Also Ask": "(error)",
                        "People Also Search For": "(error)",
                        "PAA count": 0,
                        "PASF count": 0,
                        "Note": str(e)[:80]
                    })

                # Live table update
                df_live = pd.DataFrame(results)
                live_table.dataframe(
                    df_live,
                    column_config={
                        "Google URL": st.column_config.LinkColumn("Open in Google"),
                        "People Also Ask": st.column_config.TextColumn(width="large"),
                        "People Also Search For": st.column_config.TextColumn(width="large"),
                    },
                    use_container_width=True,
                    hide_index=True
                )

                progress.progress((i + 1) / total)

                # Variable anti-detection delay
                time.sleep(delay_base + random.uniform(-1.0, 3.0))

            driver.quit()
            progress.empty()
            status.success("Extraction completed ✓")

            # Final download buttons
            st.download_button(
                "⬇️ Download CSV",
                df_live.to_csv(index=False).encode('utf-8'),
                "google_serp_results.csv",
                "text/csv"
            )

            excel_buffer = pd.ExcelWriter("google_serp_results.xlsx", engine='openpyxl')
            df_live.to_excel(excel_buffer, index=False)
            excel_buffer.close()

            with open("google_serp_results.xlsx", "rb") as f:
                st.download_button(
                    "⬇️ Download Excel",
                    f,
                    "google_serp_results.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Could not process file: {e}")

else:
    st.info("Upload a CSV or Excel file containing keywords and country codes.")
