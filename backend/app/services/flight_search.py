import os
import time
from datetime import datetime
import requests
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
    # Netherlands & Benelux
    "AMSTERDAM": "AMS",
    "AMSTERDAM SCHIPHOL": "AMS",
    "ROTTERDAM": "RTM",
    "EINDHOVEN": "EIN",
    "MAASTRICHT": "MST",
    "GRONINGEN": "GRQ",
    "BRUSSELS": "BRU",
    "BRUSSELS CHARLEROI": "CRL",
    "ANTWERP": "ANR",
    "LUXEMBOURG": "LUX",
    # UK & Ireland
    "LONDON": "LHR",
    "LONDON HEATHROW": "LHR",
    "LONDON GATWICK": "LGW",
    "LONDON STANSTED": "STN",
    "LONDON LUTON": "LTN",
    "LONDON CITY": "LCY",
    "MANCHESTER": "MAN",
    "BIRMINGHAM": "BHX",
    "EDINBURGH": "EDI",
    "GLASGOW": "GLA",
    "BRISTOL": "BRS",
    "NEWCASTLE": "NCL",
    "BELFAST": "BFS",
    "DUBLIN": "DUB",
    "CORK": "ORK",
    # Western & Central Europe
    "PARIS": "CDG",
    "PARIS CHARLES DE GAULLE": "CDG",
    "PARIS ORLY": "ORY",
    "PARIS BEAUVAIS": "BVA",
    "LYON": "LYS",
    "NICE": "NCE",
    "MARSEILLE": "MRS",
    "TOULOUSE": "TLS",
    "BORDEAUX": "BOD",
    "NANTES": "NTE",
    "BERLIN": "BER",
    "FRANKFURT": "FRA",
    "MUNICH": "MUC",
    "HAMBURG": "HAM",
    "DUSSELDORF": "DUS",
    "COLOGNE": "CGN",
    "STUTTGART": "STR",
    "HANOVER": "HAJ",
    "NUREMBERG": "NUE",
    "ZURICH": "ZRH",
    "GENEVA": "GVA",
    "BASEL": "BSL",
    "VIENNA": "VIE",
    "SALZBURG": "SZG",
    "INNSBRUCK": "INN",
    # Southern Europe & Mediterranean
    "MADRID": "MAD",
    "BARCELONA": "BCN",
    "MALAGA": "AGP",
    "ALICANTE": "ALC",
    "VALENCIA": "VLC",
    "SEVILLE": "SVQ",
    "PALMA DE MALLORCA": "PMI",
    "MALLORCA": "PMI",
    "IBIZA": "IBZ",
    "TENERIFE": "TFS",
    "GRAN CANARIA": "LPA",
    "BILBAO": "BIO",
    "LISBON": "LIS",
    "PORTO": "OPO",
    "FARO": "FAO",
    "ROME": "FCO",
    "ROME FIUMICINO": "FCO",
    "ROME CIAMPINO": "CIA",
    "MILAN": "MXP",
    "MILAN MALPENSA": "MXP",
    "MILAN LINATE": "LIN",
    "BERGAMO": "BGY",
    "VENICE": "VCE",
    "BOLOGNA": "BLQ",
    "NAPLES": "NAP",
    "FLORENCE": "FLR",
    "PALERMO": "PMO",
    "CATANIA": "CTA",
    "ATHENS": "ATH",
    "THESSALONIKI": "SKG",
    "SANTORINI": "JTR",
    "MYKONOS": "JMK",
    "HERAKLION": "HER",
    "MALTA": "MLA",
    "LARNACA": "LCA",
    "ISTANBUL": "IST",
    "ISTANBUL SABIHA": "SAW",
    "ANTALYA": "AYT",
    "IZMIR": "ADB",
    # Northern & Eastern Europe
    "COPENHAGEN": "CPH",
    "BILLUND": "BLL",
    "STOCKHOLM": "ARN",
    "GOTHENBURG": "GOT",
    "OSLO": "OSL",
    "BERGEN": "BGO",
    "HELSINKI": "HEL",
    "REYKJAVIK": "KEF",
    "PRAGUE": "PRG",
    "WARSAW": "WAW",
    "KRAKOW": "KRK",
    "GDANSK": "GDN",
    "BUDAPEST": "BUD",
    "BUCHAREST": "OTP",
    "SOFIA": "SOF",
    "ZAGREB": "ZAG",
    "SPLIT": "SPU",
    "DUBROVNIK": "DBV",
    "BELGRADE": "BEG",
    "RIGA": "RIX",
    "TALLINN": "TLL",
    "VILNIUS": "VNO",
    # Middle East & Africa
    "DUBAI": "DXB",
    "ABU DHABI": "AUH",
    "SHARJAH": "SHJ",
    "DOHA": "DOH",
    "RIYADH": "RUH",
    "JEDDAH": "JED",
    "MUSCAT": "MCT",
    "KUWAIT": "KWI",
    "BAHRAIN": "BAH",
    "AMMAN": "AMM",
    "TEL AVIV": "TLV",
    "CAIRO": "CAI",
    "MARRAKECH": "RAK",
    "CASABLANCA": "CMN",
    "JOHANNESBURG": "JNB",
    "CAPE TOWN": "CPT",
    "NAIROBI": "NBO",
    "LAGOS": "LOS",
    # North America
    "NEW YORK": "JFK",
    "NEW YORK CITY": "JFK",
    "NEWARK": "EWR",
    "LOS ANGELES": "LAX",
    "SAN FRANCISCO": "SFO",
    "CHICAGO": "ORD",
    "MIAMI": "MIA",
    "ORLANDO": "MCO",
    "BOSTON": "BOS",
    "WASHINGTON": "IAD",
    "WASHINGTON DC": "IAD",
    "ATLANTA": "ATL",
    "DALLAS": "DFW",
    "HOUSTON": "IAH",
    "SEATTLE": "SEA",
    "LAS VEGAS": "LAS",
    "DENVER": "DEN",
    "PHOENIX": "PHX",
    "MINNEAPOLIS": "MSP",
    "DETROIT": "DTW",
    "PHILADELPHIA": "PHL",
    "CHARLOTTE": "CLT",
    "SAN DIEGO": "SAN",
    "AUSTIN": "AUS",
    "TORONTO": "YYZ",
    "VANCOUVER": "YVR",
    "MONTREAL": "YUL",
    "CALGARY": "YYC",
    "MEXICO CITY": "MEX",
    "CANCUN": "CUN",
    # South America
    "SAO PAULO": "GRU",
    "RIO DE JANEIRO": "GIG",
    "BUENOS AIRES": "EZE",
    "BOGOTA": "BOG",
    "LIMA": "LIM",
    "SANTIAGO": "SCL",
    # Asia & Oceania
    "TOKYO": "HND",
    "TOKYO HANEDA": "HND",
    "TOKYO NARITA": "NRT",
    "OSAKA": "KIX",
    "SEOUL": "ICN",
    "BEIJING": "PEK",
    "SHANGHAI": "PVG",
    "HONG KONG": "HKG",
    "TAIPEI": "TPE",
    "SINGAPORE": "SIN",
    "BANGKOK": "BKK",
    "PHUKET": "HKT",
    "KUALA LUMPUR": "KUL",
    "JAKARTA": "CGK",
    "BALI": "DPS",
    "DENPASAR": "DPS",
    "MANILA": "MNL",
    "HO CHI MINH CITY": "SGN",
    "HANOI": "HAN",
    "DELHI": "DEL",
    "NEW DELHI": "DEL",
    "MUMBAI": "BOM",
    "BENGALURU": "BLR",
    "BANGALORE": "BLR",
    "HYDERABAD": "HYD",
    "CHENNAI": "MAA",
    "KOLKATA": "CCU",
    "AHMEDABAD": "AMD",
    "GOA": "GOI",
    "KOCHI": "COK",
    "SYDNEY": "SYD",
    "MELBOURNE": "MEL",
    "BRISBANE": "BNE",
    "PERTH": "PER",
    "AUCKLAND": "AKL",
}

