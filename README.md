>📡 **Live Proof-of-Concept Feed:** Watch this API broadcast live Morpho 90% kink stress tests & Ethena epoch drips every 8 hours on our **[Public Telegram Quant Monitor](https://t.me/morpho_ethena_quant)**.

# Morpho Blue & Ethena (sUSDe) Quant Bot Starter Kit (Python)

An open-source Python monitoring and execution-simulation starter kit for **Morpho Blue** leveraged loopers, liquidators, and **Ethena (`sUSDe`)** basis-trade bots.

## The On-Chain Data Bottleneck
If you build automated strategies on **Morpho Blue** or **Ethena**, standard GraphQL subgraphs and raw ERC-4626 RPC calls fail in production for three reasons:
1. **Unaccrued Intra-Block Interest:** Reading Morpho's raw `market()` struct ignores continuous-compounding Taylor expansion interest (`wTaylorCompounded`) accrued since `lastUpdate`, causing inaccurate `borrowShares` to asset conversions and false health factors.
2. **90% Utilization Kink Blindness:** Morpho's `AdaptiveCurveIRM` violently quadruples borrow rates once utilization crosses `90%`. Standard calls only show *past* rates, not forward-looking slippage ($\Delta\text{State} \rightarrow \Delta\text{Rate}$).
3. **Ethena's 8-Hour Vesting Shield:** Calling `sUSDe.totalAssets()` hides `getUnvestedAmount()`. You cannot see the live per-second reward drip or how a whale deposit dilutes current epoch APY.

---

## Quick Start (Zero RPC Setup Required)

This starter kit uses the **[Stateless DeFi Quant Simulators API on RapidAPI](https://rapidapi.com/TimothyWalters/api/defi-quant-simulators-morpho-blue-ethena)** to execute atomic `Multicall3` state simulations and normalize 36-decimal Solidity math (`WAD` / `ORACLE_PRICE_SCALE`) into clean JSON in a single `GET` request.

### 1. Grab a Free API Key
1. Go to the **[DeFi Quant Simulators RapidAPI Hub Page](https://rapidapi.com/TimothyWalters/api/defi-quant-simulators-morpho-blue-ethena)**.
2. Subscribe to the **Basic (Free)** tier (`100 requests/month` — no credit card required to test) or **Pro** for 24/7 bot polling.
3. Copy your `X-RapidAPI-Key` and `X-RapidAPI-Host`.

### 2. Run the Carry & Liquidation Guardian Bot

    pip install requests
    export RAPIDAPI_KEY="your_key_here"
    export RAPIDAPI_HOST="your_host_here.p.rapidapi.com"
    python loop_guardian_bot.py

---

## Included Popular Morpho Blue `marketId`s (Ethereum Mainnet)

Pass any of these verified 32-byte `marketId` strings into `MARKET_ID` inside `loop_guardian_bot.py` (or directly to `/api/v1/morpho/market-and-risk?marketId=...`) to simulate utilization kinks and borrower liquidations across Morpho Blue's largest markets:

| Collateral / Loan Pair | LLTV | Primary Quant Use Case | Verified `marketId` (Copy & Paste) |
| :--- | :--- | :--- | :--- |
| **wstETH / USDC** *(Default)* | `86.0%` | Flagship ETH LST leverage & institutional USDC supply | `0xb323495f7e4148be5643a4ea4a8221eef163e4bccfdedc2a6f4696baacbc86cc` |
| **cbBTC / USDC** | `86.0%` | Largest Bitcoin-backed USDC lending market ($300M+ loans) | `0x64d65c9a2d91c36d56fbc42d69e979335320169b3df63bf92789e2c8883fcc64` |
| **WBTC / USDC** | `86.0%` | Classic Wrapped BTC leverage & curator vault routing | `0x3a85e619751152991742810df6ec69ce473daef99e28a64ab2340d7b7ccfee49` |
| **wstETH / USDT** | `86.0%` | High-utilization Tether market ($130M+ loans, frequent >90% kink spikes) | `0xe7e9694b754c4d4f7e21faf7223f6fa71abaeb10296a4c43a54a7977149687d2` |
| **wstETH / WETH** | `96.5%` | High-leverage ETH staking yield loop (up to 28x leverage) | `0xb8fc70e82bc5bb53e773626fcc6a23f7eefa036918d7ef216ecfb1950a94a85e` |
| **wstETH / WETH** | `94.5%` | Secondary ETH staking yield loop | `0xd0e50cdac92fe2172043f5e0c36532c6369d24947e40968f34a5e8819ca9ec5d` |
| **sUSDe / USDT** | `91.5%` | Ethena `sUSDe` stablecoin carry-trade loop | `0xdc5333039bcf15f1237133f74d5806675d83d9cf19cfd4cfdd9be674842651bf` |
| **sUSDe / DAI** | `86.0%` | Ethena `sUSDe` / Sky (Maker) DAI leveraged basis trade | `0x39d11026eae1c6ec02aa4c0910778664089cdd97c3fd23f68f7cd05e2e95af48` |
| **sUSDe / DAI** | `91.5%` | Aggressive `sUSDe` / DAI leverage loop | `0x1247f1c237eceae0602eab1470a5061a6dd8f734ba88c7cdc5d6109fb0026b28` |
| **fxSAVE / USDC** | `91.5%` | High-yield stablecoin loop (RockawayX / Clearstar curated) | `0x17f7ae1b52670010976b3fe41324cbb2b1eb7dd8f492e51764b2828371b86b84` |

