import json
import os
import sys
import urllib.request
import urllib.error

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

PIECE_VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 20000}

# Piece-Square Tables (8x8 from rank 8 to rank 1)
PST = {
    "P": (
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5,  5, 10, 25, 25, 10,  5,  5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5, -5,-10,  0,  0,-10, -5,  5,
        5, 10, 10,-20,-20, 10, 10,  5,
        0,  0,  0,  0,  0,  0,  0,  0
    ),
    "N": (
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  0,  0,  0,-20,-40,
        -30,  0, 10, 15, 15, 10,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  0, 15, 20, 20, 15,  0,-30,
        -30,  5, 10, 15, 15, 10,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ),
    "B": (
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5, 10, 10,  5,  0,-10,
        -10,  5,  5, 10, 10,  5,  5,-10,
        -10,  0, 10, 10, 10, 10,  0,-10,
        -10, 10, 10, 10, 10, 10, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ),
    "R": (
        0,  0,  0,  0,  0,  0,  0,  0,
        5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        0,  0,  0,  5,  5,  0,  0,  0
    ),
    "Q": (
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  0,  0,  0,  0,  0,-10,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -5,  0,  5,  5,  5,  5,  0, -5,
        0,  0,  5,  5,  5,  5,  0, -5,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -20,-10,-10, -5, -5,-10,-10,-20
    ),
    "K": (
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -30,-40,-40,-50,-50,-40,-40,-30,
        -20,-30,-30,-40,-40,-30,-30,-20,
        -10,-20,-20,-20,-20,-20,-20,-10,
        20, 20,  0,  0,  0,  0, 20, 20,
        20, 30, 10,  0,  0, 10, 30, 20
    )
}

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(ENV_URL + path, data=data, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{path}: HTTP {e.code} {e.read().decode(errors='replace')}")

def parse_fen(fen):
    parts = fen.split()
    rows = parts[0].split('/')
    board = {}
    for r, row in enumerate(rows):
        c = 0
        for ch in row:
            if ch.isdigit():
                c += int(ch)
            else:
                sq = "abcdefgh"[c] + str(8 - r)
                board[sq] = ch
                c += 1
    white_to_move = (parts[1] == 'w')
    return board, white_to_move

def sq_to_idx(sq):
    col = ord(sq[0]) - ord('a')
    row = 8 - int(sq[1])
    return row * 8 + col

def evaluate_board(board, white_to_move):
    score = 0
    for sq, p in board.items():
        val = PIECE_VAL.get(p.upper(), 0)
        idx = sq_to_idx(sq)
        pst_val = 0
        if p.upper() in PST:
            if p.isupper():
                pst_val = PST[p][idx]
            else:
                # Mirror for black
                r = idx // 8
                c = idx % 8
                mirror_idx = (7 - r) * 8 + c
                pst_val = PST[p.upper()][mirror_idx]
        total = val + pst_val
        if p.isupper():
            score += total
        else:
            score -= total
    return score if white_to_move else -score

def apply_move(board, move):
    nb = dict(board)
    src = move[:2]
    dst = move[2:4]
    piece = nb.pop(src, None)
    if not piece:
        return nb
    # Handle promotion
    if len(move) == 5:
        promo = move[4]
        piece = promo.upper() if piece.isupper() else promo.lower()
    # Handle en-passant capture
    if piece.upper() == 'P' and src[0] != dst[0] and dst not in nb:
        ep_sq = dst[0] + src[1]
        nb.pop(ep_sq, None)
    # Handle castling move of rook
    if piece.upper() == 'K':
        if src == 'e1' and dst == 'g1':
            r = nb.pop('h1', None)
            if r: nb['f1'] = r
        elif src == 'e1' and dst == 'c1':
            r = nb.pop('a1', None)
            if r: nb['d1'] = r
        elif src == 'e8' and dst == 'g8':
            r = nb.pop('h8', None)
            if r: nb['f8'] = r
        elif src == 'e8' and dst == 'c8':
            r = nb.pop('a8', None)
            if r: nb['d8'] = r
    nb[dst] = piece
    return nb

def generate_pseudo_legal_captures(board, white_to_move):
    """Find capture moves for quiescence search."""
    moves = []
    for sq, p in board.items():
        if (p.isupper() and white_to_move) or (p.islower() and not white_to_move):
            c = ord(sq[0]) - ord('a')
            r = int(sq[1])
            pt = p.upper()
            if pt == 'P':
                dr = 1 if white_to_move else -1
                for dc in (-1, 1):
                    nc, nr = c + dc, r + dr
                    if 0 <= nc <= 7 and 1 <= nr <= 8:
                        tsq = chr(ord('a') + nc) + str(nr)
                        target = board.get(tsq)
                        if target and (target.isupper() != white_to_move):
                            moves.append(sq + tsq)
            elif pt in ('N', 'K'):
                deltas = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)] if pt == 'N' else [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
                for dc, dr in deltas:
                    nc, nr = c + dc, r + dr
                    if 0 <= nc <= 7 and 1 <= nr <= 8:
                        tsq = chr(ord('a') + nc) + str(nr)
                        target = board.get(tsq)
                        if target and (target.isupper() != white_to_move):
                            moves.append(sq + tsq)
            elif pt in ('B', 'R', 'Q'):
                dirs = []
                if pt in ('B', 'Q'): dirs.extend([(-1,-1),(-1,1),(1,-1),(1,1)])
                if pt in ('R', 'Q'): dirs.extend([(-1,0),(1,0),(0,-1),(0,1)])
                for dc, dr in dirs:
                    nc, nr = c + dc, r + dr
                    while 0 <= nc <= 7 and 1 <= nr <= 8:
                        tsq = chr(ord('a') + nc) + str(nr)
                        target = board.get(tsq)
                        if target:
                            if target.isupper() != white_to_move:
                                moves.append(sq + tsq)
                            break
                        nc += dc
                        nr += dr
    return moves

def quiesce(board, alpha, beta, white_to_move, depth=2):
    stand_pat = evaluate_board(board, white_to_move)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
    if depth <= 0:
        return alpha

    captures = generate_pseudo_legal_captures(board, white_to_move)
    def mvv_lva(m):
        victim = board.get(m[2:4], 'P').upper()
        attacker = board.get(m[:2], 'P').upper()
        return PIECE_VAL.get(victim, 0) - PIECE_VAL.get(attacker, 0) // 10
    captures.sort(key=mvv_lva, reverse=True)

    for m in captures:
        nb = apply_move(board, m)
        score = -quiesce(nb, -beta, -alpha, not white_to_move, depth - 1)
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

def choose_move(fen, legal_moves):
    if not legal_moves:
        return None
    if len(legal_moves) == 1:
        return legal_moves[0]

    board, white_to_move = parse_fen(fen)

    def move_priority(m):
        dst = m[2:4]
        target = board.get(dst)
        src_piece = board.get(m[:2], 'P').upper()
        if target:
            # MVV-LVA
            return 1000 + PIECE_VAL.get(target.upper(), 0) - PIECE_VAL.get(src_piece, 0)
        # Center control bonus
        if dst in ('e4', 'd4', 'e5', 'd5'):
            return 50
        if dst in ('c4', 'f4', 'c5', 'f5'):
            return 20
        return 0

    sorted_moves = sorted(legal_moves, key=move_priority, reverse=True)

    best_move = sorted_moves[0]
    best_score = -999999
    alpha = -999999
    beta = 999999

    for m in sorted_moves:
        nb = apply_move(board, m)
        # Quiescence / 1-ply search on replies
        # Evaluate reply moves
        score = -quiesce(nb, -beta, -alpha, not white_to_move, depth=2)
        if score > best_score:
            best_score = score
            best_move = m
        if score > alpha:
            alpha = score

    return best_move

def main():
    while True:
        g = post("/game", {})
        if g.get("status") == "done":
            break
        while g.get("status") == "your_move":
            move = choose_move(g["fen"], g["legal_moves"])
            g = post("/move", {"game": g["game"], "move": move})
        print(f"game {g['game']}: {g['outcome']} by {g.get('reason', '')}", file=sys.stderr)
    print(f"done: {g.get('wins')} won, {g.get('draws')} drawn, {g.get('losses')} lost", file=sys.stderr)

if __name__ == "__main__":
    main()