SEAT_MAP = {
    "economy": SeatType.ECONOMY,
    "premium_economy": SeatType.PREMIUM_ECONOMY,
    "business": SeatType.BUSINESS,
    "first": SeatType.FIRST,
}

SERPAPI_CLASS_MAP = {
    "economy": "1",
    "premium_economy": "2",
    "business": "3",
    "first": "4",
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


def _search_serpapi(
    orig_code: str,
    dest_code: str,
    departure_date: str,
    return_date: str | None,
    cabin_clean: str,
    engine_links: dict,
) -> list[dict]:
    api_key = os.getenv("SERPAPI_KEY", "").strip()
    if not api_key:
        print("[TrueFare Guru] SERPAPI_KEY is not set in environment")
        return []

    params = {
        "engine": "google_flights",
        "departure_id": orig_code,
        "arrival_id": dest_code,
        "outbound_date": departure_date,
        "travel_class": SERPAPI_CLASS_MAP.get(cabin_clean, "1"),
        "currency": "EUR",
        "hl": "en",
        "type": "1" if return_date else "2",
        "api_key": api_key,
    }
    if return_date:
        params["return_date"] = return_date

    try:
        resp = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        print(f"[TrueFare Guru] SerpApi error: {e}")
        return []

    raw_groups = payload.get("best_flights", []) + payload.get("other_flights", [])
    cabin_label = cabin_clean.replace("_", " ").title()
    links = dict(engine_links)
    if payload.get("search_metadata", {}).get("google_flights_url"):
        links["google_flights"] = payload["search_metadata"]["google_flights_url"]

    offers = []
    for item in raw_groups:
        legs = item.get("flights", [])
        if not legs or item.get("price") is None:
            continue

        airlines = ", ".join(dict.fromkeys(l.get("airline", "Airline") for l in legs))
        flight_nums = " -> ".join(l.get("flight_number", "") for l in legs if l.get("flight_number"))
        stops = max(0, len(legs) - 1)
        duration_mins = int(item.get("total_duration", 0))

        dep_time = legs[0].get("departure_airport", {}).get("time", "")
        arr_time = legs[-1].get("arrival_airport", {}).get("time", "")

        segments = [
            {
                "airline": l.get("airline", ""),
                "flight_number": l.get("flight_number", ""),
                "from": l.get("departure_airport", {}).get("id", ""),
                "to": l.get("arrival_airport", {}).get("id", ""),
                "departs": l.get("departure_airport", {}).get("time", ""),
                "arrives": l.get("arrival_airport", {}).get("time", ""),
            }
            for l in legs
        ]

        offers.append({
            "airline": airlines,
            "flight_numbers": flight_nums or airlines,
            "route": f"{orig_code} {'<->' if return_date else '->'} {dest_code}",
            "cabin": cabin_label,
            "price": round(float(item["price"]), 2),
            "stops": stops,
            "duration_mins": duration_mins,
            "departure": dep_time,
            "arrival": f"Return {return_date} (Round-trip total)" if return_date else arr_time,
            "segments": segments,
            "trip_type": "Round-trip" if return_date else "One-way",
            "booking_links": links,
        })

    return offers


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

    engine_links = build_engine_links(
        orig_code, dest_code, departure_date, return_date, cabin_clean
    )

    # Primary: SerpApi Google Flights (works reliably on Render)
    serp_offers = _search_serpapi(
        orig_code, dest_code, departure_date, return_date, cabin_clean, engine_links
    )
    if serp_offers:
        serp_offers.sort(key=lambda x: x["price"])
        final_offers = serp_offers[:10]
        CACHE[cache_key] = (now, final_offers)
        return final_offers

    # Fallback: local fli scraper
    seat_type = SEAT_MAP.get(cabin_clean, SeatType.ECONOMY)
    try:
        dep_airport = getattr(Airport, orig_code)
        arr_airport = getattr(Airport, dest_code)
    except AttributeError:
        return []

    offers = []
    cabin_label = cabin_clean.replace("_", " ").title()

    outbound_list = _fetch_leg(dep_airport, arr_airport, departure_date, seat_type)
    if return_date and outbound_list:
        inbound_list = _fetch_leg(arr_airport, dep_airport, return_date, seat_type)
        if inbound_list:
            for out_f in outbound_list[:3]:
                for in_f in inbound_list[:3]:
                    airlines = ", ".join({leg.airline.value for leg in out_f.legs + in_f.legs})
                    out_nums = " -> ".join(f"{l.airline.name} {l.flight_number}" for l in out_f.legs)
                    in_nums = " -> ".join(f"{l.airline.name} {l.flight_number}" for l in in_f.legs)
                    offers.append({
                        "airline": airlines,
                        "flight_numbers": f"Out: {out_nums} | Ret: {in_nums}",
                        "route": f"{orig_code} <-> {dest_code}",
                        "cabin": cabin_label,
                        "price": round(out_f.price + in_f.price, 2),
                        "stops": out_f.stops + in_f.stops,
                        "duration_mins": out_f.duration + in_f.duration,
                        "departure": f"Out: {out_f.legs[0].departure_datetime} -> {out_f.legs[-1].arrival_datetime}",
                        "arrival": f"Ret: {in_f.legs[0].departure_datetime} -> {in_f.legs[-1].arrival_datetime}",
                        "segments": _format_legs(out_f.legs) + _format_legs(in_f.legs),
                        "trip_type": "Round-trip",
                        "booking_links": engine_links,
                    })
    elif not return_date:
        for item in outbound_list:
            airlines = ", ".join({leg.airline.value for leg in item.legs})
            flight_nums = " -> ".join(f"{l.airline.name} {l.flight_number}" for l in item.legs)
            offers.append({
                "airline": airlines,
                "flight_numbers": flight_nums,
                "route": f"{orig_code} -> {dest_code}",
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