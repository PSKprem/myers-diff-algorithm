import sys


def read_file_as_lines(path: str) -> list[bytes] | None:
    """Read file as raw bytes and split into lines."""
    try:
        with open(path, "rb") as f:
            content = f.read()
        lines = content.split(b'\n')
        if lines and lines[-1] == b'':
            lines.pop()
        return lines
    except (FileNotFoundError, PermissionError, OSError):
        return None


def myers_diff(a, b):
    """
    Myers O(ND) difference algorithm.
    Paper: Eugene Myers, 'An O(ND) Difference Algorithm and Its Variations', 1986.

    Phase 1 – forward pass:
      V[k] = furthest x reachable on diagonal k = (x - y).
      We iterate d = 0, 1, 2, ... and for each d try every diagonal k in [-d, d].
      After each d-round we save a snapshot of V into `trace`.

    Phase 2 – backtrack:
      We walk backwards through the snapshots.  At each step d we know (x, y)
      and reproduce the same direction choice that was made during the forward
      pass (using the snapshot from d-1 rounds).  That tells us whether the
      single edit at this step was a delete (move RIGHT) or insert (move DOWN).
      The snake (diagonal moves = keeps) is reconstructed around each edit.
    """
    n, m = len(a), len(b)

    # ── Phase 1: forward ──────────────────────────────────────────────────────
    max_d = n + m
    # Use a plain list indexed as V[k + max_d] so negative k works fine.
    V = [0] * (2 * max_d + 2)

    # Sentinel: treat V[k] = -1 for k values not yet reachable.
    # k = 1 is the starting diagonal (we pretend we came from (0, -1) on k=1).
    V[1 + max_d] = 0

    trace = []    # trace[d] = snapshot of V after the d-th round

    found_d = -1
    for d in range(0, max_d + 1):
        for k in range(-d, d + 1, 2):
            ki = k + max_d
            # Choose direction
            if k == -d or (k != d and V[ki - 1] < V[ki + 1]):
                x = V[ki + 1]          # come from diagonal k+1 → move DOWN (insert)
            else:
                x = V[ki - 1] + 1     # come from diagonal k-1 → move RIGHT (delete)

            y = x - k

            # Follow the snake
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1

            V[ki] = x

            if x >= n and y >= m:
                trace.append(V[:])
                found_d = d
                break
        if found_d >= 0:
            break
        trace.append(V[:])

    # ── Phase 2: backtrack ────────────────────────────────────────────────────
    ops = []
    x, y = n, m

    for d in range(found_d, 0, -1):
        # The snapshot used to make the choice at round d is trace[d-1].
        Vprev = trace[d - 1]
        k = x - y
        ki = k + max_d

        # Reproduce the same direction choice
        if k == -d or (k != d and Vprev[ki - 1] < Vprev[ki + 1]):
            # Came from diagonal k+1 → the edit was an INSERT (move DOWN)
            prev_k = k + 1
        else:
            # Came from diagonal k-1 → the edit was a DELETE (move RIGHT)
            prev_k = k - 1

        prev_x = Vprev[prev_k + max_d]
        prev_y = prev_x - prev_k

        # The snake at the end of this d-step:  from (prev_x + edit_dx, prev_y + edit_dy)
        # to (x, y).  Walk it backwards as 'keep' operations.
        if prev_k == k + 1:
            # edit was DOWN: x didn't change, y increased by 1
            edit_end_x = prev_x
            edit_end_y = prev_y + 1
        else:
            # edit was RIGHT: x increased by 1, y didn't change
            edit_end_x = prev_x + 1
            edit_end_y = prev_y

        while x > edit_end_x and y > edit_end_y:
            ops.append(('keep', a[x - 1]))
            x -= 1
            y -= 1

        # Record the edit itself
        if prev_k == k + 1:
            # INSERT: consumed b[prev_y]
            ops.append(('insert', b[y - 1]))
            y -= 1
        else:
            # DELETE: consumed a[prev_x]
            ops.append(('delete', a[x - 1]))
            x -= 1

        # Sanity: after undoing the edit we should be at (prev_x, prev_y)
        # (any remaining diagonal moves before the edit are handled next iteration)

    # Everything remaining from (x, y) back to (0, 0) is a snake (all keeps).
    while x > 0 or y > 0:
        if x > 0 and y > 0:
            ops.append(('keep', a[x - 1]))
            x -= 1
            y -= 1
        elif x > 0:
            ops.append(('delete', a[x - 1]))
            x -= 1
        else:
            ops.append(('insert', b[y - 1]))
            y -= 1

    ops.reverse()
    return ops


