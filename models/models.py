from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime


Base = declarative_base()


# Company Table 
class Company(Base):
    __tablename__ = "companies"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False)
    email        = Column(String(100), unique=True, nullable=False)
    plan         = Column(String(20), default="free")  # free, pro, enterprise
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    # Company Users
    users        = relationship("User", back_populates="company")
    connections  = relationship("DBConnection", back_populates="company")
    conversations = relationship("Conversation", back_populates="company")


# User Table
# Each person who logs in is a user
class User(Base):
    __tablename__ = "users"

    id             = Column(Integer, primary_key=True, index=True)
    company_id     = Column(Integer, ForeignKey("companies.id"))
    name           = Column(String(100), nullable=False)
    email          = Column(String(100), unique=True, nullable=False)
    password_hash  = Column(String(255), nullable=False)

    # Role decides what data user can see
    # CEO sees everything, manager sees their department
    role           = Column(String(20), default="analyst")
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    last_login     = Column(DateTime, nullable=True)

    company        = relationship("Company", back_populates="users")
    conversations  = relationship("Conversation", back_populates="user")


# DB Connection Table
class DBConnection(Base):
    __tablename__ = "db_connections"

    id           = Column(Integer, primary_key=True, index=True)
    company_id   = Column(Integer, ForeignKey("companies.id"))
    name         = Column(String(100))       # DB_name
    db_type      = Column(String(20))        
    host         = Column(String(255))
    port         = Column(Integer)
    username     = Column(String(100))
    password_enc = Column(Text)             
    db_name      = Column(String(100))
    schema_json  = Column(Text)            
    is_active    = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    company      = relationship("Company", back_populates="connections")


# Conversation Table 
# Every question user asks is saved 
class Conversation(Base):
    __tablename__ = "conversations"

    id            = Column(Integer, primary_key=True, index=True)
    company_id    = Column(Integer, ForeignKey("companies.id"))
    user_id       = Column(Integer, ForeignKey("users.id"))
    connection_id = Column(Integer, ForeignKey("db_connections.id"))
    question      = Column(Text)             
    sql_generated = Column(Text)             
    answer        = Column(Text)             
    chart_type    = Column(String(20))       
    chart_data    = Column(Text)             
    execution_ms  = Column(Integer)          # how fast was the query
    was_cached    = Column(Boolean, default=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    company       = relationship("Company", back_populates="conversations")
    user          = relationship("User", back_populates="conversations")


# Alerts 
class Alert(Base):
    __tablename__ = "alerts"

    id                  = Column(Integer, primary_key=True, index=True)
    company_id          = Column(Integer, ForeignKey("companies.id"))

    kpi_name            = Column(String(100))

    current_value       = Column(String(50))
    historical_value    = Column(String(50))
    pct_change          = Column(String(20))

    severity            = Column(String(20))

    message             = Column(Text)
    possible_causes     = Column(Text)    
    recommended_action  = Column(Text)

    is_read             = Column(Boolean, default=False)
    created_at          = Column(DateTime, default=datetime.utcnow)
