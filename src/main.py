import sys
from pathlib import Path


def read_file_as_lines(path: str) -> list[bytes] | None:
    """
    Read a file as raw bytes and split into lines according to assignment rules.
    
    Rules:
    1. Read as raw bytes (not text)
    2. Split on newline byte \n
    3. If last piece is empty, drop it (final newline creates no extra empty line)
    4. Keep \r as part of the line (a\r\n and a\n are different lines)
    
    Returns:
        List of byte lines if successful, None if file cannot be read
    """
    try:
        with open(path, "rb") as f:
            content = f.read()
        
        # Split on newline byte
        lines = content.split(b'\n')
        
        # Drop last piece if empty
        if lines and lines[-1] == b'':
            lines.pop()
        
        return lines
    
    except (FileNotFoundError, PermissionError, OSError) as e:
        return None


def main() -> int:
    # Validate command-line arguments
    if len(sys.argv) != 4 or sys.argv[1] not in ("lines", "highlight"):
        print("usage: main.py lines|highlight A_PATH B_PATH", file=sys.stderr)
        return 2
    
    command, a_path, b_path = sys.argv[1:]
    
    # Read both files as raw bytes
    a_lines = read_file_as_lines(a_path)
    if a_lines is None:
        print(f"error: cannot read file {a_path}", file=sys.stderr)
        return 2
    
    b_lines = read_file_as_lines(b_path)
    if b_lines is None:
        print(f"error: cannot read file {b_path}", file=sys.stderr)
        return 2
    
    # Debug output to stderr for verification
    print(f"debug: successfully read {len(a_lines)} lines from {a_path}", file=sys.stderr)
    print(f"debug: successfully read {len(b_lines)} lines from {b_path}", file=sys.stderr)
    
    # TODO: Implement Myers' diff algorithm
    # TODO: Generate and print diff output
    
    return 0


raise SystemExit(main())
