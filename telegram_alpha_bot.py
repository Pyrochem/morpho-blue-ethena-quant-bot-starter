import os
import requests

# Existing secrets already configured in your environment / GitHub Actions
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_HOST = os.getenv(
    "RAPIDAPI_HOST", "defi-quant-multi-protocol-yield-risk-api.p.rapidapi.com"
).strip()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
RAPIDAPI_HUB_URL = os.getenv(
    "RAPIDAPI_HUB_URL",
    f"https://rapidapi.com/infio-infio-quant/api/defi-quant-multi-protocol-yield-risk-api",
).strip()

# Optional override if testing against Render or localhost directly
BASE_URL = (os.getenv("DEFI_API_BASE_URL") or f"https://{RAPIDAPI_HOST}").strip().rstrip("/")


def fetch_endpoint(path: str, params: dict = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    if RAPIDAPI_KEY and "localhost" not in BASE_URL:
        headers["X-RapidAPI-Key"] = RAPIDAPI_KEY
        headers["X-RapidAPI-Host"] = RAPIDAPI_HOST

     # Print the LAST 22 characters so we see .onrender.com vs .p.rapidapi.com
    unmasked_suffix = " ".join(BASE_URL[-22:])

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=25)
        is_rapidapi_proxy = "rapidapi" in str(resp.headers).lower()
        print(f"[DEBUG] Suffix: {unmasked_suffix} | Via RapidAPI Proxy: {is_rapidapi_proxy} | Status: {resp.status_code}")

        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[WARN] Non-200 response ({resp.status_code}) on {path}: {resp.text[:200]}")
            return {"error": f"HTTP {resp.status_code}", "raw": resp.text}
    except Exception as e:
        print(f"[ERROR] Request failed on {path}: {e}")
        return {"error": str(e)}


def format_num(val, decimals=2):
    if val is None or val == "UNLIMITED":
        return str(val)
    try:
        return f"{float(val):,.{decimals}f}"
    except (ValueError, TypeError):
        return str(val)


