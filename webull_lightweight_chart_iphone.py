# webull_lightweight_chart.py

import json
import requests
import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components

try:
    from pykrx import stock
except Exception:
    stock = None

st.set_page_config(page_title="Webull Style Chart", layout="wide")
st.title("Webull 스타일 주식 차트")

# =========================
# 모바일 최적화
# =========================

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        h1 {
            font-size: 24px !important;
        }

        .block-container {
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
            padding-top: 1rem !important;
        }

        div[data-testid="stMetric"] {
            padding: 4px 0;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# 한국 종목 전체 로딩
# =========================

@st.cache_data(ttl=86400)
def get_korean_stocks():

    items = []

    if stock is None:
        return items

    today = pd.Timestamp.today().strftime("%Y%m%d")

    markets = [
        ("KOSPI", ".KS"),
        ("KOSDAQ", ".KQ"),
    ]

    for market, suffix in markets:

        try:
            tickers = stock.get_market_ticker_list(today, market=market)

            for code in tickers:

                name = stock.get_market_ticker_name(code)

                items.append({
                    "label": f"{name} ({code}) - {market}",
                    "ticker": f"{code}{suffix}",
                    "name": name,
                    "code": code,
                    "market": market
                })

        except Exception:
            pass

    return items

# =========================
# 미국 종목 검색
# =========================

@st.cache_data(ttl=3600)
def search_us_stocks(keyword):

    if not keyword or len(keyword.strip()) < 2:
        return []

    url = "https://query2.finance.yahoo.com/v1/finance/search"

    params = {
        "q": keyword,
        "quotesCount": 10,
        "newsCount": 0
    }

    try:

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()

        results = []

        for item in data.get("quotes", []):

            symbol = item.get("symbol", "")
            name = item.get("shortname") or item.get("longname") or symbol
            quote_type = item.get("quoteType", "")

            if quote_type in ["EQUITY", "ETF", "INDEX"]:

                results.append({
                    "label": f"{name} ({symbol}) - US",
                    "ticker": symbol,
                    "name": name,
                    "code": symbol,
                    "market": "US"
                })

        return results

    except Exception:
        return []

# =========================
# 통합 검색
# =========================

def search_stocks(keyword):

    korean_stocks = get_korean_stocks()

    results = []

    keyword = keyword.strip()
    lower_keyword = keyword.lower()

    # 한국 종목 검색
    for item in korean_stocks:

        if (
            keyword in item["name"]
            or keyword in item["code"]
            or lower_keyword in item["label"].lower()
        ):
            results.append(item)

    # 미국 종목 검색
    results.extend(search_us_stocks(keyword))

    # 중복 제거
    unique = []

    seen = set()

    for item in results:

        if item["ticker"] not in seen:
            unique.append(item)
            seen.add(item["ticker"])

    return unique[:30]

# =========================
# 검색 UI
# =========================

col1, col2, col3 = st.columns(3)

with col1:

    keyword = st.text_input(
        "종목명 또는 종목코드",
        value="삼성전자"
    )

    search_clicked = st.button("검색")

# 최초 상태
if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = "삼성전자"

# 버튼 클릭 시 검색어 저장
if search_clicked:
    st.session_state.last_keyword = keyword

# 검색 실행
search_results = search_stocks(st.session_state.last_keyword)

# 결과 없을 경우
if not search_results:

    st.warning("검색 결과가 없습니다.")

    st.stop()

option_labels = [item["label"] for item in search_results]

option_map = {
    item["label"]: item
    for item in search_results
}

with col1:

    selected_label = st.selectbox(
        "검색 결과",
        option_labels
    )

selected_item = option_map[selected_label]

ticker = selected_item["ticker"]

# =========================
# 기간 / 봉 선택
# =========================

with col2:

    period = st.selectbox(
        "조회 기간",
        ["3mo", "6mo", "1y", "2y", "3y", "5y"],
        index=3
    )

with col3:

    interval_label = st.selectbox(
        "봉 간격",
        ["일봉", "주봉", "월봉"],
        index=0
    )

interval_map = {
    "일봉": "1d",
    "주봉": "1wk",
    "월봉": "1mo"
}

interval = interval_map[interval_label]

st.caption(
    f"선택 종목: {selected_item['label']} / Yahoo 코드: {ticker}"
)

# =========================
# 데이터 다운로드
# =========================

data = yf.download(
    ticker,
    period=period,
    interval=interval,
    auto_adjust=True,
    progress=False
)

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

if data.empty:

    st.error("데이터를 가져오지 못했습니다.")

    st.stop()

# =========================
# 이동평균
# =========================

data["MA5"] = data["Close"].rolling(5).mean()
data["MA20"] = data["Close"].rolling(20).mean()
data["MA60"] = data["Close"].rolling(60).mean()
data["MA120"] = data["Close"].rolling(120).mean()
data["MA240"] = data["Close"].rolling(240).mean()

data = data.reset_index()

date_col = "Date" if "Date" in data.columns else "Datetime"

data["time"] = pd.to_datetime(
    data[date_col]
).dt.strftime("%Y-%m-%d")

# =========================
# 캔들 데이터
# =========================

candles = []

for _, row in data.iterrows():

    candles.append({
        "time": row["time"],
        "open": round(float(row["Open"]), 2),
        "high": round(float(row["High"]), 2),
        "low": round(float(row["Low"]), 2),
        "close": round(float(row["Close"]), 2),
    })

# =========================
# MA 데이터
# =========================

def make_line(series_name):

    result = []

    for _, row in data.dropna(subset=[series_name]).iterrows():

        result.append({
            "time": row["time"],
            "value": round(float(row[series_name]), 2)
        })

    return result

ma5 = make_line("MA5")
ma20 = make_line("MA20")
ma60 = make_line("MA60")
ma120 = make_line("MA120")
ma240 = make_line("MA240")

# =========================
# 차트 HTML
# =========================

html = f"""
<!DOCTYPE html>
<html>

<head>

<script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>

<style>

body {{
    margin:0;
    background:#0b0f14;
}}

#chart {{
    width:100%;
    height:620px;
    touch-action:none;
}}

</style>

</head>

<body>

<div id="chart"></div>

<script>

const candles = {json.dumps(candles)};
const ma5 = {json.dumps(ma5)};
const ma20 = {json.dumps(ma20)};
const ma60 = {json.dumps(ma60)};
const ma120 = {json.dumps(ma120)};
const ma240 = {json.dumps(ma240)};

const chart = LightweightCharts.createChart(
    document.getElementById('chart'),
    {{
        layout: {{
            background: {{ color:'#0b0f14' }},
            textColor:'#d9d9d9',
        }},

        rightPriceScale: {{
            visible:true,
        }},

        leftPriceScale: {{
            visible:false,
        }},

        localization: {{
            priceFormatter: function(price) {{
                return Math.round(price).toLocaleString();
            }}
        }},

        timeScale: {{
            timeVisible:true,
        }},

        handleScale: {{
            mouseWheel:false,
            pinch:true,
            axisPressedMouseMove:{{
                time:true,
                price:true
            }}
        }},

        handleScroll: {{
            mouseWheel:true,
            pressedMouseMove:true,
            horzTouchDrag:true,
            vertTouchDrag:true,
        }},
    }}
);

const candleSeries = chart.addCandlestickSeries({{
    upColor:'#FF3333',
    downColor:'#1E5BFF',
    borderUpColor:'#FF3333',
    borderDownColor:'#1E5BFF',
    wickUpColor:'#FF3333',
    wickDownColor:'#1E5BFF',

    priceFormat:{{
        type:'price',
        precision:0,
        minMove:1
    }}
}});

candleSeries.setData(candles);

function addLine(data, color) {{

    const line = chart.addLineSeries({{
        color:color,
        lineWidth:2,
        priceLineVisible:false,
        lastValueVisible:false,
    }});

    line.setData(data);
}}

addLine(ma5, 'white');
addLine(ma20, 'red');
addLine(ma60, 'limegreen');
addLine(ma120, 'dodgerblue');
addLine(ma240, 'pink');

chart.timeScale().fitContent();

window.addEventListener('resize', () => {{
    chart.applyOptions({{
        width: document.getElementById('chart').clientWidth
    }});
}});

</script>

</body>
</html>
"""

components.html(
    html,
    height=660,
    scrolling=False
)

# =========================
# 현재 상태
# =========================

latest = data.dropna().iloc[-1]

st.subheader("현재 상태")

c1, c2, c3, c4 = st.columns(4)

c1.metric("현재가", f"{latest['Close']:,.0f}")
c2.metric("MA5", f"{latest['MA5']:,.0f}")
c3.metric("MA20", f"{latest['MA20']:,.0f}")
c4.metric("MA60", f"{latest['MA60']:,.0f}")

with st.expander("최근 데이터 보기"):
    st.dataframe(data.tail(30))
