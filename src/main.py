import sys
# Import sys so the script can inspect the command-line arguments,
# show usage errors, and exit with the correct status code.
# Without this, the program would not know which mode to run in,
# which files to compare, or how to communicate failures clearly.

def read_lines(path):
    # Define a helper that reads a file as raw bytes instead of text.
    # This preserves the exact original content, including binary-like data,
    # and keeps each line separated by a byte boundary for precise diffing.
    # If we converted to text too early, we could lose fidelity for unusual input.
    with open(path, 'rb') as f:
        # Open the file in binary mode so every byte stays intact.
        # This matters because the diff logic compares exact line values,
        # and a text conversion would normalize line endings and encoding.
        lines = f.read().split(b'\n')
        # Split on newline bytes so each record is a raw line fragment.
        # This lets us compare the content as a sequence of lines,
        # and it avoids treating a single file as one huge string.
    if lines and (not lines[-1]):
        # Remove the final empty record created by a trailing newline.
        # Without this, the last item would be an extra blank line,
        # which would falsely look like a deletion or insertion at the end.
        lines.pop()
        # Pop removes the artifact so the diff reflects the file's real content.
        # If we do not do this, a file ending with a newline would be miscounted.
    return lines
    # Return the exact list of raw lines to the caller.
    # This gives the diff engine a stable input to analyze without hidden formatting changes.


