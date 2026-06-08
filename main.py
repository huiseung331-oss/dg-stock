import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ----------------------------
# 페이지 기본 설정
# ----------------------------
st.set_page_config(
    page_title="한국·미국 주식 비교 분석",
    page_icon="📈",
    layout="wide"
)

st.title("📈 한국·미국 주요 주식 비교 분석")
st.caption("yfinance와 Plotly로 만든 주식 수익률·차트 비교 앱")

# ----------------------------
# 주요 종목 딕셔너리 (이름: 티커)
# yfinance에서 한국 주식은 .KS(코스피), .KQ(코스닥) 접미사 사용
# ----------------------------
KOREAN_STOCKS = {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "LG에너지솔루션": "373220.KS",
    "현대차": "005380.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "POSCO홀딩스": "005490.KS",
    "셀트리온": "068270.KS",
}

US_STOCKS = {
    "Apple (애플)": "AAPL",
    "Microsoft (마이크로소프트)": "MSFT",
    "Google (구글)": "GOOGL",
    "Amazon (아마존)": "AMZN",
    "NVIDIA (엔비디아)": "NVDA",
    "Tesla (테슬라)": "TSLA",
    "Meta (메타)": "META",
    "Netflix (넷플릭스)": "NFLX",
}

# 전체 종목 합치기
ALL_STOCKS = {**KOREAN_STOCKS, **US_STOCKS}

# ----------------------------
# 사이드바: 사용자 입력
# ----------------------------
st.sidebar.header("⚙️ 분석 설정")

selected_names = st.sidebar.multiselect(
    "비교할 종목을 선택하세요 (여러 개 선택 가능)",
    options=list(ALL_STOCKS.keys()),
    default=["삼성전자", "Apple (애플)", "NVIDIA (엔비디아)"]
)

# 기간 선택
period_options = {
    "1개월": 30,
    "3개월": 90,
    "6개월": 180,
    "1년": 365,
    "2년": 730,
}
selected_period = st.sidebar.selectbox(
    "분석 기간을 선택하세요",
    options=list(period_options.keys()),
    index=3  # 기본값: 1년
)

days = period_options[selected_period]
end_date = datetime.now()
start_date = end_date - timedelta(days=days)

# ----------------------------
# 데이터 가져오기 함수 (캐싱으로 속도 향상)
# ----------------------------
@st.cache_data(ttl=3600)  # 1시간 동안 캐시 유지
def get_stock_data(ticker, start, end):
    """yfinance로 주가 데이터를 가져온다."""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
        if df.empty:
            return None
        # 멀티인덱스 컬럼 처리 (yfinance 최신 버전 대응)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        st.error(f"{ticker} 데이터를 가져오는 중 오류 발생: {e}")
        return None

# ----------------------------
# 메인 로직
# ----------------------------
if not selected_names:
    st.warning("👈 사이드바에서 비교할 종목을 1개 이상 선택해주세요!")
    st.stop()

# 선택한 종목들의 데이터 수집
stock_data = {}
with st.spinner("📡 주가 데이터를 불러오는 중..."):
    for name in selected_names:
        ticker = ALL_STOCKS[name]
        df = get_stock_data(ticker, start_date, end_date)
        if df is not None and not df.empty:
            stock_data[name] = df

if not stock_data:
    st.error("선택한 종목의 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

# ----------------------------
# 1) 수익률 비교 (정규화된 누적 수익률)
# ----------------------------
st.subheader("📊 기간별 누적 수익률 비교")
st.caption("시작 시점을 0%로 맞춰 각 종목의 상대적 수익률을 비교합니다.")

fig_return = go.Figure()

return_summary = []  # 요약 테이블용

for name, df in stock_data.items():
    close = df["Close"].dropna()
    if len(close) < 2:
        continue
    # 누적 수익률(%) = (현재가 / 시작가 - 1) * 100
    normalized = (close / close.iloc[0] - 1) * 100
    fig_return.add_trace(go.Scatter(
        x=normalized.index,
        y=normalized.values,
        mode="lines",
        name=name
    ))
    # 최종 수익률 저장
    final_return = normalized.iloc[-1]
    return_summary.append({
        "종목": name,
        "시작가": round(float(close.iloc[0]), 2),
        "현재가": round(float(close.iloc[-1]), 2),
        f"{selected_period} 수익률(%)": round(float(final_return), 2)
    })

fig_return.update_layout(
    xaxis_title="날짜",
    yaxis_title="누적 수익률 (%)",
    hovermode="x unified",
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_return, use_container_width=True)

# ----------------------------
# 2) 수익률 요약 테이블
# ----------------------------
st.subheader("📋 수익률 요약")
if return_summary:
    summary_df = pd.DataFrame(return_summary)
    # 수익률 기준 정렬
    summary_df = summary_df.sort_values(
        by=f"{selected_period} 수익률(%)", ascending=False
    ).reset_index(drop=True)
    
    # 수익률에 색상 강조 (양수: 빨강/초록 등)
    st.dataframe(
        summary_df.style.format({
            f"{selected_period} 수익률(%)": "{:.2f}",
            "시작가": "{:,.2f}",
            "현재가": "{:,.2f}",
        }),
        use_container_width=True
    )

# ----------------------------
# 3) 개별 종목 캔들스틱 차트
# ----------------------------
st.subheader("🕯️ 개별 종목 캔들스틱 차트")

# 탭으로 종목별 차트 구분
tabs = st.tabs(list(stock_data.keys()))

for tab, (name, df) in zip(tabs, stock_data.items()):
    with tab:
        fig_candle = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            row_heights=[0.7, 0.3],
            subplot_titles=(f"{name} 주가", "거래량")
        )

        # 캔들스틱
        fig_candle.add_trace(
            go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="주가",
                increasing_line_color="red",   # 한국식: 상승=빨강
                decreasing_line_color="blue"   # 한국식: 하락=파랑
            ),
            row=1, col=1
        )

        # 거래량 막대
        fig_candle.add_trace(
            go.Bar(
                x=df.index,
                y=df["Volume"],
                name="거래량",
                marker_color="gray"
            ),
            row=2, col=1
        )

        fig_candle.update_layout(
            height=600,
            xaxis_rangeslider_visible=False,
            showlegend=False,
            hovermode="x unified"
        )
        st.plotly_chart(fig_candle, use_container_width=True)

# ----------------------------
# 푸터
# ----------------------------
st.divider()
st.caption("⚠️ 본 앱은 학습용이며, 투자 권유가 아닙니다. 데이터 출처: Yahoo Finance")
