from sqlalchemy import create_engine, Column, Integer, Boolean, BigInteger, Text, String, DateTime, ForeignKey, event
from sqlalchemy.orm import scoped_session, sessionmaker, backref, relation
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import BYTEA
import os

engine = create_engine(os.environ.get("DB_CONNECTION_STRING"))
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SyncedBlock(Base):
    __tablename__ = 'synced_blocks'
    header_hash = Column('header_hash', String(64), primary_key=True)
    height = Column('height', Integer, primary_key=True)
    
class Puzzle(Base):
    __tablename__ = 'puzzles'
    puzzle_hash = Column('puzzle_hash', String(64), primary_key=True)
    puzzle = Column('puzzle', BYTEA)

class SingletonState(Base):
    __tablename__ = 'singleton_states'
    coin_id = Column('coin_id', String(64), primary_key=True)
    melted = Column('melted', Boolean, primary_key=True)

    header_hash = Column('header_hash', String(64))
    height = Column('height', Integer)

    parent_coin_id = Column('parent_coin_id', String(64))
    puzzle_hash = Column('puzzle_hash', String(64))
    amount = Column('amount', BigInteger)

    launcher_id = Column('launcher_id', String(64))
    inner_puzzle_hash = Column('inner_puzzle_hash', String(64))