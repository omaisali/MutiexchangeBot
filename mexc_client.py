"""
MEXC Exchange API Client
Handles authentication, order placement, and account management
"""

import hmac
import hashlib
import time
import requests
import json
from typing import Dict, Optional, List
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)


class MEXCClient:
    """MEXC Exchange API Client"""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://api.mexc.com", 
                 sub_account_id: Optional[str] = None, use_sub_account: bool = False):
        """
        Initialize MEXC API Client
        
        Args:
            api_key: MEXC API Key
            api_secret: MEXC API Secret
            base_url: MEXC API base URL (default: https://api.mexc.com)
            sub_account_id: Optional sub-account ID for sub-account trading
            use_sub_account: Whether to use sub-account for trading
        """
        # Trim whitespace to prevent signature errors (common issue)
        self.api_key = api_key.strip() if api_key else ''
        self.api_secret = api_secret.strip() if api_secret else ''
        self.base_url = base_url.rstrip('/')
        self.sub_account_id = sub_account_id
        self.use_sub_account = use_sub_account
        self.session = requests.Session()
        
    def _generate_signature(self, params: Dict) -> str:
        """
        Generate HMAC-SHA256 signature for authenticated requests
        
        MEXC API signature format:
        1. Sort all parameters alphabetically by key (excluding signature itself)
        2. Create query string: key1=value1&key2=value2
        3. Generate HMAC-SHA256 with API secret
        
        Args:
            params: Request parameters dictionary (should NOT include signature)
            
        Returns:
            Signature string
        """
        # Remove signature if present (shouldn't be, but just in case)
        params_copy = {k: v for k, v in params.items() if k != 'signature'}
        
        # Sort parameters alphabetically by key
        sorted_params = sorted(params_copy.items())
        
        # Create query string: key1=value1&key2=value2
        # Use doseq=False to handle lists correctly
        query_string = urlencode(sorted_params, doseq=False)
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        if logger.level <= logging.DEBUG:
            logger.debug(f"Signature params: {sorted_params}")
            logger.debug(f"Query string: {query_string}")
            logger.debug(f"Signature: {signature}")
        
        return signature
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, 
                     signed: bool = False) -> Dict:
        """
        Make API request to MEXC
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Request parameters
            signed: Whether to include authentication signature
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        
        if signed:
            # Add timestamp and recvWindow
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            
            # Add sub-account ID if using sub-account
            if self.use_sub_account and self.sub_account_id:
                params['subAccountId'] = self.sub_account_id
            
            # Generate signature BEFORE adding it to params
            signature = self._generate_signature(params)
            params['signature'] = signature
            
            # MEXC API uses X-MEXC-APIKEY header
            # Note: Some MEXC API versions might use different header names
            # Try both common variations
            headers = {
                'X-MEXC-APIKEY': self.api_key,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        else:
            headers = {'Content-Type': 'application/json'}
        
        try:
            if method.upper() == 'GET':
                # For GET requests, params go in query string
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method.upper() == 'POST':
                # For POST requests, check if params should be in body or query
                # MEXC typically uses JSON body for POST
                response = self.session.post(url, json=params, headers=headers, timeout=10)
            elif method.upper() == 'DELETE':
                # For DELETE, MEXC might use query params or JSON body
                response = self.session.delete(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            # Get more detailed error information
            error_msg = f"MEXC API request failed: {e}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                    logger.error(f"Error details: {error_detail}")
                    # Extract specific error message if available
                    if isinstance(error_detail, dict):
                        if 'msg' in error_detail:
                            error_msg = f"MEXC API Error: {error_detail['msg']}"
                        elif 'message' in error_detail:
                            error_msg = f"MEXC API Error: {error_detail['message']}"
                        elif 'code' in error_detail:
                            error_msg = f"MEXC API Error Code {error_detail['code']}: {error_detail}"
                except:
                    error_text = e.response.text if hasattr(e.response, 'text') else str(e.response)
                    error_msg += f" - {error_text}"
                    logger.error(f"Response text: {error_text}")
                    logger.error(f"Response status: {e.response.status_code}")
                    logger.error(f"Response headers: {dict(e.response.headers)}")
                    # Try to extract error from text
                    if 'msg' in error_text or 'message' in error_text:
                        error_msg = f"MEXC API Error: {error_text}"
            logger.error(error_msg)
            raise Exception(f"MEXC API Error: {error_msg}")
        except requests.exceptions.RequestException as e:
            logger.error(f"MEXC API request failed: {e}")
            raise
    
    # Account Methods
    
    def get_account_info(self) -> Dict:
        """
        Get account information
        
        Returns:
            Account information dictionary
        """
        return self._make_request('GET', '/api/v3/account', signed=True)
    
    def get_balance(self, asset: Optional[str] = None) -> Dict:
        """
        Get account balance
        
        Args:
            asset: Specific asset symbol (e.g., 'USDT'). If None, returns all balances
            
        Returns:
            Balance information
        """
        account = self.get_account_info()
        balances = account.get('balances', [])
        
        if asset:
            for balance in balances:
                if balance['asset'] == asset:
                    return balance
            return {'asset': asset, 'free': '0.0', 'locked': '0.0'}
        
        return balances
    
    def validate_connection(self) -> Dict:
        """
        Validate API connection and get account info
        
        Returns:
            Dictionary with connection status and account info
        """
        try:
            account_info = self.get_account_info()
            return {
                'connected': True,
                'account': account_info,
                'permissions': account_info.get('permissions', []),
                'can_trade': 'SPOT' in account_info.get('permissions', []),
                'balances': account_info.get('balances', [])
            }
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return {
                'connected': False,
                'error': str(e),
                'account': None,
                'permissions': [],
                'can_trade': False,
                'balances': []
            }
    
    def get_main_balances(self) -> Dict:
        """
        Get main trading balances (USDT, BTC, ETH, etc.)
        
        Returns:
            Dictionary with main asset balances
        """
        try:
            balances = self.get_balance()
            main_assets = ['USDT', 'BTC', 'ETH', 'BNB', 'SOL']
            main_balances = {}
            
            for balance in balances:
                asset = balance.get('asset', '')
                if asset in main_assets:
                    free = float(balance.get('free', 0))
                    locked = float(balance.get('locked', 0))
                    total = free + locked
                    if total > 0:
                        main_balances[asset] = {
                            'free': free,
                            'locked': locked,
                            'total': total
                        }
            
            return main_balances
        except Exception as e:
            logger.error(f"Error getting main balances: {e}")
            return {}
    
    # Market Methods
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        Get trading symbol information
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Symbol information
        """
        params = {'symbol': symbol}
        return self._make_request('GET', '/api/v3/exchangeInfo', params=params)
    
    def get_ticker_price(self, symbol: str) -> float:
        """
        Get current ticker price
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Current price as float
        """
        params = {'symbol': symbol}
        response = self._make_request('GET', '/api/v3/ticker/price', params=params)
        return float(response.get('price', 0))
    
    def get_order_book(self, symbol: str, limit: int = 5) -> Dict:
        """
        Get order book
        
        Args:
            symbol: Trading pair symbol
            limit: Number of orders to return (default: 5)
            
        Returns:
            Order book data
        """
        params = {'symbol': symbol, 'limit': limit}
        return self._make_request('GET', '/api/v3/depth', params=params)
    
    # Trading Methods
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   quantity: Optional[float] = None, price: Optional[float] = None,
                   quote_order_qty: Optional[float] = None, stop_price: Optional[float] = None,
                   limit_price: Optional[float] = None) -> Dict:
        """
        Place a new order
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('MARKET', 'LIMIT', etc.)
            quantity: Order quantity (for MARKET/LIMIT orders)
            price: Order price (for LIMIT orders)
            quote_order_qty: Quote order quantity (for MARKET orders in quote currency)
            
        Returns:
            Order response dictionary
        """
        params = {
            'symbol': symbol,
            'side': side.upper(),
            'type': order_type.upper()
        }
        
        if order_type.upper() == 'MARKET':
            if quote_order_qty:
                params['quoteOrderQty'] = quote_order_qty
            elif quantity:
                params['quantity'] = quantity
        elif order_type.upper() == 'LIMIT':
            if not quantity or not price:
                raise ValueError("LIMIT orders require both quantity and price")
            params['quantity'] = quantity
            params['price'] = price
            params['timeInForce'] = 'GTC'  # Good Till Cancel
        elif order_type.upper() in ['STOP_MARKET', 'STOP_LIMIT', 'STOP']:
            if not quantity:
                raise ValueError("Stop orders require quantity")
            params['quantity'] = quantity
            if stop_price:
                params['stopPrice'] = stop_price
            elif price:
                params['stopPrice'] = price
            else:
                raise ValueError("Stop orders require stopPrice")
            if order_type.upper() == 'STOP_LIMIT':
                if limit_price:
                    params['price'] = limit_price  # Limit price for STOP_LIMIT
                else:
                    raise ValueError("STOP_LIMIT orders require limitPrice")
        
        logger.info(f"Placing {side} order: {params}")
        return self._make_request('POST', '/api/v3/order', params=params, signed=True)
    
    def place_market_buy(self, symbol: str, quote_quantity: float) -> Dict:
        """
        Place a market buy order
        
        Args:
            symbol: Trading pair symbol
            quote_quantity: Amount in quote currency (e.g., USDT amount for BTCUSDT)
            
        Returns:
            Order response
        """
        return self.place_order(
            symbol=symbol,
            side='BUY',
            order_type='MARKET',
            quote_order_qty=quote_quantity
        )
    
    def place_market_sell(self, symbol: str, quantity: float) -> Dict:
        """
        Place a market sell order
        
        Args:
            symbol: Trading pair symbol
            quantity: Quantity in base currency (e.g., BTC amount for BTCUSDT)
            
        Returns:
            Order response
        """
        return self.place_order(
            symbol=symbol,
            side='SELL',
            order_type='MARKET',
            quantity=quantity
        )
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict:
        """
        Get order status
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            Order status information
        """
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_request('GET', '/api/v3/order', params=params, signed=True)
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        """
        Cancel an order
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        params = {
            'symbol': symbol,
            'orderId': order_id
        }
        return self._make_request('DELETE', '/api/v3/order', params=params, signed=True)
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders
        
        Args:
            symbol: Optional trading pair symbol. If None, returns all open orders
            
        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self._make_request('GET', '/api/v3/openOrders', params=params, signed=True)
    
    def cancel_all_orders(self, symbol: str) -> Dict:
        """
        Cancel all open orders for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Cancellation response
        """
        params = {'symbol': symbol}
        return self._make_request('DELETE', '/api/v3/openOrders', params=params, signed=True)

