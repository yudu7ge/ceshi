from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()
engine = create_engine(os.getenv('DB_URL'))
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)
    username = Column(String)
    invite_code = Column(String, unique=True)
    balance = Column(Integer, default=1000)
    inviter_id = Column(Integer, ForeignKey('users.id'))
    wallet_address = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    inviter = relationship("User", remote_side=[id])
    games_as_player_a = relationship("GameHistory", foreign_keys="GameHistory.player_a_id")
    games_as_player_b = relationship("GameHistory", foreign_keys="GameHistory.player_b_id")

class GameHistory(Base):
    __tablename__ = 'game_history'
    
    id = Column(Integer, primary_key=True)
    game_id = Column(String)
    player_a_id = Column(Integer, ForeignKey('users.id'))
    player_b_id = Column(Integer, ForeignKey('users.id'))
    bet_amount = Column(Integer)
    player_a_score = Column(Integer)
    player_b_score = Column(Integer)
    winner_id = Column(Integer, ForeignKey('users.id'))
    win_amount = Column(Integer)
    status = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    player_a = relationship("User", foreign_keys=[player_a_id])
    player_b = relationship("User", foreign_keys=[player_b_id])
    winner = relationship("User", foreign_keys=[winner_id])
    
class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Integer)
    type = Column(String)  # 'deposit' or 'withdraw'
    status = Column(String)  # 'pending', 'completed', 'failed'
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User")
Base.metadata.create_all(engine)