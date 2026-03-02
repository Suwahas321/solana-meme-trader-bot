"""
Pump.fun Integration
Execute trades on Pump.fun
"""

import logging
import requests
from typing import Dict, Optional
from config import *

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class PumpFunTrader:
    """Execute trades on Pump.fun"""
    
    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address
        self.pump_fun_api = "https://api.pump.fun"
        self.session = requests.Session()
    
    def get_token_info(self, mint: str) -> Optional[Dict]:
        """Get token info from Pump.fun"""
        try:
            url = f"{self.pump_fun_api}/tokens/{mint}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return {
                'mint': mint,
                'name': data.get('name'),
                'symbol': data.get('symbol'),
                'price': float(data.get('price', 0)),
                'market_cap': float(data.get('marketCap', 0)),
                'liquidity': float(data.get('liquidity', 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting pump.fun token info: {e}")
            return None
    
    def buy_token(self, mint: str, amount_sol: float) -> Optional[str]:
        """Buy token on Pump.fun"""
        try:
            logger.info(f"Buying {mint} on Pump.fun with {amount_sol} SOL")
            
            url = f"{self.pump_fun_api}/buy"
            payload = {
                'mint': mint,
                'amountSol': amount_sol,
                'slippage': SLIPPAGE_TOLERANCE,
                'buyer': self.wallet_address
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('signature')
            
        except Exception as e:
            logger.error(f"Error buying on Pump.fun: {e}")
            return None
    
    def sell_token(self, mint: str, amount_tokens: float) -> Optional[str]:
        """Sell token on Pump.fun"""
        try:
            logger.info(f"Selling {amount_tokens} tokens of {mint}")
            
            url = f"{self.pump_fun_api}/sell"
            payload = {
                'mint': mint,
                'amount': amount_tokens,
                'slippage': SLIPPAGE_TOLERANCE,
                'seller': self.wallet_address
            }
            
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('signature')
            
        except Exception as e:
            logger.error(f"Error selling on Pump.fun: {e}")
            return None
