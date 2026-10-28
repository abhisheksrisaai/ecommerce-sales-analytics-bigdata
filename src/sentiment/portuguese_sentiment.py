#!/usr/bin/env python3
"""Portuguese review-text sentiment analysis for the Olist e-commerce dataset.

This module implements a transparent, lexicon-based sentiment scorer for
Portuguese customer reviews. It does not depend on any pretrained model or
large download; instead it uses a curated Portuguese word list and handles
text normalisation, negation and negative bigrams.

The output scores are normalised to the range [-1, 1] and can be aggregated
per product or per order.

Inputs:
    Raw review comment strings from `olist_order_reviews_dataset.csv`.

Outputs:
    Float sentiment scores in [-1, 1]; aggregated statistics via
    `aggregate_sentiment()` and `review_stats()`.

Dependencies:
    - Python standard library only (re, unicodedata).
    - pandas (only for `review_stats`).

Called from:
    src.recommender.loader_and_recommender (product-level sentiment attribution)
    tests.test_sentiment
"""
import re
import unicodedata


# ---------------------------------------------------------------------------
# Portuguese sentiment lexicon (lower-case, accent-free forms)
# ---------------------------------------------------------------------------
POSITIVE_WORDS = {
    "bom", "boa", "bons", "boas", "otimo", "otima", "otimos", "otimas",
    "excelente", "excelentes", "perfeito", "perfeita", "perfeitos", "perfeitas",
    "maravilhoso", "maravilhosa", "maravilhosos", "maravilhosas",
    "incrivel", "incriveis", "fantastico", "fantastica", "fantasticos", "fantasticas",
    "adorei", "adoramos", "adoro", "amei", "amamos", "amo",
    "gostei", "gostamos", "gosto", "gostou", "gostaram",
    "recomendo", "recomendamos", "recomendavel", "recomendado",
    "rapido", "rapida", "rapidos", "rapidas", "agil", "ageis",
    "eficiente", "eficientes", "pratico", "pratica", "praticos", "praticas",
    "bonito", "bonita", "bonitos", "bonitas", "lindo", "linda", "lindos", "lindas",
    "util", "uteis", "satisfatorio", "satisfatoria", "satisfatorios", "satisfatorias",
    "satisfeito", "satisfeita", "satisfeitos", "satisfeitas",
    "conforme", "esperado", "correto", "correta", "corretos", "corretas",
    "facil", "faceis", "simples", "confiavel", "confiaveis",
    "maravilha", "show", "top", "legal", "bacana",
    "antes", "prazo", "antecipado", "cedo",
}

NEGATIVE_WORDS = {
    "ruim", "ruins", "pessimo", "pessima", "pessimos", "pessimas",
    "horrivel", "horriveis", "terrivel", "terriveis",
    "defeito", "defeituoso", "defeituosa", "defeituosos", "defeituosas",
    "quebrado", "quebrada", "quebrados", "quebradas", "estragado", "estragada",
    "atrasado", "atrasada", "atrasados", "atrasadas", "demorou", "demora", "demorado",
    "problema", "problemas", "dificuldade", "dificuldades",
    "insatisfeito", "insatisfeita", "insatisfeitos", "insatisfeitas",
    "decepcionado", "decepcionada", "decepcionados", "decepcionadas",
    "triste", "chateado", "chateada", "chateados", "chateadas",
    "nao", "nem", "nunca", "jamais", "ninguem", "nada",
    "nao gostei", "nao recomendo", "nao chegou", "nao veio", "nao funciona",
    "errado", "errada", "errados", "erradas", "faltou", "falta", "faltando",
    "pior", "piorou", "fraco", "fraca", "fracos", "fracas",
    "devolucao", "devolver", "trocar", "troca", "reclamacao",
    "ruindade", "enganosa", "enganoso", "propaganda enganosa",
}

NEGATORS = {"nao", "nem", "nunca", "jamais", "sem", "ninguem", "nada"}