def middle_snake(A, B, Ar, Br, n, m):
    # Compute the central split point used by Myers' algorithm.
    # This is the critical search that finds the midpoint of the shortest edit path,
    # allowing the algorithm to recurse on smaller subproblems instead of comparing everything blindly.
    # If this step is skipped or broken, the diff would not know where the common middle region begins.
    delta = n - m
    # delta shows whether the left side has more items than the right side.
    # This helps pick the right diagonal set and keeps the search balanced.
    # Without this, the algorithm would not know how far the matching region is shifted.
    odd = delta & 1
    # odd tells us whether the edit distance is odd or even.
    # This matters because different diagonal conditions are used depending on parity,
    # and incorrect parity handling can produce a wrong middle point.
    max_d = (n + m + 1) // 2
    # max_d is the maximum number of edit steps we may need to traverse.
    # It bounds the search so the algorithm grows outward from the middle only as needed.
    # If we did not limit the search depth, the loops could expand too much and become expensive.
    offset = max_d + 1
    # offset shifts the diagonal index so negative values become valid array indexes.
    # This prevents Python from indexing with negative values that do not map to the expected diagonals.
    size = 2 * max_d + 3
    # size creates room for the forward and backward search tables.
    # A larger enough array keeps every diagonal representable without accidental overwrites.
    vf = [-1] * size
    # vf stores the furthest reach on each forward diagonal.
    # These values show how far into the left sequence we can reach while matching on that diagonal.
    vb = [-1] * size
    # vb stores the furthest reach on each backward diagonal.
    # This backward table balances the forward search and lets us find the shortest split point from the end.
    vf[offset + 1] = 0
    # Seed the forward search at the first valid diagonal.
    # This gives the first iteration a known starting point from which to explore outward.
    vb[offset + 1] = 0
    # Seed the backward search with the same idea from the end side.
    # This symmetry is what lets the algorithm meet in the middle without missing optimal paths.
    fs = fe = bs = be = 0
    # These variables track how far the forward and backward searches have grown.
    # They prevent the loop from rechecking old search boundaries and help the algorithm stay efficient.
    for d in range(max_d + 1):
        # Iterate one edit-distance layer at a time.
        # This is the core of Myers' approach: we expand the search by one more edit depth each pass.
        # If we break too early, we could stop before the midpoint is confirmed; if we never stop, we search unnecessarily.
        start = -d + fs
        # start is the first diagonal index to inspect in the forward pass for this depth.
        # It shrinks or grows with the current search frontier, so we do not re-explore irrelevant diagonals.
        end = d - fe
        # end is the last diagonal index we need to inspect this round.
        # This boundary is what keeps the wavefront compact and efficient.
        for k in range(start, end + 1, 2):
            # Walk diagonals in steps of two because each edit layer changes the move count by one or two.
            # This ensures we check only valid states for the current depth and ignores impossible positions.
            idx = offset + k
            # Convert the diagonal index to the actual array offset.
            # Without this translation, negative or large k values would not match the storage layout correctly.
            if k == -d or (k != d and vf[idx - 1] < vf[idx + 1]):
                # Choose the better furthest x value on the current diagonal.
                # If the previous diagonal is worse, we move right; otherwise we stay on the current path.
                # This is the classic Myers strategy for choosing the best forward frontier.
                x = vf[idx + 1]
                # Start from the diagonal to the right when the current frontier is weak.
                # This keeps the search aligned with the furthest reachable point.
            else:
                # Otherwise we keep moving forward from the left neighbor.
                x = vf[idx - 1] + 1
                # Add one because we are stepping to the next match position along the current diagonal.
                # Without this, we would not advance past the last matched segment.
            y = x - k
            # Derive the y coordinate from the diagonal equation x - y = k.
            # This conversion is essential because the diff is being computed on a 2D matrix of the two sequences.
            x0 = x
            # Save the starting x position before consuming matching characters.
            # This preserves the exact edge of the candidate snake for later returning the split point.
            y0 = y
            # Save the starting y position before the substring match begins.
            # If we did not keep this, we could not reconstruct the correct boundary after the search.
            while x < n and y < m and (A[x] == B[y]):
                # Extend the forward candidate as long as the sequences still match.
                # This is the actual common-prefix progression on that diagonal and is what finds the middle snake.
                # If we stop too soon, we might miss a longer shared section that should remain in the overlap.
                x += 1
                # Move one step right in the left sequence.
                y += 1
                # Move one step down in the right sequence.
            vf[idx] = x
            # Record the furthest x value reached on this diagonal.
            # This is cached so future diagonals can use it to decide the next move.
            if x > n:
                # If we exceeded the left sequence length, this path is beyond the valid board.
                # The search should ignore it and keep exploring other diagonals.
                fe += 2
                # Advance the forward end boundary by two to skip impossible states.
                # This keeps the frontier from revisiting already-ruled-out positions.
                continue
                # Move on to the next diagonal without doing extra work.
            if y > m:
                # If the right side is exhausted, the path has also gone out of bounds.
                # This means the current candidate cannot produce a valid split for this edit depth.
                fs += 2
                # Expand the start boundary to avoid reprocessing stale frontiers.
                # Without this, the loop could revisit invalid search states forever.
                continue
                # Skip invalid extensions so the algorithm stays efficient.
            if odd:
                # For odd edit lengths, only the backward search can confirm a valid midpoint.
                # This parity check prevents us from accepting a split that is not truly centered.
                kb = delta - k
                # Compute the matching backward diagonal index to compare against the current front.
                # This aligns the forward and reverse searches around the same center line.
                if -d < kb < d:
                    # Only compare against meaningful diagonals in range.
                    # If the mirrored diagonal is outside the current depth, it cannot confirm the midpoint.
                    xb = vb[offset + kb]
                    # Read the furthest reachable point on the matching backward diagonal.
                    # This is the key handoff between forward and backward passes.
                    if xb != -1 and x + xb >= n:
                        # If both searches meet at the correct midpoint, we have found the central snake.
                        # This is the condition that proves a valid split exists for the current segment.
                        return (x0, y0, x, y)
                        # Return the boundaries of the middle snake.
                        # These coordinates tell the recursive caller where the common section sits within the subproblem.
        start = -d + bs
        # Reset the backward search start for the same edit depth.
        # This keeps the reverse scan aligned with the same wavefront level as the forward scan.
        end = d - be
        # Set the backward search end so it explores the correct set of diagonals.
        # Without proper bounds, the reverse pass would overlap invalid regions and miscompute the midpoint.
        for k in range(start, end + 1, 2):
            # Iterate the reverse diagonals in the same parity pattern.
            # This mirrors the forward pass and finds the matching region from the end of the sequences.
            idx = offset + k
            # Translate the diagonal index again for the backward array.
            # This ensures the reverse pass writes to the correct storage slot.
            if k == -d or (k != d and vb[idx - 1] < vb[idx + 1]):
                # Select the better forward/reverse boundary for this backward diagonal.
                # This picks the longer reachable path so the algorithm does not miss the shortest edit route.
                x = vb[idx + 1]
                # Start from the right side of the current diagonal when that is the stronger route.
            else:
                # Otherwise, move from the left side of the backward state.
                x = vb[idx - 1] + 1
                # Move one step forward along the reverse diagonal to the next viable candidate.
            y = x - k
            # Convert back to the y coordinate from the same diagonal equation.
            # This keeps the reverse pass aligned with the same coordinate system as the forward pass.
            x0 = x
            # Save the starting x coordinate before the backward match progression.
            # This is needed to recover the correct recursive boundary on the end side.
            y0 = y
            # Save the starting y coordinate for the same reason.
            # Without these snapshots, the function could not report the exact split where the reverse search met the forward one.
            while x < n and y < m and (Ar[x] == Br[y]):
                # Extend the reverse candidate while the suffix still matches.
                # This walks backward over common items so we can identify the matching tail.
                # If we fail to extend here, the midpoint would be wrong and the diff shape would be off.
                x += 1
                # Advance in the reversed left sequence.
                y += 1
                # Advance in the reversed right sequence.
            vb[idx] = x
            # Cache the furthest reverse reach on this diagonal.
            # This lets the forward pass compare against the correct end-side frontier.
            if x > n:
                # A reverse candidate beyond n means it is past the valid range.
                # We can discard it and continue searching the remaining diagonals.
                be += 2
                # Expand the backward search end boundary to avoid reprocessing stale states.
                # This helps keep the algorithm efficient even when many routes are invalid.
                continue
                # Skip this invalid reverse state.
            if y > m:
                # If the tail candidate is beyond the right sequence, it is invalid.
                # This needs to be skipped so we do not overestimate the final boundary.
                bs += 2
                # Expand the actual start boundary to keep the reverse wavefront in sync.
                # Without this, the loop could revisit the same invalid region repeatedly.
                continue
                # Continue scanning other possible reverse states.
            if not odd:
                # In even edit cases, the forward pass is enough to validate the midpoint.
                # This parity check ensures we only merge states when the search is consistent.
                kf = delta - k
                # Compute the corresponding forward diagonal index to compare with the reverse side.
                # This bridges the two halves of the algorithm.
                if -d <= kf <= d:
                    # Check whether the mirrored forward candidate is actually within the selected depth.
                    # If it is outside the range, it cannot possibly produce a valid midpoint.
                    xf = vf[offset + kf]
                    # Fetch the matching forward reach for that diagonal.
                    # This is the exact point where the two search directions meet.
                    if xf != -1 and xf + x >= n:
                        # If the meet condition is satisfied, a valid middle snake has been found.
                        # This means we can split the problem and recurse on smaller, simpler ranges.
                        return (n - x, m - y, n - x0, m - y0)
                        # Return the coordinates for the centered segment in the original orientation.
                        # These values tell the caller where to recurse on the left and right subproblems.
    raise RuntimeError('middle snake not found')
    # Raise an error only after all valid diagonals have been exhausted.
    # This means the search failed to find a valid split, which should never happen for a correct diff.
    # If this error triggers, it usually points to a logic bug rather than a data problem.


