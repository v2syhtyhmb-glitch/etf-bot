import os
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from urllib.parse import quote
import math
from zoneinfo import ZoneInfo

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = "8980328689"

MONTHLY_TOTAL = 5000000
PENSION_2026 = 864000
IRP_2026 = 600000
PENSION_2027 = 360000
IRP_2027 = 250000

# ==================== ⏰ 실행 시간 판단 (사우디 기준) ====================
now_saudi = datetime.now(ZoneInfo("Asia/Riyadh"))
now_ny = datetime.now(ZoneInfo("America/New_York"))
is_dst = now_ny.dst() != timedelta(0)  # 미국만 서머타임 체크, 사우디는 고정
market_open_saudi_hour = 16 if is_dst else 17  # 서머 16:30, 윈터 17:30

# GitHub cron은 1시간까지 늦을 수 있어서 여유를 2시간으로 둠
if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
    RUN_TYPE = "MORNING"
elif 4 <= now_saudi.hour <= 6:
    RUN_TYPE = "MORNING"
elif market_open_saudi_hour <= now_saudi.hour <= market_open_saudi_hour + 1:
    RUN_TYPE = "MARKET_OPEN"
else:
    print(f"스킵! 사우디 {now_saudi.strftime('%H:%M')} / 뉴욕 DST {is_dst} / 개장 {market_open_saudi_hour}:30")
    exit()

# 미장은 주말에 안 열리니까 주말 개장 브리핑은 스킵
if RUN_TYPE == "MARKET_OPEN" and now_saudi.weekday() >= 5:
    print("주말이라 미장 휴장, 개장 브리핑 스킵")
    exit()

print(f"실행 타입: {RUN_TYPE} / 사우디 {now_saudi} / 개장 {market_open_saudi_hour}:30")

# ==================== ✈️ 휴가 카운트다운 ====================
def get_vacation_msg():
    base = date(2027, 1, 10)
    today_d = now_saudi.date()
    cycle = 84
    temp = base
    while temp < today_d:
        temp += timedelta(days=cycle)
    while temp - timedelta(days=cycle) >= today_d:
        temp -= timedelta(days=cycle)
    next_vac = temp
    prev_vac = next_vac - timedelta(days=cycle)
    dday = (next_vac - today_d).days
    if dday == 0:
        return f"✈️ 오늘이 휴가다! 🎉 즐거운 휴가 보내!\n   📅 다음 휴가: {next_vac + timedelta(days=cycle)}"
    elif dday <= 7:
        return f"✈️ 휴가까지 D-{dday}일! 곧이다! 짐 싸자! 🧳\n   📅 다음 휴가: {next_vac} (일요일)"
    elif dday <= 30:
        return f"✈️ 휴가까지 D-{dday}일! 한 달도 안 남았어!\n   📅 다음 휴가: {next_vac} (일요일)"
    else:
        return f"✈️ 휴가까지 D-{dday}일\n   📅 다음 휴가: {next_vac} (일요일) / 지난 휴가: {prev_vac}"

# ==================== ☀️ 주베일 날씨 ====================
def get_jubail_weather():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=27.0&longitude=49.65&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FRiyadh&forecast_days=1"
        r = requests.get(url, timeout=10).json()
        cur = r["current"]
        daily = r["daily"]
        temp = cur["temperature_2m"]
        hum = cur["relative_humidity_2m"]
        wind = cur["wind_speed_10m"]
        tmax = daily["temperature_2m_max"][0]
        tmin = daily["temperature_2m_min"][0]
        code = cur["weather_code"]
        if code in [0, 1]:
            w_emoji, w_txt = "☀️", "맑음"
        elif code in [2, 3]:
            w_emoji, w_txt = "⛅", "흐림"
        elif code in [45, 48]:
            w_emoji, w_txt = "🌫️", "안개"
        elif code in [51, 53, 55, 61, 63, 65]:
            w_emoji, w_txt = "🌧️", "비"
        else:
            w_emoji, w_txt = "🌤️", "대체로 맑음"
        wind_msg = "💨 오후 바람 강해짐 주의!" if wind >= 20 else f"💨 바람 {wind:.0f} km/h"
        return f"{w_emoji} 주베일 날씨 - {w_txt}\n🌡 현재 {temp:.0f}°C / 최고 {tmax:.0f}°C / 최저 {tmin:.0f}°C\n💧 습도 {hum:.0f}% / {wind_msg}"
    except:
        return "☀️ 주베일 날씨 - 확인 불가"

