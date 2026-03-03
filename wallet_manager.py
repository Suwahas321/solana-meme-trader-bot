import logging
from config import MORALIS_ENABLED, HELIUS_ENABLED
from moralis_client import MoralisClient
from helius_client import HeliosClient

logger = logging.getLogger(__name__)

class WalletManager:
    """Manages wallet data using multiple APIs with fallback"""
    
    def __init__(self, wallet_address):
        self.wallet_address = wallet_address
        
        if MORALIS_ENABLED:
            self.moralis = MoralisClient()
        else:
            self.moralis = None
            
        if HELIUS_ENABLED:
            self.helius = HeliosClient()
        else:
            self.helius = None
    
    def get_sol_balance(self):
        """Get SOL balance - try Moralis first, fallback to Helius"""
        
        # Try Moralis first (more reliable)
        if self.moralis:
            try:
                balance = self.moralis.get_sol_balance(self.wallet_address)
                if balance is not None:
                    logger.info(f"🟢 Using Moralis for SOL balance: {balance}")
                    return balance
            except Exception as e:
                logger.warning(f"⚠️ Moralis failed: {e}, trying Helius...")
        
        # Fallback to Helius
        if self.helius:
            try:
                balance = self.helius.get_balance(self.wallet_address)
                if balance is not None:
                    logger.info(f"🟢 Using Helius for SOL balance: {balance}")
                    return balance
            except Exception as e:
                logger.warning(f"⚠️ Helius also failed: {e}")
        
        logger.error(f"❌ Could not fetch SOL balance from any API")
        return 0
    
    def get_portfolio(self):
        """Get complete portfolio from best available API"""
        
        # Try Moralis first (better token data)
        if self.moralis:
            try:
                portfolio = self.moralis.get_portfolio(self.wallet_address)
                if portfolio:
                    logger.info(f"🟢 Using Moralis for portfolio")
                    return {
                        **portfolio,
                        "source": "moralis"
                    }
            except Exception as e:
                logger.warning(f"⚠️ Moralis portfolio failed: {e}")
        
        # Fallback to Helius
        if self.helius:
            try:
                sol_balance = self.helius.get_balance(self.wallet_address)
                logger.info(f"🟢 Using Helius for portfolio")
                return {
                    "sol_balance": sol_balance,
                    "tokens": [],
                    "source": "helius"
                }
            except Exception as e:
                logger.warning(f"⚠️ Helius portfolio failed: {e}")
        
        logger.error(f"❌ Could not fetch portfolio from any API")
        return {
            "sol_balance": 0,
            "tokens": [],
            "source": "none"
        }
    
    def get_portfolio_value(self):
        """Get total portfolio value in USD"""
        try:
            portfolio = self.get_portfolio()
            sol_balance = portfolio.get('sol_balance', 0)
            tokens = portfolio.get('tokens', [])
            
            # Get SOL price
            sol_price = self._get_sol_price()
            
            total_value = sol_balance * sol_price
            
            # Add token values
            for token in tokens:
                token_amount = float(token.get('balance', 0)) / (10 ** token.get('decimals', 9))
                token_price = self._get_token_price(token.get('mint'))
                total_value += token_amount * token_price
            
            logger.info(f"💰 Total Portfolio Value: ${total_value:.2f}")
            return total_value
            
        except Exception as e:
            logger.error(f"❌ Error calculating portfolio value: {e}")
            return 0
    
    def _get_sol_price(self):
        """Get current SOL price"""
        try:
            if self.moralis:
                # Use Moralis API to get SOL price
                url = "https://solana-gateway.moralis.io/token/So11111111111111111111111111111111111111112/price"
                headers = {"X-API-Key": self.moralis.api_key}
                
                import requests
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    price = response.json().get('usdPrice', 0)
                    logger.info(f"📊 SOL Price: ${price}")
                    return price
        except:
            pass
        
        # Default SOL price if API fails
        return 150  # Fallback price
    
    def _get_token_price(self, token_mint):
        """Get token price"""
        try:
            if self.moralis:
                price = self.moralis.get_token_price(token_mint)
                return price
        except:
            pass
        
        return 0
