# Google SERP Extractor – STRICTLY using ONLY your selectors
# .related-question-pair span  → People Also Ask (with filtering!)
# a.ggLgoc                     → People Also Search For

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

st.set_page_config(page_title="Google PAA & PASF – Strict Selectors", layout="wide")

st.title("Google People Also Ask & People Also Search For Extractor")
st.info("""
Using **exactly** your selectors:
- PAA: `.related-question-pair span`
- PASF: `a.ggLgoc`

Added smart filtering because .related-question-pair now contains many icon/empty spans (201 in your test!).
Only keeps likely question text (longer strings + ? heuristic).
""")

# ── Settings ─────────────────────────────────────────────
st.subheader("Settings")
col1, col2, col3 = st.columns(3)
with col1:
    delay_sec = st.slider("Delay between queries (s)", 4.0, 12.0, 6.5)
with col2:
    max_paa = st.number_input("Max PAA items", 3, 20, 12)
with col3:
    max_pasf = st.number_input("Max PASF items", 3, 15, 8)

open_tabs = st.checkbox("Open first 5 PAA questions in new tabs", False)

st.divider()

# ── Upload ───────────────────────────────────────────────
uploaded = st.file_uploader("Upload CSV/Excel (Keyword + Country)", type=["csv", "xlsx"])

df_input = None
if uploaded:
    try:
        df_input = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.success(f"Loaded {len(df_input)} rows")

        c1, c2 = st.columns(2)
        with c1: kw_col = st.selectbox("Keyword column", df_input.columns)
        with c2: cc_col = st.selectbox("Country code column", df_input.columns)

        st.dataframe(df_input.head(5))
    except Exception as e:
        st.error(f"File error: {e}")

# ── Start ────────────────────────────────────────────────
if st.button("Start Extraction", type="primary") and df_input is not None:

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(50)

    results = []
    table = st.empty()
    status = st.empty()
    progress = st.progress(0)

    total = len(df_input)

    for idx, row in df_input.iterrows():
        keyword = str(row.get(kw_col, "")).strip()
        cc = str(row.get(cc_col, "pk")).strip().lower()

        if not keyword: continue

        status.markdown(f"**{idx+1}/{total}** → **{keyword}** ({cc.upper()})")

        url = f"https://www.google.com/search?q={quote_plus(keyword)}&gl={cc}&hl=en&num=20&pws=0"

        try:
            driver.get(url)
            WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#search, body")))
            time.sleep(random.uniform(3.5, 6.5))  # JS needs time

            # ── STRICT PAA ───────────────────────────────────
            paa_raw = []
            try:
                spans = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
                for span in spans:
                    txt = span.text.strip()
                    if len(txt) > 12 and txt not in paa_raw:  # filter garbage/icon spans
                        if '?' in txt or len(txt.split()) > 4:  # question heuristic
                            paa_raw.append(txt)
                    if len(paa_raw) >= max_paa:
                        break
            except:
                pass

            # ── STRICT PASF ──────────────────────────────────
            pasf = []
            try:
                links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
                for a in links:
                    txt = a.text.strip()
                    if txt and txt not in pasf:
                        pasf.append(txt)
                    if len(pasf) >= max_pasf:
                        break
            except:
                pass

            # Advanced open tabs
            if open_tabs and paa_raw:
                for q in paa_raw[:5]:
                    q_url = f"https://www.google.com/search?q={quote_plus(q)}&gl={cc}"
                    driver.execute_script(f"window.open('{q_url}', '_blank');")
                    time.sleep(0.7)

            results.append({
                "Keyword": keyword,
                "Country": cc.upper(),
                "URL": url,
                "People Also Ask": " • ".join(paa_raw) if paa_raw else "(filtered – no valid questions found)",
                "People Also Search For": " • ".join(pasf) if pasf else "(not found)",
                "PAA count": len(paa_raw),
                "PASF count": len(pasf)
            })

        except Exception as e:
            results.append({
                "Keyword": keyword,
                "Country": cc.upper(),
                "URL": url,
                "People Also Ask": f"(error: {str(e)[:80]})",
                "People Also Search For": "(error)",
                "PAA count": 0,
                "PASF count": 0
            })

        # Live update
        df_live = pd.DataFrame(results)
        table.dataframe(
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
        time.sleep(delay_sec + random.uniform(0.5, 2.5))

    driver.quit()
    status.success("Finished!")
    progress.empty()

    st.download_button(
        "Download CSV",
        df_live.to_csv(index=False).encode('utf-8'),
        "google_serp_results.csv",
        "text/csv"
    )

st.caption("If still mostly empty: the spans contain icons/text fragments → filtering helps, but Google changed structure. Test with 'best dentist in lahore' or 'how to lose weight fast'.")