# ==================== 📚 오늘의 영어 3문장 ====================
ENGLISH_SENTENCES = [
    ("Watching the sunset makes me really happy.", "일몰을 보는 게 날 정말 행복하게 해!"),
    ("Let's grab a coffee after work.", "퇴근하고 커피 한 잔 하자."),
    ("The weather is perfect for a walk.", "산책하기 딱 좋은 날씨야!"),
    ("I need to check the site schedule first.", "현장 일정부터 확인해야 해."),
    ("Can we have a quick meeting at 10?", "10시에 간단히 회의할 수 있을까?"),
    ("Don't forget to wear your helmet.", "헬멧 쓰는 거 잊지 마."),
    ("This project is going really well.", "이 프로젝트 정말 잘 진행되고 있어."),
    ("I'm so tired today, I need an early night.", "오늘 너무 피곤해서 일찍 자야겠어."),
    ("What time is the concrete pouring?", "콘크리트 타설이 몇 시야?"),
    ("Please send me the drawings by email.", "도면 이메일로 보내줘."),
    ("Let's finish this before lunch.", "점심 전에 이거 끝내자."),
    ("The wind is too strong to work at height.", "바람이 너무 세서 고소 작업은 어려워."),
    ("I learned something new today.", "오늘 새로운 걸 배웠어."),
    ("Take care and stay safe on site.", "현장에서는 조심하고 안전하게 지내."),
    ("See you tomorrow at the same time.", "내일 같은 시간에 봐!"),
]

def get_english_3():
    day_of_year = now_saudi.timetuple().tm_yday
    start = (day_of_year * 3) % len(ENGLISH_SENTENCES)
    picked = [ENGLISH_SENTENCES[(start + i) % len(ENGLISH_SENTENCES)] for i in range(3)]
    msg = "📚 오늘의 영어 3문장\n"
    for idx, (en, ko) in enumerate(picked, 1):
        msg += f"{idx}. {en}\n   = {ko}\n"
    return msg

# ==================== 포트폴리오 ====================
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
            news.append(f"▪️ {title}")
        return "\n".join(news) if news else "▪️ 관련 뉴스 없음"
    except:
        return "▪️ 뉴스 불러오기 실패"

def get_yahoo_news(code, max_n=2):
    try:
        t = yf.Ticker(code)
        out = []
        for n in t.news[:max_n]:
            if "title" in n:
                out.append(f"▪️ {n['title']}")
            elif "content" in n:
                out.append(f"▪️ {n['content'].get('title')}")
        return "\n".join(out) if out else "▪️ 관련 뉴스 없음"
    except:
        return "▪️ 뉴스 불러오기 실패"

