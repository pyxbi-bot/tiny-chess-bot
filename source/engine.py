import json
import os
import sys
import time
import urllib.request
import urllib.error

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")

PIECE_VAL = {"P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 20000}

# Piece-Square Tables (White's perspective, rank 8 down to rank 1)
PST = {
    "P": (
        0,  0,  0,  0,  0,  0,  0,  0,
        50, 50, 50, 50, 50, 50, 50, 50,
        10, 10, 20, 30, 30, 20, 10, 10,
        5,  5, 10, 27, 27, 10,  5,  5,
        0,  0,  0, 25, 25,  0,  0,  0,
        5, -5,-10,  0,  0,-10, -5,  5,
        5, 10, 10,-25,-25, 10, 10,  5,
        0,  0,  0,  0,  0,  0,  0,  0
    ),
    "N": (
        -50,-40,-30,-30,-30,-30,-40,-50,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -30,  5, 20, 25, 25, 20,  5,-30,
        -30,  0, 20, 25, 25, 20,  0,-30,
        -30,  5, 15, 20, 20, 15,  5,-30,
        -40,-20,  0,  5,  5,  0,-20,-40,
        -50,-40,-30,-30,-30,-30,-40,-50
    ),
    "B": (
        -20,-10,-10,-10,-10,-10,-10,-20,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -10, 10, 10, 15, 15, 10, 10,-10,
        -10,  5, 10, 15, 15, 10,  5,-10,
        -10,  0, 15, 15, 15, 15,  0,-10,
        -10, 10, 15, 15, 15, 15, 10,-10,
        -10,  5,  0,  0,  0,  0,  5,-10,
        -20,-10,-10,-10,-10,-10,-10,-20
    ),
    "R": (
        0,  0,  0,  5,  5,  0,  0,  0,
        15, 20, 20, 20, 20, 20, 20, 15,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        0,  0,  0,  5,  5,  0,  0,  0
    ),
    "Q": (
        -20,-10,-10, -5, -5,-10,-10,-20,
        -10,  0,  5,  0,  0,  0,  0,-10,
        -10,  5,  5,  5,  5,  5,  0,-10,
        -5,  0,  5,  5,  5,  5,  0, -5,
        -5,  0,  5,  5,  5,  5,  0, -5,
        -10,  0,  5,  5,  5,  5,  0,-10,
        -10,  0,  0,  0,  0,  0,  0,-10,
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
    return (8 - int(sq[1])) * 8 + (ord(sq[0]) - ord('a'))

def evaluate_pos(board, white_to_move):
    score = 0
    for sq, p in board.items():
        pt = p.upper()
        v = PIECE_VAL.get(pt, 0)
        idx = sq_to_idx(sq)
        pst_val = 0
        if pt in PST:
            if p.isupper():
                pst_val = PST[pt][idx]
            else:
                r = idx // 8
                c = idx % 8
                pst_val = PST[pt][(7 - r) * 8 + c]
        tot = v + pst_val
        if p.isupper():
            score += tot
        else:
            score -= tot
    return score if white_to_move else -score

def get_pseudo_moves(board, white_to_move):
    moves = []
    for sq, p in board.items():
        if (p.isupper() == white_to_move):
            c = ord(sq[0]) - ord('a')
            r = int(sq[1])
            pt = p.upper()
            if pt == 'P':
                step = 1 if white_to_move else -1
                nr = r + step
                if 1 <= nr <= 8:
                    tsq = chr(ord('a') + c) + str(nr)
                    if tsq not in board:
                        if nr in (1, 8):
                            for promo in ('q', 'r', 'b', 'n'): moves.append(sq + tsq + promo)
                        else:
                            moves.append(sq + tsq)
                            start_rank = 2 if white_to_move else 7
                            if r == start_rank:
                                tsq2 = chr(ord('a') + c) + str(r + 2 * step)
                                if tsq2 not in board:
                                    moves.append(sq + tsq2)
                for dc in (-1, 1):
                    nc = c + dc
                    nr = r + step
                    if 0 <= nc <= 7 and 1 <= nr <= 8:
                        tsq = chr(ord('a') + nc) + str(nr)
                        target = board.get(tsq)
                        if target and (target.isupper() != white_to_move):
                            if nr in (1, 8):
                                for promo in ('q', 'r', 'b', 'n'): moves.append(sq + tsq + promo)
                            else:
                                moves.append(sq + tsq)
            elif pt in ('N', 'K'):
                deltas = [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)] if pt == 'N' else [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
                for dc, dr in deltas:
                    nc, nr = c + dc, r + dr
                    if 0 <= nc <= 7 and 1 <= nr <= 8:
                        tsq = chr(ord('a') + nc) + str(nr)
                        target = board.get(tsq)
                        if not target or (target.isupper() != white_to_move):
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
                        if not target:
                            moves.append(sq + tsq)
                        else:
                            if target.isupper() != white_to_move:
                                moves.append(sq + tsq)
                            break
                        nc += dc
                        nr += dr
    return moves

def apply_move(board, move):
    nb = dict(board)
    src = move[:2]
    dst = move[2:4]
    p = nb.pop(src, None)
    if not p:
        return nb
    if len(move) == 5:
        p = move[4].upper() if p.isupper() else move[4].lower()
    if p.upper() == 'P' and src[0] != dst[0] and dst not in nb:
        nb.pop(dst[0] + src[1], None) # en-passant
    if p.upper() == 'K': # castling rook movement
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
    nb[dst] = p
    return nb

def order_moves(moves, board):
    def score_move(m):
        dst = m[2:4]
        target = board.get(dst)
        if target:
            attacker = board.get(m[:2], 'P').upper()
            return 1000 + PIECE_VAL.get(target.upper(), 0) - PIECE_VAL.get(attacker, 0) // 10
        if len(m) == 5:
            return 900
        if dst in ('e4', 'd4', 'e5', 'd5'):
            return 50
        if dst in ('c4', 'f4', 'c5', 'f5'):
            return 25
        return 0
    return sorted(moves, key=score_move, reverse=True)

def quiesce(board, alpha, beta, white_to_move, qdepth=0):
    stand_pat = evaluate_pos(board, white_to_move)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat
    if qdepth >= 4:
        return alpha

    captures = []
    for m in get_pseudo_moves(board, white_to_move):
        dst = m[2:4]
        target = board.get(dst)
        if target:
            if target.upper() == 'K':
                return 20000
            captures.append(m)
        elif len(m) == 5:
            captures.append(m)

    if not captures:
        return stand_pat

    captures = order_moves(captures, board)
    for m in captures:
        nb = apply_move(board, m)
        score = -quiesce(nb, -beta, -alpha, not white_to_move, qdepth + 1)
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha

def alpha_beta(board, depth, alpha, beta, white_to_move):
    moves = get_pseudo_moves(board, white_to_move)
    if not moves:
        return 0

    # Immediate King capture check
    for m in moves:
        if board.get(m[2:4], '').upper() == 'K':
            return 20000 + depth

    if depth <= 0:
        return quiesce(board, alpha, beta, white_to_move)

    moves = order_moves(moves, board)
    best_val = -999999

    for m in moves:
        nb = apply_move(board, m)
        val = -alpha_beta(nb, depth - 1, -beta, -alpha, not white_to_move)
        if val > best_val:
            best_val = val
        if val > alpha:
            alpha = val
        if alpha >= beta:
            break
    return best_val

def choose_move(fen, legal_moves):
    if not legal_moves:
        return None
    if len(legal_moves) == 1:
        return legal_moves[0]

    board, white_to_move = parse_fen(fen)
    sorted_moves = order_moves(legal_moves, board)

    best_move = sorted_moves[0]
    t0 = time.time()

    # Iterative deepening: Depth 2 then Depth 3 with 4.5s timeout
    for depth in (2, 3):
        curr_best = best_move
        curr_best_score = -999999
        alpha = -999999
        beta = 999999
        aborted = False

        for m in sorted_moves:
            if time.time() - t0 > 4.5:
                aborted = True
                break

            dst = m[2:4]
            if board.get(dst, '').upper() == 'K':
                return m

            nb = apply_move(board, m)
            score = -alpha_beta(nb, depth, -beta, -alpha, not white_to_move)
            if score > curr_best_score:
                curr_best_score = score
                curr_best = m
            if score > alpha:
                alpha = score

        if not aborted:
            best_move = curr_best
        else:
            break

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
