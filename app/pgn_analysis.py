import chess
import chess.pgn
import io
import numpy as np
import math
from stockfish import Stockfish

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
stockfish = Stockfish(
    path="/usr/local/bin/stockfish",
    depth=18,
    parameters={
        "Threads": 4,
        "Hash": 512,
        "MultiPV": 1,  # Only need best move for speed
        "Skill Level": 20,
    },
)

_CACHE = {}

# ─────────────────────────────────────────────────────────────
# Core Evaluation Utilities
# ─────────────────────────────────────────────────────────────
def cp_to_winprob(cp: float) -> float:
    """Convert centipawns to win probability (Lichess model)"""
    return 100 / (1 + math.exp(-0.00368208 * cp))

def get_position_eval(board: chess.Board, player_is_white: bool) -> dict:
    """Get evaluation from player's perspective"""
    fen = board.fen()
    if fen in _CACHE:
        return _CACHE[fen]
    
    stockfish.set_fen_position(fen)
    eval_dict = stockfish.get_evaluation()
    
    # Parse evaluation
    if eval_dict["type"] == "mate":
        cp = 10000 if eval_dict["value"] > 0 else -10000
        is_mate = True
        mate_in = abs(eval_dict["value"])
    else:
        cp = eval_dict["value"]
        is_mate = False
        mate_in = None
    
    # Normalize to player perspective
    is_white_turn = board.turn == chess.WHITE
    if is_white_turn != player_is_white:
        cp = -cp
    
    # Get best move
    best_move = stockfish.get_best_move()
    
    result = {
        "cp": cp,
        "winprob": cp_to_winprob(cp),
        "best_move": best_move,
        "is_mate": is_mate,
        "mate_in": mate_in,
    }
    
    _CACHE[fen] = result
    return result

# ─────────────────────────────────────────────────────────────
# CRITICAL: Tactical Punishment Detection
# ─────────────────────────────────────────────────────────────
def detect_tactical_punishment(board_before: chess.Board, move_played: chess.Move, 
                               board_after: chess.Board, player_is_white: bool) -> dict:
    """
    Detect if the move allows OBVIOUS tactical punishment.
    This is the key to identifying "human-regrettable" moves.
    
    Returns:
        {
            "hanging_piece": bool,
            "mate_threat": int or None,  # Mate in N
            "forced_material_loss": bool,
            "eval_collapse": bool,  # Eval dropped >400cp
            "is_obvious": bool,  # Any of above
        }
    """
    punishment = {
        "hanging_piece": False,
        "mate_threat": None,
        "forced_material_loss": False,
        "eval_collapse": False,
        "is_obvious": False,
    }
    
    # Check if we hung a piece (undefended piece can be captured)
    player_pieces = board_after.pieces(chess.PAWN, player_is_white)
    for piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        player_pieces |= board_after.pieces(piece_type, player_is_white)
    
    for square in player_pieces:
        piece = board_after.piece_at(square)
        if piece and piece.color == (chess.WHITE if player_is_white else chess.BLACK):
            # Check if attacked and not defended
            attackers = board_after.attackers(not player_is_white, square)
            defenders = board_after.attackers(player_is_white, square)
            
            if attackers and not defenders:
                # Piece is hanging
                if piece.piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
                    punishment["hanging_piece"] = True
                    punishment["is_obvious"] = True
                    break
    
    # Check opponent's best response for mate threat
    stockfish.set_fen_position(board_after.fen())
    opponent_eval = stockfish.get_evaluation()
    
    if opponent_eval["type"] == "mate":
        mate_in = abs(opponent_eval["value"])
        if mate_in <= 5:  # Mate in 5 or less is obvious threat
            punishment["mate_threat"] = mate_in
            punishment["is_obvious"] = True
    
    # Check if opponent wins material by force (eval > +3)
    elif opponent_eval["value"] > 300:  # From opponent's perspective
        punishment["forced_material_loss"] = True
        punishment["is_obvious"] = True
    
    return punishment

