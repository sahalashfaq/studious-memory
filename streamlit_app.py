# Google SERP People Also Ask + People Also Search For Extractor
# Using the exact selectors you requested:
#   - People Also Ask: .related-question-pair span
#   - People Also Search For: a.ggLgoc

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
from selenium.common.exceptions import TimeoutException

# ────────────────────────────────────────────────
# Page config
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Google SERP PAA + PASF Extractor",
    page_icon="🔍",
    layout="wide"
)

st.title("Google People Also Ask & People Also Search For Extractor")
st.caption("Using selectors: .related-question-pair span  •  a.ggLgoc")

# ────────────────────────────────────────────────
# Controls
# ────────────────────────────────────────────────
st.markdown("### Settings")

col_delay, col_paa, col_pasp = st.columns([3, 2, 2])

with col_delay:
    delay_seconds = st.slider(
        "Delay between requests (seconds)",
        min_value=3.0,
        max_value=12.0,
        value=5.5,
        step=0.5,
        help="Higher value → lower risk of blocks / CAPTCHA"
    )

with col_paa:
    max_paa = st.number_input("Max People Also Ask", 3, 25, 12)

with col_pasp:
    max_pasf = st.number_input("Max People Also Search For", 3, 20, 10)

advanced_open = st.checkbox(
    "Advanced: open first 5 People Also Ask questions in new tabs",
    value=False,
    help="Only use on small keyword lists!"
)

st.divider()

# ────────────────────────────────────────────────
# File upload & column selection
# ────────────────────────────────────────────────
st.markdown("### Upload keyword list")

uploaded = st.file_uploader(
    "CSV or Excel file",
    type=["csv", "xlsx"],
    help="Should contain at least: Keyword + Country code (PK, US, IN, GB, etc.)"
)

if uploaded is not None:
    try:
        if uploaded.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded)
        else:
            df_input = pd.read_excel(uploaded)

        st.success(f"Loaded {len(df_input)} rows")

        col_kw, col_cc = st.columns(2)
        with col_kw:
            keyword_col = st.selectbox("Keyword column", df_input.columns, index=0)
        with col_cc:
            country_col = st.selectbox("Country code column (gl=)", df_input.columns, index=1)

        st.markdown("**Preview**")
        st.dataframe(df_input.head(7), use_container_width=True)

    except Exception as e:
        st.error(f"Could not read file → {e}")
        st.stop()

# ────────────────────────────────────────────────
# START
# ────────────────────────────────────────────────
if st.button("▶️  Start Extraction", type="primary", use_container_width=True) and uploaded is not None:

    # ── Selenium setup ───────────────────────────────────────
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(50)

    # Live result containers
    results = []
    live_table = st.empty()
    status = st.empty()
    progress = st.progress(0)

    total = len(df_input)

    for idx, row in df_input.iterrows():
        kw   = str(row.get(keyword_col, "")).strip()
        gl   = str(row.get(country_col, "us")).strip().lower()

        if not kw:
            continue

        status.markdown(f"**{idx+1}/{total}**   {kw}   ({gl.upper()})")

        url = f"https://www.google.com/search?q={quote_plus(kw)}&gl={gl}&hl=en&num=20&pws=0"

        try:
            driver.get(url)

            # Wait for main search results area
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#search, #res, body"))
            )

            # Give extra time for dynamic elements
            time.sleep(random.uniform(2.8, 5.5))

            # ───── People Also Ask ────── using your requested selector
            paa_list = []
            try:
                spans = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
                for span in spans:
                    text = span.text.strip()
                    if text and text not in paa_list:
                        paa_list.append(text)
                    if len(paa_list) >= max_paa:
                        break
            except:
                pass

            # ───── People Also Search For ────── using your requested selector
            pasf_list = []
            try:
                links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
                for a in links:
                    text = a.text.strip()
                    if text and text not in pasf_list:
                        pasf_list.append(text)
                    if len(pasf_list) >= max_pasf:
                        break
            except:
                pass

            # Advanced mode: open some questions
            if advanced_open and paa_list:
                for question in paa_list[:5]:
                    q_url = f"https://www.google.com/search?q={quote_plus(question)}&gl={gl}"
                    driver.execute_script(f"window.open('{q_url}', '_blank');")
                    time.sleep(0.7)

            row = {
                "Keyword": kw,
                "Country": gl.upper(),
                "URL": url,
                "People Also Ask": " • ".join(paa_list) if paa_list else "(not found)",
                "People Also Search For": " • ".join(pasf_list) if pasf_list else "(not found)",
                "PAA count": len(paa_list),
                "PASF count": len(pasf_list)
            }

            results.append(row)

        except TimeoutException:
            results.append({
                "Keyword": kw,
                "Country": gl.upper(),
                "URL": url,
                "People Also Ask": "(timeout)",
                "People Also Search For": "(timeout)",
                "PAA count": 0,
                "PASF count": 0
            })
        except Exception as e:
            results.append({
                "Keyword": kw,
                "Country": gl.upper(),
                "URL": url,
                "People Also Ask": f"(error: {str(e)[:70]})",
                "People Also Search For": "(error)",
                "PAA count": 0,
                "PASF count": 0
            })

        # ── Live update ───────────────────────────────────────
        df_live = pd.DataFrame(results)
        live_table.dataframe(
            df_live,
            column_config={
                "URL": st.column_config.LinkColumn("Google"),
                "People Also Ask": st.column_config.TextColumn(width="large"),
                "People Also Search For": st.column_config.TextColumn(width="large"),
            },
            use_container_width=True,
            hide_index=True
        )

        progress.progress((idx + 1) / total)

        time.sleep(delay_seconds + random.uniform(-1.2, 2.8))

    driver.quit()

    status.success("Extraction finished")
    progress.empty()

    # Final download
    st.download_button(
        "⬇️ Download CSV",
        df_live.to_csv(index=False).encode('utf-8'),
        file_name="google_paa_pasf_results.csv",
        mime="text/csv"
    )

else:
    if uploaded is None:
        st.info("Please upload a CSV or Excel file first.")
