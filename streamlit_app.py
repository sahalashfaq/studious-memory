# Google SERP Keyword Extractor + Trends + Advanced Crawling (2026 Cloud-Ready)

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

from pytrends.request import TrendReq
from pytrends.exceptions import ResponseError

# ────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Google SERP + Trends Insights",
    page_icon="🔍📈",
    layout="wide"
)

# Custom styling
st.markdown("""
    <style>
    .status-ok  { color: #2ecc71; font-weight: bold; }
    .status-warn { color: #e67e22; font-weight: bold; }
    .trend-up   { color: #27ae60; }
    .trend-down { color: #c0392b; }
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
# SELENIUM DRIVER (cached)
# ────────────────────────────────────────────────
@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) Chrome/128 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(35)
    return driver

# ────────────────────────────────────────────────
# GOOGLE URL BUILDER
# ────────────────────────────────────────────────
def build_google_url(keyword, country_code, num=15):
    return f"https://www.google.com/search?q={quote_plus(keyword)}&num={num}&gl={country_code.lower()}&hl=en&pws=0"

# ────────────────────────────────────────────────
# EXTRACT PAA & PASP
# ────────────────────────────────────────────────
def extract_paa(driver, limit=12):
    questions = []
    try:
        els = driver.find_elements(By.CSS_SELECTOR, ".related-question-pair span")
        for el in els:
            txt = el.text.strip()
            if txt and txt not in questions:
                questions.append(txt)
            if len(questions) >= limit:
                break
    except:
        pass
    return questions[:limit]

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
    return terms[:limit]

# ────────────────────────────────────────────────
# SIMPLE GOOGLE TRENDS ANALYSIS (per keyword + country)
# ────────────────────────────────────────────────
def get_trends_summary(keyword, country_code):
    try:
        pytrends = TrendReq(hl='en-US', tz=300, timeout=(10,25), retries=2, backoff_factor=0.1)
        pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo=country_code.upper())
        df = pytrends.interest_over_time()
        
        if df.empty or keyword not in df.columns:
            return "No trend data available (possibly low volume or API issue)."

        latest = df[keyword].iloc[-1]
        avg = df[keyword].mean()
        trend_direction = "↑ rising" if latest > avg * 1.15 else "↓ declining" if latest < avg * 0.85 else "→ stable"
        
        return f"Interest (last 12 months): **{latest}** (avg {int(avg)}) – {trend_direction}"
    
    except ResponseError:
        return "Trends API temporarily unavailable or rate-limited."
    except Exception as e:
        return f"Trends error: {str(e)[:80]} (falling back — data may be incomplete)"

# ────────────────────────────────────────────────
# SIDEBAR CONTROLS
# ────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    max_paa = st.slider("Max People Also Ask", 4, 20, 10)
    max_pasp = st.slider("Max People Also Search", 4, 15, 8)
    delay_sec = st.slider("Delay between requests (s)", 2.0, 7.0, 3.5, help="Higher = lower block risk")
    advanced_crawl = st.checkbox("Do advanced crawling: Open each PAA question in new tab", value=False,
                                 help="When checked, after extraction, browser will try to open PAA questions for deeper exploration")

# ────────────────────────────────────────────────
# MAIN TABS – Now only 2 tabs (combined Results & Tips)
# ────────────────────────────────────────────────
tab_upload, tab_results = st.tabs(["📤 Upload & Extract", "📊 Results & Insights"])

with tab_upload:
    st.subheader("Upload your keywords & country codes")
    st.caption("CSV/Excel file needed – columns: Keyword | Country (e.g. PK, US, IN)")

    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])

    if uploaded:
        try:
            df_input = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded)
            st.success(f"Loaded **{len(df_input)}** keywords")

            col1, col2 = st.columns(2)
            with col1:
                kw_col = st.selectbox("Keyword column", df_input.columns)
            with col2:
                country_col = st.selectbox("Country code column (PK, US...)", df_input.columns)

            st.dataframe(df_input.head(5), use_container_width=True)

            if st.button("🚀 Start Extraction + Trends", type="primary"):
                driver = get_driver()
                results = []
                progress = st.progress(0)
                status = st.empty()

                total = len(df_input)

                for i, row in df_input.iterrows():
                    keyword = str(row[kw_col]).strip()
                    cc = str(row[country_col]).strip().upper()

                    if not keyword or not cc:
                        continue

                    status.markdown(f"<span class='status-ok'>Processing →</span> **{keyword}** ({cc})", unsafe_allow_html=True)

                    url = build_google_url(keyword, cc)

                    try:
                        driver.get(url)
                        WebDriverWait(driver, 18).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        time.sleep(random.uniform(0.9, 2.2))

                        paa = extract_paa(driver, max_paa)
                        pasp = extract_pasp(driver, max_pasp)

                        trends_info = get_trends_summary(keyword, cc)

                        row_data = {
                            "Keyword": keyword,
                            "Country": cc,
                            "Google URL": url,
                            "People Also Ask": " • ".join(paa),
                            "People Also Search": " • ".join(pasp),
                            "PAA Count": len(paa),
                            "PASP Count": len(pasp),
                            "Google Trends (12m)": trends_info
                        }
                        results.append(row_data)

                        # Advanced crawling – open PAA questions
                        if advanced_crawl and paa:
                            for q in paa[:5]:  # limit to first 5 to avoid tab explosion
                                q_url = f"https://www.google.com/search?q={quote_plus(q)}&gl={cc.lower()}"
                                script = f"window.open('{q_url}', '_blank');"
                                driver.execute_script(script)
                                time.sleep(0.6)

                    except Exception as e:
                        results.append({
                            "Keyword": keyword,
                            "Country": cc,
                            "Google URL": url,
                            "People Also Ask": "",
                            "People Also Search": "",
                            "PAA Count": 0,
                            "PASP Count": 0,
                            "Google Trends (12m)": f"Error: {str(e)[:60]}"
                        })

                    progress.progress((i + 1) / total)
                    time.sleep(delay_sec + random.uniform(-0.8, 1.4))

                driver.quit()
                progress.empty()
                status.empty()

                st.session_state["results"] = pd.DataFrame(results)
                st.success("Extraction + Trends analysis completed! → Check Results & Insights tab")
                st.balloons()

        except Exception as e:
            st.error(f"File error: {e}")

with tab_results:
    if "results" in st.session_state and not st.session_state["results"].empty:
        df = st.session_state["results"]

        st.subheader("Extraction Results + Google Trends Insights")

        colA, colB, colC = st.columns(3)
        colA.metric("Processed Keywords", len(df))
        colB.metric("Avg PAA found", f"{df['PAA Count'].mean():.1f}")
        colC.metric("Avg PASP found", f"{df['PASP Count'].mean():.1f}")

        with st.expander("Full Data Table", expanded=True):
            st.dataframe(
                df,
                column_config={
                    "Google URL": st.column_config.LinkColumn("Google Search"),
                    "People Also Ask": st.column_config.TextColumn(width="large"),
                    "People Also Search": st.column_config.TextColumn(width="large"),
                    "Google Trends (12m)": st.column_config.TextColumn(width="medium")
                },
                use_container_width=True,
                hide_index=True
            )

        st.download_button("Download CSV", df.to_csv(index=False), "serp_trends_results.csv", "text/csv")

        st.markdown("---")
        st.subheader("Quick Tips & Best Practices")
        st.markdown("""
        - Use **3–6 sec delay** for >50 keywords to reduce CAPTCHA risk  
        - Enable **advanced crawling** only for small batches (opens many tabs!)  
        - Trends data uses unofficial pytrends → may fail occasionally (Google changes backend)  
        - For production / heavy use consider paid APIs (SerpApi, DataForSEO, Glimpse, etc.)  
        - Combine PAA questions with trends direction to find rising long-tail opportunities  
        - Run from Pakistan (PK)? Trends are very accurate for local language + English mix
        """)

        st.caption("Tool built for educational & research use • Respect Google's ToS • 2026 edition")

    else:
        st.info("Run extraction from the first tab to see results and insights here.")