# ─────────────────────────────────────────────────────────────
# CRITICAL: Blunder Classification Rules
# ─────────────────────────────────────────────────────────────
def classify_blunder(regret: float, punishment: dict, game_phase: str, 
                    pre_eval: float, post_eval: float) -> str | None:
    """
    CORE LOGIC: Classify move based on human regret psychology.
    
    Philosophy:
    - Blunder = You will kick yourself for this (obvious + severe)
    - Mistake = Clearly wrong, but not catastrophic
    - Inaccuracy = Imprecise, but understandable
    - None = Not worth mentioning
    
    Args:
        regret: Win probability lost (0-100)
        punishment: Tactical punishment dict
        game_phase: "opening" | "middlegame" | "endgame"
        pre_eval: Eval before move
        post_eval: Eval after move
    
    Returns:
        "blunder" | "mistake" | "inaccuracy" | None
    """
    
    # ═══════════════════════════════════════════════════════════
    # RULE 0: Suppress trivial regret (noise filter)
    # ═══════════════════════════════════════════════════════════
    if regret < 2.0:
        return None  # Not worth mentioning
    
    # ═══════════════════════════════════════════════════════════
    # RULE 1: Opening suppression (first 10 moves)
    # ═══════════════════════════════════════════════════════════
    if game_phase == "opening":
        # Opening has theory flexibility - be very lenient
        if regret < 8.0:
            return None  # Normal opening imprecision
        elif regret < 15.0:
            return "inaccuracy"  # Suboptimal opening choice
        elif punishment["is_obvious"]:
            return "blunder"  # Hanging piece in opening is still a blunder
        else:
            return "mistake"  # Serious opening error
    
    # ═══════════════════════════════════════════════════════════
    # RULE 2: BLUNDER detection (catastrophic + obvious)
    # ═══════════════════════════════════════════════════════════
    
    # 2A: Obvious tactical blunder (hanging piece, mate threat)
    if punishment["is_obvious"]:
        if punishment["hanging_piece"] or punishment["mate_threat"]:
            return "blunder"  # You hung something or allowed mate
    
    # 2B: Massive regret (>20% = catastrophic)
    if regret > 20.0:
        return "blunder"
    
    # 2C: Eval collapse (single move ruins position)
    eval_swing = pre_eval - post_eval
    if eval_swing > 400:  # Lost 4+ pawns equivalent
        return "blunder"
    
    # 2D: From winning to losing
    if pre_eval > 200 and post_eval < -100:  # +2 to -1
        return "blunder"
    
    # ═══════════════════════════════════════════════════════════
    # RULE 3: MISTAKE detection (clear error, not catastrophic)
    # ═══════════════════════════════════════════════════════════
    
    # 3A: Significant regret (7-20%)
    if 7.0 < regret <= 20.0:
        # Check if position meaningfully worsened
        if eval_swing > 150:  # Lost 1.5+ pawns
            return "mistake"
        # Or crossed from advantage to disadvantage
        if pre_eval > 50 and post_eval < -50:
            return "mistake"
    
    # 3B: Moderate regret with forced punishment
    if regret > 5.0 and punishment["forced_material_loss"]:
        return "mistake"
    
    # ═══════════════════════════════════════════════════════════
    # RULE 4: INACCURACY detection (imprecise but not terrible)
    # ═══════════════════════════════════════════════════════════
    
    # 4A: Small-medium regret (3-7%)
    if 3.0 < regret <= 7.0:
        return "inaccuracy"
    
    # ═══════════════════════════════════════════════════════════
    # DEFAULT: Not a problem
    # ═══════════════════════════════════════════════════════════
    return None

# ─────────────────────────────────────────────────────────────
# Game Phase Detection
# ─────────────────────────────────────────────────────────────
def detect_game_phase(move_number: int, board: chess.Board) -> str:
    """Determine game phase for context-sensitive classification"""
    if move_number <= 10:
        return "opening"
    
    # Count pieces (excluding kings and pawns)
    pieces = 0
    for piece_type in [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]:
        pieces += len(board.pieces(piece_type, chess.WHITE))
        pieces += len(board.pieces(piece_type, chess.BLACK))
    
    if pieces <= 6:  # Few pieces left
        return "endgame"
    
    return "middlegame"

# ─────────────────────────────────────────────────────────────
# Continuation Line (for validation)
# ─────────────────────────────────────────────────────────────
def get_punishment_line(board: chess.Board, depth: int = 3) -> str:
    """Get opponent's best punishment sequence"""
    temp_board = board.copy()
    line = []
    
    for _ in range(depth):
        stockfish.set_fen_position(temp_board.fen())
        best_move = stockfish.get_best_move()
        if not best_move:
            break
        
        try:
            move = chess.Move.from_uci(best_move)
            line.append(temp_board.san(move))
            temp_board.push(move)
        except:
            break
    
    return " ".join(line) if line else None

