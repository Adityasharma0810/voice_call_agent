"""
Voice LLM Pipeline with Groq, SQLAlchemy, and Function Gating
Two separate Groq models: one for decision, one for talking
"""

import os
from dotenv import load_dotenv
from pipeline import Pipeline

load_dotenv()

if __name__ == "__main__":
    # Ensure database tables are created
    from database import appointment_engine, order_engine, Base, Appointment, Order
    from functions import FUNCTION_REGISTRY

    Base.metadata.create_all(appointment_engine)
    Order.metadata.create_all(order_engine)
    print(f"Database tables created. Enabled functions: {FUNCTION_REGISTRY}")

    # Initialize and run pipeline
    pipeline = Pipeline()
    result = pipeline.run()

    print("\n=== Pipeline Complete ===")
    print(f"Response: {result['response']}")
    if result.get("function_call"):
        print(f"Function called: {result['function_call']}")