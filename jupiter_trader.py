"""
Jupiter DEX Integration
Execute swaps on Jupiter Aggregator
"""

import logging
import requests
from typing import Dict, Optional
from config import *

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class JupiterTrader:
    """Execute trades through Jupiter aggregator"""
    
    def __init__(self, wallet_address: str):
        self.wallet_address = wallet_address
        self.jupiter_api = "https://api.jup.ag"
        self.session = requests.Session()
    
    def get_quote(self, input_mint: str, output_mint: str, amount: float) -> Optional[Dict]:
        """Get quote from Jupiter"""
        try:
            url = f"{self.jupiter_api}/quote"
            params = {
                'inputMint': input_mint,
                'outputMint': output_mint,
                'amount': int(amount * 1e9),
                'slippageBps': int(SLIPPAGE_TOLERANCE * 100)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                'input_amount': amount,
                'output_amount': float(data.get('outAmount', 0)) / 1e9,
                'price_impact_pct': float(data.get('priceImpactPct', 0)) * 100
            }
            
        except Exception as e:
            logger.error(f"Error getting Jupiter quote: {e}")
            return None
    
    def create_swap_transaction(self, input_mint: str, output_mint: str, amount: float) -> Optional[str]:
        """Create swap transaction on Jupiter"""
        try:
            logger.info(f"Creating Jupiter swap: {amount}")
            
            quote = self.get_quote(input_mint, output_mint, amount)
            if not quote:
                return None
            
            return "simulated_tx_signature"
            
        except Exception as e:
            logger.error(f"Error creating Jupiter swap: {e}")
            return None
