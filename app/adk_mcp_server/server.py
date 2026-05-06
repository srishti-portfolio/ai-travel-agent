"""
MCP server exposing Google Maps tools over stdio.

This is the "tool/data source" half of the assignment. The ADK agent
(in app/agent/agent.py) connects to this server via stdio and calls
these tools through the Model Context Protocol.

IMPORTANT: When running over stdio, stdout is reserved for the MCP
protocol. All logging MUST go to stderr (use sys.stderr or logging
configured to stderr), never print() to stdout.
"""
import asyncio
import json
import logging
import os
import sys

import requests
from dotenv import load_dotenv

from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

# Log to stderr - stdout is the MCP transport channel
logging.basicConfig(
  level=logging.INFO,
  format="[mcp-server] %(asctime)s %(levelname)s %(message)s",
  stream=sys.stderr,
)
log = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
  log.warning("GOOGLE_MAPS_API_KEY is not set - tool calls will fail")

HTTP_TIMEOUT = 10  # seconds


# -------- TOOLS --------

def get_places(city: str) -> dict:
  """Find tourist places in a given city using Google Maps Text Search."""
  url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
  params = {"query": f"tourist places in {city}", "key": API_KEY}
  try:
    res = requests.get(url, params=params, timeout=HTTP_TIMEOUT).json()
  except requests.RequestException as e:
    return {"error": f"Network error contacting Google Maps: {e}"}

  if res.get("status") not in ("OK", "ZERO_RESULTS"):
    return {"error": res.get("error_message") or res.get("status", "Unknown error")}

  places = [
    {"name": p.get("name"), "address": p.get("formatted_address"), "rating": p.get("rating")}
    for p in res.get("results", [])[:10]
  ]
  return {"city": city, "places": places}


def get_directions(origin: str, destination: str) -> dict:
  """Get distance and duration between two places using Google Maps Directions."""
  url = "https://maps.googleapis.com/maps/api/directions/json"
  params = {"origin": origin, "destination": destination, "key": API_KEY}
  try:
    res = requests.get(url, params=params, timeout=HTTP_TIMEOUT).json()
  except requests.RequestException as e:
    return {"error": f"Network error contacting Google Maps: {e}"}

  if res.get("status") != "OK" or not res.get("routes"):
    return {"error": res.get("error_message") or res.get("status", "No route found")}

  leg = res["routes"][0]["legs"][0]
  return {
    "origin": origin,
    "destination": destination,
    "distance": leg["distance"]["text"],
    "duration": leg["duration"]["text"],
  }


places_tool = FunctionTool(get_places)
directions_tool = FunctionTool(get_directions)

# -------- MCP SERVER --------

app = Server("tourist-mcp-server")


@app.list_tools()
async def list_tools():
  return [
    adk_to_mcp_tool_type(places_tool),
    adk_to_mcp_tool_type(directions_tool),
  ]


@app.call_tool()
async def call_tool(name: str, arguments: dict):
  log.info("call_tool name=%s args=%s", name, arguments)
  try:
    if name == places_tool.name:
      result = get_places(**arguments)
    elif name == directions_tool.name:
      result = get_directions(**arguments)
    else:
      result = {"error": f"Tool not found: {name}"}
  except TypeError as e:
    result = {"error": f"Bad arguments for {name}: {e}"}
  except Exception as e:
    log.exception("Unhandled error in tool %s", name)
    result = {"error": f"Unexpected error: {e}"}

  return [mcp_types.TextContent(type="text", text=json.dumps(result))]


async def main():
  log.info("Starting tourist MCP server on stdio")
  async with mcp.server.stdio.stdio_server() as (read, write):
    await app.run(
      read,
      write,
      InitializationOptions(
        server_name="tourist-server",
        server_version="1.0.0",
        capabilities=app.get_capabilities(
          notification_options=NotificationOptions(),
          experimental_capabilities={},
        ),
      ),
    )


if __name__ == "__main__":
  asyncio.run(main())