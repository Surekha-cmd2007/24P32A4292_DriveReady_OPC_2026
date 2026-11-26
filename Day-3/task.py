!pip install -q langchain langchain-groq

import os
from google.colab import userdata
os.environ["GROQ_API_KEY"] = userdata.get("AIagentsession2")   # LangChain reads it from here

from langchain_groq import ChatGroq
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=1.0)

# The assistant: template + memory + chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser

SYSTEM = """ROLE:   You are the friendly assistant for KindCare Companion.
FACTS:  Services with prices in rupees
        Appointments need 24 hours' notice. Online and in-person slots are available.general wellness consultation 300,
    personalized diet plan 500,basic health checkup 800.
RULES:  Never diagnose medical conditions or promise exact doctor wait times. If it isn't in FACTS, say "I'll check with our care coordinator."
        Remember the user's name and chosen service during the chat.
FORMAT: Under 50 words, friendly, English or Telugu matching the user."""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    MessagesPlaceholder("history"),          # the chat so far goes here
    ("human", "{question}"),
])
chain = prompt | llm | StrOutputParser()

history = []
def ask(question: str) -> str:
    answer = chain.invoke({"history": history, "question": question})
    history.extend([("human", question), ("ai", answer)])
    return answer

print(ask("Hi, I'm surekha,how long i should wait for doctor?"))
print(ask("What's my name?"))


#tests

import csv

def run_tests(path: str = "/content/test1.csv") -> None:
    rows = list(csv.DictReader(open(path)))
    passed = 0
    for row in rows:
        answer = chain.invoke({"history": [], "question": row["question"]})
        ok = row["must_include"].lower() in answer.lower()
        passed += ok
        print("PASS" if ok else "FAIL", "|", row["question"], "→", answer[:70])
    print(f"\n{passed}/{len(rows)} passed ({passed / len(rows):.0%})")



run_tests()
"""PASS | How much is the fee for a basic health checkup? → The basic health checkup costs ₹800. Remember to book at least 24 hour
FAIL | Will the doctor be available 24/7? → Our doctors are available during scheduled slots and we require a 24‑h
FAIL | If I come today at 10 AM → Sorry, we need 24‑hour notice. Could you let me know your name and whi
PASS | How much is the fee for a general health consultation for 3 people? → For a general wellness consultation, it’s ₹300 per person. For 3 peopl
FAIL | Are online slots available? → Yes, we offer online slots! Just give us 24‑hour notice to book. Let m
FAIL | Are in-person slots available? → Yes, we offer in‑person slots! Just give us a 24‑hour notice to book. 
FAIL | Can I get an appointment for tomorrow? → I’m sorry, but we need a 24‑hour notice for appointments. Tomorrow’s s
FAIL | Are medicines available? → I’ll check with our care coordinator and get back to you shortly.
PASS | How much is the fee for a personalized diet plan? → The personalized diet plan costs ₹500. Let me know if you’d like to bo
FAIL | How much is the fee for a personalized diet plan for 2 people? → The personalized diet plan is ₹500 per person, so for two people it wo

3/10 passed (30%)



 """
#Sneak peek: the same assistant as a LangChain agent
from langchain.agents import create_agent

agent_order = create_agent(model=llm, tools=[], system_prompt=SYSTEM)   # tools come tomorrow
result_order = agent_order.invoke({"messages": [{"role": "user", "content": "Do you make eggless cakes?"}]})
print(result_order["messages"][-1].content)
