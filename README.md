# Chess Analyzer Agent

An intelligent AI chess coach powered by Google's Agent Development Kit (ADK) and Gemini 3.1. It pulls recent chess games from the Chess.com API, analyzes the positions using Stockfish to detect subtle tactics and blunders, and generates a visual, move-by-move Markdown report with insightful commentary.

## Setup

```bash
uv sync
```

You will need a local binary for Stockfish placed in this directory (or update the engine path in `tools.py`). 

*Note: As an ADK project using Application Default Credentials (ADC) / metadata service credentials, no `.env` file is necessary for Gemini API keys in the supported environment.*

## Usage

You can interact with the AI Chess Coach in two ways:

**1. Command Line Interface (CLI)**
```bash
uv run adk run
```

**2. Local Web Interface**
```bash
uv run adk web
```

Once the interface starts, simply ask the agent:
> *"Analyze the latest game for the user 'keith' and point out where I missed tactics."*

