import logging
import asyncio
from config import (
    WALLET_ADDRESS, 
    MORALIS_ENABLED, 
    HELIUS_ENABLED,
    LOG_LEVEL
)
from wallet_manager import WalletManager
from jupiter_trader import JupiterTrader
from raydium_trader import RaydiumTrader
from pump_fun_trader import PumpFunTrader
from risk_manager import RiskManager
from telegram_bot import TelegramBot

# Setup logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TradingBot:
    """Main trading bot with multiple API support"""
    
    def __init__(self):
        logger.info("🤖 Initializing Trading Bot...")
        
        # Check API availability
        if not (MORALIS_ENABLED or HELIUS_ENABLED):
            raise ValueError("❌ No API keys configured!")
        
        logger.info(f"📡 APIs: Moralis={MORALIS_ENABLED}, Helius={HELIUS_ENABLED}")
        
        # Initialize managers
        self.wallet_manager = WalletManager(WALLET_ADDRESS)
        self.jupiter_trader = JupiterTrader()
        self.raydium_trader = RaydiumTrader()
        self.pump_fun_trader = PumpFunTrader()
        self.risk_manager = RiskManager()
        self.telegram = TelegramBot()
        
        logger.info("✅ Trading Bot Initialized!")
    
    async def start(self):
        """Start the trading bot"""
        logger.info("🚀 Starting Trading Bot...")
        
        try:
            # Check wallet connection
            await self.check_wallet_status()
            
            # Start trading loop
            await self.trading_loop()
            
        except Exception as e:
            logger.error(f"❌ Bot error: {e}")
            await self.telegram.send_message(f"❌ Trading Bot Error: {e}")
    
    async def check_wallet_status(self):
        """Check wallet balance and connection"""
        try:
            logger.info("📊 Checking Wallet Status...")
            
            # Get balance using fallback mechanism
            balance = self.wallet_manager.get_sol_balance()
            portfolio_value = self.wallet_manager.get_portfolio_value()
            
            status_msg = f"""
            ✅ Wallet Connected!
            
            💾 Address: {WALLET_ADDRESS[:8]}...
            💰 SOL Balance: {balance:.4f}
            📈 Portfolio Value: ${portfolio_value:.2f}
            """
            
            logger.info(status_msg)
            await self.telegram.send_message(status_msg)
            
        except Exception as e:
            logger.error(f"❌ Wallet check failed: {e}")
            raise
    
    async def trading_loop(self):
        """Main trading loop"""
        logger.info("🔄 Starting Trading Loop...")
        
        while True:
            try:
                # Check wallet balance
                balance = self.wallet_manager.get_sol_balance()
                
                if balance is None or balance < 0.1:
                    logger.warning(f"⚠️ Insufficient balance: {balance} SOL")
                    await asyncio.sleep(60)
                    continue
                
                # Look for trading opportunities
                logger.info("🔍 Scanning for trading opportunities...")
                
                # Check Jupiter
                jupiter_trades = await self.jupiter_trader.find_opportunities()
                if jupiter_trades:
                    await self.handle_opportunity("Jupiter", jupiter_trades)
                
                # Check Raydium
                raydium_trades = await self.raydium_trader.find_opportunities()
                if raydium_trades:
                    await self.handle_opportunity("Raydium", raydium_trades)
                
                # Check Pump.fun
                pump_trades = await self.pump_fun_trader.find_opportunities()
                if pump_trades:
                    await self.handle_opportunity("Pump.fun", pump_trades)
                
                # Wait before next scan
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Trading loop error: {e}")
                await asyncio.sleep(60)
    
    async def handle_opportunity(self, dex_name, trades):
        """Handle a trading opportunity"""
        try:
            logger.info(f"🎯 Opportunity found on {dex_name}")
            
            for trade in trades:
                # Check risk
                risk_ok = await self.risk_manager.check_risk(trade)
                
                if not risk_ok:
                    logger.warning(f"⚠️ Trade rejected by risk manager: {trade}")
                    continue
                
                # Execute trade
                logger.info(f"📍 Executing trade on {dex_name}")
                
                if dex_name == "Jupiter":
                    tx = await self.jupiter_trader.execute_trade(trade)
                elif dex_name == "Raydium":
                    tx = await self.raydium_trader.execute_trade(trade)
                else:
                    tx = await self.pump_fun_trader.execute_trade(trade)
                
                if tx:
                    msg = f"✅ Trade executed on {dex_name}\nTX: {tx[:16]}..."
                    await self.telegram.send_message(msg)
                    logger.info(msg)
        
        except Exception as e:
            logger.error(f"❌ Error handling {dex_name} opportunity: {e}")

async def main():
    """Main entry point"""
    try:
        bot = TradingBot()
        await bot.start()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
