"""
Take Profit and Stop Loss Manager
Handles TP levels and stop-loss management according to requirements
Supports multiple exchanges

NOTE: MEXC Spot API does NOT support stop-loss orders.
We use a monitoring system to check prices and execute stop-loss manually.
Alpaca supports native stop-loss orders via API.
"""

import logging
import time
from typing import Dict, Optional, Union
from position_manager import PositionManager

logger = logging.getLogger(__name__)


class TPSLManager:
    """Manages Take Profit and Stop Loss orders"""
    
    # TP Configuration (from requirements)
    TP_CONFIG = {
        'tp1': {'percent': 1.0, 'close_percent': 10.0},   # 1% from entry, close 10% (90% remaining)
        'tp2': {'percent': 2.0, 'close_percent': 15.0},   # 2% from entry, close 15% (75% remaining)
        'tp3': {'percent': 5.0, 'close_percent': 35.0},   # 5% from entry, close 35% (40% remaining)
        'tp4': {'percent': 6.5, 'close_percent': 35.0},   # 6.5% from entry, close 35% (5% remaining)
        'tp5': {'percent': 8.0, 'close_percent': 50.0}    # 8% from entry, close 50% of remaining (2.5% runner)
    }
    
    def __init__(self, exchange_client: Union[object], position_manager: PositionManager, 
                 stop_loss_percent: float = 5.0, exchange_name: str = 'mexc'):
        """
        Initialize TP/SL Manager
        
        Args:
            exchange_client: Exchange API client instance (MEXCClient, AlpacaClient, etc.)
            position_manager: Position manager instance
            stop_loss_percent: Initial stop loss percentage (default: 5%)
            exchange_name: Name of the exchange ('mexc', 'alpaca', etc.)
        """
        self.client = exchange_client
        self.position_manager = position_manager
        self.stop_loss_percent = stop_loss_percent
        self.exchange_name = exchange_name.lower()
        self.stop_loss_monitor = None  # Will be set by TradingExecutor
    
    def calculate_tp_price(self, entry_price: float, tp_level: str, side: str) -> float:
        """
        Calculate take-profit price
        
        Args:
            entry_price: Entry price
            tp_level: TP level (tp1, tp2, etc.)
            side: 'BUY' or 'SELL'
            
        Returns:
            Take-profit price
        """
        tp_config = self.TP_CONFIG.get(tp_level, {})
        tp_percent = tp_config.get('percent', 0)
        
        if side.upper() == 'BUY':
            return entry_price * (1 + tp_percent / 100.0)
        else:  # SELL
            return entry_price * (1 - tp_percent / 100.0)
    
    def calculate_sl_price(self, entry_price: float, side: str) -> float:
        """
        Calculate stop-loss price
        
        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            
        Returns:
            Stop-loss price
        """
        if side.upper() == 'BUY':
            return entry_price * (1 - self.stop_loss_percent / 100.0)
        else:  # SELL
            return entry_price * (1 + self.stop_loss_percent / 100.0)
    
    def calculate_close_quantity(self, initial_quantity: float, tp_level: str, 
                                 remaining_quantity: float) -> float:
        """
        Calculate quantity to close for TP level
        
        Args:
            initial_quantity: Initial position quantity
            tp_level: TP level (tp1, tp2, etc.)
            remaining_quantity: Current remaining quantity
            
        Returns:
            Quantity to close
        """
        tp_config = self.TP_CONFIG.get(tp_level, {})
        
        if tp_level == 'tp5':
            # TP5: Close 50% of remaining
            return remaining_quantity * 0.5
        else:
            # TP1-TP4: Close percentage of initial quantity
            close_percent = tp_config.get('close_percent', 0)
            return initial_quantity * (close_percent / 100.0)
    
    def place_initial_stop_loss(self, symbol: str, entry_price: float, 
                                side: str, quantity: float) -> Optional[str]:
        """
        Set initial stop-loss price (5% from entry)
        
        NOTE: MEXC Spot API does NOT support stop-loss orders.
        We store the stop-loss price and the monitoring system will execute it.
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            quantity: Position quantity
            
        Returns:
            Stop-loss "order ID" (actually just a marker, not a real order)
        """
        try:
            sl_price = self.calculate_sl_price(entry_price, side)
            
            logger.info(f"Setting initial stop-loss: {symbol} @ {sl_price} ({self.stop_loss_percent}% from entry)")
            logger.warning("⚠️  MEXC Spot API doesn't support stop-loss orders. Using price monitoring instead.")
            
            # Store stop-loss price in position (monitoring system will execute)
            position = self.position_manager.get_position(symbol)
            if position:
                position['stop_loss_price'] = sl_price
                position['stop_loss_order_id'] = 'MONITORED'  # Marker, not real order
            
            # Return a marker ID (not a real order ID)
            return 'MONITORED'
                
        except Exception as e:
            logger.error(f"Error setting stop-loss: {e}", exc_info=True)
            return None
    
    def move_stop_loss_to_entry(self, symbol: str, entry_price: float, 
                                side: str, current_sl_order_id: Optional[str]) -> Optional[str]:
        """
        Move stop-loss to entry price (CRITICAL: Must happen after TP1)
        
        NOTE: MEXC Spot API doesn't support stop-loss orders.
        We update the stop-loss price in the position, and the monitoring system will execute it.
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            current_sl_order_id: Current stop-loss order ID (ignored for Spot)
            
        Returns:
            Stop-loss marker ID
        """
        try:
            # Get remaining position quantity
            position = self.position_manager.get_position(symbol)
            if not position:
                logger.error(f"No active position found for {symbol}")
                return None
            
            # Update stop-loss price to entry (breakeven)
            logger.info(f"⚠️  CRITICAL: Moving stop-loss to entry price: {symbol} @ {entry_price}")
            position['stop_loss_price'] = entry_price
            position['stop_loss_order_id'] = 'MONITORED'
            self.position_manager.mark_stop_loss_moved(symbol)
            
            # Update monitoring system
            if self.stop_loss_monitor:
                self.stop_loss_monitor.update_stop_loss_price(symbol, entry_price)
            
            logger.info(f"✅ Stop-loss price updated to entry: {entry_price}")
            logger.warning("⚠️  Stop-loss is monitored (MEXC Spot doesn't support stop-loss orders)")
            
            return 'MONITORED'
                
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR moving stop-loss to entry: {e}", exc_info=True)
            raise Exception("CRITICAL: Cannot move stop-loss to entry - project requirement failed")
    
    def place_take_profit_orders(self, symbol: str, entry_price: float, 
                                 side: str, initial_quantity: float) -> Dict[str, str]:
        """
        Place all take-profit limit orders (TP1-TP5)
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            side: 'BUY' or 'SELL'
            initial_quantity: Initial position quantity
            
        Returns:
            Dictionary of TP level -> order ID
        """
        tp_orders = {}
        position = self.position_manager.get_position(symbol)
        
        if not position:
            logger.error(f"No position found for {symbol}")
            return tp_orders
        
        for tp_level in ['tp1', 'tp2', 'tp3', 'tp4', 'tp5']:
            try:
                tp_price = self.calculate_tp_price(entry_price, tp_level, side)
                
                # Calculate quantity to close
                if tp_level == 'tp5':
                    # TP5 uses remaining quantity at that point
                    # We'll calculate based on expected remaining after TP4
                    remaining_after_tp4 = initial_quantity * 0.05  # 5% remaining after TP4
                    close_qty = remaining_after_tp4 * 0.5  # Close 50% of remaining
                else:
                    close_qty = self.calculate_close_quantity(initial_quantity, tp_level, initial_quantity)
                
                # Place limit order for take-profit
                tp_side = 'SELL' if side.upper() == 'BUY' else 'BUY'
                
                logger.info(f"Placing {tp_level}: {symbol} @ {tp_price}, Qty: {close_qty}")
                response = self.client.place_order(
                    symbol=symbol,
                    side=tp_side,
                    order_type='LIMIT',
                    quantity=close_qty,
                    price=tp_price
                )
                
                if response and 'orderId' in response:
                    order_id = str(response['orderId'])
                    tp_orders[tp_level] = order_id
                    position['tp_orders'][tp_level] = order_id
                    logger.info(f"{tp_level} order placed: {order_id}")
                else:
                    logger.warning(f"Failed to place {tp_level}: {response}")
                    
            except Exception as e:
                logger.error(f"Error placing {tp_level}: {e}")
        
        return tp_orders
    
    def check_and_handle_tp1(self, symbol: str) -> bool:
        """
        Check if TP1 has been hit and move stop-loss to entry (CRITICAL)
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if TP1 hit and stop-loss moved, False otherwise
        """
        position = self.position_manager.get_position(symbol)
        if not position:
            return False
        
        # Check if TP1 already hit
        if position['tp_hit']['tp1']:
            return True
        
        # Check if TP1 order has been filled
        tp1_order_id = position['tp_orders'].get('tp1')
        if not tp1_order_id:
            return False
        
        try:
            order_status = self.client.get_order_status(symbol, tp1_order_id)
            
            if order_status.get('status') == 'FILLED':
                logger.info(f"✅ TP1 FILLED for {symbol} - Moving stop-loss to entry (CRITICAL)")
                
                # CRITICAL: Move stop-loss to entry price
                new_sl_order_id = self.move_stop_loss_to_entry(
                    symbol,
                    position['entry_price'],
                    position['side'],
                    position['stop_loss_order_id']
                )
                
                if new_sl_order_id:
                    position['stop_loss_order_id'] = new_sl_order_id
                    position['tp_hit']['tp1'] = True
                    self.position_manager.mark_tp_hit(symbol, 'tp1')
                    
                    # Update stop-loss price in monitoring system
                    # (Since we're using Spot API, we update the monitored price)
                    from stop_loss_monitor import StopLossMonitor
                    # Note: StopLossMonitor is initialized in TradingExecutor
                    # The price is already updated in move_stop_loss_to_entry
                    
                    # Update remaining quantity
                    tp1_close_qty = self.calculate_close_quantity(
                        position['initial_quantity'],
                        'tp1',
                        position['remaining_quantity']
                    )
                    self.position_manager.update_position_quantity(symbol, tp1_close_qty)
                    
                    return True
                else:
                    raise Exception("CRITICAL: Failed to move stop-loss to entry after TP1")
                    
        except Exception as e:
            logger.error(f"Error checking TP1: {e}")
            raise
        
        return False

