from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.flight_search import search_flights
from app.agents.ranking import choose_best

app = FastAPI(title="TrueFare Guru API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"status": "online", "agent": "TrueFare Guru"}


@app.get("/search")
def search(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    cabin: str = "economy",
):
    return search_flights(origin, destination, departure_date, return_date, cabin)


@app.get("/best-flight")
def best_flight(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    cabin: str = "economy",
    preferences: str = "cheapest overall",
    has_carry_on: bool = False,
):
    flights = search_flights(origin, destination, departure_date, return_date, cabin)
    return choose_best(flights, preferences, has_carry_on)