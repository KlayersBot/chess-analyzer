import requests
import chess
import chess.pgn
import chess.svg
import chess.engine
import io
import os
import json
from resvg_python import svg_to_png
from google import genai

# Global state to allow the agent to step through the game one move at a time
class GameState:
    def __init__(self):
        self.board = None
        self.moves = []
        self.player_color = None
        self.current_ply = 0
        self.engine = None
        self.metadata = {}
        self.username = ""
        self.game_dir = ""
        self.report_filename = "report.md"

GAME_STATE = GameState()

def initialize_game_analysis(username: str, game_index: int = 0) -> str:
    """Fetches a recent game for the user and initializes the board for step-by-step analysis.
    Call this FIRST. It returns the game metadata and total number of moves.
    `game_index` defaults to 0 (latest game), 1 is the previous game, etc.
    """
    headers = {'User-Agent': 'ChessAnalyzerBot/1.0 (https://github.com/KlayersBot/chess-analyzer)'}
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    resp = requests.get(archives_url, headers=headers)
    if resp.status_code == 404:
        return json.dumps({"error": f"User '{username}' not found."})
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        return json.dumps({"error": f"Failed to fetch archives: {str(e)}"})
    
    archives = resp.json().get('archives', [])
    if not archives:
        return json.dumps({"error": "No archives found."})
    
    pgn_string = None
    valid_games = []
    
    # Look back through archives until we find enough games
    for games_url in reversed(archives):
        games_resp = requests.get(games_url, headers=headers)
        try:
            games_resp.raise_for_status()
        except requests.exceptions.HTTPError:
            continue
            
        games = games_resp.json().get('games', [])
        
        for game in reversed(games):
            if game.get('rules') == 'chess' and game.get('pgn'):
                valid_games.append(game['pgn'])
                if len(valid_games) > game_index:
                    break
        
        if len(valid_games) > game_index:
            break
            
    if len(valid_games) <= game_index:
        return json.dumps({"error": f"Could not find game at index {game_index}."})
        
    pgn_string = valid_games[game_index]

    pgn = io.StringIO(pgn_string)
    game = chess.pgn.read_game(pgn)
    
    game_dir = os.path.join("games", f"{username}_{game_index}")
    assets_dir = os.path.join(game_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    GAME_STATE.board = game.board()
    GAME_STATE.moves = list(game.mainline_moves())
    GAME_STATE.current_ply = 0
    GAME_STATE.username = username
    GAME_STATE.game_dir = game_dir
    GAME_STATE.report_filename = os.path.join(game_dir, f"report_{username}_{game_index}.md")
    
    GAME_STATE.metadata = {
        "White": game.headers.get('White', '?'),
        "Black": game.headers.get('Black', '?'),
        "Result": game.headers.get('Result', '?'),
        "Date": game.headers.get('Date', '?'),
        "Opening": game.headers.get('ECOUrl', '').split('/')[-1].replace('-', ' ')
    }
    
    GAME_STATE.player_color = chess.WHITE if GAME_STATE.metadata["White"].lower() == username.lower() else chess.BLACK

    if not GAME_STATE.engine:
        engine_path = "./stockfish"
        if os.path.exists(engine_path):
            GAME_STATE.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            
    # Reset the report file
    with open(GAME_STATE.report_filename, "w") as f:
        f.write(f"# Chess Game Analysis: {GAME_STATE.metadata['White']} vs {GAME_STATE.metadata['Black']}\n\n")
        f.write(f"- **Result:** {GAME_STATE.metadata['Result']}\n")
        f.write(f"- **Date:** {GAME_STATE.metadata['Date']}\n")
        f.write(f"- **Opening:** {GAME_STATE.metadata['Opening']}\n\n")
            
    return json.dumps({
        "status": "ready",
        "report_filename": GAME_STATE.report_filename,
        "total_moves": len(GAME_STATE.moves),
        "metadata": GAME_STATE.metadata
    })

def analyze_next_move() -> str:
    """Advances the game by ONE move and returns the engine evaluation.
    Call this repeatedly in a loop. When it returns 'status': 'game_over', the analysis is complete.
    """
    if GAME_STATE.current_ply >= len(GAME_STATE.moves):
        # Cleanup engine on completion
        if GAME_STATE.engine:
            GAME_STATE.engine.quit()
            GAME_STATE.engine = None
        return json.dumps({"status": "game_over"})
        
    board = GAME_STATE.board
    move = GAME_STATE.moves[GAME_STATE.current_ply]
    
    move_number = (GAME_STATE.current_ply // 2) + 1
    color_moved_str = "White" if GAME_STATE.current_ply % 2 == 0 else "Black"
    color_moved = chess.WHITE if GAME_STATE.current_ply % 2 == 0 else chess.BLACK
    is_player_turn = ((GAME_STATE.current_ply % 2 == 0 and GAME_STATE.player_color == chess.WHITE) or 
                      (GAME_STATE.current_ply % 2 != 0 and GAME_STATE.player_color == chess.BLACK))
    
    move_info = {
        "status": "success",
        "move_number": move_number,
        "color": color_moved_str,
        "is_player_turn": is_player_turn,
        "evaluation_before_move": None,
        "evaluation_after_move": None,
        "move_label": "Good",
        "deep_commentary": None,
        "engine_recommended_move": None,
        "actual_move_played": None,
        "image_path": None
    }
    
    eval_before_val = 0.0
    eval_after_val = 0.0
    best_move_san = None
    
    # Analyze the position BEFORE the move is pushed
    if GAME_STATE.engine:
        try:
            info = GAME_STATE.engine.analyse(board, chess.engine.Limit(time=0.1))
            # Always get relative to White for easier math
            score_w = info["score"].white()
            if score_w.score() is not None:
                eval_before_val = score_w.score() / 100.0
            else:
                eval_before_val = 100.0 if score_w.mate() > 0 else -100.0
            
            # Keep evaluation relative to player for the old field if needed
            score_player = info["score"].white() if GAME_STATE.player_color == chess.WHITE else info["score"].black()
            cp = score_player.score(mate_score=10000)
            if cp is not None:
                move_info["evaluation_before_move"] = cp / 100.0
            
            best_move = info.get("pv", [None])[0]
            if best_move:
                best_move_san = board.san(best_move)
                move_info["engine_recommended_move"] = best_move_san
        except Exception as e:
            move_info["error_before"] = str(e)

    # Now push the move
    actual_move_san = board.san(move)
    move_info["actual_move_played"] = actual_move_san
    board.push(move)
    
    mate_moves = None
    # Analyze AFTER the move
    if GAME_STATE.engine:
        try:
            info_after = GAME_STATE.engine.analyse(board, chess.engine.Limit(time=0.1))
            score_w = info_after["score"].white()
            mate_moves = score_w.mate()
            if score_w.score() is not None:
                eval_after_val = score_w.score() / 100.0
            else:
                eval_after_val = 100.0 if score_w.mate() > 0 else -100.0
            
            score_player = info_after["score"].white() if GAME_STATE.player_color == chess.WHITE else info_after["score"].black()
            cp = score_player.score(mate_score=10000)
            if cp is not None:
                move_info["evaluation_after_move"] = cp / 100.0
        except Exception as e:
            move_info["error_after"] = str(e)

    # Calculate Delta (from the perspective of the player who just moved)
    if color_moved == chess.WHITE:
        delta = eval_after_val - eval_before_val
    else:
        delta = eval_before_val - eval_after_val
        
    # Label heuristic
    label = "Good"
    if delta <= -3.0:
        label = "Blunder"
    elif delta <= -1.0:
        label = "Mistake"
    elif delta <= -0.5:
        label = "Inaccuracy"
    elif actual_move_san == best_move_san:
        label = "Best Move"
    elif delta >= 1.5 and -2.0 < eval_before_val < 2.0:
        label = "Brilliant"
    
    move_info["move_label"] = label
    
    # Get Deep Commentary using gemini-2.5-pro for interesting moves
    if label in ["Blunder", "Mistake", "Brilliant", "Great Move"]:
        try:
            client = genai.Client()
            prompt = f"""You are an expert Chess Grandmaster. 
The player ({color_moved_str}) just played {actual_move_san}.
This move was evaluated as a {label}.
Evaluation went from {eval_before_val:.2f} to {eval_after_val:.2f}.
The engine's recommended best move was {best_move_san}.
Here is the current FEN: {board.fen()}
Provide a short, deeply insightful 2-3 sentence commentary on WHY this move was a {label}, focusing on the tactical or positional consequences. Do NOT just repeat the evaluation numbers, explain the chess ideas."""
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=prompt,
            )
            move_info["deep_commentary"] = response.text.strip()
        except Exception as e:
            move_info["deep_commentary"] = f"Error getting deep commentary: {str(e)}"

    # Generate composite SVG with Evaluation Bar
    original_svg = str(chess.svg.board(board, orientation=GAME_STATE.player_color, lastmove=move))
    if original_svg.startswith("<?xml"):
        original_svg = original_svg.split("?>", 1)[1]
        
    # Map eval to 0..1
    clamped_eval = max(-5.0, min(5.0, eval_after_val))
    white_percentage = (clamped_eval + 5.0) / 10.0
    bar_height = 390
    white_pixels = int(bar_height * white_percentage)
    black_pixels = bar_height - white_pixels
    
    if GAME_STATE.player_color == chess.WHITE:
        white_y = black_pixels
        black_y = 0
        text_y = 380 if white_percentage > 0.5 else 20
    else:
        white_y = 0
        black_y = white_pixels
        text_y = 20 if white_percentage > 0.5 else 380

    eval_text = f"{eval_after_val:+.1f}" if mate_moves is None else f"M{abs(mate_moves)}"
    
    composite_svg = f"""<svg viewBox="0 0 420 390" width="420" height="390" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="{black_y}" width="20" height="{black_pixels}" fill="#404040"/>
    <rect x="0" y="{white_y}" width="20" height="{white_pixels}" fill="#f0f0f0"/>
    <text x="10" y="195" font-size="14" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="{'black' if white_percentage > 0.5 else 'white'}" transform="rotate(-90 10 195)">{eval_text}</text>
    <svg x="30" y="0" width="390" height="390">
        {original_svg}
    </svg>
</svg>"""

    img_filename = f"move_{GAME_STATE.current_ply + 1:03d}.png"
    img_rel_path = os.path.join("assets", img_filename)
    img_path = os.path.join(GAME_STATE.game_dir, img_rel_path)
    png_data = svg_to_png(composite_svg)
    with open(img_path, "wb") as f:
        f.write(bytes(png_data))
        
    move_info["image_path"] = img_rel_path
    
    GAME_STATE.current_ply += 1
    return json.dumps(move_info)

def append_to_report(markdown_content: str) -> str:
    """Appends your commentary and visuals for the current move to the report file.
    Use this after each move so you don't have to hold the entire report in your memory.
    """
    with open(GAME_STATE.report_filename, "a") as f:
        f.write(markdown_content + "\n\n")
    return f"Successfully appended to {GAME_STATE.report_filename}"
