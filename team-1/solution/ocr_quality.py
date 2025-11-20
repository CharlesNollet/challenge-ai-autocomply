from __future__ import annotations

import re
from typing import Tuple

try:
    from langdetect import detect_langs  # type: ignore
except Exception:
    detect_langs = None  # type: ignore

BAD_CHARS = set("\uFFFD�\x00□■▯▢▣▤▥▦▧▨▩▪▫●○•◦·¤§")

_vowel_re = re.compile(r"[aeiouyàâäéèêëîïôöùûüÿœæAEIOUYÀÂÄÉÈÊËÎÏÔÖÙÛÜŸŒÆ]")
_word_re = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}")


def _alnum_ratio(text: str) -> float:
    if not text:
        return 0.0
    clean = re.sub(r"\s+", " ", text)
    return sum(c.isalnum() for c in clean) / max(1, len(clean))


def _lang_score(text: str, expected=("en", "fr")) -> float:
    if not detect_langs or len(text) < 80:
        return 1.0
    try:
        probs = detect_langs(text[:2000])
    except Exception:
        return 0.0
    return max((p.prob for p in probs if p.lang in expected), default=0.0)


def score_text_quality(text: str) -> float:
    """
    Compute a 0-100 OCR/text quality score. Higher is better.
    """
    if not text or not text.strip():
        return 0.0

    n = len(text)
    printable_ratio = sum(1 for c in text if c.isprintable()) / n
    alpha_ratio = sum(1 for c in text if c.isalpha()) / n
    bad_ratio = sum(1 for c in text if c in BAD_CHARS) / n

    tokens = _word_re.findall(text)
    vowel_ratio = (
        (sum(1 for t in tokens if _vowel_re.search(t)) / max(1, len(tokens)))
        if tokens
        else 0.0
    )
    avg_token_len = (sum(len(t) for t in tokens) / len(tokens)) if tokens else 0.0
    token_score = (min(1.0, avg_token_len / 5.0) * 0.5) + (vowel_ratio * 0.5)

    length_score = min(1.0, n / 300.0)
    alnum = _alnum_ratio(text)
    lang = _lang_score(text)

    raw = (
        0.25 * length_score +
        0.20 * alnum +
        0.20 * alpha_ratio +
        0.15 * token_score +
        0.10 * printable_ratio +
        0.10 * lang -
        0.30 * bad_ratio
    )
    return max(0.0, min(1.0, raw)) * 100.0


def needs_vision_fallback(text: str, threshold: float = 35.0) -> Tuple[bool, float]:
    """
    Decide if vision fallback is warranted. Returns (needs_fallback, quality_score).
    """
    # Early fast path: treat alnum-sparse pages as likely OCR failures
    if len((text or "").strip()) >= 100 and _alnum_ratio(text) < 0.50:
        return True, 0.0
    score = score_text_quality(text)
    return score < threshold, score


