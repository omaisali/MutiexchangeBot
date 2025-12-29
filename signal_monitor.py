"""
Signal Monitor
Tracks TradingView webhook signals and connection status
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import deque
import threading

class SignalMonitor:
    """Monitors TradingView webhook signals"""
    
    def __init__(self, max_signals: int = 100):
        """
        Initialize Signal Monitor
        
        Args:
            max_signals: Maximum number of signals to keep in history
        """
        self.max_signals = max_signals
        self.signals = deque(maxlen=max_signals)
        self.last_signal_time = None
        self.last_signal_data = None
        self.total_signals = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.lock = threading.Lock()
        self.webhook_connected = False
        self.webhook_last_ping = None
        
    def add_signal(self, signal_data: Dict, executed: bool = False, error: Optional[str] = None):
        """
        Add a signal to the monitor
        
        Args:
            signal_data: Signal data from TradingView
            executed: Whether the trade was executed successfully
            error: Error message if execution failed
        """
        with self.lock:
            # Handle price as dict or direct value
            price_value = 0
            if isinstance(signal_data.get('price'), dict):
                price_value = signal_data.get('price', {}).get('close', 0)
            elif signal_data.get('price'):
                price_value = float(signal_data.get('price', 0))
            
            signal_record = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'symbol': signal_data.get('symbol', ''),
                'signal': signal_data.get('signal', ''),
                'price': price_value,
                'executed': executed,
                'error': error,
                'indicators': signal_data.get('indicators', {})
            }
            
            self.signals.append(signal_record)
            self.last_signal_time = time.time()
            self.last_signal_data = signal_record
            self.total_signals += 1
            
            if executed:
                self.successful_trades += 1
            elif error:
                self.failed_trades += 1
    
    def get_recent_signals(self, limit: int = 10) -> List[Dict]:
        """
        Get recent signals
        
        Args:
            limit: Number of recent signals to return
            
        Returns:
            List of recent signal records
        """
        with self.lock:
            return list(self.signals)[-limit:]
    
    def get_status(self) -> Dict:
        """
        Get current monitoring status
        
        Returns:
            Status dictionary
        """
        with self.lock:
            time_since_last = None
            if self.last_signal_time:
                time_since_last = time.time() - self.last_signal_time
            
            webhook_status = 'connected' if self.webhook_connected else 'disconnected'
            if self.webhook_last_ping:
                ping_age = time.time() - self.webhook_last_ping
                if ping_age > 300:  # 5 minutes
                    webhook_status = 'disconnected'
            
            return {
                'webhook_status': webhook_status,
                'last_signal_time': self.last_signal_time,
                'last_signal_datetime': self.last_signal_data['datetime'] if self.last_signal_data else None,
                'time_since_last_signal': time_since_last,
                'total_signals': self.total_signals,
                'successful_trades': self.successful_trades,
                'failed_trades': self.failed_trades,
                'recent_signals_count': len(self.signals),
                'last_signal': self.last_signal_data
            }
    
    def ping_webhook(self):
        """Mark webhook as active (called periodically)"""
        with self.lock:
            self.webhook_connected = True
            self.webhook_last_ping = time.time()
    
    def mark_webhook_disconnected(self):
        """Mark webhook as disconnected"""
        with self.lock:
            self.webhook_connected = False

