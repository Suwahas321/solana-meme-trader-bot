"""
Main Trading Bot Engine - MORALIS FIXED VERSION
Solana Meme Coin Trader with Telegram + Moralis API
Better error handling, retry logic, fallback systems
"""

import logging
import time
import os
import threading
import asyncio
from datetime import datetime
from typing import Dict, Optional, List

from config import *
from technical_analysis import TechnicalAnalysis
from dex_screener import DexScreenerClient  # Now uses Moralis
from helius_client import HeliusClient
from raydium_trader import RaydiumTrader
from jupiter_trader import JupiterTrader
from pump_fun_trader import PumpFunTrader
from wallet_manager import WalletManager
from risk_manager import RiskManager
from monitoring import Monitor
from telegram_bot import TelegramBotHandler

logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SolanaMemeCoinTradingBot:
    """Main trading bot orchestrator"""

    def __init__(self):
        logger.info("=" * 70)
        logger.info("SOLANA MEME COIN TRADING BOT v2.0 - MORALIS EDITION")
        logger.info("=" * 70)

        if PAPER_TRADING:
            logger.warning("⚠️ RUNNING IN PAPER TRADING MODE")
        else:
            logger.critical("🚨 RUNNING IN LIVE TRADING MODE")

        self.wallet = None
        self.telegram = None
        self.trading_active = True
        self.start_time = datetime.now()
        
        try:
            # ===== WALLET INITIALIZATION =====
            logger.info("=" * 70)
            logger.info("STEP 1: LOADING WALLET")
            logger.info("=" * 70)
            
            private_key = os.getenv('WALLET_PRIVATE_KEY')
            
            if not private_key:
                logger.error("❌ WALLET_PRIVATE_KEY not found!")
                logger.error("❌ Set it in Railway Variables")
                self.wallet = None
            else:
                try:
                    logger.info("✅ Private key found, initializing wallet...")
                    self.wallet = WalletManager(private_key)
                    addr = self.wallet.get_address()
                    if addr and addr != "not_initialized":
                        logger.info(f"✅ WALLET INITIALIZED: {addr[:12]}...")
                    else:
                        logger.error("❌ Wallet address not initialized")
                        self.wallet = None
                except Exception as e:
                    logger.error(f"❌ Wallet error: {e}")
                    self.wallet = None
            
            # ===== API CLIENTS =====
            logger.info("=" * 70)
            logger.info("STEP 2: INITIALIZING API CLIENTS")
            logger.info("=" * 70)
            
            try:
                self.dex_screener = DexScreenerClient()
                logger.info("✅ Moralis token discovery initialized")
            except Exception as e:
                logger.error(f"❌ Token discovery error: {e}")
                self.dex_screener = None
            
            try:
                self.helius = HeliusClient()
                logger.info("✅ Helius client initialized")
            except Exception as e:
                logger.error(f"❌ Helius error: {e}")
                self.helius = None
            
            try:
                wallet_addr = self.wallet.get_address() if self.wallet else "default"
                self.raydium = RaydiumTrader(wallet_addr)
                logger.info("✅ Raydium trader initialized")
            except Exception as e:
                logger.error(f"⚠️ Raydium error: {e}")
                self.raydium = None
            
            try:
                wallet_addr = self.wallet.get_address() if self.wallet else "default"
                self.jupiter = JupiterTrader(wallet_addr)
                logger.info("✅ Jupiter trader initialized")
            except Exception as e:
                logger.error(f"⚠️ Jupiter error: {e}")
                self.jupiter = None
            
            try:
                wallet_addr = self.wallet.get_address() if self.wallet else "default"
                self.pump_fun = PumpFunTrader(wallet_addr)
                logger.info("✅ Pump.fun trader initialized")
            except Exception as e:
                logger.error(f"⚠️ Pump.fun error: {e}")
                self.pump_fun = None
            
            # ===== ANALYSIS & RISK =====
            logger.info("=" * 70)
            logger.info("STEP 3: INITIALIZING ANALYSIS & RISK MANAGEMENT")
            logger.info("=" * 70)
            
            try:
                self.ta = TechnicalAnalysis()
                logger.info("✅ Technical analysis initialized")
            except Exception as e:
                logger.error(f"❌ TA error: {e}")
                self.ta = None
            
            try:
                balance = 100.0
                if self.wallet:
                    try:
                        balance = self.wallet.get_balance() or 100.0
                    except:
                        balance = 100.0
                
                self.risk_manager = RiskManager(wallet_balance_sol=balance)
                logger.info(f"✅ Risk manager initialized (balance: {balance:.4f} SOL)")
            except Exception as e:
                logger.error(f"❌ Risk manager error: {e}")
                self.risk_manager = None
            
            try:
                self.monitor = Monitor()
                logger.info("✅ Monitor initialized")
            except Exception as e:
                logger.error(f"❌ Monitor error: {e}")
                self.monitor = None
            
            # ===== TELEGRAM =====
            logger.info("=" * 70)
            logger.info("STEP 4: INITIALIZING TELEGRAM BOT")
            logger.info("=" * 70)
            
            try:
                self.telegram = TelegramBotHandler(self)
                self.telegram.start_polling()
                logger.info("✅ Telegram bot initialized")
            except Exception as e:
                logger.error(f"⚠️ Telegram error: {e}")
                logger.warning("⚠️ Bot will run without Telegram")
                self.telegram = None
            
            logger.info("=" * 70)
            logger.info("✅ BOT INITIALIZATION COMPLETE")
            logger.info("=" * 70)
            
        except Exception as e:
            logger.error(f"❌ Critical initialization error: {e}")
            raise
    
    def scan_new_tokens(self) -> List[Dict]:
        """Scan for new tokens with error handling"""
        try:
            if not self.dex_screener:
                logger.warning("⚠️ Token discovery not available")
                return []
            
            logger.info("🔍 Scanning for new tokens...")
            
            try:
                tokens = self.dex_screener.get_latest_tokens(limit=50)
            except Exception as e:
                logger.error(f"Error getting tokens: {e}")
                return []
            
            if not tokens:
                logger.warning("⚠️ No tokens found")
                return []
            
            filtered_tokens = self.dex_screener.filter_tokens(tokens)
            logger.info(f"✅ Found {len(filtered_tokens)} tokens")
            
            return filtered_tokens
            
        except Exception as e:
            logger.error(f"Error scanning: {e}")
            return []
    
    def analyze_token(self, token_data: Dict) -> Optional[Dict]:
        """Analyze token with error handling"""
        try:
            if not self.ta:
                return None
            
            mint = token_data.get('mint_address')
            if not mint:
                return None
            
            # Try to get OHLCV data
            try:
                ohlcv = self.dex_screener.get_token_ohlcv(mint, "1h")
            except:
                logger.debug(f"Could not get OHLCV for {mint}")
                ohlcv = []
            
            if not ohlcv or len(ohlcv) < 20:
                logger.debug(f"Insufficient OHLCV data for {mint}")
                return None
            
            analysis = self.ta.calculate_all_indicators(ohlcv)
            
            # Try holder concentration check
            holder_concentration = None
            if self.helius:
                try:
                    holder_concentration = self.helius.check_holder_concentration(mint)
                except:
                    logger.debug(f"Could not check holders for {mint}")
            
            should_buy = self._should_buy(analysis, holder_concentration, token_data)
            
            return {
                'token': token_data,
                'analysis': analysis,
                'holder_concentration': holder_concentration,
                'should_buy': should_buy
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing token: {e}")
            return None
    
    def _should_buy(self, analysis: Dict, holder_concentration: Optional[float],
                   token_data: Dict) -> bool:
        """Determine if should buy"""
        try:
            signals = analysis.get('signals', {})
            
            if signals.get('buy_confidence', 0) < 60:
                return False
            
            if holder_concentration and holder_concentration > MAX_CONCENTRATION:
                logger.debug(f"Holder concentration too high: {holder_concentration}%")
                return False
            
            return True
        except:
            return False
    
    def execute_buy(self, token_data: Dict, analysis: Dict) -> Optional[str]:
        """Execute buy with error handling"""
        try:
            if not self.risk_manager:
                return None
            
            mint = token_data.get('mint_address')
            symbol = token_data.get('symbol', 'UNKNOWN')
            
            try:
                can_trade, reason = self.risk_manager.can_open_trade(
                    len([p for p in self.risk_manager.positions.values() if p.get('status') == 'open']),
                    0
                )
            except:
                can_trade = False
                reason = "Risk check failed"
            
            if not can_trade:
                logger.debug(f"Cannot trade: {reason}")
                return None
            
            try:
                position_size = self.risk_manager.calculate_position_size(self.risk_manager.wallet_balance)
            except:
                position_size = 0.01
            
            confidence = analysis.get('signals', {}).get('buy_confidence', 0)
            
            if PAPER_TRADING:
                logger.info(f"📝 PAPER BUY: {symbol} @ {position_size} SOL ({confidence:.2f}%)")
                tx_sig = f"paper_tx_{int(time.time())}"
            else:
                logger.info(f"🟢 LIVE BUY: {symbol}")
                tx_sig = None
                
                # Try Jupiter
                if self.jupiter:
                    try:
                        tx_sig = self.jupiter.create_swap_transaction(
                            "So11111111111111111111111111111111111111112",
                            mint,
                            position_size
                        )
                        if tx_sig:
                            logger.info(f"✅ Jupiter swap: {tx_sig}")
                    except Exception as e:
                        logger.warning(f"Jupiter failed: {e}")
                
                # Try Raydium
                if not tx_sig and self.raydium:
                    try:
                        tx_sig = self.raydium.create_swap_transaction(
                            "So11111111111111111111111111111111111111112",
                            mint,
                            position_size
                        )
                        if tx_sig:
                            logger.info(f"✅ Raydium swap: {tx_sig}")
                    except Exception as e:
                        logger.warning(f"Raydium failed: {e}")
                
                # Try Pump.fun
                if not tx_sig and self.pump_fun:
                    try:
                        tx_sig = self.pump_fun.buy_token(mint, position_size)
                        if tx_sig:
                            logger.info(f"✅ Pump.fun swap: {tx_sig}")
                    except Exception as e:
                        logger.warning(f"Pump.fun failed: {e}")
                
                if not tx_sig:
                    logger.error(f"❌ All DEX trades failed for {symbol}")
                    return None
            
            if tx_sig and self.risk_manager:
                try:
                    price = token_data.get('price_usd', 0)
                    self.risk_manager.add_position(mint, price, position_size, 
                        (position_size / price) if price > 0 else 0)
                    
                    if self.monitor:
                        self.monitor.log_trade_open(mint, position_size, price, confidence)
                except Exception as e:
                    logger.error(f"Error recording position: {e}")
            
            return tx_sig
            
        except Exception as e:
            logger.error(f"Error executing buy: {e}")
            return None
    
    def check_open_positions(self):
        """Check positions with error handling"""
        try:
            if not self.risk_manager:
                return
            
            for mint, position in list(self.risk_manager.positions.items()):
                try:
                    if position.get('status') != 'open':
                        continue
                    
                    if not self.dex_screener:
                        continue
                    
                    token_data = self.dex_screener.search_token(mint)
                    if not token_data:
                        continue
                    
                    current_price = token_data.get('price_usd', 0)
                    if current_price <= 0:
                        continue
                    
                    self.risk_manager.update_position(mint, current_price)
                    position = self.risk_manager.positions.get(mint, {})
                    
                    if self.risk_manager.check_stop_loss(mint):
                        self._execute_sell(mint, current_price, "Stop Loss", position.get('pnl_percent', 0))
                        continue
                    
                    tp_hit, tp_level = self.risk_manager.check_take_profit(mint)
                    if tp_hit:
                        self._execute_sell(mint, current_price, f"Take Profit {tp_level}x", position.get('pnl_percent', 0))
                
                except Exception as e:
                    logger.debug(f"Error checking position {mint}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error checking positions: {e}")
    
    def _execute_sell(self, mint: str, current_price: float, reason: str, pnl_percent: float):
        """Execute sell with error handling"""
        try:
            if not self.risk_manager:
                return
            
            position = self.risk_manager.positions.get(mint)
            if not position:
                return
            
            if PAPER_TRADING:
                logger.info(f"📝 PAPER SELL: {reason} | PnL: {pnl_percent:.2f}%")
            else:
                logger.info(f"🔴 LIVE SELL: {reason}")
                
                if self.pump_fun:
                    try:
                        tx_sig = self.pump_fun.sell_token(mint, position.get('position_size_tokens', 0))
                        if tx_sig:
                            logger.info(f"✅ Sell executed: {tx_sig}")
                    except Exception as e:
                        logger.error(f"Sell error: {e}")
                        return
            
            self.risk_manager.close_position(mint, current_price, reason)
            
            if self.monitor:
                self.monitor.log_trade_close(mint, current_price, pnl_percent, reason)
            
            logger.info(f"✅ Position closed: {reason}")
        
        except Exception as e:
            logger.error(f"Error executing sell: {e}")
    
    def print_status(self):
        """Print bot status"""
        try:
            logger.info("\n" + "=" * 70)
            logger.info("📊 BOT STATUS")
            logger.info("=" * 70)
            logger.info(f"Uptime: {datetime.now() - self.start_time}")
            
            if self.wallet:
                logger.info(f"Wallet: ✅ Connected")
            else:
                logger.info(f"Wallet: ⚠️ Not connected")
            
            if self.telegram:
                logger.info(f"Telegram: ✅ Connected")
            else:
                logger.info(f"Telegram: ⚠️ Not connected")
            
            if self.risk_manager:
                try:
                    summary = self.risk_manager.get_portfolio_summary()
                    logger.info(f"Open positions: {summary.get('open_positions', 0)}")
                    logger.info(f"Total trades: {summary.get('total_trades', 0)}")
                except:
                    pass
            
            logger.info("=" * 70 + "\n")
        
        except Exception as e:
            logger.error(f"Status error: {e}")
    
    def run(self):
        """Main bot loop"""
        logger.info("🚀 Starting trading loop...")
        logger.info("=" * 70)
        
        scan_counter = 0
        
        try:
            while self.trading_active:
                try:
                    # Scan every 6 iterations (~3 minutes)
                    if scan_counter % 6 == 0:
                        tokens = self.scan_new_tokens()
                        
                        for token in tokens[:5]:
                            try:
                                analysis = self.analyze_token(token)
                                
                                if analysis and analysis.get('should_buy'):
                                    self.execute_buy(token, analysis)
                            except Exception as e:
                                logger.debug(f"Error processing token: {e}")
                                continue
                    
                    # Check positions continuously
                    self.check_open_positions()
                    
                    # Print status every 10 iterations
                    if scan_counter % 10 == 0:
                        self.print_status()
                    
                    scan_counter += 1
                    time.sleep(UPDATE_INTERVAL_SECONDS)
                
                except Exception as e:
                    logger.error(f"Loop error: {e}")
                    time.sleep(UPDATE_INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            logger.info("⏹️ Bot shutting down...")
            self.trading_active = False


if __name__ == "__main__":
    try:
        bot = SolanaMemeCoinTradingBot()
        bot.run()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
