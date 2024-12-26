import httpx
from .config import Config
import logging

BASE_URL = "https://api.the-odds-api.com/v4/sports"

logger = logging.getLogger(__name__)

# Fetch all sports
async def get_all_sports():
    try:
        logger.info("Fetching all sports from Odds API.")
        logger.debug(f"Using ODDS_API_KEY: {Config.ODDS_API_KEY}")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}?apiKey={Config.ODDS_API_KEY}")
            response.raise_for_status()
            logger.info("Fetched sports data successfully.")
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"Request error while fetching sports: {str(e)}")
        return {"error": f"An error occurred while requesting data: {str(e)}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP status error while fetching sports: {str(e)}")
        return {"error": f"Unexpected HTTP response: {str(e)}"}

# Fetch the next event for a specific sport
async def get_next_event(sport_key: str):
    """
    Fetch all upcoming events for the given sport key.
    """
    try:
        logger.info(f"Fetching next events for sport key: {sport_key}")
        async with httpx.AsyncClient() as client:
            url = f"{BASE_URL}/{sport_key}/events?apiKey={Config.ODDS_API_KEY}"
            logger.info(f"Constructed URL: {url}")
            response = await client.get(url)
            response.raise_for_status()
            events = response.json()
            if not events:
                logger.warning(f"No events found for sport key: {sport_key}")
                return []
            logger.info("Fetched events successfully.")
            return events  # Return all events as a list
    except httpx.RequestError as e:
        logger.error(f"Request error while fetching events: {str(e)}")
        return {"error": f"An error occurred while requesting data: {str(e)}"}
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP status error while fetching events: {str(e)}")
        return {"error": f"Unexpected HTTP response: {str(e)}"}
