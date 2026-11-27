#setup
!pip install -q langchain langchain-groq gspread

import os
from google.colab import userdata, auth
os.environ["GROQ_API_KEY"] = userdata.get("AIagentsession2")

from langchain_groq import ChatGroq
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.2, max_retries=3)

auth.authenticate_user()
import gspread
from google.auth import default
creds, _ = default()
gc = gspread.authorize(creds)
sh = gc.create("SwiftRoute Travel Bookings")      # run once; next time use gc.open("SwiftRoute Travel Bookings")
ws = sh.sheet1
ws.append_row(["name", "destination", "seats", "travel_date", "ac_sleeper", "total"])
print("Sheet ready:", sh.url)
#Sheet ready: https://docs.google.com/spreadsheets/d/1ccZtl915ImS4piXGbKEDDapRayzQP1k46QuN9l75qlA



#Data, the Order model and three tools
from typing import Literal
from pydantic import BaseModel, Field
from langchain.tools import tool

FARES = {"hyderabad": 850, "bangalore": 1200, "chennai": 1100, "vijayawada": 450, "tirupati": 950}
TIMINGS = {
    "hyderabad": "8:00 PM & 10:30 PM",
    "bangalore": "6:30 PM & 9:00 PM",
    "chennai": "7:15 PM & 10:00 PM",
    "vijayawada": "7:00 AM, 2:00 PM & 9:30 PM",
    "tirupati": "7:30 PM & 9:45 PM"
}

class TicketBooking(BaseModel):
    """A bus ticket booking taken from a customer's chat message."""
    name: str = Field(description="Passenger's first name")
    destination: Literal["hyderabad", "bangalore", "chennai", "vijayawada", "tirupati"] = Field(description="Destination city")
    seats: int = Field(description="Number of seats", ge=1)
    travel_date: str = Field(description="Travel date as the customer said it")
    ac_sleeper: bool = Field(description="True if the passenger asked for AC Sleeper; False for Semi-Sleeper")

extractor = llm.with_structured_output(TicketBooking)
#ADDED FIVE MESSY MESSAGES
messy_messages = [
    "hi bro need two ac slpr tickets to hydrabad on 28 nov, im karthik",
    "Good morning!! My cousin has a function so I want 1 semi sleeper seat to vijayawada tomorrow, name is Priya",
    "for 15 dec book three seats chennai pls... AC sleeper if available. - Rajesh",
    "hey can u check & book 2 tix to banglore for sunday? Divya here",
    "tirupati 4 seats ac sleeper 2nd dec, Suresh speaking",
]

for i, msg in enumerate(messy_messages, start=1):
    try:
        parsed = extractor.invoke(msg)
        print(f"Message {i}: {msg}")
        print(f"Extracted: {parsed}\n")
    except Exception as e:
        print(f"Message {i}: {msg}")
        print(f"Could not parse structured output: {e}\n")
#TOOLS
@tool
def get_ticket_fare(destination: str, seats: int = 1) -> str:
    """Get the base Semi-Sleeper ticket fare in rupees for a destination and seat count.

    Args:
        destination: Destination city, e.g. "hyderabad", "bangalore", "chennai", "vijayawada", or "tirupati"
        seats: Number of seats the passenger wants to book
    """
    fare = FARES.get(destination.lower().strip())
    if fare is None:
        return f"We don't operate buses to '{destination}'. Available routes: {', '.join(FARES)}."
    return f"{seats} x {destination.title()} (Semi-Sleeper) = Rs {fare * seats}"

@tool
def get_bus_timings(destination: str) -> str:
    """Check daily bus departure timings for a destination city, e.g. "hyderabad"."""
    schedule = TIMINGS.get(destination.lower().strip())
    return f"Buses to {destination.title()} depart daily at {schedule}." if schedule else f"No scheduled buses found for '{destination}'."

@tool
def book_ticket(name: str, destination: str, seats: int, travel_date: str, ac_sleeper: bool) -> str:
    """Save a confirmed travel ticket booking to the Bookings sheet.
    Use only when the passenger has given their name, destination, seat count, and travel date."""
    try:
        booking = TicketBooking(
            name=name,
            destination=destination.lower().strip(),
            seats=seats,
            travel_date=travel_date,
            ac_sleeper=ac_sleeper
        )
    except Exception as e:
        return f"Could not complete booking: {e}. Ask the passenger to correct it."
    
    # AC Sleeper adds Rs 300 per seat
    ac_upgrade = 300 * booking.seats if booking.ac_sleeper else 0
    total = (FARES[booking.destination] * booking.seats) + ac_upgrade
    
    ws.append_row([
        booking.name, booking.destination, booking.seats, booking.travel_date,
        "yes" if booking.ac_sleeper else "no", total
    ])
    coach = "AC Sleeper" if booking.ac_sleeper else "Semi-Sleeper"
    return f"Booked: {booking.seats} {coach} seat(s) to {booking.destination.title()} for {booking.name} on {booking.travel_date}, Total: Rs {total}."


