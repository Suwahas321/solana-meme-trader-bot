"""
Risk Management
Position sizing, stop loss, take profit
"""

import logging
from typing import Dict, Tuple
from config import *

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class RiskManager:
    """Manage portfolio risk and position sizing"""
    
    def __init__(self, wallet_balance_sol: float):
        self.wallet_balance = wallet_balance_sol
        self.positions = {}
        self.total_trades = 0
        self.winning_trades = 0
    
    def calculate_position_size(self, available_balance: float) -> float:
        """Calculate position size"""
        position_size = min(BUY_AMOUNT_SOL, available_balance / MAX_OPEN_TRADES)
        logger.info(f"Position size: {position_size} SOL")
        return position_size
    
    def can_open_trade(self, open_trades: int, daily_loss_percent: float) -> Tuple[bool, str]:
        """Check if we can open a new trade"""
        if open_trades >= MAX_OPEN_TRADES:
            return False, f"Max trades ({MAX_OPEN_TRADES}) reached"
        
        if daily_loss_percent <= MAX_DAILY_LOSS_PERCENT:
            return False, f"Daily loss limit reached"
        
        return True, "OK"
    
    def add_position(self, token_mint: str, entry_price: float,
                    position_size_sol: float, position_size_tokens: float) -> Dict:
        """Add a new position"""
        position = {
            'mint': token_mint,
            'entry_price': entry_price,
            'position_size_sol': position_size_sol,
            'position_size_tokens': position_size_tokens,
            'entry_value': position_size_sol,
            'status': 'open',
            'tp1_hit': False,
            'tp2_hit': False,
            'sl_hit': False,
            'current_price': entry_price,
            'pnl': 0,
            'pnl_percent': 0
        }
        
        self.positions[token_mint] = position
        logger.info(f"Position opened: {token_mint}")
        
        return position
    
    def update_position(self, token_mint: str, current_price: float) -> Dict:
        """Update position with current price"""
        if token_mint not in self.positions:
            return None
        
        position = self.positions[token_mint]
        position['current_price'] = current_price
        
        position_value = position['position_size_tokens'] * current_price
        position['pnl'] = position_value - position['entry_value']
        position['pnl_percent'] = (position['pnl'] / position['entry_value'] * 100) if position['entry_value'] > 0 else 0
        
        logger.debug(f"{token_mint}: {position['pnl_percent']:.2f}% PnL")
        
        return position
    
    def check_stop_loss(self, token_mint: str) -> bool:
        """Check if stop loss is hit"""
        if token_mint not in self.positions:
            return False
        
        position = self.positions[token_mint]
        if position['pnl_percent'] <= STOP_LOSS_PERCENT:
            logger.warning(f"STOP LOSS HIT: {token_mint}")
            position['status'] = 'closed'
            position['sl_hit'] = True
            return True
        
        return False
    
    def check_take_profit(self, token_mint: str) -> Tuple[bool, int]:
        """Check if take profit is hit"""
        if token_mint not in self.positions:
            return False, 0
        
        position = self.positions[token_mint]
        
        if position['pnl_percent'] >= TAKE_PROFIT_2_PERCENT and not position['tp2_hit']:
            logger.info(f"TAKE PROFIT 2 HIT: {token_mint}")
            position['tp2_hit'] = True
            return True, 2
        
        if position['pnl_percent'] >= TAKE_PROFIT_1_PERCENT and not position['tp1_hit']:
            logger.info(f"TAKE PROFIT 1 HIT: {token_mint}")
            position['tp1_hit'] = True
            return True, 1
        
        return False, 0
    
    def close_position(self, token_mint: str, exit_price: float, reason: str) -> Dict:
        """Close a position"""
        if token_mint not in self.positions:
            return None
        
        position = self.positions[token_mint]
        position['exit_price'] = exit_price
        position['status'] = 'closed'
        position['close_reason'] = reason
        
        if position['pnl'] > 0:
            self.winning_trades += 1
        
        self.total_trades += 1
        
        logger.info(f"Position closed: {token_mint} - {reason}")
        
        return position
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        open_positions = [p for p in self.positions.values() if p['status'] == 'open']
        closed_positions = [p for p in self.positions.values() if p['status'] == 'closed']
        
        total_pnl = sum(p['pnl'] for p in closed_positions)
        
        return {
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': f"{(self.winning_trades / self.total_trades * 100):.2f}%" if self.total_trades > 0 else "0%",
            'total_pnl_sol': total_pnl,
            'open_position_pnl': sum(p['pnl'] for p in open_positions),
            'unrealized_pnl_percent': sum(p['pnl_percent'] for p in open_positions) / len(open_positions) if open_positions else 0
      }
