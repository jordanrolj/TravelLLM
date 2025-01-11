import streamlit as st
import os
from dotenv import load_dotenv
from agents.flight_agent import guess_airport_code, find_flights
from agents.activities_agent import find_activities
from agents.hotel_agent import get_hotel_offers, get_hotels_in_city

from helpers.llm_helpers import (
    get_conversation_chain,
    parse_location,
    parse_dates,
    geocode_place
)

# Load environment variables (OpenAI keys, etc.)
load_dotenv()

st.title("TravelBot")

# ------------------------------------------------
# Session State Initialization
# ------------------------------------------------
if "step" not in st.session_state:
    st.session_state.step = 0

#initialize dictinary for the price at each step
if "price_at_steps" not in st.session_state:
    st.session_state.price_at_steps = {step: 0 for step in range(8)}

# Create a single LLM conversation chain
if "conversation_chain" not in st.session_state:
    st.session_state.conversation_chain = get_conversation_chain()

# Data containers
if "origin_raw" not in st.session_state:
    st.session_state.origin_raw = ""          # we won't ask for this, but let's keep it
if "destination_raw" not in st.session_state:
    st.session_state.destination_raw = ""
if "origin_code" not in st.session_state:
    st.session_state.origin_code = ""
if "destination_code" not in st.session_state:
    st.session_state.destination_code = ""

if "flight_choice" not in st.session_state:
    st.session_state.flight_choice = None

if "hotel_ids" not in st.session_state:
    st.session_state.hotel_ids = []
if "hotel_choice" not in st.session_state:
    st.session_state.hotel_choice = None

if "activity_choices" not in st.session_state:
    st.session_state.activity_choices = []

if "depart_date" not in st.session_state:
    st.session_state.depart_date = ""
if "return_date" not in st.session_state:
    st.session_state.return_date = ""

# Helper to go back
def go_back(step):
    st.session_state.step = step

# Quick summary function
def show_summary():
    st.write("**Current Summary**:")
    if st.session_state.origin_code:
        st.write(f"Origin Airport: {st.session_state.origin_code}")
    if st.session_state.destination_code:
        st.write(f"Destination Airport: {st.session_state.destination_code}")
    if st.session_state.depart_date:
        st.write(f"Departure: {st.session_state.depart_date}")
    if st.session_state.return_date:
        st.write(f"Return: {st.session_state.return_date}")
    if st.session_state.flight_choice:
        st.write(f"Chosen Flight: {st.session_state.flight_choice}")
    if st.session_state.hotel_choice:
        st.write(f"Chosen Hotel Offer: {st.session_state.hotel_choice}")
    if st.session_state.activity_choices:
        st.write("Chosen Activities:")
        for a in st.session_state.activity_choices:
            st.write(f" - {a}")

    current_step = st.session_state.step
    current_step_price = st.session_state.price_at_steps.get(current_step, 0)
    st.write(f"**Total Price:** ${current_step_price}")

# ------------------------------------------------
# STEP 0: Destination Only (Assume origin = DTW)
# ------------------------------------------------
if st.session_state.step == 0:
    st.subheader("Step 1: Destination")
    st.write("Origin is assumed to be **DTW** (Detroit).")
    st.session_state.origin_code = "DTW"  # Hardcode

    loc_input = st.text_input("Where do you want to go?")


    if st.button("Submit Location", key="submit_location_step0"):
        if loc_input.strip() == "":
            st.warning("Please enter a location.")
        else:
            st.session_state.location_raw = loc_input.strip()
            st.session_state.step = 1
            #Reruns webpage
            st.rerun()

    show_summary()


# ------------------------------------------------
# STEP 1: Parse location
# ------------------------------------------------
elif st.session_state.step == 1:
    st.subheader("Step 1: Confirm your location")
    st.write("We’ll use the LLM to parse the location string you provided.")

    loc_parsed = parse_location(st.session_state.conversation_chain, st.session_state.location_raw)
    st.session_state.location_parsed = loc_parsed

    city = loc_parsed.get("city", "") or ""
    state = loc_parsed.get("state", "") or ""
    country = loc_parsed.get("country", "") or ""
    clarifications = loc_parsed.get("clarifications", "")
    st.session_state.coordinate_search = f'{city } {state}, {country}'
    st.session_state.city = city

    st.write(f"**City**: {city}")
    st.write(f"**State/Province**: {state}")
    st.write(f"**Country**: {country}")
    if clarifications:
        st.warning(f"Clarifications: {clarifications}")

    if st.button("Confirm Location", key="confirm_location_step1"):
        st.session_state.step = 2
        st.rerun()
    if st.button("Back", key="back_step1"):
        go_back(0)

    show_summary()

