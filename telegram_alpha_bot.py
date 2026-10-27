import os
import requests

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"]
RAPIDAPI_HOST = os.environ["RAPIDAPI_HOST"]
TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"]

# Paste your RapidAPI Storefront URL here so every alert links to your product
STOREFRONT_URL = "https://rapidapi.com/TimothyWalters/api/defi-quant-simulators-morpho-blue-ethena"

MARKET_ID = "0x39d11026eae1c6ec02aa4c0910778664089cdd97c3fd23f68f7cd05e2e95af48" # sUSDe/DAI

def broadcast_alpha():
    headers = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST}

    ethena_resp = requests.get(
        f"https://{RAPIDAPI_HOST}/api/v1/ethena/vesting-and-dilution",
        headers=headers, params={"simStakeUsde": 25000000}, timeout=20
    )
    ethena_resp.raise_for_status()
    ethena = ethena_resp.json()

    morpho_resp = requests.get(
        f"https://{RAPIDAPI_HOST}/api/v1/morpho/market-and-risk",
        headers=headers, params={"marketId": MARKET_ID, "simBorrowDelta": 2000000}, timeout=20
    )
    morpho_resp.raise_for_status()
    morpho = morpho_resp.json()

    earn_apy = ethena["yieldAndDilutionSimulation"]["liveAnnualizedApyPercent"]
    drip = ethena["vestingMechanics"]["linearDripUsdePerSecond"]
    unvested = ethena["vestingMechanics"]["unvestedRemainingUsde"]

    util = morpho["marketState"]["utilizationPercent"]
    borrow_apy = morpho["ratesAndKinkSimulation"]["currentBorrowApyPercent"]
    sim_apy = morpho["ratesAndKinkSimulation"]["simulatedPostTradeBorrowApyPercent"]
    kink_flag = "🚨 ABOVE 90% KINK" if morpho["ratesAndKinkSimulation"]["isAbove90PercentKink"] else "✅ Below 90% Kink"

    net_5x_roe = ((5 * earn_apy) - (4 * borrow_apy))

    msg = (
        f"📡 *Live DeFi Quant State (Morpho + Ethena)*\n\n"
        f"🟢 *Ethena sUSDe (Live 8h Epoch)*\n"
        f"• Real-Time Yield: `{earn_apy:.2f}% APY`\n"
        f"• Unvested Drip: `${drip:.2f}/sec` (`${unvested:,.0f}` rem)\n\n"
        f"🏦 *Morpho Blue (sUSDe/DAI 86% LLTV)*\n"
        f"• Utilization: `{util:.2f}%` ({kink_flag})\n"
        f"• Live Borrow Rate: `{borrow_apy:.2f}% APY`\n"
        f"• +$2M Whale Slippage: `{sim_apy:.2f}% APY`\n\n"
        f"💰 *5x Loop Net Carry:* `{net_5x_roe:+.2f}% ROE`\n\n"
        f"⚡ _Powered by Stateless Multicall3 Quant API_ — [Get API Access on RapidAPI]({STOREFRONT_URL})"
    )

    tg_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    tg_res = requests.post(tg_url, json={
        "chat_id": TG_CHAT,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }, timeout=15)
    tg_res.raise_for_status()
    print("Telegram broadcast sent successfully!")

if __name__ == "__main__":
    broadcast_alpha()
  
