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

#https://developers.amadeus.com/self-service/category/hotels/api-doc/hotel-list/api-reference
def get_hotels_in_city(city_code: str, radius_km=10):
    """
    Use reference_data.locations.hotels.by_city to list hotels in that city.
    Returns a list of hotels (each has a 'hotelId').
    """
    amadeus = init_amadeus()
    try:
        response = amadeus.reference_data.locations.hotels.by_city.get(
            cityCode=city_code,
            radius=radius_km,
            radiusUnit="KM"
        )
        return response.data  # list of hotels
    except ResponseError as e:
        print(f"Error retrieving hotels by city: {e}")
        return []
    
#https://developers.amadeus.com/self-service/category/hotels/api-doc/hotel-search/api-reference
def get_hotel_offers(hotel_ids, check_in, check_out, adults=1, rooms=1):
    """
    Fetch actual offers for the given hotel(s) using the v3 Hotel Search endpoint.
    """
    amadeus = init_amadeus()
    if not hotel_ids:
        return []

    try:
        response = amadeus.shopping.hotel_offers_search.get(
            hotelIds=",".join(hotel_ids),
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=adults,
            roomQuantity=rooms,
            currency="USD"
        )
        return response.data
    except ResponseError as e:
        print(f"Error retrieving hotel offers: {e}")
        return []