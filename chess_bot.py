import chess
import sys
import math
import random
import time

class SearchTimeout(Exception):
    pass

# --- MEMORY GLOBALS ---
TRANSPOSITION_TABLE = {}
KILLER_MOVES = {} # Short-term memory for brilliant quiet moves!
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2

# --- PSTs (A1 = Index 0) ---
PAWN_PST = [
    0,   0,   0,   0,   0,   0,   0,   0,
    5,  10,  10, -20, -20,  10,  10,   5,
    5,  -5, -10,   0,   0, -10,  -5,   5,
   10,  10,  20,  30,  30,  20,  10,  10,
   30,  30,  50,  70,  70,  50,  30,  30,
   80,  80, 120, 150, 150, 120,  80,  80, 
  600, 600, 600, 600, 600, 600, 600, 600, 
    0,   0,   0,   0,   0,   0,   0,   0
]
KNIGHT_PST = [
   -50,-40,-30,-30,-30,-30,-40,-50,
   -40,-20,  0,  0,  0,  0,-20,-40,
   -30,  0, 10, 15, 15, 10,  0,-30,
   -30,  5, 15, 20, 20, 15,  5,-30,
   -30,  0, 15, 20, 20, 15,  0,-30,
   -30,  5, 10, 15, 15, 10,  5,-30,
   -40,-20,  0,  5,  5,  0,-20,-40,
   -50,-40,-30,-30,-30,-30,-40,-50
]
BISHOP_PST = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]
ROOK_PST = [
     0,  0,  5, 10, 10,  5,  0,  0,
    -5,  0,  5, 10, 10,  5,  0, -5,
    -5,  0,  5, 10, 10,  5,  0, -5,
    -5,  0,  5, 10, 10,  5,  0, -5,
    -5,  0,  5, 10, 10,  5,  0, -5,
    -5,  0,  5, 10, 10,  5,  0, -5,
    30, 30, 30, 30, 30, 30, 30, 30,
     0,  0,  0,  0,  0,  0,  0,  0
]
QUEEN_PST = [
   -20,-10,-10, -5, -5,-10,-10,-20,
   -10,  0,  5,  0,  0,  0,  0,-10,
   -10,  5,  5,  5,  5,  5,  0,-10,
     0,  0,  5,  5,  5,  5,  0, -5,
    -5,  0,  5,  5,  5,  5,  0, -5,
   -10,  0,  5,  5,  5,  5,  0,-10,
   -10,  0,  0,  0,  0,  0,  0,-10,
   -20,-10,-10, -5, -5,-10,-10,-20
]
KING_MG_PST = [
    20, 30, 10,  0,  0, 10, 30, 20, 
    20, 20,  0,  0,  0,  0, 20, 20, 
   -10,-20,-20,-20,-20,-20,-20,-10, 
   -20,-30,-30,-40,-40,-30,-30,-20, 
   -30,-40,-40,-50,-50,-40,-40,-30, 
   -30,-40,-40,-50,-50,-40,-40,-30, 
   -30,-40,-40,-50,-50,-40,-40,-30, 
   -30,-40,-40,-50,-50,-40,-40,-30  
]
KING_EG_PST = [
   -50,-40,-30,-20,-20,-30,-40,-50,
   -30,-20,-10,  0,  0,-10,-20,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 30, 40, 40, 30,-10,-30,
   -30,-10, 20, 30, 30, 20,-10,-30,
   -30,-30,  0,  0,  0,  0,-30,-30,
   -50,-30,-30,-30,-30,-30,-30,-50
]

