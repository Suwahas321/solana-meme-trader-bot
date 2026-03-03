"""
Main Trading Bot Engine
Solana Meme Coin Trader with Telegram
"""

import logging
import time
import os
import threading
import asyncio
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
        logger.info("=" * 60)
        logger.info("SOLANA MEME COIN TRADING BOT v1.1")
        logger.info("=" * 60)

        if PAPER_TRADING:
            logger.warning("⚠️ RUNNING IN PAPER TRADING MODE")
        else:
            logger.critical("🚨 RUNNING IN LIVE TRADING MODE")

        try:
            private_key = os.getenv('WALLET_PRIVATE_KEY')
            if not private_key:
                raise ValueError("WALLET_PRIVATE_KEY not found in .env")

            # --- Wallet ---
            self.wallet = WalletManager(private_key)
            logger.info(f"Wallet initialized: {self.wallet.get_address()}")

            # --- Get REAL wallet balance for RiskManager ---
            real_balance = self.wallet.get_balance()
            if real_balance is None or real_balance == 0:
                real_balance = 0.1  # Safe fallback if API unavailable
                logger.warning(f"⚠️ Could not fetch real balance — using fallback {real_balance} SOL")
            else:
                logger.info(f"✅ Real wallet balance: {real_balance:.4f} SOL")

            # --- Market data ---
            self.dex_screener = DexScreenerClient()
            self.helius = HeliusClient()

            # --- DEX traders ---
            self.raydium = RaydiumTrader(self.wallet.get_address())
            self.jupiter = JupiterTrader(self.wallet.get_address())
            self.pump_fun = PumpFunTrader(self.wallet.get_address())

            # --- Analysis & Risk (use REAL balance) ---
            self.ta = TechnicalAnalysis()
            self.risk_manager = RiskManager(wallet_balance_sol=real_balance)
            self.monitor = Monitor()

            self.start_time = datetime.now()
            self.trading_active = True

            # Track tokens we've already traded to avoid re-entry
            self._traded_mints: set = set()

            # --- Telegram ---
            try:
                self.telegram = TelegramBotHandler(self)
                self.telegram.start_polling()
                logger.info("✅ Telegram bot initialized")
            except Exception as e:
                logger.warning(f"⚠️ Telegram init warning: {e}")
                self.telegram = None

            self.monitored_tokens = {}
            logger.info("✅ Bot initialized successfully")

        except Exception as e:
            logger.error(f"❌ Initialization error: {e}")
            raise

    def scan_new_tokens(self) -> List[Dict]:
        """Scan for new tokens"""
        try:
            logger.info("🔍 Scanning for new tokens...")
            tokens = self.dex_screener.get_latest_tokens(limit=80)
            logger.info(f"Raw fetch: {len(tokens)} tokens")
            filtered = self.dex_screener.filter_tokens(tokens)
            logger.info(f"After filter: {len(filtered)} tokens pass criteria")
            return filtered
        except Exception as e:
            logger.error(f"Error scanning tokens: {e}")
            return []

    def analyze_token(self, token_data: Dict) -> Optional[Dict]:
        """
        Analyze a token.
        - If OHLCV data is available, use full TA.
        - If not (DexScreener free tier), use market signal scoring from pair data.
        """
        try:
            mint = token_data.get('mint_address')
            if not mint:
                return None

            # Skip already traded tokens this session
            if mint in self._traded_mints:
                return None

            # Try TA (will return empty list on free tier)
            ohlcv = self.dex_screener.get_token_ohlcv(mint, timeframe="1h")

            if ohlcv and len(ohlcv) >= 20:
                # Full technical analysis path
                analysis = self.ta.calculate_all_indicators(ohlcv)
                holder_concentration = self.helius.check_holder_concentration(mint)
                return {
                    'token': token_data,
                    'analysis': analysis,
                    'holder_concentration': holder_concentration,
                    'analysis_method': 'ta',
                    'should_buy': self._should_buy_ta(analysis, holder_concentration, token_data)
                }
            else:
                # Market signals path (no OHLCV available)
                score, reasons = self._score_token_market_signals(token_data)
                confidence = (score / 7) * 100  # Normalise to %
                holder_concentration = self.helius.check_holder_concentration(mint)

                should_buy = (
                    confidence >= MIN_BUY_CONFIDENCE
                    and (holder_concentration is None or holder_concentration <= MAX_CONCENTRATION)
                )

                logger.info(
                    f"📊 {token_data.get('symbol','?')} | "
                    f"score={score}/7 ({confidence:.0f}%) | "
                    f"buy={should_buy} | {', '.join(reasons)}"
                )

                return {
                    'token': token_data,
                    'analysis': {
                        'signals': {
                            'buy_confidence': confidence,
                            'should_buy': should_buy,
                            'active_signals': score,
                            'total_signals': 7,
                            'signal_alignment': f"{score}/7"
                        }
                    },
                    'holder_concentration': holder_concentration,
                    'analysis_method': 'market_signals',
                    'should_buy': should_buy
                }

        except Exception as e:
            logger.debug(f"Error analyzing token {token_data.get('symbol','?')}: {e}")
            return None

    def _score_token_market_signals(self, token_data: Dict):
        """
        Score a token 0-7 based on market data available from DexScreener.
        Returns (score, list_of_triggered_reasons).
        """
        score = 0
        reasons = []

        # 1. Any positive 24h price momentum
        pc24 = token_data.get('price_change_24h', 0)
        if pc24 > 0:
            score += 1
            reasons.append(f"24h+{pc24:.0f}%")

        # 2. Any positive 1h momentum
        pc1h = token_data.get('price_change_1h', 0)
        if pc1h > 0:
            score += 1
            reasons.append(f"1h+{pc1h:.1f}%")

        # 3. Liquidity above minimum (aggressive — just needs to pass filter)
        liq = token_data.get('liquidity_usd', 0)
        if liq >= MIN_LIQUIDITY_USD:
            score += 1
            reasons.append(f"liq=${liq:,.0f}")

        # 4. Any meaningful volume
        vol = token_data.get('volume_24h_usd', 0)
        if vol >= MIN_VOLUME_24H_USD * 2:
            score += 1
            reasons.append(f"vol=${vol:,.0f}")

        # 5. Buy/sell ratio >= 1.0 (at least equal buyers vs sellers)
        bsr = token_data.get('buy_sell_ratio', 1.0)
        if bsr >= 1.0:
            score += 1
            reasons.append(f"bsr={bsr:.2f}")

        # 6. Any valid market cap present
        mc = token_data.get('market_cap_usd', 0)
        if mc > 0:
            score += 1
            reasons.append(f"mc=${mc:,.0f}")

        # 7. Any buy activity in 24h (>= 20 buys)
        buys = token_data.get('buys_24h', 0)
        if buys >= 20:
            score += 1
            reasons.append(f"buys={buys}")

        return score, reasons

    def _should_buy_ta(self, analysis: Dict, holder_concentration: Optional[float],
                       token_data: Dict) -> bool:
        """Gate for TA-based analysis path"""
        signals = analysis.get('signals', {})
        if signals.get('buy_confidence', 0) < MIN_BUY_CONFIDENCE:
            return False
        if holder_concentration and holder_concentration > MAX_CONCENTRATION:
            return False
        return True

    def execute_buy(self, token_data: Dict, analysis: Dict) -> Optional[str]:
        """Execute buy order"""
        try:
            mint = token_data['mint_address']
            symbol = token_data.get('symbol', '?')
            confidence = analysis['analysis']['signals']['buy_confidence']

            open_count = len([p for p in self.risk_manager.positions.values() if p['status'] == 'open'])
            can_trade, reason = self.risk_manager.can_open_trade(open_count, 0)

            if not can_trade:
                logger.warning(f"Cannot open trade: {reason}")
                return None

            # Refresh wallet balance before buying
            real_balance = self.wallet.get_balance()
            if real_balance is not None:
                self.risk_manager.wallet_balance = real_balance

            position_size = self.risk_manager.calculate_position_size(self.risk_manager.wallet_balance)

            if PAPER_TRADING:
                logger.info(f"📝 PAPER BUY: {symbol} | {position_size} SOL | confidence={confidence:.1f}%")
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
                    logger.error("All DEX buy attempts failed")
                    return None

            if tx_sig:
                self.risk_manager.add_position(
                    mint,
                    token_data['price_usd'],
                    position_size,
                    (position_size / token_data['price_usd']) if token_data['price_usd'] > 0 else 0
                )
                self.monitor.log_trade_open(mint, position_size, token_data['price_usd'], confidence)
                self._traded_mints.add(mint)
                logger.info(f"✅ BUY EXECUTED: {symbol} | tx={tx_sig[:16]}...")

                # Send Telegram alert
                if self.telegram:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.telegram.send_alert(
                            "🟢 Trade Opened",
                            f"Token: {symbol}\nAmount: {position_size:.4f} SOL\nPrice: ${token_data['price_usd']:.8f}\nConfidence: {confidence:.1f}%",
                            "trade_open"
                        ))
                        loop.close()
                    except Exception:
                        pass

                return tx_sig
            return None

        except Exception as e:
            logger.error(f"Error executing buy: {e}")
            return None

    def check_open_positions(self):
        """Check open positions for TP/SL"""
        try:
            for mint, position in list(self.risk_manager.positions.items()):
                if position['status'] != 'open':
                    continue

                token_data = self.dex_screener.search_token(mint)
                if not token_data:
                    logger.debug(f"Could not fetch price for {mint[:8]}...")
                    continue

                current_price = token_data['price_usd']
                self.risk_manager.update_position(mint, current_price)
                position = self.risk_manager.positions[mint]

                if self.risk_manager.check_stop_loss(mint):
                    self._execute_sell(mint, current_price, "Stop Loss", position['pnl_percent'])
                    continue

                tp_hit, tp_level = self.risk_manager.check_take_profit(mint)
                if tp_hit:
                    self._execute_sell(mint, current_price, f"Take Profit {tp_level}", position['pnl_percent'])

        except Exception as e:
            logger.error(f"Error checking positions: {e}")

    def _execute_sell(self, mint: str, current_price: float, reason: str, pnl_percent: float):
        """Execute sell order"""
        try:
            position = self.risk_manager.positions.get(mint)
            if not position:
                return

            if PAPER_TRADING:
                logger.info(f"📝 PAPER SELL: {mint[:8]}... | reason={reason} | pnl={pnl_percent:.2f}%")
            else:
                tx_sig = self.pump_fun.sell_token(mint, position['position_size_tokens'])
                if not tx_sig:
                    logger.error("Sell failed on pump.fun")
                    return

            self.risk_manager.close_position(mint, current_price, reason)
            self.monitor.log_trade_close(mint, current_price, pnl_percent, reason)

            logger.info(f"✅ SELL EXECUTED: {reason} | pnl={pnl_percent:.2f}%")

            if self.telegram:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.telegram.send_alert(
                        "🔴 Trade Closed" if pnl_percent < 0 else "✅ Trade Closed",
                        f"Token: {mint[:8]}...\nReason: {reason}\nPnL: {pnl_percent:+.2f}%",
                        "trade_close"
                    ))
                    loop.close()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error executing sell: {e}")

    def print_status(self):
        """Print bot status"""
        try:
            summary = self.risk_manager.get_portfolio_summary()
            perf = self.monitor.get_performance_summary()
            real_balance = self.wallet.get_balance()
            balance_str = f"{real_balance:.4f} SOL" if real_balance else "N/A"

            logger.info("=" * 60)
            logger.info("📊 BOT STATUS")
            logger.info("=" * 60)
            logger.info(f"Uptime:          {datetime.now() - self.start_time}")
            logger.info(f"Wallet Balance:  {balance_str}")
            logger.info(f"Open Positions:  {summary['open_positions']}")
            logger.info(f"Total Trades:    {perf['total_trades']}")
            logger.info(f"Win Rate:        {perf['win_rate']}")
            logger.info(f"Tokens Scanned:  {len(self._traded_mints)} traded this session")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"Error printing status: {e}")

    def _check_hard_stop(self) -> bool:
        """
        Hard stop — halt all trading if total SOL losses hit MAX_TOTAL_LOSS_SOL.
        Returns True if the bot should stop immediately.
        """
        try:
            from config import MAX_TOTAL_LOSS_SOL
            current_balance = self.wallet.get_balance()
            if current_balance is None:
                return False
            initial = getattr(self.wallet, 'initial_balance', None)
            if not initial:
                return False
            loss_sol = initial - current_balance
            if loss_sol >= MAX_TOTAL_LOSS_SOL:
                logger.critical(
                    f"🚨 HARD STOP: Lost {loss_sol:.4f} SOL "
                    f"(limit = {MAX_TOTAL_LOSS_SOL} SOL). Halting bot."
                )
                self.trading_active = False
                if self.telegram:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.telegram.send_alert(
                            "🚨 HARD STOP — Bot Halted",
                            f"Total loss reached {loss_sol:.4f} SOL\n"
                            f"Limit: {MAX_TOTAL_LOSS_SOL} SOL\n"
                            f"All trading stopped. Check your wallet immediately.",
                            "error"
                        ))
                        loop.close()
                    except Exception:
                        pass
                return True
        except Exception as e:
            logger.error(f"Hard stop check error: {e}")
        return False

    def run(self):
        """Main bot loop"""
        logger.info("🚀 Bot starting main loop...")
        if not PAPER_TRADING:
            logger.critical("🚨 LIVE TRADING ACTIVE — Real SOL will be spent")
            logger.critical(f"🚨 Max loss cap: {getattr(__import__('config'), 'MAX_TOTAL_LOSS_SOL', 0.4)} SOL")
        scan_counter = 0

        try:
            while self.trading_active:
                try:
                    # Hard SOL loss cap — checked every cycle in live mode
                    if not PAPER_TRADING and self._check_hard_stop():
                        break

                    # Scan every 6 cycles (~3 min at 30s interval)
                    if scan_counter % 6 == 0:
                        tokens = self.scan_new_tokens()
                        logger.info(f"Processing {min(len(tokens), 10)} tokens for analysis...")

                        for token in tokens[:10]:
                            if not self.trading_active:
                                break
                            result = self.analyze_token(token)
                            if result and result.get('should_buy'):
                                self.execute_buy(token, result)

                    self.check_open_positions()

                    if scan_counter % 10 == 0:
                        self.print_status()

                    scan_counter += 1
                    time.sleep(UPDATE_INTERVAL_SECONDS)

                except Exception as e:
                    logger.error(f"Main loop error: {e}")
                    time.sleep(UPDATE_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logger.info("⏹️ Bot shutting down...")
            self.trading_active = False


if __name__ == "__main__":
    bot = SolanaMemeCoinTradingBot()
    bot.run()
