"""
DexScreener API Integration
Fetch token data, price, liquidity, and market cap
"""

import requests
import logging
from typing import Dict, Optional, List
from config import *
from datetime import datetime

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class DexScreenerClient:
    """DexScreener API client for Solana token data"""
    
    def __init__(self):
        self.api_url = DEXSCREENER_API
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'solana-meme-trader-bot/1.0'})
    
    def search_token(self, token_address: str) -> Optional[Dict]:
        """Search for token on Solana"""
        try:
            url = f"{self.api_url}/tokens/solana/{token_address}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('pairs'):
                return self._parse_token_data(data['pairs'][0])
            return None
            
        except Exception as e:
            logger.error(f"Error searching token {token_address}: {e}")
            return None
    
    def get_latest_tokens(self, limit: int = 20) -> List[Dict]:
        """Get latest tokens on Solana"""
        try:
            url = f"{self.api_url}/tokens/solana?limit={limit}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            for pair in data.get('pairs', [])[:limit]:
                token = self._parse_token_data(pair)
                if token:
                    tokens.append(token)
            
            return tokens
            
        except Exception as e:
            logger.error(f"Error fetching latest tokens: {e}")
            return []
    
    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """Get OHLCV candle data"""
        try:
            url = f"{self.api_url}/tokens/solana/{token_address}/candlesticks?timeframe={timeframe}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            candles = []
            
            for candle in data.get('candles', []):
                candles.append({
                    'timestamp': candle.get('timestamp'),
                    'open': float(candle.get('open', 0)),
                    'high': float(candle.get('high', 0)),
                    'low': float(candle.get('low', 0)),
                    'close': float(candle.get('close', 0)),
                    'volume': float(candle.get('volume', 0))
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {token_address}: {e}")
            return []
    
    def _parse_token_data(self, pair_data: Dict) -> Optional[Dict]:
        """Parse token data from DexScreener response"""
        try:
            base_token = pair_data.get('baseToken', {})
            
            liquidity = float(pair_data.get('liquidity', {}).get('usd', 0))
            market_cap = float(pair_data.get('marketCap', 0))
            
            if liquidity < MIN_LIQUIDITY_USD:
                return None
            if market_cap > MAX_MARKET_CAP_USD:
                return None
            
            price_usd = float(pair_data.get('priceUsd', 0))
            price_change_24h = float(pair_data.get('priceChange', {}).get('h24', 0))
            volume_24h = float(pair_data.get('volume', {}).get('h24', 0))
            
            return {
                'mint_address': base_token.get('address'),
                'symbol': base_token.get('symbol'),
                'name': base_token.get('name'),
                'price_usd': price_usd,
                'price_change_24h': price_change_24h,
                'liquidity_usd': liquidity,
                'market_cap_usd': market_cap,
                'volume_24h_usd': volume_24h,
                'dex': pair_data.get('dexId'),
                'pair_address': pair_data.get('pairAddress'),
                'created_at': pair_data.get('pairCreatedAt'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing token data: {e}")
            return None
    
    def filter_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Filter tokens by trading criteria"""
        filtered = []
        
        for token in tokens:
            if token['market_cap_usd'] > MAX_MARKET_CAP_USD:
                continue
            if token['liquidity_usd'] < MIN_LIQUIDITY_USD:
                continue
            if token['volume_24h_usd'] < MIN_VOLUME_24H_USD:
                continue
            
            filtered.append(token)
        
        return filtered
