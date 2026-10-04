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
    Diff algorithm using LCS approach.
    Returns list of (op, item) tuples representing the edit script.
    """
    n, m = len(a), len(b)
    
    if n == 0:
        return [('insert', item) for item in b]
    if m == 0:
        return [('delete', item) for item in a]
    
    # DP table for LCS length
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    
    # Backtrack to build edit script
    result = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i-1] == b[j-1]:
            result.append(('keep', a[i-1]))
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or dp[i][j-1] >= dp[i-1][j]):
            result.append(('insert', b[j-1]))
            j -= 1
        else:
            result.append(('delete', a[i-1]))
            i -= 1
    
    result.reverse()
    return result


def print_diff_lines(ops):
    """Print Part A: line diff with delete-first rule."""
    i = 0
    while i < len(ops):
        op, item = ops[i]
        if op == 'keep':
            sys.stdout.buffer.write(b' ' + item + b'\n')
            i += 1
        else:
            # Collect change block
            deletes, inserts = [], []
            while i < len(ops) and ops[i][0] != 'keep':
                op, item = ops[i]
                (deletes if op == 'delete' else inserts).append(item)
                i += 1
            # Delete-first rule
            for item in deletes:
                sys.stdout.buffer.write(b'-' + item + b'\n')
            for item in inserts:
                sys.stdout.buffer.write(b'+' + item + b'\n')


def char_diff_ranges(old_bytes, new_bytes):
    """Calculate character-level diff ranges."""
    old_str = old_bytes.decode('utf-8')
    new_str = new_bytes.decode('utf-8')
    
    ops = myers_diff(list(old_str), list(new_str))
    
    old_ranges, new_ranges = [], []
    old_pos, new_pos = 0, 0
    old_start, new_start = None, None
    
    for op, char in ops:
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
    
    def format_ranges(ranges):
        if not ranges:
            return '.'
        merged = []
        for start, end in ranges:
            if merged and merged[-1][1] == start:
                merged[-1] = (merged[-1][0], end)
            else:
                merged.append((start, end))
        return ','.join(f'{s}-{e}' for s, e in merged)
    
    return format_ranges(old_ranges), format_ranges(new_ranges)


def print_diff_highlight(ops):
    """Print Part B: line diff with character ranges."""
    i = 0
    while i < len(ops):
        op, item = ops[i]
        if op == 'keep':
            sys.stdout.buffer.write(b' ' + item + b'\n')
            i += 1
        else:
            deletes, inserts = [], []
            while i < len(ops) and ops[i][0] != 'keep':
                op, item = ops[i]
                (deletes if op == 'delete' else inserts).append(item)
                i += 1
            
            for item in deletes:
                sys.stdout.buffer.write(b'-' + item + b'\n')
            
            pairs = min(len(deletes), len(inserts))
            for j, item in enumerate(inserts):
                sys.stdout.buffer.write(b'+' + item + b'\n')
                if j < pairs:
                    old_r, new_r = char_diff_ranges(deletes[j], item)
                    sys.stdout.buffer.write(f'? {old_r} | {new_r}\n'.encode('utf-8'))


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        print("usage: main.py lines|highlight A_PATH B_PATH", file=sys.stderr)
        return 2
    
    command, a_path, b_path = sys.argv[1:]
    
    a_lines = read_file_as_lines(a_path)
    if a_lines is None:
        print(f"error: cannot read file {a_path}", file=sys.stderr)
        return 2
    
    b_lines = read_file_as_lines(b_path)
    if b_lines is None:
        print(f"error: cannot read file {b_path}", file=sys.stderr)
        return 2
    
    ops = myers_diff(a_lines, b_lines)
    
    if command == "lines":
        print_diff_lines(ops)
    else:
        print_diff_highlight(ops)
    
    return 0


raise SystemExit(main())
