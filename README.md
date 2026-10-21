# IGDB MCP Server

Access the IGDB (Internet Game Database) API through Model Context Protocol (MCP)

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io)
[![FastMCP](https://img.shields.io/badge/FastMCP-Powered-orange)](https://github.com/jlowin/fastmcp)
[![uv](https://img.shields.io/badge/uv-Package%20Manager-purple)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![IGDB API](https://img.shields.io/badge/IGDB-API%20v4-red)](https://api-docs.igdb.com)

## Overview

The IGDB MCP Server provides seamless access to the Internet Game Database (IGDB) through the Model Context Protocol. IGDB is a comprehensive database containing information about video games, including:

- Game metadata (titles, descriptions, ratings)
- Release dates and platforms
- Developer and publisher information
- Genres, themes, and game modes
- User ratings and hype metrics
- Cover art and media

### Key Features

- **Full IGDB API Access**: Search games, get detailed information, find trending titles
- **Smart Caching**: OAuth tokens are cached to minimize authentication overhead
- **Flexible Queries**: Use simple searches or advanced Apicalypse query language
- **Pre-built Prompts**: Common queries ready to use
- **Type-Safe**: Built with Pydantic for robust data validation

## Quick Start

### Prerequisites
- [uv](https://github.com/astral-sh/uv) installed
- MCP-compatible client (Claude Desktop, Cursor, Copilot, or others)

### Get IGDB Credentials
1. Create a [Twitch account](https://www.twitch.tv) (if you don't have one)
2. Go to [Twitch Developer Console](https://dev.twitch.tv/console) → Register Your Application
3. Get your **Client ID** and generate a **Client Secret**

📖 [Full IGDB authentication guide](https://api-docs.igdb.com/#account-creation)

### Configure Your MCP Client

Add this to your MCP client's configuration:

```json
{
  "mcpServers": {
    "igdb-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/bielacki/igdb-mcp-server.git", "igdb-mcp-server"],
      "env": {
        "IGDB_CLIENT_ID": "your_client_id",
        "IGDB_CLIENT_SECRET": "your_secret"
      }
    }
  }
}
```

### Start Exploring

Start exploring with these example prompts:

🔍 **Search & Discovery**
- "Search for Elden Ring and its expansions"
- "Find all Persona games from the last 5 years"
- "Show me games similar to Hades"

📊 **Game Information**
- "Get details about Baldur's Gate 3"
- "Tell me everything about Cyberpunk 2077 including DLC"
- "What platforms is Hogwarts Legacy available on?"

🔥 **Trending & Popular**
- "What are the most anticipated upcoming games?"
- "Show me the highest rated indie games of 2024"
- "Find games with the most hype right now"

🎯 **Advanced Queries**
- "Find games similar to Skyrim with a rating of 85 or higher"
- "List all games by Larian Studios"
- "Show upcoming Silent Hill and Resident Evil games"

## Core Components

### Tools

| Tool | Description | Parameters | Example Usage |
|------|-------------|------------|---------------|
| **search_games** | Search for games by name | • `query` (required): Search term<br>• `fields`: Fields to return (default: basic info)<br>• `limit`: Results count (1-500, default: 10) | "Search for Elden Ring games" |
| **get_game_details** | Get comprehensive game information | • `game_id` (required): IGDB game ID<br>• `fields`: Fields to return (default: extensive) | "Get details for game ID 1942" |
| **get_most_anticipated_games** | Find upcoming games by hype | • `fields`: Fields to return<br>• `limit`: Results count (1-500, default: 25)<br>• `min_hypes`: Min hype count (default: 25) | "Show most anticipated games" |
| **custom_query** | Execute Apicalypse queries | • `endpoint` (required): API endpoint<br>• `query` (required): Apicalypse query string | "Find RPGs rated above 90" |

### Resources

| Resource | Description | Returns |
|----------|-------------|---------|
| **igdb://endpoints** | List of all IGDB API endpoints | Available endpoints with descriptions |
| **igdb://query-syntax** | Apicalypse query language guide | Syntax reference and examples |

### Pre-built Prompts

| Prompt | Description | Use Case |
|--------|-------------|----------|
| **search_game** | Formatted game search results | Quick game discovery with clean output |
| **game_details** | Comprehensive game information | Full details including ratings, platforms, developers |
| **most_anticipated** | Trending upcoming games | Discover hyped unreleased games with statistics |

## Troubleshooting

### Authentication Errors
- **"IGDB_CLIENT_ID not set"**: Check your MCP client config has the env variables
- **"Invalid credentials"**: Verify your Client ID and Secret are correct
- **"Token expired"**: The server handles token refresh automatically

### Rate Limiting
IGDB allows 4 requests per second. The server doesn't implement rate limiting, so:
- Avoid rapid repeated queries
- Use field expansion instead of multiple requests
- Leverage multi-query for batch operations

### Common Query Issues
- **No results**: Check spelling, try broader search terms
- **Missing fields**: Some fields may be null; handle gracefully
- **Query syntax error**: Verify Apicalypse syntax, check semicolons

### Environment Variables
Ensure your MCP client config includes:
```json
"env": {
  "IGDB_CLIENT_ID": "abc123...",
  "IGDB_CLIENT_SECRET": "xyz789..."
}
```

## License & Credits

[MIT License](LICENSE) - see LICENSE file for details


**Credits**:
- IGDB API by [IGDB.com](https://www.igdb.com)
- MCP protocol by Anthropic
- Built with [FastMCP](https://github.com/jlowin/fastmcp)

---

For more information about IGDB API capabilities, visit the [official IGDB API documentation](https://api-docs.igdb.com).