# ------------------------------------------------
# STEP 2: Guess (Destination) Airport Code & Confirm
# ------------------------------------------------
elif st.session_state.step == 2:
    st.subheader("Step 2: Confirm Airport Codes")
    dest_guess = guess_airport_code(st.session_state.city)

    st.write(f"Origin (hard-coded): DTW")
    st.write(f"Guessed destination: {dest_guess}")

    if st.button("Confirm these codes", key="confirm_codes_step2"):
        st.session_state.origin_code = "DTW"
        st.session_state.destination_code = dest_guess or ""
        st.session_state.step = 3
        st.rerun()

    if st.button("Back", key="back_step2"):
        go_back(1)

    show_summary()

# ------------------------------------------------
# STEP 3: Date Input (Departure mandatory, Return optional)
# ------------------------------------------------
elif st.session_state.step == 3:
    st.subheader("Step 3: Travel Dates")

    dep = st.date_input("Departure Date", key="dep_date")
    ret = st.date_input("Return Date", key="ret_date")

    if st.button("Next", key="next_dates_step3"):
        # Convert the date objects to strings
        st.session_state.depart_date = dep.isoformat()
        # If user didn't pick a return date, let's store None
        if ret and ret != dep:
            st.session_state.return_date = ret.isoformat()
        else:
            st.session_state.return_date = ""

        st.session_state.step = 4
        st.rerun()

    if st.button("Back", key="back_step3"):
        go_back(2)

    show_summary()

# ------------------------------------------------
# STEP 4: Search Flights
# ------------------------------------------------
elif st.session_state.step == 4:
    st.subheader("Step 4: Flight Search & Selection")
    if not st.session_state.origin_code or not st.session_state.destination_code:
        st.error("Missing airport codes. Go back and fix.")
    else:
        flights_data = find_flights(
            st.session_state.origin_code,
            st.session_state.destination_code,
            st.session_state.depart_date,
            st.session_state.return_date or None
        )
        if not flights_data:
            st.write("No flights found or an error occurred.")
        else:
            flight_summaries = []  # we'll store user-friendly labels here
            flight_prices = []
            for f in flights_data:
                flight_id = f.get("id", "UnknownID")
                price = f.get("price", {}).get("grandTotal", "??")
                flight_prices.append(float(price))
                # Build a summary string:
                # 1. Show flight ID, total price
                summary_lines = [f"**Flight {flight_id}** - **${price}**"]

                # 2. For each itinerary, show segment details
                itineraries = f.get("itineraries", [])
                for idx_it, itin in enumerate(itineraries, start=1):
                    segments = itin.get("segments", [])
                    summary_lines.append(f"_Itinerary {idx_it}_:")


                    for idx_seg, seg in enumerate(segments, start=1):
                        dep_iata = seg.get("departure", {}).get("iataCode", "")
                        dep_time = seg.get("departure", {}).get("at", "")
                        arr_iata = seg.get("arrival", {}).get("iataCode", "")
                        arr_time = seg.get("arrival", {}).get("at", "")
                        dur = seg.get("duration", "??")
                        carrier = seg.get("carrierCode", "")
                        flight_num = seg.get("number", "")

                        segment_line = (
                            f"  - Segment {idx_seg}: {dep_iata} ({dep_time}) → "
                            f"{arr_iata} ({arr_time}), {dur}, Airline {carrier}, Flight {flight_num}"
                        )
                        summary_lines.append(segment_line)

                # Join lines into a single multi-line string. 
                # We can use Markdown formatting or just plain text.
                flight_summary = "\n".join(summary_lines)
                flight_summaries.append(flight_summary)

            # Now present them in a radio:
            chosen_summary = st.radio("Choose a flight:", flight_summaries, key="flight_options")

            if st.button("Confirm Flight", key="confirm_flight_step4"):
                chosen_index = flight_summaries.index(chosen_summary)
                st.session_state.price_at_steps[5] = st.session_state.price_at_steps[4] + flight_prices[chosen_index]
                st.session_state.flight_choice = chosen_summary
                st.session_state.step = 5
                st.rerun()

    if st.button("Back", key="back_step4"):
        go_back(3)

    show_summary()