def diff_marks(a, b):
    # Identify which items are deleted from the left side and inserted on the right side.
    # This output becomes the mask used later to produce the final diff view.
    # Without this step, the algorithm would only know that files differ, not where each change starts and ends.
    na = len(a)
    # Save the length of the left sequence as the number of items in A.
    # This is needed later when translating filtered diff positions back to original positions.
    nb = len(b)
    # Save the length of the right sequence as the number of items in B.
    # This lets us build the insertion mask with the same original indexing.
    ids = {}
    # Build a mapping from distinct values to small integer IDs.
    # This compresses equal items into a shared representation so equality checking is efficient.
    ia = []
    # Store the compact IDs for each item in the left sequence.
    ib = []
    # Store the compact IDs for each item in the right sequence.
    for item in a:
        # Scan every item in the original left sequence.
        value = ids.get(item)
        # Check whether this value has already been assigned a compact ID.
        # This avoids creating multiple IDs for the same item and keeps matches stable.
        if value is None:
            # If this is the first time we have seen the value, assign a new ID.
            value = len(ids)
            # Use the current map size so IDs stay compact and deterministic.
            ids[item] = value
            # Save the new mapping so later occurrences in either sequence reuse the same ID.
        ia.append(value)
        # Append the compact ID to the left-side list.
        # This turns the original sequence into a normalized integer sequence for matching.
    for item in b:
        # Repeat the same canonicalization for the items on the right.
        value = ids.get(item)
        # Reuse an existing ID when the item already exists in A; otherwise create one on demand.
        # This is important because a match across both lists is based on the same identity number.
        if value is None:
            # Create the ID for a new unique item only when it has not already appeared.
            value = len(ids)
            # The counter continues from the existing size so both sequences share one global ID space.
            ids[item] = value
            # Save the mapping for later reuse.
        ib.append(value)
        # Append the right-side compact ID so both sequences align by value identity.
    in_a = set(ia)
    # Build the set of left-side values that exist in A.
    # This lets us keep only the values that are relevant for intersection-based filtering.
    in_b = set(ib)
    # Build the set of right-side values that exist in B.
    # This is the mirror of the previous step for the matching side.
    ma = [i for i, value in enumerate(ia) if value in in_b]
    # Keep only positions in A that correspond to an item also present in B.
    # This filters out values that cannot match anywhere in the other sequence.
    mb = [j for j, value in enumerate(ib) if value in in_a]
    # Keep only positions in B that correspond to an item also present in A.
    # This creates the mirrored subset needed for efficient diffing.
    fa = [ia[i] for i in ma]
    # Convert the filtered left indices back into their compact IDs.
    # This produces the actual candidate values that are comparable against the right half.
    fb = [ib[j] for j in mb]
    # Convert the filtered right indices back into their compact IDs.
    # This keeps both sequences aligned on the same identity scheme.
    del_f = bytearray(len(fa))
    # Allocate a byte array for the left-side delete mask.
    # Each byte records whether a filtered left item should be deleted in the remaining diff.
    ins_f = bytearray(len(fb))
    # Allocate a byte array for the right-side insert mask.
    # Each byte records whether a filtered right item should be inserted in the remaining diff.
    stack = [(0, len(fa), 0, len(fb))]
    # Start with one remaining subproblem covering the full filtered ranges.
    # This stack-based recursion is how the algorithm breaks large diffs into smaller independent pieces.
    while stack:
        # Continue until every remaining segment has been reduced to exact matches or deletions/insertions.
        a0, a1, b0, b1 = stack.pop()
        # Pop the next subrange to solve.
        # Each tuple holds the left and right boundaries of the currently unresolved diff chunk.
        while a0 < a1 and b0 < b1 and (fa[a0] == fb[b0]):
            # Skip over the matching prefix shared by both halves.
            # This eliminates the parts that do not need to change and reduces the remaining work.
            a0 += 1
            # Advance the left boundary to the first unresolved item.
            b0 += 1
            # Advance the right boundary in the same way so the sequences stay aligned.
        while a0 < a1 and b0 < b1 and (fa[a1 - 1] == fb[b1 - 1]):
            # Skip over the matching suffix shared by both halves.
            # This is a cheap optimization that removes common tail elements before we recurse deeper.
            a1 -= 1
            # Shrink the left range from the right side.
            b1 -= 1
            # Shrink the right range from the right side to keep the remaining segments aligned.
        if a0 == a1:
            # If the left side has no unresolved elements, the remaining difference is purely insertion.
            if b0 < b1:
                # Only add an insert marker when a right-side range still needs to appear.
                ins_f[b0:b1] = b'\x01' * (b1 - b0)
                # Mark every remaining item in that right-side range as inserted.
                # This identifies exactly which lines were added to the new version.
            continue
            # Continue to the next unresolved subproblem.
        if b0 == b1:
            # If the right side has no unresolved elements, the difference is purely deletion.
            del_f[a0:a1] = b'\x01' * (a1 - a0)
            # Mark every remaining left-side item as deleted.
            # This tells us which lines were removed from the old version.
            continue
            # Continue to the next segment after recording the deletion range.
        A = fa[a0:a1]
        # Extract the remaining left segment to compare against the right segment.
        B = fb[b0:b1]
        # Extract the remaining right segment to compare against the left segment.
        n = a1 - a0
        # Record the left subproblem length.
        m = b1 - b0
        # Record the right subproblem length.
        Ar = A[::-1]
        # Reverse the left segment so the algorithm can search from the end.
        Br = B[::-1]
        # Reverse the right segment to mirror the backward search.
        A.append(-1)
        # Add a sentinel to the left segment so the search can detect the boundary cleanly.
        B.append(-2)
        # Add a different sentinel to the right segment so the searches do not accidentally merge.
        Ar.append(-1)
        # Add the left-sentinel for the reversed view as well.
        Br.append(-2)
        # Add the right-sentinel for the reversed view as well.
        sx, sy, ex, ey = middle_snake(A, B, Ar, Br, n, m)
        # Ask Myers' midpoint routine for the exact split coordinates.
        # The returned values tell us how much of each side belongs to the left and right halves of the split.
        stack.append((a0 + ex, a1, b0 + ey, b1))
        # Push the right-side chunk so it is solved after the left-side chunk.
        # This keeps recursion ordered so the algorithm respects the discovered midpoint.
        stack.append((a0, a0 + sx, b0, b0 + sy))
        # Push the left-side chunk before the right-side chunk to maintain a consistent decomposition.
        # If we reversed their order or ignored the split, we could produce a wrong diff layout.
    del_a = bytearray(b'\x01') * na
    # Start with all left-side items marked as changed.
    # This default makes the final mask explicit, and then we overwrite only the unchanged positions.
    ins_b = bytearray(b'\x01') * nb
    # Start with all right-side items marked as changed.
    # This makes the default insertion mask conservative until we refine it with the actual diff.
    for filtered_index, original_index in enumerate(ma):
        # Map each filtered left-side index back to the original left index.
        del_a[original_index] = del_f[filtered_index]
        # Restore the actual delete mask value for the original item.
        # If we did not do this remapping, the mask would be based on filtered positions instead of real file positions.
    for filtered_index, original_index in enumerate(mb):
        # Map each filtered right-side index back to the original right index.
        ins_b[original_index] = ins_f[filtered_index]
        # Restore the actual insertion mask value for the original item.
        # This ensures insertions are reported in the correct file positions.
    return (del_a, ins_b)
    # Return the mark arrays that tell where deletions and insertions happen.
    # These arrays are the essential data for the final rendering pass.


