import requests
from cachetools import cached, TTLCache
from config import Config

cache = TTLCache(maxsize=100, ttl=60)

class CryptoAPI:
    """Cryptocurrency price API"""
    
    def __init__(self):
        self.session = requests.Session()
    
    @cached(cache)
    def get_price(self, crypto='BTC'):
        """Get cryptocurrency price in USD"""
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': crypto.lower(),
                'vs_currencies': 'usd'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get(crypto.lower(), {}).get('usd', 0)
            return 0
        except Exception as e:
            print(f"Crypto API error: {e}")
            return 0
    
    @cached(cache)
    def get_all_prices(self):
        """Get prices for all supported cryptos"""
        prices = {}
        for crypto in Config.CRYPTO_CURRENCIES:
            prices[crypto] = self.get_price(crypto)
        return prices
    
    def convert_usd_to_crypto(self, usd_amount, crypto='BTC'):
        """Convert USD to crypto"""
        price = self.get_price(crypto)
        if price > 0:
            return usd_amount / price
        return 0
    
    def convert_crypto_to_usd(self, crypto_amount, crypto='BTC'):
        """Convert crypto to USD"""
        price = self.get_price(crypto)
        return crypto_amount * price
