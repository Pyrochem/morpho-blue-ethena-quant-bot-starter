import os
import requests

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"].strip()
RAPIDAPI_HOST_1 = os.environ["RAPIDAPI_HOST"].strip().replace("https://", "").strip("/")
# After creating RapidAPI Project #2, add RAPIDAPI_HOST_2 to GitHub Secrets (or fallback to Host 1)
RAPIDAPI_HOST_2 = os.environ.get("RAPIDAPI_HOST_2", RAPIDAPI_HOST_1).strip().replace("https://", "").strip("/")

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()

STOREFRONT_MORPHO_ETHENA = "https://rapidapi.com/infio-infio-quant/api/defi-quant-simulators-morpho-blue-ethena"
STOREFRONT_FLUID_SKY = "https://rapidapi.com/infio-infio-quant/api/fluid-bigmath-and-sky-susds-quant-simulators"

MARKET_ID = "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"
WSTETH_TOKEN = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"

def find_val(data, target_keys, default=0.0):
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
    h1 = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST_1}
    h2 = {"x-rapidapi-key": RAPIDAPI_KEY, "x-rapidapi-host": RAPIDAPI_HOST_2}

    # 1. Ethena & Morpho (API #1)
    ethena = requests.get(f"https://{RAPIDAPI_HOST_1}/api/v1/ethena/vesting-and-dilution", headers=h1, params={"simStakeUsde": 25000000}, timeout=20).json()
    morpho = requests.get(f"https://{RAPIDAPI_HOST_1}/api/v1/morpho/market-and-risk", headers=h1, params={"marketId": MARKET_ID, "simBorrowDelta": 2000000}, timeout=20).json()

    # 2. Fluid & Sky sUSDS (API #2)
    fluid = requests.get(f"https://{RAPIDAPI_HOST_2}/api/v1/fluid/liquidity-state", headers=h2, params={"token": WSTETH_TOKEN, "simBorrowDelta": 2500}, timeout=20).json()
    sky = requests.get(f"https://{RAPIDAPI_HOST_2}/api/v1/sky/susds-carry-simulator", headers=h2, params={"leverage": 6}, timeout=20).json()

    # Parse API #1
    earn_apy = float(find_val(ethena, ["liveAnnualizedApyPercent", "currentApyPercent"]))
    drip = float(find_val(ethena, ["linearDripUsdePerSecond", "dripPerSecond"]))
    m_util = float(find_val(morpho, ["utilizationPercent", "utilization"]))
    m_borrow = float(find_val(morpho, ["currentBorrowApyPercent", "borrowApyPercent"]))

    # Parse API #2
    f_util = float(find_val(fluid, ["utilizationPercent"]))
    f_borrow = float(find_val(fluid, ["borrowAprPercent"]))
    f_avail = float(find_val(fluid, ["availableLiquidityHuman"]))
    sky_apy = float(find_val(sky, ["liveSsrApyPercent"]))
    sky_roe = float(find_val(sky, ["netLeveragedRoePercent"]))

    msg = (
        f"📡 <b>Live DeFi Quant Suite Telemetry (4-Protocol Snapshot)</b>\n\n"
        f"🟢 <b>Ethena sUSDe (8h Epoch):</b>\n" 
        f"• Real-Time Yield: <code>{earn_apy:.2f}% APY</code>\n"
        f"• Unvested Drip: <code>${drip:.2f}/sec</code> (<code>${unvested:,.0f}</code> rem)\n\n"
        f"🏦 <b>Morpho Blue:</b>\n" 
        f"• Utilization: <code>{util:.2f}%</code> ({kink_flag})\n"
        f"• Live Borrow Rate: <code>{borrow_apy:.2f}% APY</code>\n"
        f"• +$2M Whale Slippage: <code>{sim_apy:.2f}% APY</code>\n\n"
        f"💰 <b>5x Loop Net Carry:</b> <code>{net_5x_roe:+.2f}% ROE</code>\n\n"
        f"💧 <b>Fluid (wstETH BigMath):</b> <code>{f_util:.2f}% Util</code> | <code>{f_borrow:.2f}% APR</code> (<code>{f_avail:,.0f} wstETH</code> avail)\n"
        f"☀️ <b>Sky sUSDS (6x Carry Loop):</b> <code>{sky_apy:.2f}% SSR</code> → <code>{sky_roe:+.2f}% Net ROE</code>\n\n"
        f"⚡ <b>Stateless Multicall3 APIs on RapidAPI:</b>\n"
        f"• <a href='{STOREFRONT_MORPHO_ETHENA}'>Morpho Blue & Ethena Quant API</a>\n"
        f"• <a href='{STOREFRONT_FLUID_SKY}'>Fluid BigMath & Sky sUSDS Quant API</a>"
    )

    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=15
    ).raise_for_status()

if __name__ == "__main__":
    broadcast_alpha()
