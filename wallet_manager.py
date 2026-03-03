"""
Wallet Manager
Real wallet balance via Helius API.
Supports private key formats: base58, hex, JSON byte array.
"""

import requests
import logging
import os
import json
from typing import Dict, Optional, List
from config import LOG_LEVEL
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Helius API client
# ══════════════════════════════════════════════════════════════════════════════

class HeliusClient:
    """Helius API client for real wallet data"""

    def __init__(self):
        self.api_key = os.getenv('HELIUS_API_KEY')
        self.base_url = "https://api.helius.xyz/v0"
        self.session = requests.Session()

        if not self.api_key:
            logger.warning("⚠️ HELIUS_API_KEY not set — real balance unavailable")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ Helius API ready")

    def get_wallet_balance(self, wallet_address: str) -> Optional[float]:
        """Return wallet balance in SOL"""
        if not self.enabled:
            return None
        try:
            url = f"{self.base_url}/balance?address={wallet_address}&api-key={self.api_key}"
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            lamports = float(data.get('lamports', 0))
            sol = lamports / 1_000_000_000
            logger.info(f"✅ Balance from Helius: {sol:.4f} SOL")
            return sol
        except requests.exceptions.HTTPError as e:
            logger.error(f"Helius HTTP error {e.response.status_code} getting balance")
            return None
        except Exception as e:
            logger.error(f"Helius balance error: {e}")
            return None

    def get_wallet_transactions(self, wallet_address: str, limit: int = 10) -> List[Dict]:
        if not self.enabled:
            return []
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/transactions?api-key={self.api_key}&limit={limit}"
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Helius transactions error: {e}")
            return []

    def get_token_balances(self, wallet_address: str) -> List[Dict]:
        if not self.enabled:
            return []
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/balances?api-key={self.api_key}"
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            tokens = []
            if data.get('nativeBalance'):
                sol = float(data['nativeBalance'].get('lamports', 0)) / 1_000_000_000
                tokens.append({'mint': 'SOL', 'symbol': 'SOL', 'balance': sol, 'decimals': 9})
            for t in data.get('tokens', []):
                try:
                    tokens.append({
                        'mint': t.get('mint'),
                        'symbol': t.get('symbol', 'UNKNOWN'),
                        'balance': float(t.get('tokenAmount', {}).get('uiAmount', 0)),
                        'decimals': int(t.get('tokenAmount', {}).get('decimals', 0))
                    })
                except Exception:
                    continue
            return tokens
        except Exception as e:
            logger.error(f"Helius token balances error: {e}")
            return []

    def check_holder_concentration(self, token_mint: str) -> Optional[float]:
        if not self.enabled:
            return None
        try:
            url = f"{self.base_url}/token-metadata?mint={token_mint}&api-key={self.api_key}"
            r = self.session.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            holders = data.get('holders', []) if data else []
            if holders:
                return float(holders[0].get('balance', 0)) / 100
            return None
        except Exception as e:
            logger.debug(f"Holder concentration error: {e}")
            return None


# ══════════════════════════════════════════════════════════════════════════════
# Wallet Manager
# ══════════════════════════════════════════════════════════════════════════════

