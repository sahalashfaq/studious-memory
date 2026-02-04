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

st.set_page_config(page_title="Google SERP Extractor", layout="wide")
st.title("🔍 Google SERP Keyword Extractor")
st.caption("PAA: .related-question-pair span | PASF: Updated CSS/XPath for visual & text related searches")

# ────────────────────────────────────────────────
# Settings
# ────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    max_paa = st.number_input("Max PAA items", 3, 25, 12)
with col2:
    max_pasf = st.number_input("Max PASF items", 3, 20, 10)
with col3:
    delay_sec = st.slider("Delay between queries (seconds)", 4.0, 15.0, 6.5)
with col4:
    headless = st.checkbox("Run in headless mode (invisible browser)", value=True)

open_tabs = st.checkbox("Open first 5 PAA questions in new tabs", False)

st.divider()

# ────────────────────────────────────────────────
# Upload
# ────────────────────────────────────────────────
uploaded = st.file_uploader("Upload CSV/Excel (Keyword + Country columns)", type=["csv", "xlsx"])

if uploaded:
    try:
        df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
        st.success(f"Loaded {len(df)} rows")
        c1, c2 = st.columns(2)
        with c1:
            kw_col = st.selectbox("Keyword column", df.columns)
        with c2:
            cc_col = st.selectbox("Country column", df.columns)
        st.dataframe(df.head(6), use_container_width=True)
    except Exception as e:
        st.error(f"File error: {e}")

# ────────────────────────────────────────────────
# Extraction Functions (unchanged)
# ────────────────────────────────────────────────
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


def extract_pasf(driver, limit):
    terms = []
    try:
        # Visual / image-based PASF
        spans = driver.find_elements(By.CSS_SELECTOR, "div.yVCOtc.CvgGZ.AnbG7b.LJEGod.t6uYac span.Yt787.JGD2rd")
        for s in spans:
            text = s.text.strip()
            if text and text not in terms:
                terms.append(text)
            if len(terms) >= limit:
                return terms
    except:
        pass

    # Fallback: classic related searches
    try:
        links = driver.find_elements(By.CSS_SELECTOR, "#bres a, div.brs_col a")
        for link in links:
            try:
                span_text = link.find_element(By.TAG_NAME, "span").text.strip()
                text = span_text if span_text else link.text.strip()
            except:
                text = link.text.strip()
            if text and text not in terms:
                terms.append(text)
            if len(terms) >= limit:
                break
    except:
        pass
    return terms

# ────────────────────────────────────────────────
# Start Extraction
# ────────────────────────────────────────────────
if st.button("🚀 Start Extraction", type="primary") and uploaded is not None:
    # ── Browser setup ───────────────────────────────────────
    options = Options()

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    else:
        # When running headed → make it look more like real user
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(45)
    except Exception as e:
        st.error(f"ChromeDriver failed to start:\n{e}\n\nMake sure chromedriver is installed and in PATH.")
        st.stop()

    results = []
    table = st.empty()
    status = st.empty()
    progress = st.progress(0)

    total = len(df)

    for idx, row in df.iterrows():
        keyword = str(row.get(kw_col, "")).strip()
        cc = str(row.get(cc_col, "pk")).strip().lower()

        if not keyword:
            continue

        status.markdown(f"**{idx+1}/{total}** → **{keyword}**  ({cc.upper()})  {'[headless]' if headless else '[visible browser]'}")
        
        url = f"https://www.google.com/search?q={quote_plus(keyword)}&gl={cc}&hl=en&num=20&pws=0"

        try:
            driver.get(url)
            WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(random.uniform(3.0, 7.0))

            paa = extract_paa(driver, max_paa)
            pasf = extract_pasf(driver, max_pasf)

            if open_tabs and paa and not headless:
                # Only try opening tabs in headed mode (makes more sense)
                for q in paa[:5]:
                    driver.execute_script(f"window.open('https://www.google.com/search?q={quote_plus(q)}&gl={cc}', '_blank');")
                    time.sleep(0.7)

            results.append({
                "Keyword": keyword,
                "Country": cc.upper(),
                "URL": url,
                "People Also Ask": " • ".join(paa) if paa else "(not found)",
                "People Also Search For": " • ".join(pasf) if pasf else "(not found)",
                "PAA count": len(paa),
                "PASF count": len(pasf)
            })

        except Exception as e:
            results.append({
                "Keyword": keyword,
                "Country": cc.upper(),
                "URL": url,
                "People Also Ask": "(error)",
                "People Also Search For": f"(error: {str(e)[:80]})",
                "PAA count": 0,
                "PASF count": 0
            })

        table.dataframe(
            pd.DataFrame(results),
            column_config={
                "URL": st.column_config.LinkColumn("Google"),
                "People Also Ask": st.column_config.TextColumn(width="large"),
                "People Also Search For": st.column_config.TextColumn(width="large"),
            },
            use_container_width=True,
            hide_index=True
        )

        progress.progress((idx + 1) / total)
        time.sleep(delay_sec + random.uniform(0, 2.2))

    driver.quit()
    status.success("Extraction finished!")
    progress.empty()

    st.download_button(
        "⬇️ Download CSV",
        pd.DataFrame(results).to_csv(index=False),
        "serp_results.csv",
        "text/csv"
    )
