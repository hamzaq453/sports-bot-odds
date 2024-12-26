from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import httpx
from .team_sports_mapping import team_sports_mapping
from .config import Config

app = FastAPI()

logging.basicConfig(level=logging.INFO)

API_KEY = Config.ODDS_API_KEY
BASE_URL = "https://api.the-odds-api.com/v4"
DEFAULT_REGION = "us"
DEFAULT_MARKETS = "h2h"
ODDS_FORMAT = "american"

def fetch_odds(sport: str):
    url = (
        f"{BASE_URL}/sports/{sport}/odds/?apiKey={API_KEY}"
        f"&regions={DEFAULT_REGION}&markets={DEFAULT_MARKETS}&oddsFormat={ODDS_FORMAT}"
    )
    logging.info(f"Fetching odds from URL: {url}")
    try:
        response = httpx.get(url)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logging.error(f"Error fetching odds: {exc}")
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))

class UserQuery(BaseModel):
    user_query: str

def get_sport_from_team(team: str):
    for mapped_team, sport in team_sports_mapping.items():
        if mapped_team.lower() in team.lower():
            logging.info(f"Identified sport '{sport}' for team '{team}'.")
            return sport
    return None

def process_query(user_query: str):
    user_query_lower = user_query.lower()

    # Check if the query is about odds or game
    if "odds" in user_query_lower:
        for team in team_sports_mapping.keys():
            if team.lower() in user_query_lower:
                sport = get_sport_from_team(team)
                if sport:
                    odds_data = fetch_odds(sport)
                    return format_odds_response(team, odds_data)
        return "Sorry, I couldn't find odds for the requested team."

    elif "game" in user_query_lower:
        for team in team_sports_mapping.keys():
            if team.lower() in user_query_lower:
                sport = get_sport_from_team(team)
                if sport:
                    odds_data = fetch_odds(sport)
                    return format_game_response(team, odds_data)
        return "Sorry, I couldn't find the next game for the requested team."

    return "Sorry, I couldn't understand your query. Please specify if you want odds or game details."

def format_odds_response(team: str, odds_data):
    if not odds_data:
        return f"No odds data available for the team '{team}'."

    formatted_response = f"Here are the latest odds for {team} games:\n"
    for event in odds_data:
        home_team = event["home_team"]
        away_team = event["away_team"]
        start_time = event["commence_time"]

        if team.lower() in [home_team.lower(), away_team.lower()]:
            formatted_response += f"\n- Game: {home_team} vs {away_team} (Start Time: {start_time})"
            for bookmaker in event.get("bookmakers", []):
                bookmaker_name = bookmaker["title"]
                outcomes = bookmaker["markets"][0]["outcomes"]
                for outcome in outcomes:
                    if outcome["name"].lower() == team.lower():
                        formatted_response += (
                            f"\n  Bookmaker: {bookmaker_name}\n  Team: {team} at {outcome['price']} odds"
                        )
    return formatted_response

def format_game_response(team: str, odds_data):
    if not odds_data:
        return f"No upcoming games found for the team '{team}'."

    for event in odds_data:
        home_team = event["home_team"]
        away_team = event["away_team"]
        start_time = event["commence_time"]

        if team.lower() in [home_team.lower(), away_team.lower()]:
            return f"The next game for {team} is {home_team} vs {away_team} on {start_time}."

    return f"No upcoming games found for the team '{team}'."

@app.post("/query")
async def handle_query(query: UserQuery):
    logging.info(f"Received user query: {query.user_query}")
    response = process_query(query.user_query)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
