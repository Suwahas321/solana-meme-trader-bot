import requests
import logging
from config import MORALIS_API_KEY

logger = logging.getLogger(__name__)

class MoralisClient:
    """Moralis API client for Solana wallet data"""
    
    def __init__(self):
        self.api_key = MORALIS_API_KEY
        self.base_url = "https://solana-gateway.moralis.io/account"
        self.headers = {"X-API-Key": self.api_key}
    
    def get_sol_balance(self, wallet_address):
        """Get native SOL balance"""
        try:
            url = f"{self.base_url}/balance"
            params = {
                "network": "mainnet",
                "address": wallet_address
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            balance_lamports = data.get('lamports', 0)
            balance_sol = balance_lamports / 1e9
            
            logger.info(f"✅ Moralis SOL Balance: {balance_sol} SOL")
            return balance_sol
            
        except Exception as e:
            logger.error(f"❌ Moralis error fetching SOL balance: {e}")
            return None
    
    def get_spl_tokens(self, wallet_address):
        """Get all SPL token balances"""
        try:
            url = f"{self.base_url}/tokens"
            params = {
                "network": "mainnet",
                "address": wallet_address
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            tokens = response.json()
            logger.info(f"✅ Moralis found {len(tokens)} SPL tokens")
            return tokens
            
        except Exception as e:
            logger.error(f"❌ Moralis error fetching SPL tokens: {e}")
            return []
    
    def get_portfolio(self, wallet_address):
        """Get complete portfolio (SOL + tokens)"""
        try:
            sol_balance = self.get_sol_balance(wallet_address)
            spl_tokens = self.get_spl_tokens(wallet_address)
            
            portfolio = {
                "sol_balance": sol_balance,
                "tokens": spl_tokens,
                "source": "moralis"
            }
            
            return portfolio
            
        except Exception as e:
            logger.error(f"❌ Moralis error fetching portfolio: {e}")
            return None
    
    def get_token_price(self, token_mint):
        """Get token price from Moralis"""
        try:
            url = f"https://solana-gateway.moralis.io/token/{token_mint}/price"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            price = data.get('usdPrice', 0)
            
            return price
            
        except Exception as e:
            logger.error(f"❌ Moralis error fetching token price: {e}")
            return 0
