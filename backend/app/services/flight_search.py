import time
from datetime import datetime
from fli.models import (
    Airport,
    FlightSearchFilters,
    FlightSegment,
    PassengerInfo,
    SeatType,
    SortBy,
    TripType,
)
from fli.search import SearchFlights

CACHE: dict[tuple, tuple[float, list[dict]]] = {}
CACHE_TTL = 600  # 10 minutes
_LAST_CALL_TS = 0.0

CITY_TO_IATA = {
    "AMSTERDAM": "AMS",
    "AMSTERDAM SCHIPHOL": "AMS",
    "ROTTERDAM": "RTM",
    "EINDHOVEN": "EIN",
    "BRUSSELS": "BRU",
    "LONDON": "LHR",
    "LONDON HEATHROW": "LHR",
    "LONDON STANSTED": "STN",
    "LONDON GATWICK": "LGW",
    "LONDON LUTON": "LTN",
    "MANCHESTER": "MAN",
    "EDINBURGH": "EDI",
    "DUBLIN": "DUB",
    "PARIS": "CDG",
    "PARIS ORLY": "ORY",
    "LYON": "LYS",
    "NICE": "NCE",
    "MADRID": "MAD",
    "BARCELONA": "BCN",
    "MALAGA": "AGP",
    "LISBON": "LIS",
    "PORTO": "OPO",
    "ROME": "FCO",
    "MILAN": "MXP",
    "VENICE": "VCE",
    "BERLIN": "BER",
    "FRANKFURT": "FRA",
    "MUNICH": "MUC",
    "ZURICH": "ZRH",
    "GENEVA": "GVA",
    "VIENNA": "VIE",
    "PRAGUE": "PRG",
    "WARSAW": "WAW",
    "COPENHAGEN": "CPH",
    "STOCKHOLM": "ARN",
    "OSLO": "OSL",
    "ATHENS": "ATH",
    "ISTANBUL": "IST",
    "DUBAI": "DXB",
    "ABU DHABI": "AUH",
    "DOHA": "DOH",
    "NEW YORK": "JFK",
    "NEW YORK CITY": "JFK",
    "NEWARK": "EWR",
    "LOS ANGELES": "LAX",
    "SAN FRANCISCO": "SFO",
    "CHICAGO": "ORD",
    "MIAMI": "MIA",
    "BOSTON": "BOS",
    "TORONTO": "YYZ",
    "VANCOUVER": "YVR",
    "TOKYO": "HND",
    "SINGAPORE": "SIN",
    "BANGKOK": "BKK",
    "SEOUL": "ICN",
    "SYDNEY": "SYD",
    "DELHI": "DEL",
    "MUMBAI": "BOM",
}

SEAT_MAP = {
    "economy": SeatType.ECONOMY,
    "premium_economy": SeatType.PREMIUM_ECONOMY,
    "business": SeatType.BUSINESS,
    "first": SeatType.FIRST,
}


def resolve_iata(location: str) -> str:
    clean = location.strip().upper()
    if "(" in clean and ")" in clean:
        code = clean.split("(")[-1].split(")")[0].strip()
        if len(code) == 3:
            return code
    return CITY_TO_IATA.get(clean, clean)


def build_engine_links(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    cabin: str = "economy",
) -> dict:
    orig = origin.upper()
    dest = destination.upper()
    dep_dt = datetime.strptime(departure_date, "%Y-%m-%d")
    dep_yymmdd = dep_dt.strftime("%y%m%d")

    sky_cabin = {
        "economy": "economy",
        "premium_economy": "premiumeconomy",
        "business": "business",
        "first": "first",
    }.get(cabin, "economy")

    kayak_cabin = {
        "economy": "",
        "premium_economy": "/premium",
        "business": "/business",
        "first": "/first",
    }.get(cabin, "")

    if return_date:
        ret_dt = datetime.strptime(return_date, "%Y-%m-%d")
        ret_yymmdd = ret_dt.strftime("%y%m%d")
        return {
            "google_flights": (
                f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}"
                f"%20from%20{orig}%20on%20{departure_date}%20through%20{return_date}%20{cabin}"
            ),
            "skyscanner": f"https://www.skyscanner.net/transport/flights/{orig.lower()}/{dest.lower()}/{dep_yymmdd}/{ret_yymmdd}/?cabinclass={sky_cabin}",
            "kiwi": f"https://www.kiwi.com/en/search/results/{orig}/{dest}/{departure_date}/{return_date}",
            "kayak": f"https://www.kayak.com/flights/{orig}-{dest}/{departure_date}/{return_date}{kayak_cabin}?sort=price_a",
        }

    return {
        "google_flights": (
            f"https://www.google.com/travel/flights?q=Flights%20to%20{dest}"
            f"%20from%20{orig}%20on%20{departure_date}%20oneway%20{cabin}"
        ),
        "skyscanner": f"https://www.skyscanner.net/transport/flights/{orig.lower()}/{dest.lower()}/{dep_yymmdd}/?cabinclass={sky_cabin}",
        "kiwi": f"https://www.kiwi.com/en/search/results/{orig}/{dest}/{departure_date}/no-return",
        "kayak": f"https://www.kayak.com/flights/{orig}-{dest}/{departure_date}{kayak_cabin}?sort=price_a",
    }