def get_fear_greed():
    try:
        r = requests.get("https://production.dataviz.cnn.io/business/fear-and-greed-data", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        data = r.json()
        score = int(data["fear_and_greed"]["score"])
        rating = data["fear_and_greed"]["rating"]
        return score, rating
    except:
        try:
            vix = yf.Ticker("^VIX").history(period="2d")["Close"].iloc[-1]
            score = max(0, min(100, int(100 - vix * 2.5)))
            rating = "공포" if score < 25 else "탐욕" if score > 75 else "중립"
            return score, rating + "(추정)"
        except:
            return 50, "확인불가"

def get_dividend_info():
    msg = ""
    for code, name, emoji in [("VOO","VOO","🇺🇸"), ("QQQM","QQQM","💻"), ("SCHD","SCHD","💰")]:
        try:
            t = yf.Ticker(code)
            div = t.dividends
            if len(div) > 0:
                last_date = div.index[-1].strftime("%Y-%m-%d")
                last_amt = div.iloc[-1]
                yld = t.info.get("dividendYield", 0)
                if yld:
                    yld = yld * 100
                msg += f"{emoji} {name} : {last_date} ${last_amt:.2f} / 연 {yld:.2f}%\n"
            else:
                msg += f"{emoji} {name} : 배당 데이터 없음\n"
        except:
            msg += f"{emoji} {name} : 확인 불가\n"
    return msg

def bar(pct):
    pct = max(0, min(100, pct))
    filled = int(pct / 10)
    return "🟩" * filled + "⬜" * (10 - filled) + f" {pct:.0f}%"

today = now_saudi
today_str = today.strftime("%Y-%m-%d")
is_sunday = today.weekday() == 6

vacation_msg = get_vacation_msg()
weather_msg = get_jubail_weather()
english_msg = get_english_3()

try:
    krw_hist = yf.Ticker("KRW=X").history(period="2d")["Close"]
    usdkrw = krw_hist.iloc[-1]
    usdkrw_chg = ((krw_hist.iloc[-1] - krw_hist.iloc[-2]) / krw_hist.iloc[-2]) * 100
    fx_emoji = "📈" if usdkrw_chg > 0 else "📉"
    fx_msg = f"{fx_emoji} 달러/원 : {usdkrw:,.0f}원 ({usdkrw_chg:+.2f}%)"
except:
    usdkrw = 1470
    fx_msg = "💱 달러/원 : 확인 불가"

indices = {"S&P500": ("^GSPC","🇺🇸"), "NASDAQ": ("^IXIC","💻"), "DOW": ("^DJI","🏭"), "VIX": ("^VIX","😨"), "미국채10년": ("^TNX","🏦")}
market_msg = ""
sp_chg = 0
for name, (code, emoji) in indices.items():
    try:
        price, chg, _, _ = get_info(code)
        if name == "S&P500":
            sp_chg = chg
        chg_emoji = "🔴" if chg < 0 else "🟢" if chg > 0 else "⚪"
        market_msg += f"{emoji} {name} : {price:,.2f}  {chg_emoji} {chg:+.2f}%\n"
    except:
        market_msg += f"{emoji} {name} : 데이터 없음\n"

alert_msg = ""
if sp_chg <= -2:
    alert_msg = f"\n🚨🚨 급락 알림! S&P500 {sp_chg:.2f}% 급락 중! 💸 추가 매수 기회?\n"
elif sp_chg <= -1:
    alert_msg = f"\n⚠️ S&P500 {sp_chg:.2f}% 하락 - 적립하기 좋은 날! 🛒\n"
elif sp_chg >= 1:
    alert_msg = f"\n🎉 S&P500 {sp_chg:.2f}% 상승! 기분 좋게 적립 고고! 🚀\n"

fg_score, fg_rating = get_fear_greed()
if fg_score < 25:
    fg_emoji = "😱"
    fg_comment = "극단적 공포! 버핏이 좋아하는 구간 😍"
elif fg_score < 45:
    fg_emoji = "😨"
    fg_comment = "공포 구간 - 분할 매수 찬스!"
elif fg_score < 55:
    fg_emoji = "😐"
    fg_comment = "중립 - 그냥 꾸준히 적립!"
elif fg_score < 75:
    fg_emoji = "🙂"
    fg_comment = "살짝 탐욕 - 욕심 부리지 말기!"
else:
    fg_emoji = "🤑"
    fg_comment = "극단적 탐욕! 조심조심 ⚠️"
fg_msg = f"{fg_emoji} 공포탐욕지수 : {fg_score}점 ({fg_rating})\n   ↳ {fg_comment}"

# ==================== 📊 보유종목 전체 9종 ====================
core_msg = ""
total_krw = 0
total_from_high = 0
cnt = 0
emojis = {
    "AAPL": "🍎", "VOO": "🇺🇸", "QQQM": "💻",
    "TIGER 미국S&P500": "🇰🇷", "KODEX 미국나스닥100": "🇰🇷",
    "SOL 미국배당다우존스": "🇰🇷", "TIGER 미국배당다우존스": "🇰🇷",
    "KODEX 미국우주항공": "🚀", "SOL 조선TOP3플러스": "🚢"
}
for name, code, qty, cur in holdings:
    try:
        price, chg, ma5, from_high = get_info(code)
        total_from_high += from_high
        cnt += 1
        chg_emoji = "🔴" if chg < 0 else "🟢"
        if cur == "$":
            val_usd = price * qty
            val_krw = val_usd * usdkrw
            total_krw += val_krw
            core_msg += f"{emojis.get(name,'📊')} {name} ${price:.1f} {chg_emoji} {chg:+.1f}% | {val_krw/10000:.0f}만원\n"
        else:
            val_krw = price * qty
            total_krw += val_krw
            core_msg += f"{emojis.get(name,'📊')} {name} {price:,.0f}원 {chg_emoji} {chg:+.1f}% | {val_krw/10000:.0f}만원\n"
    except:
        core_msg += f"{emojis.get(name,'📊')} {name} : 데이터 없음\n"

sp_news = get_google_news("S&P500 뉴욕증시", 2)
aapl_news = get_yahoo_news("AAPL", 2)
if aapl_news == "▪️ 관련 뉴스 없음":
    aapl_news = get_google_news("AAPL 애플", 2)
cpi_news = get_google_news("CPI FOMC 연준 금리", 2)
news_msg = f"""📰 오늘의 뉴스
🇺🇸 [S&P500]
{sp_news}

🍎 [AAPL]
{aapl_news}

🏦 [CPI / FOMC]
{cpi_news}"""

avg_from_high = total_from_high / cnt if cnt else 0
try:
    vix_price = yf.Ticker("^VIX").history(period="2d")["Close"].iloc[-1]
except:
    vix_price = 18
if avg_from_high <= -10:
    idea = "💎 매수 - 코어 ETF 적립 비중 확대! 공포에 사는 게 버핏 방식!"
    idea_emoji = "💎"
elif vix_price >= 25:
    idea = "🛒 매수 - 분할 적립! 한 번에 몰빵 금지!"
    idea_emoji = "🛒"
else:
    idea = "⏳ 보유 - 정해진 날짜에 정해진 금액만큼 적립 유지!"
    idea_emoji = "⏳"

score = 100
if avg_from_high < -10:
    score -= 10
if avg_from_high < -20:
    score -= 10
if vix_price >= 25:
    score -= 5
score = max(60, min(95, int(score)))
if score >= 85:
    health_emoji = "💪💪💪"
    health = "매우 건강! 분산 완전 잘 되어 있음!"
elif score >= 75:
    health_emoji = "💪💪"
    health = "건강! 테마주 변동성만 관리하면 됨!"
else:
    health_emoji = "💪"
    health = "조정 필요! 코어 비중 늘릴 때!"

if today.year <= 2026:
    pension, irp = PENSION_2026, IRP_2026
    period_label = "올해말까지"
else:
    pension, irp = PENSION_2027, IRP_2027
    period_label = "내년부터"

remain = MONTHLY_TOTAL - pension - irp
voo_amt = int(remain * 0.5)
qqqm_amt = int(remain * 0.3)
schd_amt = remain - voo_amt - qqqm_amt

div_msg = get_dividend_info()

deep_msg = ""
if is_sunday:
    deep_msg = f"""
━━━━━━━━━━━━━━━━
📚 [주말 딥다이브 - 주간 복기]
🔍 이번 주 S&P500은 고점 대비 {avg_from_high:.1f}% 위치
🧠 공포탐욕 {fg_score}점 : {"지금은 남들이 두려워할 때!" if fg_score < 30 else "평온하게 적립 유지할 때!"}
🌍 달리오 원칙 : 분산이 최고의 방어! 코어 80% + 테마 20% 유지
📖 하워드 막스 원칙 : 사이클은 반복된다. 지금 하락은 다음 상승의 씨앗!
📅 다음 주 체크 : CPI / FOMC 일정 + 배당락일 확인
"""

# ==================== 📩 메시지 분기 ====================
if RUN_TYPE == "MARKET_OPEN":
    # 개장용 짧은 버전 - 프리마켓 마감이 아니라 개장 직후 스냅샷
    message = f"""━━━━━━━━━━━━━━━━
🇺🇸 [미장 개장 브리핑]
📅 {today_str} / 사우디 {now_saudi.strftime('%H:%M')} / 뉴욕 {now_ny.strftime('%H:%M')} ({'서머타임' if is_dst else '윈터타임'})
━━━━━━━━━━━━━━━━
{alert_msg}
📈 시장요약 (전일 종가 기준)
{market_msg}{fx_msg}
{fg_msg}

━━━━━━━━━━━━━━━━
📊 보유종목 (전체 9종)
{core_msg}
💰 전체 평가액 약 {total_krw:,.0f}원

━━━━━━━━━━━━━━━━
💡 오늘의 투자아이디어
{idea_emoji} {idea}
━━━━━━━━━━━━━━━━
"""
else:
    # 아침용 긴 버전 (기존 그대로)
    message = f"""━━━━━━━━━━━━━━━━
☀️ [주베일 아침 브리핑]
📅 {today_str} / {period_label}
━━━━━━━━━━━━━━━━
{vacation_msg}

━━━━━━━━━━━━━━━━
{weather_msg}

━━━━━━━━━━━━━━━━
{english_msg}
━━━━━━━━━━━━━━━━
💼 [포트폴리오 브리핑]
{alert_msg}
📈 시장요약
{market_msg}{fx_msg}
{fg_msg}

━━━━━━━━━━━━━━━━
{news_msg}

━━━━━━━━━━━━━━━━
📊 보유종목 (전체 9종)
{core_msg}
💰 전체 평가액 약 {total_krw:,.0f}원
   (환율 {usdkrw:,.0f}원 적용)

━━━━━━━━━━━━━━━━
💡 오늘의 투자아이디어
{idea_emoji} {idea}

━━━━━━━━━━━━━━━━
💰 이번달 투자전략 (총 5,000,000원)
🏦 연금저축 : {pension:,}원
🏦 IRP : {irp:,}원
✨ 잔여 {remain:,}원
   🇺🇸 VOO {voo_amt:,}원 (50%) {bar(50)}
   💻 QQQM {qqqm_amt:,}원 (30%) {bar(30)}
   💰 SCHD {schd_amt:,}원 (20%) {bar(20)}

━━━━━━━━━━━━━━━━
💵 배당 캘린더
{div_msg}
━━━━━━━━━━━━━━━━
⭐ 포트폴리오 건강도 : {score}점 / 100점
{health_emoji} {health}
{bar(score)}
{deep_msg}
━━━━━━━━━━━━━━━━
"""

print(message)
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
requests.post(url, json={"chat_id": CHAT_ID, "text": message})
print("전송완료")
