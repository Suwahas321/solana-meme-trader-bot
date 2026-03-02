"""
Real-time Monitoring & Alerts
Track open positions, prices, signals
"""

import logging
from typing import Dict
from datetime import datetime
from config import *

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


class Monitor:
    """Real-time trading monitor"""
    
    def __init__(self):
        self.active_trades = {}
        self.alerts = []
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0
        }
    
    def log_trade_open(self, token_mint: str, amount_sol: float, entry_price: float,
                       confidence: float):
        """Log a new trade"""
        self.active_trades[token_mint] = {
            'opened_at': datetime.now().isoformat(),
            'amount_sol': amount_sol,
            'entry_price': entry_price,
            'confidence': confidence,
            'status': 'open'
        }
        
        logger.info(f"🟢 TRADE OPENED: {token_mint}")
        logger.info(f"   Amount: {amount_sol} SOL @ {entry_price}")
        logger.info(f"   Confidence: {confidence:.2f}%")
    
    def log_trade_close(self, token_mint: str, exit_price: float, pnl_percent: float,
                        reason: str):
        """Log trade closure"""
        if token_mint in self.active_trades:
            self.active_trades[token_mint]['status'] = 'closed'
        
        if pnl_percent > 0:
            logger.info(f"🟢 PROFIT: {token_mint} +{pnl_percent:.2f}% - {reason}")
            self.performance_metrics['winning_trades'] += 1
        else:
            logger.warning(f"🔴 LOSS: {token_mint} {pnl_percent:.2f}% - {reason}")
            self.performance_metrics['losing_trades'] += 1
        
        self.performance_metrics['total_trades'] += 1
    
    def log_alert(self, level: str, message: str):
        """Log alert"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.alerts.append(alert)
        
        if level == 'CRITICAL':
            logger.critical(f"🚨 {message}")
        elif level == 'WARNING':
            logger.warning(f"⚠️ {message}")
        else:
            logger.info(f"ℹ️ {message}")
    
    def get_performance_summary(self) -> Dict:
        """Get performance statistics"""
        total = self.performance_metrics['total_trades']
        win_rate = (self.performance_metrics['winning_trades'] / total * 100) if total > 0 else 0
        
        return {
            'total_trades': total,
            'winning_trades': self.performance_metrics['winning_trades'],
            'losing_trades': self.performance_metrics['losing_trades'],
            'win_rate': f"{win_rate:.2f}%",
            'avg_pnl': f"{self.performance_metrics['total_pnl'] / total:.2f}%" if total > 0 else "0%"
          }
