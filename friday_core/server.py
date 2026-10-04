#!/usr/bin/env python3
"""
SEVA AI FastMCP Server
Main entry point for the Sagar Tamang's F.R.I.D.A.Y. engine.
Exposes all kiosk capabilities as standardized @mcp.tool endpoints.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.fastmcp import FastMCP

from friday_core.tools.portal_tool import register_portal_tools
from friday_core.tools.mobile_tool import register_mobile_tools
from friday_core.tools.printer_tool import register_printer_tools
from friday_core.tools.offline_tool import register_offline_tools
from friday_core.voice_agent import VoiceAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP("SEVA AI Kiosk Server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SEVA AI FastMCP Server...")
    voice_agent = VoiceAgent()
    await voice_agent.start()
    app.state.voice_agent = voice_agent
    yield
    await voice_agent.stop()
    logger.info("SEVA AI FastMCP Server stopped.")


app = FastAPI(title="SEVA AI Kiosk", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def register_all_tools():
    register_portal_tools(mcp)
    register_mobile_tools(mcp)
    register_printer_tools(mcp)
    register_offline_tools(mcp)
    logger.info("All MCP tools registered successfully")


register_all_tools()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SEVA AI Kiosk"}


@app.get("/tools")
async def list_tools():
    return {"tools": list(mcp._tools.keys())}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)