"""
Bot Configuration - Solana Meme Coin Trading Bot
Adjust these settings before running
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== TRADING SETTINGS ====================
BUY_AMOUNT_SOL = 0.01  # Per trade
TAKE_PROFIT_1_PERCENT = 300  # 3x (sell 50%)
TAKE_PROFIT_2_PERCENT = 500  # 5x (sell 50%)
STOP_LOSS_PERCENT = -35  # -35%
MAX_OPEN_TRADES = 3  # Max concurrent positions
PAPER_TRADING = True  # Set to False for LIVE TRADING ⚠️

# ==================== MARKET FILTERS ====================
MIN_LIQUIDITY_USD = 10000
MAX_MARKET_CAP_USD = 500000
MIN_VOLUME_24H_USD = 5000
MIN_HOLDERS = 100
MAX_CONCENTRATION = 30  # Top holder shouldn't be >30%

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
PANIC_SELL_THRESHOLD = -50
MAX_DAILY_LOSS_PERCENT = -20

# ==================== PERFORMANCE TARGETS ====================
TARGET_WIN_RATE = 0.80
TARGET_PROFIT_FACTOR = 2.0
