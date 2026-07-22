#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PRStK daily scanner: writes docs/report.json and sends a Telegram Mini App button."""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "docs" / "report.json"
TG_TOKEN = os.getenv("TG_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL", "").rstrip("/")
SUBSCRIBERS = [item.strip() for item in os.getenv("TG_CHAT_IDS", "").split(",") if item.strip()]

TW_POOL = [
    "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2881.TW", "2882.TW",
    "2303.TW", "3231.TW", "2357.TW", "2603.TW", "3711.TW", "2379.TW", "3034.TW",
    "2345.TW", "2301.TW", "2408.TW", "3008.TW", "1519.TW", "2615.TW",
]
MARKET_NAMES = {
    "^TWII": "�啗��䭾�", "^TWOII": "�啗�瑹�眺", "006208.TW": "006208", "00685L.TW": "00685L",
    "2330.TW": "�啁���", "^DJI": "�梶�", "^IXIC": "蝝齿鱻�𥪜�", "^SOX": "鞎餃�",
    "VOO": "VOO", "VT": "VT", "SPYG": "SPYG", "QQQM": "QQQM", "TSM": "TSM",
}


def as_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def breakout_tag(close):
    if len(close) < 21:
        return ""
    now, history = close.iloc[-1], close.iloc[:-1]
    if now > history.iloc[-20:].max():
        return "�� ��20憭拇鰵擃�"
    if now < history.iloc[-20:].min():
        return "�� ��20憭拇鰵雿�"
    if now > history.iloc[-5:].max():
        return "�糃 ��5憭拇鰵擃�"
    if now < history.iloc[-5:].min():
        return "��� ��5憭拇鰵雿�"
    return ""


def tw_stock_universe():
    """Fetch all listed and OTC symbols, with a small fallback for API outages."""
    headers = {"User-Agent": "Mozilla/5.0"}
    result = {}
    sources = [
        ("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", "Code", "Name", ".TW"),
        ("https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes", "SecuritiesCompanyCode", "CompanyName", ".TWO"),
    ]
    for url, code_key, name_key, suffix in sources:
        try:
            for item in requests.get(url, headers=headers, timeout=20).json():
                code = str(item.get(code_key, "")).strip()
                if len(code) == 4 and code.isdigit():
                    result[f"{code}{suffix}"] = str(item.get(name_key, code)).strip()
        except requests.RequestException:
            pass
    if not result:
        result = {symbol: MARKET_NAMES.get(symbol, symbol.split(".")[0]) for symbol in TW_POOL}
    return result


def download_frames(symbols, period="1y", batch_size=80):
    """Yield individual price frames. Batching keeps GitHub Actions memory stable."""
    for start in range(0, len(symbols), batch_size):
        batch = symbols[start:start + batch_size]
        try:
            raw = yf.download(batch, period=period, group_by="ticker", auto_adjust=False,
                              progress=False, threads=True)
            for symbol in batch:
                try:
                    frame = raw[symbol].dropna() if len(batch) > 1 else raw.dropna()
                    if not frame.empty:
                        yield symbol, frame
                except (KeyError, TypeError):
                    continue
        except Exception as exc:
            print(f"download batch failed: {exc}", file=sys.stderr)


def stock_name(symbol, names):
    code = symbol.replace(".TW", "").replace(".TWO", "")
    name = names.get(symbol) or MARKET_NAMES.get(symbol) or code
    return f"{name}({code})" if name != code else code


def scan_momentum(symbols, names):
    records = []
    for symbol, frame in download_frames(symbols, period="100d"):
        if len(frame) < 60:
            continue
        close = frame["Close"].astype(float)
        current = as_float(close.iloc[-1])
        ma5, ma20, ma60 = (as_float(close.rolling(n).mean().iloc[-1]) for n in (5, 20, 60))
        if not ma60 or current < ma5:
            continue
        ret10 = (current / as_float(close.iloc[-11], current) - 1) * 100
        volatility = close.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) * 100
        score = min(99.9, max(0, 50 + (current / ma60 - 1) * 220 + (ma5 / ma60 - 1) * 140 + ret10 * 1.2 - as_float(volatility) * .08))
        records.append({"name": stock_name(symbol, names), "code": symbol.split(".")[0], "price": round(current, 2),
                        "score": round(score, 1), "tag": breakout_tag(close)})
    return sorted(records, key=lambda item: item["score"], reverse=True)[:10]


