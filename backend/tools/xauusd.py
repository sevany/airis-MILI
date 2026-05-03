"""
XAUUSD (Gold) Market Data Module - EOD + Delayed Live Data
Fetches EOD data + 15-min delayed live price from EOD Historical Data API
Compatible with $19.99/mo plan
"""
import requests
import json
import os
from datetime import datetime, timedelta
from backend.config import Config
from backend.tools.indicators import full_technical_analysis

class XAUUSDData:
    """XAUUSD market data fetcher - $19.99 EOD plan compatible"""
    
    BASE_URL = "https://eodhistoricaldata.com/api"
    SYMBOL = "XAUUSD.FOREX"  # Gold vs USD
    CACHE_DIR = "./data/xauusd"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or Config.EOD_API_KEY
        if not self.api_key:
            raise ValueError("EOD_API_KEY not configured")
        
        # Ensure cache directory exists
        os.makedirs(self.CACHE_DIR, exist_ok=True)
    
    def safe_float(self, value, default=0.0):
        """Safely convert to float, handle 'NA' and None"""
        if value is None or value == 'NA' or value == '':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_delayed_price(self):
        """
        Get XAUUSD price (15-min delayed on $19.99 plan)
        Uses real-time endpoint which returns delayed data based on plan tier
        
        Returns:
            dict: Current price data (15min delayed)
        """
        try:
            # Use real-time endpoint - returns delayed data for lower-tier plans
            url = f"{self.BASE_URL}/real-time/{self.SYMBOL}"
            params = {
                'api_token': self.api_key,
                'fmt': 'json'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'price': self.safe_float(data.get('close')),
                'change': self.safe_float(data.get('change')),
                'change_percent': self.safe_float(data.get('change_p')),
                'timestamp': str(data.get('timestamp', '')),
                'high': self.safe_float(data.get('high')),
                'low': self.safe_float(data.get('low')),
                'open': self.safe_float(data.get('open'))
            }
        
        except Exception:
            # Silent fail - will fall back to EOD
            raise
    
    def get_current_price(self):
        """
        Get current/latest XAUUSD price
        Tries delayed API, falls back to latest EOD close
        
        Returns:
            dict: Current price data
        """
        try:
            # Try delayed live data first
            delayed_data = self.get_delayed_price()
            
            # If delayed has valid price, use it
            if delayed_data['price'] > 0:
                return delayed_data
            
            # Fall back to latest EOD close (silent fallback)
            candles = self.load_cached_eod()
            
            if not candles:
                candles = self.get_eod_data(days=5)
            
            if candles and len(candles) > 0:
                latest = candles[0]
                return {
                    'price': latest['close'],
                    'change': latest['close'] - latest['open'],
                    'change_percent': ((latest['close'] - latest['open']) / latest['open']) * 100 if latest['open'] > 0 else 0,
                    'timestamp': latest['date'],
                    'high': latest['high'],
                    'low': latest['low'],
                    'open': latest['open']
                }
            
            return {
                'price': 0,
                'change': 0,
                'change_percent': 0,
                'timestamp': '',
                'high': 0,
                'low': 0,
                'open': 0
            }
        
        except Exception as e:
            # Silent fallback to EOD
            candles = self.load_cached_eod() or self.get_eod_data(days=5)
            if candles:
                latest = candles[0]
                return {
                    'price': latest['close'],
                    'change': 0,
                    'change_percent': 0,
                    'timestamp': latest['date'],
                    'high': latest['high'],
                    'low': latest['low'],
                    'open': latest['open']
                }
            return {'price': 0, 'change': 0, 'change_percent': 0, 'timestamp': '', 'high': 0, 'low': 0, 'open': 0}
    
    def get_eod_data(self, days=90):
        """
        Get end-of-day XAUUSD data
        
        Args:
            days: Number of days of historical data
            
        Returns:
            list: [{'date', 'open', 'high', 'low', 'close', 'volume'}, ...]
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = f"{self.BASE_URL}/eod/{self.SYMBOL}"
            params = {
                'api_token': self.api_key,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'fmt': 'json'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Parse daily candles (reverse to get newest first)
            candles = []
            for item in reversed(data):
                try:
                    candles.append({
                        'date': str(item.get('date', '')),
                        'open': self.safe_float(item.get('open')),
                        'high': self.safe_float(item.get('high')),
                        'low': self.safe_float(item.get('low')),
                        'close': self.safe_float(item.get('close')),
                        'volume': self.safe_float(item.get('volume'))
                    })
                except (ValueError, TypeError) as e:
                    print(f"⚠️  Skipping invalid candle: {e}")
                    continue
            
            return candles
        
        except Exception as e:
            print(f"❌ EOD data error: {str(e)}")
            raise
    
    def cache_eod_data(self, days=90):
        """Fetch and cache EOD data locally"""
        try:
            print(f"📈 Fetching {days} days of XAUUSD EOD data...")
            candles = self.get_eod_data(days)
            
            cache_file = os.path.join(self.CACHE_DIR, 'eod_cache.json')
            with open(cache_file, 'w') as f:
                json.dump({
                    'updated_at': datetime.now().isoformat(),
                    'candles': candles
                }, f, indent=2)
            
            print(f"✓ Cached {len(candles)} candles to {cache_file}")
            return candles
        
        except Exception as e:
            print(f"❌ Cache EOD error: {str(e)}")
            raise
    
    def load_cached_eod(self):
        """Load cached EOD data"""
        cache_file = os.path.join(self.CACHE_DIR, 'eod_cache.json')
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check if cache is fresh (< 24 hours old)
            updated_at = datetime.fromisoformat(data['updated_at'])
            age_hours = (datetime.now() - updated_at).total_seconds() / 3600
            
            if age_hours < 24:
                # Silent - cache is fresh
                return data['candles']
            else:
                # Cache stale - will refresh silently
                return None
        
        except Exception as e:
            return None
    
    def get_full_analysis(self):
        """
        Get comprehensive XAUUSD trading analysis
        Combines cached EOD data + delayed price + technical indicators
        
        Returns:
            dict: Complete trading analysis
        """
        try:
            # Try to load cached EOD data
            candles = self.load_cached_eod()
            
            # If no cache or stale, fetch fresh
            if not candles:
                candles = self.cache_eod_data()
            
            # Get current price (delayed or EOD)
            current_price_data = self.get_current_price()
            current_price = current_price_data['price']
            
            # Run technical analysis
            ta = full_technical_analysis(candles)
            
            # Combine everything
            return {
                'current_price': current_price,
                'change_today': current_price_data['change'],
                'change_percent': current_price_data['change_percent'],
                'technical_analysis': ta,
                'last_updated': datetime.now().isoformat()
            }
        
        except Exception as e:
            print(f"❌ Full analysis error: {str(e)}")
            raise
    
    def health_check(self):
        """Check if API is accessible"""
        try:
            data = self.get_current_price()
            if data and data.get('price', 0) > 0:
                return True, f"✓ XAUUSD data connected (${data['price']:.2f})"
            return False, "✗ XAUUSD data: No price data"
        except Exception as e:
            return False, f"✗ XAUUSD data: {str(e)}"