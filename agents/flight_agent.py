import os
from amadeus import Client, ResponseError


def init_amadeus():
    amadeus_api_key = os.getenv("AMADEUS_API_KEY")
    amadeus_api_secret = os.getenv("AMADEUS_API_SECRET")
    
    amadeus = Client(
        client_id=amadeus_api_key,
        client_secret=amadeus_api_secret,
        hostname ="production"
    )
    return amadeus

#https://developers.amadeus.com/self-service/category/flights/api-doc/airline-code-lookup/api-reference
def guess_airport_code(place_query: str):
    """
    Use Amadeus reference_data.locations to find possible airport/city codes
    that match 'place_query'. Return the first IATA code or None if not found.
    """
    amadeus = init_amadeus()
    try:
        response = amadeus.reference_data.locations.get(
            keyword=place_query,
            subType="AIRPORT,CITY",
            page={"limit": 5}  # optionally increase/decrease
        )
        data = response.data
        if not data:
            return None
        # Just pick the first match for demonstration
        return data[0].get("iataCode")
    except ResponseError as e:
        print(f"Error guessing airport code for '{place_query}': {e}")
        return None

def find_flights(origin_code, dest_code, departure_date,
                  return_date=None, max_price=None):
    """
    Query the Amadeus Flight Offers Search API for flights.
    """
    amadeus = init_amadeus()
    try:
        flight_params = {
            "originLocationCode": origin_code,
            "destinationLocationCode": dest_code,
            "departureDate": departure_date,
            "adults": 1,
            "currencyCode": "USD",
            "max": 5
        }
        if return_date:
            flight_params["returnDate"] = return_date
        if max_price:
            flight_params["maxPrice"] = max_price

        response = amadeus.shopping.flight_offers_search.get(**flight_params)
        return response.data
    except ResponseError as e:
        print(f"Amadeus Flight Query Error: {e}")
        print(flight_params)
        return []
