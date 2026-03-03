"""
DexScreener API Integration
Fixed: token profiles now have pair data fetched so filters have real values
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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'solana-meme-trader-bot/1.0',
            'Accept': 'application/json'
        })
        self.last_request_time = 0
        self.min_request_interval = 0.4

    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def _get(self, url: str, timeout: int = 12) -> Optional[dict]:
        try:
            self._rate_limit()
            r = self.session.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.debug(f"GET failed [{url}]: {e}")
            return None

    # ------------------------------------------------------------------ public
    def search_token(self, token_address: str) -> Optional[Dict]:
        """Get current token data by mint address"""
        data = self._get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}")
        if not data:
            return None
        pairs = [p for p in (data.get('pairs') or []) if p.get('chainId') == 'solana']
        if not pairs:
            return None
        pairs.sort(key=lambda p: float((p.get('liquidity') or {}).get('usd', 0) or 0), reverse=True)
        return self._parse_pair(pairs[0])

    def get_latest_tokens(self, limit: int = 50) -> List[Dict]:
        """
        Get latest Solana tokens with REAL pair data.

        Root cause of 30->0 filter bug:
        The token-profiles endpoint only returns token addresses and metadata —
        it does NOT include liquidity/volume/marketCap. Every token had 0 for
        these fields and failed all filters.

        Fix: collect addresses from profiles/boosts, then call the tokens
        endpoint for each to get real pair data before filtering.
        """
        addresses = []

        # Source 1: token-profiles
        addrs1 = self._get_profile_addresses(limit * 2)
        logger.info(f"Profiles source: {len(addrs1)} addresses")
        addresses.extend(addrs1)

        # Source 2: token-boosts (supplement)
        addrs2 = self._get_boost_addresses(limit * 2)
        logger.info(f"Boosts source:   {len(addrs2)} addresses")
        addresses.extend(addrs2)

        # Deduplicate while preserving order
        seen = set()
        unique_addresses = []
        for a in addresses:
            if a and a not in seen:
                seen.add(a)
                unique_addresses.append(a)

        # Fallback if no addresses found
        if len(unique_addresses) < 5:
            logger.warning("Profile/boost endpoints returned no Solana addresses — using search fallback")
            return self._search_solana_tokens(limit)

        logger.info(f"Fetching pair data for {min(len(unique_addresses), limit)} addresses...")

        tokens = []
        for addr in unique_addresses[:limit]:
            token = self._fetch_pair_data(addr)
            if token:
                tokens.append(token)

        logger.info(f"Pair data fetched: {len(tokens)} tokens with real values")
        return tokens

    def get_token_ohlcv(self, token_address: str, timeframe: str = "1h") -> List[Dict]:
        """DexScreener free tier has no OHLCV endpoint — always empty"""
        return []

    # ------------------------------------------------------------------ sources
    def _get_profile_addresses(self, limit: int) -> List[str]:
        """Get token addresses from token-profiles/latest/v1"""
        data = self._get("https://api.dexscreener.com/token-profiles/latest/v1")
        if not data or not isinstance(data, list):
            logger.warning("token-profiles: no data returned")
            return []
        addresses = []
        for entry in data[:limit]:
            # Only take Solana tokens
            chain = entry.get('chainId', '')
            if chain and chain != 'solana':
                continue
            addr = entry.get('tokenAddress') or entry.get('address')
            if addr:
                addresses.append(addr)
        return addresses

    def _get_boost_addresses(self, limit: int) -> List[str]:
        """Get token addresses from token-boosts/latest/v1"""
        data = self._get("https://api.dexscreener.com/token-boosts/latest/v1")
        if not data or not isinstance(data, list):
            return []
        addresses = []
        for entry in data[:limit]:
            chain = entry.get('chainId', '')
            if chain and chain != 'solana':
                continue
            addr = entry.get('tokenAddress') or entry.get('address')
            if addr:
                addresses.append(addr)
        return addresses

    def _fetch_pair_data(self, token_address: str) -> Optional[Dict]:
        """
        Fetch real pair data for a token address.
        This is the critical step that gives us liquidity/volume/marketCap.
        """
        data = self._get(f"https://api.dexscreener.com/latest/dex/tokens/{token_address}")
        if not data:
            return None
        pairs = [p for p in (data.get('pairs') or []) if p.get('chainId') == 'solana']
        if not pairs:
            return None
        # Best pair = highest liquidity
        pairs.sort(key=lambda p: float((p.get('liquidity') or {}).get('usd', 0) or 0), reverse=True)
        return self._parse_pair(pairs[0])

    def _search_solana_tokens(self, limit: int) -> List[Dict]:
        """Search-based fallback when profile endpoints fail"""
        queries = ["solana meme", "pump fun sol", "raydium sol", "new sol token",
                   "bonk", "sol cat", "sol dog", "pepe sol"]
        tokens = []
        seen = set()
        for q in queries:
            if len(tokens) >= limit:
                break
            data = self._get(f"https://api.dexscreener.com/latest/dex/search?q={q.replace(' ', '%20')}")
            if not data:
                continue
            for pair in (data.get('pairs') or []):
                if pair.get('chainId') != 'solana':
                    continue
                addr = (pair.get('baseToken') or {}).get('address', '')
                if not addr or addr in seen:
                    continue
                seen.add(addr)
                token = self._parse_pair(pair)
                if token:
                    tokens.append(token)
        logger.info(f"Search fallback: {len(tokens)} tokens")
        return tokens

    # ------------------------------------------------------------------ parser
    def _parse_pair(self, pair: Dict) -> Optional[Dict]:
        """Parse a DexScreener pair into our standard token dict"""
        try:
            if not pair or not isinstance(pair, dict):
                return None
            if pair.get('chainId') and pair['chainId'] != 'solana':
                return None

            base  = pair.get('baseToken') or {}
            mint  = base.get('address')
            if not mint:
                return None

            liq_obj    = pair.get('liquidity') or {}
            liquidity  = float(liq_obj.get('usd', 0) or 0)
            market_cap = float(pair.get('marketCap', 0) or pair.get('fdv', 0) or 0)
            price_usd  = float(pair.get('priceUsd', 0) or 0)

            pc = pair.get('priceChange') or {}
            price_change_1h  = float(pc.get('h1',  0) or 0)
            price_change_6h  = float(pc.get('h6',  0) or 0)
            price_change_24h = float(pc.get('h24', 0) or 0)

            vol = pair.get('volume') or {}
            volume_1h  = float(vol.get('h1',  0) or 0)
            volume_24h = float(vol.get('h24', 0) or 0)

            txns     = pair.get('txns') or {}
            t24      = txns.get('h24') or {}
            buys_24  = int(t24.get('buys',  0) or 0)
            sells_24 = int(t24.get('sells', 0) or 0)
            bsr      = (buys_24 / sells_24) if sells_24 > 0 else (1.5 if buys_24 > 0 else 1.0)

            return {
                'mint_address':     mint,
                'symbol':           base.get('symbol', 'UNKNOWN'),
                'name':             base.get('name', 'Unknown'),
                'price_usd':        price_usd,
                'price_change_1h':  price_change_1h,
                'price_change_6h':  price_change_6h,
                'price_change_24h': price_change_24h,
                'liquidity_usd':    liquidity,
                'market_cap_usd':   market_cap,
                'volume_1h_usd':    volume_1h,
                'volume_24h_usd':   volume_24h,
                'buys_24h':         buys_24,
                'sells_24h':        sells_24,
                'buy_sell_ratio':   bsr,
                'dex':              pair.get('dexId', 'unknown'),
                'pair_address':     pair.get('pairAddress'),
                'created_at':       pair.get('pairCreatedAt'),
                'timestamp':        datetime.now().isoformat()
            }
        except Exception as e:
            logger.debug(f"_parse_pair error: {e}")
            return None

    # ------------------------------------------------------------------ filter
    def filter_tokens(self, tokens: List[Dict]) -> List[Dict]:
        """Filter tokens by criteria — logs every rejection"""
        passed = []
        counts = dict(no_price=0, no_addr=0, mc=0, liq=0, vol=0, dump=0)

        for t in tokens:
            if not t:
                continue
            if not t.get('mint_address'):
                counts['no_addr'] += 1
                continue
            if t.get('price_usd', 0) == 0:
                counts['no_price'] += 1
                continue

            mc  = t.get('market_cap_usd', 0)
            liq = t.get('liquidity_usd',  0)
            vol = t.get('volume_24h_usd', 0)
            pc1 = t.get('price_change_1h', 0)

            if mc > MAX_MARKET_CAP_USD:
                counts['mc'] += 1
                logger.debug(f"REJECT mc   : {t['symbol']} ${mc:,.0f} > max ${MAX_MARKET_CAP_USD:,.0f}")
                continue
            if liq < MIN_LIQUIDITY_USD:
                counts['liq'] += 1
                logger.debug(f"REJECT liq  : {t['symbol']} ${liq:,.0f} < min ${MIN_LIQUIDITY_USD:,.0f}")
                continue
            if vol < MIN_VOLUME_24H_USD:
                counts['vol'] += 1
                logger.debug(f"REJECT vol  : {t['symbol']} ${vol:,.0f} < min ${MIN_VOLUME_24H_USD:,.0f}")
                continue
            if pc1 < MIN_PRICE_CHANGE_1H:
                counts['dump'] += 1
                logger.debug(f"REJECT dump : {t['symbol']} 1h={pc1:.1f}% < {MIN_PRICE_CHANGE_1H}%")
                continue

            passed.append(t)

        logger.info(
            f"Filter: {len(passed)}/{len(tokens)} passed | "
            f"rejected → liq:{counts['liq']} vol:{counts['vol']} "
            f"mc:{counts['mc']} dump:{counts['dump']} "
            f"no_price:{counts['no_price']} no_addr:{counts['no_addr']}"
        )
        return passed
