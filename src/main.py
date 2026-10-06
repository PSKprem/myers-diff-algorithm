import sys

def read_lines(path):
    """Read a file as raw bytes while preserving its original line structure."""

    # Binary mode keeps the diff honest: no encoding conversion, newline
    # normalization, or decoding error can change what the user actually wrote.
    with open(path, 'rb') as f:

        lines = f.read().split(b'\n')

    # split(b'\n') creates a final empty element when the file ends with a
    # newline. That is a storage artifact, not an extra blank line to compare.
    if lines and (not lines[-1]):

        lines.pop()

    return lines

def middle_snake(A, B, Ar, Br, n, m):
    """Return the midpoint that minimizes the edit distance between two sequences."""

    # Myers' algorithm searches diagonals in an edit graph. delta tells us how
    # far the final diagonal is shifted because the two sequences have different
    # lengths, and the parity decides whether the front and back waves can meet
    # during the forward or backward half of the search.
    delta = n - m

    odd = delta & 1

    # We only need to search half of the maximum possible edit distance because
    # this function finds a split point. The caller solves the two smaller halves
    # later, which keeps the full diff from becoming one huge recursive problem.
    max_d = (n + m + 1) // 2

    # Diagonal numbers can be negative, so offset translates them into valid
    # byte/list indexes. The extra padding lets idx - 1 and idx + 1 stay safe at
    # the active frontier edges.
    offset = max_d + 1

    size = 2 * max_d + 3

    # vf and vb store the furthest x position reached on each diagonal from the
    # front and from the back. Keeping only the frontier is why Myers diff is
    # memory efficient compared with filling an entire edit-distance matrix.
    vf = [-1] * size

    vb = [-1] * size

    # The initial diagonal is seeded at offset + 1 to match the recurrence below:
    # the first step can read neighboring diagonals without special setup code.
    vf[offset + 1] = 0

    vb[offset + 1] = 0

    # These trim values skip frontiers that already ran outside the edit graph.
    # They are small performance guards for very uneven or already-exhausted
    # ranges.
    fs = fe = bs = be = 0

    for d in range(max_d + 1):

        # Forward wave: each d means "allow one more edit". k is the diagonal
        # x - y, and we advance by 2 because only every other diagonal is
        # reachable at a given edit depth.
        start = -d + fs

        end = d - fe

        for k in range(start, end + 1, 2):

            idx = offset + k

            # Choose whether the best previous path came from an insertion-like
            # move or a deletion-like move. The larger furthest reach is kept
            # because it gives the shortest path the most progress.
            if k == -d or (k != d and vf[idx - 1] < vf[idx + 1]):

                x = vf[idx + 1]

            else:

                x = vf[idx - 1] + 1

            y = x - k

            x0 = x

            y0 = y

            # After paying for one edit, matching items are free. This loop is
            # the "snake": a maximal run of equal items on the same diagonal.
            while x < n and y < m and (A[x] == B[y]):
                # Advance along the matching diagonal until the sequences diverge.

                x += 1

                y += 1

            vf[idx] = x

            # If a frontier stepped past one side, trim that edge so later
            # iterations do not keep checking impossible diagonals.
            if x > n:

                fe += 2

                continue

            if y > m:

                fs += 2

                continue

            if odd:

                # With odd total path length, the forward wave can meet the
                # previous backward wave. x + xb >= n means the two searches
                # overlap, proving that this snake is a valid split.
                kb = delta - k

                if -d < kb < d:

                    xb = vb[offset + kb]

                    if xb != -1 and x + xb >= n:

                        return (x0, y0, x, y)

        start = -d + bs

        end = d - be

        # Backward wave: it is the same search, but over reversed slices. Doing
        # both directions lets us find the middle split without computing the
        # whole path at once.
        for k in range(start, end + 1, 2):

            idx = offset + k

            if k == -d or (k != d and vb[idx - 1] < vb[idx + 1]):

                x = vb[idx + 1]

            else:

                x = vb[idx - 1] + 1

            y = x - k

            x0 = x

            y0 = y

            # Match common suffix content in the reversed view. The returned
            # coordinates are converted back to the original orientation below.
            while x < n and y < m and (Ar[x] == Br[y]):

                x += 1

                y += 1

            vb[idx] = x

            if x > n:

                be += 2

                continue

            if y > m:

                bs += 2

                continue

            if not odd:

                # With even total path length, the backward wave is the one that
                # can meet the current forward wave at the same depth.
                kf = delta - k

                if -d <= kf <= d:

                    xf = vf[offset + kf]

                    if xf != -1 and xf + x >= n:

                        return (n - x, m - y, n - x0, m - y0)

    raise RuntimeError('middle snake not found')

