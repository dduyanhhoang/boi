"""Align gold ARPAbet to gold Vietnamese, and count what maps to what.

This is the check on phonemap, not a step in generation. The syllabifier says
which English phones belong to which slot; the aligner lines those slots up
against the gold syllables and records the Vietnamese piece the native speaker
actually used. Where the table's first choice differs from the gold's most
common piece, the table is wrong or the word is lexical.

Syllable counts differ when the repair guesses wrong, so the two sequences are
matched by edit distance over syllables rather than by position.
"""

import collections

from . import g2p, syllabify, vi


def _align(slots, gold):
    """Monotonic match between slots and gold syllables, as index pairs."""
    n, m = len(slots), len(gold)
    # cost[i][j] = cheapest way to match slots[:i] against gold[:j]
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i
    for j in range(1, m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost[i][j] = min(cost[i - 1][j] + 1, cost[i][j - 1] + 1, cost[i - 1][j - 1])
    pairs = []
    i, j = n, m
    while i and j:
        if cost[i][j] == cost[i - 1][j - 1]:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif cost[i][j] == cost[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return list(reversed(pairs))


def counts(rows):
    """{(phone, role): Counter(vietnamese piece)} over gold rows."""
    table = collections.defaultdict(collections.Counter)
    skipped = []
    for row in rows:
        phones = g2p.phones(row["word"])
        variants = syllabify.variants(phones) if phones else []
        if not variants:
            skipped.append(row["word"])
            continue
        slots = variants[0][0]
        try:
            gold = vi.parse_word(row["vi_form"])
        except ValueError:
            skipped.append(row["word"])
            continue
        for si, gi in _align(slots, gold):
            slot, syl = slots[si], gold[gi]
            if slot.inserted:
                table[("(inserted)", "nucleus")][syl.nucleus] += 1
                continue
            key = slot.onset[-1] if slot.onset else "(none)"
            table[(key, "onset")][syl.onset] += 1
            table[(slot.nucleus, "nucleus")][syl.nucleus + ("+" + syl.coda if
                                                           syl.coda in "iyuo" and syl.coda else "")] += 1
            if slot.coda:
                table[("+".join(slot.coda), "coda")][syl.coda or "(drop)"] += 1
    return table, skipped
