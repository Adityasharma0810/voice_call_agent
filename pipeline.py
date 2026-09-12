import os
import sys
import json
from dotenv import load_dotenv
from groq import Groq
from functions import get_available_functions, FUNCTION_REGISTRY, SQL_QUERIES, execute_function
from database import get_appointment_db, get_order_db

load_dotenv()

# ===== TWO DIFFERENT GROQ MODELS =====
DECISION_MODEL = os.getenv("GROQ_MODEL_DECISION", "openai/gpt-oss-120b")
TALK_MODEL = os.getenv("GROQ_MODEL_TALK", "qwen/qwen3.6-27b")

class DecisionLLM:
    """LLM 1: Understands conversation, decides which functions to enable"""
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def decide_functions(self, conversation_text: str) -> dict:
        available = get_available_functions()
        available_json = json.dumps(available)

        prompt = f"""
You are the decision engine for an AI assistant.
The user conversation is: "{conversation_text}"

Available functions (only those marked True can be used): {available_json}

Analyze the conversation. Which of these functions should be ACTIVE (True) for the assistant to use?
Return ONLY a JSON object with function names and boolean values, e.g. {{"appointment_making": true, "order_booking": false}}.
Only set to true if the conversation clearly needs that function.
"""

        chat_completion = self.client.chat.completions.create(
            messages=[{"role": "system", "content": "You are a function-gating decision model."},
             {"role": "user", "content": prompt}],
            model=DECISION_MODEL,
            temperature=0.2,
            max_tokens=200
        )
        response_text = chat_completion.choices[0].message.content

        # Parse JSON from response
        try:
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned)
            # User requirement: "function whose values are true those are only functions the llm can use"
            # So only functions that are True in registry AND the decision says True can be used
            return {k: (v and result.get(k, False)) for k, v in FUNCTION_REGISTRY.items()}
        except Exception:
            # Fallback: only enabled registry functions can be used
            return {k: FUNCTION_REGISTRY[k] for k in FUNCTION_REGISTRY}


class TalkLLM:
    """LLM 2: Talks to user, understands full conversation, uses allowed functions"""
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.conversation_history = []

    def talk(self, user_text: str, allowed_functions: dict = None) -> dict:
        allowed_functions = allowed_functions or {}

        # Add user message
        self.conversation_history.append({"role": "user", "content": user_text})

        # Build context of available functions and predefined SQL
        func_context = "\n".join([
            f"- {name}: SQL query for booking = {SQL_QUERIES[name]['create']}" if name in SQL_QUERIES else f"- {name}: available"
            for name, enabled in allowed_functions.items() if enabled
        ])

        system_msg = f"""You are a helpful conversational AI assistant.
The user is speaking to you via voice input. You must understand the full conversation context.
Only these functions are currently allowed (True only): {json.dumps(allowed_functions)}.
Predefined SQL queries available for functions:
{func_context}

When a user asks to book an appointment or place an order, use the function with predefined SQL queries. Do not invent SQL; use exactly the predefined queries.
Respond naturally to the user, and if they ask to book/order, confirm the details and call the appropriate function.
"""

        messages = [{"role": "system", "content": system_msg}] + self.conversation_history[-6:]  # last 6 messages for context

        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=TALK_MODEL,
            temperature=0.7,
            max_tokens=500
        )
        assistant_text = chat_completion.choices[0].message.content
        self.conversation_history.append({"role": "assistant", "content": assistant_text})

        # Check if assistant decided to use a function (simple keyword detection)
        result = {"response": assistant_text, "function_call": None}
        lower_text = assistant_text.lower()
        for func_name in allowed_functions:
            if allowed_functions.get(func_name) and func_name.replace("_", " ") in lower_text:
                result["function_call"] = func_name
                break

        return result


class Pipeline:
    def __init__(self):
        self.decision_llm = DecisionLLM()
        self.talk_llm = TalkLLM()

    def get_user_input(self) -> str:
        """Get input from argv (typed conversation mode). Voice will be added by your friend."""
        if len(sys.argv) > 1:
            return " ".join(sys.argv[1:])
        return ""

    def run(self):
        print("=== LLM Voice Pipeline Started ===")
        user_speech = self.get_user_input()
        if not user_speech:
            print("Usage: python main.py 'your message here'  OR pipe via stdin")
            print("Example: python main.py 'book an appointment for tomorrow at 4pm'")
            return {"response": "", "function_call": None}
        print(f"User input: {user_speech}")

        # 2. Decision LLM decides which functions are allowed
        allowed = self.decision_llm.decide_functions(user_speech)
        print(f"Decision LLM allowed functions: {allowed}")

        # Only functions with True in original registry can be used
        final_allowed = {k: v for k, v in allowed.items() if FUNCTION_REGISTRY.get(k, False) is True}
        print(f"Only registry-True functions allowed: {final_allowed}")

        # 3. Talk LLM responds using allowed functions and predefined SQL
        result = self.talk_llm.talk(user_speech, allowed_functions=final_allowed)
        print(f"Talk LLM response: {result['response']}")

        if result.get("function_call"):
            # Appointment DB
            if result["function_call"] == "appointment_making":
                from database import AppointmentSession, Appointment
                db = AppointmentSession()
                try:
                    params = {"user_id":"user_001","title":"Meeting","start_time":"2026-09-13 10:00","end_time":"2026-09-13 11:00","location":"Room A","notes":""}
                    res = execute_function("appointment_making", params, db)
                    print(f"Booking result: {res}")
                finally:
                    db.close()
            # Order DB
            elif result["function_call"] == "order_booking":
                from database import OrderSession, Order
                db = OrderSession()
                try:
                    params = {"user_id":"user_001","item_name":"Coffee","quantity":2,"price":5.0,"total":10.0}
                    res = execute_function("order_booking", params, db)
                    print(f"Order result: {res}")
                finally:
                    db.close()

        return result