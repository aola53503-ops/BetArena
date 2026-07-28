from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import Config

Base = declarative_base()
engine = create_engine(Config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    balance = Column(Float, default=Config.STARTING_BALANCE)
    crypto_balance = Column(Float, default=0.0)
    total_bets = Column(Integer, default=0)
    total_won = Column(Float, default=0.0)
    total_lost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

class Bet(Base):
    __tablename__ = 'bets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    match = Column(String(200))
    league = Column(String(100))
    bet_type = Column(String(50))
    selection = Column(String(100))
    odds = Column(Float)
    amount = Column(Float)
    potential_win = Column(Float)
    status = Column(String(20))  # 'pending', 'won', 'lost', 'cancelled'
    result = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    settled_at = Column(DateTime)

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    type = Column(String(20))  # 'deposit', 'withdrawal', 'bet', 'win'
    amount = Column(Float)
    currency = Column(String(10), default='USD')
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

class Database:
    @staticmethod
    def get_session():
        return SessionLocal()
    
    @staticmethod
    def get_user(telegram_id):
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if not user:
                user = User(telegram_id=telegram_id)
                session.add(user)
                session.commit()
            return user
        finally:
            session.close()
    
    @staticmethod
    def update_balance(telegram_id, amount):
        session = SessionLocal()
        try:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.balance += amount
                user.last_active = datetime.utcnow()
                session.commit()
                return user.balance
            return None
        finally:
            session.close()
    
    @staticmethod
    def add_bet(telegram_id, match, league, bet_type, selection, odds, amount, potential_win):
        session = SessionLocal()
        try:
            bet = Bet(
                user_id=telegram_id,
                match=match,
                league=league,
                bet_type=bet_type,
                selection=selection,
                odds=odds,
                amount=amount,
                potential_win=potential_win,
                status='pending'
            )
            session.add(bet)
            
            # Update user stats
            user = session.query(User).filter_by(telegram_id=telegram_id).first()
            if user:
                user.total_bets += 1
                user.balance -= amount
            
            session.commit()
            return bet
        finally:
            session.close()
    
    @staticmethod
    def settle_bet(bet_id, result, won):
        session = SessionLocal()
        try:
            bet = session.query(Bet).filter_by(id=bet_id).first()
            if bet:
                bet.status = 'won' if won else 'lost'
                bet.result = result
                bet.settled_at = datetime.utcnow()
                
                if won:
                    user = session.query(User).filter_by(telegram_id=bet.user_id).first()
                    if user:
                        user.balance += bet.potential_win
                        user.total_won += bet.potential_win
                else:
                    user = session.query(User).filter_by(telegram_id=bet.user_id).first()
                    if user:
                        user.total_lost += bet.amount
                
                session.commit()
                return bet
            return None
        finally:
            session.close()
    
    @staticmethod
    def get_bets(telegram_id, limit=20):
        session = SessionLocal()
        try:
            bets = session.query(Bet).filter_by(user_id=telegram_id).order_by(
                Bet.created_at.desc()
            ).limit(limit).all()
            return bets
        finally:
            session.close()
    
    @staticmethod
    def add_transaction(telegram_id, trans_type, amount, currency, description):
        session = SessionLocal()
        try:
            transaction = Transaction(
                user_id=telegram_id,
                type=trans_type,
                amount=amount,
                currency=currency,
                description=description
            )
            session.add(transaction)
            session.commit()
            return transaction
        finally:
            session.close()
