"""
Local text embeddings for legal-section retrieval (Week 2, Track A).

Uses the sentence-transformer ``all-MiniLM-L6-v2`` (384 dimensions), run fully
locally — no external API. The model is loaded lazily and cached, and is baked
into the Docker image (see Dockerfile) so the first request needs no download.

Embeddings are L2-normalized, so cosine similarity == dot product and pgvector's
CosineDistance behaves predictably.
"""
from functools import lru_cache

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def get_model():
    # Imported lazily so importing this module (and Django startup) doesn't pull
    # in torch unless embeddings are actually used.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """Embed a single string -> 384-float list."""
    return embed_texts([text])[0]


def embed_texts(texts) -> list[list[float]]:
    """Embed a list of strings -> list of 384-float lists."""
    vectors = get_model().encode(
        list(texts),
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectors]


def section_embedding_text(section) -> str:
    """The text we embed for a LegalSection: title + body.

    The title ("Theft.", "House-trespass.") carries strong signal, so we prepend
    it to the verbatim section text before embedding.
    """
    title = (section.title or "").strip()
    body = (section.text or "").strip()
    return f"{title}\n{body}".strip()
