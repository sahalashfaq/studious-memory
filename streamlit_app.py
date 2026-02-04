# Google SERP People Also Ask + Related Searches Extractor
# Single page layout • Live table update • Streamlit Cloud compatible
# Updated selectors & waiting strategy — February 2026 edition

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

# ────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Google SERP PAA + Related Extractor",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Google People Also Ask & Related Searches Extractor")
st.caption("Live results • Works best with question-style or commercial keywords • Lahore PK friendly")

# ────────────────────────────────────────────────
# SETTINGS – all in main area
# ────────────────────────────────────────────────
st.markdown("### ⚙️ Extraction Settings")

col1, col2, col3 = st.columns([2, 2, 3])
with col1:
    max_paa = st.slider("Max People Also Ask to collect", 3, 20, 10)
with col2:
    max_related = st.slider("Max Related Searches", 3, 15, 8)
with col3:
    delay_between = st.slider(
        "Delay between requests (seconds)",
        2.5, 10.0, 5.0,
        help="Higher value = much lower chance of CAPTCHA / block"
    )

advanced_open_tabs = st.checkbox(
    "Advanced: Automatically open first 4 People Also Ask questions in new tabs",
    value=False,
    help="Only recommended for very small lists (≤10 keywords)"
)

st.markdown("---")

# ────────────────────────────────────────────────
# FILE UPLOAD
# ────────────────────────────────────────────────
st.markdown("### 📁 Upload your list")
st.markdown("CSV or Excel file with at least two columns: **Keyword** and **Country code** (PK, US, IN, GB, etc.)")

uploaded_file = st.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx"],
    help="Example: Keyword = 'best pizza in lahore', Country = 'PK'"
)

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.success(f"Loaded {len(df)} rows")

        colA, colB = st.columns(2)
        with colA:
            keyword_column = st.selectbox("Keyword column", options=list(df.columns), index=0)
        with colB:
            country_column = st.selectbox("Country code column (gl=)", options=list(df.columns), index=1)

        st.markdown("**Preview (first 6 rows)**")
        st.dataframe(df.head(6), use_container_width=True)

    except Exception as e:
        st.error(f"File reading error: {e}")
        st.stop()

# ────────────────────────────────────────────────
# START BUTTON
# ────────────────────────────────────────────────
if st.button("🚀 Start Extraction", type="primary", use_container_width=True) and uploaded_file is not None:

    # ── Driver setup ───────────────────────────────────────
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)

    # ── Live result table ──────────────────────────────────
    results = []
    result_container = st.empty()
    status_text = st.empty()
    progress_bar = st.progress(0)

    total_rows = len(df)

    for idx, row in df.iterrows():
        keyword = str(row.get(keyword_column, "")).strip()
        cc = str(row.get(country_column, "us")).strip().lower()

        if not keyword:
            continue

        status_text.markdown(f"**Processing {idx+1}/{total_rows}** → **{keyword}**  ({cc.upper()})")

        url = f"https://www.google.com/search?q={quote_plus(keyword)}&gl={cc}&hl=en&num=20&pws=0"

        try:
            driver.get(url)

            # Wait for main content — more generous timeout
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#search, div#res, body"))
            )

            # Extra settle time — modern SERPs are very JS heavy
            time.sleep(random.uniform(2.8, 5.2))

            # ──────── People Also Ask ───────────────────────────────
            paa_items = []

            # 2025–2026 common selector patterns (multiple attempts)
            paa_selectors = [
                "div[jsname='jIA8B'] div[role='button'] span",          # frequent in 2025+
                "div.related-question-pair span",
                "div[jscontroller] div[aria-expanded='false'] span",
                "span[aria-label*='question']",
                ".related-searches a span",
            ]

            for selector in paa_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        text = el.text.strip()
                        if text and text not in paa_items and ('?' in text or len(text.split()) > 3):
                            paa_items.append(text)
                        if len(paa_items) >= max_paa:
                            break
                    if paa_items:
                        break  # stop after first successful selector
                except:
                    continue

            # ──────── Related Searches ──────────────────────────────
            related_items = []

            related_selectors = [
                "div#bres a",                           # broad related searches
                "div.card-section a",
                "div.related-searches a",
                "a[href*='/search?q='] span",
            ]

            for selector in related_selectors:
                try:
                    links = driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in links:
                        txt = link.text.strip()
                        if txt and txt not in related_items and len(txt.split()) >= 2:
                            related_items.append(txt)
                        if len(related_items) >= max_related:
                            break
                    if related_items:
                        break
                except:
                    continue

            # ──────── Advanced mode: open some PAA questions ────────
            if advanced_open_tabs and paa_items:
                for q in paa_items[:4]:
                    q_url = f"https://www.google.com/search?q={quote_plus(q)}&gl={cc}"
                    driver.execute_script(f"window.open('{q_url}', '_blank');")
                    time.sleep(0.6)

            # Save row
            results.append({
                "Keyword": keyword,
                "Country": cc.upper(),
                "URL": url,
                "People Also Ask": " • ".join(paa_items) if paa_items else "(not found)",
                "Related Searches": " • ".join(related_items) if related_items else "(not found)",
                "PAA count": len(paa_items),
                "Related count": len(related_items),
            })

        except TimeoutException:
            results.append({
                "Keyword": keyword,
                "Country": cc.upper(),
                "URL": url,
                "People Also Ask": "(timeout)",
                "Related Searches": "(timeout)",
                "PAA count": 0,
                "Related count": 0,
            })
        except Exception as e:
            results.append({
                "Keyword": keyword,
                "Country": cc.upper(),
                "URL": url,
                "People Also Ask": f"(error: {str(e)[:60]})",
                "Related Searches": "(error)",
                "PAA count": 0,
                "Related count": 0,
            })

        # ── Live update ────────────────────────────────────────
        live_df = pd.DataFrame(results)
        result_container.dataframe(
            live_df,
            column_config={
                "URL": st.column_config.LinkColumn("Google Search"),
                "People Also Ask": st.column_config.TextColumn(width="large"),
                "Related Searches": st.column_config.TextColumn(width="large"),
            },
            use_container_width=True,
            hide_index=True
        )

        progress_bar.progress((idx + 1) / total_rows)

        # Anti-detection delay
        time.sleep(delay_between + random.uniform(-1.0, 2.5))

    driver.quit()

    status_text.success("Extraction finished ✓")
    progress_bar.empty()

    # Final download
    st.download_button(
        label="⬇️ Download full results as CSV",
        data=live_df.to_csv(index=False).encode('utf-8'),
        file_name="google_serp_paa_related.csv",
        mime="text/csv"
    )

else:
    if uploaded_file is None:
        st.info("Please upload your CSV or Excel file to begin.")