def atr(frame, window=14):
    high, low, close = frame["High"], frame["Low"], frame["Close"]
    return pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1).rolling(window).mean()


def scan_price_action(symbols, names):
    records = []
    for symbol, frame in download_frames(symbols, period="1y"):
        if len(frame) < 40:
            continue
        f = frame.copy().astype(float)
        current, previous = f.iloc[-1], f.iloc[-2]
        support = f["Low"].iloc[-21:-1].min()
        avg_vol = f["Volume"].iloc[-21:-1].mean()
        is_spring = current["Low"] < support and current["Close"] >= support
        is_reclaim = current["Close"] > previous["High"] and current["Low"] <= previous["High"] * 1.015
        if not (is_spring or is_reclaim):
            continue
        vol_ratio = current["Volume"] / avg_vol if avg_vol else 1
        setup = "�炊 �游�蝧�" if is_spring else "�㴓 鈭埝��噼萱"
        records.append({"name": stock_name(symbol, names), "code": symbol.split(".")[0], "price": round(as_float(current["Close"]), 2),
                        "score": round(min(99.9, 80 + vol_ratio * 4.5), 1), "tag": setup,
                        "turnover": as_float(current["Close"] * current["Volume"])})
    return sorted(records, key=lambda item: item["turnover"], reverse=True)[:10]


def scan_resonance(symbols, names):
    records = []
    for symbol, frame in download_frames(symbols, period="1y"):
        if len(frame) < 150:
            continue
        f = frame.copy().astype(float)
        close, current, previous = f["Close"], f.iloc[-1], f.iloc[-2]
        ma60 = close.rolling(60).mean().iloc[-1]
        vol_ma = f["Volume"].rolling(20).mean().iloc[-1]
        sweep = current["Low"] < previous["Low"] and current["Close"] > previous["Low"]
        reversal = min(current["Open"], current["Close"]) - current["Low"] > abs(current["Close"]-current["Open"])*1.2
        if sweep and (current["Volume"] > vol_ma * 1.2 or reversal) and current["Close"] >= ma60:
            score = min(99.9, 60 + (current["Close"] / ma60 - 1) * 300 + current["Volume"] / vol_ma * 10)
            records.append({"name": stock_name(symbol, names), "code": symbol.split(".")[0], "price": round(as_float(current["Close"]), 2),
                            "score": round(score, 1), "tag": "�𨥈� 瘚���抒枤畾�"})
    return sorted(records, key=lambda item: item["score"], reverse=True)[:10]


def scan_value(symbols, names):
    # Yahoo fundamental endpoints are slow. Keep this focused watchlist instead of adding 2,000 serial calls.
    records = []
    for symbol in TW_POOL:
        try:
            info = yf.Ticker(symbol).get_info()
            roe = as_float(info.get("returnOnEquity")) * 100
            payout = as_float(info.get("payoutRatio")) * 100
            pe = as_float(info.get("trailingPE", info.get("forwardPE")), 0)
            price = as_float(info.get("currentPrice", info.get("regularMarketPrice")))
            if roe > 17 and payout > 20 and price:
                records.append({"name": stock_name(symbol, names), "code": symbol.split(".")[0], "price": round(price, 2),
                                "score": round(min(99.5, roe*.6+payout*.4), 1), "tag": f"PER {pe:.1f}" if pe else "PER ��"})
        except Exception:
            continue
    return sorted(records, key=lambda item: item["score"], reverse=True)[:5]


def market_snapshot(market):
    tickers = ["^TWII", "^TWOII", "006208.TW", "00685L.TW", "2330.TW"] if market == "tw" else ["^DJI", "^IXIC", "^SOX", "VOO", "VT", "SPYG", "QQQM", "TSM"]
    cards = []
    for symbol, frame in download_frames(tickers, period="60d", batch_size=len(tickers)):
        close = frame["Close"].astype(float)
        if len(close) < 2:
            continue
        price, previous = as_float(close.iloc[-1]), as_float(close.iloc[-2])
        change = (price / previous - 1) * 100 if previous else 0
        cards.append({"name": MARKET_NAMES.get(symbol, symbol), "price": round(price, 2), "change": round(change, 2), "tag": breakout_tag(close)})
    return cards


