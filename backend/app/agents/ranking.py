BUDGET_AIRLINES = {"Ryanair", "Vueling", "easyJet", "Wizz Air", "Transavia"}


def choose_best(
    flights: list[dict],
    preferences: str = "cheapest overall",
    has_carry_on: bool = False,
) -> dict:
    if not flights:
        return {
            "error": (
                "No live flights were returned for this exact route/cabin combination. "
                "Try switching cabin class (e.g., Business or Economy on short-haul routes) or adjusting your dates."
            )
        }

    prefs = preferences.lower()
    scored = []

    for f in flights:
        is_economy = f.get("cabin", "Economy").lower() == "economy"
        bag_fee = (
            22
            if (is_economy and has_carry_on and any(b in f["airline"] for b in BUDGET_AIRLINES))
            else 0
        )
        true_price = round(f["price"] + bag_fee, 2)

        score = true_price + (f["stops"] * 35) + (f["duration_mins"] * 0.1)

        if "nonstop" in prefs and f["stops"] > 0:
            score += 100
        if "morning" in prefs and "06:" <= f["departure"][-8:-3] <= "11:":
            score -= 20

        scored.append((score, true_price, bag_fee, f))

    scored.sort(key=lambda x: x[0])
    _, best_price, bag_fee, best = scored[0]

    bag_note = (
        f"includes ~€{bag_fee} estimated carry-on fee"
        if bag_fee > 0
        else "carry-on included or traveling light"
    )

    recommendation = (
        f"Best Pick: {best['airline']} ({best['flight_numbers']}) — €{best_price} total ({bag_note})\n"
        f"• Route & Cabin: {best['route']} · {best['cabin']} ({best['trip_type']})\n"
        f"• Outbound: {best['departure']}\n"
        f"• Arrival / Return: {best['arrival']}\n"
        f"• Total Flight Time: {best['duration_mins']} mins ({'Nonstop' if best['stops'] == 0 else str(best['stops']) + ' stop(s)'})\n\n"
        f"How to Book This Exact Fare:\n"
        f"1. Click Google Flights or Skyscanner below to open this route & date pre-filled.\n"
        f"2. Match flight number {best['flight_numbers']} at the departure time shown above.\n"
        f"3. Select the airline's direct booking option at checkout to avoid third-party agency markups."
    )

    return {
        "recommendation": recommendation,
        "booking_steps": [
            f"1. Click Google Flights, Skyscanner, Kiwi, or KAYAK on the {best['airline']} card below.",
            f"2. Select flight {best['flight_numbers']} ({best['departure']}).",
            "3. Choose 'Book with Airline' on the redirect screen to lock in the direct carrier price and baggage allowance.",
        ],
        "raw_results": flights,
    }