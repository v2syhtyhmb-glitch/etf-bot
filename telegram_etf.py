import os
import yfinance as yf
import requests

BOT_TOKEN = os.environ.get("9132978624:AAETY7iC9ieC6qD2zGikNvNGIFwdBeygJWI")
CHAT_ID = "8980328689"

etfs = ["VOO", "QQQM", "SCHD"]

message = "=== 상민 투자 브리핑 ===\n\n"

for etf in etfs:
    try:
        ticker = yf.Ticker(etf)
        history = ticker.history(period="5d")
        today = history["Close"].iloc[-1]
        yesterday = history["Close"].iloc[-2]
        change = ((today - yesterday) / yesterday) * 100
        message += f"{etf}: ${today:.2f} ({change:+.2f}%)\n"
    except Exception as e:
        message += f"{etf}: 데이터 불러오기 실패\n"

# 토큰에 혹시 붙은 공백/줄바꿈 제거
BOT_TOKEN = BOT_TOKEN.strip() if BOT_TOKEN else ""
print(f"토큰 길이: {len(BOT_TOKEN) if BOT_TOKEN else '없음'}")
print(f"토큰 앞 5글자: {BOT_TOKEN[:5] if BOT_TOKEN else '없음'}")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
response = requests.post(url, json={"chat_id": CHAT_ID, "text": message})
print("텔레그램 응답:", response.text)
print("전송완료")
