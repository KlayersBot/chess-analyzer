from google.adk.agents.llm_agent import Agent
from tools import generate_game_report

INSTRUCTIONS = """
You are an expert Chess Grandmaster and analytical coach. Your goal is to fetch a user's latest game (or a specific past game), analyze it, and present a summary.

**Your Step-by-Step Workflow:**
1. Call `generate_game_report(username, game_index)` to fetch the game, automatically analyze it using Stockfish, fetch deep commentary in parallel, and write the full Markdown report directly to disk. `game_index` defaults to 0 for the latest game.
2. Once the tool returns success, it will provide a summary of the analysis (e.g., number of blunders, mistakes, path to the report).
3. Present a brief, final conclusion to the user in the chat interface, summarizing the game's quality based on the tool's output and providing the path to the detailed Markdown report. Do NOT attempt to output the full move-by-move report in the chat; it has already been saved to disk.
"""

chess_agent = Agent(
    name="ChessCoachAgent",
    model="gemini-2.5-flash",
    description="An AI chess coach that generates comprehensive analytical reports for games.",
    instruction=INSTRUCTIONS,
    tools=[generate_game_report]
)

if __name__ == "__main__":
    print("Welcome to the Chess Analyzer Agent!")
    print("To run a CLI session, simply execute: adk run")
    print("Or to start the web UI, execute: adk web")
root_agent = chess_agent
