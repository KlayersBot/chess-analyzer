import requests
import chess
import chess.pgn
import chess.svg
import chess.engine
import io
import os
import cairosvg
import argparse

def fetch_latest_game(username):
    headers = {'User-Agent': 'ChessAnalyzerBot/1.0 (https://github.com/KlayersBot/chess-analyzer)'}
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    resp = requests.get(archives_url, headers=headers)
    resp.raise_for_status()
    archives = resp.json().get('archives', [])
    if not archives:
        raise Exception("No archives found.")
    
    games_url = archives[-1]
    games_resp = requests.get(games_url, headers=headers)
    games_resp.raise_for_status()
    games = games_resp.json().get('games', [])
    
    # Find the last completed game with moves
    for game in reversed(games):
        if game.get('rules') == 'chess' and game.get('pgn'):
            return game['pgn']
    raise Exception("No valid games found.")

def analyze_game(pgn_string, engine_path="stockfish", username="keith"):
    pgn = io.StringIO(pgn_string)
    game = chess.pgn.read_game(pgn)
    
    os.makedirs("assets", exist_ok=True)
    
    board = game.board()
    
    # Determine player color for board orientation
    player_color = chess.WHITE
    if game.headers.get("Black", "").lower() == username.lower():
        player_color = chess.BLACK

    engine = None
    if os.path.exists(engine_path):
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    else:
        print(f"Warning: Stockfish engine not found at {engine_path}. Commentary will be limited.")
        
    report = f"# Chess Game Analysis: {game.headers.get('White', '?')} vs {game.headers.get('Black', '?')}\n\n"
    report += f"- **Result:** {game.headers.get('Result', '?')}\n"
    report += f"- **Date:** {game.headers.get('Date', '?')}\n"
    
    eco = game.headers.get('ECOUrl', '').split('/')[-1].replace('-', ' ')
    if eco:
        report += f"- **Opening:** {eco}\n\n"
    else:
        report += "\n"
    
    prev_cp = 0
    
    for i, move in enumerate(game.mainline_moves()):
        board.push(move)
        move_number = (i // 2) + 1
        color_str = "White" if i % 2 == 0 else "Black"
        
        # Generate SVG and convert to PNG
        svg_data = chess.svg.board(board, orientation=player_color, lastmove=move)
        img_filename = f"move_{i+1:03d}.png"
        img_path = os.path.join("assets", img_filename)
        cairosvg.svg2png(bytestring=svg_data.encode('utf-8'), write_to=img_path)
        
        report += f"### Move {move_number} ({color_str}): {move}\n\n"
        report += f"![Board State](assets/{img_filename})\n\n"
        
        # Engine Analysis
        if engine:
            try:
                info = engine.analyse(board, chess.engine.Limit(time=0.1))
                
                # Get perspective evaluation
                score = info["score"].white() if player_color == chess.WHITE else info["score"].black()
                cp = score.score(mate_score=10000)
                
                if cp is not None:
                    eval_diff = cp - prev_cp
                    report += f"**Evaluation:** {cp/100.0:+.2f} \n\n"
                    
                    # Only comment on the player's moves, or massive opponent blunders
                    is_player_turn = ((i % 2 == 0 and player_color == chess.WHITE) or 
                                      (i % 2 != 0 and player_color == chess.BLACK))
                    
                    if is_player_turn:
                        if eval_diff <= -300:
                            report += f"> **Commentary:** Blunder! You just gave away a massive advantage. Tactical misstep.\n\n"
                        elif eval_diff <= -100:
                            report += f"> **Commentary:** Mistake. You missed a better continuation here.\n\n"
                        elif eval_diff >= 200:
                            report += f"> **Commentary:** Brilliant! You found a crushing tactical continuation.\n\n"
                    else:
                        # Opponent made a move
                        if eval_diff >= 300:
                            report += f"> **Commentary:** Your opponent just blundered! Find the punishment.\n\n"
                            
                    prev_cp = cp
            except Exception as e:
                report += f"*(Engine evaluation skipped: {e})*\n\n"
        
    if engine:
        engine.quit()
        
    with open("report.md", "w") as f:
        f.write(report)
    print("Analysis complete. Saved to report.md")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze a Chess.com game.")
    parser.add_argument("--user", default="keith", help="Chess.com username")
    parser.add_argument("--engine", default="./stockfish", help="Path to Stockfish binary")
    args = parser.parse_args()
    
    try:
        print(f"Fetching latest game for {args.user}...")
        pgn = fetch_latest_game(args.user)
        print("Analyzing game...")
        analyze_game(pgn, engine_path=args.engine, username=args.user)
    except Exception as e:
        print(f"Error: {e}")
