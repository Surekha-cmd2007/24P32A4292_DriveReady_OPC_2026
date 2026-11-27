# SwiftRoute Travels — AI Ticket Booking Agent

An AI-powered conversational booking agent built with **LangChain**, **Groq (`openai/gpt-oss-20b`)**, **Pydantic**, and **Google Sheets (`gspread`)**. The agent answers route timing and fare inquiries, validates passenger booking details using structured schemas, and logs confirmed reservations directly to a live Google Sheet.



## Agent Overview

This notebook implements a tool-calling agent in Google Colab across four main sections:

1. **Environment & Google Sheets Integration:** Authenticates with Google Colab credentials, initializes the Groq LLM, and creates a `SwiftRoute Travel Bookings` spreadsheet with columns: `name`, `destination`, `seats`, `travel_date`, `ac_sleeper`, and `total`.
2. **Data Validation & Custom Tools:** Uses a Pydantic `BaseModel` (`TicketBooking`) and LangChain `@tool` functions (`get_ticket_fare`, `get_bus_timings`, and `book_ticket`) to enforce strict business rules and prevent guessed fares or schedules.
3. **Stateful Conversational Agent:** Built with `create_agent`, maintaining multi-turn conversation history so passengers can ask about schedules or fares first and confirm bookings in follow-up messages.
4. **Structured Extraction & Trace Inspection:** Tests `with_structured_output()` against noisy customer messages and uses `.pretty_print()` to inspect and count model and tool invocations per turn.


## Key Components & Tools

| Component / Tool | Purpose |

`TicketBooking` (Pydantic Model)** | Validates passenger `name`, allowed `destination` (`Literal`), positive `seats` count (`ge=1`), `travel_date`, and `ac_sleeper` boolean preference. |
`get_ticket_fare(destination, seats)`** | Looks up base Semi-Sleeper ticket fares in rupees and calculates subtotals without guessing. |
`get_bus_timings(destination)`** | Retrieves daily bus departure schedules for supported routes (Hyderabad, Bangalore, Chennai, Vijayawada, Tirupati). |
`book_ticket(...)`** | Validates the booking through `TicketBooking`, adds the Rs 300/seat AC Sleeper upgrade if requested, appends the confirmed row to Google Sheets, and returns a booking summary. |



 Exercises Completed

 1. Structured Output Testing (`with_structured_output`)
* Attached the `TicketBooking` Pydantic schema directly to `ChatGroq` via `llm.with_structured_output(TicketBooking)`.
* Tested extraction across **5 messy customer messages** containing typos (e.g., *"hydrabad"*, *"banglore"*), informal phrasing, written numbers (*"two"*, *"three"*), and missing coach preferences (handled cleanly with `default=False` and `try/except` error handling).

 2. Execution Trace Analysis (`pretty_print()`)
* Inspected the internal LangChain message trace (`HumanMessage` -> `AIMessage` -> `ToolMessage` -> `AIMessage`) for a multi-part query (*"What are the bus timings to Hyderabad? How much for 2 tickets?"*).
* Counted exact execution steps per turn:
  * **Model Calls (`AIMessage`):** 2 calls (1st call selects the required tools; 2nd call synthesizes the tool outputs into a concise response).
  * **Tool Calls:** 2 calls (`get_bus_timings` and `get_ticket_fare`).






## Sample Question & Call Counts

* **Question:** `"What are the bus timings to Tirupati? How much for 3 tickets?"`
* **Tool Calls (2):**
  1. `get_bus_timings(destination="tirupati")`
  2. `get_ticket_fare(destination="tirupati", seats=3)`
* **Model Calls (2):**
  1. First `AIMessage` decides to call `get_bus_timings` and `get_ticket_fare`.
  2. Second `AIMessage` reads both tool outputs and writes the final reply under 60 words.
