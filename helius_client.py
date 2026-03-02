"""
Helius API Integration
On-chain data, token metadata, holder info
"""

import requests
import logging
from typing import Dict, Optional, List
from config import *

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class HeliusClient:
    """Helius RPC client for advanced Solana data"""
    
    def __init__(self):
        self.api_key = HELIUS_API_KEY
        self.rpc_url = f"{HELIUS_MAINNET_URL}/?api-key={HELIUS_API_KEY}"
        self.session = requests.Session()
    
    def get_token_metadata(self, token_address: str) -> Optional[Dict]:
        """Get comprehensive token metadata"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getAsset",
                "params": {"id": token_address}
            }
            
            response = self.session.post(self.rpc_url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'result' in data:
                return data['result']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting token metadata: {e}")
            return None
    
    def get_token_holders(self, token_address: str, limit: int = 100) -> List[Dict]:
        """Get top token holders"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenHolders",
                "params": {"tokenAddress": token_address, "limit": limit}
            }
            
            response = self.session.post(self.rpc_url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('result', [])
            
        except Exception as e:
            logger.error(f"Error getting token holders: {e}")
            return []
    
    def check_holder_concentration(self, token_address: str) -> Optional[float]:
        """Check if top holder has too much concentration"""
        try:
            holders = self.get_token_holders(token_address, limit=10)
            
            if not holders:
                return None
            
            total_supply = float(holders[0].get('supply', 0))
            top_holder_amount = float(holders[0].get('amount', 0))
            
            if total_supply > 0:
                concentration = (top_holder_amount / total_supply) * 100
                return concentration
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking holder concentration: {e}")
            return None
