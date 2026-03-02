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
            if data and data.get('pairs'):
                return self._parse_token_data(data['pairs'][0])
            return None
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout searching token {token_address}")
            return None
        except Exception as e:
            logger.error(f"Error searching token {token_address}: {e}")
            return None
    
    def get_latest_tokens(self, limit: int = 20) -> List[Dict]:
        """Get latest tokens on Solana - with multiple fallback methods"""
        tokens = []
        
        # Method 1: Try the /latest endpoint (most reliable)
        logger.info("🔍 Attempting to fetch tokens from DexScreener...")
        tokens = self._try_latest_endpoint(limit)
        if tokens:
            return tokens
        
        # Method 2: Try searching by Raydium pairs (fallback)
        logger.warning("⚠️ /latest endpoint failed, trying Raydium pairs...")
        tokens = self._try_raydium_pairs(limit)
        if tokens:
            return tokens
        
        # Method 3: Try searching trending tokens (last resort)
        logger.warning("⚠️ Raydium failed, trying trending tokens...")
        tokens = self._try_trending_tokens(limit)
        if tokens:
            return tokens
        
        logger.error("❌ All methods failed to fetch tokens")
        return []
    
    def _try_latest_endpoint(self, limit: int) -> List[Dict]:
        """Try the /latest endpoint"""
        try:
            url = f"{self.api_url}/tokens/solana/latest"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if data is None or not isinstance(data, dict):
                return []
            
            pairs = data.get('pairs', [])
            if not pairs:
                return []
            
            for pair in pairs[:limit]:
                if pair is None:
                    continue
                token = self._parse_token_data(pair)
                if token:
                    tokens.append(token)
            
            if tokens:
                logger.info(f"✅ Fetched {len(tokens)} tokens from /latest endpoint")
            return tokens
            
        except requests.exceptions.Timeout:
            logger.warning("⚠️ /latest endpoint timeout")
            return []
        except requests.exceptions.ConnectionError:
            logger.warning("⚠️ /latest endpoint connection error")
            return []
        except requests.exceptions.HTTPError as e:
            logger.warning(f"⚠️ HTTP Error from /latest: {e.response.status_code}")
            return []
        except Exception as e:
            logger.warning(f"⚠️ Error with /latest endpoint: {e}")
            return []
    
    def _try_raydium_pairs(self, limit: int) -> List[Dict]:
        """Try fetching Raydium pairs"""
        try:
            # Query for Raydium DEX pairs
            url = f"{self.api_url}/dexes/solana/raydium"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if data is None or not isinstance(data, dict):
                return []
            
            pairs = data.get('pairs', [])
            if not pairs:
                return []
            
            for pair in pairs[:limit]:
                if pair is None:
                    continue
                token = self._parse_token_data(pair)
                if token:
                    tokens.append(token)
            
            if tokens:
                logger.info(f"✅ Fetched {len(tokens)} tokens from Raydium")
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ Error with Raydium endpoint: {e}")
            return []
    
    def _try_trending_tokens(self, limit: int) -> List[Dict]:
        """Try fetching trending tokens"""
        try:
            # Query for trending tokens
            url = f"{self.api_url}/tokens/solana/trending"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if data is None or not isinstance(data, dict):
                return []
            
            pairs = data.get('pairs', [])
            if not pairs:
                return []
            
            for pair in pairs[:limit]:
                if pair is None:
                    continue
                token = self._parse_token_data(pair)
                if token:
                    tokens.append(token)
            
            if tokens:
                logger.info(f"✅ Fetched {len(tokens)} tokens from trending")
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ Error with trending endpoint: {e}")
            return []
    
    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """Get OHLCV candle data"""
        try:
            url = f"{self.api_url}/tokens/solana/{token_address}/candlesticks?timeframe={timeframe}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            candles = []
            
            if data is None or not isinstance(data, dict):
                logger.warning(f"Invalid OHLCV response for {token_address}")
                return []
            
            for candle in data.get('candles', []):
                if candle is None:
                    continue
                try:
                    candles.append({
                        'timestamp': candle.get('timestamp'),
                        'open': float(candle.get('open', 0)),
                        'high': float(candle.get('high', 0)),
                        'low': float(candle.get('low', 0)),
                        'close': float(candle.get('close', 0)),
                        'volume': float(candle.get('volume', 0))
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing candle data: {e}")
                    continue
            
            return candles
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching OHLCV for {token_address}")
            return []
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {token_address}: {e}")
            return []
    
    def _parse_token_data(self, pair_data: Dict) -> Optional[Dict]:
        """Parse token data from DexScreener response"""
        try:
            if pair_data is None or not isinstance(pair_data, dict):
                logger.warning("Invalid pair_data received")
                return None
            
            base_token = pair_data.get('baseToken', {})
            
            # Safe extraction with defaults
            liquidity = float(pair_data.get('liquidity', {}).get('usd', 0)) if pair_data.get('liquidity') else 0
            market_cap = float(pair_data.get('marketCap', 0)) if pair_data.get('marketCap') else 0
            
            if liquidity < MIN_LIQUIDITY_USD:
                return None
            if market_cap > MAX_MARKET_CAP_USD:
                return None
            
            price_usd = float(pair_data.get('priceUsd', 0)) if pair_data.get('priceUsd') else 0
            price_change_24h = float(pair_data.get('priceChange', {}).get('h24', 0)) if pair_data.get('priceChange') else 0
            volume_24h = float(pair_data.get('volume', {}).get('h24', 0)) if pair_data.get('volume') else 0
            
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
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"Error parsing token data: {e}")
            return None
    
    def filter_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Filter tokens by trading criteria"""
        filtered = []
        
        for token in tokens:
            if token is None:
                continue
            if token.get('market_cap_usd', 0) > MAX_MARKET_CAP_USD:
                continue
            if token.get('liquidity_usd', 0) < MIN_LIQUIDITY_USD:
                continue
            if token.get('volume_24h_usd', 0) < MIN_VOLUME_24H_USD:
                continue
            
            filtered.append(token)
        
        return filtered
