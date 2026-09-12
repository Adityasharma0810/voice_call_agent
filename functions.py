from sqlalchemy.orm import Session
from typing import Dict, Any
import json

# Global registry - only enable functions that should be callable
FUNCTION_REGISTRY = {
    "appointment_making": True,  # Only functions with True value can be used
    "order_booking": True
}

# Predefined SQL queries for each function
SQL_QUERIES = {
    "appointment_making": {
        "create": "INSERT INTO appointments (user_id, start_time, end_time, title, location, notes) VALUES (?, ?, ?, ?, ?, ?)",
        "read": "SELECT * FROM appointments WHERE user_id = ?",
        "update": "UPDATE appointments SET start_time = ?, end_time = ?, title = ?, location = ? WHERE id = ?",
        "delete": "DELETE FROM appointments WHERE id = ?"
    },
    "order_booking": {
        "create": "INSERT INTO orders (user_id, item_name, quantity, price, total) VALUES (?, ?, ?, ?, ?)",
        "read": "SELECT * FROM orders WHERE user_id = ?",
        "update": "UPDATE orders SET quantity = ?, price = ?, total = ? WHERE id = ?",
        "delete": "DELETE FROM orders WHERE id = ?"
    }
}

def appointment_making(params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Book an appointment with the user"""
    try:
        db.execute(
            SQL_QUERIES["appointment_making"]["create"],
            (
                params.get("user_id"),
                params.get("start_time"),
                params.get("end_time"),
                params.get("title"),
                params.get("location"),
                params.get("notes")
            )
        )
        db.commit()
        return {"status": "success", "message": "Appointment created successfully", "id": db.execute("SELECT last_insert_rowid() FROM appointments").fetchone()[0]}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

def order_booking(params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Book an order for the user"""
    try:
        db.execute(
            SQL_QUERIES["order_booking"]["create"],
            (
                params.get("user_id"),
                params.get("item_name"),
                params.get("quantity"),
                params.get("price"),
                params.get("total")
            )
        )
        db.commit()
        return {"status": "success", "message": "Order created successfully", "id": db.execute("SELECT last_insert_rowid() FROM orders").fetchone()[0]}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

def get_available_functions() -> Dict[str, bool]:
    """Return only enabled functions"""
    return {k: v for k, v in FUNCTION_REGISTRY.items() if v}

def execute_function(function_name: str, params: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """Execute a function if it's enabled"""
    if not FUNCTION_REGISTRY.get(function_name, False):
        return {"status": "error", "message": f"Function {function_name} is not enabled"}

    if function_name == "appointment_making":
        return appointment_making(params, db)
    elif function_name == "order_booking":
        return order_booking(params, db)
    else:
        return {"status": "error", "message": f"Unknown function {function_name}"}