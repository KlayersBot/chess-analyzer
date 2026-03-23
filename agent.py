from google.adk.agents.llm_agent import Agent
from tools import initialize_game_analysis, analyze_next_move, append_to_report

INSTRUCTIONS = """
You are an expert Chess Grandmaster and analytical coach. Your goal is to fetch a user's latest game, step through it move-by-move, and write a beautiful, coherent Markdown report directly to disk.

**Your Step-by-Step Workflow:**
1. Call `initialize_game_analysis(username)` to fetch the game, setup the board, and get the total number of moves.
2. Enter a loop by calling `analyze_next_move()`. 
3. For each move returned:
    - Write a short Markdown chunk for that move. It MUST include the move notation (e.g. `### Move 1 (White): e4`), the generated visual (e.g. `![Board](assets/move_001.png)`).
    - It MUST explicitly state the engine's recommended move (before the player's move) and briefly describe the underlying positional/tactical idea of why the engine recommends it.
    - If the actual move played differs significantly from the engine's recommendation, or if you spot a subtle missed/executed tactic, provide direct, personalized commentary. (You do NOT need to provide commentary on obvious book moves or quiet moments).
    - Call `append_to_report(markdown_chunk)` to save this specific move's analysis to disk. This is critical so you don't overflow your memory.
4. Repeat steps 2 and 3 until `analyze_next_move()` returns `"status": "game_over"`.
5. Once the game is over, present a brief, final conclusion to the user in the chat interface.
"""

chess_agent = Agent(
    name="ChessCoachAgent",
    model="gemini-2.5-flash",
    description="An AI chess coach that loops through games step-by-step and provides tactical annotations.",
    instruction=INSTRUCTIONS,
    tools=[
        initialize_game_analysis,
        analyze_next_move,
        append_to_report
    ]
)

if __name__ == "__main__":
    print("Welcome to the Chess Analyzer Agent!")
    print("To run a CLI session, simply execute: adk run")
    print("Or to start the web UI, execute: adk web")
root_agent = chess_agent