def evaluate_board(board):
    PAWN = 100
    KNIGHT = 320
    BISHOP = 330
    ROOK = 500
    QUEEN = 900
    KING = 20000

    score = 0
    piece_map = board.piece_map()

    # --- TAPERED EVALUATION (Smooth Blending) ---
    knights = len(board.pieces(chess.KNIGHT, chess.WHITE)) + len(board.pieces(chess.KNIGHT, chess.BLACK))
    bishops = len(board.pieces(chess.BISHOP, chess.WHITE)) + len(board.pieces(chess.BISHOP, chess.BLACK))
    rooks = len(board.pieces(chess.ROOK, chess.WHITE)) + len(board.pieces(chess.ROOK, chess.BLACK))
    queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
    
    phase_score = (knights * 1) + (bishops * 1) + (rooks * 2) + (queens * 4)
    phase = min(phase_score / 24.0, 1.0) # 1.0 = Opening, 0.0 = Empty Endgame
    # --------------------------------------------

    # 1. Base Material & PSTs
    for square, piece in piece_map.items():
        sign = 1 if piece.color == chess.WHITE else -1
        s = square if piece.color == chess.WHITE else chess.square_mirror(square)
        
        if piece.piece_type == chess.PAWN:
            pawn_score = PAWN_PST[s]
            # Smoothly double the pawn's positional value as pieces disappear
            pawn_score += pawn_score * (1.0 - phase) 
            score += sign * (PAWN + pawn_score)
        elif piece.piece_type == chess.KNIGHT:
            score += sign * (KNIGHT + KNIGHT_PST[s])
        elif piece.piece_type == chess.BISHOP:
            score += sign * (BISHOP + BISHOP_PST[s])
        elif piece.piece_type == chess.ROOK:
            score += sign * (ROOK + ROOK_PST[s])
        elif piece.piece_type == chess.QUEEN:
            score += sign * (QUEEN + QUEEN_PST[s])
        elif piece.piece_type == chess.KING:
            # Smoothly blend the Middle-Game and Endgame King tables
            mg_king = KING_MG_PST[s] * phase
            eg_king = KING_EG_PST[s] * (1.0 - phase)
            score += sign * (KING + mg_king + eg_king)

    # 2. Pawn Structure & Castling Awareness
    for f in range(8):
        w_pawns = sum(1 for r in range(8) if board.piece_at(chess.square(f, r)) == chess.Piece(chess.PAWN, chess.WHITE))
        b_pawns = sum(1 for r in range(8) if board.piece_at(chess.square(f, r)) == chess.Piece(chess.PAWN, chess.BLACK))
        if w_pawns > 1: score -= 30 # Penalize White doubled pawns
        if b_pawns > 1: score += 30 # Penalize Black doubled pawns
        
    if board.king(chess.WHITE) in [chess.G1, chess.C1, chess.B1]: score += 40
    if board.king(chess.BLACK) in [chess.G8, chess.C8, chess.B8]: score -= 40

    # 3. Center Control (Early Game)
    if phase > 0.5:
        center_squares = [chess.D4, chess.E4, chess.D5, chess.E5]
        white_center = sum(1 for sq in center_squares if board.color_at(sq) == chess.WHITE)
        black_center = sum(1 for sq in center_squares if board.color_at(sq) == chess.BLACK)
        score += (white_center - black_center) * 15  

    # 4. Anti-Sniper Tactics (King Safety)
    white_king_sq = board.king(chess.WHITE)
    black_king_sq = board.king(chess.BLACK)
    
    if white_king_sq:
        wk_file = chess.square_file(white_king_sq)
        wk_rank = chess.square_rank(white_king_sq)
        for sq in list(board.pieces(chess.ROOK, chess.BLACK)) + list(board.pieces(chess.QUEEN, chess.BLACK)):
            if chess.square_file(sq) == wk_file or chess.square_rank(sq) == wk_rank:
                score -= 60 
                
    if black_king_sq:
        bk_file = chess.square_file(black_king_sq)
        bk_rank = chess.square_rank(black_king_sq)
        for sq in list(board.pieces(chess.ROOK, chess.WHITE)) + list(board.pieces(chess.QUEEN, chess.WHITE)):
            if chess.square_file(sq) == bk_file or chess.square_rank(sq) == bk_rank:
                score += 60 
                
    return score