def ranges(marks):
    # Turn a binary change mask into a human-readable range string.
    # Example: 101100 becomes "1-3,5-6" so a UI can show the modified spans clearly.
    # Without this conversion, the diff would be a raw bit pattern and not easily readable.
    n = len(marks)
    # Record the number of marks so we know the array's end boundary.
    parts = []
    # Store each contiguous changed range as text.
    start = marks.find(1)
    # Find the first changed position in the mask.
    # If there are no changes, the function will return -1 and the loop ends immediately.
    while start != -1:
        # Keep scanning while there are still changed positions left.
        end = marks.find(0, start)
        # Find the next unchanged position after the current change block.
        # The end of the current range is the index right before the zero,
        # which means the changed block is [start, end).
        if end == -1:
            # If no zero appears after the start, the block runs to the end of the list.
            end = n
            # Use the array length as the logical end of the final range.
        parts.append(f'{start}-{end}')
        # Store the contiguous range in a compact start-end format.
        # This is easier to read than a long list of positions.
        if end >= n:
            # Stop once we have reached the array end.
            # Breaking here prevents an infinite loop when the final block extends to the end.
            break
            # End the loop because there is no remaining range to evaluate.
        start = marks.find(1, end)
        # Continue searching for the next changed position after the current block.
        # This loops through every modified segment without missing any sections.
    return ','.join(parts) if parts else '.'
    # Return a comma-separated list of ranges when changes exist.
    # If nothing changed, return a single dot to signal the empty case cleanly.