def _fetch_leg(dep_airport, arr_airport, travel_date: str, seat_type) -> list:
    global _LAST_CALL_TS
    filters = FlightSearchFilters(
        trip_type=TripType.ONE_WAY,
        passenger_info=PassengerInfo(adults=1),
        flight_segments=[
            FlightSegment(
                departure_airport=[[dep_airport, 0]],
                arrival_airport=[[arr_airport, 0]],
                travel_date=travel_date,
            )
        ],
        seat_type=seat_type,
        sort_by=SortBy.CHEAPEST,
    )

    for attempt in range(2):
        elapsed = time.time() - _LAST_CALL_TS
        if elapsed < 2.2:
            time.sleep(2.2 - elapsed)

        _LAST_CALL_TS = time.time()
        try:
            res = SearchFlights().search(filters)
            if res:
                return res
        except Exception as e:
            print(f"[TrueFare Guru] Attempt {attempt + 1} paused: {e}")
            if "429" in str(e):
                time.sleep(5)
    return []


def _format_legs(legs) -> list[dict]:
    return [
        {
            "airline": leg.airline.value,
            "flight_number": f"{leg.airline.name} {leg.flight_number}",
            "from": leg.departure_airport.name,
            "to": leg.arrival_airport.name,
            "departs": str(leg.departure_datetime),
            "arrives": str(leg.arrival_datetime),
        }
        for leg in legs
    ]


def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str | None = None,
    cabin: str = "economy",
) -> list[dict]:
    orig_code = resolve_iata(origin)
    dest_code = resolve_iata(destination)
    cabin_clean = cabin.lower()

    cache_key = (orig_code, dest_code, departure_date, return_date, cabin_clean)
    now = time.time()
    if cache_key in CACHE:
        cached_time, cached_offers = CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return cached_offers

    seat_type = SEAT_MAP.get(cabin_clean, SeatType.ECONOMY)
    dep_airport = getattr(Airport, orig_code)
    arr_airport = getattr(Airport, dest_code)

    engine_links = build_engine_links(
        orig_code, dest_code, departure_date, return_date, cabin_clean
    )
    offers = []
    cabin_label = cabin_clean.replace("_", " ").title()

    outbound_list = _fetch_leg(dep_airport, arr_airport, departure_date, seat_type)

    if return_date and outbound_list:
        inbound_list = _fetch_leg(arr_airport, dep_airport, return_date, seat_type)
        if inbound_list:
            for out_f in outbound_list[:5]:
                for in_f in inbound_list[:2]:
                    airlines = ", ".join(
                        {leg.airline.value for leg in out_f.legs + in_f.legs}
                    )
                    flight_nums = " / ".join(
                        [f"{l.airline.name} {l.flight_number}" for l in out_f.legs]
                        + [f"{l.airline.name} {l.flight_number}" for l in in_f.legs]
                    )
                    offers.append({
                        "airline": airlines,
                        "flight_numbers": flight_nums,
                        "route": f"{orig_code} ⇄ {dest_code}",
                        "cabin": cabin_label,
                        "price": round(out_f.price + in_f.price, 2),
                        "stops": out_f.stops + in_f.stops,
                        "duration_mins": out_f.duration + in_f.duration,
                        "departure": f"Out: {out_f.legs[0].departure_datetime} → {out_f.legs[-1].arrival_datetime}",
                        "arrival": f"Ret: {in_f.legs[0].departure_datetime} → {in_f.legs[-1].arrival_datetime}",
                        "segments": _format_legs(out_f.legs) + _format_legs(in_f.legs),
                        "trip_type": "Round-trip",
                        "booking_links": engine_links,
                    })
        else:
            for out_f in outbound_list[:5]:
                airlines = ", ".join({leg.airline.value for leg in out_f.legs})
                flight_nums = " → ".join(
                    f"{l.airline.name} {l.flight_number}" for l in out_f.legs
                )
                offers.append({
                    "airline": airlines,
                    "flight_numbers": f"{flight_nums} (Outbound)",
                    "route": f"{orig_code} ⇄ {dest_code}",
                    "cabin": cabin_label,
                    "price": round(out_f.price * 2, 2),
                    "stops": out_f.stops,
                    "duration_mins": out_f.duration,
                    "departure": str(out_f.legs[0].departure_datetime),
                    "arrival": f"Est. round-trip (return {return_date})",
                    "segments": _format_legs(out_f.legs),
                    "trip_type": "Round-trip (Est.)",
                    "booking_links": engine_links,
                })
    elif not return_date:
        for item in outbound_list:
            airlines = ", ".join({leg.airline.value for leg in item.legs})
            flight_nums = " → ".join(
                f"{l.airline.name} {l.flight_number}" for l in item.legs
            )
            offers.append({
                "airline": airlines,
                "flight_numbers": flight_nums,
                "route": f"{orig_code} → {dest_code}",
                "cabin": cabin_label,
                "price": item.price,
                "stops": item.stops,
                "duration_mins": item.duration,
                "departure": str(item.legs[0].departure_datetime),
                "arrival": str(item.legs[-1].arrival_datetime),
                "segments": _format_legs(item.legs),
                "trip_type": "One-way",
                "booking_links": engine_links,
            })

    if not offers:
        return []

    offers.sort(key=lambda x: x["price"])
    final_offers = offers[:10]
    CACHE[cache_key] = (now, final_offers)
    return final_offers