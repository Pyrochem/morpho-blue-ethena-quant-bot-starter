import os
import requests

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"].strip()
RAPIDAPI_HOST = os.environ["RAPIDAPI_HOST"].strip().replace("https://", "").replace("http://", "").strip("/")
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()

# Paste your RapidAPI Storefront URL here
STOREFRONT_URL = "https://rapidapi.com/TimothyWalters/api/defi-quant-simulators-morpho-blue-ethena"

# Flagship Morpho Blue wstETH/USDC market (Fallback to sUSDe/DAI)
MARKET_ID = "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"

def find_val(data, target_keys, default=0.0):
    """Recursively searches nested JSON dicts for the first matching key."""
    if not isinstance(data, dict):
        return default
    for k in target_keys:
        if k in data and data[k] is not None:
            return data[k]
    for v in data.values():
        if isinstance(v, dict):
            res = find_val(v, target_keys, None)
            if res is not None:
                return res
    return default

def broadcast_alpha():
    headers = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}

    # 1. Fetch Ethena sUSDe Live Epoch Data
    ethena_resp = requests.get(
        f"https://{RAPIDAPI_HOST}/api/v1/ethena/vesting-and-dilution",
        headers=headers, params={"simStakeUsde": 25000000}, timeout=20
    )
    print("Ethena Status:", ethena_resp.status_code)
    ethena = ethena_resp.json()

    # 2. Fetch Morpho Blue Market & Kink Data
    morpho_resp = requests.get(
        f"https://{RAPIDAPI_HOST}/api/v1/morpho/market-and-risk",
        headers=headers, params={"marketId": MARKET_ID, "simBorrowDelta": 2000000}, timeout=20
    )
    print("Morpho Status:", morpho_resp.status_code)
    morpho = morpho_resp.json()
    print("Morpho JSON Keys:", list(morpho.keys()))

    if "error" in morpho or morpho_resp.status_code != 200:
        raise RuntimeError(f"Morpho Endpoint returned error: {morpho}")

    # Extract Ethena metrics
    earn_apy = float(find_val(ethena, ["liveAnnualizedApyPercent", "currentApyPercent", "apy"]))
    drip = float(find_val(ethena, ["linearDripUsdePerSecond", "dripPerSecond"]))
    unvested = float(find_val(ethena, ["unvestedRemainingUsde", "unvestedAmount", "unvestedUsde"]))

    # Extract Morpho metrics (adapts automatically to your exact schema)
    util = float(find_val(morpho, ["utilizationPercent", "utilization", "currentUtilizationPercent"]))
    borrow_apy = float(find_val(morpho, ["currentBorrowApyPercent", "borrowApyPercent", "borrowApy"]))
    sim_apy = float(find_val(morpho, ["simulatedPostTradeBorrowApyPercent", "postTradeBorrowApyPercent", "simulatedBorrowApyPercent"], borrow_apy))
    is_above_kink = bool(find_val(morpho, ["isAbove90PercentKink", "isAboveKink"], util >= 90.0))
    kink_flag = "🚨 ABOVE 90% KINK" if is_above_kink else "✅ Below 90% Kink"

    net_5x_roe = ((5.0 * earn_apy) - (4.0 * borrow_apy))

    msg = (
        f"📡 <b>Live DeFi Quant State (Morpho + Ethena)</b>\n\n"
        f"🟢 <b>Ethena sUSDe (Live 8h Epoch)</b>\n"
        f"• Real-Time Yield: <code>{earn_apy:.2f}% APY</code>\n"
        f"• Unvested Drip: <code>${drip:.2f}/sec</code> (<code>${unvested:,.0f}</code> rem)\n\n"
        f"🏦 <b>Morpho Blue (Flagship Market)</b>\n"
        f"• Utilization: <code>{util:.2f}%</code> ({kink_flag})\n"
        f"• Live Borrow Rate: <code>{borrow_apy:.2f}% APY</code>\n"
        f"• +$2M Whale Slippage: <code>{sim_apy:.2f}% APY</code>\n\n"
        f"💰 <b>5x Loop Net Carry:</b> <code>{net_5x_roe:+.2f}% ROE</code>\n\n"
        f"⚡ <i>Powered by Stateless Multicall3 Quant API</i> — <a href='{STOREFRONT_URL}'>Get API Access on RapidAPI</a>"
    )

    tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    tg_res = requests.post(tg_url, json={
        "chat_id": TG_CHAT,
        "text": msg,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }, timeout=15)

    if not tg_res.ok:
        raise RuntimeError(f"Telegram API Error ({tg_res.status_code}): {tg_res.text}")

    print("Telegram broadcast sent successfully!")

if __name__ == "__main__":
    broadcast_alpha()
