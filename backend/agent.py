import asyncio
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_openai import ChatOpenAI

from langchain_mcp_adapters.client import (
    MultiServerMCPClient
)

from langgraph.graph import (
    StateGraph,
    MessagesState,
    START,
    END
)

from langgraph.prebuilt import (
    ToolNode,
    tools_condition
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent


MCP_SERVER = (
    BASE_DIR / "mcp_server.py"
)




# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Agent Development Workshop"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],                # 5173 4200

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]

)


# ============================================================
# REQUEST MODEL
# ============================================================

class QueryRequest(BaseModel):

    query: str


# ============================================================
# GLOBALS
# ============================================================

mcp_client = None

tools = []

graph = None


# ============================================================
# LLM
# ============================================================

llm = ChatOpenAI(

    model="gpt-5.6",

    temperature=0,

    reasoning_effort="none"

)


# ============================================================
# EXTRACT SENDER
# ============================================================

def extract_sender(query: str):

    query_lower = query.lower().strip()


    patterns = [

        r"search\s+(?:an?\s+)?email(?:s)?\s+from\s+(.+)",

        r"search\s+(?:my\s+)?email(?:s)?\s+from\s+(.+)",

        r"find\s+(?:an?\s+)?email(?:s)?\s+from\s+(.+)",

        r"find\s+(?:my\s+)?email(?:s)?\s+from\s+(.+)",

        r"show\s+(?:my\s+)?email(?:s)?\s+from\s+(.+)",

    ]


    for pattern in patterns:

        match = re.match(
            pattern,
            query_lower
        )

        if match:

            sender = match.group(1).strip()

            sender = re.sub(
                r"\s+(?:in|on|from)\s+gmail.*$",
                "",
                sender
            ).strip()

            return sender


    return None


# ============================================================
# EXTRACT DRIVE QUERY
# ============================================================

def extract_drive_query(query: str):

    query_lower = query.lower().strip()


    patterns = [

        r"search\s+(.+?)\s+in\s+(?:google\s+)?drive",

        r"find\s+(.+?)\s+in\s+(?:google\s+)?drive",

        r"search\s+(?:google\s+)?drive\s+for\s+(.+)",

        r"find\s+(?:google\s+)?drive\s+for\s+(.+)",

    ]


    for pattern in patterns:

        match = re.match(
            pattern,
            query_lower
        )

        if match:

            return match.group(1).strip()


    return None


# ============================================================
# VALIDATE CONTEXT
# ============================================================

def detect_context(query: str):

    sender = extract_sender(
        query
    )

    if sender:

        return "gmail", sender


    drive_query = extract_drive_query(
        query
    )

    if drive_query:

        return "drive", drive_query


    return "invalid", None


# ============================================================
# AGENT NODE
# ============================================================

def agent_node(state: MessagesState):

    response = llm.bind_tools(
        tools
    ).invoke(
        state["messages"]
    )

    return {
        "messages": response
    }


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    global mcp_client
    global tools
    global graph


    print()
    print("=" * 60)
    print("Starting Agent Development Workshop")
    print("=" * 60)


    # --------------------------------------------------------
    # MCP CLIENT
    # --------------------------------------------------------

    mcp_client = MultiServerMCPClient({

        "google_tools": {

            "transport": "stdio",

            "command": sys.executable,

            "args": [
                str(MCP_SERVER)
            ]

        }

    })


    # --------------------------------------------------------
    # LOAD MCP TOOLS
    # --------------------------------------------------------

    tools = await mcp_client.get_tools()


    print()
    print("MCP Tools Loaded:")


    for tool in tools:

        print(
            f"- {tool.name}"
        )


    # --------------------------------------------------------
    # LANGGRAPH
    # --------------------------------------------------------

    workflow = StateGraph(
        MessagesState
    )


    workflow.add_node(
        "agent",
        agent_node
    )


    workflow.add_node(
        "tools",
        ToolNode(tools)
    )


    workflow.add_edge(
        START,
        "agent"
    )


    workflow.add_conditional_edges(

        "agent",

        tools_condition

    )


    workflow.add_edge(
        "tools",
        "agent"
    )


    graph = workflow.compile()


    print()
    print("LangGraph initialized.")

    print()
    print("Server ready.")

    print("=" * 60)
    print()


# ============================================================
# QUERY API
# ============================================================

@app.post("/query")
async def query_agent(
    request: QueryRequest
):

    query = request.query.strip()


    if not query:

        return {

            "answer":
                "Invalid context. Please provide a query."

        }


    # ========================================================
    # HARD CONTEXT CHECK
    # ========================================================

    context, value = detect_context(
        query
    )


    # ========================================================
    # INVALID
    # ========================================================

    if context == "invalid":

        return {

            "answer": (
                "Invalid context.\n\n"
                "I can only search:\n"
                "1. Gmail\n"
                "2. Google Drive"
            )

        }


    # ========================================================
    # GMAIL
    # ========================================================

    if context == "gmail":

        tool = next(

            (
                t
                for t in tools
                if t.name == "search_gmail"
            ),

            None

        )


        if tool is None:

            return {

                "answer":
                    "Gmail tool is not available."

            }


        # ----------------------------------------------------
        # DIRECT TOOL CALL
        #
        # This guarantees strict sender behavior.
        #
        # We do NOT ask the LLM to construct the sender.
        # ----------------------------------------------------

        try:

            result = await tool.ainvoke({

                "sender": value

            })


            return {

                "answer": str(result)

            }


        except Exception as error:

            print(
                "Gmail error:",
                repr(error)
            )


            return {

                "answer":
                    f"Gmail search failed: {error}"

            }


    # ========================================================
    # GOOGLE DRIVE
    # ========================================================

    if context == "drive":

        tool = next(

            (
                t
                for t in tools
                if t.name == "search_google_drive"
            ),

            None

        )


        if tool is None:

            return {

                "answer":
                    "Google Drive tool is not available."

            }


        try:

            result = await tool.ainvoke({

                "query": value

            })


            return {

                "answer": str(result)

            }


        except Exception as error:

            print(
                "Google Drive error:",
                repr(error)
            )


            return {

                "answer":
                    f"Google Drive search failed: {error}"

            }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
def home():

    return {

        "message":
            "Agent Development Workshop API",

        "status":
            "online"

    }


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    import uvicorn


    uvicorn.run(

        app,

        host="0.0.0.0",

        port=8000

    )