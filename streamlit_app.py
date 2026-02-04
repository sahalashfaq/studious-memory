# Google SERP Keyword Extractor – Single Column Layout (2026 Cloud Fix)
# No tabs, no sidebar – everything in one flow

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
# PAGE CONFIG – Wide + clean
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Google SERP Extractor",
    page_icon="🔍",
    layout="wide"
)

# Simple styling
st.markdown("""
    <style>
    .status-ok  { color: #2ecc71; font-weight: bold; }
    .status-warn { color: #e67e22; font-weight: bold; }
    .big-title { font-size: 32px; font-weight: bold; margin-bottom: 8px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="big-title">🔍 Google SERP Keyword Extractor</div>', unsafe_allow_html=True)
st.caption("Extracts People Also Ask + People Also Search For • Single page layout • Lahore-friendly 🇵🇰")

# ────────────────────────────────────────────────
# CONTROLS – All at the top, no sidebar
# ────────────────────────────────────────────────
st.markdown("### ⚙️ Settings")
col1, col2, col3 = st.columns(3)
with col1:
    max_paa = st.slider("Max People Also Ask", 4, 20, 10)
with col2:
    max_pasp = st.slider("Max People Also Search", 4, 15, 8)
with col3:
    delay_sec = st.slider("Delay between requests (seconds)", 2.0, 8.0, 4.0, help="Higher = safer from blocks")

advanced_crawl = st.checkbox(
    "Advanced mode: Open each People Also Ask question in new browser tab (after extraction)",
    value=False,
    help="Warning: can open 10–50+ tabs quickly – use only on small files!"
)

st.markdown("---")

# ────────────────────────────────────────────────
# FILE UPLOAD & COLUMN SELECTION
# ────────────────────────────────────────────────
st.markdown("### 📤 Upload your file")
uploaded = st.file_uploader("CSV or Excel file (must have Keyword + Country columns)", type=["csv", "xlsx", "xls"])

if uploaded:
    try:
        df_input = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.success(f"Loaded **{len(df_input)}** rows")

        colA, colB = st.columns(2)
        with colA:
            kw_col = st.selectbox("Keyword column", df_input.columns)
        with colB:
            country_col = st.selectbox("Country code column (e.g. PK, US, IN)", df_input.columns)

        st.markdown("**Preview (first 5 rows)**")
        st.dataframe(df_input.head(6), use_container_width=True)

    except Exception as e:
        st.error(f"Could not read file: {e}")
        st.stop()

st.markdown("---")

# ────────────────────────────────────────────────
# START BUTTON + PROCESSING
# ────────────────────────────────────────────────
if st.button("🚀 Start Extraction", type="primary") and uploaded:
    with st.spinner("Starting browser & extracting data..."):
        # Driver setup
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(40)

    results = []
    progress = st.progress(0)
    status = st.empty()

    total = len(df_input)

    for i, row in df_input.iterrows():
        keyword = str(row.get(kw_col, "")).strip()
        cc = str(row.get(country_col, "")).strip().upper()

        if not keyword or not cc:
            continue

        status.markdown(f"<span class='status-ok'>Now processing:</span> **{keyword}** ({cc})", unsafe_allow_html=True)

        url = f"https://www.google.com/search?q={quote_plus(keyword)}&num=15&gl={cc.lower()}&hl=en&pws=0"

        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(1.0, 2.5))  # Let JS load

            # Extract PAA
            paa_list = []
            try:
                els = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
                for el in els:
                    txt = el.text.strip()
                    if txt and txt not in paa_list:
                        paa_list.append(txt)
                    if len(paa_list) >= max_paa:
                        break
            except:
                pass

            # Extract PASP
            pasp_list = []
            try:
                links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
                for a in links:
                    txt = a.text.strip()
                    if txt and txt not in pasp_list:
                        pasp_list.append(txt)
                    if len(pasp_list) >= max_pasp:
                        break
            except:
                pass

            row_data = {
                "Keyword": keyword,
                "Country": cc,
                "Google URL": url,
                "People Also Ask": " • ".join(paa_list),
                "People Also Search For": " • ".join(pasp_list),
                "PAA Count": len(paa_list),
                "PASP Count": len(pasp_list),
                "Note": ""
            }

            # Advanced crawling
            if advanced_crawl and paa_list:
                for q in paa_list[:4]:  # limit to 4 to avoid too many tabs
                    q_url = f"https://www.google.com/search?q={quote_plus(q)}&gl={cc.lower()}"
                    driver.execute_script(f"window.open('{q_url}', '_blank');")
                    time.sleep(0.7)

            results.append(row_data)

        except Exception as e:
            results.append({
                "Keyword": keyword,
                "Country": cc,
                "Google URL": url,
                "People Also Ask": "",
                "People Also Search For": "",
                "PAA Count": 0,
                "PASP Count": 0,
                "Note": f"Error: {str(e)[:80]}"
            })

        progress.progress((i + 1) / total)
        time.sleep(delay_sec + random.uniform(-0.6, 1.2))

    driver.quit()
    progress.empty()
    status.empty()

    df_results = pd.DataFrame(results)

    st.success(f"Extraction finished! Processed {len(df_results)} keywords.")

    # ── RESULTS DISPLAY ──
    st.markdown("### 📊 Results")
    st.dataframe(
        df_results,
        column_config={
            "Google URL": st.column_config.LinkColumn("Open Search"),
            "People Also Ask": st.column_config.TextColumn(width="large"),
            "People Also Search For": st.column_config.TextColumn(width="large"),
        },
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "⬇️ Download CSV",
        df_results.to_csv(index=False),
        "serp_results.csv",
        "text/csv"
    )

    st.markdown("---")

    # ── TIPS SECTION (now inline) ──
    st.markdown("### 💡 Quick Tips")
    st.markdown("""
    - Use **4–6 second delay** for >30 keywords to avoid blocks/CAPTCHA  
    - **Advanced mode** opens new tabs – only enable for small tests (5–15 rows max)  
    - Google sometimes changes CSS selectors → PAA/PASP might miss occasionally  
    - For Pakistan (PK), results are usually very accurate for local + English searches  
    - **Google Trends disabled** due to library compatibility issue on Streamlit Cloud (urllib3 conflict)  
      → You can fix locally with `pip install urllib3<2` but it may break other packages
    """)

else:
    if not uploaded:
        st.info("Please upload your CSV/Excel file to begin.")
