"""
Moralis Token Discovery API - RELIABLE SOLANA TOKEN DATA
Using Moralis API: https://docs.moralis.com/data-api/solana/token
Replaces DexScreener with more reliable source
"""

import requests
import logging
import os
from typing import Dict, Optional, List
from config import *
from datetime import datetime
import time

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class DexScreenerClient:
    """Token discovery using Moralis API (replaces DexScreener)"""
    
    def __init__(self):
        """Initialize Moralis client"""
        # Read Moralis API key from environment
        self.moralis_key = os.getenv('MORALIS_API_KEY')
        
        if not self.moralis_key:
            logger.warning("⚠️ MORALIS_API_KEY not set - will use fallback")
            self.moralis_key = None
        
        self.api_url = "https://solana-gateway.moralis.io/api/v1"
        self.session = requests.Session()
        if self.moralis_key:
            self.session.headers.update({
                'X-API-Key': self.moralis_key,
                'User-Agent': 'solana-meme-bot/1.0'
            })
        
        self.last_request_time = 0
        self.min_request_interval = 0.5
        logger.info("✅ Moralis Token Discovery initialized")
    
    def _rate_limit(self):
        """Rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def search_token(self, token_address: str) -> Optional[Dict]:
        """Get token metadata by address
        GET /token/{network}/{address}
        """
        if not self.moralis_key:
            logger.warning("⚠️ Moralis API key not set")
            return None
        
        try:
            self._rate_limit()
            url = f"{self.api_url}/token/solana/{token_address}"
            
            logger.debug(f"Fetching token: {token_address[:8]}...")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_token_data(data)
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching token {token_address}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.debug(f"HTTP error: {e}")
            return None
        except Exception as e:
            logger.debug(f"Error searching token: {e}")
            return None
    
    def get_latest_tokens(self, limit: int = 50) -> List[Dict]:
        """Get latest token transfers (indicates new/active tokens)
        Endpoint: GET /token/solana/transfers
        """
        if not self.moralis_key:
            logger.warning("⚠️ Moralis API key not set - using fallback")
            return self._get_fallback_tokens(limit)
        
        try:
            self._rate_limit()
            
            # Use transfers endpoint to find active tokens
            url = f"{self.api_url}/token/solana/transfers"
            
            params = {
                'limit': limit,
                'order_by': 'block_time',
                'order_direction': 'DESC'
            }
            
            logger.info(f"Fetching latest tokens from Moralis...")
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            tokens = []
            
            if not data or 'result' not in data:
                logger.warning("No tokens in Moralis response")
                return self._get_fallback_tokens(limit)
            
            # Process transfers to extract unique tokens
            seen_tokens = set()
            for transfer in data['result'][:limit*5]:
                try:
                    token_addr = transfer.get('mint')
                    if token_addr and token_addr not in seen_tokens:
                        seen_tokens.add(token_addr)
                        
                        # Get full token metadata
                        token_data = self.search_token(token_addr)
                        if token_data:
                            tokens.append(token_data)
                        
                        if len(tokens) >= limit:
                            break
                
                except Exception as e:
                    logger.debug(f"Error processing token: {e}")
                    continue
            
            filtered = self.filter_tokens(tokens)
            logger.info(f"✅ Got {len(filtered)} tokens from Moralis")
            return filtered
            
        except Exception as e:
            logger.error(f"Error fetching latest tokens: {e}")
            return self._get_fallback_tokens(limit)
    
    def _get_fallback_tokens(self, limit: int) -> List[Dict]:
        """Fallback: manually fetch popular tokens"""
        try:
            logger.info("Using fallback: fetching popular tokens")
            
            # Popular Solana tokens to check
            popular_tokens = [
                "EPjFWdd5Au5A6KwZAeFsc4Uj4zqQmxCx3pYEYwLPxvgx",  # USDC
                "So11111111111111111111111111111111111111112",   # SOL
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenEuw",  # USDT
            ]
            
            tokens = []
            for token_addr in popular_tokens[:limit]:
                try:
                    token = self.search_token(token_addr)
                    if token:
                        tokens.append(token)
                except:
                    continue
            
            logger.info(f"Fallback: got {len(tokens)} tokens")
            return tokens
            
        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            return []
    
    def get_token_pools(self, token_address: str) -> List[Dict]:
        """Get liquidity pools for token"""
        try:
            # For now, just return the token itself
            token = self.search_token(token_address)
            return [token] if token else []
        except Exception as e:
            logger.error(f"Error getting pools: {e}")
            return []
    
    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """OHLCV data not available in Moralis free tier"""
        return []
    
    def _parse_token_data(self, moralis_data: Dict) -> Optional[Dict]:
        """Parse Moralis token response"""
        try:
            if not moralis_data or not isinstance(moralis_data, dict):
                return None
            
            token_address = moralis_data.get('address') or moralis_data.get('mint')
            if not token_address:
                return None
            
            # Extract price info
            price_usd = 0
            if 'usd_price' in moralis_data:
                price_usd = float(moralis_data['usd_price'])
            
            # Extract liquidity if available
            liquidity = 0
            if 'liquidity' in moralis_data:
                liquidity = float(moralis_data['liquidity'])
            
            # Extract market cap if available
            market_cap = 0
            if 'market_cap' in moralis_data:
                market_cap = float(moralis_data['market_cap'])
            elif price_usd > 0 and 'total_supply' in moralis_data:
                total_supply = float(moralis_data['total_supply'])
                market_cap = price_usd * total_supply
            
            # Apply filters
            if liquidity < MIN_LIQUIDITY_USD:
                logger.debug(f"Token {token_address[:8]} filtered: low liquidity ${liquidity}")
                return None
            
            if market_cap > MAX_MARKET_CAP_USD:
                logger.debug(f"Token {token_address[:8]} filtered: high market cap ${market_cap}")
                return None
            
            return {
                'mint_address': token_address,
                'symbol': moralis_data.get('symbol', 'UNKNOWN'),
                'name': moralis_data.get('name', 'Unknown'),
                'price_usd': price_usd,
                'price_change_24h': float(moralis_data.get('price_change_percent_24h', 0)),
                'liquidity_usd': liquidity,
                'market_cap_usd': market_cap,
                'volume_24h_usd': float(moralis_data.get('volume_24h', 0)),
                'dex': 'Moralis',
                'pair_address': token_address,
                'created_at': moralis_data.get('created_at'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Error parsing token: {e}")
            return None
    
    def filter_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Filter tokens by criteria"""
        filtered = []
        
        for token in tokens:
            if not token:
                continue
            
            # Skip if no valid price
            if token.get('price_usd', 0) == 0:
                continue
            
            # Check market cap
            if token.get('market_cap_usd', 0) > MAX_MARKET_CAP_USD:
                continue
            
            # Check liquidity
            if token.get('liquidity_usd', 0) < MIN_LIQUIDITY_USD:
                continue
            
            # Check volume
            if token.get('volume_24h_usd', 0) < MIN_VOLUME_24H_USD:
                continue
            
            filtered.append(token)
        
        logger.info(f"Filtered: {len(tokens)} → {len(filtered)} tokens")
        return filtered
