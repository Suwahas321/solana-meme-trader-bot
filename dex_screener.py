"""
DexScreener API Integration - Enhanced Version
Fetch token data, price, liquidity, and market cap
With fallback endpoints and better error handling
"""

import requests
import logging
from typing import Dict, Optional, List
from config import *
from datetime import datetime
import time

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class DexScreenerClient:
    """DexScreener API client for Solana token data"""
    
    def __init__(self):
        self.api_url = DEXSCREENER_API
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'solana-meme-trader-bot/1.0',
            'Accept': 'application/json'
        })
        self.last_request_time = 0
        self.min_request_interval = 0.5  # Minimum 0.5 seconds between requests
    
    def _rate_limit(self):
        """Simple rate limiting to avoid hitting API limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def search_token(self, token_address: str) -> Optional[Dict]:
        """Search for token on Solana"""
        try:
            self._rate_limit()
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
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error searching token {token_address}")
            return None
        except Exception as e:
            logger.error(f"Error searching token {token_address}: {e}")
            return None
    
    def get_latest_tokens(self, limit: int = 20) -> List[Dict]:
        """Get latest tokens on Solana - using correct endpoint"""
        try:
            self._rate_limit()
            
            # DexScreener endpoint for latest tokens
            url = f"{self.api_url}/tokens/solana/latest"
            
            logger.info(f"Fetching latest tokens from: {url}")
            
            response = self.session.get(url, timeout=15)  # Increased timeout
            
            # Log response status
            logger.info(f"DexScreener response status: {response.status_code}")
            
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            # Handle response structure properly
            if data is None:
                logger.warning("DexScreener returned None response")
                return []
            
            if not isinstance(data, dict):
                logger.warning(f"Unexpected response type: {type(data)}")
                logger.warning(f"Response data: {data}")
                return []
            
            pairs = data.get('pairs', [])
            
            if not pairs:
                logger.warning("No pairs found in DexScreener response")
                logger.warning(f"Response keys: {data.keys()}")
                return []
            
            logger.info(f"DexScreener returned {len(pairs)} pairs")
            
            for i, pair in enumerate(pairs[:limit]):
                if pair is None:
                    continue
                try:
                    token = self._parse_token_data(pair)
                    if token:
                        tokens.append(token)
                except Exception as e:
                    logger.debug(f"Error parsing pair {i}: {e}")
                    continue
            
            logger.info(f"✅ Fetched and parsed {len(tokens)} tokens from DexScreener")
            return tokens
            
        except requests.exceptions.Timeout:
            logger.error("DexScreener API timeout - request took too long (>15 seconds)")
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"DexScreener API connection error: {e}")
            return []
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error from DexScreener: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text[:200]}")
            return []
        except Exception as e:
            logger.error(f"Error fetching latest tokens: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """Get OHLCV candle data"""
        try:
            self._rate_limit()
            
            url = f"{self.api_url}/tokens/solana/{token_address}/candlesticks?timeframe={timeframe}"
            response = self.session.get(url, timeout=15)
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
            liquidity_obj = pair_data.get('liquidity', {})
            if isinstance(liquidity_obj, dict):
                liquidity = float(liquidity_obj.get('usd', 0))
            else:
                liquidity = 0
            
            market_cap = float(pair_data.get('marketCap', 0)) if pair_data.get('marketCap') else 0
            
            if liquidity < MIN_LIQUIDITY_USD:
                return None
            if market_cap > MAX_MARKET_CAP_USD:
                return None
            
            price_usd = float(pair_data.get('priceUsd', 0)) if pair_data.get('priceUsd') else 0
            
            price_change_obj = pair_data.get('priceChange', {})
            if isinstance(price_change_obj, dict):
                price_change_24h = float(price_change_obj.get('h24', 0))
            else:
                price_change_24h = 0
            
            volume_obj = pair_data.get('volume', {})
            if isinstance(volume_obj, dict):
                volume_24h = float(volume_obj.get('h24', 0))
            else:
                volume_24h = 0
            
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
