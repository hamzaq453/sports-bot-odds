from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
import httpx
from .team_sports_mapping import team_sports_mapping
from .config import Config
from openai import OpenAI

app = FastAPI()

logging.basicConfig(level=logging.INFO)

# Configuration for API keys
API_KEY = Config.ODDS_API_KEY
OPENAI_API_KEY = Config.OPENAI_API_KEY
BASE_URL = "https://api.the-odds-api.com/v4"
DEFAULT_REGION = "us"
DEFAULT_MARKETS = "h2h"
ODDS_FORMAT = "american"

# OpenAI client configuration
client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_odds(sport: str):
    url = (
        f"{BASE_URL}/sports/{sport}/odds/?apiKey={API_KEY}"
        f"&regions={DEFAULT_REGION}&markets={DEFAULT_MARKETS}&oddsFormat={ODDS_FORMAT}"
    )
    logging.info(f"Fetching odds from URL: {url}")
    try:
        response = httpx.get(url, timeout=30)  # Increased timeout
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        logging.error(f"Error fetching odds: {exc}")
        raise HTTPException(status_code=exc.response.status_code, detail=str(exc))
    except httpx.ConnectTimeout as exc:
        logging.error(f"Connection timed out: {exc}")
        raise HTTPException(status_code=504, detail="The server took too long to respond.")
    except httpx.RequestError as exc:
        logging.error(f"Error connecting to the API: {exc}")
        raise HTTPException(status_code=502, detail="Error connecting to the API.")

class UserQuery(BaseModel):
    user_query: str

def get_sport_from_team(team: str):
    for mapped_team, sport in team_sports_mapping.items():
        if mapped_team.lower() in team.lower():
            logging.info(f"Identified sport '{sport}' for team '{team}'.")
            return sport
    return None

def fetch_ai_analysis(team: str, home_team: str, away_team: str, start_time: str, odds_data: dict):
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a sports analyst providing concise, insightful betting predictions for upcoming games. Avoid lengthy explanations of methods and focus on team performance, statistical comparisons, and actionable betting recommendations."
            },
            {
                "role": "user",
                "content": (
                    f"Provide a concise summary of the upcoming matchup between {home_team} and {away_team}. "
                    f"Include recent performance metrics (win-loss record, key stats, streaks), statistical comparisons (offense, defense, scoring), "
                    f"and historical head-to-head trends if relevant. Highlight current odds from this data: {odds_data}. "
                    f"Identify value opportunities based on the analysis. Conclude with a clear prediction of which team is more likely to win or cover the spread. "
                    f"The game is scheduled on {start_time}."
                ),
            }
        ]
        # Create a chat completion request
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="gpt-4o"  # Use the appropriate model name configured for your account
        )
        # Extract the response text from the completion object
        ai_response = chat_completion.choices[0].message.content.strip()
        logging.info("AI analysis successfully generated.")
        return ai_response
    except Exception as e:
        logging.error(f"Error fetching AI predictions: {e}")
        return "Unable to fetch AI predictions at the moment."

def process_query(user_query: str):
    user_query_lower = user_query.lower()

    # Check if the query is about odds or game
    if "odds" in user_query_lower or "game" in user_query_lower:
        for team in team_sports_mapping.keys():
            if team.lower() in user_query_lower:
                sport = get_sport_from_team(team)
                if sport:
                    odds_data = fetch_odds(sport)
                    if "odds" in user_query_lower:
                        return format_odds_response(team, odds_data)
                    if "game" in user_query_lower:
                        return format_game_response(team, odds_data)
        return "Sorry, I couldn't find the requested information for the team."

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
            ai_analysis = fetch_ai_analysis(team, home_team, away_team, start_time, odds_data)
            return f"The next game for {team} is {home_team} vs {away_team} on {start_time}.\n\nAI Analysis:\n{ai_analysis}"

    return f"No upcoming games found for the team '{team}'."

@app.post("/query")
async def handle_query(query: UserQuery):
    logging.info(f"Received user query: {query.user_query}")
    response = process_query(query.user_query)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
