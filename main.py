import asyncio
from typing import Annotated
import aiohttp 
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.bearer import BearerAuthProvider, RSAKeyPair
from mcp.server.auth.provider import AccessToken
from mcp.types import TextContent
from pydantic import Field

# --- Load environment variables ---
load_dotenv()

TOKEN = 'auth_token'
MY_NUMBER = '919818039142'

assert TOKEN is not None, "Please set AUTH_TOKEN in your .env file"
assert MY_NUMBER is not None, "Please set MY_NUMBER in your .env file"

# --- Auth Provider ---
class SimpleBearerAuthProvider(BearerAuthProvider):
    def __init__(self, token: str):
        k = RSAKeyPair.generate()
        super().__init__(public_key=k.public_key, jwks_uri=None, issuer=None, audience=None)
        self.token = token

    async def load_access_token(self, token: str) -> AccessToken | None:
        if token == self.token:
            return AccessToken(
                token=token,
                client_id="math-client",
                scopes=["*"],
                expires_at=None,
            )
        return None

mcp = FastMCP(
    "Simple Math MCP Server",
    auth=SimpleBearerAuthProvider(TOKEN),
)

@mcp.tool
async def validate() -> str:
    return MY_NUMBER

# --- Tool: add_numbers ---
@mcp.tool(description="Add two numbers together and return the result")
async def add_numbers(
    number1: Annotated[float, Field(description="First number to add")],
    number2: Annotated[float, Field(description="Second number to add")],
) -> list[TextContent]:
    """Add two numbers and return the result."""
    result = number1 + number2
    return [TextContent(type="text", text=f"The sum of {number1} and {number2} is {result}")]


@mcp.tool(description="Generate a meme for a given topic by calling the meme generation API")
async def generate_meme(
    topic: Annotated[str, Field(description="Topic to search for news and generate a meme")],
    article_index: Annotated[int, Field(description="Index of the news article to use", ge=0)] = 0
) -> list[TextContent]:
    """
    Generate a meme using the topic and optional article index by sending a POST request
    to the meme generation API.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://memegen-lb2x.onrender.com/puch_generate_meme",
                json={"topic": topic, "articleIndex": article_index},
                timeout=60
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return [TextContent(type="text", text=f"API request failed: {error_text}")]
                
                data = await resp.json()
                
                if not data.get("success"):
                    return [TextContent(type="text", text=f"Error: {data.get('error', 'Unknown error')}")]

                meme_url = data["memeUrl"]
                article = data.get("article", {})
                caption = data.get("caption", {})

                return [
                    TextContent(type="text", text=f"**Meme Generated!**\nTopic: {topic}\n\n"
                                                  f"Article: {article.get('title')}\n"
                                                  f"Description: {article.get('description')}\n"
                                                  f"Caption: {caption.get('topText', '')} / {caption.get('bottomText', '')}\n"
                                                  f"Meme URL: {meme_url}")
                ]

    except Exception as e:
        return [TextContent(type="text", text=f"Exception occurred: {str(e)}")]


# --- Run MCP Server ---
async def main():
    print("🧮 Starting Simple Math MCP server on http://0.0.0.0:8086")
    await mcp.run_async("streamable-http", host="0.0.0.0", port=8086)

if __name__ == "__main__":
    asyncio.run(main())