def build_digest_message() -> str:
    # 1. Cross-Protocol Stablecoin Carry Radar
    radar = fetch_endpoint("/api/v1/radar/stablecoin-yield-matrix", {"leverage": 5})
    # 2. Morpho Blue
    morpho = fetch_endpoint("/api/v1/morpho/market-and-risk", {"simBorrowDelta": 2000000})
    # 3. Ethena sUSDe
    ethena = fetch_endpoint("/api/v1/ethena/vesting-and-dilution", {"simStakeUsde": 25000000})
    # 4. Fluid Protocol
    fluid = fetch_endpoint("/api/v1/fluid/liquidity-state", {"simBorrowDelta": 2500})
    # 5. Sky Protocol sUSDS
    sky = fetch_endpoint("/api/v1/sky/susds-carry-simulator", {"leverage": 6})
    # 6. Euler V2
    euler = fetch_endpoint(
        "/api/v1/euler-v2/vault-and-evc-simulator", {"simBorrowDelta": 1000000}
    )
    # 7. Pendle V2 (Dynamic Active Market Resolution)
    pendle = fetch_endpoint(
        "/api/v1/pendle-v2/logit-curve-and-twap",
        {"twapSeconds": 900, "simPtSwapDelta": 25000},
    )

    block_num = radar.get("blockNumber", morpho.get("blockNumber", "Latest"))
    arb = radar.get("arbitrageSummary", {})
    best_yield = arb.get("bestYieldLeg", {})
    cheapest_debt = arb.get("cheapestDebtLeg", {})

    kink_badge = "⚠️ <b>ABOVE 90% KINK</b>" if morpho.get("isAbove90Kink") else "✅ Below Kink"

    euler_vault = euler.get("vault", {})
    euler_rates = euler.get("liquidityAndRates", {})
    euler_sim = euler.get("irmKinkSimulation", {})
    euler_caps = euler.get("amountCapsDecoded", {})

    pendle_pt = pendle.get("tokens", {}).get("PT", {})
    pendle_mat = pendle.get("maturityProfile", {})
    pendle_curve = pendle.get("logitCurveState", {})
    pendle_rates = pendle.get("ratesAndOracleComparison", {})
    pendle_sim = pendle.get("tradeSimulation") or {}

    twap_apy = pendle_rates.get("twapImpliedFixedApyPercent")
    twap_str = f"{twap_apy}%" if twap_apy is not None else "N/A"
    swap_shift = pendle_sim.get("impliedApyShiftBps")
    swap_str = f"{swap_shift} bps" if swap_shift is not None else "N/A"

    lines = [
        "⚡ <b>DeFi Quant 6-Protocol Radar & Risk Telemetry</b>",
        f"📦 <b>Ethereum Block:</b> <code>#{block_num}</code>",
        "",
        "🎯 <b>1. Cross-Protocol Stablecoin Carry Radar (5x Loop)</b>",
        f"• Best Yield Leg: <b>{best_yield.get('protocol', 'N/A')}</b> (<code>{best_yield.get('apyPercent', 0)}%</code>)",
        f"• Cheapest Debt Leg: <b>{cheapest_debt.get('protocol', 'N/A')}</b> (<code>{cheapest_debt.get('apyPercent', 0)}%</code>)",
        f"• Net Spread: <code>{arb.get('unleveragedSpreadBps', 0)} bps</code> | <b>5x Loop ROE: {arb.get('projectedNetLoopRoePercent', 0)}%</b>",
        "",
        f"🦋 <b>2. Morpho Blue ({morpho.get('loanSymbol', 'USDC')} AdaptiveCurveIRM)</b>",
        f"• Utilization: <code>{morpho.get('utilizationPercent', 0)}%</code> ({kink_badge})",
        f"• Borrow APY: <code>{morpho.get('currentBorrowApyPercent', 0)}%</code> → Post-$2M Borrow: <code>{morpho.get('simulatedPostTradeBorrowApyPercent', 0)}%</code>",
        "",
        "🌊 <b>3. Ethena sUSDe (8h Epoch Vesting & Dilution)</b>",
        f"• Live APY: <code>{ethena.get('liveAnnualizedApyPercent', 0)}%</code> | Unvested Drip: <code>${format_num(ethena.get('unvestedRemainingUsde', 0), 0)}</code>",
        f"• Post-$25M Whale Stake Diluted APY: <code>{ethena.get('postTradeDilutedApyPercent', 0)}%</code>",
        "",
        f"💧 <b>4. Fluid Liquidity Layer (56|8 BigMath - {fluid.get('symbol', 'wstETH')})</b>",
        f"• Utilization: <code>{fluid.get('utilizationPercent', 0)}%</code> | Borrow APR: <code>{fluid.get('borrowAprPercent', 0)}%</code>",
        f"• Available Liquidity: <code>{format_num(fluid.get('availableLiquidityHuman', 0))} {fluid.get('symbol', '')}</code>",
        "",
        "☀️ <b>5. Sky Protocol sUSDS (RAY Continuous Carry)</b>",
        f"• Live SSR APY: <code>{sky.get('liveSsrApyPercent', 0)}%</code> | Rate: <code>{sky.get('exchangeRateUsdsPerSusds', 0)}</code>",
        f"• 6x Leveraged ROE vs Morpho: <code>{sky.get('netLeveragedRoePercent', 0)}%</code> (<code>{sky.get('carryRegime', '')}</code>)",
        "",
        f"🛡️ <b>6. Euler V2 ({euler_vault.get('symbol', 'eUSDC')} EVK Vault Caps & Kink)</b>",
        f"• Util: <code>{euler_rates.get('utilizationPercent', 0)}%</code> | Borrow APY: <code>{euler_rates.get('borrowApyPercent', 0)}%</code> → Post-$1M: <code>{euler_sim.get('postTradeBorrowApyPercent', 0)}%</code>",
        f"• Borrow Cap Headroom: <code>{format_num(euler_caps.get('remainingBorrowHeadroomHuman', 'UNLIMITED'), 0)}</code>",
        "",
        f"⏳ <b>7. Pendle V2 ({pendle_pt.get('symbol', 'PT')} Logit Curve & TWAP)</b>",
        f"• Maturity: <code>{pendle_mat.get('daysToMaturity', 0)}d</code> | PT Pool Ratio: <code>{pendle_curve.get('ptPoolProportionPercent', 0)}%</code>",
        f"• Spot Implied APY: <code>{pendle_rates.get('spotImpliedFixedApyPercent', 0)}%</code> | 15m TWAP: <code>{twap_str}</code>",
        f"• 25k PT Swap Slippage: <code>{swap_str}</code>",
        "",
        "🔌 <b>API & Claude/Cursor MCP Server:</b>",
        f"<a href='{RAPIDAPI_HUB_URL}'>RapidAPI Flagship Suite</a> | <code>npx defi-quant-mcp-server</code>",
    ]
    return "\n".join(lines)


def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID environment variables.")

    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(tg_url, json=payload, timeout=15)
    resp.raise_for_status()
    print("✅ Successfully broadcast 7-endpoint Quant Briefing to Telegram!")


if __name__ == "__main__":
    digest = build_digest_message()
    send_telegram_message(digest)
