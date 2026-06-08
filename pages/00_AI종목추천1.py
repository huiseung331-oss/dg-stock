import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ----------------------------
# 페이지 기본 설정
# ----------------------------
st.set_page_config(
    page_title="AI 관련 주식 대시보드",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI 관련 주식 대시보드")
st.caption("AI 시대를 이끄는 주요 기업들의 주가를 비교 분석합니다 (학습용)")

# ----------------------------
# AI 관련 주요 종목 (이름: 티커)
# ----------------------------
AI_STOCKS = {
    "NVIDIA (엔비디아·AI칩)": "NVDA",
    "Microsoft (MS·오픈AI)": "MSFT",
    "Google (구글·제미나이)": "GOOGL",
    "Amazon (아마존·AWS)": "AMZN",
    "Meta (메타·라마)": "META",
    "AMD (반도체)": "AMD",
    "Palantir (AI분석)": "PLTR",
    "TSMC (반도체파운드리)": "TSM",
    "삼성전자 (HBM메모리)": "005930.KS",
    "SK하이닉스 (HBM메모리)": "000660.KS",
}

# ----------------------------
# 사이드바: 사용자 입력
# ----------------------------
st.sidebar.header("⚙️ 분석 설정")

selected_names = st.sidebar.multiselect(
    "분석할 AI 종목을 선택하세요",
    options=list(AI_STOCKS.keys()),
    default=["NVIDIA (엔비디아·AI칩)", "Microsoft (MS·오픈AI)", "삼성전자 (HBM메모리)"]
)

period_options = {
    "1개월": 30,
    "3개월": 90,
    "6개월": 180,
    "1년": 365,
    "2년": 730,
}
selected_period = st.sidebar.selectbox(
    "분석 기간",
    options=list(period_options.keys()),
    index=3
)

days = period_options[selected_period]
end_date = datetime.now()
start_date = end_date - timedelta(days=days)

# ----------------------------
# 데이터 가져오기 함수 (캐싱)
# ----------------------------
@st.cache_data(ttl=3600)
def get_stock_data(ticker, start, end):
    """yfinance로 주가 데이터를 가져온다."""
    try:
        df = yf.download(ticker, start=start, end=end, progress=False)
        if df.empty:
            return None
        # 멀티인덱스 컬럼 처리
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        st.error(f"{ticker} 데이터 오류: {e}")
        return None

# ----------------------------
# 입력 검증
# ----------------------------
if not selected_names:
    st.warning("👈 사이드바에서 분석할 종목을 1개 이상 선택해주세요!")
    st.stop()

# 데이터 수집
stock_data = {}
with st.spinner("📡 주가 데이터를 불러오는 중..."):
    for name in selected_names:
        ticker = AI_STOCKS[name]
        df = get_stock_data(ticker, start_date, end_date)
        if df is not None and not df.empty:
            stock_data[name] = df

if not stock_data:
    st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

# ----------------------------
# 1) 핵심 지표 카드 (KPI)
# ----------------------------
st.subheader("📌 핵심 지표 요약")

# 종목 수만큼 컬럼 생성 (최대 4개씩)
cols = st.columns(len(stock_data))

for col, (name, df) in zip(cols, stock_data.items()):
    close = df["Close"].dropna()
    if len(close) < 2:
        continue
    current_price = float(close.iloc[-1])
    start_price = float(close.iloc[0])
    pct_change = (current_price / start_price - 1) * 100
    
    with col:
        st.metric(
            label=name.split(" (")[0],  # 괄호 앞 이름만 표시
            value=f"{current_price:,.2f}",
            delta=f"{pct_change:.2f}%"
        )

# ----------------------------
# 2) 누적 수익률 비교
# ----------------------------
st.subheader("📊 누적 수익률 비교")
st.caption("시작 시점을 0%로 맞춰 상대적 수익률을 비교합니다.")

fig_return = go.Figure()

for name, df in stock_data.items():
    close = df["Close"].dropna()
    if len(close) < 2:
        continue
    normalized = (close / close.iloc[0] - 1) * 100
    fig_return.add_trace(go.Scatter(
        x=normalized.index,
        y=normalized.values,
        mode="lines",
        name=name.split(" (")[0]
    ))

fig_return.update_layout(
    xaxis_title="날짜",
    yaxis_title="누적 수익률 (%)",
    hovermode="x unified",
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_return, use_container_width=True)

# ----------------------------
# 3) 변동성(위험도) 분석
# ----------------------------
st.subheader("📉 변동성(위험도) 분석")
st.caption("일일 수익률의 표준편차로 종목별 위험도를 비교합니다. 값이 클수록 변동이 심해요.")

volatility_data = []
for name, df in stock_data.items():
    close = df["Close"].dropna()
    if len(close) < 2:
        continue
    # 일일 수익률 계산
    daily_returns = close.pct_change().dropna()
    # 연율화 변동성(%) = 일일 표준편차 * sqrt(252거래일) * 100
    volatility = daily_returns.std() * np.sqrt(252) * 100
    volatility_data.append({
        "종목": name.split(" (")[0],
        "연율화 변동성(%)": round(float(volatility), 2)
    })

if volatility_data:
    vol_df = pd.DataFrame(volatility_data).sort_values(
        by="연율화 변동성(%)", ascending=False
    )
    fig_vol = px.bar(
        vol_df,
        x="종목",
        y="연율화 변동성(%)",
        color="연율화 변동성(%)",
        color_continuous_scale="Reds",
        text="연율화 변동성(%)"
    )
    fig_vol.update_traces(texttemplate="%{text}%", textposition="outside")
    fig_vol.update_layout(height=400)
    st.plotly_chart(fig_vol, use_container_width=True)

# ----------------------------
# 4) 상관관계 히트맵 (2개 이상일 때만)
# ----------------------------
if len(stock_data) >= 2:
    st.subheader("🔗 종목 간 상관관계")
    st.caption("두 종목의 주가가 얼마나 비슷하게 움직이는지 보여줘요. 1에 가까울수록 같이 움직입니다.")

    # 종가들을 하나의 데이터프레임으로 합치기
    close_dict = {}
    for name, df in stock_data.items():
        close_dict[name.split(" (")[0]] = df["Close"]
    
    combined = pd.DataFrame(close_dict)
    # 일일 수익률 기준 상관관계 (가격보다 정확함)
    returns_corr = combined.pct_change().dropna().corr()

    fig_corr = px.imshow(
        returns_corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1,
        aspect="auto"
    )
    fig_corr.update_layout(height=500)
    st.plotly_chart(fig_corr, use_container_width=True)

# ----------------------------
# 5) 개별 종목 상세 차트
# ----------------------------
st.subheader("🕯️ 개별 종목 상세 차트")

tabs = st.tabs([name.split(" (")[0] for name in stock_data.keys()])

for tab, (name, df) in zip(tabs, stock_data.items()):
    with tab:
        fig = go.Figure()
        # 종가 라인
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            mode="lines", name="종가", line=dict(color="black")
        ))
        # 20일 이동평균선
        ma20 = df["Close"].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=ma20,
            mode="lines", name="20일 이동평균", line=dict(color="orange", dash="dash")
        ))
        fig.update_layout(
            title=f"{name} 주가 추이",
            xaxis_title="날짜", yaxis_title="가격",
            hovermode="x unified", height=450
        )
        st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# 푸터
# ----------------------------
st.divider()
st.caption("⚠️ 본 대시보드는 학습용이며, 투자 권유가 아닙니다. 데이터 출처: Yahoo Finance")
