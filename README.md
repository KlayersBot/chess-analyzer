# Chess Analyzer

A Python pipeline that pulls recent chess games from the Chess.com API, parses the PGN, generates visual board states using `python-chess`, and provides tactical commentary using Stockfish.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You will also need to download a local binary for Stockfish and place it in this directory (or point the script to it).

## Usage

```bash
python analyze.py --user keith --engine /path/to/stockfish
```

This generates `report.md` along with move-by-move PNG images in the `assets/` directory.
