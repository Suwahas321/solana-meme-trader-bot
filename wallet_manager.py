"""
Wallet Manager with Helius API Integration
Real wallet balance monitoring and transaction tracking
"""

import requests
import logging
from typing import Dict, Optional, List
from config import *
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class HeliusClient:
    """Helius API client for Solana wallet monitoring"""
    
    def __init__(self):
        self.api_key = os.getenv('HELIUS_API_KEY')
        self.base_url = "https://api.helius.xyz/v0"
        self.session = requests.Session()
        
        if not self.api_key:
            logger.warning("⚠️ HELIUS_API_KEY not found in .env - Helius features disabled")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ Helius API initialized")
    
    def get_wallet_balance(self, wallet_address: str) -> Optional[float]:
        """Get real wallet balance in SOL"""
        if not self.enabled:
            logger.debug("Helius disabled - cannot get wallet balance")
            return None
        
        try:
            url = f"{self.base_url}/balance?address={wallet_address}&api-key={self.api_key}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Convert from lamports to SOL (1 SOL = 1,000,000,000 lamports)
            balance_lamports = float(data.get('lamports', 0))
            balance_sol = balance_lamports / 1_000_000_000
            
            logger.info(f"✅ Wallet balance: {balance_sol:.4f} SOL")
            return balance_sol
            
        except requests.exceptions.Timeout:
            logger.error("Helius API timeout getting wallet balance")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Helius HTTP error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return None
    
    def get_wallet_transactions(self, wallet_address: str, limit: int = 10) -> List[Dict]:
        """Get recent wallet transactions"""
        if not self.enabled:
            logger.debug("Helius disabled - cannot get transactions")
            return []
        
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/transactions?api-key={self.api_key}&limit={limit}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            transactions = response.json()
            
            if not isinstance(transactions, list):
                logger.warning(f"Unexpected transaction response type: {type(transactions)}")
                return []
            
            logger.info(f"✅ Retrieved {len(transactions)} transactions")
            return transactions
            
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def get_transaction_details(self, tx_signature: str) -> Optional[Dict]:
        """Get detailed transaction information"""
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/transactions/?api-key={self.api_key}&txn-signature={tx_signature}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except Exception as e:
            logger.error(f"Error getting transaction details: {e}")
            return None
    
    def get_token_balances(self, wallet_address: str) -> List[Dict]:
        """Get all token balances for wallet"""
        if not self.enabled:
            logger.debug("Helius disabled - cannot get token balances")
            return []
        
        try:
            url = f"{self.base_url}/addresses/{wallet_address}/balances?api-key={self.api_key}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            tokens = []
            
            # Parse native SOL balance
            if data.get('nativeBalance'):
                native_balance = float(data['nativeBalance'].get('lamports', 0)) / 1_000_000_000
                tokens.append({
                    'mint': 'SOL',
                    'symbol': 'SOL',
                    'balance': native_balance,
                    'decimals': 9
                })
            
            # Parse token balances
            for token in data.get('tokens', []):
                try:
                    tokens.append({
                        'mint': token.get('mint'),
                        'symbol': token.get('symbol', 'UNKNOWN'),
                        'balance': float(token.get('tokenAmount', {}).get('uiAmount', 0)),
                        'decimals': int(token.get('tokenAmount', {}).get('decimals', 0))
                    })
                except (ValueError, TypeError, KeyError):
                    continue
            
            logger.info(f"✅ Retrieved {len(tokens)} token balances")
            return tokens
            
        except Exception as e:
            logger.error(f"Error getting token balances: {e}")
            return []
    
    def check_holder_concentration(self, token_mint: str) -> Optional[float]:
        """Check holder concentration for token (potential rugpull indicator)"""
        if not self.enabled:
            return None
        
        try:
            url = f"{self.base_url}/token-metadata?mint={token_mint}&api-key={self.api_key}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Try to get holder info
            if data and data.get('holders'):
                # Calculate concentration (top holder percentage)
                all_holders = data['holders']
                if len(all_holders) > 0:
                    top_holder_percentage = (all_holders[0].get('balance', 0) / 100)
                    return top_holder_percentage
            
            return None
            
        except Exception as e:
            logger.debug(f"Error checking holder concentration: {e}")
            return None


class WalletManager:
    """Manages wallet with Helius integration for real-time monitoring"""
    
    def __init__(self, private_key: str):
        """Initialize wallet manager"""
        self.private_key = private_key
        self.helius = HeliusClient()
        
        # Get wallet address from private key
        try:
            from solders.keypair import Keypair
            keypair = Keypair.from_secret_key(bytes.fromhex(private_key))
            self.wallet_address = str(keypair.pubkey())
        except Exception as e:
            logger.error(f"Error loading wallet: {e}")
            self.wallet_address = None
        
        # Track initial balance
        self.initial_balance = None
        self.starting_balance = 100  # Default starting balance (from config)
        
        if self.wallet_address:
            logger.info(f"✅ Wallet initialized: {self.wallet_address[:8]}...")
            
            # Get real balance if Helius available
            real_balance = self.get_balance()
            if real_balance:
                self.starting_balance = real_balance
                self.initial_balance = real_balance
                logger.info(f"✅ Real wallet balance: {real_balance:.4f} SOL")
        else:
            logger.warning("⚠️ Could not initialize wallet address")
    
    def get_address(self) -> str:
        """Get wallet address"""
        return self.wallet_address
    
    def get_balance(self) -> Optional[float]:
        """Get real wallet balance from Helius"""
        if not self.wallet_address or not self.helius.enabled:
            # Return simulated balance if Helius not available
            logger.debug("Using simulated balance (Helius not available)")
            return self.starting_balance
        
        balance = self.helius.get_wallet_balance(self.wallet_address)
        if balance is not None:
            return balance
        
        # Fallback to default
        return self.starting_balance
    
    def get_token_balances(self) -> List[Dict]:
        """Get all token balances"""
        if not self.wallet_address:
            return []
        
        return self.helius.get_token_balances(self.wallet_address)
    
    def get_portfolio_value(self) -> Dict:
        """Get total portfolio value"""
        balances = self.get_token_balances()
        
        total_value = 0
        sol_balance = 0
        
        for token in balances:
            if token.get('symbol') == 'SOL':
                sol_balance = token.get('balance', 0)
                total_value += sol_balance
            else:
                # For other tokens, would need price data
                # For now, just show balance
                pass
        
        return {
            'sol_balance': sol_balance,
            'total_value_sol': total_value,
            'token_count': len(balances),
            'tokens': balances
        }
    
    def get_recent_transactions(self, limit: int = 10) -> List[Dict]:
        """Get recent transactions"""
        if not self.wallet_address:
            return []
        
        return self.helius.get_wallet_transactions(self.wallet_address, limit)
    
    def get_balance_change(self) -> Optional[float]:
        """Get balance change since start"""
        if self.initial_balance is None:
            return None
        
        current = self.get_balance()
        if current is None:
            return None
        
        change = current - self.initial_balance
        return change
    
    def get_balance_change_percent(self) -> Optional[float]:
        """Get balance change percentage"""
        if self.initial_balance is None or self.initial_balance == 0:
            return None
        
        change = self.get_balance_change()
        if change is None:
            return None
        
        percent = (change / self.initial_balance) * 100
        return percent