# ------------------------------------------------
# STEP 5: Find Hotels with Offers in Destination City
# ------------------------------------------------
elif st.session_state.step == 5:
    st.subheader("Step 5: Find Hotels in Destination City")
    if not st.session_state.destination_code:
        st.error("No destination code. Go back.")
    else:
        st.write("Searching hotels by city code:", st.session_state.destination_code)
        hotels_data = get_hotels_in_city(st.session_state.destination_code, radius_km=10)
        
        if not hotels_data:
            st.write("No hotels found or error.")
        else:
            hotel_names = []
            hotel_ids = []
            for h in hotels_data:
                hname = h.get("name", "Unknown Hotel")
                hid = h.get("hotelId", "")
                label = f"{hname} ({hid})"
                hotel_names.append(label)
                hotel_ids.append(hid)
	
            chosen_hotel = st.selectbox("Pick a Hotel to see offers:", hotel_names, key="hotel_selectbox")
            offer_summaries = []
            offer_prices = []
            
            if st.button("See Offers for Hotel", key="see_offers_button"):
                idx = hotel_names.index(chosen_hotel)
                selected_id = hotel_ids[idx]
                offers = get_hotel_offers(
                    [selected_id],
                    check_in=st.session_state.depart_date,
                    check_out=st.session_state.return_date or None
                )
                if not offers:
                    st.write("No offers for that hotel or error.")
                else:
                    st.session_state.offers = offers  # Persist offers
                    # Process offers into summaries and prices
                    offer_summaries = []
                    offer_prices = []
                    for item in offers:
                        if "offers" in item:
                            for o in item["offers"]:
                                oid = o.get("id", "N/A")
                                price = o.get("price", {}).get("total", "??")
                                summary = f"Offer ID: {oid} - Price: ${price}"
                                offer_summaries.append(summary)
                                try:
                                    offer_prices.append(float(price))
                                except:
                                    offer_prices.append(0)
                    st.session_state.offer_summaries = offer_summaries
                    st.session_state.offer_prices = offer_prices
                    if "offer_summaries" in st.session_state and st.session_state.offer_summaries:
                        chosen_offer_summary = st.radio(
                            "Choose a hotel offer:",
                            st.session_state.offer_summaries,
                            key="hotel_offers_radio"
                        )
                        if st.button("Confirm Hotel Offer", key="confirm_hotel_offer"):
                            chosen_index = st.session_state.offer_summaries.index(chosen_offer_summary)
                            st.session_state.price_at_steps[5] = st.session_state.price_at_steps[4] + st.session_state.offer_prices[chosen_index]
                            confirmed_summary = f"Confirmed Hotel Offer: {chosen_offer_summary}"
                            st.session_state.hotel_choice = confirmed_summary
                            st.session_state.step = 6
                            st.rerun()
                    else:
                        st.write("No offers available for selection.")

    if st.button("Back", key="back_step5"):
        go_back(4)
    
    show_summary()

# ------------------------------------------------
# STEP 6: Activities by lat/lon
# ------------------------------------------------
elif st.session_state.step == 6:
    st.subheader("Step 6: Activities")
    # We use Nominatim (via geocode_place) on the raw DESTINATION
    geo = geocode_place(st.session_state.coordinate_search)
    if not geo:
        st.write("Could not geocode your destination. Try again or skip activities.")
    else:
        lat, lon = geo["latitude"], geo["longitude"]
        acts_data = find_activities(lat, lon, radius_km=5)
        if not acts_data:
            st.write("No activities found or error.")
        else:
            chosen_acts = []
            for i, act in enumerate(acts_data):
                #print(act)
                aname = act.get("name", "Unknown Activity")
                price = act.get("price", {}).get("amount", "??")
                act_label = f"{aname} (${price})"
                if st.checkbox(act_label, key=f"act_{i}_step6"):
                    chosen_acts.append(act_label)

            if st.button("Confirm Activities", key="confirm_activities_step6"):
                st.session_state.activity_choices = chosen_acts
                #TODO: add in price of activities
                st.session_state.price_at_steps[7] = st.session_state.price_at_steps[6]
                st.session_state.step = 7
                st.rerun()

    if st.button("Back"):
        go_back(5)

    show_summary()

# ------------------------------------------------
# STEP 7: Final Summary
# ------------------------------------------------
elif st.session_state.step == 7:
    st.subheader("Final Step: Review Your Trip")
    show_summary()
    st.success("All steps complete!")
    st.write("If you need to change something, go back to a previous step.")
    for s in range(0, 7):
        if st.button(f"Back to Step {s}", key=f"back_to_step_{s}"):
            go_back(s)