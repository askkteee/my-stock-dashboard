import streamlit as st
import pandas as pd
from data_collector import (
    get_naver_theme_top4, get_theme_stocks, get_candlestick_chart, 
    get_realtime_news, get_market_summary, get_watch_list_data, get_macro_indicators, get_stock_name
)

# PC/모바일 반응형 레이아웃 설정
st.set_page_config(page_title="실시간 국내 증시 대시보드", page_icon="📈", layout="wide")

# 📱 [NEW] 모바일 화면 최적화를 위한 CSS 여백 축소 마법
st.markdown("""
<style>
/* 전체 화면 좌우 상하 여백을 모바일에 맞게 확 줄여줍니다 */
.block-container {
    padding-top: 2rem !important;
    padding-bottom: 2rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}
/* 표(데이터프레임) 글자 크기를 모바일에서도 보기 좋게 살짝 조정합니다 */
div[data-testid="stDataFrame"] {
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# 🎨 데이터 색상 지정 함수 (HTS 스타일)
def color_positive_negative(val):
    if isinstance(val, str):
        if val.startswith('+'):
            return 'color: #ff4b4b; font-weight: bold;' # 🔴 빨간색 (상승/순매수)
        elif val.startswith('-'):
            return 'color: #0068c9; font-weight: bold;' # 🔵 파란색 (하락/순매도)
    return ''

st.sidebar.header("⚙️ 대시보드 제어판")
if st.sidebar.button("🔄 실시간 데이터 새로고침"):
    st.cache_data.clear()
    st.toast("최신 데이터로 갱신되었습니다!", icon="🔥")

st.title("🚀 실시간 국내 증시 주도 테마 & 시황 대시보드")
st.markdown("---")

# ------------------------------------------
# 상단: 거시 경제 & 지수 흐름
# ------------------------------------------
st.subheader("📊 오늘의 거시 경제 & 시장 지수")
col1, col2, col3, col4, col5 = st.columns(5)

market_data = get_market_summary()
macro_data = get_macro_indicators()

if market_data:
    with col1: st.metric("📊 KOSPI", market_data["kospi_price"], market_data["kospi_diff"])
    with col2: st.metric("📈 KOSDAQ", market_data["kosdaq_price"], market_data["kosdaq_diff"])
    with col3:
        status = "매도 우위" if "-" in market_data["foreigner"] else "매수 우위"
        st.metric("💰 외국인 (코스피)", status, market_data["foreigner"])

if macro_data:
    with col4: st.metric("💵 원/달러 환율", macro_data["usd"], macro_data["usd_diff"])
    with col5: st.metric("🇺🇸 나스닥 지수", macro_data["nasdaq"], macro_data["nasdaq_diff"])

st.markdown("---")

# ------------------------------------------
# 중단: 테마(좌측) & 캔들 차트(우측)
# ------------------------------------------
col_left, col_right = st.columns([5, 5])

with col_left:
    st.subheader("🔥 당일 강세 테마 TOP 4")
    theme_df = get_naver_theme_top4()
    
    if not theme_df.empty:
        # 📱 [NEW] use_container_width=True 적용
        st.dataframe(theme_df[['순위', '테마명', '평균 등락률(%)']], hide_index=True, use_container_width=True)
        st.markdown("👇 **테마별 주도주(대장주) 분석하기**")
        selected_theme = st.selectbox("스크리너에 연동할 테마를 선택하세요:", theme_df['테마명'])
        
        selected_url = theme_df[theme_df['테마명'] == selected_theme]['theme_url'].values[0]
        theme_leaders_dict = get_theme_stocks(selected_url)
    else:
        st.error("테마 데이터를 불러오지 못했습니다.")
        theme_leaders_dict = {}

with col_right:
    st.subheader("📈 시장 지수 캔들 차트 (최근 3개월)")
    index_sel = st.radio("지수 선택", ["코스피(KOSPI)", "코스닥(KOSDAQ)"], horizontal=True, label_visibility="collapsed")
    sym = 'KS11' if "KOSPI" in index_sel else 'KQ11'
    
    fig = get_candlestick_chart(sym)
    if fig: st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ------------------------------------------
# 하단: 다기능 스크리너 & 뉴스
# ------------------------------------------
st.subheader("📌 종합 분석 스크리너")
tab1, tab2, tab3 = st.tabs(["🚀 테마 대장주 스크리너", "⭐ 나만의 관심 종목 포트폴리오", "📰 시장 특징주 주요 뉴스"])

with tab1:
    st.markdown("**선택하신 테마 대장주의 실시간 기술적 시그널 및 당일 순매수 수량입니다.**")
    
    if theme_leaders_dict:
        screener_df = get_watch_list_data(theme_leaders_dict)
        try:
            styled_df = screener_df.style.map(color_positive_negative, subset=['등락률', '외국인', '기관계'])
        except:
            styled_df = screener_df.style.applymap(color_positive_negative, subset=['등락률', '외국인', '기관계'])
            
        # 📱 [NEW] use_container_width=True 적용
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
    else:
        st.info("분석할 테마 대장주 정보가 없습니다.")

with tab2:
    st.info("평소 관심 있는 종목의 코드를 입력해 보세요!")
    
    if 'my_codes' not in st.session_state:
        st.session_state['my_codes'] = "005930, 000660" 
        
    input_codes = st.text_input("종목코드 입력 (쉼표로 구분, 예: 005930, 000660)", value=st.session_state['my_codes'])
    
    if input_codes:
        st.session_state['my_codes'] = input_codes
        code_list = [c.strip() for c in input_codes.split(',') if len(c.strip()) == 6]
        
        if code_list:
            with st.spinner('종목 데이터를 불러오고 계산 중입니다...'):
                custom_dict = {get_stock_name(c): c for c in code_list}
                custom_df = get_watch_list_data(custom_dict)
                try:
                    styled_custom_df = custom_df.style.map(color_positive_negative, subset=['등락률', '외국인', '기관계'])
                except:
                    styled_custom_df = custom_df.style.applymap(color_positive_negative, subset=['등락률', '외국인', '기관계'])
                    
                # 📱 [NEW] use_container_width=True 적용
                st.dataframe(styled_custom_df, hide_index=True, use_container_width=True)
        else:
            st.warning("올바른 6자리 숫자 종목코드를 입력해 주세요.")

with tab3:
    st.markdown("**네이버 금융 실시간 주요 뉴스 (클릭 시 이동)**")
    try:
        news_df = get_realtime_news()
        # 📱 [NEW] use_container_width=True 적용
        st.dataframe(news_df, hide_index=True, use_container_width=True, column_config={"링크": st.column_config.LinkColumn("기사 읽기")})
    except:
        st.error("뉴스 데이터를 불러오지 못했습니다.")