# Bigrams that flip or strengthen sentiment
NEGATIVE_BIGRAMS = {
    "nao gostei", "nao recomendo", "nao chegou", "nao veio",
    "nao funciona", "nao gosto", "nao adorei", "nao amei",
    "nao util", "nao conforme",
}


def normalise(text):
    """Normalise raw Portuguese text for lexicon matching.

    The normalisation steps are:
    1. Convert to lower case.
    2. Remove accents using Unicode NFKD decomposition.
    3. Replace punctuation and special characters with spaces.
    4. Collapse multiple spaces and strip leading/trailing whitespace.

    Parameters
    ----------
    text : str or any
        Raw review comment. Non-string inputs return an empty string.

    Returns
    -------
    str
        Lower-case, accent-free, punctuation-cleaned text.
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ASCII")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_text(text):
    """Return a sentiment score in [-1, 1] for a single Portuguese text.

    The scorer uses the curated `POSITIVE_WORDS` and `NEGATIVE_WORDS` lexicons.
    Negation is handled by looking up to two words before a sentiment word for
    a negator in `NEGATORS`. Explicit negative bigrams such as "nao gostei"
    receive a stronger negative weight.

    Parameters
    ----------
    text : str
        Portuguese review comment.

    Returns
    -------
    float or None
        Sentiment score in [-1, 1], or None if the input is empty or not a
        string.
    """
    text = normalise(text)
    if not text:
        return None

    words = text.split()
    pos = 0
    neg = 0

    # Count bigrams first to catch negated expressions
    for bigram in NEGATIVE_BIGRAMS:
        if bigram in text:
            neg += 2

    for i, word in enumerate(words):
        if word in NEGATIVE_BIGRAMS:
            continue  # already counted above
        if word in POSITIVE_WORDS:
            # Check preceding negator within a 2-word window
            window = words[max(0, i - 2):i]
            if any(w in NEGATORS for w in window):
                neg += 1
            else:
                pos += 1
        elif word in NEGATIVE_WORDS:
            pos_window = words[max(0, i - 2):i]
            if any(w in NEGATORS for w in pos_window):
                pos += 1
            else:
                neg += 1

    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def aggregate_sentiment(texts):
    """Aggregate sentiment over an iterable of texts.

    Parameters
    ----------
    texts : iterable of str
        Review comments to score.

    Returns
    -------
    dict
        {
            "mean": mean sentiment score (float),
            "count": number of scored texts (int),
            "coverage": same as count (int, kept for backward compatibility)
        }
        Returns zeros and count 0 when no scorable text is found.
    """
    scores = [s for t in texts if (s := score_text(t)) is not None]
    if not scores:
        return {"mean": 0.0, "count": 0, "coverage": 0}
    return {
        "mean": round(sum(scores) / len(scores), 4),
        "count": len(scores),
        "coverage": len(scores),
    }


def review_stats(reviews_df, text_col="review_comment_message"):
    """Add sentiment columns to a reviews DataFrame.

    Parameters
    ----------
    reviews_df : pandas.DataFrame
        DataFrame containing review text.
    text_col : str, optional
        Name of the column holding review comments. Default is
        "review_comment_message".

    Returns
    -------
    pandas.DataFrame
        Copy of `reviews_df` with added columns:
        - `sentiment_score`: float score in [-1, 1] (None for empty text).
        - `has_text`: boolean indicating a non-empty comment.

    Raises
    ------
    KeyError
        If `text_col` is not present in `reviews_df`.
    """
    import pandas as pd

    if text_col not in reviews_df.columns:
        raise KeyError(f"Reviews DataFrame is missing required column: {text_col}")

    df = reviews_df.copy()
    scores = []
    for text in df[text_col]:
        scores.append(score_text(text))
    df["sentiment_score"] = scores
    df["has_text"] = df[text_col].notna() & (df[text_col].astype(str).str.strip() != "")
    return df
