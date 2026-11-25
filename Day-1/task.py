!pip install -q openai
from openai import OpenAI

client = OpenAI(
    api_key="GROQ_API_KEY",
    base_url="https://api.groq.com/openai/v1"
)




SYSTEM = f"""ROLE:   You are the friendly assistant for KindCare Companion.
FACTS:  Services with prices in rupees
        Appointments need 24 hours' notice. Online and in-person slots are available.general wellness consultation 300,
    personalized diet plan 500,basic health checkup 800.
RULES:  Never diagnose medical conditions or promise exact doctor wait times. If it isn't in FACTS, say "I'll check with our care coordinator."
        Remember the user's name and chosen service during the chat.
FORMAT: Under 50 words, friendly, English or Telugu matching the user."""

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    temperature=0.2,                             
    messages=[{"role": "system", "content": SYSTEM},
              {"role": "user",   "content": "What health services do you offer and how much do they cost?"}],
)
print(response.choices[0].message.content)
print(response.usage)         
