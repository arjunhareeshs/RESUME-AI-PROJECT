# eval/evaluator.py
from typing import Tuple
import re
from rapidfuzz.distance import Levenshtein
import math

def normalize_text(t: str) -> str:
    # lowercase, collapse whitespace, remove non-printables
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def char_error_rate(ref: str, hyp: str) -> float:
    """
    CER = edit_distance(chars) / len(ref)
    0.0 is perfect, 1.0 is completely different
    """
    r = normalize_text(ref)
    h = normalize_text(hyp)
    dist = Levenshtein.distance(r, h)
    denom = max(1, len(r))
    return dist / denom

def word_error_rate(ref: str, hyp: str) -> float:
    """
    WER = edit_distance(words) / #words_in_ref
    Uses Levenshtein on tokens.
    """
    r = normalize_text(ref).split()
    h = normalize_text(hyp).split()
    # Map tokens to single chars to use Levenshtein efficiently for lists
    # But rapidfuzz Levenshtein supports sequences. We'll compute distance by dynamic programming:
    # Use simple DP Levenshtein for lists:
    m, n = len(r), len(h)
    if m == 0:
        return 0.0 if n == 0 else 1.0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if r[i - 1] == h[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1,      # deletion
                           dp[i][j - 1] + 1,      # insertion
                           dp[i - 1][j - 1] + cost)  # substitution
    wer = dp[m][n] / m
    return wer

def normalized_levenshtein(ref: str, hyp: str) -> float:
    r = normalize_text(ref)
    h = normalize_text(hyp)
    dist = Levenshtein.distance(r, h)
    max_len = max(1, len(r), len(h))
    return 1.0 - (dist / max_len)  # 1.0 is perfect match, 0.0 is worst

def token_overlap(ref: str, hyp: str) -> float:
    r = set(normalize_text(ref).split())
    h = set(normalize_text(hyp).split())
    if not r:
        return 0.0
    inter = r.intersection(h)
    return len(inter) / len(r)

def evaluate_pair(ref_text: str, hyp_text: str) -> dict:
    cer = char_error_rate(ref_text, hyp_text)
    wer = word_error_rate(ref_text, hyp_text)
    lev_score = normalized_levenshtein(ref_text, hyp_text)
    overlap = token_overlap(ref_text, hyp_text)
    return {
        "CER": cer,
        "WER": wer,
        "Normalized_Levenshtein": lev_score,
        "Token_Overlap": overlap
    }
