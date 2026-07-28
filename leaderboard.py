from database import Database

class Leaderboard:
    """Leaderboard system"""
    
    def __init__(self):
        self.db = Database()
    
    def get_top_users(self, limit=10, by='total_won'):
        """Get top users by specified metric"""
        session = self.db.get_session()
        try:
            from database import User
            users = session.query(User).order_by(
                getattr(User, by).desc()
            ).limit(limit).all()
            return users
        finally:
            session.close()
    
    def format_leaderboard(self, users):
        """Format leaderboard for display"""
        if not users:
            return "No users on the leaderboard yet!"
        
        message = "🏆 *LEADERBOARD* 🏆\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        emojis = ['🥇', '🥈', '🥉']
        for i, user in enumerate(users):
            rank_emoji = emojis[i] if i < 3 else f"{i+1}."
            
            # Get user name
            name = user.first_name or user.username or f"User{user.telegram_id}"
            
            message += f"{rank_emoji} *{name}*\n"
            message += f"├─ Balance: ${user.balance:.2f}\n"
            message += f"├─ Bets: {user.total_bets}\n"
            message += f"└─ Won: ${user.total_won:.2f}\n\n"
        
        return message