def score_move(board, move, tt_best_move=None, depth=0):
    if move == tt_best_move:
        return 9999999 
        
    score = 0
    
    if len(board.move_stack) > 0:
        last_move = board.peek()
        if move.to_square == last_move.to_square and board.is_capture(move):
            score += 50000 
    
    if board.is_capture(move):
        captured_piece = board.piece_at(move.to_square)
        moving_piece = board.piece_at(move.from_square)
        cap_val = captured_piece.piece_type if captured_piece else chess.PAWN
        mov_val = moving_piece.piece_type if moving_piece else chess.PAWN
        score += 10000 + (cap_val * 100) - mov_val
        
    elif depth in KILLER_MOVES and move == KILLER_MOVES[depth]:
        # THE KILLER HEURISTIC! Prioritize this brilliant quiet move!
        score += 9000 
        
    if move.promotion: score += 8000
    if board.gives_check(move): score += 5000
    return score

def get_ordered_moves(board, only_tactical=False, tt_best_move=None, depth=0):
    moves = list(board.legal_moves)
    if only_tactical: 
        moves = [m for m in moves if board.is_capture(m) or m.promotion]
    return sorted(moves, key=lambda m: score_move(board, m, tt_best_move, depth), reverse=True)

def quiescence_search(board, alpha, beta, maximizing_player, q_depth=0):
    in_check = board.is_check()
    stand_pat = evaluate_board(board)
    if q_depth >= 4: return stand_pat

    if maximizing_player:
        if not in_check:
            if stand_pat >= beta: return beta
            if alpha < stand_pat: alpha = stand_pat
        moves = get_ordered_moves(board, only_tactical=not in_check)
        if not moves and in_check: return -99999 
            
        for move in moves:
            board.push(move)
            score = quiescence_search(board, alpha, beta, False, q_depth + 1)
            board.pop()
            if score >= beta: return beta
            if score > alpha: alpha = score
        return alpha
    else:
        if not in_check:
            if stand_pat <= alpha: return alpha
            if beta > stand_pat: beta = stand_pat
        moves = get_ordered_moves(board, only_tactical=not in_check)
        if not moves and in_check: return 99999 
            
        for move in moves:
            board.push(move)
            score = quiescence_search(board, alpha, beta, True, q_depth + 1)
            board.pop()
            if score <= alpha: return alpha
            if score < beta: beta = score
        return beta

def minimax(board, depth, alpha, beta, maximizing_player, start_time, allow_null=True):
    if time.time() - start_time > 15.0:
        raise SearchTimeout() 

    if board.is_checkmate():
        return (-99999 if board.turn == chess.WHITE else 99999), None
    if board.is_stalemate() or board.is_insufficient_material() or board.can_claim_draw():
        return 0, None 

    board_hash = board.fen()
    tt_best_move = None
    if board_hash in TRANSPOSITION_TABLE:
        entry = TRANSPOSITION_TABLE[board_hash]
        tt_best_move = entry['best_move']
        if entry['depth'] >= depth:
            if entry['flag'] == EXACT: return entry['value'], tt_best_move
            elif entry['flag'] == LOWERBOUND: alpha = max(alpha, entry['value'])
            elif entry['flag'] == UPPERBOUND: beta = min(beta, entry['value'])
            if alpha >= beta: return entry['value'], tt_best_move

    if depth == 0:
        return quiescence_search(board, alpha, beta, maximizing_player), None

    is_endgame = len(board.piece_map()) <= 10
    in_check = board.is_check()
    
    if allow_null and depth >= 3 and not in_check and not is_endgame:
        board.push(chess.Move.null())
        if maximizing_player:
            eval, _ = minimax(board, depth - 3, alpha, beta, False, start_time, allow_null=False)
            board.pop()
            if eval >= beta: return beta, None
        else:
            eval, _ = minimax(board, depth - 3, alpha, beta, True, start_time, allow_null=False)
            board.pop()
            if eval <= alpha: return alpha, None

    ordered_moves = get_ordered_moves(board, tt_best_move=tt_best_move, depth=depth)
    best_move = None
    original_alpha = alpha

    if maximizing_player:
        max_eval = -math.inf
        for move in ordered_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, False, start_time, allow_null=True)
            board.pop()
            if eval > max_eval:
                max_eval = eval
                best_move = move
            alpha = max(alpha, eval)
            if beta <= alpha: 
                # Save the Killer Move!
                if not board.is_capture(move): KILLER_MOVES[depth] = move
                break 
        
        flag = EXACT
        if max_eval <= original_alpha: flag = UPPERBOUND
        elif max_eval >= beta: flag = LOWERBOUND
        TRANSPOSITION_TABLE[board_hash] = {'depth': depth, 'flag': flag, 'value': max_eval, 'best_move': best_move}
        return max_eval, best_move
        
    else:
        min_eval = math.inf
        for move in ordered_moves:
            board.push(move)
            eval, _ = minimax(board, depth - 1, alpha, beta, True, start_time, allow_null=True)
            board.pop()
            if eval < min_eval:
                min_eval = eval
                best_move = move
            beta = min(beta, eval)
            if beta <= alpha: 
                # Save the Killer Move!
                if not board.is_capture(move): KILLER_MOVES[depth] = move
                break 
            
        flag = EXACT
        if min_eval <= original_alpha: flag = UPPERBOUND
        elif min_eval >= beta: flag = LOWERBOUND
        TRANSPOSITION_TABLE[board_hash] = {'depth': depth, 'flag': flag, 'value': min_eval, 'best_move': best_move}
        return min_eval, best_move

