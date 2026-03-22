# Chess Analyzer Implementation Plan (Revised)

**Project:** Chess.com Game Fetcher & Visual Analyzer
**Target User:** Keith
**Core Tech Stack:** Python, `requests` (Chess.com API), `python-chess` (PGN parsing, board visualization, UCI engine interaction), `pytest` (Testing)

## Objective
Build a resilient, automated pipeline that pulls your recent chess games from the public Chess.com API, parses the PGN, generates visual board states for every single move using `python-chess`, and provides move-by-move tactical commentary. 

---

## Phase 1: Data Acquisition (Chess.com API)
- **Endpoint:** Use the PubAPI to fetch archives: `https://api.chess.com/pub/player/{username}/games/archives`
- **Target:** Pull the most recent month's archive, filter for the last completed game.
- **Hygiene & Error Handling:**
  - Implement exponential backoff for HTTP 429 (Rate Limit) and 5xx errors.
  - Set a custom `User-Agent` string (Chess.com API strictly requires this or they will block the request).
  - Handle "Aborted" games (games with 0 or 1 move) by skipping to the next valid completed game.

## Phase 2: Game Parsing & Visualization (`python-chess`)
- **Dependencies:** `chess`, `chess.pgn`, `chess.svg`, and `cairosvg` (for converting SVG strings to PNG bytes).
- **Workflow:**
  1. Load the PGN string into a `chess.pgn.Game` object.
  2. Iterate through `game.mainline_moves()`.
  3. After each push, use `chess.svg.board(board)` to generate an SVG.
  4. Convert the SVG to PNG and save it (e.g., `assets/move_001_w.png`).
- **Edge Cases to Handle:**
  - Verify castling, *en passant*, and underpromotions render correctly in `chess.svg`.
  - Flip the board perspective based on which color Keith played (Black vs. White).
  - Highlight the most recent move using the `arrows` or `squares` parameters.

## Phase 3: Commentary Engine & Stockfish Integration
*Getting & Interacting with Stockfish:*
- **Binary Acquisition:** The Stockfish binary will be downloaded as part of the setup script (via package manager like `apt-get install stockfish`, `brew install stockfish`, or fetching the pre-compiled binary directly from GitHub releases for CI/CD environments).
- **Interaction (UCI Protocol):** We will use `python-chess`'s native engine module (`chess.engine.SimpleEngine.popen_uci("path/to/stockfish")`) to communicate with the binary via the Universal Chess Interface (UCI) protocol.

*Tactical Detection Workflow:*
1. **Analyze Position:** For each board state, call `engine.analyse(board, chess.engine.Limit(time=0.1))` to get the evaluation and top lines.
2. **Tactical Detection:** Compare the evaluation of the actual move played against the evaluation of the engine's best move. 
   - Detect *missed tactics* (e.g., the engine saw a +5.0 material gain or forced mate, but the played move dropped the eval to +0.5).
   - Detect *executed tactics* (e.g., the played move matches the engine's only winning tactical line).
3. **LLM Narrative:** Feed the PGN subset, Stockfish evaluations, and identified tactical motifs to an LLM (e.g., Gemini/Claude). Prompt the LLM to focus the narrative explicitly on these tactics—praising a well-executed skewer or ruthlessly pointing out a missed mate-in-3.
4. **Hygiene:** Set strict timeout limits on the Stockfish evaluation to prevent hanging. Filter LLM prompts so it only comments on pivotal tactical moments, skipping quiet positional maneuvers.

## Phase 4: Assembly & Output
- **Markdown Report Generator:** Stitch the generated images and the commentary text into a chronological Markdown file.
- **Structure:**
  - Game Metadata (White vs Black, Date, Opening Name, Result, Accuracy)
  - Move-by-Move Breakdown
- **Hygiene:** Ensure image paths are relative so the Markdown renders correctly when pushed to GitHub.

## Phase 5: Automation & Deployment
- Wrap the entire script into a CLI command: `python analyze.py --user keith --latest`
- Add a GitHub Actions workflow or a cron job to automatically run this script daily, generate the report, and commit it to the repository.

---

## Phase 6: Testing & Quality Assurance (Hygiene)
To ensure the analyzer doesn't break silently or generate garbage outputs, a robust testing suite using `pytest` is required.

### 1. Unit Tests
- **API Fetcher:** Mock the `requests` library to simulate Chess.com API responses.
- **PGN Parser:** Feed known, hardcoded PGN strings and assert the correct number of moves are parsed.
- **Stockfish Integration:** Pass a known blunder position to the engine wrapper and assert that the centipawn drop exceeds the blunder threshold.

### 2. Integration Tests
- Run the full pipeline (API -> PGN -> SVG -> Report) using a mocked API response.
- **Output Validation:** Check that the final Markdown file exists, contains the correct metadata, and references the exact number of expected PNG files.

### 3. Visual Regression / Snapshot Testing
- Save a "golden" set of SVG/PNG outputs for a specific known game.
- During testing, generate the images for that game and do a byte-comparison against the golden set.

### 4. Continuous Integration
- Configure a GitHub Action (`.github/workflows/test.yml`) to run the `pytest` suite on every push.
