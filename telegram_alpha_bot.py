import os
import time
import requests

RAPIDAPI_KEY = os.environ["RAPIDAPI_KEY"].strip()
RAPIDAPI_HOST_1 = os.environ["RAPIDAPI_HOST"].strip().replace("https://", "").strip("/")
RAPIDAPI_HOST_2 = os.environ.get("RAPIDAPI_HOST_2", RAPIDAPI_HOST_1).strip().replace("https://", "").strip("/")

TG_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TG_CHAT = os.environ["TELEGRAM_CHAT_ID"].strip()

STOREFRONT_MORPHO_ETHENA = "https://rapidapi.com/infio-infio-quant/api/defi-quant-simulators-morpho-blue-ethena"
STOREFRONT_FLUID_SKY = "https://rapidapi.com/infio-infio-quant/api/fluid-bigmath-and-sky-susds-quant-simulators"

MARKET_ID = "0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc"
WSTETH_TOKEN = "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0"
SIM_FLUID_BORROW = 2500
TARGET_SKY_LEVERAGE = 6

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
    ethena = requests.get(
        f"https://{RAPIDAPI_HOST_1}/api/v1/ethena/vesting-and-dilution", 
        headers=h1, 
        params={"simStakeUsde": 25000000}, 
        timeout=20
    ).json() 
    time.sleep(2)
    
    morpho = requests.get(
        f"https://{RAPIDAPI_HOST_1}/api/v1/morpho/market-and-risk", 
        headers=h1, 
        params={"marketId": MARKET_ID, "simBorrowDelta": 2000000}, 
        timeout=20
    ).json()
    time.sleep(2)

    # 2. Fluid & Sky sUSDS (API #2)
    fluid = requests.get(
        f"https://{RAPIDAPI_HOST_2}/api/v1/fluid/liquidity-state", 
        headers=h2, 
        params={"token": WSTETH_TOKEN, "simBorrowDelta": SIM_FLUID_BORROW}, 
        timeout=20
    )
    print("Fluid HTTP Status:", fluid_res.status_code)
    fluid = fluid_res.json()
    time.sleep(2)
    
    sky = requests.get(
        f"https://{RAPIDAPI_HOST_2}/api/v1/sky/susds-carry-simulator", 
        headers=h2, 
        params={"leverage": TARGET_SKY_LEVERAGE}, 
        timeout=20
    )
    print("Sky HTTP Status:", sky_res.status_code)
    sky = sky_res.json()
    
    # Parse API #1
    earn_apy = float(find_val(ethena, ["liveAnnualizedApyPercent", "currentApyPercent"]))
    drip = float(find_val(ethena, ["linearDripUsdePerSecond", "dripPerSecond"]))
    unvested = float(find_val(ethena, ["unvestedRemainingUsde", "unvestedAmount", "unvestedUsde"]))
    
    # Extract Morpho metrics (adapts automatically to your exact schema)
    m_util = float(find_val(morpho, ["utilizationPercent", "utilization"]))
    m_borrow = float(find_val(morpho, ["currentBorrowApyPercent", "borrowApyPercent"]))
    sim_apy = float(find_val(morpho, ["simulatedPostTradeBorrowApyPercent", "postTradeBorrowApyPercent", "simulatedBorrowApyPercent"], m_borrow))
    is_above_kink = bool(find_val(morpho, ["isAbove90PercentKink", "isAboveKink"], m_util >= 90.0))
    kink_flag = "🚨 ABOVE 90% KINK" if is_above_kink else "✅ Below 90% Kink"
    net_5x_roe = ((5.0 * earn_apy) - (4.0 * m_borrow))

    # --- Parse Fluid Protocol (API #2) ---
    f_symbol = str(find_val(fluid, ["symbol"], "wstETH"))
    f_supply = float(find_val(fluid, ["totalSupplyHuman"]))
    f_borrow = float(find_val(fluid, ["totalBorrowHuman"]))
    f_avail = float(find_val(fluid, ["availableLiquidityHuman"]))
    f_util = float(find_val(fluid, ["utilizationPercent"]))
    f_borrow_apr = float(find_val(fluid, ["borrowAprPercent"]))
    f_post_util = float(find_val(fluid, ["postTradeUtilizationPercent"]))

    # --- Parse Sky sUSDS Carry (API #2) ---
    sky_ssr_apy = float(find_val(sky, ["liveSsrApyPercent"]))
    sky_ex_rate = float(find_val(sky, ["exchangeRateUsdsPerSusds"], 1.0))
    sky_bench_borrow = float(find_val(sky, ["morphoBorrowApyPercent"]))
    sky_net_roe = float(find_val(sky, ["netLeveragedRoePercent"]))
    sky_breakeven = float(find_val(sky, ["breakevenBorrowApyPercent"]))
    sky_regime = str(find_val(sky, ["carryRegime"], "UNKNOWN"))

    msg = (
        f"📡 <b>Live DeFi Quant Suite Telemetry (4-Protocol Snapshot)</b>\n\n"
        f"🟢 <b>Ethena sUSDe (8h Epoch):</b>\n" 
        f"• Real-Time Yield: <code>{earn_apy:.2f}% APY</code>\n"
        f"• Unvested Drip: <code>${drip:.2f}/sec</code> (<code>${unvested:,.0f}</code> rem)\n\n"
        f"🏦 <b>Morpho Blue:</b>\n" 
        f"• Utilization: <code>{m_util:.2f}%</code> ({kink_flag})\n"
        f"• Live Borrow Rate: <code>{m_borrow:.2f}% APY</code>\n"
        f"• +$2M Whale Slippage: <code>{sim_apy:.2f}% APY</code>\n\n"
        f"💰 <b>5x Loop Net Carry:</b> <code>{net_5x_roe:+.2f}% ROE</code>\n\n"
        f"💧 <b>Fluid Protocol ({f_symbol} BigMath):</b>\n"
        f"• Total Supply / Borrow: <code>{f_supply:,.2f} {f_symbol}</code> / <code>{f_borrow:,.2f} {f_symbol}</code>\n"
        f"• Available Liquidity: <code>{f_avail:,.2f} {f_symbol}</code>\n"
        f"• Live Utilization & APR: <code>{f_util:.2f}% util</code> @ <code>{f_borrow_apr:.2f}% Borrow APR</code>\n"
        f"• Post-Trade Util (+{SIM_FLUID_BORROW:,} {f_symbol}): <code>{f_post_util:.2f}%</code>\n\n"
        f"☀️ <b>Sky (sUSDS) Live RAY & {TARGET_SKY_LEVERAGE}x Morpho Carry:</b>\n"
        f"• Live Un-Dripped SSR APY: <code>{sky_ssr_apy:.2f}%</code> (<code>1 sUSDS = {sky_ex_rate:.6f} USDS</code>)\n"
        f"• Benchmark Borrow APY: <code>{sky_bench_borrow:.2f}%</code>\n"
        f"• Net {TARGET_SKY_LEVERAGE}x Leveraged ROE: <code>{sky_net_roe:+.2f}% APY</code>\n"
        f"• Breakeven Borrow Ceiling: <code>{sky_breakeven:.2f}% APY</code>\n"
        f"• Carry Regime Signal: <code>[{sky_regime}]</code>\n\n"
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
