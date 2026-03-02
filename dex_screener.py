"""
DexScreener API Integration - CORRECT Implementation
Using actual working endpoints from DexScreener API
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
        # Correct base URL
        self.api_url = "https://api.dexscreener.com/latest"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'solana-meme-trader-bot/1.0',
            'Accept': 'application/json'
        })
        self.last_request_time = 0
        self.min_request_interval = 0.5
    
    def _rate_limit(self):
        """Rate limiting to avoid hitting API limits"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def search_token(self, token_address: str) -> Optional[Dict]:
        """Search for token by address"""
        try:
            self._rate_limit()
            # Use the correct search endpoint
            url = f"https://api.dexscreener.com/latest/dex/pairs/solana/{token_address}"
            
            logger.debug(f"Searching token: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data and data.get('pair'):
                return self._parse_token_data(data['pair'])
            return None
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout searching token {token_address}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error searching token {token_address}")
            return None
        except Exception as e:
            logger.debug(f"Error searching token {token_address}: {e}")
            return None
    
    def get_latest_tokens(self, limit: int = 20) -> List[Dict]:
        """Get latest tokens on Solana"""
        try:
            self._rate_limit()
            
            # Try token profiles endpoint
            tokens = self._get_token_profiles(limit)
            if tokens and len(tokens) > 0:
                logger.info(f"✅ Fetched {len(tokens)} tokens from token profiles")
                return tokens
            
            # Fallback: Try searching for common tokens
            tokens = self._get_trending_tokens(limit)
            if tokens and len(tokens) > 0:
                logger.info(f"✅ Fetched {len(tokens)} tokens from trending search")
                return tokens
            
            logger.warning("⚠️ Could not fetch tokens from any endpoint")
            return []
            
        except Exception as e:
            logger.error(f"Error in get_latest_tokens: {e}")
            return []
    
    def _get_token_profiles(self, limit: int) -> List[Dict]:
        """Get token profiles from DexScreener"""
        try:
            self._rate_limit()
            url = "https://api.dexscreener.com/token-profiles/latest/v1"
            
            logger.info(f"Fetching token profiles from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if not isinstance(data, list):
                logger.warning(f"Unexpected response type: {type(data)}")
                return []
            
            logger.info(f"DexScreener returned {len(data)} token profiles")
            
            for i, token_profile in enumerate(data[:limit]):
                try:
                    if token_profile:
                        token = self._parse_token_profile(token_profile)
                        if token:
                            tokens.append(token)
                except Exception as e:
                    logger.debug(f"Error parsing token profile {i}: {e}")
                    continue
            
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ Token profiles endpoint failed: {e}")
            return []
    
    def _get_trending_tokens(self, limit: int) -> List[Dict]:
        """Search for trending tokens"""
        try:
            self._rate_limit()
            
            # Search for SOL/USDC pair as example
            search_queries = [
                "SOL/USDC",
                "MEME/SOL",
                "RAY/USDC",
                "SRM/USDC"
            ]
            
            tokens = []
            
            for query in search_queries[:limit]:
                try:
                    self._rate_limit()
                    url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
                    
                    logger.debug(f"Searching: {query}")
                    response = self.session.get(url, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    if data and isinstance(data, dict) and data.get('pairs'):
                        for pair in data['pairs'][:3]:  # Get top 3 for each query
                            if pair:
                                token = self._parse_token_data(pair)
                                if token:
                                    tokens.append(token)
                
                except Exception as e:
                    logger.debug(f"Error searching {query}: {e}")
                    continue
            
            return tokens
            
        except Exception as e:
            logger.warning(f"⚠️ Trending search failed: {e}")
            return []
    
    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """Get OHLCV candle data - Note: May not be available on free tier"""
        try:
            self._rate_limit()
            # DexScreener may not provide OHLCV on free tier
            # Returning empty list for now
            logger.debug(f"OHLCV data not available on free tier")
            return []
            
        except Exception as e:
            logger.debug(f"Error fetching OHLCV: {e}")
            return []
    
    def _parse_token_data(self, pair_data: Dict) -> Optional[Dict]:
        """Parse token data from pair response"""
        try:
            if not pair_data or not isinstance(pair_data, dict):
                return None
            
            base_token = pair_data.get('baseToken', {})
            
            # Safe extraction with defaults
            liquidity = float(pair_data.get('liquidity', {}).get('usd', 0)) if pair_data.get('liquidity') else 0
            market_cap = float(pair_data.get('marketCap', 0)) if pair_data.get('marketCap') else 0
            
            # Apply filters
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
    
    def _parse_token_profile(self, token_profile: Dict) -> Optional[Dict]:
        """Parse token from profile response"""
        try:
            if not token_profile or not isinstance(token_profile, dict):
                return None
            
            # Extract token info from profile
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
                'dex': 'Raydium',  # Most common on Solana
                'pair_address': token_profile.get('pairAddress'),
                'created_at': token_profile.get('createdAt'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Error parsing token profile: {e}")
            return None
    
    def filter_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Filter tokens by trading criteria"""
        filtered = []
        
        for token in tokens:
            if not token:
                continue
            
            # Skip if no valid price
            if token.get('price_usd', 0) == 0:
                continue
            
            # Check market cap filter
            if token.get('market_cap_usd', 0) > MAX_MARKET_CAP_USD:
                continue
            
            # Check liquidity filter
            if token.get('liquidity_usd', 0) < MIN_LIQUIDITY_USD:
                continue
            
            # Check volume filter
            if token.get('volume_24h_usd', 0) < MIN_VOLUME_24H_USD:
                continue
            
            filtered.append(token)
        
        return filtered
