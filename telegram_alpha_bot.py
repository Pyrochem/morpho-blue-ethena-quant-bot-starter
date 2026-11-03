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
BASE_URL = os.getenv("DEFI_API_BASE_URL", f"https://{RAPIDAPI_HOST}").rstrip("/")


def fetch_endpoint(path: str, params: dict = None) -> dict:
    url = f"{BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    if RAPIDAPI_KEY and "localhost" not in BASE_URL:
        headers["X-RapidAPI-Key"] = RAPIDAPI_KEY
        headers["X-RapidAPI-Host"] = RAPIDAPI_HOST

    resp = requests.get(url, headers=headers, params=params, timeout=25)
    resp.raise_for_status()
    return resp.json()


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
        f"• Live APY: <code>{ethena.get('liveAnnualizedApyPercent', 0)}%</code> | Unvested Drip: <code>${
