import requests
import logging
from config import HELIUS_API_KEY

logger = logging.getLogger(__name__)

class HeliosClient:
    """Helius API client for Solana wallet data"""
    
    def __init__(self):
        self.api_key = HELIUS_API_KEY
        self.base_url = "https://api.helius.xyz/v0"
    
    def get_balance(self, wallet_address):
        """Get wallet balance (SOL)"""
        try:
            url = f"https://api.mainnet-beta.solana.com"
            
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [wallet_address]
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            balance_lamports = data.get('result', {}).get('value', 0)
            balance_sol = balance_lamports / 1e9
            
            logger.info(f"✅ Helius SOL Balance: {balance_sol} SOL")
            return balance_sol
            
        except Exception as e:
            logger.error(f"❌ Helius error fetching balance: {e}")
            return None
    
    def get_token_holders(self, token_mint):
        """Get token holder information"""
        try:
            url = f"{self.base_url}/token/metadata"
            params = {
                "token": token_mint,
                "api-key": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            logger.error(f"❌ Helius error fetching token info: {e}")
            return None
    
    def get_token_holders_count(self, token_mint):
        """Get number of token holders"""
        try:
            token_info = self.get_token_holders(token_mint)
            if token_info:
                holders = token_info.get('holder_count', 0)
                logger.info(f"✅ Helius - Token {token_mint} has {holders} holders")
                return holders
            return 0
            
        except Exception as e:
            logger.error(f"❌ Helius error fetching holder count: {e}")
            return 0
