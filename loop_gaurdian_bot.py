import os
import requests
from datetime import datetime

# =====================================================================
# CONFIGURATION: Get your API key from RapidAPI Hub
# =====================================================================
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "YOUR_RAPIDAPI_KEY_HERE")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "YOUR_RAPIDAPI_HOST_HERE")

# Default: Morpho Blue sUSDe / DAI (86% LLTV)
MARKET_ID = "0x39d11026eae1c6ec02aa4c0910778664089cdd97c3fd23f68f7cd05e2e95af48"
TARGET_WALLET_ADDRESS = ""  # Optional: Any 0x borrower wallet to track liquidation risk

INITIAL_EQUITY_USD = 100_000
LEVERAGE_MULTIPLIER = 5.0
SIMULATED_NEW_BORROW = 2_000_000

HEADERS = {
    "x-rapidapi-key": RAPIDAPI_KEY,
    "x-rapidapi-host": RAPIDAPI_HOST
}

def run_quant_guardian():
    print("\n" + "="*72)
    print(f" 📡 DEFI QUANT CARRY & RISK GUARDIAN | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*72)

    # 1. Query Ethena sUSDe Intra-Epoch Vesting & Dilution Simulator
    ethena = requests.get(
        f"https://{RAPIDAPI_HOST}/api/v1/ethena/vesting-and-dilution",
        headers=HEADERS,
        params={"simStakeUsde": 25000000},
        timeout=15
    ).json()

    # 2. Query Morpho Blue Kink & Position Risk Simulator
    morpho_params = {"marketId": MARKET_ID, "simBorrowDelta": SIMULATED_NEW_BORROW}
    if TARGET_WALLET_ADDRESS:
        morpho_params["user"] = TARGET_WALLET_ADDRESS

    morpho = requests.get(
        f"https://{RAPIDAPI_HOST}/api/v1/morpho/market-and-risk",
        headers=HEADERS,
        params=morpho_params,
        timeout=15
    ).json()

    earn_apy = ethena["yieldAndDilutionSimulation"]["liveAnnualizedApyPercent"]
    unvested_usde = ethena["vestingMechanics"]["unvestedRemainingUsde"]
    drip_per_sec = ethena["vestingMechanics"]["linearDripUsdePerSecond"]

    borrow_apy = morpho["ratesAndKinkSimulation"]["currentBorrowApyPercent"]
    sim_borrow_apy = morpho["ratesAndKinkSimulation"]["simulatedPostTradeBorrowApyPercent"]
    utilization = morpho["marketState"]["utilizationPercent"]
    above_kink = morpho["ratesAndKinkSimulation"]["isAbove90PercentKink"]

    total_collateral = INITIAL_EQUITY_USD * LEVERAGE_MULTIPLIER
    total_debt = total_collateral - INITIAL_EQUITY_USD
    net_annual_profit = (total_collateral * (earn_apy / 100.0)) - (total_debt * (borrow_apy / 100.0))
    net_daily_profit = net_annual_profit / 365.0

    # What if the market takes on $2M more debt right now?
    sim_annual_cost = total_debt * (sim_borrow_apy / 100.0)
    sim_net_daily_profit = ((total_collateral * (earn_apy / 100.0)) - sim_annual_cost) / 365.0

    print(f"\n📊 1. ETHENA sUSDe LIVE EPOCH STATE")
    print(f"   • Live Annualized APY:     {earn_apy:.2f}%")
    print(f"   • Unvested Epoch Drip:     ${unvested_usde:,.2f} (${drip_per_sec:.2f}/sec)")

    print(f"\n🏦 2. MORPHO BLUE MARKET & KINK SIMULATION")
    print(f"   • Utilization:             {utilization:.2f}% {'⚠️ [ABOVE 90% KINK]' if above_kink else '✅ [<90% Kink]'}")
    print(f"   • Current Borrow APY:      {borrow_apy:.2f}%")
    print(f"   • Post-Trade APY (+$2M):   {sim_borrow_apy:.2f}%")

    print(f"\n💰 3. LEVERAGED LOOP P&L (${INITIAL_EQUITY_USD:,.0f} @ {LEVERAGE_MULTIPLIER}x)")
    print(f"   • Net Daily Carry:         ${net_daily_profit:+,.2f} / day")
    print(f"   • Carry After +$2M Whale:  ${sim_net_daily_profit:+,.2f} / day")

    if morpho.get("borrowerRisk"):
        risk = morpho["borrowerRisk"]
        print(f"\n🔍 4. ON-CHAIN WALLET RISK ({risk['user'][:10]}...)")
        print(f"   • Health Factor:           {risk['healthFactor']}")
        print(f"   • Drop to Liquidation:     {risk['collateralDropToLiquidationPercent']}%")

    print("\n🤖 5. AUTOMATED BOT EXECUTION SIGNAL:")
    if net_daily_profit <= 0:
        print("   🔴 [ACTION: EMERGENCY UNWIND] Loan interest exceeds bond yield!")
    elif above_kink or sim_net_daily_profit <= 0:
        print("   🟡 [ACTION: DE-RISK / HALT LOOPING] Market is near or above the 90% kink.")
    else:
        print(f"   🟢 [ACTION: HOLD & COMPOUND] Safely netting +${net_daily_profit:,.2f}/day.")

    print("="*72 + "\n")

if __name__ == "__main__":
    run_quant_guardian()
