import os
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = "8980328689"

# === 투자 조건 ===
MONTHLY_TOTAL = 5000000
PENSION_2026 = 864000
IRP_2026 = 600000
PENSION_2027 = 360000
IRP_2027 = 250000

# (이름, 티커, 보유수량, 통화)
holdings = [
    ("AAPL", "AAPL", 36, "$"),
    ("VOO", "VOO", 14.765993, "$"),
    ("QQQM", "QQQM", 11.468944, "$"),
    ("TIGER 미국S&P500", "360750.KS", 783, "₩"),
    ("KODEX 미국나스닥100", "133690.KS", 194, "₩"),
    ("SOL 미국배당다우존스", "446720.KS", 51, "₩"),
    ("TIGER 미국배당다우존스", "458730.KS", 169, "₩"),
    ("KODEX 미국우주항공", "0167Z0.KS", 309, "₩"),
    ("SOL 조선TOP3플러스", "466920.KS", 26, "₩"),
]

def get_info(ticker_code):
    t = yf.Ticker(ticker_code)
    h = t.history(period="1y")
    today = h["Close"].iloc[-1]
    yday = h["Close"].iloc[-2]
    chg = ((today - yday) / yday) * 100
    ma5 = h["Close"].tail(5).mean()
    high52 = h["Close"].max()
    from_high = ((today - high52) / high52) * 100
    return today, chg, ma5, from_high

def get_google_news(keyword, max_n=2):
    try:
        url = f"https://news.google.com/rss/search?q={quote(keyword)}&hl=ko&gl=KR&ceid=KR:ko"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(r.content)
        news = []
        for item in root.findall(".//item")[:max_n]:
            title = item.find("title").text
            # 구글 뉴스 제목 뒤에 " - 매체명" 제거
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
            news.append(f"- {title}")
        return "\n".join(news) if news else "관련 뉴스 없음"
    except Exception as e:
        return "뉴스 불러오기 실패"

def get_yahoo_news(ticker_code, max_n=2):
    try:
        t = yf.Ticker(ticker_code)
        news_list = t.news[:max_n]
        out = []
        for n in news_list:
            if "title" in n:
                out.append(f"- {n['title']}")
            elif "content" in n and "title" in n["content"]:
                out.append(f"- {n['content']['title']}")
        return "\n".join(out) if out else "관련 뉴스 없음"
    except:
        return "뉴스 불러오기 실패"

today_str = datetime.now().strftime("%Y-%m-%d")

# 1. 전일 미국시장 분석
indices = {
    "S&P500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
    "VIX": "^VIX",
    "미국채10년": "^TNX",
}
market_msg = ""
for name, code in indices.items():
    try:
        price, chg, _, _ = get_info(code)
        market_msg += f"{name}: {price:,.2f} ({chg:+.2f}%)\n"
    except:
        market_msg += f"{name}: 데이터 없음\n"

try:
    vix_price = yf.Ticker("^VIX").history(period="2d")["Close"].iloc[-1]
    if vix_price >= 25:
        vix_comment = "공포 구간. 남들이 두려워할 때가 기회."
    elif vix_price >= 20:
        vix_comment = "약간 불안. 적립 유지, 공포에 팔지 말기."
    else:
        vix_comment = "평온. 탐욕 경계, 꾸준히 적립."
except:
    vix_price = 18
    vix_comment = "VIX 확인 불가"

# 2. 보유종목 분석 - 핵심 3종
core_msg = ""
total_from_high = 0
cnt = 0
for name, code, qty, cur in holdings[:3]:
    try:
        price, chg, ma5, from_high = get_info(code)
        total_from_high += from_high
        cnt += 1
        if from_high <= -15:
            risk = "위험도 낮음 / 할인 구간"
        elif chg <= -2:
            risk = "단기 조정 / 적립 기회"
        elif price < ma5:
            risk = "조정 중 / 보유"
        else:
            risk = "추세 양호 / 보유"
        core_msg += f"{name}: ${price:.2f} ({chg:+.2f}%) / 고점 대비 {from_high:.1f}% / {risk}\n"
    except:
        core_msg += f"{name}: 데이터 없음\n"

# 3. 뉴스 - RSS (실시간)
sp_news = get_google_news("S&P500 뉴욕증시", 2)
aapl_news = get_yahoo_news("AAPL", 2)
if aapl_news == "관련 뉴스 없음":
    aapl_news = get_google_news("AAPL 애플", 2)
cpi_news = get_google_news("CPI FOMC 연준 금리", 2)

news_msg = f"""📰 오늘의 뉴스
[S&P500]
{sp_news}

[AAPL]
{aapl_news}

[CPI / FOMC]
{cpi_news}"""

# 4. 투자 아이디어
avg_from_high = total_from_high / cnt if cnt else 0
if avg_from_high <= -10:
    idea = "매수 - 코어 ETF 적립 비중 확대. 공포에 사는 게 버핏 방식."
elif vix_price >= 25:
    idea = "매수 - 분할 적립. 한 번에 몰빵 금지."
else:
    idea = "보유 - 정해진 날짜에 정해진 금액만큼 적립 유지. 관망은 적립식의 적."

# 5. 포트폴리오 건강도
score = 100
if avg_from_high < -10:
    score -= 10
if avg_from_high < -20:
    score -= 10
if vix_price >= 25:
    score -= 5
score = max(60, min(95, int(score)))
if score >= 85:
    health = "매우 건강. 분산 잘 되어 있음."
elif score >= 75:
    health = "건강. 테마주 변동성만 관리하면 됨."
else:
    health = "조정 필요. 코어 비중을 늘릴 때."

# 6. 월 적립식 제안
now = datetime.now()
if now.year <= 2026:
    pension, irp = PENSION_2026, IRP_2026
    period_label = "올해말까지 (연금 864,000원 + IRP 600,000원)"
else:
    pension, irp = PENSION_2027, IRP_2027
    period_label = "내년부터 (연금 360,000원 + IRP 250,000원)"

remain = MONTHLY_TOTAL - pension - irp
voo_amt = int(remain * 0.5)
qqqm_amt = int(remain * 0.3)
schd_amt = remain - voo_amt - qqqm_amt

message = f"""[포트폴리오 브리핑]
📅 {today_str} / {period_label}

📈 시장요약
{market_msg}VIX 코멘트: {vix_comment}

{news_msg}

📊 보유종목 (핵심)
{core_msg}전체 보유 9종목 - S&P500/나스닥/배당/우주항공/조선으로 분산 중

💡 오늘의 투자아이디어
{idea}

📆 경제일정 (24시간)
CPI / PCE / FOMC / 실업률 / GDP 중 오늘 발표되는 주요 지표는 위 뉴스에서 확인. 발표 당일은 변동성 확대 가능 - 적립 날짜를 발표 전후로 나누면 좋음.

💰 이번달 투자전략
총 5,000,000원
- 연금저축 {pension:,}원
- IRP {irp:,}원
- 잔여 {remain:,}원 -> VOO {voo_amt:,}원(50%) / QQQM {qqqm_amt:,}원(30%) / SCHD {schd_amt:,}원(20%)

⭐ 포트폴리오 건강도: {score}점 / 100점
{health}
"""

print(message)
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
requests.post(url, json={"chat_id": CHAT_ID, "text": message})
print("전송완료")
