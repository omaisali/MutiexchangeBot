"""
Alpaca Markets API Client
Handles authentication, order placement, and account management for Alpaca
"""

import requests
import json
from typing import Dict, Optional, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AlpacaClient:
    """Alpaca Markets API Client"""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://paper-api.alpaca.markets"):
        """
        Initialize Alpaca API Client
        
        Args:
            api_key: Alpaca API Key ID
            api_secret: Alpaca API Secret Key
            base_url: Alpaca API base URL
                - Paper: https://paper-api.alpaca.markets
                - Live: https://api.alpaca.markets
        """
        # Trim whitespace to prevent errors
        self.api_key = api_key.strip() if api_key else ''
        self.api_secret = api_secret.strip() if api_secret else ''
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        
        # Set default headers for all requests
        self.session.headers.update({
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.api_secret,
            'Content-Type': 'application/json'
        })
        
        # Log loaded keys (masked) for verification
        if self.api_key:
            masked_key = f"{self.api_key[:6]}...{self.api_key[-4:]}" if len(self.api_key) > 10 else "***"
            logger.info(f"🔑 Loaded Alpaca API Key: {masked_key} (length: {len(self.api_key)})")
        if self.api_secret:
            masked_secret = f"{self.api_secret[:6]}...{self.api_secret[-4:]}" if len(self.api_secret) > 10 else "***"
            logger.info(f"🔑 Loaded Alpaca API Secret: {masked_secret} (length: {len(self.api_secret)})")
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict:
        """
        Make authenticated API request
        
        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint (e.g., '/v2/account')
            params: Query parameters
            data: Request body data
            
        Returns:
            Response JSON as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, timeout=10)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=params, json=data, timeout=10)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            try:
                error_data = e.response.json()
                error_msg = error_data.get('message', error_data.get('error', error_msg))
            except:
                error_msg = str(e)
            
            logger.error(f"Alpaca API Error: {error_msg}")
            raise Exception(f"Alpaca API Error: {error_msg}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            raise Exception(f"Request error: {e}")
    
    def validate_connection(self) -> Dict:
        """
        Validate API connection and permissions
        
        Returns:
            Dictionary with 'connected' and 'can_trade' status
        """
        try:
            account = self._make_request('GET', '/v2/account')
            
            # Check if account is active and trading is allowed
            trading_blocked = account.get('trading_blocked', False)
            account_blocked = account.get('account_blocked', False)
            pattern_day_trader = account.get('pattern_day_trader', False)
            
            can_trade = not trading_blocked and not account_blocked
            
            return {
                'connected': True,
                'can_trade': can_trade,
                'account_status': {
                    'trading_blocked': trading_blocked,
                    'account_blocked': account_blocked,
                    'pattern_day_trader': pattern_day_trader
                }
            }
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return {
                'connected': False,
                'can_trade': False,
                'error': str(e)
            }
    
    def get_account_info(self) -> Dict:
        """
        Get account information
        
        Returns:
            Account information dictionary
        """
        return self._make_request('GET', '/v2/account')
    
    def get_balance(self, asset: str = 'USD') -> Dict:
        """
        Get balance for a specific asset
        
        Args:
            asset: Asset symbol (default: 'USD' for cash)
            
        Returns:
            Balance information
        """
        account = self.get_account_info()
        
        if asset.upper() == 'USD':
            return {
                'asset': 'USD',
                'free': float(account.get('cash', 0)),
                'locked': float(account.get('cash', 0)) - float(account.get('buying_power', 0)),
                'total': float(account.get('cash', 0))
            }
        else:
            # For positions, get from positions endpoint
            positions = self.get_positions()
            for pos in positions:
                if pos['symbol'] == asset:
                    return {
                        'asset': asset,
                        'free': float(pos.get('qty', 0)),
                        'locked': 0.0,
                        'total': float(pos.get('qty', 0))
                    }
            
            return {
                'asset': asset,
                'free': 0.0,
                'locked': 0.0,
                'total': 0.0
            }
    
    def get_main_balances(self) -> Dict:
        """
        Get main account balances (cash and positions)
        
        Returns:
            Dictionary of asset balances
        """
        balances = {}
        
        try:
            account = self.get_account_info()
            
            # Add cash balance
            cash = float(account.get('cash', 0))
            if cash > 0:
                balances['USD'] = {
                    'free': cash,
                    'locked': cash - float(account.get('buying_power', 0)),
                    'total': cash
                }
            
            # Add position balances
            positions = self.get_positions()
            for pos in positions:
                symbol = pos['symbol']
                qty = float(pos.get('qty', 0))
                if qty > 0:
                    balances[symbol] = {
                        'free': abs(qty),
                        'locked': 0.0,
                        'total': abs(qty)
                    }
            
        except Exception as e:
            logger.error(f"Error getting balances: {e}")
        
        return balances
    
    def get_positions(self) -> List[Dict]:
        """
        Get all open positions
        
        Returns:
            List of position dictionaries
        """
        try:
            return self._make_request('GET', '/v2/positions')
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a specific symbol
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            
        Returns:
            Position dictionary or None
        """
        try:
            # Alpaca uses symbol without exchange suffix
            clean_symbol = symbol.replace('USDT', '').replace('USD', '')
            return self._make_request('GET', f'/v2/positions/{clean_symbol}')
        except Exception as e:
            # Position doesn't exist
            return None
    
    def get_ticker_price(self, symbol: str) -> float:
        """
        Get current ticker price
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL' or 'AAPLUSD')
            
        Returns:
            Current price
            
        Note:
            Alpaca Markets API only supports stocks, not crypto.
            For crypto symbols, this will raise an error.
        """
        try:
            # Alpaca uses symbol without exchange suffix
            clean_symbol = symbol.replace('USDT', '').replace('USD', '')
            
            # Check if this looks like a crypto symbol (common crypto tickers)
            crypto_symbols = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI', 'ATOM']
            if clean_symbol.upper() in crypto_symbols:
                raise ValueError(f"Alpaca Markets API does not support crypto trading. Symbol '{symbol}' is a cryptocurrency. Alpaca only supports stocks. Please use a stock exchange (like MEXC) for crypto trading.")
            
            # Get latest trade (stocks only)
            latest_trade = self._make_request('GET', f'/v2/stocks/{clean_symbol}/trades/latest')
            return float(latest_trade.get('p', 0))
        except ValueError:
            # Re-raise ValueError (our custom crypto error)
            raise
        except Exception as e:
            error_msg = str(e)
            # Check if it's a 404 (symbol not found)
            if '404' in error_msg or 'Not Found' in error_msg:
                # Check if it might be crypto
                clean_symbol = symbol.replace('USDT', '').replace('USD', '')
                crypto_symbols = ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'MATIC', 'AVAX', 'LINK', 'UNI', 'ATOM']
                if clean_symbol.upper() in crypto_symbols:
                    raise ValueError(f"Alpaca Markets API does not support crypto trading. Symbol '{symbol}' is a cryptocurrency. Alpaca only supports stocks. Please use a stock exchange (like MEXC) for crypto trading.")
                else:
                    raise ValueError(f"Symbol '{symbol}' not found on Alpaca. Alpaca only supports stocks, not crypto or forex.")
            logger.error(f"Error getting ticker price for {symbol}: {e}")
            # Fallback: try to get from positions
            try:
                position = self.get_position(symbol)
                if position:
                    return float(position.get('current_price', 0))
            except:
                pass
            raise
    
    def place_order(self, symbol: str, side: str, order_type: str,
                   quantity: Optional[float] = None,
                   notional: Optional[float] = None,
                   limit_price: Optional[float] = None,
                   stop_price: Optional[float] = None,
                   time_in_force: str = 'day') -> Dict:
        """
        Place an order
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL')
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', 'stop_limit'
            quantity: Number of shares (for market/limit orders)
            notional: Dollar amount (alternative to quantity for market orders)
            limit_price: Limit price (for limit/stop_limit orders)
            stop_price: Stop price (for stop/stop_limit orders)
            time_in_force: 'day', 'gtc', 'opg', 'cls', 'ioc', 'fok'
            
        Returns:
            Order response
        """
        # Alpaca uses symbol without exchange suffix
        clean_symbol = symbol.replace('USDT', '').replace('USD', '')
        
        order_data = {
            'symbol': clean_symbol,
            'side': side.lower(),
            'type': order_type.lower(),
            'time_in_force': time_in_force.lower()
        }
        
        if order_type.lower() == 'market':
            if notional:
                order_data['notional'] = notional
            elif quantity:
                order_data['qty'] = str(quantity)
            else:
                raise ValueError("Market orders require either quantity or notional")
        elif order_type.lower() == 'limit':
            if not quantity or not limit_price:
                raise ValueError("Limit orders require quantity and limit_price")
            order_data['qty'] = str(quantity)
            order_data['limit_price'] = str(limit_price)
        elif order_type.lower() in ['stop', 'stop_limit']:
            if not quantity or not stop_price:
                raise ValueError("Stop orders require quantity and stop_price")
            order_data['qty'] = str(quantity)
            order_data['stop_price'] = str(stop_price)
            if order_type.lower() == 'stop_limit':
                if not limit_price:
                    raise ValueError("Stop-limit orders require limit_price")
                order_data['limit_price'] = str(limit_price)
        
        logger.info(f"Placing {side} order: {order_data}")
        return self._make_request('POST', '/v2/orders', data=order_data)
    
    def place_market_buy(self, symbol: str, notional: float) -> Dict:
        """
        Place a market buy order
        
        Args:
            symbol: Trading symbol
            notional: Dollar amount to spend
            
        Returns:
            Order response
        """
        return self.place_order(
            symbol=symbol,
            side='buy',
            order_type='market',
            notional=notional
        )
    
    def place_market_sell(self, symbol: str, quantity: float) -> Dict:
        """
        Place a market sell order
        
        Args:
            symbol: Trading symbol
            quantity: Number of shares to sell
            
        Returns:
            Order response
        """
        return self.place_order(
            symbol=symbol,
            side='sell',
            order_type='market',
            quantity=quantity
        )
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, 
                         limit_price: float) -> Dict:
        """
        Place a limit order
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Number of shares
            limit_price: Limit price
            
        Returns:
            Order response
        """
        return self.place_order(
            symbol=symbol,
            side=side,
            order_type='limit',
            quantity=quantity,
            limit_price=limit_price
        )
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """
        Get order status
        
        Args:
            symbol: Trading symbol (not used by Alpaca, but kept for compatibility)
            order_id: Order ID
            
        Returns:
            Order status dictionary
        """
        return self._make_request('GET', f'/v2/orders/{order_id}')
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get open orders
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            clean_symbol = symbol.replace('USDT', '').replace('USD', '')
            params['symbols'] = clean_symbol
        
        return self._make_request('GET', '/v2/orders', params=params)
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        return self._make_request('DELETE', f'/v2/orders/{order_id}')
    
    def cancel_all_orders(self) -> List[Dict]:
        """
        Cancel all open orders
        
        Returns:
            List of cancellation responses
        """
        return self._make_request('DELETE', '/v2/orders')

