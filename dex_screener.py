"""
DexScreener API Integration - Alternative Endpoints
Uses multiple fallback endpoints to get token data
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
    """DexScreener API client for Solana token data with multiple fallbacks"""
    
    def __init__(self):
        self.api_url = DEXSCREENER_API
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'solana-meme-trader-bot/1.0',
            'Accept': 'application/json'
        })
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
    
    def _rate_limit(self):
        """Rate limiting to avoid hitting API limits"""
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
            
        except Exception as e:
            logger.debug(f"Error searching token {token_address}: {e}")
            return None
    
    def get_latest_tokens(self, limit: int = 20) -> List[Dict]:
        """Get latest tokens - tries multiple endpoints"""
        tokens = []
        
        # Try endpoint 1: /latest (most common)
        tokens = self._try_latest_endpoint(limit)
        if tokens:
            logger.info(f"✅ Got {len(tokens)} tokens from /latest endpoint")
            return tokens
        
        # Try endpoint 2: /top boosts (trending)
        tokens = self._try_top_boosts_endpoint(limit)
        if tokens:
            logger.info(f"✅ Got {len(tokens)} tokens from /top boosts endpoint")
            return tokens
        
        # Try endpoint 3: Search Solana pairs
        tokens = self._try_solana_pairs_endpoint(limit)
        if tokens:
            logger.info(f"✅ Got {len(tokens)} tokens from /solana/pairs endpoint")
            return tokens
        
        # Try endpoint 4: Manual token list (hardcoded popular ones)
        tokens = self._try_manual_popular_tokens()
        if tokens:
            logger.info(f"✅ Got {len(tokens)} tokens from manual list")
            return tokens
        
        logger.error("❌ All DexScreener endpoints failed")
        return []
    
    def _try_latest_endpoint(self, limit: int) -> List[Dict]:
        """Try the /latest endpoint"""
        try:
            self._rate_limit()
            url = f"{self.api_url}/tokens/solana/latest"
            logger.info(f"Trying /latest endpoint: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if not data or not isinstance(data, dict):
                return []
            
            pairs = data.get('pairs', [])
            if not pairs:
                return []
            
            for pair in pairs[:limit]:
                if pair:
                    token = self._parse_token_data(pair)
                    if token:
                        tokens.append(token)
            
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ /latest endpoint failed: {e}")
            return []
    
    def _try_top_boosts_endpoint(self, limit: int) -> List[Dict]:
        """Try the /top boosts endpoint"""
        try:
            self._rate_limit()
            url = f"{self.api_url}/tokens/solana/top/boosts"
            logger.info(f"Trying /top boosts endpoint: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if not data or not isinstance(data, dict):
                return []
            
            pairs = data.get('pairs', [])
            if not pairs:
                return []
            
            for pair in pairs[:limit]:
                if pair:
                    token = self._parse_token_data(pair)
                    if token:
                        tokens.append(token)
            
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ /top boosts endpoint failed: {e}")
            return []
    
    def _try_solana_pairs_endpoint(self, limit: int) -> List[Dict]:
        """Try the /solana/pairs endpoint"""
        try:
            self._rate_limit()
            url = f"{self.api_url}/dex/pairs/solana/latest"
            logger.info(f"Trying /dex/pairs endpoint: {url}")
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if not data or not isinstance(data, dict):
                return []
            
            pairs = data.get('pairs', [])
            if not pairs:
                return []
            
            for pair in pairs[:limit]:
                if pair:
                    token = self._parse_token_data(pair)
                    if token:
                        tokens.append(token)
            
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ /dex/pairs endpoint failed: {e}")
            return []
    
    def _try_manual_popular_tokens(self) -> List[Dict]:
        """Fallback: Return manual list of popular tokens"""
        try:
            logger.info("Using manual popular tokens list as fallback")
            
            # Some popular tokens to search
            popular_tokens = [
                "EPjFWaLb3odcccccccccccccccccccccccccccccccc",  # USDC
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenM9",   # USDT
                "MangoCzJ36AjZyKwVj3VnYU4GTonjfVEnJmvvWaxLac",  # MANGO
                "11111111111111111111111111111111",             # Wrapped SOL
            ]
            
            tokens = []
            for token_addr in popular_tokens:
                token = self.search_token(token_addr)
                if token:
                    tokens.append(token)
            
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ Manual tokens list failed: {e}")
            return []
    
    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """Get OHLCV candle data"""
        try:
            self._rate_limit()
            url = f"{self.api_url}/tokens/solana/{token_address}/candlesticks?timeframe={timeframe}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            candles = []
            
            if not data or not isinstance(data, dict):
                return []
            
            for candle in data.get('candles', []):
                if candle:
                    try:
                        candles.append({
                            'timestamp': candle.get('timestamp'),
                            'open': float(candle.get('open', 0)),
                            'high': float(candle.get('high', 0)),
                            'low': float(candle.get('low', 0)),
                            'close': float(candle.get('close', 0)),
                            'volume': float(candle.get('volume', 0))
                        })
                    except (ValueError, TypeError):
                        continue
            
            return candles
            
        except Exception as e:
            logger.debug(f"Error fetching OHLCV for {token_address}: {e}")
            return []
    
    def _parse_token_data(self, pair_data: Dict) -> Optional[Dict]:
        """Parse token data from DexScreener response"""
        try:
            if not pair_data or not isinstance(pair_data, dict):
                return None
            
            base_token = pair_data.get('baseToken', {})
            
            # Safe extraction
            liquidity_obj = pair_data.get('liquidity', {})
            liquidity = float(liquidity_obj.get('usd', 0)) if isinstance(liquidity_obj, dict) else 0
            
            market_cap = float(pair_data.get('marketCap', 0)) if pair_data.get('marketCap') else 0
            
            if liquidity < MIN_LIQUIDITY_USD:
                return None
            if market_cap > MAX_MARKET_CAP_USD:
                return None
            
            price_usd = float(pair_data.get('priceUsd', 0)) if pair_data.get('priceUsd') else 0
            
            price_change_obj = pair_data.get('priceChange', {})
            price_change_24h = float(price_change_obj.get('h24', 0)) if isinstance(price_change_obj, dict) else 0
            
            volume_obj = pair_data.get('volume', {})
            volume_24h = float(volume_obj.get('h24', 0)) if isinstance(volume_obj, dict) else 0
            
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
            logger.debug(f"Error parsing token data: {e}")
            return None
    
    def filter_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Filter tokens by trading criteria"""
        filtered = []
        
        for token in tokens:
            if not token:
                continue
            if token.get('market_cap_usd', 0) > MAX_MARKET_CAP_USD:
                continue
            if token.get('liquidity_usd', 0) < MIN_LIQUIDITY_USD:
                continue
            if token.get('volume_24h_usd', 0) < MIN_VOLUME_24H_USD:
                continue
            
            filtered.append(token)
        
        return filtered