class WalletManager:
    """Manages Solana wallet — loads key, fetches real balance via Helius"""

    def __init__(self, private_key: str):
        self.private_key = private_key
        self.helius = HeliusClient()

        # Load wallet address (supports base58, hex, JSON array)
        self.wallet_address = self._load_wallet_address(private_key)

        # Balance tracking — NO hardcoded fallback
        self.initial_balance: Optional[float] = None
        self.starting_balance: Optional[float] = None

        if self.wallet_address:
            logger.info(f"✅ Wallet initialized: {self.wallet_address[:8]}...{self.wallet_address[-6:]}")
            real_balance = self.get_balance()
            if real_balance is not None:
                self.initial_balance = real_balance
                self.starting_balance = real_balance
                logger.info(f"✅ Starting balance: {real_balance:.4f} SOL")
            else:
                logger.warning("⚠️ Could not fetch real balance — check HELIUS_API_KEY")
        else:
            logger.error("❌ Wallet address could not be loaded — check WALLET_PRIVATE_KEY format")

    # ------------------------------------------------------------------ key loading
    def _load_wallet_address(self, private_key: str) -> Optional[str]:
        """
        Load keypair from private key and return public address.
        Supports three formats:
          1. Base58 string  — most common (Phantom / Solflare export)
          2. Hex string     — 128 hex chars (64 bytes)
          3. JSON byte array — [1,2,...,64]
        """
        try:
            from solders.keypair import Keypair
        except ImportError:
            logger.error("solders not installed — run: pip install solders")
            return None

        pk = private_key.strip()

        # Format 1: JSON byte array [1,2,...,64]
        if pk.startswith('['):
            try:
                byte_list = json.loads(pk)
                keypair = Keypair.from_bytes(bytes(byte_list))
                addr = str(keypair.pubkey())
                logger.info(f"Key format: JSON array → {addr[:8]}...")
                return addr
            except Exception as e:
                logger.debug(f"JSON array key failed: {e}")

        # Format 2: Hex string (128 or 64 chars)
        hex_clean = pk.replace('0x', '').replace(' ', '')
        if len(hex_clean) in (128, 64) and all(c in '0123456789abcdefABCDEF' for c in hex_clean):
            try:
                keypair = Keypair.from_bytes(bytes.fromhex(hex_clean))
                addr = str(keypair.pubkey())
                logger.info(f"Key format: hex → {addr[:8]}...")
                return addr
            except Exception as e:
                logger.debug(f"Hex key failed: {e}")

        # Format 3a: Base58 via solders built-in
        try:
            keypair = Keypair.from_base58_string(pk)
            addr = str(keypair.pubkey())
            logger.info(f"Key format: base58 (solders) → {addr[:8]}...")
            return addr
        except Exception as e:
            logger.debug(f"solders base58 failed: {e}")

        # Format 3b: Base58 via base58 library
        try:
            import base58
            decoded = base58.b58decode(pk)
            keypair = Keypair.from_bytes(decoded)
            addr = str(keypair.pubkey())
            logger.info(f"Key format: base58 (lib) → {addr[:8]}...")
            return addr
        except Exception as e:
            logger.debug(f"base58 lib failed: {e}")

        logger.error(
            "❌ WALLET_PRIVATE_KEY not recognised.\n"
            "   Accepted formats:\n"
            "   • Base58 string  (from Phantom: Settings → Export Private Key)\n"
            "   • 128-char hex string\n"
            "   • JSON byte array [1,2,...,64]"
        )
        return None

    # ------------------------------------------------------------------ public API
    def get_address(self) -> str:
        return self.wallet_address or "not_initialized"

    def get_balance(self) -> Optional[float]:
        """Get real SOL balance from Helius. Returns None if unavailable."""
        if not self.wallet_address:
            return None
        if not self.helius.enabled:
            logger.warning("Helius disabled — cannot fetch real balance")
            return self.starting_balance  # May be None on first call
        balance = self.helius.get_wallet_balance(self.wallet_address)
        return balance  # Can be None — callers must handle this

    def get_token_balances(self) -> List[Dict]:
        if not self.wallet_address:
            return []
        return self.helius.get_token_balances(self.wallet_address)

    def get_portfolio_value(self) -> Dict:
        balances = self.get_token_balances()
        sol_balance = 0.0
        for t in balances:
            if t.get('symbol') == 'SOL':
                sol_balance = t.get('balance', 0)
        return {
            'sol_balance': sol_balance,
            'total_value_sol': sol_balance,
            'token_count': len(balances),
            'tokens': balances
        }

    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        if not self.wallet_address:
            return []
        return self.helius.get_wallet_transactions(self.wallet_address, limit)

    def get_balance_change(self) -> Optional[float]:
        if self.initial_balance is None:
            return None
        current = self.get_balance()
        if current is None:
            return None
        return current - self.initial_balance

    def get_balance_change_percent(self) -> Optional[float]:
        if not self.initial_balance:
            return None
        change = self.get_balance_change()
        if change is None:
            return None
        return (change / self.initial_balance) * 100