def build_output(a, b, del_a, ins_b, highlight):
    # Assemble the final diff output with unchanged lines, deletions, insertions, and optional highlights.
    # This is the last rendering step that turns the masks into the final byte stream for the CLI.
    # Without this step, the algorithm would only compute internal masks instead of visible changes.
    na = len(a)
    # Record the length of the original left file.
    nb = len(b)
    # Record the length of the new right file.
    out = []
    # Collect the final output lines in a list before writing them once.
    i = j = 0
    # i tracks the current index in the old file; j tracks the current index in the new file.
    # These pointers let the function march through both files in lockstep while producing output.
    while True:
        # Keep processing until both arrays are fully consumed.
        next_delete = del_a.find(1, i)
        # Find the next deletion marker in the old sequence.
        # This tells us where the next changed block begins in the left file.
        next_insert = ins_b.find(1, j)
        # Find the next insertion marker in the new sequence.
        # This tells us where the next changed block begins in the right file.
        if next_delete == -1 and next_insert == -1:
            # If both arrays no longer contain changes, the remaining content is unchanged.
            break
            # Stop the loop; there is nothing more to render.
        count = na - i
        # Start with the maximum number of unchanged lines remaining in A.
        # We will later shrink this as needed to avoid crossing the next change.
        if next_delete != -1:
            # If a deletion begins before the next insertion, limit the unchanged window to that delete start.
            count = min(count, next_delete - i)
            # This keeps only the unchanged prefix before the deletion boundary.
        if next_insert != -1:
            # If an insertion begins earlier than the delete boundary, limit the unchanged window to that insertion start.
            count = min(count, next_insert - j)
            # This keeps the unchanged lines aligned to both sequences.
        if count:
            # Emit unchanged lines only when there is a non-zero window to print.
            out.extend((b' ' + line for line in a[i:i + count]))
            # Prefix each preserved line with a space so diff output remains aligned with changed lines.
            # If we did not do this, unchanged content would not visibly separate from added and removed lines.
            i += count
            # Move the old pointer past the preserved block.
            j += count
            # Move the new pointer past the preserved block.
        delete_end = del_a.find(0, i)
        # Find the end of the current deletion block in the old sequence.
        # The first zero marks the first unchanged line after the removed region.
        if delete_end == -1:
            # If no zero exists, the deletion block reaches the end of the old file.
            delete_end = na
            # Use the end of the file as the final boundary.
        insert_end = ins_b.find(0, j)
        # Find the end of the current insertion block in the new sequence.
        # This gives the inserted region's clear end on the right side.
        if insert_end == -1:
            # If no zero exists, the insertion block reaches the end of the new file.
            insert_end = nb
            # Use the end of the file as the final boundary.
        deleted = a[i:delete_end]
        # Extract the actual lines deleted from the old sequence.
        inserted = b[j:insert_end]
        # Extract the actual lines inserted into the new sequence.
        out.extend((b'-' + line for line in deleted))
        # Emit each deleted line with a minus prefix.
        # This lets the user immediately see what was removed.
        if not highlight:
            # In plain diff mode, we only mark deletions and insertions without extra analysis.
            out.extend((b'+' + line for line in inserted))
            # Emit inserted lines with a plus prefix.
            # This produces a standard minimal diff view without any inline highlight commentary.
        else:
            # In highlight mode, we add a second annotation line for each inserted line.
            # This helps explain the textual changes in more detail.
            paired = min(len(deleted), len(inserted))
            # Compare only the number of lines that can be matched by position.
            # This keeps the highlight logic from indexing beyond the shorter list.
            for index, line in enumerate(inserted):
                # Walk each inserted line so we can pair it with its nearest deleted counterpart when possible.
                out.append(b'+' + line)
                # Emit the inserted line first so the viewer sees the new content.
                if index < paired:
                    # Only compare pairs while both lists still have an item at this index.
                    old = deleted[index].decode('utf-8', 'surrogateescape')
                    # Decode the left-side line to text so we can diff it precisely.
                    # We use surrogateescape to preserve any odd bytes without crashing the program.
                    new = line.decode('utf-8', 'surrogateescape')
                    # Decode the inserted line the same way so both sides are comparable.
                    deleted_marks, inserted_marks = diff_marks(old, new)
                    # Run the same diff algorithm on the two small strings to highlight the character-level changes.
                    # This is useful because it explains which parts inside a line changed, not just the full-line insert/delete.
                    marker = f'? {ranges(deleted_marks)} | {ranges(inserted_marks)}'.encode('utf-8')
                    # Convert the character-level ranges into a compact marker string.
                    # This indicates the changed spans on the old and new versions of the line.
                    out.append(marker)
                    # Append the commentary line right after the inserted line.
                    # This gives users a quick hint about the actual internal text change.
        i = delete_end
        # Advance the old pointer to the first unchanged item after the deletion block.
        j = insert_end
        # Advance the new pointer to the first unchanged item after the insertion block.
    if i < na:
        # If any unchanged lines remain at the end of the old file, print them now.
        out.extend((b' ' + line for line in a[i:]))
        # Preserve the final tail of the original file with a leading space.
        # Without this, the last lines of the file would be omitted from the final output.
    return out
    # Return the final byte stream ready to print to stdout.
    # This is the end product of the diff algorithm and the final user-visible result.


