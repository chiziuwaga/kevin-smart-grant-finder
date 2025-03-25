"""
Database models for the application.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Grant(Base):
    __tablename__ = 'grants'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    amount = Column(Float)
    deadline = Column(DateTime)
    source = Column(String)
    url = Column(String)
    status = Column(String)

class Analysis(Base):
    __tablename__ = 'analyses'

    id = Column(Integer, primary_key=True)
    grant_id = Column(Integer, ForeignKey('grants.id'))
    score = Column(Float)
    notes = Column(String)
    timestamp = Column(DateTime)
    
    grant = relationship('Grant')