def print_diff_lines(ops):
    """Print Part A: line diff with delete-first rule."""
    out = sys.stdout.buffer
    i = 0
    while i < len(ops):
        op, item = ops[i]
        if op == 'keep':
            out.write(b' ' + item + b'\n')
            i += 1
        else:
            # Collect the whole change block, then apply delete-first rule
            deletes = []
            inserts = []
            while i < len(ops) and ops[i][0] != 'keep':
                op2, item2 = ops[i]
                if op2 == 'delete':
                    deletes.append(item2)
                else:
                    inserts.append(item2)
                i += 1
            for item2 in deletes:
                out.write(b'-' + item2 + b'\n')
            for item2 in inserts:
                out.write(b'+' + item2 + b'\n')


def char_diff_ranges(old_bytes: bytes, new_bytes: bytes):
    """
    Run Myers diff at character level and return (old_range_str, new_range_str).
    Both inputs are valid UTF-8 (guaranteed by the assignment for highlight tests).
    We work on Unicode code points so each emoji counts as 1.
    """
    old_cps = list(old_bytes.decode('utf-8'))
    new_cps = list(new_bytes.decode('utf-8'))

    ops = myers_diff(old_cps, new_cps)

    old_ranges = []
    new_ranges = []
    old_pos = 0
    new_pos = 0
    old_start = None
    new_start = None

    for op, _ in ops:
        if op == 'keep':
            if old_start is not None:
                old_ranges.append((old_start, old_pos))
                old_start = None
            if new_start is not None:
                new_ranges.append((new_start, new_pos))
                new_start = None
            old_pos += 1
            new_pos += 1
        elif op == 'delete':
            if old_start is None:
                old_start = old_pos
            old_pos += 1
        else:  # insert
            if new_start is None:
                new_start = new_pos
            new_pos += 1

    if old_start is not None:
        old_ranges.append((old_start, old_pos))
    if new_start is not None:
        new_ranges.append((new_start, new_pos))

    def fmt(ranges):
        if not ranges:
            return '.'
        merged = [list(ranges[0])]
        for s, e in ranges[1:]:
            if s == merged[-1][1]:
                merged[-1][1] = e
            else:
                merged.append([s, e])
        return ','.join(f'{s}-{e}' for s, e in merged)

    return fmt(old_ranges), fmt(new_ranges)


def print_diff_highlight(ops):
    """Print Part B: line diff with per-pair character-range lines."""
    out = sys.stdout.buffer
    i = 0
    while i < len(ops):
        op, item = ops[i]
        if op == 'keep':
            out.write(b' ' + item + b'\n')
            i += 1
        else:
            deletes = []
            inserts = []
            while i < len(ops) and ops[i][0] != 'keep':
                op2, item2 = ops[i]
                if op2 == 'delete':
                    deletes.append(item2)
                else:
                    inserts.append(item2)
                i += 1

            for item2 in deletes:
                out.write(b'-' + item2 + b'\n')

            pairs = min(len(deletes), len(inserts))
            for j, item2 in enumerate(inserts):
                out.write(b'+' + item2 + b'\n')
                if j < pairs:
                    old_r, new_r = char_diff_ranges(deletes[j], item2)
                    out.write(f'? {old_r} | {new_r}\n'.encode())


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ('lines', 'highlight'):
        print('usage: main.py lines|highlight A_PATH B_PATH', file=sys.stderr)
        return 2

    command, a_path, b_path = sys.argv[1], sys.argv[2], sys.argv[3]

    a_lines = read_file_as_lines(a_path)
    if a_lines is None:
        print(f'error: cannot read file {a_path}', file=sys.stderr)
        return 2

    b_lines = read_file_as_lines(b_path)
    if b_lines is None:
        print(f'error: cannot read file {b_path}', file=sys.stderr)
        return 2

    ops = myers_diff(a_lines, b_lines)

    if command == 'lines':
        print_diff_lines(ops)
    else:
        print_diff_highlight(ops)

    return 0


raise SystemExit(main())