#RESULT OF FIVE MESSY QUESTIONS

# Message 1: hi bro need two ac slpr tickets to hydrabad on 28 nov, im karthik
# Extracted: name='karthik' destination='hyderabad' seats=2 travel_date='28 nov' ac_sleeper=True

# Message 2: Good morning!! My cousin has a function so I want 1 semi sleeper seat to vijayawada tomorrow, name is Priya
# Extracted: name='Priya' destination='vijayawada' seats=1 travel_date='tomorrow' ac_sleeper=False

# Message 3: for 15 dec book three seats chennai pls... AC sleeper if available. - Rajesh
# Extracted: name='Rajesh' destination='chennai' seats=3 travel_date='15 dec' ac_sleeper=True

# Message 4: hey can u check & book 2 tix to banglore for sunday? Divya here
# Could not parse structured output: Error code: 400 - {'error': {'message': 'Tool choice is required, but model did not call a tool', 'type': 'invalid_request_error', 'code': 'tool_use_failed', 'failed_generation': 'Sure thing! Just to make sure I get everything right, would you like the tickets in AC Sleeper or Semi‑Sleeper?'}}

# Message 5: tirupati 4 seats ac sleeper 2nd dec, Suresh speaking
# Extracted: name='Suresh' destination='tirupati' seats=4 travel_date='2nd dec' ac_sleeper=True

#THE AGENT
from langchain.agents import create_agent

SYSTEM = """ROLE:   You are the friendly ticket booking assistant for SwiftRoute Travels.
FACTS:  All routes have Semi-Sleeper and AC Sleeper coaches. AC Sleeper costs Rs 300 extra per seat. Passengers must carry a valid Govt ID.
RULES:  Always use get_ticket_fare for prices and get_bus_timings for schedules; never guess them.
        Before calling book_ticket, ensure you have name, destination, seats, and travel date; ask if missing.
        After booking, read the ticket details back with the total fare.
FORMAT: Under 60 words, friendly, English or Telugu matching the passenger."""

agent = create_agent(
    model=llm,
    tools=[get_ticket_fare, get_bus_timings, book_ticket],
    system_prompt=SYSTEM
)

history = []
def chat(text: str) -> str:
    global history
    try:
        result = agent.invoke({"messages": history + [{"role": "user", "content": text}]})
        history = result["messages"]                  # keep the whole run as memory
        return history[-1].content
    except Exception as e:
        print("Agent error:", e)
        return "Sorry, our booking server is a little busy. Please try again in a minute."


print(chat("I'm Karthik. Book 2 AC sleeper seats to Hyderabad for 28 Nov."))   # check your sheet!
print(chat("I'm Vara. Book 3 AC sleeper seats to bangalore for 29 Nov."))   # check your sheet!
print(chat("I'm kohli. Book 4 AC sleeper seats to bangalore for 3 june."))   # check your sheet!
print(chat("I'm thala. Book 7 AC sleeper seats to chennai for 7 july."))   # check your sheet!

#OUTPUT: Hi Karthik! Your 2 AC Sleeper seats to Hyderabad on 28 Nov are booked. Total fare Rs 2300. Please bring a valid Govt ID on the day. Safe travels!
# Hey Vara! Your 3 AC Sleeper seats to Bangalore on 29 Nov are booked. Total fare Rs 4500. Don’t forget your Govt ID. Have a great trip!
# Hi Kohli! Your 4 AC Sleeper seats to Bangalore on 3 June are booked. Total fare Rs 6000. Remember to carry a valid Govt ID. Safe travels!
# Hey Thala! Your 7 AC Sleeper seats to Chennai on 7 July are booked. Total fare Rs 9800. Bring a valid Govt ID. Enjoy the trip!


#See what it did
for m in history:
    m.pretty_print()        # question → tool calls → tool results → answers
# ================================ Human Message =================================

# I'm Karthik. Book 2 AC sleeper seats to Hyderabad for 28 Nov.
# ================================== Ai Message ==================================
# Tool Calls:
#   get_ticket_fare (fc_7216db65-5542-4eb8-941f-fd62fb4a0b43)
#  Call ID: fc_7216db65-5542-4eb8-941f-fd62fb4a0b43
#   Args:
#     destination: hyderabad
#     seats: 2
# ================================= Tool Message =================================
# Name: get_ticket_fare

