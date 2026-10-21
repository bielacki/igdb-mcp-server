"""
IGDB MCP Server - A Model Context Protocol server for the IGDB (Internet Game Database) API.

This server provides tools to interact with the IGDB API, allowing you to search and retrieve
information about games, platforms, companies, and more.
"""

import os
import time
import httpx
from pydantic import Field
from fastmcp import FastMCP
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Annotated

# Initialize the FastMCP server
mcp = FastMCP(
    "IGDB API Server",
    instructions="""
    IGDB API Integration Best Practices:

    QUERY OPTIMIZATION:
    • Use nested fields to reduce API calls (e.g., platforms.name, cover.url, involved_companies.company.name)
    • Leverage multiquery endpoint for batch operations instead of sequential calls
    • For counts/aggregations, use dedicated endpoints (games/count) rather than fetching all records

    SEARCH & FILTERING:
    • Use 'search' for text queries, 'where' for exact filtering
    • Combine conditions efficiently: use & (AND), | (OR) operators
    • Check for null values when filtering ratings or dates to avoid missing data

    RESPONSE HANDLING:
    • Always validate results exist before accessing properties
    • Handle missing/null fields gracefully in responses
    • Consider pagination limits (max 500 per request) for large result sets

    PERFORMANCE TIPS:
    • Batch related queries using multiquery when fetching connected data
    • Use field expansion wisely - deeply nested fields increase response time
    • For time-based queries, use Unix timestamps for precise filtering
    """,
)

# Configuration
IGDB_BASE_URL = "https://api.igdb.com/v4"
TWITCH_AUTH_URL = "https://id.twitch.tv/oauth2/token"

# Cache for OAuth token
token_cache = {"access_token": None, "expires_at": None}