def diff_marks(a, b):
    """Return deletion and insertion masks for the two sequences."""

    na = len(a)

    nb = len(b)

    ids = {}

    ia = []

    ib = []

    # Map arbitrary input values to compact integer IDs. Integer sequences are
    # cheaper to compare repeatedly, and using one shared map guarantees that
    # equal lines/characters receive the same identity on both sides.
    for item in a:

        value = ids.get(item)

        if value is None:

            value = len(ids)

            ids[item] = value

        ia.append(value)

    for item in b:

        value = ids.get(item)

        if value is None:

            value = len(ids)

            ids[item] = value

        ib.append(value)

    # Values that occur on only one side can never participate in a match. We
    # filter them out before running Myers so the expensive part works only on
    # plausible matches; those one-sided values stay marked as changed later.
    in_a = set(ia)

    in_b = set(ib)

    ma = [i for i, value in enumerate(ia) if value in in_b]

    mb = [j for j, value in enumerate(ib) if value in in_a]

    fa = [ia[i] for i in ma]

    fb = [ib[j] for j in mb]

    del_f = bytearray(len(fa))

    ins_f = bytearray(len(fb))

    # Use an explicit stack instead of Python recursion. Large files can create
    # many splits, and a stack avoids recursion-depth failures while preserving
    # the divide-and-conquer shape of Myers' algorithm.
    stack = [(0, len(fa), 0, len(fb))]

    while stack:

        a0, a1, b0, b1 = stack.pop()

        # Trim matching edges first. This reduces the subproblem before the
        # middle-snake search and also prevents unchanged prefixes/suffixes from
        # being marked as edits.
        while a0 < a1 and b0 < b1 and (fa[a0] == fb[b0]):

            a0 += 1

            b0 += 1

        while a0 < a1 and b0 < b1 and (fa[a1 - 1] == fb[b1 - 1]):

            a1 -= 1

            b1 -= 1

        if a0 == a1:

            # Nothing remains on the left, so every unresolved right-side item is
            # an insertion.
            if b0 < b1:

                ins_f[b0:b1] = b'\x01' * (b1 - b0)

            continue

        if b0 == b1:

            # Nothing remains on the right, so every unresolved left-side item is
            # a deletion.
            del_f[a0:a1] = b'\x01' * (a1 - a0)

            continue

        A = fa[a0:a1]

        B = fb[b0:b1]

        n = a1 - a0

        m = b1 - b0

        Ar = A[::-1]

        Br = B[::-1]

        # Sentinels stop the snake scan from accidentally reading past the real
        # slice. They must differ so a boundary on A never matches a boundary on
        # B and creates a fake common item.
        A.append(-1)

        B.append(-2)

        Ar.append(-1)

        Br.append(-2)

        sx, sy, ex, ey = middle_snake(A, B, Ar, Br, n, m)

        # Split around the middle snake. The matching snake itself is excluded
        # from both new subproblems because it is unchanged.
        stack.append((a0 + ex, a1, b0 + ey, b1))

        stack.append((a0, a0 + sx, b0, b0 + sy))

    del_a = bytearray(b'\x01') * na

    ins_b = bytearray(b'\x01') * nb

    # The filtered masks use filtered indexes, but the renderer needs original
    # file indexes. Items removed by filtering remain marked as changed, which is
    # correct because they had no possible match on the other side.
    for filtered_index, original_index in enumerate(ma):

        del_a[original_index] = del_f[filtered_index]

    for filtered_index, original_index in enumerate(mb):

        ins_b[original_index] = ins_f[filtered_index]

    return (del_a, ins_b)

