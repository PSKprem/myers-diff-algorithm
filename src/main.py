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
    Based on: http://www.xmailserver.org/diff2.pdf
    
    This implementation builds the edit script incrementally as it explores
    the edit graph, avoiding the need for backtracking.
    """
    n, m = len(a), len(b)
    
    # Handle edge cases
    if n == 0:
        return [('insert', item) for item in b]
    if m == 0:
        return [('delete', item) for item in a]
    
    # Frontier maps diagonal k to (x_position, history)
    # k = x - y, so each diagonal represents x - y = constant
    frontier = {1: (0, [])}
    
    a_max = n
    b_max = m
    
    for d in range(0, a_max + b_max + 1):
        for k in range(-d, d + 1, 2):
            # Decide whether to go DOWN (insert) or RIGHT (delete)
            # DOWN: come from k+1 diagonal (y increases)
            # RIGHT: come from k-1 diagonal (x increases)
            go_down = (k == -d or 
                       (k != d and frontier.get(k - 1, (-1, []))[0] < 
                        frontier.get(k + 1, (-1, []))[0]))
            
            if go_down:
                # Move DOWN (insert from b)
                old_x, history = frontier[k + 1]
                x = old_x
            else:
                # Move RIGHT (delete from a)
                old_x, history = frontier[k - 1]
                x = old_x + 1
            
            # Copy history to avoid modifying shared state
            history = list(history)
            
            y = x - k
            
            # Record the edit operation
            # Use 1-indexed positions for comparisons (Myers paper convention)
            if 1 <= y <= b_max and go_down:
                history.append(('insert', b[y - 1]))
            elif 1 <= x <= a_max:
                history.append(('delete', a[x - 1]))
            
            # Follow the diagonal ("snake") - matching elements
            while x < a_max and y < b_max and a[x] == b[y]:
                x += 1
                y += 1
                history.append(('keep', a[x - 1]))
            
            # Check if we've reached the end
            if x >= a_max and y >= b_max:
                return history
            
            # Update frontier for this diagonal
            frontier[k] = (x, history)
    
    # Should never reach here
    return []


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
