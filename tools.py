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
import concurrent.futures

def fetch_commentary(task):
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=task['prompt'],
        )
        return task['index'], response.text.strip()
    except Exception as e:
        return task['index'], f"Error getting deep commentary: {str(e)}"

def generate_game_report(username: str, game_index: int = 0) -> str:
    """Fetches a game, evaluates all moves, generates images, and writes a full markdown report to disk.
    This is extremely fast because it processes deep LLM commentary in parallel.
    Call this once per game.
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
    
    valid_games = []
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
    report_filename = os.path.join(game_dir, f"report_{username}_{game_index}.md")
    
    metadata = {
        "White": game.headers.get('White', '?'),
        "Black": game.headers.get('Black', '?'),
        "Result": game.headers.get('Result', '?'),
        "Date": game.headers.get('Date', '?'),
        "Opening": game.headers.get('ECOUrl', '').split('/')[-1].replace('-', ' ') if game.headers.get('ECOUrl') else 'Unknown'
    }
    
    player_color = chess.WHITE if metadata["White"].lower() == username.lower() else chess.BLACK
    board = game.board()
    moves = list(game.mainline_moves())
    
    engine_path = "./stockfish"
    engine = None
    if os.path.exists(engine_path):
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    else:
        return json.dumps({"error": "Stockfish engine not found at ./stockfish"})

    analyzed_moves = []
    commentary_tasks = []

    print(f"Starting sequential engine analysis for {len(moves)} moves...")
    
    for i, move in enumerate(moves):
        move_number = (i // 2) + 1
        color_moved_str = "White" if i % 2 == 0 else "Black"
        color_moved = chess.WHITE if i % 2 == 0 else chess.BLACK
        
        eval_before_val = 0.0
        best_move_san = None
        
        # Eval Before
        try:
            info = engine.analyse(board, chess.engine.Limit(time=0.1))
            score_w = info["score"].white()
            eval_before_val = score_w.score() / 100.0 if score_w.score() is not None else (100.0 if score_w.mate() > 0 else -100.0)
            best_move = info.get("pv", [None])[0]
            if best_move:
                best_move_san = board.san(best_move)
        except Exception:
            pass

        actual_move_san = board.san(move)
        board.push(move)
        
        # Eval After
        eval_after_val = 0.0
        mate_moves = None
        try:
            info_after = engine.analyse(board, chess.engine.Limit(time=0.1))
            score_w = info_after["score"].white()
            mate_moves = score_w.mate()
            eval_after_val = score_w.score() / 100.0 if score_w.score() is not None else (100.0 if score_w.mate() > 0 else -100.0)
        except Exception:
            pass

        # Delta & Label
        delta = eval_after_val - eval_before_val if color_moved == chess.WHITE else eval_before_val - eval_after_val
        
        label = "Good 👍"
        label_plain = "Good"
        if delta <= -3.0:
            label = "Blunder ❌"
            label_plain = "Blunder"
        elif delta <= -1.0:
            label = "Mistake ❓"
            label_plain = "Mistake"
        elif delta <= -0.5:
            label = "Inaccuracy ⁈"
            label_plain = "Inaccuracy"
        elif actual_move_san == best_move_san:
            label = "Best Move ✅"
            label_plain = "Best Move"
        elif delta >= 1.5 and -2.0 < eval_before_val < 2.0:
            label = "Brilliant ‼️"
            label_plain = "Brilliant"

        # Generate SVG
        original_svg = str(chess.svg.board(board, orientation=player_color, lastmove=move))
        if original_svg.startswith("<?xml"):
            original_svg = original_svg.split("?>", 1)[1]
            
        clamped_eval = max(-5.0, min(5.0, eval_after_val))
        white_percentage = (clamped_eval + 5.0) / 10.0
        bar_height = 390
        white_pixels = int(bar_height * white_percentage)
        black_pixels = bar_height - white_pixels
        
        if player_color == chess.WHITE:
            white_y, black_y = black_pixels, 0
        else:
            white_y, black_y = 0, white_pixels

        eval_text = f"{eval_after_val:+.1f}" if mate_moves is None else f"M{abs(mate_moves)}"
        text_color = 'black' if white_percentage > 0.5 else 'white'
        
        composite_svg = f'''<svg viewBox="0 0 420 390" width="420" height="390" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="{black_y}" width="20" height="{black_pixels}" fill="#404040"/>
            <rect x="0" y="{white_y}" width="20" height="{white_pixels}" fill="#f0f0f0"/>
            <text x="10" y="195" font-size="14" text-anchor="middle" font-family="sans-serif" font-weight="bold" fill="{text_color}" transform="rotate(-90 10 195)">{eval_text}</text>
            <svg x="30" y="0" width="390" height="390">
                {original_svg}
            </svg>
        </svg>'''

        img_filename = f"move_{i + 1:03d}.png"
        img_rel_path = os.path.join("assets", img_filename)
        img_path = os.path.join(game_dir, img_rel_path)
        with open(img_path, "wb") as f:
            f.write(bytes(svg_to_png(composite_svg)))

        move_data = {
            "move_number": move_number,
            "color": color_moved_str,
            "actual_move_san": actual_move_san,
            "best_move_san": best_move_san,
            "label": label,
            "eval_before": eval_before_val,
            "eval_after": eval_after_val,
            "img_rel_path": img_rel_path,
            "deep_commentary": None
        }

        if label_plain in ["Blunder", "Mistake", "Brilliant", "Great"]:
            prompt = f"""You are an expert Chess Grandmaster. 
