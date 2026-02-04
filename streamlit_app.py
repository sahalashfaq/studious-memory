# Google SERP Keyword Extractor – Streamlit Cloud Ready (2026 Edition)
# People Also Ask + People Also Search For – with nice layout

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

# ────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Google SERP Keyword Insights",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ────────────────────────────────────────────────
# CUSTOM CSS (optional – clean look)
# ────────────────────────────────────────────────
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .big-font {
        font-size: 22px !important;
        font-weight: bold;
    }
    .status-ok  { color: #2ecc71; font-weight: bold; }
    .status-warn { color: #e67e22; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# SELENIUM DRIVER (Cloud-optimized)
# ────────────────────────────────────────────────
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(35)
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
# EXTRACTORS
# ────────────────────────────────────────────────
def extract_paa(driver, limit=12):
    questions = []
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
        for el in elements:
            txt = el.text.strip()
            if txt and txt not in questions:
                questions.append(txt)
            if len(questions) >= limit:
                break
    except:
        pass
    return questions

def extract_pasp(driver, limit=10):
    terms = []
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
        for a in links:
            txt = a.text.strip()
            if txt and txt not in terms:
                terms.append(txt)
            if len(terms) >= limit:
                break
    except:
        pass
    return terms

# ────────────────────────────────────────────────
# SIDEBAR – CONTROLS
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Controls")
    max_paa  = st.slider("Max People Also Ask",  4, 20, 10)
    max_pasp = st.slider("Max People Also Search", 4, 15, 8)
    delay    = st.slider("Delay between requests (sec)", 1.8, 6.0, 3.2)
    st.caption("Higher delay = lower block risk")

# ────────────────────────────────────────────────
# MAIN UI – TABS
# ────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📤 Upload & Run", "📊 Results", "ℹ️ About & Tips"])

with tab1:
    st.subheader("Upload keywords & countries")

    uploaded_file = st.file_uploader(
        "Upload CSV or Excel (must have Keyword & Country columns)",
        type=["csv", "xlsx", "xls"]
    )

    if uploaded_file:
        try:
            if uploaded_file.name.endswith(".csv"):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)

            st.success(f"Loaded **{len(df_input)}** rows")

            col1, col2 = st.columns(2)
            with col1:
                keyword_col = st.selectbox("Keyword column", df_input.columns, index=0)
            with col2:
                country_col = st.selectbox("Country code column (US, PK, IN...)", df_input.columns, index=1)

            st.markdown(f"**Preview (first 5 rows)**")
            st.dataframe(df_input.head(), use_container_width=True)

            if st.button("🚀 Start SERP Extraction", type="primary"):
                if keyword_col not in df_input or country_col not in df_input:
                    st.error("Selected columns not found in file.")
                else:
                    with st.spinner("Initializing browser..."):
                        driver = get_driver()

                    results = []
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    eta_placeholder = st.empty()

                    total = len(df_input)

                    for idx, row in df_input.iterrows():
                        kw   = str(row[keyword_col]).strip()
                        cc   = str(row[country_col]).strip().upper()

                        if not kw or not cc:
                            continue

                        status_text.markdown(f"<span class='status-ok'>Processing:</span> **{kw}** ({cc})", unsafe_allow_html=True)

                        url = build_google_url(kw, cc)

                        try:
                            driver.get(url)
                            WebDriverWait(driver, 18).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                            time.sleep(random.uniform(0.8, 2.1))  # JS render delay

                            paa_list  = extract_paa(driver, max_paa)
                            pasp_list = extract_pasp(driver, max_pasp)

                            results.append({
                                "Seed Keyword": kw,
                                "Country": cc,
                                "Google URL": url,
                                "People Also Ask": " • ".join(paa_list),
                                "People Also Search For": " • ".join(pasp_list),
                                "PAA Count": len(paa_list),
                                "PASP Count": len(pasp_list)
                            })

                        except Exception as e:
                            results.append({
                                "Seed Keyword": kw,
                                "Country": cc,
                                "Google URL": url,
                                "People Also Ask": "",
                                "People Also Search For": "",
                                "PAA Count": 0,
                                "PASP Count": 0,
                                "Error": str(e)[:120]
                            })

                        # Progress & fake ETA
                        prog = (idx + 1) / total
                        progress_bar.progress(prog)
                        elapsed = (idx + 1) * delay * 1.3
                        remaining = (total - idx - 1) * delay * 1.4
                        eta_placeholder.caption(f"Elapsed ~{elapsed//60:.0f} min • ETA ~{remaining//60:.0f} min")

                        time.sleep(delay + random.uniform(-0.7, 1.3))

                    driver.quit()
                    progress_bar.empty()
                    status_text.empty()
                    eta_placeholder.empty()

                    # Save to session state
                    st.session_state["results_df"] = pd.DataFrame(results)

                    st.success("Extraction finished! See Results tab →")
                    st.balloons()

        except Exception as e:
            st.error(f"File reading error: {e}")

with tab2:
    if "results_df" in st.session_state:
        df = st.session_state["results_df"]

        st.subheader("Extraction Results")

        colA, colB, colC = st.columns(3)
        colA.metric("Keywords processed", len(df))
        colB.metric("Avg PAA per keyword", f"{df['PAA Count'].mean():.1f}")
        colC.metric("Avg PASP per keyword", f"{df['PASP Count'].mean():.1f}")

        with st.expander("Full Results Table", expanded=True):
            st.dataframe(
                df,
                column_config={
                    "Google URL": st.column_config.LinkColumn("Google URL"),
                    "People Also Ask": st.column_config.TextColumn(width="medium"),
                    "People Also Search For": st.column_config.TextColumn(width="medium"),
                },
                use_container_width=True,
                hide_index=True
            )

        col_download1, col_download2 = st.columns(2)
        with col_download1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "serp_keywords.csv", "text/csv")

        with col_download2:
            excel_buffer = pd.ExcelWriter("serp_keywords.xlsx", engine='openpyxl')
            df.to_excel(excel_buffer, index=False)
            excel_buffer.close()
            with open("serp_keywords.xlsx", "rb") as f:
                st.download_button(
                    "Download Excel",
                    f,
                    "serp_keywords.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("Run extraction from the first tab to see results here.")

with tab3:
    st.subheader("About this tool")
    st.markdown("""
    - Extracts **People Also Ask** & **People Also Search For** from Google SERP  
    - Country-specific results via `gl=` parameter  
    - Designed & tested for **Streamlit Community Cloud** (uses system Chromium)  
    - Rate limiting & random delays included to reduce blocking risk  

    **Tips for best results**
    - Use 3–5 second delay for >50 keywords  
    - Add proxy support if you get CAPTCHA often (not included here)  
    - Keep keyword list < 200–300 per run on free cloud tier  
    """)

    st.caption("Made with ❤️ in 2026 • Enjoy responsibly")