def uci_loop():
    board = chess.Board()
    global KILLER_MOVES
    
    while True:
        try: line = input()
        except EOFError: break
        if not line: continue
        line = line.strip()

        if line == "uci":
            print("id name Run_Bot_God_Mode")
            print("id author Cursor")
            print("uciok")
        elif line == "isready": print("readyok")
        elif line.startswith("position"):
            tokens = line.split()
            if "startpos" in tokens: board.set_fen(chess.STARTING_FEN)
            else:
                fen_idx = tokens.index("fen") + 1 if "fen" in tokens else 1
                board.set_fen(" ".join(tokens[fen_idx:fen_idx+6]))
            if "moves" in tokens:
                for move_uci in tokens[tokens.index("moves") + 1:]:
                    move = chess.Move.from_uci(move_uci)
                    if move in board.legal_moves: board.push(move)
                    else: break
        elif line.startswith("go"):
            if len(TRANSPOSITION_TABLE) > 1000000:
                TRANSPOSITION_TABLE.clear() 
            KILLER_MOVES.clear() # Clear memory for the new search!

            if board.fullmove_number == 1:
                book_moves = ["e2e4"] if board.turn == chess.WHITE else ["e7e5", "c7c5", "d7d5", "g8f6"]
                valid = [chess.Move.from_uci(m) for m in book_moves if chess.Move.from_uci(m) in board.legal_moves]
                best_move = random.choice(valid) if valid else random.choice(list(board.legal_moves))
                print(f"bestmove {best_move.uci()}")
                continue 

            legal_moves = list(board.legal_moves)
            if len(legal_moves) == 1:
                print(f"bestmove {legal_moves[0].uci()}")
                continue 

            start_time = time.time()
            best_move_overall = None
            best_score_overall = 0
            MAX_DEPTH = 10 
            
            if board.fullmove_number <= 5:
                TIME_LIMIT = 4.0   
            else:
                TIME_LIMIT = 14.8  

            for current_depth in range(1, MAX_DEPTH + 1):
                depth_start = time.time() 
                try:
                    score, move = minimax(board, current_depth, -math.inf, math.inf, board.turn, start_time, allow_null=True)
                    if move is not None:
                        best_move_overall = move
                        best_score_overall = score
                        
                    print(f"info depth {current_depth} score cp {int(best_score_overall)}")
                    
                    depth_duration = time.time() - depth_start
                    time_used = time.time() - start_time
                    estimated_next_depth_time = depth_duration * 5
                    
                    if time_used + estimated_next_depth_time > TIME_LIMIT:
                        break 
                except SearchTimeout:
                    break 

            if best_move_overall is None:
                fallback_moves = list(board.legal_moves)
                if fallback_moves:
                    best_move_overall = fallback_moves[0]

            print(f"bestmove {best_move_overall.uci()}" if best_move_overall else "bestmove 0000") 
        elif line == "quit": break

if __name__ == '__main__':
    uci_loop()