import requests
import pandas as pd
from bs4 import BeautifulSoup
import FinanceDataReader as fdr
import re
import streamlit as st
import plotly.graph_objects as go
import datetime

# 1. 네이버 금융 당일 강세 테마
@st.cache_data(ttl=60)
def get_naver_theme_top4():
    url = "https://finance.naver.com/sise/theme.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    table = soup.find('table', {'class': 'type_1'})
    if table is None: return pd.DataFrame()
        
    rows = table.find_all('tr')
    theme_list = []
    rank = 1
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 3:
            a_tag = cols[0].find('a')
            if a_tag:
                theme_name = a_tag.text.strip()
                theme_url = "https://finance.naver.com" + a_tag['href']
                unrate = cols[1].text.strip()
                try: unrate_num = float(unrate.replace('%', '').replace('+', '').strip())
                except: unrate_num = 0.0
                
                theme_list.append({
                    "순위": rank, "테마명": theme_name, "평균 등락률(%)": unrate_num, "theme_url": theme_url
                })
                rank += 1
                if rank > 4: break
    return pd.DataFrame(theme_list)

# 1-1. 특정 테마의 주도주 긁어오기
@st.cache_data(ttl=60)
def get_theme_stocks(theme_url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(theme_url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    table = soup.find('table', {'class': 'type_5'})
    if not table: return {}
        
    rows = table.find_all('tr')
    stocks_dict = {}
    for row in rows:
        tds = row.find_all('td')
        if len(tds) >= 4:
            name_td = tds[0].find('a')
            if name_td:
                name = name_td.text.strip()
                code = name_td['href'].split('code=')[-1]
                stocks_dict[name] = code
        if len(stocks_dict) >= 3: break
    return stocks_dict

# 2. 전문가용 인터랙티브 캔들 차트
@st.cache_data(ttl=60)
def get_candlestick_chart(symbol='KS11'):
    try:
        df = fdr.DataReader(symbol).tail(60) 
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                    open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'],
                    increasing_line_color='red', decreasing_line_color='blue')])
        fig.update_layout(
            xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=10, b=0),
            height=320, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig
    except: return None

# 3. 실시간 주요 뉴스
@st.cache_data(ttl=60)
def get_realtime_news():
    url = "https://finance.naver.com/news/mainnews.naver"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers)
    res.encoding = 'euc-kr'
    soup = BeautifulSoup(res.text, 'html.parser')
    
    news_list = []
    subjects = soup.find_all('dd', {'class': 'articleSubject'})
    for sub in subjects[:5]:
        a_tag = sub.find('a')
        if a_tag:
            title = a_tag.text.strip()
            link = "https://finance.naver.com" + a_tag['href'] 
            news_list.append({"기사 제목": title, "링크": link})
    return pd.DataFrame(news_list)

# 4. 당일 시장 지수 (네이버 모바일)
@st.cache_data(ttl=60)
def get_market_summary():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        kospi_data = requests.get("https://m.stock.naver.com/api/index/KOSPI/price?pageSize=1&page=1", headers=headers).json()[0]
        kosdaq_data = requests.get("https://m.stock.naver.com/api/index/KOSDAQ/price?pageSize=1&page=1", headers=headers).json()[0]
        
        url_main = "https://finance.naver.com/"
        res_main = requests.get(url_main, headers=headers)
        res_main.encoding = 'euc-kr'
        soup = BeautifulSoup(res_main.text, 'html.parser')
        
        foreigner_text = "0"
        kospi_area = soup.find('div', class_='kospi_area')
        if kospi_area:
            match = re.search(r'외국인\s*([+-]?[\d,]+)', kospi_area.get_text())
            if match: foreigner_text = match.group(1)
                
        return {
            "kospi_price": str(kospi_data['closePrice']),
            "kospi_diff": str(kospi_data['fluctuationsRatio']) + "%",
            "kosdaq_price": str(kosdaq_data['closePrice']),
            "kosdaq_diff": str(kosdaq_data['fluctuationsRatio']) + "%",
            "foreigner": foreigner_text + "억 원"
        }
    except: return None

