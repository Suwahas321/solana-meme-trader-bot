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
        self.polling_task = None
        self.loop = None
        
        logger.info("✅ Telegram bot initialized")
    
    def _setup_handlers(self):
        """Setup command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        self.application.add_handler(CommandHandler("pause", self.cmd_pause))
        self.application.add_handler(CommandHandler("resume", self.cmd_resume))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command"""
        try:
            user = update.effective_user
            message = f"""
🤖 **Solana Meme Coin Trading Bot**

👋 Welcome {user.first_name}!

**Commands:**
• `/status` - Bot status
• `/positions` - Open positions
• `/stats` - Trading stats
• `/pause` - Pause trading
• `/resume` - Resume trading
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error in cmd_start: {e}")
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bot status"""
        try:
            if hasattr(self.trading_bot, 'risk_manager') and self.trading_bot.risk_manager:
                summary = self.trading_bot.risk_manager.get_portfolio_summary()
            else:
                summary = {
                    'open_positions': 0,
                    'total_trades': 0,
                    'win_rate': 0
                }
            
            wallet_address = "Not initialized"
            if hasattr(self.trading_bot, 'wallet') and self.trading_bot.wallet:
                try:
                    wallet_address = self.trading_bot.wallet.get_address()[:8] + "..."
                except:
                    wallet_address = "Error getting address"
            
            trading_status = '🟢 ACTIVE' if getattr(self.trading_bot, 'trading_active', False) else '🔴 PAUSED'
            
            status_text = f"""
🤖 **BOT STATUS**

**Trading:** {trading_status}
**Wallet:** `{wallet_address}`

**Portfolio:**
• Open Trades: {summary.get('open_positions', 0)}
• Total Trades: {summary.get('total_trades', 0)}
• Win Rate: {summary.get('win_rate', 0)}%
**⏱️ Uptime:** {self._get_uptime()}
"""
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in cmd_status: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show open positions"""
        try:
            if not hasattr(self.trading_bot, 'risk_manager') or not self.trading_bot.risk_manager:
                await update.message.reply_text("✅ Risk manager not initialized")
                return
            
            positions = getattr(self.trading_bot.risk_manager, 'positions', {})
            open_positions = [p for p in positions.values() 
                            if p.get('status') == 'open']
            
            if not open_positions:
                await update.message.reply_text("✅ No open positions")
                return
            
            text = f"📈 **OPEN POSITIONS ({len(open_positions)})**\n\n"
            
            for i, pos in enumerate(open_positions, 1):
                pnl_percent = pos.get('pnl_percent', 0)
                pnl_emoji = "🟢" if pnl_percent > 0 else "🔴"
                mint = pos.get('mint', 'Unknown')[:8]
                text += f"{i}. {mint}... - {pnl_emoji} {pnl_percent:.2f}%\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in cmd_positions: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show statistics"""
        try:
            if hasattr(self.trading_bot, 'monitor') and self.trading_bot.monitor:
                perf = self.trading_bot.monitor.get_performance_summary()
            else:
                perf = {
                    'total_trades': 0,
                    'win_rate': 0,
                    'winning_trades': 0,
                    'losing_trades': 0
                }
            
            stats_text = f"""
📊 **TRADING STATS**

• Total Trades: {perf.get('total_trades', 0)}
• Win Rate: {perf.get('win_rate', 0)}%
• Wins: {perf.get('winning_trades', 0)}
• Losses: {perf.get('losing_trades', 0)}
"""
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in cmd_stats: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Pause trading"""
        try:
            self.trading_bot.trading_active = False
            await update.message.reply_text("⏸️ Trading paused")
            logger.warning("Trading paused by user via Telegram")
        except Exception as e:
            logger.error(f"Error in cmd_pause: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Resume trading"""
        try:
            self.trading_bot.trading_active = True
            await update.message.reply_text("▶️ Trading resumed")
            logger.info("Trading resumed by user via Telegram")
        except Exception as e:
            logger.error(f"Error in cmd_resume: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
    
    async def send_alert(self, title: str, message: str, alert_type: str = "info"):
        """Send alert to Telegram"""
        try:
            emoji_map = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
                "trade_open": "🟢",
                "trade_close": "🔴"
            }
            
            emoji = emoji_map.get(alert_type, "📢")
            full_message = f"{emoji} **{title}**\n\n{message}"
            
            if self.chat_id:
                await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=full_message,
                    parse_mode='Markdown'
                )
                logger.info(f"Alert sent: {title}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def _start_polling_async(self):
        """Start polling in async context"""
        try:
            logger.info("Starting Telegram bot polling...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=["message", "callback_query"])
            logger.info("✅ Telegram bot polling started")
        except Exception as e:
            logger.error(f"Error in async polling: {e}")
    
    def start_polling(self):
        """Start Telegram bot polling in separate thread"""
        def run_bot():
            try:
                # Create new event loop for this thread
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                logger.info("Starting Telegram bot polling in thread...")
                self.loop.run_until_complete(self._start_polling_async())
                
                # Keep the loop running
                self.loop.run_forever()
                
            except Exception as e:
                logger.error(f"Telegram polling thread error: {e}")
            finally:
                if self.loop:
                    self.loop.close()
        
        # Start polling in separate thread
        polling_thread = Thread(target=run_bot, daemon=True, name="TelegramBot")
        polling_thread.start()
        logger.info("✅ Telegram bot thread started")
    
    async def stop_polling(self):
        """Stop Telegram bot polling"""
        try:
            logger.info("Stopping Telegram bot...")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            logger.info("✅ Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    def _get_uptime(self) -> str:
        """Get bot uptime"""
        try:
            if hasattr(self.trading_bot, 'start_time'):
                uptime_seconds = (datetime.now() - self.trading_bot.start_time).total_seconds()
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                seconds = int(uptime_seconds % 60)
                return f"{hours}h {minutes}m {seconds}s"
            return "N/A"
        except:
            return "N/A"
