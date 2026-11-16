from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.flight_search import search_flights, build_engine_links, resolve_iata
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
    orig_code = resolve_iata(origin)
    dest_code = resolve_iata(destination)
    links = build_engine_links(
        orig_code, dest_code, departure_date, return_date, cabin.lower()
    )
    flights = search_flights(origin, destination, departure_date, return_date, cabin)
    result = choose_best(flights, preferences, has_carry_on)
    result["booking_links"] = links
    return result