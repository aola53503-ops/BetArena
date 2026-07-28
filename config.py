import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """BetArena Configuration"""
    
    # Telegram Bot Token
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not found")
    
    # Odds API (Optional - for live odds)
    ODDS_API_KEY = os.getenv('ODDS_API_KEY')
    
    # Database - FIXED: Use sqlite:/// (three slashes, not four)
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///betarena.db')
    
    # Default Currency
    DEFAULT_CURRENCY = os.getenv('DEFAULT_CURRENCY', 'USD')
    
    # Supported Cryptocurrencies
    CRYPTO_CURRENCIES = ['BTC', 'ETH', 'SOL', 'USDT']
    
    # Leagues
    LEAGUES = {
        'premier_league': '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League',
        'la_liga': '🇪🇸 La Liga',
        'serie_a': '🇮🇹 Serie A',
        'bundesliga': '🇩🇪 Bundesliga',
        'ligue_1': '🇫🇷 Ligue 1',
        'champions_league': '🏆 Champions League',
        'nba': '🏀 NBA',
        'mlb': '⚾ MLB'
    }
    
    # Bet Types
    BET_TYPES = ['Moneyline', 'Spread', 'Total', 'Parlay']
    
    # Starting Balance
    STARTING_BALANCE = 100.0
    
    # Minimum Bet
    MIN_BET = 1.0
    
    # Maximum Bet
    MAX_BET = 1000.0
    
    # House Edge (for crypto bets)
    HOUSE_EDGE = 0.02  # 2%