# 5. 거시 경제 지표 연동
@st.cache_data(ttl=60)
def get_macro_indicators():
    try:
        start_date = (datetime.datetime.now() - datetime.timedelta(days=14)).strftime('%Y-%m-%d')
        
        usd_df = fdr.DataReader('USD/KRW', start=start_date).dropna(subset=['Close'])
        if len(usd_df) >= 2:
            usd_price = float(usd_df['Close'].iloc[-1])
            usd_diff = float(usd_df['Close'].iloc[-1] - usd_df['Close'].iloc[-2])
        else:
            usd_price, usd_diff = 0.0, 0.0

        ndx_df = fdr.DataReader('IXIC', start=start_date).dropna(subset=['Close'])
        if len(ndx_df) >= 2:
            ndx_price = float(ndx_df['Close'].iloc[-1])
            ndx_diff = float((ndx_df['Close'].iloc[-1] - ndx_df['Close'].iloc[-2]) / ndx_df['Close'].iloc[-2] * 100)
        else:
            ndx_price, ndx_diff = 0.0, 0.0

        return {
            "usd": f"{usd_price:,.1f} 원" if usd_price else "조회 불가",
            "usd_diff": f"{usd_diff:+.1f} 원" if usd_price else "",
            "nasdaq": f"{ndx_price:,.2f}" if ndx_price else "조회 불가",
            "nasdaq_diff": f"{ndx_diff:+.2f}%" if ndx_price else ""
        }
    except: return None

# 6. 투자자별 수급 파악 (🚀 외국인/기관 집중)
@st.cache_data(ttl=60)
def get_investor_trend(ticker_code):
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={ticker_code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
        res.encoding = 'euc-kr'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for table in soup.find_all('table', {'class': 'type2'}):
            for tr in table.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) == 9:
                    date_text = tds[0].text.strip()
                    if '.' in date_text and any(c.isdigit() for c in date_text):
                        return {
                            "외국인": f"{tds[6].text.strip()}주", 
                            "기관계": f"{tds[5].text.strip()}주"
                        }
        return {"외국인": "-", "기관계": "-"}
    except: 
        return {"외국인": "오류", "기관계": "오류"}

# 7. 기술적 지표 연산
@st.cache_data(ttl=60)
def calculate_technical_indicators(ticker_code):
    try:
        start_date = (datetime.datetime.now() - datetime.timedelta(days=150)).strftime('%Y-%m-%d')
        df = fdr.DataReader(ticker_code, start=start_date).dropna(subset=['Close']).tail(100)
        if df.empty or len(df) < 2: return None
            
        close = df['Close']
        latest_price = float(close.iloc[-1])
        prev_price = float(close.iloc[-2])
        
        change_rate = ((latest_price - prev_price) / prev_price) * 100
        
        sma20 = close.rolling(window=20).mean()
        
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))
        
        ema1 = close.ewm(span=15, adjust=False).mean()
        ema2 = ema1.ewm(span=15, adjust=False).mean()
        ema3 = ema2.ewm(span=15, adjust=False).mean()
        trix = ema3.pct_change() * 100
        
        signal = []
        signal.append("SMA20 상회" if latest_price > sma20.iloc[-1] else "SMA20 하회")
        if rsi.iloc[-1] < 30: signal.append("RSI 과매도")
        elif rsi.iloc[-1] > 70: signal.append("RSI 과매수")
        if trix.iloc[-1] > trix.iloc[-2] and trix.iloc[-2] < 0: signal.append("Trix 골든크로스")
            
        return {
            "현재가": f"{int(latest_price):,} 원",
            "등락률": f"{change_rate:+.2f}%", 
            "기술적 신호": " / ".join(signal)
        }
    except: return {"현재가": "오류", "등락률": "오류", "기술적 신호": "오류"}

# 8. 종목명 자동 검색
@st.cache_data(ttl=3600)
def get_stock_name(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        name = soup.select_one('.wrap_company h2 a').text
        return name
    except: return f"종목({code})"

# 9. 최종 스크리너 데이터 조립
@st.cache_data(ttl=60)
def get_watch_list_data(dynamic_stocks_dict):
    result = []
    for name, code in dynamic_stocks_dict.items():
        tech_data = calculate_technical_indicators(code)
        inv_data = get_investor_trend(code)
        
        if tech_data:
            result.append({
                "종목명": name,
                "현재가": tech_data["현재가"],
                "등락률": tech_data["등락률"],
                "기술적 신호": tech_data["기술적 신호"],
                "외국인": inv_data["외국인"],
                "기관계": inv_data["기관계"]
            })
            
    df = pd.DataFrame(result)
    if not df.empty:
        df = df[['종목명', '현재가', '등락률', '기술적 신호', '외국인', '기관계']]
    return df