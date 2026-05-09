# webull_lightweight_chart.py

import json
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

col1, col2, col3 = st.columns(3)

with col1:
    ticker = st.text_input("종목코드", value="005930.KS")

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
    st.error("데이터를 가져오지 못했습니다. 종목코드를 확인해주세요.")
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

data = data.reset_index()
date_col = "Date" if "Date" in data.columns else "Datetime"
data["time"] = pd.to_datetime(data[date_col]).dt.strftime("%Y-%m-%d")

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

html = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>

    <style>
        body {{
            margin: 0;
            background: #0b0f14;
            color: white;
            font-family: Arial, sans-serif;
        }}

        #chart {{
            width: 100%;
            height: 620px;
            position: relative;
        }}

        @media (max-width: 768px) {{
            #chart {{
                height: 520px;
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

        #double-month-bands,
        #month-lines {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
        }}

        #double-month-bands {{
            z-index: 6;
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
        <div id="double-month-bands"></div>
        <div id="month-lines"></div>

        <div class="ma-legend">
            <span style="color:white">MA5</span>
            <span style="color:red">MA20</span>
            <span style="color:limegreen">MA60</span>
            <span style="color:dodgerblue">MA120</span>
            <span style="color:pink">MA240</span>
            <button id="double-toggle" class="double-btn" type="button">Double</button>
        </div>

        <div id="tooltip" class="tooltip"></div>
    </div>

    <script>
        const candles = {json.dumps(candles)};
        const monthlyDoubleBands = {json.dumps(monthly_double_bands)};
        const mergedDoubleBands = {json.dumps(merged_double_bands)};

        const ma5 = {json.dumps(ma5)};
        const ma20 = {json.dumps(ma20)};
        const ma60 = {json.dumps(ma60)};
        const ma120 = {json.dumps(ma120)};
        const ma240 = {json.dumps(ma240)};

        const chartElement = document.getElementById('chart');
        const tooltip = document.getElementById('tooltip');
        const monthLinesLayer = document.getElementById('month-lines');
        const doubleMonthLayer = document.getElementById('double-month-bands');
        const doubleToggle = document.getElementById('double-toggle');

        const chartHeight = window.innerWidth <= 768 ? 520 : 620;

        let doubleMode = 0;

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
            }},

            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},

            handleScale: {{
                mouseWheel: false,
                pinch: true,
                axisPressedMouseMove: true,
                axisDoubleClickReset: true,
            }},

            handleScroll: {{
                mouseWheel: true,
                pressedMouseMove: true,
                horzTouchDrag: true,
                vertTouchDrag: false,
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
        addLine(ma240, 'pink');

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

        function redrawOverlays() {{
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

latest = data.dropna().iloc[-1]

st.subheader("현재 상태")

c1, c2, c3, c4 = st.columns(4)

c1.metric("현재가", f"{latest['Close']:,.0f}")
c2.metric("MA5", f"{latest['MA5']:,.0f}")
c3.metric("MA20", f"{latest['MA20']:,.0f}")
c4.metric("MA60", f"{latest['MA60']:,.0f}")

with st.expander("최근 데이터 보기"):
    st.dataframe(data.tail(30))