class IGDBClient:
    """Client for interacting with the IGDB API."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.http_client = httpx.AsyncClient()

    async def get_access_token(self) -> str:
        """Get or refresh the OAuth access token."""
        # Check if we have a valid cached token
        if token_cache["access_token"] and token_cache["expires_at"]:
            if datetime.now() < token_cache["expires_at"]:
                return token_cache["access_token"]

        # Get a new token from Twitch OAuth
        response = await self.http_client.post(
            TWITCH_AUTH_URL,
            params={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        )
        response.raise_for_status()

        data = response.json()
        token_cache["access_token"] = data["access_token"]
        # Set expiry slightly before actual expiry for safety
        token_cache["expires_at"] = datetime.now() + timedelta(
            seconds=data["expires_in"] - 300
        )

        return data["access_token"]

    async def make_request(self, endpoint: str, query: str) -> List[Dict[str, Any]]:
        """Make a request to the IGDB API."""
        token = await self.get_access_token()

        response = await self.http_client.post(
            f"{IGDB_BASE_URL}/{endpoint}",
            headers={
                "Client-ID": self.client_id,
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            content=query,
            timeout=30.0,
        )
        response.raise_for_status()

        data = response.json()
        if isinstance(data, list):
            return data
        return [data]

    async def close(self):
        """Close the HTTP client."""
        await self.http_client.aclose()


def get_igdb_client() -> IGDBClient:
    """Get or create the IGDB client singleton."""
    global _igdb_client

    if "_igdb_client" not in globals():
        # Get credentials from environment variables
        client_id = os.getenv("IGDB_CLIENT_ID")
        client_secret = os.getenv("IGDB_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise ValueError(
                "Please set IGDB_CLIENT_ID and IGDB_CLIENT_SECRET environment variables. "
                "You can obtain these from https://api-docs.igdb.com/#account-creation"
            )

        _igdb_client = IGDBClient(client_id, client_secret)

    return _igdb_client


@mcp.tool(
    name="search_games",
    title="Search Games",
    description="Search for games in the IGDB database"
)
async def search_games(
    query: Annotated[str, Field(description="Search term for finding games")],
    fields: Annotated[
        str, Field(description="Comma-separated list of fields to return")
    ] = "name,rating,rating_count,first_release_date,platforms.name",
    limit: Annotated[
        int, Field(description="Maximum number of results to return", ge=1, le=500)
    ] = 10,
) -> List[Dict[str, Any]]:
    """
    Search for games in the IGDB database.

    Args:
        query: Search term for finding games
        fields: Comma-separated list of fields to return
        limit: Maximum number of results to return (default: 10, max: 500)

    Returns:
        List of games matching the search criteria
    """
    igdb_client = get_igdb_client()

    search_query = f'search "{query}"; fields {fields}; limit {limit};'
    return await igdb_client.make_request("games", search_query)


@mcp.tool(
    name="get_game_details",
    title="Get Game Details",
    description="Retrieve detailed information about a specific game from IGDB"
)
async def get_game_details(
    game_id: Annotated[int, Field(description="The IGDB ID of the game")],
    fields: Annotated[
        Optional[str],
        Field(description="Comma-separated list of fields to return"),
    ] = "id,slug,name,rating,rating_count,hypes,first_release_date,platforms.name,genres.name,status,cover.url,summary,involved_companies.company.name,involved_companies.developer,involved_companies.publisher",
) -> Dict[str, Any]:
    """
    Get detailed information about a specific game.

    Args:
        game_id: The IGDB ID of the game
        fields: Comma-separated list of fields to return (default: all fields)

    Returns:
        Detailed information about the game
    """
    igdb_client = get_igdb_client()

    query = f"fields {fields}; where id = {game_id};"
    results = await igdb_client.make_request("games", query)

    if not results:
        raise ValueError(f"No game found with ID {game_id}")

    return results[0]


@mcp.tool(
    name="get_most_anticipated_games",
    title="Get Most Anticipated Games",
    description="Fetch upcoming games sorted by hype count, filtered for future or TBA releases"
)
async def get_most_anticipated_games(
    fields: Annotated[
        str,
        Field(description="Comma-separated list of fields to return"),
    ] = "id,slug,name,hypes,first_release_date,platforms.name,genres.name,status",
    limit: Annotated[
        int, Field(description="Maximum number of results to return", ge=1, le=500)
    ] = 25,
    min_hypes: Annotated[
        int, Field(description="Minimum number of hypes required", ge=0)
    ] = 25,
) -> List[Dict[str, Any]]:
    """
    Get the most anticipated upcoming games based on hype count.
    Automatically filters for future or TBA releases.

    Args:
        fields: Comma-separated list of fields to return
        limit: Maximum number of results to return (default: 25, max: 500)
        min_hypes: Minimum number of hypes required (default: 25)

    Returns:
        List of most anticipated games sorted by hype count
    """
    igdb_client = get_igdb_client()

    # Get current timestamp
    current_timestamp = int(time.time())

    # Build query: games with hypes that are either future releases or TBA
    query = (
        f"fields {fields}; "
        f"where hypes >= {min_hypes} & "
        f"(status = null | status != 0) & "
        f"(first_release_date > {current_timestamp} | first_release_date = null); "
        f"sort hypes desc; "
        f"limit {limit};"
    )

    return await igdb_client.make_request("games", query)


@mcp.tool(
    name="custom_query",
    title="Custom IGDB Query",
    description="Run a custom Apicalypse query against any IGDB API endpoint"
)
async def custom_query(
    endpoint: Annotated[
        str,
        Field(
            description="The API endpoint to query (e.g., 'games', 'companies', 'platforms', 'people', 'characters')"
        ),
    ],
    query: Annotated[str, Field(description="The Apicalypse query string")],
) -> List[Dict[str, Any]]:
    """
    Execute a custom IGDB API query.

    This allows advanced users to write their own IGDB queries using the Apicalypse query language.
    See https://api-docs.igdb.com/#apicalypse for query syntax.

    Args:
        endpoint: The API endpoint to query (e.g., "games", "companies", "platforms")
        query: The Apicalypse query string

    Returns:
        Raw response from the IGDB API

    Example:
        endpoint: "games"
        query: "fields name,rating; where rating > 90; sort rating desc; limit 5;"
    """
    igdb_client = get_igdb_client()

    return await igdb_client.make_request(endpoint, query)


@mcp.resource(
    uri="igdb://endpoints",
    title="IGDB Endpoints",
    description="List of available IGDB API endpoints and their descriptions"
)
async def get_endpoints() -> str:
    """
    Get a list of available IGDB API endpoints and their descriptions.
    """
    return """
    Available IGDB endpoints:
    
    - games: Video game information
    - platforms: Gaming platforms (PC, PlayStation, Xbox, etc.)
    - companies: Game developers and publishers
    - genres: Game genres (Action, RPG, etc.)
    - themes: Game themes (Fantasy, Sci-fi, etc.)
    - game_modes: Game modes (Single-player, Multiplayer, etc.)
    - characters: Video game characters
    - franchises: Game franchises and series
    - collections: Game collections
    - game_engines: Game engines (Unreal, Unity, etc.)
    - artworks: Official game artworks
    - covers: Game cover art
    - screenshots: Game screenshots
    - videos: Game videos and trailers
    - websites: Game-related websites
    - release_dates: Game release dates by region
    - regions: Region for game localization
    - age_ratings: Age ratings from various organizations
    - multiplayer_modes: Multiplayer mode details
    - player_perspectives: Player perspectives (First-person, Third-person, etc.)
    - keywords: Game keywords and tags
    - involved_companies: Companies involved in game development
    - events: Gaming events (E3, GamesCom, etc.)
    - search: Multi-resource search endpoint
    - popularity_primitives: Popularity metrics for games (IGDB Visits, Want to Play, etc.)
    - popularity_types: Types of popularity metrics (Visits, Want to Play, Steam Total Reviews etc.)
    - multiquery: Execute multiple queries in a single request (The Multi-Query syntax is made up of three pieces: “Endpoint name”, “Result Name (Given by you)”, and the APICalypse query inside the body {})
    
    Use the custom_query tool to access any of these endpoints with custom queries.
    """


@mcp.resource(
    uri="igdb://query-syntax",
    title="IGDB Query Syntax",
    description="Guide to the IGDB Apicalypse query language with examples"
)
async def get_query_syntax() -> str:
    """
    Get IGDB Apicalypse query language syntax guide.
    """
    return """
    IGDB Apicalypse Query Language Syntax:
    
    Basic Structure:
    - fields: Select which fields to return
    - exclude: Exclude specific fields
    - where: Filter results
    - sort: Sort results
    - limit: Limit number of results
    - offset: Skip results for pagination
    - search: Text search
    
    Examples:
    
    1. Basic query:
       fields name,rating,summary; limit 10;
    
    2. Filtering:
       fields name,rating; where rating > 80; limit 5;
    
    3. Sorting:
       fields name,first_release_date; sort first_release_date desc; limit 10;
    
    4. Text search:
       search "zelda"; fields name,summary; limit 10;
    
    5. Complex conditions:
       fields name,rating,platforms.name;
       where rating > 75 & platforms = (6,48,130);
       sort rating desc;
       limit 20;
    
    6. Nested fields:
       fields name,cover.url,involved_companies.company.name;

    7. Multi-query for efficient counting and batch operations:

        COUNTING EXAMPLES (Most Efficient):
        // Single count
        query games/count "ps4_2018_count" {
            where release_dates.platform = 48 & release_dates.y = 2018;
        };

        // Multiple counts in one request
        query games/count "ps4_games" {
            where release_dates.platform = 48;
        };
        query games/count "xbox_games" {
            where release_dates.platform = 49;
        };
        query games/count "highly_rated" {
            where rating > 90 & rating_count > 100;
        };

        // Combining counts with data fetching
        query games "top_rpgs" {
            fields name, rating, platforms.name;
            where genres = 12 & rating != null;
            sort rating desc;
            limit 5;
        };
        query games/count "total_rpgs" {
            where genres = 12;
        };
            
    Field Operators:
    - = : Equals
    - != : Not equals
    - > : Greater than
    - >= : Greater than or equal
    - < : Less than
    - <= : Less than or equal
    - ~ : Contains (for arrays)
    - !~ : Does not contain
    
    Logical Operators:
    - & : AND
    - | : OR
    - ! : NOT
    
    Special Values:
    - null : Check for null values
    - () : Array/tuple for multiple values
    - * : All fields (use sparingly)
    """


@mcp.prompt(
    name="search_game",
    title="Search Game",
    description="Search for a game by name and present top 5 results"
)
def search_game(game_name: str) -> str:
    """Searches a game by name."""
    return f"""Search for '{game_name}' and present top 5 results:

