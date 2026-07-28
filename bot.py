#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import os
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

from config import Config
from database import Database
from odds_api import OddsAPI
from crypto_api import CryptoAPI
from bet_engine import BetEngine
from leaderboard import Leaderboard

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== CONSTANTS ====================
SELECTING_SPORT, SELECTING_MATCH, SELECTING_BET_TYPE, ENTERING_AMOUNT = range(4)

# ==================== INITIALIZATION ====================
db = Database()
odds = OddsAPI()
crypto = CryptoAPI()
bet_engine = BetEngine()
leaderboard = Leaderboard()

# ==================== COMMAND HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with main menu"""
    user = update.effective_user
    db_user = db.get_user(user.id)
    
    keyboard = [
        [InlineKeyboardButton("⚽ Live Matches", callback_data="live_matches"),
         InlineKeyboardButton("📊 My Bets", callback_data="my_bets")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("💎 Crypto Prices", callback_data="crypto_prices"),
         InlineKeyboardButton("📈 Stats", callback_data="stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"""
🏟️ *BETARENA* - The Ultimate Betting Arena 🏟️

*Welcome {user.first_name}!*

💰 Balance: ${db_user.balance:.2f}
🎮 Total Bets: {db_user.total_bets}
🏆 Total Won: ${db_user.total_won:.2f}

*Select an option:*
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def live_matches_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live matches"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 *Fetching live matches...*\n\nPlease wait...",
        parse_mode='Markdown'
    )
    
    # Get sports selection
    keyboard = []
    for league_key, league_name in Config.LEAGUES.items():
        keyboard.append([InlineKeyboardButton(league_name, callback_data=f"sport_{league_key}")])
    keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⚽ *Select a league:*",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def sport_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sport selected, show matches"""
    query = update.callback_query
    await query.answer()
    
    league_key = query.data.replace("sport_", "")
    league_name = Config.LEAGUES.get(league_key, league_key)
    
    await query.edit_message_text(
        f"🔍 *Loading {league_name} matches...*",
        parse_mode='Markdown'
    )
    
    # Get matches for this league
    games = odds.get_league_games(league_key)
    
    if not games:
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data=f"sport_{league_key}")],
                    [InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ No matches available for {league_name}\n\nPlease try again later.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return
    
    # Show matches
    keyboard = []
    for game in games[:10]:
        display = f"{game['home_team']} vs {game['away_team']}"
        keyboard.append([InlineKeyboardButton(display, callback_data=f"match_{game['game_id']}")])
    keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚽ *{league_name} - Matches*\n\nSelect a match to bet on:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    # Store games in context
    context.user_data['games'] = {game['game_id']: game for game in games}

async def match_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Match selected, show bet options"""
    query = update.callback_query
    await query.answer()
    
    game_id = query.data.replace("match_", "")
    games = context.user_data.get('games', {})
    game = games.get(game_id)
    
    if not game:
        await query.edit_message_text(
            "⚠️ Match not found. Please try again.",
            parse_mode='Markdown'
        )
        return
    
    context.user_data['current_match'] = game
    
    keyboard = [
        [InlineKeyboardButton("🏠 Home", callback_data=f"bet_home_{game_id}"),
         InlineKeyboardButton("🤝 Draw", callback_data=f"bet_draw_{game_id}")],
        [InlineKeyboardButton("✈️ Away", callback_data=f"bet_away_{game_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="live_matches")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    odds_display = game['odds']
    
    await query.edit_message_text(
        f"""
⚽ *{game['match']}*
📋 *League:* {game['league']}

💰 *Odds:*
🏠 Home: {odds_display.get('home', 0):.2f}
🤝 Draw: {odds_display.get('draw', 0):.2f}
✈️ Away: {odds_display.get('away', 0):.2f}

Select your bet:
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def bet_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bet type selected, enter amount"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split("_")
    bet_type = data[1]  # home, draw, away
    game_id = data[2]
    
    games = context.user_data.get('games', {})
    game = games.get(game_id)
    
    if not game:
        await query.edit_message_text(
            "⚠️ Match not found. Please try again.",
            parse_mode='Markdown'
        )
        return
    
    # Store bet info
    context.user_data['bet_type'] = bet_type
    context.user_data['bet_game'] = game
    
    # Get odds
    odds_value = game['odds'].get(bet_type, 0)
    if bet_type == 'home':
        selection_name = game['home_team']
    elif bet_type == 'draw':
        selection_name = 'Draw'
    else:
        selection_name = game['away_team']
    
    context.user_data['odds_value'] = odds_value
    context.user_data['selection_name'] = selection_name
    
    # Ask for amount
    user = update.effective_user
    db_user = db.get_user(user.id)
    
    keyboard = [
        [InlineKeyboardButton("$10", callback_data="amount_10"),
         InlineKeyboardButton("$25", callback_data="amount_25"),
         InlineKeyboardButton("$50", callback_data="amount_50")],
        [InlineKeyboardButton("$100", callback_data="amount_100"),
         InlineKeyboardButton("$250", callback_data="amount_250"),
         InlineKeyboardButton("$500", callback_data="amount_500")],
        [InlineKeyboardButton("🔙 Back", callback_data="live_matches")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"""
💰 *Place Your Bet*

🎯 *Selection:* {selection_name}
⚽ *Match:* {game['match']}
📊 *Odds:* {odds_value:.2f}

💵 *Your Balance:* ${db_user.balance:.2f}

Select amount or type custom:
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def amount_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Amount selected, place bet"""
    query = update.callback_query
    await query.answer()
    
    amount_str = query.data.replace("amount_", "")
    
    if amount_str == "custom":
        await query.edit_message_text(
            "💰 Enter amount:",
            parse_mode='Markdown'
        )
        return ENTERING_AMOUNT
    
    amount = float(amount_str)
    await place_bet(update, context, amount)

async def custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Custom amount entered"""
    try:
        amount = float(update.message.text)
        await place_bet(update, context, amount)
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid number.",
            parse_mode='Markdown'
        )
        return ENTERING_AMOUNT

async def place_bet(update, context, amount):
    """Place the bet"""
    user = update.effective_user
    db_user = db.get_user(user.id)
    
    # Get bet info
    game = context.user_data.get('bet_game', {})
    bet_type = context.user_data.get('bet_type', '')
    odds_value = context.user_data.get('odds_value', 0)
    selection_name = context.user_data.get('selection_name', '')
    
    # Validate
    if not game or not bet_type:
        await update.message.reply_text(
            "⚠️ Invalid bet. Please try again.",
            parse_mode='Markdown'
        )
        return
    
    if amount < Config.MIN_BET:
        await update.message.reply_text(
            f"❌ Minimum bet is ${Config.MIN_BET:.2f}",
            parse_mode='Markdown'
        )
        return
    
    if amount > Config.MAX_BET:
        await update.message.reply_text(
            f"❌ Maximum bet is ${Config.MAX_BET:.2f}",
            parse_mode='Markdown'
        )
        return
    
    if amount > db_user.balance:
        await update.message.reply_text(
            f"❌ Insufficient balance! You have ${db_user.balance:.2f}",
            parse_mode='Markdown'
        )
        return
    
    # Calculate potential win
    potential_win = bet_engine.calculate_payout(odds_value, amount)
    
    # Place bet in database
    bet = db.add_bet(
        user.id,
        game['match'],
        game['league'],
        'moneyline',
        selection_name,
        odds_value,
        amount,
        potential_win
    )
    
    if not bet:
        await update.message.reply_text(
            "❌ Failed to place bet. Please try again.",
            parse_mode='Markdown'
        )
        return
    
    # Clear context
    context.user_data.pop('bet_game', None)
    context.user_data.pop('bet_type', None)
    context.user_data.pop('odds_value', None)
    context.user_data.pop('selection_name', None)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Simulate bet result (for demo)
    # In production, this would wait for actual match results
    result_win = bet_engine.determine_winner(game, 'moneyline', bet_type)
    
    if result_win:
        # Settle as win
        db.settle_bet(bet.id, 'Won', True)
        status = "✅ *WINNER!* 🎉"
        win_amount = potential_win
    else:
        db.settle_bet(bet.id, 'Lost', False)
        status = "❌ *Lost* 😢"
        win_amount = 0
    
    # Get updated balance
    updated_user = db.get_user(user.id)
    
    await update.message.reply_text(
        f"""
🏟️ *Bet Placed!*
━━━━━━━━━━━━━━━━━━━━━

{status}

📊 *Match:* {game['match']}
🎯 *Selection:* {selection_name}
💰 *Odds:* {odds_value:.2f}
💵 *Stake:* ${amount:.2f}
🎰 *Payout:* ${win_amount:.2f}

💎 *New Balance:* ${updated_user.balance:.2f}

🔑 *Bet ID:* #{bet.id}
""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def my_bets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's bets"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    bets = db.get_bets(user.id, limit=10)
    
    if not bets:
        await query.edit_message_text(
            "📊 *No bets placed yet*\n\nPlace your first bet to get started!",
            parse_mode='Markdown'
        )
        return
    
    message = "📊 *My Bets*\n━━━━━━━━━━━━━━━━\n\n"
    
    for bet in bets:
        status_emoji = '🟢' if bet.status == 'won' else '🔴' if bet.status == 'lost' else '🟡'
        status_text = bet.status.upper() if bet.status else 'PENDING'
        
        message += f"{status_emoji} *{bet.match}*\n"
        message += f"├─ Selection: {bet.selection}\n"
        message += f"├─ Odds: {bet.odds:.2f}\n"
        message += f"├─ Stake: ${bet.amount:.2f}\n"
        if bet.status == 'won':
            message += f"└─ Won: ${bet.potential_win:.2f}\n"
        elif bet.status == 'lost':
            message += f"└─ Lost: ${bet.amount:.2f}\n"
        else:
            message += f"└─ ⏳ Pending...\n"
        message += "\n"
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show leaderboard"""
    query = update.callback_query
    await query.answer()
    
    users = leaderboard.get_top_users(limit=10)
    board = leaderboard.format_leaderboard(users)
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        board,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user balance"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = db.get_user(user.id)
    
    # Get crypto prices
    prices = crypto.get_all_prices()
    
    message = f"""
💰 *Balance*
━━━━━━━━━━━━━━━━

💵 *USD Balance:* ${db_user.balance:.2f}

📊 *Stats:*
├─ Total Bets: {db_user.total_bets}
├─ Total Won: ${db_user.total_won:.2f}
└─ Total Lost: ${db_user.total_lost:.2f}

💎 *Crypto Values:*
"""
    
    for crypto_name, price in prices.items():
        if price > 0:
            crypto_amount = db_user.balance / price
            message += f"├─ {crypto_name}: {crypto_amount:.6f}\n"
    
    keyboard = [
        [InlineKeyboardButton("💎 Deposit Crypto", callback_data="deposit")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def crypto_prices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show crypto prices"""
    query = update.callback_query
    await query.answer()
    
    prices = crypto.get_all_prices()
    
    message = "💎 *Crypto Prices*\n━━━━━━━━━━━━━━━━\n\n"
    
    for crypto_name, price in prices.items():
        if price > 0:
            message += f"💰 {crypto_name}: ${price:.2f}\n"
    
    message += f"\n📅 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="crypto_prices")],
        [InlineKeyboardButton("🏠 Menu", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user stats"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db_user = db.get_user(user.id)
    
    win_rate = (db_user.total_won / (db_user.total_won + db_user.total_lost) * 100) if (db_user.total_won + db_user.total_lost) > 0 else 0
    
    message = f"""
📈 *Your Stats*
━━━━━━━━━━━━━━━━

📊 *Overall:*
├─ Total Bets: {db_user.total_bets}
├─ Total Won: ${db_user.total_won:.2f}
├─ Total Lost: ${db_user.total_lost:.2f}
├─ Win Rate: {win_rate:.1f}%
└─ Balance: ${db_user.balance:.2f}

🏆 *Ranking:*
Coming soon...

📅 *Member Since:*
{db_user.created_at.strftime('%Y-%m-%d')}
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deposit crypto"""
    query = update.callback_query
    await query.answer()
    
    message = """
💎 *Deposit Crypto*

To deposit, send crypto to the following address:

📬 *BTC Address:* `1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa`

📬 *ETH Address:* `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`

📬 *USDT Address:* `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`

⚠️ *Minimum Deposit:* $10 equivalent
⏳ *Processing Time:* 1-3 confirmations

*Contact support for large deposits.*
"""
    
    keyboard = [[InlineKeyboardButton("🏠 Menu", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to menu"""
    query = update.callback_query
    await query.answer()
    await start_command(update, context)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled.\n\nType /start to return to menu!",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

# ==================== MAIN FUNCTION ====================

def main():
    try:
        token = os.getenv('BOT_TOKEN')
        if not token:
            logger.error("❌ BOT_TOKEN not set!")
            sys.exit(1)
        
        logger.info("🏟️ BetArena is starting...")
        
        application = Application.builder().token(token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(live_matches_command, pattern="^live_matches$"))
        application.add_handler(CallbackQueryHandler(my_bets_command, pattern="^my_bets$"))
        application.add_handler(CallbackQueryHandler(leaderboard_command, pattern="^leaderboard$"))
        application.add_handler(CallbackQueryHandler(balance_command, pattern="^balance$"))
        application.add_handler(CallbackQueryHandler(crypto_prices_command, pattern="^crypto_prices$"))
        application.add_handler(CallbackQueryHandler(stats_command, pattern="^stats$"))
        application.add_handler(CallbackQueryHandler(deposit_command, pattern="^deposit$"))
        application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu$"))
        
        # Sport and match handlers
        application.add_handler(CallbackQueryHandler(sport_selected, pattern="^sport_"))
        application.add_handler(CallbackQueryHandler(match_selected, pattern="^match_"))
        
        # Bet handlers
        application.add_handler(CallbackQueryHandler(bet_type_selected, pattern="^bet_"))
        application.add_handler(CallbackQueryHandler(amount_selected, pattern="^amount_"))
        
        # Custom amount handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, custom_amount))
        
        logger.info("✅ BetArena is running!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
