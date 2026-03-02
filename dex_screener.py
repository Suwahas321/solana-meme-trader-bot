"""
DexScreener API Integration - OFFICIAL ENDPOINTS
Using correct endpoints from https://docs.dexscreener.com/api/reference
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
        self.api_url = "https://api.dexscreener.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'solana-meme-trader-bot/1.0',
            'Accept': 'application/json'
        })
        self.last_request_time = 0
        self.min_request_interval = 0.5
        logger.info("✅ DexScreener client initialized")
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def search_token(self, token_address: str) -> Optional[Dict]:
        """GET /latest/dex/pairs/solana/{pairId}"""
        try:
            self._rate_limit()
            url = f"{self.api_url}/latest/dex/pairs/solana/{token_address}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data and data.get('pairs') and len(data['pairs']) > 0:
                return self._parse_token_data(data['pairs'][0])
            return None
        except Exception as e:
            logger.debug(f"Error searching token: {e}")
            return None
    
    def get_latest_tokens(self, limit: int = 20) -> List[Dict]:
        """GET /token-profiles/latest/v1 (60 req/min)"""
        try:
            self._rate_limit()
            url = f"{self.api_url}/token-profiles/latest/v1"
            logger.info(f"Fetching latest token profiles...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                logger.warning(f"Unexpected response type: {type(data)}")
                return []
            
            logger.info(f"✅ DexScreener returned {len(data)} token profiles")
            tokens = []
            
            for i, token_profile in enumerate(data[:limit]):
                try:
                    if token_profile:
                        token = self._parse_token_profile(token_profile)
                        if token:
                            tokens.append(token)
                except Exception as e:
                    logger.debug(f"Error parsing token {i}: {e}")
                    continue
            
            logger.info(f"✅ Fetched {len(tokens)} tokens")
            return tokens
            
        except Exception as e:
            logger.error(f"Error fetching tokens: {e}")
            return self._search_fallback(limit)
    
    def _search_fallback(self, limit: int) -> List[Dict]:
        """Fallback: GET /latest/dex/search?q= (300 req/min)"""
        try:
            self._rate_limit()
            logger.info("Using fallback search...")
            
            search_queries = ["SOL/USDC", "SOL/USDT", "JUP/SOL"]
            tokens = []
            
            for query in search_queries[:limit]:
                try:
                    self._rate_limit()
                    url = f"{self.api_url}/latest/dex/search"
                    response = self.session.get(url, params={'q': query}, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data and data.get('pairs'):
                        for pair in data['pairs'][:3]:
                            if pair:
                                token = self._parse_token_data(pair)
                                if token:
                                    tokens.append(token)
                except Exception as e:
                    logger.debug(f"Error searching {query}: {e}")
                    continue
            
            logger.info(f"✅ Fallback found {len(tokens)} tokens")
            return tokens
        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            return []
    
    def get_token_pools(self, token_address: str) -> List[Dict]:
        """GET /token-pairs/v1/solana/{tokenAddress} (300 req/min)"""
        try:
            self._rate_limit()
            url = f"{self.api_url}/token-pairs/v1/solana/{token_address}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                return []
            
            tokens = []
            for pair in data[:5]:
                try:
                    token = self._parse_token_data(pair)
                    if token:
                        tokens.append(token)
                except:
                    continue
            return tokens
        except Exception as e:
            logger.error(f"Error getting pools: {e}")
            return []
    
    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """OHLCV not available on free tier"""
        return []
    
    def _parse_token_data(self, pair_data: Dict) -> Optional[Dict]:
        try:
            if not pair_data:
                return None
            
            base_token = pair_data.get('baseToken', {})
            liquidity_obj = pair_data.get('liquidity', {})
            liquidity = float(liquidity_obj.get('usd', 0)) if isinstance(liquidity_obj, dict) else 0
            market_cap = float(pair_data.get('marketCap', 0)) if pair_data.get('marketCap') else 0
            
            if liquidity < MIN_LIQUIDITY_USD or market_cap > MAX_MARKET_CAP_USD:
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
            logger.debug(f"Error parsing token: {e}")
            return None
    
    def _parse_token_profile(self, token_profile: Dict) -> Optional[Dict]:
        try:
            if not token_profile:
                return None
            
            token_address = token_profile.get('tokenAddress')
            if not token_address:
                return None
            
            return {
                'mint_address': token_address,
                'symbol': token_profile.get('symbol', 'UNKNOWN'),
                'name': token_profile.get('name', 'Unknown'),
                'price_usd': float(token_profile.get('price', 0)) if token_profile.get('price') else 0,
                'price_change_24h': float(token_profile.get('priceChange24h', 0)) if token_profile.get('priceChange24h') else 0,
                'liquidity_usd': float(token_profile.get('liquidity', 0)) if token_profile.get('liquidity') else 0,
                'market_cap_usd': float(token_profile.get('marketCap', 0)) if token_profile.get('marketCap') else 0,
                'volume_24h_usd': float(token_profile.get('volume24h', 0)) if token_profile.get('volume24h') else 0,
                'dex': token_profile.get('dexId', 'Raydium'),
                'pair_address': token_profile.get('pairAddress'),
                'created_at': token_profile.get('createdAt'),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"Error parsing profile: {e}")
            return None
    
    def filter_tokens(self, tokens: List[Dict]) -> List[Dict]:
        filtered = []
        for token in tokens:
            if not token or token.get('price_usd', 0) == 0:
                continue
            if token.get('market_cap_usd', 0) > MAX_MARKET_CAP_USD:
                continue
            if token.get('liquidity_usd', 0) < MIN_LIQUIDITY_USD:
                continue
            if token.get('volume_24h_usd', 0) < MIN_VOLUME_24H_USD:
                continue
            filtered.append(token)
        
        logger.info(f"Filtered: {len(tokens)} → {len(filtered)} tokens")
        return filtered
