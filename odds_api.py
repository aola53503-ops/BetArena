import requests
import json
import time
from datetime import datetime
from cachetools import cached, TTLCache
from config import Config

cache = TTLCache(maxsize=200, ttl=60)

class OddsAPI:
    """Live odds provider"""
    
    def __init__(self):
        self.api_key = Config.ODDS_API_KEY
        self.base_url = "https://api.the-odds-api.com/v4"
        self.session = requests.Session()
    
    @cached(cache)
    def get_live_games(self, sport='soccer'):
        """Get live games with odds"""
        if not self.api_key:
            # Return mock data if no API key
            return self.get_mock_games()
        
        try:
            url = f"{self.base_url}/sports/{sport}/odds"
            params = {
                'apiKey': self.api_key,
                'region': 'eu',
                'markets': 'h2h',
                'dateFormat': 'iso'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                time.sleep(5)
                response = self.session.get(url, params=params, timeout=15)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"API Error: {e}")
            return self.get_mock_games()
    
    def get_mock_games(self):
        """Return mock games when API is not available"""
        return [
            {
                'id': '1',
                'home_team': 'Manchester City',
                'away_team': 'Arsenal',
                'sport_title': 'Premier League',
                'sport_key': 'premier_league',
                'commence_time': datetime.now().isoformat(),
                'bookmakers': [
                    {
                        'key': 'mockbook',
                        'title': 'Mock Book',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Manchester City', 'price': 1.85},
                                    {'name': 'Draw', 'price': 3.40},
                                    {'name': 'Arsenal', 'price': 4.20}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'id': '2',
                'home_team': 'Real Madrid',
                'away_team': 'Barcelona',
                'sport_title': 'La Liga',
                'sport_key': 'la_liga',
                'commence_time': datetime.now().isoformat(),
                'bookmakers': [
                    {
                        'key': 'mockbook',
                        'title': 'Mock Book',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Real Madrid', 'price': 2.10},
                                    {'name': 'Draw', 'price': 3.20},
                                    {'name': 'Barcelona', 'price': 3.50}
                                ]
                            }
                        ]
                    }
                ]
            },
            {
                'id': '3',
                'home_team': 'Bayern Munich',
                'away_team': 'Borussia Dortmund',
                'sport_title': 'Bundesliga',
                'sport_key': 'bundesliga',
                'commence_time': datetime.now().isoformat(),
                'bookmakers': [
                    {
                        'key': 'mockbook',
                        'title': 'Mock Book',
                        'markets': [
                            {
                                'key': 'h2h',
                                'outcomes': [
                                    {'name': 'Bayern Munich', 'price': 1.75},
                                    {'name': 'Draw', 'price': 3.60},
                                    {'name': 'Borussia Dortmund', 'price': 4.50}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    
    def format_game(self, game):
        """Format game for display"""
        home_team = game.get('home_team', 'Unknown')
        away_team = game.get('away_team', 'Unknown')
        league = game.get('sport_title', 'Unknown')
        
        # Get best odds
        best_home = 0
        best_draw = 0
        best_away = 0
        
        for bookmaker in game.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market.get('key') == 'h2h':
                    for outcome in market.get('outcomes', []):
                        name = outcome.get('name', '')
                        price = outcome.get('price', 0)
                        
                        if name == home_team:
                            best_home = max(best_home, price)
                        elif name == away_team:
                            best_away = max(best_away, price)
                        elif name == 'Draw':
                            best_draw = max(best_draw, price)
        
        return {
            'match': f"{home_team} vs {away_team}",
            'league': league,
            'home_team': home_team,
            'away_team': away_team,
            'odds': {
                'home': best_home,
                'draw': best_draw,
                'away': best_away
            },
            'game_id': game.get('id', ''),
            'commence_time': game.get('commence_time')
        }
    
    def get_league_games(self, league):
        """Get games for a specific league"""
        games = self.get_live_games()
        filtered = [g for g in games if league in g.get('sport_key', '').lower()]
        return [self.format_game(g) for g in filtered]