def main():
    # Parse the command-line arguments and orchestrate the whole diff process.
    # This is the entry point where the user chooses between plain line output and highlighted output.
    # Without this, the program would not know which mode to run or which files to compare.
    if len(sys.argv) != 4:
        # The program expects exactly three arguments after the script name: mode, file A, file B.
        # If the user provides any other number, the input is invalid and we must reject it.
        print('usage: main.py lines|highlight A_PATH B_PATH', file=sys.stderr)
        # Print the expected usage description to stderr so the user sees the correct command format.
        # The error goes to stderr instead of stdout because it is a failure message, not program output.
        return 2
        # Return a nonzero exit code to signal an invalid command invocation.
    command = sys.argv[1]
    # Read the selected mode from the first argument.
    # This chooses between a plain diff and the more detailed highlight mode.
    if command not in ('lines', 'highlight'):
        # Validate the selected mode so the program rejects unsupported commands explicitly.
        # Without this, bad input could silently run the wrong branch or crash later.
        print('usage: main.py lines|highlight A_PATH B_PATH', file=sys.stderr)
        # Show the same usage message again to keep the interface consistent.
        return 2
        # Return a failure code because the user requested an unsupported operation.
    try:
        # Wrap file reads in a try block so file access errors are reported cleanly.
        a = read_lines(sys.argv[2])
        # Load the first file as a sequence of raw lines.
        # This gives the diff engine the original content to compare against the second file.
        b = read_lines(sys.argv[3])
        # Load the second file in the same manner so both sides share the same representation.
    except OSError as exc:
        # Catch file-related problems like missing files or unreadable paths.
        # Without this guard, the program would crash with a traceback instead of a helpful message.
        print(f'error: cannot read file: {exc}', file=sys.stderr)
        # Print a concise error showing the underlying operating-system problem.
        # This helps the user understand what prevented the diff from running.
        return 2
        # Return a failure code to indicate the operation could not complete.
    del_a, ins_b = diff_marks(a, b)
    # Compute the exact deletion and insertion masks for the two input files.
    # These masks are the heart of the algorithm and tell exactly which regions differ.
    output = build_output(a, b, del_a, ins_b, command == 'highlight')
    # Turn the masks into the final human-readable diff output.
    # If the command is highlight, we include extra annotations; otherwise we use the standard line diff format.
    if output:
        # Only write output if there is something to show.
        # This avoids printing a blank newline when the files are exactly identical.
        sys.stdout.buffer.write(b'\n'.join(output) + b'\n')
        # Write the finished diff lines to stdout as bytes.
        # Joining with newlines ensures each diff record is clearly separated.
        sys.stdout.buffer.flush()
        # Force the bytes to be sent immediately so the output is visible to the caller.
    return 0
    # Return zero to signal successful completion.
    # This is the standard success code expected by shell scripts and automation.
if __name__ == '__main__':
    # Guard the script so it runs only when invoked directly.
    # This prevents imported modules from executing the CLI logic unexpectedly.
    raise SystemExit(main())
    # Exit with the return code from main().
    # This is the standard Python pattern for CLI entry points and lets the script behave like a command-line tool.