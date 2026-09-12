from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Database configuration
# Separate databases for appointment and order
APPOINTMENT_URL = os.getenv("APPOINTMENT_DB_URL", "sqlite:///appointment.db")
ORDER_URL = os.getenv("ORDER_DB_URL", "sqlite:///order.db")

appointment_engine = create_engine(APPOINTMENT_URL, echo=False, future=True)
AppointmentSession = sessionmaker(bind=appointment_engine, autoflush=False, autocommit=False)

order_engine = create_engine(ORDER_URL, echo=False, future=True)
OrderSession = sessionmaker(bind=order_engine, autoflush=False, autocommit=False)

Base = declarative_base()

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    title = Column(String, nullable=False)
    location = Column(String)
    notes = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# Separate order DB using its own engine and base
OrderBase = declarative_base()

class Order(OrderBase):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables on their respective DBs
Base.metadata.create_all(appointment_engine)
OrderBase.metadata.create_all(order_engine)

def get_appointment_db():
    session = AppointmentSession()
    try:
        yield session
    finally:
        session.close()

def get_order_db():
    session = OrderSession()
    try:
        yield session
    finally:
        session.close()