import os
import yfinance as yf
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = "8980328689"

# (이름, 야후 티커, 보유수량, 통화)
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

message = "=== 상민 투자 브리핑 (적립식) ===\n\n"

for name, ticker_code, qty, currency in holdings:
    try:
        ticker = yf.Ticker(ticker_code)
        hist = ticker.history(period="1y")
        today = hist["Close"].iloc[-1]
        yesterday = hist["Close"].iloc[-2]
        change = ((today - yesterday) / yesterday) * 100
        ma5 = hist["Close"].tail(5).mean()
        high52 = hist["Close"].max()
        from_high = ((today - high52) / high52) * 100
        value = today * qty

        # 적립식용 신호
        if change <= -2:
            signal = "🔥 오늘 세일중! 같은 돈으로 더 많이 사네"
        elif change <= -1:
            signal = "👀 살짝 할인중"
        elif from_high <= -15:
            signal = "💙 고점 대비 많이 빠져서 적립하기 좋은 구간"
        elif today < ma5:
            signal = "📉 5일선 아래 - 조정 중, 적립 유지"
        else:
            signal = "✅ 평온하게 적립 유지"

        if currency == "$":
            message += f"{name}: ${today:.2f} ({change:+.2f}%)\n보유 {qty:.2f}주 / 평가 ${value:,.0f}\n고점 대비 {from_high:.1f}% / {signal}\n\n"
        else:
            message += f"{name}: {today:,.0f}원 ({change:+.2f}%)\n보유 {qty:.0f}주 / 평가 {value:,.0f}원\n고점 대비 {from_high:.1f}% / {signal}\n\n"

    except Exception as e:
        message += f"{name}: 데이터 불러오기 실패\n\n"

message += "💡 적립식 원칙: 타이밍 맞추기보다 매달 꾸준히!\n떨어질 때 더 많이 사는 게 적립식의 힘!"

BOT_TOKEN = BOT_TOKEN.strip() if BOT_TOKEN else ""
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
response = requests.post(url, json={"chat_id": CHAT_ID, "text": message})
print("텔레그램 응답:", response.text)
print("전송완료")
