# Google SERP Extractor – STRICTLY using ONLY the selectors you requested
# .related-question-pair span → People Also Ask
# a.ggLgoc → People Also Search For
# No other selectors / paths / jsname added

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

# Page setup
st.set_page_config(page_title="Google PAA & PASF Extractor (Strict Selectors)", layout="wide")

st.title("Google People Also Ask + People Also Search For")
st.warning("""
**Important 2026 reality check**  
The selectors `.related-question-pair span` and `a.ggLgoc` are from older Google SERPs (2020–2023).  
Google changed classes multiple times — these are now very rarely present.  
Most results will show "(not found)" — even on queries that have PAA/PASF visible in your browser.  
This is **not a code error**, it's Google's current HTML.
""")

# Controls
st.subheader("Settings")

col1, col2, col3 = st.columns(3)
with col1:
    delay = st.slider("Delay between queries (seconds)", 3.0, 12.0, 6.0)
with col2:
    max_paa = st.number_input("Max PAA items", 3, 20, 10)
with col3:
    max_pasf = st.number_input("Max PASF items", 3, 15, 8)

open_tabs = st.checkbox("Open first 4 PAA questions in new tabs (advanced mode)", False)

st.divider()

# Upload
uploaded = st.file_uploader("Upload CSV/Excel (Keyword + Country code columns)", type=["csv", "xlsx"])

if uploaded:
    try:
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.success(f"Loaded {len(df)} rows")

        c1, c2 = st.columns(2)
        with c1:
            kw_col = st.selectbox("Keyword column", df.columns)
        with c2:
            cc_col = st.selectbox("Country code column (us, pk, in...)", df.columns)

        st.dataframe(df.head(5), use_container_width=True)
    except Exception as e:
        st.error(f"File error: {e}")
        st.stop()

if st.button("Start Extraction", type="primary") and uploaded:

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)

    results = []
    table_placeholder = st.empty()
    status = st.empty()
    prog = st.progress(0)

    total = len(df)

    for i, row in df.iterrows():
        keyword = str(row.get(kw_col, "")).strip()
        country = str(row.get(cc_col, "us")).strip().lower()

        if not keyword:
            continue

        status.text(f"Processing {i+1}/{total}: {keyword} ({country.upper()})")

        url = f"https://www.google.com/search?q={quote_plus(keyword)}&gl={country}&hl=en&num=20&pws=0"

        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(3.0, 6.0))  # Give time for dynamic content

            # STRICT People Also Ask – only your selector
            paa = []
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
                for el in elements:
                    txt = el.text.strip()
                    if txt and txt not in paa:
                        paa.append(txt)
                    if len(paa) >= max_paa:
                        break
            except:
                pass

            # STRICT People Also Search For – only your selector
            pasf = []
            try:
                links = driver.find_elements(By.CSS_SELECTOR, "a.ggLgoc")
                for link in links:
                    txt = link.text.strip()
                    if txt and txt not in pasf:
                        pasf.append(txt)
                    if len(pasf) >= max_pasf:
                        break
            except:
                pass

            # Optional: open tabs
            if open_tabs and paa:
                for q in paa[:4]:
                    qurl = f"https://www.google.com/search?q={quote_plus(q)}&gl={country}"
                    driver.execute_script(f"window.open('{qurl}', '_blank');")
                    time.sleep(0.8)

            results.append({
                "Keyword": keyword,
                "Country": country.upper(),
                "URL": url,
                "People Also Ask": " • ".join(paa) if paa else "(not found with .related-question-pair span)",
                "People Also Search For": " • ".join(pasf) if pasf else "(not found with a.ggLgoc)",
                "PAA count": len(paa),
                "PASF count": len(pasf)
            })

        except TimeoutException:
            results.append({
                "Keyword": keyword,
                "Country": country.upper(),
                "URL": url,
                "People Also Ask": "(timeout)",
                "People Also Search For": "(timeout)",
                "PAA count": 0,
                "PASF count": 0
            })
        except Exception as e:
            results.append({
                "Keyword": keyword,
                "Country": country.upper(),
                "URL": url,
                "People Also Ask": f"(error: {str(e)[:80]})",
                "People Also Search For": "(error)",
                "PAA count": 0,
                "PASF count": 0
            })

        # Live table
        df_results = pd.DataFrame(results)
        table_placeholder.dataframe(
            df_results,
            column_config={
                "URL": st.column_config.LinkColumn("Google Search"),
                "People Also Ask": st.column_config.TextColumn(width="large"),
                "People Also Search For": st.column_config.TextColumn(width="large"),
            },
            use_container_width=True,
            hide_index=True
        )

        prog.progress((i + 1) / total)
        time.sleep(delay + random.uniform(0, 2))

    driver.quit()
    status.success("Done!")
    prog.empty()

    st.download_button(
        "Download CSV",
        df_results.to_csv(index=False).encode('utf-8'),
        "serp_results_strict_selectors.csv",
        "text/csv"
    )

st.divider()
st.caption("Tool fixed to use ONLY your two selectors. If still mostly empty → Google no longer uses those classes in 2026.")