def ranges(marks):
    """Convert a binary mask into a compact range list."""

    n = len(marks)

    parts = []

    start = marks.find(1)

    # Store ranges as half-open intervals [start, end). That matches Python's
    # slicing convention and avoids off-by-one ambiguity in the highlight output.
    while start != -1:

        end = marks.find(0, start)

        if end == -1:

            end = n

        parts.append(f'{start}-{end}')

        if end >= n:

            break

        start = marks.find(1, end)

    return ','.join(parts) if parts else '.'

def build_output(a, b, del_a, ins_b, highlight):
    """Build the final diff output using the computed change masks."""

    na = len(a)

    nb = len(b)

    out = []

    i = j = 0

    while True:

        # Find the next changed block on either side. Until one appears, the two
        # files are aligned and can be emitted as unchanged context.
        next_delete = del_a.find(1, i)

        next_insert = ins_b.find(1, j)

        if next_delete == -1 and next_insert == -1:

            break

        count = na - i

        if next_delete != -1:

            count = min(count, next_delete - i)

        if next_insert != -1:

            count = min(count, next_insert - j)

        if count:

            # Unchanged lines are emitted from A only because, in aligned regions,
            # A and B contain the same content.
            out.extend((b' ' + line for line in a[i:i + count]))

            i += count

            j += count

        delete_end = del_a.find(0, i)

        if delete_end == -1:

            delete_end = na

        insert_end = ins_b.find(0, j)

        if insert_end == -1:

            insert_end = nb

        deleted = a[i:delete_end]

        inserted = b[j:insert_end]

        # A changed block may contain only deletions, only insertions, or both.
        # Rendering deletions first gives a stable old-then-new diff layout.
        out.extend((b'-' + line for line in deleted))

        if not highlight:

            out.extend((b'+' + line for line in inserted))

        else:

            paired = min(len(deleted), len(inserted))

            # Highlight mode compares paired old/new lines character by
            # character. Extra inserted lines still print normally, but they have
            # no old partner for an inline marker.
            for index, line in enumerate(inserted):

                out.append(b'+' + line)

                if index < paired:

                    old = deleted[index].decode('utf-8', 'surrogateescape')

                    new = line.decode('utf-8', 'surrogateescape')

                    # Reuse the same diff engine at character level. That keeps
                    # line highlighting consistent with the line-level algorithm.
                    deleted_marks, inserted_marks = diff_marks(old, new)

                    marker = f'? {ranges(deleted_marks)} | {ranges(inserted_marks)}'.encode('utf-8')

                    out.append(marker)

        i = delete_end

        j = insert_end

    if i < na:

        out.extend((b' ' + line for line in a[i:]))

    return out

def main():
    """Run the CLI entry point for line and highlight diff modes."""

    # The CLI accepts exactly one mode and two paths. Returning 2 follows the
    # common shell convention for invalid command usage.
    if len(sys.argv) != 4:

        print('usage: main.py lines|highlight A_PATH B_PATH', file=sys.stderr)

        return 2

    command = sys.argv[1]

    if command not in ('lines', 'highlight'):

        print('usage: main.py lines|highlight A_PATH B_PATH', file=sys.stderr)

        return 2

    try:

        # File errors are reported without a traceback so the tool behaves like a
        # normal command-line program.
        a = read_lines(sys.argv[2])

        b = read_lines(sys.argv[3])

    except OSError as exc:

        print(f'error: cannot read file: {exc}', file=sys.stderr)

        return 2

    del_a, ins_b = diff_marks(a, b)

    # The algorithm phase returns masks; the rendering phase decides whether the
    # user asked for plain line output or extra inline highlights.
    output = build_output(a, b, del_a, ins_b, command == 'highlight')

    if output:

        sys.stdout.buffer.write(b'\n'.join(output) + b'\n')

        sys.stdout.buffer.flush()

    return 0

if __name__ == '__main__':
    # Execute the CLI only when the script is run directly.

    raise SystemExit(main())
