"""
Bot Configuration - Solana Meme Coin Trading Bot
Enhanced with Moralis + Helius + Multi-DEX Support
Adjust these settings before running
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==================== API KEYS & ENDPOINTS ====================
# Primary APIs (at least one required)
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY', '')
MORALIS_API_KEY = os.getenv('MORALIS_API_KEY', '')
SOLANA_RPC_URL = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')

# Feature flags
MORALIS_ENABLED = bool(MORALIS_API_KEY)
HELIUS_ENABLED = bool(HELIUS_API_KEY)

# Validate at least one API is configured
if not (MORALIS_ENABLED or HELIUS_ENABLED):
    raise ValueError("❌ ERROR: At least one API key required - Set MORALIS_API_KEY or HELIUS_API_KEY")

print(f"✅ APIs Configured - Moralis: {MORALIS_ENABLED}, Helius: {HELIUS_ENABLED}")

# Legacy endpoints (kept for compatibility)
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"
HELIUS_MAINNET_URL = "https://mainnet.helius-rpc.com"

# ==================== WALLET CONFIGURATION ====================
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS', '')
WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY', '')

if not WALLET_ADDRESS:
    raise ValueError("❌ ERROR: WALLET_ADDRESS not configured in environment")
if not WALLET_PRIVATE_KEY:
    raise ValueError("❌ ERROR: WALLET_PRIVATE_KEY not configured in environment")

# ==================== TRADING SETTINGS ====================
BUY_AMOUNT_SOL = float(os.getenv('BUY_AMOUNT_SOL', '0.02'))        # Per trade — small test size
TAKE_PROFIT_1_PERCENT = float(os.getenv('TAKE_PROFIT_1_PERCENT', '20'))   # 1.2x (sell 50%)
TAKE_PROFIT_2_PERCENT = float(os.getenv('TAKE_PROFIT_2_PERCENT', '50'))   # 1.5x (sell 50%)
STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '-25'))      # Tightened to -25% — protects capital faster
MAX_OPEN_TRADES = int(os.getenv('MAX_OPEN_TRADES', '2'))          # Only 2 concurrent — max exposure 0.04 SOL at once
PAPER_TRADING = os.getenv('PAPER_TRADING', 'False').lower() == 'true'        # 🚨 LIVE TRADING ENABLED

# ==================== MARKET FILTERS ====================
MIN_LIQUIDITY_USD = float(os.getenv('MIN_LIQUIDITY_USD', '1000'))       # Aggressive — catches very new tokens ($1k min)
MAX_MARKET_CAP_USD = float(os.getenv('MAX_MARKET_CAP_USD', '10000000'))  # $10M cap — wide net for meme coins
MIN_VOLUME_24H_USD = float(os.getenv('MIN_VOLUME_24H_USD', '500'))       # Very low threshold — early stage tokens
MIN_HOLDERS = int(os.getenv('MIN_HOLDERS', '10'))               # Minimal — new tokens start with few holders
MAX_CONCENTRATION = float(os.getenv('MAX_CONCENTRATION', '50'))         # Relaxed — allow up to 50% top holder

# Minimum buy confidence from TA (when OHLCV available)
MIN_BUY_CONFIDENCE = float(os.getenv('MIN_BUY_CONFIDENCE', '50'))        # Lowered from 60 — more trades

# Minimum price change to consider a token (momentum filter)
MIN_PRICE_CHANGE_1H = float(os.getenv('MIN_PRICE_CHANGE_1H', '-10.0'))   # Allow tokens down up to -10% in 1h

# ==================== TECHNICAL ANALYSIS ====================
# Moving Averages
SMA_SHORT = int(os.getenv('SMA_SHORT', '10'))
SMA_LONG = int(os.getenv('SMA_LONG', '20'))
EMA_SHORT = int(os.getenv('EMA_SHORT', '12'))
EMA_LONG = int(os.getenv('EMA_LONG', '26'))

# RSI
RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
RSI_OVERBOUGHT = float(os.getenv('RSI_OVERBOUGHT', '70'))
RSI_OVERSOLD = float(os.getenv('RSI_OVERSOLD', '30'))
RSI_BUY_THRESHOLD = float(os.getenv('RSI_BUY_THRESHOLD', '45'))
RSI_SELL_THRESHOLD = float(os.getenv('RSI_SELL_THRESHOLD', '65'))

# MACD
MACD_FAST = int(os.getenv('MACD_FAST', '12'))
MACD_SLOW = int(os.getenv('MACD_SLOW', '26'))
MACD_SIGNAL = int(os.getenv('MACD_SIGNAL', '9'))

# Bollinger Bands
BB_PERIOD = int(os.getenv('BB_PERIOD', '20'))
BB_STD_DEV = float(os.getenv('BB_STD_DEV', '2'))

# Volume
VOLUME_MA_PERIOD = int(os.getenv('VOLUME_MA_PERIOD', '20'))
MIN_VOLUME_RATIO = float(os.getenv('MIN_VOLUME_RATIO', '1.5'))

# ==================== DEX SETTINGS ====================
DEXES = {
    "raydium": os.getenv('DEX_RAYDIUM', 'True').lower() == 'true',
    "jupiter": os.getenv('DEX_JUPITER', 'True').lower() == 'true',
    "pump_fun": os.getenv('DEX_PUMP_FUN', 'True').lower() == 'true'
}

SLIPPAGE_TOLERANCE = float(os.getenv('SLIPPAGE_TOLERANCE', '3.0'))

# ==================== MONITORING ====================
UPDATE_INTERVAL_SECONDS = int(os.getenv('UPDATE_INTERVAL_SECONDS', '30'))
PRICE_CHECK_INTERVAL = int(os.getenv('PRICE_CHECK_INTERVAL', '5'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== EMERGENCY SETTINGS ====================
ENABLE_PANIC_SELL = os.getenv('ENABLE_PANIC_SELL', 'True').lower() == 'true'
PANIC_SELL_THRESHOLD = float(os.getenv('PANIC_SELL_THRESHOLD', '-30'))      # Panic sell if any position drops -30%
MAX_DAILY_LOSS_PERCENT = float(os.getenv('MAX_DAILY_LOSS_PERCENT', '-15'))    # Stop all trading if wallet down -15% in a day
MAX_TOTAL_LOSS_SOL = float(os.getenv('MAX_TOTAL_LOSS_SOL', '0.4'))        # Hard stop — halt bot if total losses exceed 0.4 SOL

# ==================== PERFORMANCE TARGETS ====================
TARGET_WIN_RATE = float(os.getenv('TARGET_WIN_RATE', '0.80'))
TARGET_PROFIT_FACTOR = float(os.getenv('TARGET_PROFIT_FACTOR', '2.0'))

# ==================== TELEGRAM CONFIGURATION ====================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
SEND_TELEGRAM_MESSAGES = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

# ==================== API RETRY SETTINGS ====================
API_RETRY_ATTEMPTS = int(os.getenv('API_RETRY_ATTEMPTS', '3'))
API_RETRY_DELAY = int(os.getenv('API_RETRY_DELAY', '2'))  # seconds

# ==================== PRINT CONFIGURATION SUMMARY ====================
def print_config_summary():
    """Print configuration summary for debugging"""
    logger.info("=" * 60)
    logger.info("🤖 TRADING BOT CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"💾 Wallet: {WALLET_ADDRESS[:8]}...")
    logger.info(f"📡 APIs: Moralis={MORALIS_ENABLED}, Helius={HELIUS_ENABLED}")
    logger.info(f"���� DEXs: Raydium={DEXES['raydium']}, Jupiter={DEXES['jupiter']}, Pump.fun={DEXES['pump_fun']}")
    logger.info(f"💰 Trade Size: {BUY_AMOUNT_SOL} SOL | Max Trades: {MAX_OPEN_TRADES}")
    logger.info(f"📈 TP: {TAKE_PROFIT_1_PERCENT}% / {TAKE_PROFIT_2_PERCENT}% | SL: {STOP_LOSS_PERCENT}%")
    logger.info(f"🎯 Min Liquidity: ${MIN_LIQUIDITY_USD} | Min Holders: {MIN_HOLDERS}")
    logger.info(f"📊 Paper Trading: {PAPER_TRADING}")
    logger.info("=" * 60)

# Call on import
print_config_summary()
