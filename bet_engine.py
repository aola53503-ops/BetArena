import random
from datetime import datetime
from config import Config

class BetEngine:
    """Betting engine for BetArena"""
    
    def __init__(self):
        self.house_edge = Config.HOUSE_EDGE
    
    def calculate_payout(self, odds, amount):
        """Calculate potential payout"""
        return amount * odds
    
    def calculate_parlay_payout(self, bets):
        """Calculate parlay payout"""
        total_odds = 1
        for bet in bets:
            total_odds *= bet.get('odds', 1)
        return total_odds
    
    def determine_winner(self, match, bet_type, selection):
        """Determine if bet is a winner (simulated)"""
        # In production, this would use real match results
        # For demo, use random with weighted probabilities
        
        # Simulate match result
        result = random.random()
        
        if bet_type == 'moneyline':
            if selection == 'home':
                # Home win probability (adjusted for odds)
                return result < 0.45
            elif selection == 'draw':
                return 0.25 < result < 0.55
            else:  # away
                return result > 0.55
        
        elif bet_type == 'spread':
            # Simulate spread bet
            spread_result = random.uniform(-10, 10)
            if selection == 'home':
                return spread_result > 0
            else:
                return spread_result < 0
        
        elif bet_type == 'total':
            # Simulate total over/under
            total_result = random.randint(1, 10)
            target = 5
            if selection == 'over':
                return total_result > target
            else:
                return total_result < target
        
        return False
    
    def format_bet_confirmation(self, bet):
        """Format bet confirmation message"""
        return f"""
✅ *Bet Placed!*

📊 *Match:* {bet.match}
📋 *League:* {bet.league}
🎯 *Bet Type:* {bet.bet_type}
🔮 *Selection:* {bet.selection}
💰 *Odds:* {bet.odds:.2f}
💵 *Amount:* ${bet.amount:.2f}
🎰 *Potential Win:* ${bet.potential_win:.2f}

🔑 *Bet ID:* #{bet.id}
📅 *Placed:* {bet.created_at.strftime('%Y-%m-%d %H:%M')}

*Good luck!* 🍀
"""