1. Use the search_games tool with:
    - Required fields: name,slug,summary,rating,rating_count,first_release_date,platforms.name,genres.name,involved_companies.company.name,involved_companies.developer,involved_companies.publisher
    - Limit: 5

2. Format each result as:

## 🎮 [Name] ([Year from first_release_date])

[Link](https://www.igdb.com/games/[slug])

[Short summary in plain text or "No summary available."]

• **Rating**: [rating]/100 ([rating_count] reviews) or "Not rated"
• **Platforms**: [comma-separated]
• **Genres**: [comma-separated]
• **Developer**: [developer names or "Unknown"]

Handle null values gracefully."""


@mcp.prompt(
    name="game_details",
    title="Game Details",
    description="Get comprehensive details for a game by name"
)
def game_details(game_name: str) -> str:
    """Prompt template for detailed game information."""
    return f"""Get comprehensive details for '{game_name}':

1. Search for game ID using search_games - obtain 5 results, pick the most relevant one based on review counts and ratings (fields: id,slug,name,alternative_names.name,first_release_date,rating,rating_count).
2. Fetch full details with get_game_details (fields: id,slug,name,rating,rating_count,total_rating,total_rating_count,aggregated_rating,aggregated_rating_count,hypes,follows,first_release_date,platforms.name,genres.name,game_modes.name,themes.name,player_perspectives.name,status,summary,storyline,involved_companies.company.name,involved_companies.developer,involved_companies.publisher,category,franchise.name,collection.name,game_engines.name,dlcs.name,expansions.name,expanded_games.name,remasters.name,remasters.first_release_date,remakes.name,remakes.first_release_datesimilar_games.name,similar_games.rating)
3. Structure output:

# [Name] ([Year])

https://www.igdb.com/games/[slug]

IGDB rating: [rating]/100 ([rating_count] reviews)

## Core Info
- Release: [first_release_date as YYYY-MM-DD]
- Platforms: [comma-separated]
- Genres: [comma-separated]
- Modes: [comma-separated]
- Themes: [comma-separated]
- Perspectives: [comma-separated]
- Developers: [developer names or "Unknown"]
- Publishers: [publisher names or "Unknown"]

## Description
[Summary and storyline in plain text or "No description available."]

## Metadata
- ID: [id]
- Category: [category]
- Franchise: 
- Collection: 
- Engine: [game engine names]
- Popularity: follows, hypes

## Related
- DLCs: [dlc names]
- Expansions: [expansion names]
- Remasters: [remaster names] ([remaster first_release_date as YYYY-MM-DD] or "TBA")
- Remakes: [remake names] ([remake first_release_date as YYYY-MM-DD] or "TBA")

## Similar games
Top 5 [similar_games] with name, year, rating sorted by their index in similar_games.

Show "N/A" for missing data."""


@mcp.prompt(
    name="most_anticipated",
    title="Most Anticipated Games",
    description="Find the most anticipated upcoming games based on user hypes on IGDB"
)
def most_anticipated() -> str:
    """Finds the most anticipated upcoming games based on user hypes on IGDB."""
    return """Top most anticipated upcoming games:

1. Use the get_most_anticipated_games tool:
    - Required fields: id,slug,name,hypes,first_release_date,platforms.name,genres.name,involved_companies.company.name,involved_companies.developer,involved_companies.publisher,status
    - Limit: 10
2. Format results as:

## 🎮 [Name] ([first_release_date])

[Link](https://www.igdb.com/games/[slug])

• **Hypes**: [hypes]
• **Platforms**: [comma-separated]
• **Genres**: [comma-separated]
• **Developer**: [developer names or "Unknown"]

3. Include statistics:
   • Hype analysis (average, highest, median)
   • Platform/genre distribution
   • Release timeline breakdown (next 3 months / 6 months / 1 year / TBA)
   • Development status breakdown if available

The tool automatically filters for future releases or TBA games with significant hype."""


def run_server():
    """Main entry point for the server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    # Run the server
    run_server()
