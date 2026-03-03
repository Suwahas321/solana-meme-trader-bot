"""
Telegram Bot Integration
Real-time alerts, position monitoring, command execution
"""

import logging
import os
import asyncio
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv
from threading import Thread

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class TelegramBotHandler:
    """Handle Telegram bot interactions"""

    def __init__(self, trading_bot):
        self.trading_bot = trading_bot
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env")

        self.application = Application.builder().token(self.telegram_token).build()
        self._setup_handlers()
        self.loop = None
        logger.info("✅ Telegram bot initialized")

    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("pause", self.cmd_pause))
        self.application.add_handler(CommandHandler("resume", self.cmd_resume))
        self.application.add_handler(CommandHandler("balance", self.cmd_balance))
        self.application.add_handler(CommandHandler("wallet", self.cmd_wallet))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

    # ------------------------------------------------------------------ helpers
    def _get_real_balance(self) -> Optional[float]:
        """Fetch real wallet balance from WalletManager"""
        try:
            if hasattr(self.trading_bot, 'wallet') and self.trading_bot.wallet:
                return self.trading_bot.wallet.get_balance()
        except Exception as e:
            logger.debug(f"Balance fetch error: {e}")
        return None

    def _get_wallet_address(self) -> str:
        try:
            if hasattr(self.trading_bot, 'wallet') and self.trading_bot.wallet:
                addr = self.trading_bot.wallet.get_address()
                if addr:
                    return addr
        except Exception:
            pass
        return "Not initialized"

    def _get_uptime(self) -> str:
        try:
            if hasattr(self.trading_bot, 'start_time'):
                uptime_seconds = (datetime.now() - self.trading_bot.start_time).total_seconds()
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                seconds = int(uptime_seconds % 60)
                return f"{hours}h {minutes}m {seconds}s"
        except Exception:
            pass
        return "N/A"

    # ------------------------------------------------------------------ commands
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        message = (
            f"🤖 *Solana Meme Coin Trading Bot*\n\n"
            f"👋 Welcome {user.first_name}\\!\n\n"
            f"*Commands:*\n"
            f"• `/status` \\- Bot status\n"
            f"• `/balance` \\- Live wallet balance\n"
            f"• `/wallet` \\- Wallet address\n"
            f"• `/positions` \\- Open positions\n"
            f"• `/stats` \\- Trading statistics\n"
            f"• `/pause` \\- Pause trading\n"
            f"• `/resume` \\- Resume trading"
        )
        await update.message.reply_text(message, parse_mode='MarkdownV2')

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            summary = {'open_positions': 0, 'total_trades': 0, 'win_rate': '0%'}
            if hasattr(self.trading_bot, 'risk_manager') and self.trading_bot.risk_manager:
                summary = self.trading_bot.risk_manager.get_portfolio_summary()

            addr = self._get_wallet_address()
            short_addr = addr[:8] + "..." + addr[-6:] if len(addr) > 14 else addr

            current_balance = self._get_real_balance()
            balance_str = f"{current_balance:.4f} SOL" if current_balance is not None else "Fetching..."

            trading_status = '🟢 ACTIVE' if getattr(self.trading_bot, 'trading_active', False) else '🔴 PAUSED'

            text = (
                f"🤖 *BOT STATUS*\n\n"
                f"*Trading:* {trading_status}\n"
                f"*Wallet:* `{short_addr}`\n"
                f"*Balance:* {balance_str}\n\n"
                f"*Portfolio:*\n"
                f"• Open Trades: {summary.get('open_positions', 0)}\n"
                f"• Total Trades: {summary.get('total_trades', 0)}\n"
                f"• Win Rate: {summary.get('win_rate', '0%')}\n\n"
                f"⏱ Uptime: {self._get_uptime()}"
            )
            await update.message.reply_text(text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"cmd_status error: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            current_balance = self._get_real_balance()

            if current_balance is None:
                await update.message.reply_text("⚠️ Could not fetch wallet balance. Check HELIUS_API_KEY.")
                return

            # Get initial balance from WalletManager
            initial_balance = None
            try:
                initial_balance = self.trading_bot.wallet.initial_balance
            except Exception:
                pass

            balance_change = 0.0
            change_pct = 0.0
            change_emoji = "⚪"

            if initial_balance and initial_balance > 0:
                balance_change = current_balance - initial_balance
                change_pct = (balance_change / initial_balance) * 100
                if balance_change > 0:
                    change_emoji = "🟢"
                elif balance_change < 0:
                    change_emoji = "🔴"

            profit_label = "✅ Profitable!" if balance_change > 0 else ("⚠️ At loss" if balance_change < 0 else "➡️ Breakeven")
            init_str = f"{initial_balance:.4f} SOL" if initial_balance else "N/A"

            text = (
                f"💰 *ACCOUNT BALANCE*\n\n"
                f"*Current Balance:* `{current_balance:.4f} SOL`\n"
                f"*Starting Balance:* `{init_str}`\n\n"
                f"{change_emoji} *Change:* `{balance_change:+.4f} SOL` ({change_pct:+.2f}%)\n\n"
                f"{profit_label}"
            )
            await update.message.reply_text(text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"cmd_balance error: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            addr = self._get_wallet_address()
            if addr == "Not initialized":
                await update.message.reply_text("⚠️ Wallet not initialized. Check WALLET_PRIVATE_KEY.")
                return

            text = (
                f"💳 *WALLET DETAILS*\n\n"
                f"*Full Address:*\n`{addr}`\n\n"
                f"*Network:* Solana Mainnet\n"
                f"*Status:* ✅ Connected\n\n"
                f"[View on Solscan](https://solscan.io/account/{addr})"
            )
            await update.message.reply_text(text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"cmd_wallet error: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            if not hasattr(self.trading_bot, 'risk_manager') or not self.trading_bot.risk_manager:
                await update.message.reply_text("⚠️ Risk manager not initialized")
                return

            positions = getattr(self.trading_bot.risk_manager, 'positions', {})
            open_positions = [p for p in positions.values() if p.get('status') == 'open']

            if not open_positions:
                await update.message.reply_text("✅ No open positions right now.")
                return

            text = f"📈 *OPEN POSITIONS ({len(open_positions)})*\n\n"
            for i, pos in enumerate(open_positions, 1):
                pnl_pct = pos.get('pnl_percent', 0)
                pnl_emoji = "🟢" if pnl_pct > 0 else "🔴"
                mint = pos.get('mint', 'Unknown')
                entry = pos.get('entry_price', 0)
                current = pos.get('current_price', 0)
                size = pos.get('position_size_sol', 0)
                text += (
                    f"{i}. `{mint[:10]}...`\n"
                    f"   Entry: ${entry:.8f} → Now: ${current:.8f}\n"
                    f"   Size: {size:.4f} SOL | {pnl_emoji} {pnl_pct:+.2f}%\n\n"
                )

            await update.message.reply_text(text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"cmd_positions error: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            perf = {'total_trades': 0, 'win_rate': '0%', 'winning_trades': 0, 'losing_trades': 0, 'avg_pnl': '0%'}
            if hasattr(self.trading_bot, 'monitor') and self.trading_bot.monitor:
                perf = self.trading_bot.monitor.get_performance_summary()

            summary = {}
            if hasattr(self.trading_bot, 'risk_manager') and self.trading_bot.risk_manager:
                summary = self.trading_bot.risk_manager.get_portfolio_summary()

            text = (
                f"📊 *TRADING STATS*\n\n"
                f"• Total Trades: {perf.get('total_trades', 0)}\n"
                f"• Wins: {perf.get('winning_trades', 0)}\n"
                f"• Losses: {perf.get('losing_trades', 0)}\n"
                f"• Win Rate: {perf.get('win_rate', '0%')}\n"
                f"• Avg PnL: {perf.get('avg_pnl', '0%')}\n\n"
                f"*Unrealized PnL:* {summary.get('unrealized_pnl_percent', 0):.2f}%\n"
                f"*Total Realized PnL:* {summary.get('total_pnl_sol', 0):.4f} SOL"
            )
            await update.message.reply_text(text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"cmd_stats error: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            self.trading_bot.trading_active = False
            await update.message.reply_text("⏸️ Trading paused.")
            logger.warning("Trading paused via Telegram")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            self.trading_bot.trading_active = True
            await update.message.reply_text("▶️ Trading resumed.")
            logger.info("Trading resumed via Telegram")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await update.callback_query.answer()
        except Exception as e:
            logger.error(f"button_callback error: {e}")

    # ------------------------------------------------------------------ alerts
    async def send_alert(self, title: str, message: str, alert_type: str = "info"):
        """Send proactive alert to Telegram chat"""
        try:
            emoji_map = {
                "info": "ℹ️", "success": "✅", "warning": "⚠️",
                "error": "❌", "trade_open": "🟢", "trade_close": "🔴"
            }
            emoji = emoji_map.get(alert_type, "📢")
            full_message = f"{emoji} *{title}*\n\n{message}"

            if self.chat_id:
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=full_message,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"send_alert error: {e}")

    # ------------------------------------------------------------------ polling
    async def _start_polling_async(self):
        try:
            logger.info("Starting Telegram polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=["message", "callback_query"])
            logger.info("✅ Telegram polling started")
        except Exception as e:
            logger.error(f"Polling start error: {e}")

    def start_polling(self):
        """Start Telegram bot in a daemon thread"""
        def run_bot():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.loop.run_until_complete(self._start_polling_async())
                self.loop.run_forever()
            except Exception as e:
                logger.error(f"Telegram thread error: {e}")
            finally:
                if self.loop:
                    self.loop.close()

        t = Thread(target=run_bot, daemon=True, name="TelegramBot")
        t.start()
        logger.info("✅ Telegram bot thread started")

    async def stop_polling(self):
        try:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        except Exception as e:
            logger.error(f"Stop polling error: {e}")
