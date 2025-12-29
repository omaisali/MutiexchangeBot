"""
Trading Bot Dashboard
Web interface for managing API keys, exchanges, and trading settings
"""

import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets

logger = logging.getLogger(__name__)


class Dashboard:
    """Trading Bot Dashboard"""
    
    def __init__(self, config_file: str = 'dashboard_config.json'):
        """
        Initialize Dashboard
        
        Args:
            config_file: Path to configuration file
        """
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        self.config_file = config_file
        self.secret_key = os.getenv('DASHBOARD_SECRET_KEY', secrets.token_hex(32))
        self.app.secret_key = self.secret_key
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize demo mode (enabled by default for client demonstration)
        from demo_mode import DemoMode
        self.demo_mode = DemoMode()
        # Don't enable here - will be enabled in main_with_dashboard with signal_monitor
        logger.info("🎮 Demo mode initialized")
        
        # Setup routes
        self._setup_routes()
    
    def _load_config(self) -> dict:
        """Load configuration from file"""
        default_config = {
            'exchanges': {
                'mexc': {
                    'enabled': False,
                    'api_key': '',
                    'api_secret': '',
                    'base_url': 'https://api.mexc.com',
                    'name': 'MEXC',
                    'paper_trading': False,
                    'sub_account_id': '',  # Optional sub-account ID
                    'use_sub_account': False
                }
            },
            'trading_settings': {
                'position_size_percent': 20.0,  # Configurable 20-100%
                'position_size_fixed': '',
                'use_percentage': True,
                'webhook_port': 5000,
                'webhook_host': '0.0.0.0',
                'warn_existing_positions': True
            },
            'risk_management': {
                'stop_loss_percent': 5.0
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    # Merge with defaults
                    default_config.update(loaded_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            """Dashboard home page"""
            return render_template('dashboard.html', config=self.config)
        
        @self.app.route('/api/exchanges', methods=['GET'])
        def get_exchanges():
            """Get all exchange configurations"""
            return jsonify(self.config['exchanges'])
        
        @self.app.route('/api/exchanges/<exchange_name>', methods=['GET'])
        def get_exchange(exchange_name):
            """Get specific exchange configuration"""
            if exchange_name in self.config['exchanges']:
                exchange_config = self.config['exchanges'][exchange_name].copy()
                # Don't return secrets in GET request
                exchange_config['api_secret'] = '***' if exchange_config.get('api_secret') else ''
                return jsonify(exchange_config)
            return jsonify({'error': 'Exchange not found'}), 404
        
        @self.app.route('/api/exchanges/<exchange_name>', methods=['POST'])
        def update_exchange(exchange_name):
            """Update exchange configuration"""
            if exchange_name not in self.config['exchanges']:
                return jsonify({'error': 'Exchange not found'}), 404
            
            data = request.get_json()
            
            # Update exchange configuration
            exchange = self.config['exchanges'][exchange_name]
            
            # Only update if new values provided (don't overwrite with empty strings)
            if 'enabled' in data:
                exchange['enabled'] = bool(data['enabled'])
            
            if 'api_key' in data and data['api_key']:
                exchange['api_key'] = data['api_key']
            
            if 'api_secret' in data and data['api_secret']:
                # Only update if not masked
                if data['api_secret'] != '***':
                    exchange['api_secret'] = data['api_secret']
            
            if 'base_url' in data:
                exchange['base_url'] = data['base_url']
            
            if 'paper_trading' in data:
                exchange['paper_trading'] = bool(data['paper_trading'])
            
            if 'sub_account_id' in data:
                exchange['sub_account_id'] = data['sub_account_id']
            
            if 'use_sub_account' in data:
                exchange['use_sub_account'] = bool(data['use_sub_account'])
            
            # Save configuration
            if self._save_config():
                return jsonify({'status': 'success', 'message': 'Exchange updated successfully'})
            else:
                return jsonify({'error': 'Failed to save configuration'}), 500
        
        @self.app.route('/api/exchanges/<exchange_name>/toggle', methods=['POST'])
        def toggle_exchange(exchange_name):
            """Enable/disable exchange"""
            if exchange_name not in self.config['exchanges']:
                return jsonify({'error': 'Exchange not found'}), 404
            
            data = request.get_json()
            enabled = data.get('enabled', False)
            
            self.config['exchanges'][exchange_name]['enabled'] = enabled
            
            if self._save_config():
                return jsonify({
                    'status': 'success',
                    'message': f"Exchange {'enabled' if enabled else 'disabled'} successfully",
                    'enabled': enabled
                })
            else:
                return jsonify({'error': 'Failed to save configuration'}), 500
        
        @self.app.route('/api/trading-settings', methods=['GET'])
        def get_trading_settings():
            """Get trading settings"""
            return jsonify(self.config['trading_settings'])
        
        @self.app.route('/api/trading-settings', methods=['POST'])
        def update_trading_settings():
            """Update trading settings"""
            data = request.get_json()
            
            # Update trading settings
            for key, value in data.items():
                if key in self.config['trading_settings']:
                    # Convert string numbers to float/int
                    if key == 'position_size_percent':
                        try:
                            # Ensure position size is between 20-100%
                            position_size = float(value) if value else 20.0
                            self.config['trading_settings'][key] = max(20.0, min(100.0, position_size))
                        except ValueError:
                            pass
                    elif key == 'position_size_fixed':
                        try:
                            self.config['trading_settings'][key] = float(value) if value else ''
                        except ValueError:
                            pass
                    elif key == 'use_percentage':
                        self.config['trading_settings'][key] = bool(value)
                    else:
                        self.config['trading_settings'][key] = value
            
            if self._save_config():
                return jsonify({'status': 'success', 'message': 'Trading settings updated successfully'})
            else:
                return jsonify({'error': 'Failed to save configuration'}), 500
        
        @self.app.route('/api/risk-management', methods=['GET'])
        def get_risk_management():
            """Get risk management settings"""
            return jsonify(self.config['risk_management'])
        
        @self.app.route('/api/risk-management', methods=['POST'])
        def update_risk_management():
            """Update risk management settings"""
            data = request.get_json()
            
            # Update risk management settings
            for key, value in data.items():
                if key in self.config['risk_management']:
                    try:
                        self.config['risk_management'][key] = float(value)
                    except ValueError:
                        pass
            
            if self._save_config():
                return jsonify({'status': 'success', 'message': 'Risk management settings updated successfully'})
            else:
                return jsonify({'error': 'Failed to save configuration'}), 500
        
        @self.app.route('/api/exchanges/status', methods=['GET'])
        def get_exchanges_status():
            """Get connection status and balances for all exchanges"""
            status = {}
            
            # Check if demo mode is active
            if self.demo_mode.is_active():
                # Return demo data for MEXC
                demo_status = self.demo_mode.get_demo_connection_status()
                demo_balances = self.demo_mode.get_demo_balances()
                
                status['mexc'] = {
                    'name': 'MEXC',
                    'enabled': True,
                    'connected': demo_status['connected'],
                    'can_trade': demo_status['can_trade'],
                    'balances': demo_balances,
                    'demo_mode': True
                }
                return jsonify(status)
            
            # Filter out Alpaca (removed from supported exchanges)
            for exchange_name, exchange_config in self.config['exchanges'].items():
                if exchange_name == 'alpaca':
                    continue  # Skip Alpaca
                exchange_status = {
                    'name': exchange_config.get('name', exchange_name),
                    'enabled': exchange_config.get('enabled', False),
                    'connected': False,
                    'can_trade': False,
                    'balances': {}
                }
                
                # Only check if API keys are configured
                if exchange_config.get('api_key') and exchange_config.get('api_secret'):
                    try:
                        if exchange_name == 'mexc':
                            from mexc_client import MEXCClient
                            try:
                                client = MEXCClient(
                                    api_key=exchange_config['api_key'],
                                    api_secret=exchange_config['api_secret'],
                                    base_url=exchange_config.get('base_url', 'https://api.mexc.com'),
                                    sub_account_id=exchange_config.get('sub_account_id', ''),
                                    use_sub_account=exchange_config.get('use_sub_account', False)
                                )
                                validation = client.validate_connection()
                                exchange_status['connected'] = validation['connected']
                                exchange_status['can_trade'] = validation['can_trade']
                                if validation['connected']:
                                    exchange_status['balances'] = client.get_main_balances()
                                # Don't set error message - UI will just show "Not connected"
                            except Exception as e:
                                logger.error(f"Error validating MEXC connection: {e}", exc_info=True)
                                exchange_status['connected'] = False
                                # Don't set error message - UI will just show "Not connected"
                        else:
                            # Don't set error message - UI will just show "Not connected"
                            pass
                    except Exception as e:
                        logger.error(f"Error checking {exchange_name}: {e}")
                        # Don't set error message - UI will just show "Not connected"
                else:
                    # Don't set error message - UI will just show "Not connected"
                    pass
                
                status[exchange_name] = exchange_status
            
            return jsonify(status)
        
        @self.app.route('/api/test-connection/<exchange_name>', methods=['POST'])
        def test_connection(exchange_name):
            """Test exchange API connection"""
            if exchange_name not in self.config['exchanges']:
                return jsonify({'error': 'Exchange not found'}), 404
            
            exchange = self.config['exchanges'][exchange_name]
            
            if not exchange.get('api_key') or not exchange.get('api_secret'):
                return jsonify({'error': 'API credentials not configured'}), 400
            
            try:
                if exchange_name == 'mexc':
                    from mexc_client import MEXCClient
                    client = MEXCClient(
                        api_key=exchange['api_key'],
                        api_secret=exchange['api_secret'],
                        base_url=exchange['base_url']
                    )
                    validation = client.validate_connection()
                    if validation['connected']:
                        return jsonify({
                            'status': 'success',
                            'message': 'Connection successful',
                            'can_trade': validation['can_trade'],
                            'balances': client.get_main_balances()
                        })
                    else:
                        return jsonify({
                            'status': 'error',
                            'error': validation.get('error', 'Connection failed')
                        }), 500
                else:
                    return jsonify({'error': 'Exchange not supported'}), 400
                    
            except Exception as e:
                logger.error(f"Connection test failed: {e}")
                return jsonify({
                    'error': 'Connection failed',
                    'message': str(e)
                }), 500
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Get bot status"""
            if self.demo_mode.is_active():
                demo_stats = self.demo_mode.get_demo_stats()
                return jsonify({
                    'exchanges_enabled': ['mexc'],
                    'total_exchanges': 1,
                    'position_size': self.config['trading_settings'].get('position_size_percent', 0),
                    'demo_mode': True,
                    'demo_stats': demo_stats
                })
            
            enabled_exchanges = [
                name for name, config in self.config['exchanges'].items()
                if config.get('enabled', False) and name != 'alpaca'
            ]
            
            return jsonify({
                'exchanges_enabled': enabled_exchanges,
                'total_exchanges': len([k for k in self.config['exchanges'].keys() if k != 'alpaca']),
                'position_size': self.config['trading_settings'].get('position_size_percent', 0),
                'demo_mode': False
            })
        
        @self.app.route('/api/demo/trades', methods=['GET'])
        def get_demo_trades():
            """Get demo trades"""
            limit = request.args.get('limit', 10, type=int)
            trades = self.demo_mode.get_demo_trades(limit)
            return jsonify({'trades': trades, 'demo_mode': True})
        
        @self.app.route('/api/demo/positions', methods=['GET'])
        def get_demo_positions():
            """Get demo positions"""
            positions = self.demo_mode.get_demo_positions()
            return jsonify({'positions': positions, 'demo_mode': True})
        
        @self.app.route('/api/demo/stats', methods=['GET'])
        def get_demo_stats():
            """Get demo statistics"""
            stats = self.demo_mode.get_demo_stats()
            return jsonify({'stats': stats, 'demo_mode': True})
        
        @self.app.route('/api/demo/toggle', methods=['POST'])
        def toggle_demo_mode():
            """Toggle demo mode on/off"""
            data = request.get_json() or {}
            enable = data.get('enable', True)
            
            if enable:
                self.demo_mode.enable()
                return jsonify({'status': 'success', 'message': 'Demo mode enabled', 'demo_mode': True})
            else:
                self.demo_mode.disable()
                return jsonify({'status': 'success', 'message': 'Demo mode disabled', 'demo_mode': False})
        
        @self.app.route('/api/signals/status', methods=['GET'])
        def signals_status():
            """Get signal monitoring status (proxy to webhook handler)"""
            # In demo mode, get status directly from signal_monitor if available
            if self.demo_mode.is_active() and hasattr(self, 'signal_monitor') and self.signal_monitor:
                status = self.signal_monitor.get_status()
                # Ensure webhook shows as connected in demo mode
                status['webhook_status'] = 'connected'
                return jsonify(status), 200
            
            try:
                import requests
                webhook_port = self.config['trading_settings'].get('webhook_port', 5000)
                response = requests.get(f'http://localhost:{webhook_port}/api/signals/status', timeout=2)
                if response.status_code == 200:
                    status = response.json()
                    # In demo mode, ensure webhook shows as connected
                    if self.demo_mode.is_active() and status.get('webhook_status') != 'connected':
                        status['webhook_status'] = 'connected'
                    return jsonify(status), 200
                else:
                    # In demo mode, return demo status
                    if self.demo_mode.is_active():
                        if hasattr(self, 'signal_monitor') and self.signal_monitor:
                            status = self.signal_monitor.get_status()
                            status['webhook_status'] = 'connected'
                            return jsonify(status), 200
                        return jsonify({
                            'webhook_status': 'connected',
                            'last_signal_time': time.time(),
                            'last_signal_datetime': datetime.now().isoformat(),
                            'time_since_last_signal': 0,
                            'total_signals': 10,
                            'successful_trades': 10,
                            'failed_trades': 0,
                            'recent_signals_count': 10
                        }), 200
                    return jsonify({
                        'webhook_status': 'disconnected',
                        'error': 'Webhook server not responding'
                    }), 200
            except Exception as e:
                # In demo mode, return demo status even if webhook is not accessible
                if self.demo_mode.is_active():
                    # Try to get from signal_monitor if available
                    if hasattr(self, 'signal_monitor') and self.signal_monitor:
                        status = self.signal_monitor.get_status()
                        status['webhook_status'] = 'connected'
                        return jsonify(status), 200
                    return jsonify({
                        'webhook_status': 'connected',
                        'last_signal_time': time.time(),
                        'last_signal_datetime': datetime.now().isoformat(),
                        'time_since_last_signal': 0,
                        'total_signals': 10,
                        'successful_trades': 10,
                        'failed_trades': 0,
                        'recent_signals_count': 10
                    }), 200
                return jsonify({
                    'webhook_status': 'disconnected',
                    'error': 'Webhook server not available'
                }), 200
        
        @self.app.route('/api/signals/recent', methods=['GET'])
        def recent_signals():
            """Get recent signals (proxy to webhook handler)"""
            # In demo mode, get signals directly from signal_monitor if available
            if self.demo_mode.is_active() and hasattr(self, 'signal_monitor'):
                limit = request.args.get('limit', 10, type=int)
                signals = self.signal_monitor.get_recent_signals(limit)
                return jsonify({'signals': signals}), 200
            
            try:
                import requests
                webhook_port = self.config['trading_settings'].get('webhook_port', 5000)
                limit = request.args.get('limit', 10, type=int)
                response = requests.get(f'http://localhost:{webhook_port}/api/signals/recent?limit={limit}', timeout=2)
                if response.status_code == 200:
                    return jsonify(response.json()), 200
                else:
                    # In demo mode, return empty if webhook not accessible (will be populated by demo signals)
                    return jsonify({'signals': []}), 200
            except Exception as e:
                # In demo mode, return empty if webhook not accessible (will be populated by demo signals)
                return jsonify({'signals': []}), 200
    
    def run(self, host: str = '0.0.0.0', port: int = 8080, debug: bool = False):
        """
        Run the dashboard server
        
        Args:
            host: Host to bind to
            port: Port to listen on
            debug: Enable debug mode
        """
        logger.info(f"Starting dashboard on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

