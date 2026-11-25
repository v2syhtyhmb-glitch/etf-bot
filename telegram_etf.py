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

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
response = requests.post(url, json={"chat_id": CHAT_ID, "text": message})
print("텔레그램 응답:", response.text)
print("전송완료")
