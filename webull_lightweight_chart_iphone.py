# webull_lightweight_chart_iphone.py

import json
import re
from pathlib import Path

import FinanceDataReader as fdr

import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components


st.set_page_config(page_title="Webull Style Chart", layout="wide")
st.title("Webull 스타일 주식 차트")


st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        #chart {
            height: 430px;
            width: calc(100% - 32px);
            margin-right: 32px;
            touch-action: none;
        }
    }

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
    </style>
    """,
    unsafe_allow_html=True
)


CSV_PATH = Path(__file__).resolve().with_name("kr_stock_list.csv")


@st.cache_data(show_spinner=False)
def load_kr_stocks(path, modified_ns):
    # modified_ns invalidates Streamlit's cache when the CSV is replaced.
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    required = {"Code", "Name", "Market", "AsOf"}
    if not required.issubset(frame.columns):
        raise ValueError("CSV에 Code, Name, Market, AsOf 열이 필요합니다.")
    if frame.empty or not frame["Code"].str.fullmatch(r"[0-9A-Z]{6}").all():
        raise ValueError("CSV 종목코드 형식을 확인해주세요.")
    return frame.drop_duplicates("Code").sort_values(["Name", "Code"])


def normalize_name(value):
    return re.sub(r"\s+", "", value).casefold()


INDEX_MAP = {
    "KOSPI200": "^KS200", "코스피200": "^KS200", "^KS200": "^KS200",
    "KOSPI": "^KS11", "코스피": "^KS11",
    "KOSDAQ": "^KQ11", "코스닥": "^KQ11",
    "SPX": "^GSPC", "S&P500": "^GSPC",
    "NASDAQ": "^IXIC", "나스닥": "^IXIC", "DOW": "^DJI", "다우": "^DJI",
    "KODEX200": "069500", "KODEX레버리지": "122630",
}


def resolve_ticker(user_input, stocks, market="자동"):
    query = user_input.strip()
    key = normalize_name(query).upper()
    if not query:
        return "^KS200"
    if key in INDEX_MAP:
        return INDEX_MAP[key]
    # Never append Yahoo's suffix to a Korean code. Normalize pasted legacy codes too.
    code = re.sub(r"\.(KS|KQ)$", "", query.upper())
    if re.fullmatch(r"[0-9]{6}", code) or code in set(stocks["Code"]):
        return code
    if market == "미국":
        return query.upper()
    names = stocks["Name"].map(normalize_name)
    exact = stocks[names == normalize_name(query)]
    matches = exact if not exact.empty else stocks[
        names.str.contains(normalize_name(query), regex=False)
        | stocks["Code"].str.contains(query.upper(), regex=False)
    ]
    # US tickers remain available even if their letters occur in Korean company names.
    if exact.empty and market == "자동" and re.fullmatch(r"[A-Za-z^][A-Za-z0-9.^=/-]*", query):
        return query.upper()
    if not matches.empty:
        labels = {
            row.Code: f"{row.Name} · {row.Code} · {row.Market}"
            for row in matches.itertuples()
        }
        selected = st.selectbox(
            "한국 종목 선택 (목록 안에서 입력하여 자동완성)",
            list(labels), format_func=labels.get,
            index=0 if len(matches) == 1 else None,
            placeholder="검색 결과에서 종목을 선택하세요",
            key=f"kr_match_{query}_{market}",
        )
        if selected is None:
            st.info(f"{len(matches):,}개 검색 결과 중 조회할 종목을 선택해주세요.")
            st.stop()
        return selected
    st.error("일치하는 한국 종목이 없습니다. 검색어 또는 CSV 갱신 여부를 확인해주세요.")
    st.stop()


@st.cache_data(ttl=600, show_spinner=False)
def download_prices(ticker, period, interval):
    if re.fullmatch(r"[0-9A-Z]{6}", ticker) and (
        ticker[0].isdigit() or ticker in set(kr_stocks["Code"])
    ):
        start = pd.Timestamp.now(tz="Asia/Seoul").tz_localize(None).normalize() - pd.DateOffset(
            months={"3mo": 3, "6mo": 6, "1y": 12, "2y": 24, "3y": 36, "5y": 60}[period]
        )
        # NAVER accepts the bare Korean code; do not send it to yfinance.
        prices = fdr.DataReader(f"NAVER:{ticker}", start.strftime("%Y-%m-%d"))
        if not prices.empty and interval != "1d":
            rule = "W-FRI" if interval == "1wk" else "ME"
            prices = prices.resample(rule).agg({
                "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
            }).dropna(subset=["Open", "High", "Low", "Close"])
        prices.index.name = "Date"
        return prices
    return yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)


try:
    kr_stocks = load_kr_stocks(str(CSV_PATH), CSV_PATH.stat().st_mtime_ns)
except (OSError, ValueError, pd.errors.ParserError) as exc:
    st.error(f"종목 목록을 읽을 수 없습니다: {exc}")
    st.info("kr_stock_list.csv를 Python 파일과 같은 폴더에 업로드해주세요.")
    st.stop()

st.caption(f"한국 종목 목록 기준일: {kr_stocks['AsOf'].min()} · {len(kr_stocks):,}종목")
market = st.selectbox("시장", ["자동", "한국", "미국"], help="영문 한국 종목의 부분검색은 한국을 선택하세요. 미국 티커는 미국을 선택하면 바로 조회합니다.")


col1, col2, col3 = st.columns(3)

with col1:
    ticker_input = st.text_input("종목명 또는 종목코드", value="KOSPI200")

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


ticker = resolve_ticker(ticker_input, kr_stocks, market)

st.caption(f"조회 티커: {ticker}")


interval_map = {
    "일봉": "1d",
    "주봉": "1wk",
    "월봉": "1mo"
}

interval = interval_map[interval_label]


try:
    with st.spinner("주가를 불러오는 중입니다..."):
        data = download_prices(ticker, period, interval)
except Exception as exc:
    st.error(f"주가 조회에 실패했습니다 ({ticker}): {exc}")
    st.info("잠시 후 다시 시도해주세요. 종목 목록 검색은 로컬 CSV를 사용하지만 주가는 인터넷 연결이 필요합니다.")
    st.stop()


if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)


if data.empty:
    st.error("데이터를 가져오지 못했습니다. 종목명 또는 종목코드를 확인해주세요.")
    st.stop()


data.index = pd.to_datetime(data.index)


monthly_double_bands = []
merged_double_bands = []


if interval_label == "일봉":
    monthly_groups = data.groupby(data.index.to_period("M"))

    for _, group in monthly_groups:
        if len(group) < 2:
            continue

        month_open = float(group["Open"].iloc[0])
        month_close = float(group["Close"].iloc[-1])
        is_up = month_close >= month_open

        monthly_double_bands.append({
            "start": group.index.min().strftime("%Y-%m-%d"),
            "end": group.index.max().strftime("%Y-%m-%d"),
            "open": round(month_open, 2),
            "close": round(month_close, 2),
            "up": is_up
        })

    current_group = None

    for band in monthly_double_bands:
        if current_group is None:
            current_group = band.copy()
        elif current_group["up"] == band["up"]:
            current_group["end"] = band["end"]
            current_group["close"] = band["close"]
        else:
            merged_double_bands.append(current_group)
            current_group = band.copy()

    if current_group is not None:
        merged_double_bands.append(current_group)


# 날짜 컬럼 안전 처리
data = data.reset_index()

possible_date_cols = ["Date", "Datetime", "index"]

date_col = None

for col in possible_date_cols:
    if col in data.columns:
        date_col = col
        break

if date_col is None:
    st.error("날짜 컬럼을 찾지 못했습니다.")
    st.write("현재 컬럼 목록:", list(data.columns))
    st.stop()

data["time"] = pd.to_datetime(data[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
data = data.dropna(subset=["time"])


data["MA5"] = data["Close"].rolling(5).mean()
data["MA20"] = data["Close"].rolling(20).mean()
data["MA60"] = data["Close"].rolling(60).mean()
data["MA120"] = data["Close"].rolling(120).mean()
data["MA240"] = data["Close"].rolling(240).mean()


candles = []

for _, row in data.iterrows():
    candles.append({
        "time": row["time"],
        "open": round(float(row["Open"]), 2),
        "high": round(float(row["High"]), 2),
        "low": round(float(row["Low"]), 2),
        "close": round(float(row["Close"]), 2),
    })


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


wave_bands = []

if interval_label == "일봉":
    wave_points = []

    for _, row in data.dropna(subset=["MA120", "MA240"]).iterrows():
        if row["MA240"] > row["MA120"]:
            state = "blue"
        elif row["MA240"] < row["MA120"]:
            state = "red"
        else:
            state = "neutral"

        wave_points.append({
            "time": row["time"],
            "ma120": round(float(row["MA120"]), 2),
            "ma240": round(float(row["MA240"]), 2),
            "state": state
        })

    current_band = []

    for point in wave_points:
        if not current_band:
            current_band = [point]
        elif current_band[-1]["state"] == point["state"]:
            current_band.append(point)
        else:
            if len(current_band) >= 2 and current_band[0]["state"] != "neutral":
                wave_bands.append({
                    "state": current_band[0]["state"],
                    "points": current_band
                })
            current_band = [point]

    if len(current_band) >= 2 and current_band[0]["state"] != "neutral":
        wave_bands.append({
            "state": current_band[0]["state"],
            "points": current_band
        })


big_signals = []

if interval_label == "일봉":
    big_data = data.dropna(subset=["MA60", "MA240"]).copy()

    for i in range(1, len(big_data)):
        prev = big_data.iloc[i - 1]
        curr = big_data.iloc[i]

        prev_ma60 = float(prev["MA60"])
        prev_ma240 = float(prev["MA240"])
        curr_ma60 = float(curr["MA60"])
        curr_ma240 = float(curr["MA240"])

        time = curr["time"]
        cross_price = (curr_ma60 + curr_ma240) / 2

        if prev_ma60 < prev_ma240 and curr_ma60 >= curr_ma240:
            big_signals.append({
                "time": time,
                "price": round(cross_price, 2),
                "type": "gold"
            })

        elif prev_ma60 > prev_ma240 and curr_ma60 <= curr_ma240:
            big_signals.append({
                "time": time,
                "price": round(cross_price, 2),
                "type": "dead"
            })


html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>

    <style>
        html, body {{
            margin: 0;
            background: #444444;
            color: #444444;
            font-family: Arial, sans-serif;
        }}

        #chart {{
            width: calc(100% - 18px);
            height: 620px;
            position: relative;
            background: #0b0f14;
            touch-action: none;
            -webkit-user-select: none;
            user-select: none;
        }}

        @media (max-width: 768px) {{
            #chart {{
                height: 520px;
                width: calc(100% - 18px);
                background: #0b0f14;
                touch-action: none;
            }}

            .ma-legend {{
                font-size: 11px;
                padding: 4px 6px;
                top: 8px;
                left: 8px;
            }}

            .ma-legend span {{
                margin-right: 6px;
            }}

            .double-btn {{
                font-size: 11px;
                padding: 1px 6px;
                margin-left: 4px;
            }}

            .tooltip {{
                font-size: 11px;
            }}
        }}

        #wave-bands,
        #double-month-bands,
        #big-markers,
        #month-lines {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
        }}

        #wave-bands {{
            z-index: 5;
        }}

        #double-month-bands {{
            z-index: 6;
        }}

        #big-markers {{
            z-index: 12;
        }}

        #month-lines {{
            z-index: 7;
        }}

        .month-line {{
            position: absolute;
            top: 0;
            bottom: 0;
            width: 1px;
            border-left: 1px dotted rgba(180, 180, 180, 0.35);
        }}

        .double-month-band {{
            position: absolute;
            pointer-events: none;
            border-radius: 2px;
        }}

        .double-month-up {{
            background: rgba(255, 0, 0, 0.28);
            border: 1px solid rgba(255, 0, 0, 0.45);
        }}

        .double-month-down {{
            background: rgba(0, 80, 255, 0.28);
            border: 1px solid rgba(0, 80, 255, 0.45);
        }}

        .ma-legend {{
            position: absolute;
            top: 12px;
            left: 16px;
            z-index: 20;
            font-size: 13px;
            background: rgba(11, 15, 20, 0.72);
            padding: 6px 8px;
            border-radius: 6px;
        }}

        .ma-legend span {{
            margin-right: 12px;
        }}

        .double-btn {{
            margin-left: 8px;
            padding: 2px 8px;
            border: 1px solid rgba(255,255,255,0.35);
            border-radius: 5px;
            background: rgba(255,255,255,0.08);
            color: white;
            cursor: pointer;
            font-size: 12px;
        }}

        .double-btn.mode1 {{
            background: rgba(255,255,255,0.28);
        }}

        .double-btn.mode2 {{
            background: rgba(255, 200, 0, 0.35);
        }}

        .big-marker {{
            position: absolute;
            pointer-events: none;
            text-align: center;
            font-weight: bold;
            white-space: nowrap;
            text-shadow: 0 1px 3px rgba(0,0,0,0.95);
        }}

        .big-marker.gold {{
            color: #ff0000;
            transform: translate(-50%, 5px);
        }}

        .big-marker.dead {{
            color: #0048ff;
            transform: translate(-50%, calc(-100% - 5px));
        }}

        .big-arrow-shape {{
            position: relative;
            width: 14px;
            height: 18px;
            margin: 0 auto;
        }}

        .big-arrow-shape.up::before {{
            content: "";
            position: absolute;
            left: 4px;
            top: 7px;
            width: 6px;
            height: 11px;
            background: #ff0000;
        }}

        .big-arrow-shape.up::after {{
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            width: 0;
            height: 0;
            border-left: 7px solid transparent;
            border-right: 7px solid transparent;
            border-bottom: 8px solid #ff0000;
        }}

        .big-arrow-shape.down::before {{
            content: "";
            position: absolute;
            left: 4px;
            top: 0;
            width: 6px;
            height: 11px;
            background: #0048ff;
        }}

        .big-arrow-shape.down::after {{
            content: "";
            position: absolute;
            left: 0;
            top: 10px;
            width: 0;
            height: 0;
            border-left: 7px solid transparent;
            border-right: 7px solid transparent;
            border-top: 8px solid #0048ff;
        }}

        .big-text {{
            font-size: 11px;
            line-height: 12px;
        }}

        .big-marker.gold .big-text {{
            margin-top: 1px;
        }}

        .big-marker.dead .big-text {{
            margin-bottom: 1px;
        }}

        .tooltip {{
            position: absolute;
            display: none;
            padding: 8px 10px;
            background: rgba(20, 24, 30, 0.92);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px;
            font-size: 12px;
            z-index: 30;
            pointer-events: none;
            line-height: 1.5;
        }}
    </style>
</head>

<body>
    <div id="chart">
        <div id="wave-bands"></div>
        <div id="double-month-bands"></div>
        <div id="big-markers"></div>
        <div id="month-lines"></div>

        <div class="ma-legend">
            <span style="color:white">MA5</span>
            <span style="color:red">MA20</span>
            <span style="color:limegreen">MA60</span>
            <span style="color:dodgerblue">MA120</span>
            <span style="color:#f000ff">MA240</span>
            <button id="double-toggle" class="double-btn" type="button">Double</button>
            <button id="wave-toggle" class="double-btn" type="button">Wave</button>
            <button id="big-toggle" class="double-btn" type="button">Big</button>
        </div>

        <div id="tooltip" class="tooltip"></div>
    </div>

    <script>
        const candles = {json.dumps(candles)};
        const monthlyDoubleBands = {json.dumps(monthly_double_bands)};
        const mergedDoubleBands = {json.dumps(merged_double_bands)};
        const waveBands = {json.dumps(wave_bands)};
        const bigSignals = {json.dumps(big_signals)};

        const ma5 = {json.dumps(ma5)};
        const ma20 = {json.dumps(ma20)};
        const ma60 = {json.dumps(ma60)};
        const ma120 = {json.dumps(ma120)};
        const ma240 = {json.dumps(ma240)};

        const chartElement = document.getElementById('chart');
        const tooltip = document.getElementById('tooltip');
        const monthLinesLayer = document.getElementById('month-lines');
        const doubleMonthLayer = document.getElementById('double-month-bands');
        const waveLayer = document.getElementById('wave-bands');
        const bigLayer = document.getElementById('big-markers');

        const doubleToggle = document.getElementById('double-toggle');
        const waveToggle = document.getElementById('wave-toggle');
        const bigToggle = document.getElementById('big-toggle');

        const chartHeight = window.innerWidth <= 768 ? 520 : 620;

        let doubleMode = 0;
        let waveMode = false;
        let bigMode = false;

        const chart = LightweightCharts.createChart(chartElement, {{
            width: chartElement.clientWidth,
            height: chartHeight,

            layout: {{
                background: {{ color: '#0b0f14' }},
                textColor: '#d9d9d9',
            }},

            grid: {{
                vertLines: {{ color: 'rgba(255,255,255,0.08)' }},
                horzLines: {{ color: 'rgba(255,255,255,0.08)' }},
            }},

            rightPriceScale: {{
                visible: true,
                borderColor: 'rgba(255,255,255,0.2)',
            }},

            leftPriceScale: {{
                visible: false,
            }},

            localization: {{
                priceFormatter: function(price) {{
                    return Math.round(price).toLocaleString();
                }},
            }},

            timeScale: {{
                borderColor: 'rgba(255,255,255,0.2)',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 10,
            }},

            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},

            handleScale: {{
                mouseWheel: false,
                pinch: true,
                axisPressedMouseMove: {{
                    time: true,
                    price: true
                }},
                axisDoubleClickReset: {{
                    time: true,
                    price: true
                }},
            }},

            handleScroll: {{
                mouseWheel: true,
                pressedMouseMove: true,
                horzTouchDrag: true,
                vertTouchDrag: true,
            }},
        }});

        const candleSeries = chart.addCandlestickSeries({{
            upColor: '#FF3333',
            downColor: '#1E5BFF',
            borderUpColor: '#FF3333',
            borderDownColor: '#1E5BFF',
            wickUpColor: '#FF3333',
            wickDownColor: '#1E5BFF',

            priceFormat: {{
                type: 'price',
                precision: 0,
                minMove: 1,
            }},
        }});

        candleSeries.setData(candles);

        function addLine(data, color) {{
            const line = chart.addLineSeries({{
                color: color,
                lineWidth: 2,
                title: '',
                priceLineVisible: false,
                lastValueVisible: false,

                priceFormat: {{
                    type: 'price',
                    precision: 0,
                    minMove: 1,
                }},
            }});

            line.setData(data);
        }}

        addLine(ma5, 'white');
        addLine(ma20, 'red');
        addLine(ma60, 'limegreen');
        addLine(ma120, 'dodgerblue');
        addLine(ma240, '#f000ff');

        const candleMap = new Map();

        candles.forEach(function(item) {{
            candleMap.set(item.time, item);
        }});

        chart.subscribeCrosshairMove(function(param) {{
            if (!param || !param.time || !param.point) {{
                tooltip.style.display = 'none';
                return;
            }}

            const date = param.time;
            const candle = candleMap.get(date);

            if (!candle) {{
                tooltip.style.display = 'none';
                return;
            }}

            tooltip.innerHTML =
                '<b>' + date + '</b><br>' +
                '시가: ' + Math.round(candle.open).toLocaleString() + '<br>' +
                '고가: ' + Math.round(candle.high).toLocaleString() + '<br>' +
                '저가: ' + Math.round(candle.low).toLocaleString() + '<br>' +
                '종가: ' + Math.round(candle.close).toLocaleString();

            tooltip.style.display = 'block';

            let left = param.point.x + 20;
            let top = param.point.y + 20;

            if (left > chartElement.clientWidth - 160) {{
                left = param.point.x - 150;
            }}

            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
        }});

        function drawMonthLines() {{
            monthLinesLayer.innerHTML = '';

            let previousMonth = '';

            candles.forEach(function(item) {{
                const currentMonth = item.time.substring(0, 7);

                if (currentMonth !== previousMonth) {{
                    const x = chart.timeScale().timeToCoordinate(item.time);

                    if (x !== null) {{
                        const barSpacing = chart.timeScale().options().barSpacing || 6;
                        const adjustedX = x - (barSpacing / 2);

                        if (adjustedX >= 0 && adjustedX <= chartElement.clientWidth) {{
                            const line = document.createElement('div');
                            line.className = 'month-line';
                            line.style.left = adjustedX + 'px';
                            monthLinesLayer.appendChild(line);
                        }}
                    }}

                    previousMonth = currentMonth;
                }}
            }});
        }}

        function drawBandBox(band) {{
            const x1 = chart.timeScale().timeToCoordinate(band.start);
            const x2 = chart.timeScale().timeToCoordinate(band.end);

            const yOpen = candleSeries.priceToCoordinate(band.open);
            const yClose = candleSeries.priceToCoordinate(band.close);

            if (x1 === null || x2 === null || yOpen === null || yClose === null) {{
                return;
            }}

            const barSpacing = chart.timeScale().options().barSpacing || 6;
            const left = Math.min(x1, x2) - (barSpacing / 2);
            const width = Math.max(12, Math.abs(x2 - x1) + barSpacing);

            const top = Math.min(yOpen, yClose);
            const height = Math.max(2, Math.abs(yClose - yOpen));

            const box = document.createElement('div');

            if (band.up) {{
                box.className = 'double-month-band double-month-up';
            }} else {{
                box.className = 'double-month-band double-month-down';
            }}

            box.style.left = left + 'px';
            box.style.width = width + 'px';
            box.style.top = top + 'px';
            box.style.height = height + 'px';

            doubleMonthLayer.appendChild(box);
        }}

        function drawMonthlyDoubleBands() {{
            doubleMonthLayer.innerHTML = '';

            if (doubleMode === 0) {{
                return;
            }}

            const bandsToDraw = doubleMode === 1
                ? monthlyDoubleBands
                : mergedDoubleBands;

            bandsToDraw.forEach(function(band) {{
                drawBandBox(band);
            }});
        }}

        function drawWaveBands() {{
            waveLayer.innerHTML = '';

            if (!waveMode) {{
                return;
            }}

            waveBands.forEach(function(band) {{
                const topPoints = [];
                const bottomPoints = [];

                band.points.forEach(function(point) {{
                    const x = chart.timeScale().timeToCoordinate(point.time);

                    const y240 = candleSeries.priceToCoordinate(point.ma240);
                    const y120 = candleSeries.priceToCoordinate(point.ma120);

                    if (x === null || y240 === null || y120 === null) {{
                        return;
                    }}

                    topPoints.push([x, y240]);
                    bottomPoints.push([x, y120]);
                }});

                if (topPoints.length < 2 || bottomPoints.length < 2) {{
                    return;
                }}

                const polygonPoints = topPoints
                    .concat(bottomPoints.reverse())
                    .map(function(p) {{
                        return p[0] + ',' + p[1];
                    }})
                    .join(' ');

                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.style.position = 'absolute';
                svg.style.left = '0';
                svg.style.top = '0';
                svg.style.width = '100%';
                svg.style.height = '100%';
                svg.style.overflow = 'visible';

                const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                polygon.setAttribute('points', polygonPoints);

                if (band.state === 'blue') {{
                    polygon.setAttribute('fill', 'rgba(0, 80, 255, 0.18)');
                }} else {{
                    polygon.setAttribute('fill', 'rgba(255, 0, 0, 0.18)');
                }}

                polygon.setAttribute('stroke', 'none');

                svg.appendChild(polygon);
                waveLayer.appendChild(svg);
            }});
        }}

        function drawBigSignals() {{
            bigLayer.innerHTML = '';

            if (!bigMode) {{
                return;
            }}

            bigSignals.forEach(function(signal) {{
                const x = chart.timeScale().timeToCoordinate(signal.time);
                const y = candleSeries.priceToCoordinate(signal.price);

                if (x === null || y === null) {{
                    return;
                }}

                const marker = document.createElement('div');

                if (signal.type === 'gold') {{
                    marker.className = 'big-marker gold';
                    marker.innerHTML =
                        '<div class="big-arrow-shape up"></div>' +
                        '<div class="big-text">빅골드</div>';
                }} else {{
                    marker.className = 'big-marker dead';
                    marker.innerHTML =
                        '<div class="big-text">빅데드</div>' +
                        '<div class="big-arrow-shape down"></div>';
                }}

                marker.style.left = x + 'px';
                marker.style.top = y + 'px';

                bigLayer.appendChild(marker);
            }});
        }}

        function redrawOverlays() {{
            drawWaveBands();
            drawBigSignals();
            drawMonthLines();
            drawMonthlyDoubleBands();
        }}

        doubleToggle.addEventListener('click', function() {{
            doubleMode = (doubleMode + 1) % 3;

            doubleToggle.classList.remove('mode1');
            doubleToggle.classList.remove('mode2');

            if (doubleMode === 1) {{
                doubleToggle.classList.add('mode1');
                doubleToggle.innerText = 'Double';
            }} else if (doubleMode === 2) {{
                doubleToggle.classList.add('mode2');
                doubleToggle.innerText = 'Double 2';
            }} else {{
                doubleToggle.innerText = 'Double';
            }}

            redrawOverlays();
        }});

        waveToggle.addEventListener('click', function() {{
            waveMode = !waveMode;

            if (waveMode) {{
                waveToggle.classList.add('mode2');
            }} else {{
                waveToggle.classList.remove('mode2');
            }}

            redrawOverlays();
        }});

        bigToggle.addEventListener('click', function() {{
            bigMode = !bigMode;

            if (bigMode) {{
                bigToggle.classList.add('mode2');
            }} else {{
                bigToggle.classList.remove('mode2');
            }}

            redrawOverlays();
        }});

        chart.timeScale().subscribeVisibleTimeRangeChange(function() {{
            redrawOverlays();
        }});

        chart.timeScale().fitContent();

        setTimeout(function() {{
            redrawOverlays();
        }}, 300);

        window.addEventListener('resize', function() {{
            const newHeight = window.innerWidth <= 768 ? 520 : 620;

            chart.applyOptions({{
                width: chartElement.clientWidth,
                height: newHeight
            }});

            redrawOverlays();
        }});
    </script>
</body>
</html>
"""


components.html(html, height=660, scrolling=False)


latest_data = data.dropna(subset=["Close", "MA5", "MA20", "MA60"])

if latest_data.empty:
    st.warning("이동평균선을 계산하기에 데이터가 부족합니다.")
    st.stop()

latest = latest_data.iloc[-1]

st.subheader("현재 상태")

c1, c2, c3, c4 = st.columns(4)

c1.metric("현재가", f"{latest['Close']:,.0f}")
c2.metric("MA5", f"{latest['MA5']:,.0f}")
c3.metric("MA20", f"{latest['MA20']:,.0f}")
c4.metric("MA60", f"{latest['MA60']:,.0f}")


with st.expander("최근 데이터 보기"):
    st.dataframe(data.tail(30))