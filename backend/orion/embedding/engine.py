"""Semantic vector engine — BGE-small-en-v1.5 via ONNX Runtime (no PyTorch).

Uses the pre-exported ONNX model from HuggingFace + onnxruntime for
CPU inference. HuggingFace tokenizer handles text tokenization.

The ONNX session and tokenizer are cached as module-level singletons,
loaded on first use.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_ONNX_MODEL_NAME = "xenova/bge-small-en-v1.5"  # Has pre-exported ONNX files
_EMBEDDING_DIM = 384

# Module-level singletons
_TOKENIZER = None
_SESSION = None


def _download_onnx_model() -> Path:
    """Download the pre-exported ONNX model from HuggingFace.

    Uses the xenova/bge-small-en-v1.5 repo which has ONNX files already.

    Returns:
        Path to the downloaded model.onnx file.
    """
    from huggingface_hub import hf_hub_download

    # Download the ONNX model file
    model_path = hf_hub_download(
        repo_id=_ONNX_MODEL_NAME,
        filename="onnx/model.onnx",
    )
    logger.info("ONNX model downloaded to %s", model_path)
    return Path(model_path)


def _get_tokenizer():
    """Lazy-load the tokenizer."""
    global _TOKENIZER
    if _TOKENIZER is None:
        from transformers import AutoTokenizer

        _TOKENIZER = AutoTokenizer.from_pretrained(_MODEL_NAME)
        logger.info("Tokenizer loaded for %s", _MODEL_NAME)
    return _TOKENIZER


def _get_session():
    """Lazy-load the ONNX Runtime inference session."""
    global _SESSION
    if _SESSION is None:
        import onnxruntime as ort

        onnx_path = _download_onnx_model()
        _SESSION = ort.InferenceSession(
            str(onnx_path),
            providers=["CPUExecutionProvider"],
        )
        logger.info("ONNX session created")
    return _SESSION


def _mean_pooling(
    token_embeddings: np.ndarray, attention_mask: np.ndarray
) -> np.ndarray:
    """Apply mean pooling to token embeddings, respecting the attention mask."""
    mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(np.float32)
    sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
    sum_mask = np.clip(np.sum(mask_expanded, axis=1), a_min=1e-9, a_max=None)
    return sum_embeddings / sum_mask


def _normalize(embeddings: np.ndarray) -> np.ndarray:
    """L2-normalize embedding vectors."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.clip(norms, a_min=1e-9, a_max=None)
    return embeddings / norms


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def embed_text(text: str) -> list[float]:
    """Embed a single text string into a 384-dim vector.

    Args:
        text: Input text to embed.

    Returns:
        List of 384 floats (the embedding vector).
    """
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a batch.

    Args:
        texts: List of input text strings.

    Returns:
        List of embedding vectors (each 384 floats).
    """
    if not texts:
        return []

    tokenizer = _get_tokenizer()
    session = _get_session()

    # Tokenize
    encoded = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="np",
    )

    # Prepare ONNX inputs
    input_ids = encoded["input_ids"].astype(np.int64)
    attention_mask = encoded["attention_mask"].astype(np.int64)

    # Check which inputs the model expects
    input_names = {inp.name for inp in session.get_inputs()}
    onnx_inputs = {"input_ids": input_ids, "attention_mask": attention_mask}

    if "token_type_ids" in input_names:
        token_type_ids = np.zeros_like(input_ids, dtype=np.int64)
        onnx_inputs["token_type_ids"] = token_type_ids

    # Run inference
    outputs = session.run(None, onnx_inputs)

    # outputs[0] is last_hidden_state: (batch, seq_len, hidden_dim)
    token_embeddings = outputs[0]

    # Mean pooling + L2 normalize
    pooled = _mean_pooling(token_embeddings, attention_mask.astype(np.float32))
    normalized = _normalize(pooled)

    return normalized.tolist()


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Since embeddings are L2-normalized, cosine similarity equals dot product.

    Args:
        vec_a: First embedding vector.
        vec_b: Second embedding vector.

    Returns:
        Cosine similarity score in [-1, 1]. Higher = more similar.
    """
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    dot = float(np.dot(a, b))
    return max(-1.0, min(1.0, dot))


def semantic_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute semantic similarity between two embedding vectors.

    Wraps cosine_similarity with a floor at 0.0, providing an explicit
    [0, 1] contract for requirement-traceability scoring. Negative cosine
    values (semantically opposed texts) are mapped to 0.0 rather than
    being silently lost via ad-hoc clamping scattered across callers.

    Args:
        vec_a: First embedding vector.
        vec_b: Second embedding vector.

    Returns:
        Semantic similarity score in [0, 1]. Higher = more similar.
    """
    return max(0.0, cosine_similarity(vec_a, vec_b))


def get_embedding_dim() -> int:
    """Return the embedding dimensionality (384 for BGE-small-en-v1.5)."""
    return _EMBEDDING_DIM
