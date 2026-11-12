"""Lab 3: report a score with a Wilson 95 percent confidence interval.

Run:  python lab3_wilson.py
Write the wilson() function. The checks at the bottom tell you when it is right.
"""
import math

Z = 1.96  # for a 95 percent interval


def wilson(k, n, z=Z):
    """Return (low, high) for k correct answers out of n, as fractions between 0 and 1."""
    # Answer. Hint given: p = k / n; centre = (p + z*z/(2*n)) / (1 + z*z/n); half = z * sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n); return centre - half, centre + half (clamp to 0 and 1)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def show(label, k, n):
    low, high = wilson(k, n)
    print(f"{label:28} {k:2} of {n}: {100 * k / n:5.1f}%  interval {100 * low:5.1f}% to {100 * high:5.1f}%")
    return low, high


if __name__ == "__main__":
    try:
        low, high = wilson(9, 40)
    except NotImplementedError:
        raise SystemExit("wilson() is not written yet. Open lab3_wilson.py and replace the TODO.")
    if not (abs(low - 0.123) < 0.001 and abs(high - 0.375) < 0.001):
        raise SystemExit(f"wilson(9, 40) should be about 0.123 to 0.375. Yours gives {low:.3f} to {high:.3f}.")
    if not (0.0 <= wilson(0, 40)[0] < 1e-9 and 1 - 1e-9 < wilson(40, 40)[1] <= 1.0):
        raise SystemExit("The interval must stay between 0 and 1. Clamp the two ends with max() and min().")
    print("wilson() passes its checks.\n")
    a = show("Scripted baseline in lab 2", 4, 10)
    b = show("Pair A on the validation set", 9, 40)
    c = show("Pair B on the validation set", 13, 40)
    overlap = b[1] >= c[0]
    print(f"\nPair A and pair B intervals {'overlap' if overlap else 'do not overlap'}.")
    print("Write one sentence: can pair B's model be called better on this evidence?")