The player ({color_moved_str}) just played {actual_move_san}.
This move was evaluated as a {label_plain}.
Evaluation went from {eval_before_val:.2f} to {eval_after_val:.2f}.
The engine's recommended best move was {best_move_san}.
Here is the current FEN: {board.fen()}
Provide a short, deeply insightful 2-3 sentence commentary on WHY this move was a {label_plain}, focusing on the tactical or positional consequences. Do NOT just repeat the evaluation numbers, explain the chess ideas."""
            commentary_tasks.append({
                "index": i,
                "prompt": prompt
            })

        analyzed_moves.append(move_data)

    engine.quit()

    # Parallel processing of commentary tasks
    print(f"Fetching deep commentary for {len(commentary_tasks)} moves in parallel (max 8 workers)...")
    if commentary_tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_task = {executor.submit(fetch_commentary, task): task for task in commentary_tasks}
            for future in concurrent.futures.as_completed(future_to_task):
                idx, commentary = future.result()
                analyzed_moves[idx]["deep_commentary"] = commentary

    # Build Markdown Report
    print("Building report...")
    md_lines = [
        f"# Chess Game Analysis: {metadata['White']} vs {metadata['Black']}\n",
        f"- **Result:** {metadata['Result']}",
        f"- **Date:** {metadata['Date']}",
        f"- **Opening:** {metadata['Opening']}\n"
    ]

    for data in analyzed_moves:
        md_lines.append(f"### Move {data['move_number']} ({data['color']}): {data['actual_move_san']} - {data['label']}")
        md_lines.append(f'<p align="center"><img src="{data["img_rel_path"]}" alt="Board" width="400"></p>')
        
        if data['deep_commentary']:
            md_lines.append(data['deep_commentary'] + "\n")
        else:
            rec = f" The engine recommended **{data['best_move_san']}**." if data['best_move_san'] and data['actual_move_san'] != data['best_move_san'] else ""
            md_lines.append(f"Played **{data['actual_move_san']}**.{rec}\n")
        md_lines.append("\n")

    with open(report_filename, "w") as f:
        f.write("\n".join(md_lines))

    return json.dumps({
        "status": "success",
        "message": f"Successfully analyzed {len(moves)} moves and generated report.",
        "report_path": report_filename,
        "blunders": len([m for m in analyzed_moves if 'Blunder' in m['label']]),
        "mistakes": len([m for m in analyzed_moves if 'Mistake' in m['label']]),
        "brilliants": len([m for m in analyzed_moves if 'Brilliant' in m['label']])
    })