def macro_data(market):
    try:
        vix = as_float(yf.Ticker("^VIX").history(period="5d")["Close"].iloc[-1], 15)
    except Exception:
        vix = 15
    if market != "tw":
        return [{"label": "蝢舘� VIX", "value": f"{vix:.2f}"}]
    try:
        twii = yf.Ticker("^TWII").history(period="180d")["Close"].dropna()
        ma = twii.rolling(125).mean().iloc[-1]
        score = min(100, max(0, 50 + (twii.iloc[-1]/ma-1)*500))
    except Exception:
        score = 50
    state = "璆萄漲�鞉�" if score < 10 else "�鞉�" if score <= 25 else "銝剔� / 璈��" if score <= 50 else "鞎芸帚" if score <= 75 else "璆萄漲鞎芸帚"
    return [{"label": "�啗��鞉剏��痕憍�", "value": f"{score:.1f} 繚 {state}"}, {"label": "VIX", "value": f"{vix:.2f}"}]


def anue_news(keywords):
    try:
        payload = requests.get("https://news.cnyes.com/api/v3/news/category/tw_stock?limit=100", timeout=15).json()
        items = payload.get("items", {}).get("data", [])
        selected = [item for item in items if any(word in item.get("title", "") for word in keywords)][:3]
        return [{"title": item["title"], "url": f"https://news.cnyes.com/news/id/{item['newsId']}"} for item in selected]
    except Exception:
        return []


def build_report(market):
    names = tw_stock_universe() if market == "tw" else {symbol: symbol for symbol in TW_POOL}
    symbols = list(names)
    report = {
        "title": "PRStK | 蝔𣈯��文��蠘汗", "market": "�啗�" if market == "tw" else "蝢舘�",
        "date": datetime.now().astimezone().strftime("%m/%d"),
        "updatedAt": datetime.now().astimezone().strftime("%m/%d %H:%M"),
        "marketCards": market_snapshot(market),
        "strategies": [
            {"id": "momentum", "title": "�㴓 �閗��蹱�", "subtitle": "頞典𨋍��㮾撠滚撥摨西�蝒�聦�閗�", "items": scan_momentum(symbols, names)},
            {"id": "resonance", "title": "�𨥈� 銝厩雁�望𥲤", "subtitle": "瘚���扳��文���撥�Ｗ���", "items": scan_resonance(symbols, names)},
            {"id": "price-action", "title": "�𣺿 Price Action", "subtitle": "�游�蝧餉�鈭埝��噼萱蝯鞉�", "items": scan_price_action(symbols, names)},
            {"id": "value", "title": "��儭� �孵�潭�鞈�", "subtitle": "ROE����舐�����寧祟��", "items": scan_value(symbols, names)},
        ],
        "macro": macro_data(market),
        "news": anue_news(["�啁���", "�𠰴�擃�", "蝘烐�", "憭抒𥿢"]),
        "disclaimer": "�砍�摰寧�蝟餌絞�硋��渲�閮𦠜㟲���銝齿��鞉�鞈�遣霅堆��閗��滩��芾�閰蓥摯憸券麬��",
        "closing": "瘥誩予�賣糓憟賣����憭抬����憟賭��潛��其��𤏸澈銝𠺪�",
    }
    return report


def write_report(report):
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def send_mini_app(report):
    if not (TG_TOKEN and WEB_APP_URL and SUBSCRIBERS):
        print("Telegram skipped: set TG_TOKEN, TG_CHAT_IDS and WEB_APP_URL in GitHub Secrets.")
        return
    url = f"{WEB_APP_URL}/?v={datetime.now().strftime('%Y%m%d%H%M')}"
    text = f"�篅�剏 <b>PRStK嚚𦦵��讐𥿢敺屸�蠘汗</b>嚗ùreport['date']}嚗声n鞈��撌脫凒�堆�暺墧�銝𧢲䲮�厰��亦�摰峕㟲撣�聦��銵冽踎��"
    keyboard = {"inline_keyboard": [[{"text": "�� �见�蝔𣈯��文��蠘汗", "web_app": {"url": url}}]]}
    for chat_id in SUBSCRIBERS:
        try:
            response = requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={
                "chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": keyboard,
                "disable_web_page_preview": True,
            }, timeout=20)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"Telegram send failed for {chat_id}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    market = sys.argv[1].lower() if len(sys.argv) > 1 else "tw"
    if market not in {"tw", "us"}:
        raise SystemExit("Usage: python main.py [tw|us]")
    final_report = build_report(market)
    write_report(final_report)
    send_mini_app(final_report)
    print(f"Done: {REPORT_PATH}")
解釋
