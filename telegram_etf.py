import os
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import quote

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = "8980328689"

MONTHLY_TOTAL = 5000000
PENSION_2026 = 864000
IRP_2026 = 600000
PENSION_2027 = 360000
IRP_2027 = 250000

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

def get_info(code):
    t = yf.Ticker(code)
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
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
            news.append(f"- {title}")
        return "\n".join(news) if news else "관련 뉴스 없음"
    except:
        return "뉴스 불러오기 실패"

def get_yahoo_news(code, max_n=2):
    try:
        t = yf.Ticker(code)
        out = []
        for n in t.news[:max_n]:
            if "title" in n:
                out.append(f"- {n['title']}")
            elif "content" in n:
                out.append(f"- {n['content'].get('title')}")
        return "\n".join(out) if out else "관련 뉴스 없음"
    except:
        return "뉴스 불러오기 실패"

def get_fear_greed():
    # CNN 공포탐욕지수
    try:
        r = requests.get("https://production.dataviz.cnn.io/business/fear-and-greed-data", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        score = int(data["fear_and_greed"]["score"])
        rating = data["fear_and_greed"]["rating"]
        return score, rating
    except:
        # 실패시 VIX로 추정
        try:
            vix = yf.Ticker("^VIX").history(period="2d")["Close"].iloc[-1]
            score = max(0, min(100, int(100 - vix * 2.5)))
            rating = "공포" if score < 25 else "탐욕" if score > 75 else "중립"
            return score, rating + "(추정)"
        except:
            return 50, "확인불가"

def get_dividend_info():
    # 배당 캘린더 - VOO, QQQM, SCHD, SOL배당
    msg = ""
    for code, name in [("VOO","VOO"), ("QQQM","QQQM"), ("SCHD","SCHD")]:
        try:
            t = yf.Ticker(code)
            div = t.dividends
            if len(div) > 0:
                last_date = div.index[-1].strftime("%Y-%m-%d")
                last_amt = div.iloc[-1]
                yld = t.info.get("dividendYield", 0)
                if yld:
                    yld = yld * 100
                msg += f"{name}: 최근 {last_date} ${last_amt:.2f} / 연 배당률 {yld:.2f}%\n"
            else:
                msg += f"{name}: 배당 데이터 없음\n"
        except:
            msg += f"{name}: 확인 불가\n"
    return msg

today = datetime.now()
today_str = today.strftime("%Y-%m-%d")
is_sunday = today.weekday() == 6  # 6 = 일요일

# 환율
try:
    usdkrw = yf.Ticker("KRW=X").history(period="2d")["Close"].iloc[-1]
    usdkrw_chg = ((yf.Ticker("KRW=X").history(period="2d")["Close"].iloc[-1] - yf.Ticker("KRW=X").history(period="2d")["Close"].iloc[-2]) / yf.Ticker("KRW=X").history(period="2d")["Close"].iloc[-2]) * 100
    fx_msg = f"달러/원: {usdkrw:,.0f}원 ({usdkrw_chg:+.2f}%)"
except:
    usdkrw = 1470
    fx_msg = "달러/원: 확인 불가 (1470원 가정)"

# 시장
indices = {"S&P500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX", "미국채10년": "^TNX"}
market_msg = ""
sp_chg = 0
for name, code in indices.items():
    try:
        price, chg, _, _ = get_info(code)
        if name == "S&P500":
            sp_chg = chg
        market_msg += f"{name}: {price:,.2f} ({chg:+.2f}%)\n"
    except:
        market_msg += f"{name}: 데이터 없음\n"

# 급락 알림
alert_msg = ""
if sp_chg <= -2:
    alert_msg = f"\n⚠️⚠️ 급락 알림! S&P500 {sp_chg:.2f}% 급락 중! 오늘 추가 매수 기회? 분할 매수 고려!\n"
elif sp_chg <= -1:
    alert_msg = f"\n⚠️ S&P500 {sp_chg:.2f}% 하락 - 적립하기 좋은 날!\n"

# 공포탐욕
fg_score, fg_rating = get_fear_greed()
fg_msg = f"공포탐욕지수: {fg_score} ({fg_rating})"
if fg_score < 25:
    fg_msg += " - 극단적 공포, 버핏이 좋아하는 구간"
elif fg_score > 75:
    fg_msg += " - 극단적 탐욕, 조심!"

# 보유종목 + 원화 평가
core_msg = ""
total_usd = 0
total_krw = 0
total_from_high = 0
cnt = 0
for name, code, qty, cur in holdings[:3]:
    try:
        price, chg, ma5, from_high = get_info(code)
        total_from_high += from_high
        cnt += 1
        val_usd = price * qty
        total_usd += val_usd
        val_krw = val_usd * usdkrw
        if from_high <= -15:
            risk = "할인 구간"
        elif chg <= -2:
            risk = "단기 조정 / 적립 기회"
        elif price < ma5:
            risk = "조정 중 / 보유"
        else:
            risk = "추세 양호 / 보유"
        core_msg += f"{name}: ${price:.2f} ({chg:+.2f}%) / {val_usd:,.0f}$ ({val_krw:,.0f}원) / {risk}\n"
    except:
        core_msg += f"{name}: 데이터 없음\n"

# 전체 평가액 (9종목)
for name, code, qty, cur in holdings:
    try:
        price, _, _, _ = get_info(code)
        if cur == "$":
            total_krw += price * qty * usdkrw
        else:
            total_krw += price * qty
    except:
        pass

# 뉴스
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

# 경제일정 - 뉴스에서 유추 + 고정 패턴
econ_msg = "CPI / PCE / FOMC / GDP 발표 주간은 위 뉴스 확인. 발표 당일 22:30(한국시간) 변동성 확대 주의."

# 투자 아이디어
avg_from_high = total_from_high / cnt if cnt else 0
try:
    vix_price = yf.Ticker("^VIX").history(period="2d")["Close"].iloc[-1]
except:
    vix_price = 18
if avg_from_high <= -10:
    idea = "매수 - 코어 ETF 적립 비중 확대. 공포에 사는 게 버핏 방식."
elif vix_price >= 25:
    idea = "매수 - 분할 적립. 한 번에 몰빵 금지."
else:
    idea = "보유 - 정해진 날짜에 정해진 금액만큼 적립 유지."

# 건강도
score = 100
if avg_from_high < -10:
    score -= 10
if avg_from_high < -20:
    score -= 10
if vix_price >= 25:
    score -= 5
score = max(60, min(95, int(score)))
health = "매우 건강" if score >= 85 else "건강" if score >= 75 else "조정 필요"

# 목표 달성률
if today.year <= 2026:
    pension, irp = PENSION_2026, IRP_2026
    period_label = "올해말까지 (연금 864,000원 + IRP 600,000원)"
    months_passed = today.month  # 1~12
    pension_target_ytd = pension * months_passed
    irp_target_ytd = irp * months_passed
else:
    pension, irp = PENSION_2027, IRP_2027
    period_label = "내년부터 (연금 360,000원 + IRP 250,000원)"
    months_passed = today.month
    pension_target_ytd = pension * months_passed
    irp_target_ytd = irp * months_passed

remain = MONTHLY_TOTAL - pension - irp
voo_amt = int(remain * 0.5)
qqqm_amt = int(remain * 0.3)
schd_amt = remain - voo_amt - qqqm_amt

div_msg = get_dividend_info()

# 주말 딥다이브 추가
deep_msg = ""
if is_sunday:
    deep_msg = f"""
📚 [주말 딥다이브 - 주간 복기]
- 이번 주 S&P500은 고점 대비 {avg_from_high:.1f}% 위치
- 공포탐욕 {fg_score}점: {"지금은 남들이 두려워할 때" if fg_score < 30 else "평온하게 적립 유지할 때"}
- 달리오 원칙: 분산이 최고의 방어. 코어 80% + 테마 20% 유지
- 하워드 막스 원칙: 사이클은 반복된다. 지금의 하락은 다음 상승의 씨앗
- 다음 주 체크: CPI / FOMC 일정 + 배당락일 확인
"""

message = f"""[포트폴리오 브리핑]
📅 {today_str} / {period_label}
{alert_msg}
📈 시장요약
{market_msg}{fx_msg}
😨 {fg_msg}

{news_msg}

📊 보유종목 (핵심)
{core_msg}전체 평가액 약 {total_krw:,.0f}원 (환율 {usdkrw:,.0f}원 적용)

💡 오늘의 투자아이디어
{idea}

📆 경제일정 (24시간)
{econ_msg}

💰 이번달 투자전략
총 5,000,000원
- 연금저축 {pension:,}원 (올해 누적 목표 {pension_target_ytd:,}원)
- IRP {irp:,}원 (올해 누적 목표 {irp_target_ytd:,}원)
- 잔여 {remain:,}원 -> VOO {voo_amt:,}원(50%) / QQQM {qqqm_amt:,}원(30%) / SCHD {schd_amt:,}원(20%)

💵 배당 캘린더
{div_msg}
⭐ 포트폴리오 건강도: {score}점 / 100점 - {health}
{deep_msg}
"""

print(message)
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
requests.post(url, json={"chat_id": CHAT_ID, "text": message})
print("전송완료")
