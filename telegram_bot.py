"""
Telegram Bot Integration
Real-time alerts, position monitoring, command execution
"""

import logging
import os
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

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
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show bot status"""
        try:
            summary = self.trading_bot.risk_manager.get_portfolio_summary()
            
            status_text = f"""
🤖 **BOT STATUS**

**Trading:** {'🟢 ACTIVE' if self.trading_bot.trading_active else '🔴 PAUSED'}
**Wallet:** `{self.trading_bot.wallet.get_address()[:8]}...`

**Portfolio:**
• Open Trades: {summary['open_positions']}
• Total Trades: {summary['total_trades']}
• Win Rate: {summary['win_rate']}
"""
            
            await update.message.reply_text(status_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show open positions"""
        try:
            open_positions = [p for p in self.trading_bot.risk_manager.positions.values() 
                            if p['status'] == 'open']
            
            if not open_positions:
                await update.message.reply_text("✅ No open positions")
                return
            
            text = f"📈 **OPEN POSITIONS ({len(open_positions)})**\n\n"
            
            for i, pos in enumerate(open_positions, 1):
                pnl_emoji = "🟢" if pos['pnl_percent'] > 0 else "🔴"
                text += f"{i}. {pos['mint'][:8]}... - {pnl_emoji} {pos['pnl_percent']:.2f}%\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show statistics"""
        try:
            perf = self.trading_bot.monitor.get_performance_summary()
            
            stats_text = f"""
📊 **STATS**

• Total Trades: {perf['total_trades']}
• Win Rate: {perf['win_rate']}
• Wins: {perf['winning_trades']}
• Losses: {perf['losing_trades']}
"""
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    async def cmd_pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Pause trading"""
        self.trading_bot.trading_active = False
        await update.message.reply_text("⏸️ Trading paused")
        logger.warning("Trading paused by user")
    
    async def cmd_resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Resume trading"""
        self.trading_bot.trading_active = True
        await update.message.reply_text("▶️ Trading resumed")
        logger.info("Trading resumed by user")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
    
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
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def start_polling(self):
        """Start Telegram bot polling"""
        logger.info("Starting Telegram bot polling...")
        self.application.run_polling()