# 2 x Hyderabad (Semi-Sleeper) = Rs 1700
# ================================== Ai Message ==================================
# Tool Calls:
#   book_ticket (fc_b5f28501-5f47-4de9-81af-cac68be530c3)
#  Call ID: fc_b5f28501-5f47-4de9-81af-cac68be530c3
#   Args:
#     ac_sleeper: True
#     destination: hyderabad
#     name: Karthik
#     seats: 2
#     travel_date: 28 Nov
# ================================= Tool Message =================================
# Name: book_ticket

# Booked: 2 AC Sleeper seat(s) to Hyderabad for Karthik on 28 Nov, Total: Rs 2300.
# ================================== Ai Message ==================================

# Hi Karthik! Your 2 AC Sleeper seats to Hyderabad on 28 Nov are booked. Total fare Rs 2300. Please bring a valid Govt ID. Safe travels!
# ================================ Human Message =================================

# I'm Vara. Book 3 AC sleeper seats to bangalore for 29 Nov.
# ================================== Ai Message ==================================
# Tool Calls:
#   get_ticket_fare (fc_eab82408-62bf-43f9-9994-ed29001f28d3)
#  Call ID: fc_eab82408-62bf-43f9-9994-ed29001f28d3
#   Args:
#     destination: bangalore
#     seats: 3
# ================================= Tool Message =================================
# Name: get_ticket_fare

# 3 x Bangalore (Semi-Sleeper) = Rs 3600
# ================================== Ai Message ==================================
# Tool Calls:
#   book_ticket (fc_5c5dfb77-8abc-4dff-9f0c-e0a91bb98326)
#  Call ID: fc_5c5dfb77-8abc-4dff-9f0c-e0a91bb98326
#   Args:
#     ac_sleeper: True
#     destination: bangalore
#     name: Vara
#     seats: 3
#     travel_date: 29 Nov
# ================================= Tool Message =================================
# Name: book_ticket

# Booked: 3 AC Sleeper seat(s) to Bangalore for Vara on 29 Nov, Total: Rs 4500.
# ================================== Ai Message ==================================

# Hey Vara! Your 3 AC Sleeper seats to Bangalore on 29 Nov are booked. Total fare Rs 4500. Don’t forget your Govt ID. Have a great trip!
# ================================ Human Message =================================

# I'm kohli. Book 4 AC sleeper seats to bangalore for 3 june.
# ================================== Ai Message ==================================
# Tool Calls:
#   get_ticket_fare (fc_8cbba87d-6b12-462b-b810-cffbd26f03d1)
#  Call ID: fc_8cbba87d-6b12-462b-b810-cffbd26f03d1
#   Args:
#     destination: bangalore
#     seats: 4
# ================================= Tool Message =================================
# Name: get_ticket_fare

# 4 x Bangalore (Semi-Sleeper) = Rs 4800
# ================================== Ai Message ==================================
# Tool Calls:
#   book_ticket (fc_6451ada8-522e-4e05-b629-b3226fe74c58)
#  Call ID: fc_6451ada8-522e-4e05-b629-b3226fe74c58
#   Args:
#     ac_sleeper: True
#     destination: bangalore
#     name: kohli
#     seats: 4
#     travel_date: 3 June
# ================================= Tool Message =================================
# Name: book_ticket

# Booked: 4 AC Sleeper seat(s) to Bangalore for kohli on 3 June, Total: Rs 6000.
# ================================== Ai Message ==================================

# Hi Kohli! Your 4 AC Sleeper seats to Bangalore on 3 June are booked. Total fare Rs 6000. Remember to carry a valid Govt ID. Safe travels!
# ================================ Human Message =================================

# I'm thala. Book 7 AC sleeper seats to chennai for 7 july.
# ================================== Ai Message ==================================
# Tool Calls:
#   get_ticket_fare (fc_33f5836c-90d1-465d-b8ca-47502d5b4aaa)
#  Call ID: fc_33f5836c-90d1-465d-b8ca-47502d5b4aaa
#   Args:
#     destination: chennai
#     seats: 7
# ================================= Tool Message =================================
# Name: get_ticket_fare

# 7 x Chennai (Semi-Sleeper) = Rs 7700
# ================================== Ai Message ==================================
# Tool Calls:
#   book_ticket (fc_4cf5c2c8-132f-419e-96b3-49fc9d7fbc33)
#  Call ID: fc_4cf5c2c8-132f-419e-96b3-49fc9d7fbc33
#   Args:
#     ac_sleeper: True
#     destination: chennai
#     name: thala
#     seats: 7
#     travel_date: 7 July
# ================================= Tool Message =================================
# Name: book_ticket

# Booked: 7 AC Sleeper seat(s) to Chennai for thala on 7 July, Total: Rs 9800.
# ================================== Ai Message ==================================

# Hey Thala! Your 7 AC Sleeper seats to Chennai on 7 July are booked. Total fare Rs 9800. Bring a valid Govt ID. Enjoy the trip!





