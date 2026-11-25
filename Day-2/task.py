import json, functools
from openai import RateLimitError, APIConnectionError

MODEL = "openai/gpt-oss-20b"


SERVICES = {
    "general wellness consultation": 300,
    "personalized diet plan": 500,
    "basic health checkup": 800,
}

SYSTEM = f"""ROLE:   You are the friendly assistant for KindCare Companion.
FACTS:  Services with prices in rupees: {json.dumps(SERVICES)}
        Appointments need 24 hours' notice. Online and in-person slots are available.
RULES:  Never diagnose medical conditions or promise exact doctor wait times. If it isn't in FACTS, say "I'll check with our care coordinator."
        Remember the user's name and chosen service during the chat.
FORMAT: Under 50 words, friendly, English or Telugu matching the user."""

def log_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        print(f"   [log] {func.__name__}{args} -> {result!r}")
        return result
    return wrapper

@log_call
def get_price(item: str, qty: int = 1) -> int:
    """Return the total price in rupees for qty of a service in SERVICES."""
    return MENU[item.lower().strip()] * qty

history = [{"role": "system", "content": SYSTEM}]
MAX_TURNS = 8

def chat(user_text: str) -> str:
    history.append({"role": "user", "content": user_text})
    recent = [history[0]] + history[1:][-MAX_TURNS:]
    try:
        response = client.chat.completions.create(model=MODEL, messages=recent, temperature=0.3)
        reply = response.choices[0].message.content
    except RateLimitError:
        reply = "We're a little busy. Please try again in a minute."
    except APIConnectionError:
        reply = "I can't reach the server right now. Please try again shortly."
    history.append({"role": "assistant", "content": reply})
    return reply


while True:
    text = input("You: ")
    if text.lower().strip() in ("bye", "exit", "quit"):
        print("Bot:Take care! Thank you for reaching out to KindCare Companion.")
        break
    print("Bot:", chat(text))
