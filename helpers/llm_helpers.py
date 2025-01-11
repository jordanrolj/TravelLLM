import os
import json
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers import ResponseSchema, StructuredOutputParser
from amadeus import Client, ResponseError
import requests

def get_conversation_chain():
   """
   Returns a ConversationChain with buffer memory, so it retains
   conversation context across multiple user inputs.
   """
   openai_api_key = os.getenv("OPENAI_API_KEY")
   llm = ChatOpenAI(
       openai_api_key=openai_api_key,
       temperature=0.3,
       model_name="gpt-4o"
   )
   memory = ConversationBufferMemory(return_messages=True)
   chain = ConversationChain(llm=llm, memory=memory, verbose=False)
   return chain


def parse_location(conversation_chain, location_string):
    """
    Parse the user's location using a structured output parser,
    but specifically instruct the LLM to guess missing fields if possible.
    """
    
    schemas = [
        ResponseSchema(name="city", description="City name, or best guess if not explicit"),
        ResponseSchema(name="state", description="State/Province name if applicable. Otherwise null or empty"),
        ResponseSchema(name="country", description="Country name or best guess"),
        ResponseSchema(name="clarifications", description="Any extra info or ambiguities")
    ]

    parser = StructuredOutputParser.from_response_schemas(schemas)
    format_instructions = parser.get_format_instructions()

    prompt_text = f"""
You are a helpful travel assistant. The user provided the following location:
"{location_string}"

1. If the user location is ambiguous or missing a piece (e.g. 'Barcelona' has no state in Spain),
   try to guess or clarify from context. 
2. If there's no state or province concept, set state to null (or an empty string).
3. Return the final result in JSON with the keys: city, state, country, clarifications.

{format_instructions}
"""

    llm_output = conversation_chain.run(prompt_text)
    parsed = parser.parse(llm_output)
    return dict(parsed)


def parse_dates(conversation_chain, date_string):

    #Define the schema we want
    date_schemas = [
        ResponseSchema(
            name="start_date",
            description="ISO date for start (e.g. 2024-03-06), empty if unknown"
        ),
        ResponseSchema(
            name="end_date",
            description="ISO date for end (e.g. 2024-03-10), empty if unknown"
        ),
        ResponseSchema(
            name="clarifications",
            description="Any notes or ambiguities. If none, empty string."
        )
    ]

    #Create a parser from the schemas
    parser = StructuredOutputParser.from_response_schemas(date_schemas)
    format_instructions = parser.get_format_instructions()

    # 3) Build the prompt, including the format instructions
    #    so the LLM knows exactly how to format its JSON.
    prompt_text = f"""
You are a travel assistant. The user provided the following date information:
"{date_string}"

Your task: parse it into valid JSON with keys:
- start_date
- end_date
- clarifications

Each date should be in ISO format (YYYY-MM-DD) if possible.
If ambiguous or invalid, mention that in 'clarifications'.

{format_instructions}
"""

    # 4) Run the chain
    llm_output = conversation_chain.run(prompt_text)

    # 5) Let the structured parser handle the output
    try:
        parsed_data = parser.parse(llm_output)
        return dict(parsed_data)
    except Exception as e:
        # fallback if for some reason the LLM still didn't follow instructions
        return {
            "start_date": "",
            "end_date": "",
            "clarifications": f"Could not parse: {llm_output}\nError: {str(e)}"
        }


def geocode_place(place_query: str):
    """
    Make a GET request to Nominatim with the free-form query.
    Return lat/lon from the top match if found, plus the full display_name.
    """
    base_url = "https://nominatim.openstreetmap.org/search"
    #print(place_query)
    params = {
        "q": place_query,
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "YourAppName/1.0 (contact@yourdomain.com)"
    }
    try:
        #resp = requests.get(base_url, params=params, timeout=10)
        response = requests.get(base_url, headers=headers, params=params)
        data = response.json()
    except Exception as e:
        print(f"Nominatim request error: {e}")
        return None

    if not data:
        return None

    top = data[0]
    lat = float(top["lat"])
    lon = float(top["lon"])
    display_name = top.get("display_name", "")
    return {
        "latitude": lat,
        "longitude": lon,
        "display_name": display_name
    }
