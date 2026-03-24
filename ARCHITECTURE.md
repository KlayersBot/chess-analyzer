# Architecture

The Chess Analyzer Agent is a robust AI pipeline built using the Google Agent Development Kit (ADK). Its primary function is to retrieve a player's recent chess games from Chess.com, parse the moves, evaluate positions via a local Stockfish engine, and generate a play-by-play interactive Markdown report with corresponding chessboard visuals.

## System Components

1. **`agent.py` - AI Orchestrator**
   - Configures the `ChessCoachAgent` using `google.adk.agents.llm_agent.Agent`.
   - Utilizes the `gemini-2.5-flash` model to analyze evaluations and provide personalized coaching commentary for tactical missteps or significant deviations from the engine's best line.

2. **`tools.py` - Core Tools & State Management**
   - **`GameState` Singleton:** Stores the current state of the analysis, maintaining the `chess.Board`, move list, current ply, and user metadata persistently across tool calls.
   - **`initialize_game_analysis(username, game_index)`**: Contacts the `api.chess.com` archives to retrieve PGNs, parses them with `python-chess`, and sets up the board state.
   - **`analyze_next_move()`**: Steps forward one ply, analyzes the position using the Stockfish UCI engine to generate evaluations, and creates a visual board representation via `resvg-python`.
   - **`append_to_report(markdown_content)`**: Sequentially appends the LLM-generated commentary and engine evaluations directly to a local Markdown file (e.g., `report_{user}_{index}.md`), minimizing context overflow inside the agent memory.

3. **External Dependencies**
   - **Stockfish Binary**: Provides the localized engine analysis for scoring and best move determination.
   - **Python-Chess**: Handles PGN parsing, rule enforcement, and SVG generation for the board states.
   - **Chess.com API**: Source of truths for retrieving historical game data.
   - **resvg-python**: Used to convert the SVG board representations from python-chess into PNGs suitable for Markdown display.

## Execution Flow

1. The user asks the `ChessCoachAgent` to review a game (e.g., "Analyze the last 5 games for kar2on").
2. The agent loop iteratively invokes `initialize_game_analysis` -> `analyze_next_move` -> `append_to_report` until completion.
3. Assets (`.png` files) are incrementally written into the `assets/` directory.
4. The final structured output is saved as a Markdown report file.

## Testing

Testing is done using `pytest`. The primary tests evaluate the robustness of our tool functions, such as proper HTTP error handling and accurate JSON return responses from the tools.