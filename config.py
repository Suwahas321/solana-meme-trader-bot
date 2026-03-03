"""
Bot Configuration - Solana Meme Coin Trading Bot
Adjust these settings before running
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== TRADING SETTINGS ====================
BUY_AMOUNT_SOL = 0.02        # Per trade — small test size
TAKE_PROFIT_1_PERCENT = 20   # 1.2x (sell 50%)
TAKE_PROFIT_2_PERCENT = 50   # 1.5x (sell 50%)
STOP_LOSS_PERCENT = -25      # Tightened to -25% — protects capital faster
MAX_OPEN_TRADES = 2          # Only 2 concurrent — max exposure 0.04 SOL at once
PAPER_TRADING = False        # 🚨 LIVE TRADING ENABLED

# ==================== MARKET FILTERS ====================
MIN_LIQUIDITY_USD = 1000       # Aggressive — catches very new tokens ($1k min)
MAX_MARKET_CAP_USD = 10000000  # $10M cap — wide net for meme coins
MIN_VOLUME_24H_USD = 500       # Very low threshold — early stage tokens
MIN_HOLDERS = 10               # Minimal — new tokens start with few holders
MAX_CONCENTRATION = 50         # Relaxed — allow up to 50% top holder

# Minimum buy confidence from TA (when OHLCV available)
MIN_BUY_CONFIDENCE = 50        # Lowered from 60 — more trades

# Minimum price change to consider a token (momentum filter)
MIN_PRICE_CHANGE_1H = -10.0   # Allow tokens down up to -10% in 1h

# ==================== TECHNICAL ANALYSIS ====================
# Moving Averages
SMA_SHORT = 10
SMA_LONG = 20
EMA_SHORT = 12
EMA_LONG = 26

# RSI
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_BUY_THRESHOLD = 45
RSI_SELL_THRESHOLD = 65

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2

# Volume
VOLUME_MA_PERIOD = 20
MIN_VOLUME_RATIO = 1.5

# ==================== DEX SETTINGS ====================
DEXES = {
    "raydium": True,
    "jupiter": True,
    "pump_fun": True
}

SLIPPAGE_TOLERANCE = 3.0

# ==================== API KEYS & ENDPOINTS ====================
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
HELIUS_MAINNET_URL = "https://mainnet.helius-rpc.com"
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Load from environment variables
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY', '')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '')

# ==================== MONITORING ====================
UPDATE_INTERVAL_SECONDS = 30
PRICE_CHECK_INTERVAL = 5
LOG_LEVEL = "INFO"

# ==================== EMERGENCY SETTINGS ====================
ENABLE_PANIC_SELL = True
PANIC_SELL_THRESHOLD = -30      # Panic sell if any position drops -30%
MAX_DAILY_LOSS_PERCENT = -15    # Stop all trading if wallet down -15% in a day
MAX_TOTAL_LOSS_SOL = 0.4        # Hard stop — halt bot if total losses exceed 0.4 SOL

# ==================== PERFORMANCE TARGETS ====================
TARGET_WIN_RATE = 0.80
TARGET_PROFIT_FACTOR = 2.0
