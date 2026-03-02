"""
Main Trading Bot Engine
Solana Meme Coin Trader with Telegram
"""

import logging
import time
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, Optional, List

from config import *
from technical_analysis import TechnicalAnalysis
from dex_screener import DexScreenerClient
from helius_client import HeliusClient
from raydium_trader import RaydiumTrader
from jupiter_trader import JupiterTrader
from pump_fun_trader import PumpFunTrader
from wallet_manager import WalletManager
from risk_manager import RiskManager
from monitoring import Monitor
from telegram_bot import TelegramBotHandler

load_dotenv()

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SolanaMemeCoinTradingBot:
    """Main trading bot orchestrator"""
    
    def __init__(self):
        """Initialize the bot"""
        logger.info("=" * 60)
        logger.info("SOLANA MEME COIN TRADING BOT v1.0")
        logger.info("=" * 60)
        
        if PAPER_TRADING:
            logger.warning("⚠️ RUNNING IN PAPER TRADING MODE")
        else:
            logger.critical("🚨 RUNNING IN LIVE TRADING MODE")
        
        try:
            private_key = os.getenv('WALLET_PRIVATE_KEY')
            helius_key = os.getenv('HELIUS_API_KEY')
            
            if not private_key:
                raise ValueError("WALLET_PRIVATE_KEY not found in .env")
            
            self.wallet = WalletManager(private_key)
            logger.info(f"Wallet initialized")
            
            self.dex_screener = DexScreenerClient()
            self.helius = HeliusClient()
            
            self.raydium = RaydiumTrader(self.wallet.get_address())
            self.jupiter = JupiterTrader(self.wallet.get_address())
            self.pump_fun = PumpFunTrader(self.wallet.get_address())
            
            self.ta = TechnicalAnalysis()
            self.risk_manager = RiskManager(wallet_balance_sol=100)
            self.monitor = Monitor()
            
            self.telegram = TelegramBotHandler(self)
            logger.info("✅ Telegram bot initialized")
            
            self.monitored_tokens = {}
            self.trading_active = True
            self.start_time = datetime.now()
            
            logger.info("✅ Bot initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            raise
    
    def scan_new_tokens(self) -> List[Dict]:
        """Scan for new tokens"""
        try:
            logger.info("🔍 Scanning for new tokens...")
            
            tokens = self.dex_screener.get_latest_tokens(limit=50)
            filtered_tokens = self.dex_screener.filter_tokens(tokens)
            
            logger.info(f"Found {len(filtered_tokens)} tokens matching criteria")
            
            return filtered_tokens
            
        except Exception as e:
            logger.error(f"Error scanning tokens: {e}")
            return []
    
    def analyze_token(self, token_data: Dict) -> Dict:
        """Analyze a token"""
        try:
            mint = token_data['mint_address']
            
            ohlcv = self.dex_screener.get_token_ohlcv(mint, timeframe="1h")
            
            if not ohlcv or len(ohlcv) < 20:
                return None
            
            analysis = self.ta.calculate_all_indicators(ohlcv)
            
            holder_concentration = self.helius.check_holder_concentration(mint)
            
            result = {
                'token': token_data,
                'analysis': analysis,
                'holder_concentration': holder_concentration,
                'should_buy': self._should_buy(analysis, holder_concentration, token_data)
            }
            
            return result
            
        except Exception as e:
            logger.debug(f"Error analyzing token: {e}")
            return None
    
    def _should_buy(self, analysis: Dict, holder_concentration: Optional[float],
                   token_data: Dict) -> bool:
        """Determine if we should buy"""
        signals = analysis['signals']
        
        if signals['buy_confidence'] < 60:
            return False
        
        if holder_concentration and holder_concentration > MAX_CONCENTRATION:
            return False
        
        return True
    
    def execute_buy(self, token_data: Dict, analysis: Dict) -> Optional[str]:
        """Execute buy order"""
        try:
            mint = token_data['mint_address']
            symbol = token_data['symbol']
            confidence = analysis['signals']['buy_confidence']
            
            can_trade, reason = self.risk_manager.can_open_trade(
                len([p for p in self.risk_manager.positions.values() if p['status'] == 'open']),
                0
            )
            
            if not can_trade:
                logger.warning(f"Cannot open trade: {reason}")
                return None
            
            position_size = self.risk_manager.calculate_position_size(self.risk_manager.wallet_balance)
            
            if PAPER_TRADING:
                logger.info(f"📝 PAPER BUY: {symbol}")
                logger.info(f"   Amount: {position_size} SOL")
                logger.info(f"   Confidence: {confidence:.2f}%")
                
                tx_sig = f"paper_tx_{int(time.time())}"
                
            else:
                tx_sig = self.jupiter.create_swap_transaction(
                    "So11111111111111111111111111111111111111112",
                    mint,
                    position_size
                )
                
                if not tx_sig:
                    tx_sig = self.raydium.create_swap_transaction(
                        "So11111111111111111111111111111111111111112",
                        mint,
                        position_size
                    )
                
                if not tx_sig:
                    tx_sig = self.pump_fun.buy_token(mint, position_size)
                
                if not tx_sig:
                    logger.error(f"Failed to execute buy")
                    return None
            
            if tx_sig:
                self.risk_manager.add_position(
                    mint,
                    token_data['price_usd'],
                    position_size,
                    (position_size / token_data['price_usd']) if token_data['price_usd'] > 0 else 0
                )
                
                self.monitor.log_trade_open(mint, position_size, token_data['price_usd'], confidence)
                
                logger.info(f"✅ BUY ORDER EXECUTED: {tx_sig}")
                return tx_sig
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing buy: {e}")
            return None
    
    def check_open_positions(self):
        """Check open positions"""
        try:
            for mint, position in list(self.risk_manager.positions.items()):
                if position['status'] != 'open':
                    continue
                
                token_data = self.dex_screener.search_token(mint)
                if not token_data:
                    continue
                
                current_price = token_data['price_usd']
                
                self.risk_manager.update_position(mint, current_price)
                position = self.risk_manager.positions[mint]
                
                if self.risk_manager.check_stop_loss(mint):
                    self._execute_sell(mint, current_price, "Stop Loss", position['pnl_percent'])
                    continue
                
                tp_hit, tp_level = self.risk_manager.check_take_profit(mint)
                if tp_hit:
                    self._execute_sell(mint, current_price, f"Take Profit {tp_level}x", position['pnl_percent'])
                
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    def _execute_sell(self, mint: str, current_price: float, reason: str, pnl_percent: float):
        """Execute sell order"""
        try:
            position = self.risk_manager.positions[mint]
            
            if PAPER_TRADING:
                logger.info(f"📝 PAPER SELL: {mint[:8]}...")
                logger.info(f"   Reason: {reason}")
                logger.info(f"   PnL: {pnl_percent:.2f}%")
            else:
                tx_sig = self.pump_fun.sell_token(mint, position['position_size_tokens'])
                
                if not tx_sig:
                    logger.error(f"Failed to execute sell")
                    return
            
            self.risk_manager.close_position(mint, current_price, reason)
            self.monitor.log_trade_close(mint, current_price, pnl_percent, reason)
            
            logger.info(f"✅ SELL ORDER EXECUTED: {reason}")
            
        except Exception as e:
            logger.error(f"Error executing sell: {e}")
    
    def print_status(self):
        """Print bot status"""
        try:
            summary = self.risk_manager.get_portfolio_summary()
            perf = self.monitor.get_performance_summary()
            
            logger.info("\n" + "=" * 60)
            logger.info("📊 BOT STATUS")
            logger.info("=" * 60)
            logger.info(f"Uptime: {datetime.now() - self.start_time}")
            logger.info(f"Open Positions: {summary['open_positions']}")
            logger.info(f"Total Trades: {perf['total_trades']}")
            logger.info(f"Win Rate: {perf['win_rate']}")
            logger.info("=" * 60 + "\n")
            
        except Exception as e:
            logger.error(f"Error printing status: {e}")
    
    def run(self):
        """Main bot loop"""
        logger.info("🚀 Bot starting...")
        
        scan_counter = 0
        
        try:
            while self.trading_active:
                try:
                    if scan_counter % 6 == 0:
                        tokens = self.scan_new_tokens()
                        
                        for token in tokens[:5]:
                            analysis = self.analyze_token(token)
                            
                            if analysis and analysis['should_buy']:
                                self.execute_buy(token, analysis)
                    
                    self.check_open_positions()
                    
                    if scan_counter % 10 == 0:
                        self.print_status()
                    
                    scan_counter += 1
                    time.sleep(UPDATE_INTERVAL_SECONDS)
                    
                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    time.sleep(UPDATE_INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            logger.info("⏹️ Bot shutting down...")
            self.trading_active = False


if __name__ == "__main__":
    bot = SolanaMemeCoinTradingBot()
    bot.run()
