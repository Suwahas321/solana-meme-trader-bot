import requests, logging, os
from typing import Dict, Optional, List
from config import *
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

class HeliusClient:
    def __init__(self):
        self.api_key = os.getenv('HELIUS_API_KEY')
        self.base_url = "https://api.helius.xyz/v0"
        self.session = requests.Session()
        self.enabled = bool(self.api_key)
        if self.api_key:
            logger.info("✅ Helius API initialized")
        else:
            logger.warning("⚠️ HELIUS_API_KEY not set!")
    
    def get_wallet_balance(self, wallet_address: str) -> Optional[float]:
        if not self.enabled:
            return None
        try:
            url = f"{self.base_url}/balance?address={wallet_address}&api-key={self.api_key}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            balance_sol = float(response.json().get('lamports', 0)) / 1_000_000_000
            logger.info(f"✅ Balance: {balance_sol:.4f} SOL")
            return balance_sol
        except Exception as e:
            logger.error(f"❌ Balance error: {e}")
            return None
    
    def get_wallet_transactions(self, wallet_address: str, limit: int = 10) -> List[Dict]:
        if not self.enabled:
            return []
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/transactions?api-key={self.api_key}&limit={limit}"
            response = self.session.get(url, timeout=10)
            return response.json()
        except:
            return []
    
    def get_token_balances(self, wallet_address: str) -> List[Dict]:
        if not self.enabled:
            return []
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/balances?api-key={self.api_key}"
            data = self.session.get(url, timeout=10).json()
            tokens = []
            if data.get('nativeBalance'):
                sol = float(data['nativeBalance'].get('lamports', 0)) / 1_000_000_000
                tokens.append({'mint': 'SOL', 'symbol': 'SOL', 'balance': sol})
            for t in data.get('tokens', []):
                try:
                    tokens.append({'mint': t.get('mint'), 'symbol': t.get('symbol', 'UNKNOWN'), 'balance': float(t.get('tokenAmount', {}).get('uiAmount', 0))})
                except:
                    pass
            return tokens
        except:
            return []

class WalletManager:
    def __init__(self, private_key: str):
        self.helius = HeliusClient()
        self.wallet_address = None
        self.initial_balance = None
        self.starting_balance = 100.0
        
        logger.info("="*50)
        logger.info("WALLET INIT")
        logger.info("="*50)
        
        try:
            from solders.keypair import Keypair
            try:
                key_bytes = bytes.fromhex(private_key)
                self.wallet_address = str(Keypair.from_secret_key(key_bytes).pubkey())
                logger.info(f"✅ Hex format decoded")
            except ValueError:
                try:
                    import base58
                    key_bytes = base58.b58decode(private_key)
                    self.wallet_address = str(Keypair.from_secret_key(key_bytes).pubkey())
                    logger.info(f"✅ Base58 format decoded")
                except Exception as e:
                    logger.error(f"❌ Both formats failed: {e}")
        except ImportError:
            logger.error("❌ solders not installed")
        except Exception as e:
            logger.error(f"❌ Error: {e}")
        
        if self.wallet_address:
            logger.info(f"✅ Wallet: {self.wallet_address[:12]}...")
            real_balance = self.get_balance()
            if real_balance and real_balance != 100:
                self.starting_balance = real_balance
                self.initial_balance = real_balance
                logger.info(f"✅ REAL BALANCE: {real_balance:.4f} SOL")
            else:
                logger.warning(f"⚠️ Using mock: 100 SOL")
        else:
            logger.error(f"❌ Wallet not initialized - key format wrong?")
        logger.info("="*50)
    
    def get_address(self) -> str:
        return self.wallet_address or "not_initialized"
    
    def get_balance(self) -> Optional[float]:
        if not self.wallet_address or not self.helius.enabled:
            return self.starting_balance
        balance = self.helius.get_wallet_balance(self.wallet_address)
        return balance if balance else self.starting_balance
    
    def get_token_balances(self) -> List[Dict]:
        return self.helius.get_token_balances(self.wallet_address) if self.wallet_address else []
    
    def get_portfolio_value(self) -> Dict:
        tokens = self.get_token_balances()
        sol = sum(t.get('balance', 0) for t in tokens if t.get('symbol') == 'SOL')
        return {'sol_balance': sol, 'total_value_sol': sol, 'token_count': len(tokens), 'tokens': tokens}
    
    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        return self.helius.get_wallet_transactions(self.wallet_address, limit) if self.wallet_address else []
    
    def get_balance_change(self) -> Optional[float]:
        if not self.initial_balance:
            return None
        current = self.get_balance()
        return current - self.initial_balance if current else None
    
    def get_balance_change_percent(self) -> Optional[float]:
        if not self.initial_balance or self.initial_balance == 0:
            return None
        change = self.get_balance_change()
        return (change / self.initial_balance * 100) if change else None
