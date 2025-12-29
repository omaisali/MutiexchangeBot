"""
Webhook Handler
Receives and processes TradingView webhook alerts
"""

import json
import logging
from typing import Dict, Optional
from flask import Flask, request, jsonify
import jsonschema
from trading_executor import TradingExecutor
from signal_monitor import SignalMonitor

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles TradingView webhook requests"""
    
    def __init__(self, trading_executor: Optional[TradingExecutor] = None, signal_monitor: Optional[SignalMonitor] = None):
        """
        Initialize Webhook Handler
        
        Args:
            trading_executor: TradingExecutor instance (optional for demo mode)
            signal_monitor: Optional SignalMonitor instance
        """
        self.executor = trading_executor
        self.signal_monitor = signal_monitor or SignalMonitor()
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            """Handle TradingView webhook POST requests"""
            try:
                # Mark webhook as connected
                self.signal_monitor.ping_webhook()
                
                # Get request data
                data = request.get_json()
                
                if not data:
                    # Try to parse as form data (TradingView sends form data)
                    data = request.form.to_dict()
                    if 'message' in data:
                        # Parse pipe-delimited message
                        data = self._parse_pipe_message(data)
                
                logger.info(f"Received webhook: {json.dumps(data, indent=2)}")
                
                # Validate and parse signal data
                signal_data = self._parse_signal_data(data)
                
                if not signal_data:
                    error_msg = 'Invalid signal data'
                    self.signal_monitor.add_signal(data if data else {}, executed=False, error=error_msg)
                    return jsonify({'status': 'error', 'message': error_msg}), 400
                
                # Execute trading signal (or simulate in demo mode)
                if self.executor:
                    order_response = self.executor.execute_signal(signal_data)
                    
                    if order_response:
                        self.signal_monitor.add_signal(signal_data, executed=True)
                        return jsonify({
                            'status': 'success',
                            'message': 'Order executed successfully',
                            'order': order_response
                        }), 200
                    else:
                        error_msg = 'Failed to execute order'
                        self.signal_monitor.add_signal(signal_data, executed=False, error=error_msg)
                        return jsonify({
                            'status': 'error',
                            'message': error_msg
                        }), 500
                else:
                    # Demo mode: simulate trade execution
                    from demo_mode import DemoMode
                    demo = DemoMode()
                    if demo.is_active():
                        # Simulate trade execution
                        price = float(signal_data.get('price', 0))
                        symbol = signal_data.get('symbol', 'BTCUSDT')
                        side = signal_data.get('signal', 'BUY')
                        # Estimate quantity based on typical position size
                        quantity = (1000 / price) if price > 0 else 0.01  # Simulate $1000 trade
                        
                        trade = demo.simulate_trade(symbol, side, price, quantity)
                        logger.info(f"🎮 Demo trade simulated: {trade}")
                        self.signal_monitor.add_signal(signal_data, executed=True)
                        return jsonify({
                            'status': 'success',
                            'message': 'Demo trade executed successfully',
                            'order': trade,
                            'demo': True
                        }), 200
                    
                    error_msg = 'No trading executor available'
                    self.signal_monitor.add_signal(signal_data, executed=False, error=error_msg)
                    return jsonify({
                        'status': 'error',
                        'message': error_msg
                    }), 500
                    
            except Exception as e:
                logger.error(f"Webhook error: {e}", exc_info=True)
                error_msg = str(e)
                self.signal_monitor.add_signal(data if 'data' in locals() else {}, executed=False, error=error_msg)
                return jsonify({
                    'status': 'error',
                    'message': error_msg
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            self.signal_monitor.ping_webhook()
            return jsonify({'status': 'healthy'}), 200
        
        @self.app.route('/api/signals/status', methods=['GET'])
        def signals_status():
            """Get signal monitoring status"""
            status = self.signal_monitor.get_status()
            return jsonify(status), 200
        
        @self.app.route('/api/signals/recent', methods=['GET'])
        def recent_signals():
            """Get recent signals"""
            limit = request.args.get('limit', 10, type=int)
            signals = self.signal_monitor.get_recent_signals(limit)
            return jsonify({'signals': signals}), 200
    
    def _parse_pipe_message(self, data: Dict) -> Dict:
        """
        Parse pipe-delimited message from TradingView
        
        Args:
            data: Request data dictionary
            
        Returns:
            Parsed signal data dictionary
        """
        message = data.get('message', '')
        ticker = data.get('ticker', '')
        time_str = data.get('time', '')
        
        # Parse pipe-delimited fields
        fields = {}
        for item in message.split('|'):
            if '=' in item:
                key, value = item.split('=', 1)
                fields[key] = value
        
        # Build signal data structure
        signal_data = {
            'symbol': ticker or fields.get('SYMBOL', ''),
            'time': time_str,
            'timestamp': int(fields.get('TIME', 0)),
            'signal': fields.get('SIGNAL', ''),
            'indicators': {
                'wt': {
                    'flag': fields.get('WT_FLAG', 'false').lower() == 'true',
                    'wt1': float(fields.get('WT1', 0)),
                    'wt2': float(fields.get('WT2', 0)),
                    'cross_type': fields.get('WT_CROSS', 'NONE'),
                    'window_active': fields.get('WT_WINDOW', 'NONE') != 'NONE'
                },
                'bb': {
                    'flag': fields.get('BB_FLAG', 'false').lower() == 'true',
                    'upper': float(fields.get('BB_UPPER', 0)),
                    'lower': float(fields.get('BB_LOWER', 0)),
                    'basis': float(fields.get('BB_BASIS', 0)),
                    'ma_value': float(fields.get('MA_VALUE', 0)),
                    'percent_b': float(fields.get('BB_PERCENT', 0))
                },
                'rsi': {
                    'value': float(fields.get('RSI_VALUE', 0)),
                    'buy_threshold_min': float(fields.get('RSI_BUY_THRESHOLD_MIN', 54.0)),
                    'buy_threshold_max': float(fields.get('RSI_BUY_THRESHOLD_MAX', 82.0)),
                    'sell_threshold_min': float(fields.get('RSI_SELL_THRESHOLD_MIN', 27.0)),
                    'sell_threshold_max': float(fields.get('RSI_SELL_THRESHOLD_MAX', 43.0)),
                    'condition_met': fields.get('RSI_CONDITION', 'false').lower() == 'true'
                }
            },
            'price': {
                'close': float(fields.get('PRICE_CLOSE', 0)),
                'open': float(fields.get('PRICE_OPEN', 0)),
                'high': float(fields.get('PRICE_HIGH', 0)),
                'low': float(fields.get('PRICE_LOW', 0))
            },
            'strategy': {
                'entry_type': fields.get('ENTRY_TYPE', 'NEXT_CANDLE_OPEN'),
                'all_conditions_met': True
            }
        }
        
        return signal_data
    
    def _parse_signal_data(self, data: Dict) -> Optional[Dict]:
        """
        Parse and validate signal data from webhook
        
        Args:
            data: Raw webhook data
            
        Returns:
            Parsed signal data or None if invalid
        """
        # If data is already in JSON format, use it directly
        if 'symbol' in data and 'signal' in data:
            return data
        
        # Otherwise, try to parse from TradingView format
        return self._parse_pipe_message(data)
    
    def run(self, host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
        """
        Run the webhook server
        
        Args:
            host: Host to bind to
            port: Port to listen on
            debug: Enable debug mode
        """
        logger.info(f"Starting webhook server on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