# ─────────────────────────────────────────────────────────────
# MAIN ANALYSIS
# ─────────────────────────────────────────────────────────────
def analyze_pgn(pgn: str, username: str):
    """
    Analyze PGN and return only GENUINE HUMAN BLUNDERS.
    
    Philosophy: Only flag moves that a human will genuinely regret
    when reviewing the game. Ignore engine quibbles and opening theory.
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    if not game:
        raise ValueError("Invalid PGN")
    
    headers = game.headers
    user = username.strip().lower()
    white = headers.get("White", "").lower()
    black = headers.get("Black", "").lower()
    
    if white == user:
        player_is_white = True
    elif black == user:
        player_is_white = False
    else:
        raise ValueError("User not in game")
    
    board = game.board()
    problems = []
    
    blunders = 0
    mistakes = 0
    inaccuracies = 0
    
    for ply, move in enumerate(game.mainline_moves()):
        # Only analyze player moves
        is_player_move = (ply % 2 == 0 and player_is_white) or (ply % 2 == 1 and not player_is_white)
        
        if not is_player_move:
            board.push(move)
            continue
        
        move_num = ply // 2 + 1
        game_phase = detect_game_phase(move_num, board)
        
        # ══════════════════════════════════════════════════════
        # BEFORE move: What was best available?
        # ══════════════════════════════════════════════════════
        pre_eval = get_position_eval(board, player_is_white)
        pre_board = board.copy()
        
        # ══════════════════════════════════════════════════════
        # CRITICAL CHECK: Did you play the best move?
        # ══════════════════════════════════════════════════════
        if move.uci() == pre_eval["best_move"]:
            board.push(move)
            continue  # Perfect move - not a problem!
        
        # ══════════════════════════════════════════════════════
        # AFTER move: What did you get?
        # ══════════════════════════════════════════════════════
        board.push(move)
        post_eval = get_position_eval(board, player_is_white)
        
        # ══════════════════════════════════════════════════════
        # Calculate regret (human psychology metric)
        # ══════════════════════════════════════════════════════
        regret = pre_eval["winprob"] - post_eval["winprob"]
        
        # ══════════════════════════════════════════════════════
        # Detect tactical punishment (obviousness)
        # ══════════════════════════════════════════════════════
        punishment = detect_tactical_punishment(
            pre_board, move, board, player_is_white
        )
        
        # ══════════════════════════════════════════════════════
        # CLASSIFY using multi-dimensional rules
        # ══════════════════════════════════════════════════════
        classification = classify_blunder(
            regret=regret,
            punishment=punishment,
            game_phase=game_phase,
            pre_eval=pre_eval["cp"],
            post_eval=post_eval["cp"]
        )
        
        # ══════════════════════════════════════════════════════
        # If not a problem, skip
        # ══════════════════════════════════════════════════════
        if classification is None:
            continue
        
        # ══════════════════════════════════════════════════════
        # Record the problem
        # ══════════════════════════════════════════════════════
        
        # Count by severity
        if classification == "blunder":
            blunders += 1
        elif classification == "mistake":
            mistakes += 1
        elif classification == "inaccuracy":
            inaccuracies += 1
        
        # Get punishment line for context
        punishment_line = None
        if classification in ["blunder", "mistake"]:
            punishment_line = get_punishment_line(board, depth=4)
        
        # Format evaluations
        def format_eval(cp, is_mate, mate_in):
            if is_mate:
                sign = "" if cp > 0 else "-"
                return f"{sign}#{mate_in}"
            sign = "+" if cp >= 0 else "-"
            return f"{sign}{abs(cp)/100:.2f}"
        
        # Build SAN notation for moves
        played_san = pre_board.san(move)
        best_move_obj = chess.Move.from_uci(pre_eval["best_move"])
        best_san = pre_board.san(best_move_obj)
        
        problems.append({
            "move_number": move_num,
            "played": played_san,
            "best_move": best_san,
            
            # Classification
            "severity": classification,
            "regret": round(regret, 1),
            
            # Evaluations
            "eval_before": format_eval(pre_eval["cp"], pre_eval["is_mate"], pre_eval["mate_in"]),
            "eval_after": format_eval(post_eval["cp"], post_eval["is_mate"], post_eval["mate_in"]),
            
            # Tactical context
            "hanging_piece": punishment["hanging_piece"],
            "mate_threat": punishment["mate_threat"],
            "forced_loss": punishment["forced_material_loss"],
            
            # Validation
            "punishment_line": punishment_line,
            
            # Context
            "game_phase": game_phase,
        })
    
    player = headers.get("White") if player_is_white else headers.get("Black")
    opponent = headers.get("Black") if player_is_white else headers.get("White")
    
    return {
    
        "game_link": headers.get("Site", "").split("?")[0] if headers.get("Site") else None,
        "player": player,
        "game_mode": headers.get("TimeControl", "unknown"),
        "opponent": opponent,
        "player_color": "white" if player_is_white else "black",
        
        # Summary
        "total_problems": len(problems),
        "blunders": blunders,
        "mistakes": mistakes,
        "inaccuracies": inaccuracies,
        "pushups": blunders * 10,  # Only blunders count for punishment!
        
        # Detailed problems
        "problems": problems,
    }