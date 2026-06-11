"""
Dense Retriever implementation using SentenceTransformers + ChromaDB.

Supports:
- Building a ChromaDB collection with bi-encoder embeddings
- Loading an existing collection for search
- Applying the BGE query instruction prefix automatically
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.retrieval.base import BaseRetriever
from src.schemas.retrieval import RetrievalResult
from src.utils.text_utils import apply_bge_query_prefix, clean_text

logger = logging.getLogger(__name__)


class DenseRetriever(BaseRetriever):
    """
    Retriever backed by dense bi-encoder embeddings stored in ChromaDB.

    The BGE query prefix (``"Represent this sentence for searching relevant
    passages: "``) is applied automatically to every query string.

    Args:
        chroma_path:      Directory where ChromaDB stores its data files.
        embedding_model:  SentenceTransformer model name or path.
        collection_name:  ChromaDB collection name.
    """

    def __init__(
        self,
        chroma_path: Path,
        embedding_model: str,
        collection_name: str = "books",
    ) -> None:
        self._chroma_path = Path(chroma_path)
        self._embedding_model_name = embedding_model
        self._collection_name = collection_name
        self._collection = None
        self._encoder = None

    @property
    def name(self) -> str:
        return "dense"

    def _get_encoder(self):
        """Lazy-load the SentenceTransformer model (avoids loading at import time).

        Model weights are cached in ``models/bge_cache/`` inside the project so
        subsequent runs load from local disk — no internet / API call needed.
        """
        if self._encoder is None:
            # Import here to allow the module to be imported without torch installed
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            # Resolve cache dir relative to project root (3 levels up from this file)
            _project_root = Path(__file__).resolve().parents[2]
            _cache_dir = _project_root / "models" / "bge_cache"
            _cache_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Loading SentenceTransformer '%s' (cache: %s)",
                self._embedding_model_name,
                _cache_dir,
            )
            self._encoder = SentenceTransformer(
                self._embedding_model_name,
                cache_folder=str(_cache_dir),
            )
        return self._encoder

    def _get_collection(self):
        """Lazy-load the ChromaDB collection."""
        if self._collection is None:
            import chromadb  # noqa: PLC0415
            from chromadb.config import Settings as ChromaSettings  # noqa: PLC0415
            client = chromadb.PersistentClient(
                path=str(self._chroma_path),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = client.get_collection(name=self._collection_name)
        return self._collection

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------
    @classmethod
    def build(
        cls,
        df: pd.DataFrame,
        chroma_path: Path,
        embedding_model: str,
        collection_name: str = "books",
        batch_size: int = 64,
    ) -> "DenseRetriever":
        """
        Encode the corpus and upsert embeddings into a ChromaDB collection.

        Args:
            df:               DataFrame with ``isbn13``, ``title``, ``description``,
                              ``authors``, ``categories``, ``average_rating``,
                              ``published_year``, and ``thumbnail`` columns.
            chroma_path:      Directory for ChromaDB persistence.
            embedding_model:  SentenceTransformer model name.
            collection_name:  ChromaDB collection name (created fresh).
            batch_size:       Number of documents encoded per forward pass.

        Returns:
            A ready-to-use ``DenseRetriever`` instance connected to the new collection.
        """
        import chromadb  # noqa: PLC0415
        from chromadb.config import Settings as ChromaSettings  # noqa: PLC0415
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        from tqdm import tqdm  # noqa: PLC0415

        logger.info(
            "Building dense index: %d documents with model '%s'",
            len(df),
            embedding_model,
        )

        chroma_path = Path(chroma_path)
        chroma_path.mkdir(parents=True, exist_ok=True)

        # Cache model locally inside the project so every pipeline step reuses
        # the same weights without hitting the HuggingFace Hub again.
        _project_root = Path(__file__).resolve().parents[2]
        _cache_dir = _project_root / "models" / "bge_cache"
        _cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Model cache dir: %s", _cache_dir)

        encoder = SentenceTransformer(embedding_model, cache_folder=str(_cache_dir))

        # Prepare documents (clean description used for corpus – no query prefix)
        descriptions = [clean_text(str(d)) for d in df["description"]]

        logger.info("Encoding %d descriptions in batches of %d…", len(descriptions), batch_size)
        embeddings = encoder.encode(
            descriptions,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

        # Connect to / reset ChromaDB
        client = chromadb.PersistentClient(
            path=str(chroma_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        try:
            client.delete_collection(collection_name)
            logger.info("Deleted existing collection '%s'", collection_name)
        except Exception:
            logger.warning("Collection '%s' did not exist and could not be deleted.", collection_name)

        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Prepare metadata for each document
        isbn_list = df["isbn13"].astype(str).tolist()
        metadatas = []
        for _, row in df.iterrows():
            metadatas.append(
                {
                    "title": str(row.get("title", "")),
                    "authors": str(row.get("authors", "")),
                    "categories": str(row.get("categories", "")),
                    "average_rating": float(row.get("average_rating", 0.0)),
                    "published_year": int(row.get("published_year", 0)),
                    "thumbnail": str(row.get("thumbnail", "")),
                }
            )

        # Upsert in batches
        upsert_batch_size = 500
        for start in tqdm(range(0, len(df), upsert_batch_size), desc="Upserting to ChromaDB"):
            end = min(start + upsert_batch_size, len(df))
            collection.upsert(
                ids=isbn_list[start:end],
                embeddings=embeddings[start:end].tolist(),
                documents=descriptions[start:end],
                metadatas=metadatas[start:end],
            )

        logger.info("Dense index built: %d documents in collection '%s'", len(df), collection_name)

        instance = cls(chroma_path, embedding_model, collection_name)
        instance._collection = collection
        instance._encoder = encoder
        return instance

    @classmethod
    def load(
        cls,
        chroma_path: Path,
        embedding_model: str,
        collection_name: str = "books",
    ) -> "DenseRetriever":
        """
        Connect to an existing ChromaDB collection (lazy – no data loaded yet).

        Args:
            chroma_path:     Directory containing ChromaDB data.
            embedding_model: SentenceTransformer model name (must match what was used to build).
            collection_name: ChromaDB collection name.

        Returns:
            A ``DenseRetriever`` ready for search (encoder + collection loaded on first call).
        """
        logger.info(
            "Connecting to dense index at '%s', collection '%s'",
            chroma_path,
            collection_name,
        )
        return cls(chroma_path, embedding_model, collection_name)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Retrieve top-k documents using cosine similarity in embedding space.

        The BGE query prefix is prepended to ``query`` automatically.

        Args:
            query:  Natural-language search query.
            top_k:  Number of results to return.

        Returns:
            Ranked list of ``RetrievalResult`` (highest cosine similarity first).
        """
        encoder = self._get_encoder()
        collection = self._get_collection()

        prefixed_query = apply_bge_query_prefix(query)
        query_embedding = encoder.encode(
            [prefixed_query],
            normalize_embeddings=True,
        )

        raw = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k,
            include=["metadatas", "distances"],
        )

        results: list[RetrievalResult] = []
        for rank, (isbn, meta, dist) in enumerate(
            zip(
                raw["ids"][0],
                raw["metadatas"][0],
                raw["distances"][0],
            ),
            start=1,
        ):
            # ChromaDB cosine distance → similarity: score = 1 – distance
            score = 1.0 - float(dist)
            results.append(
                RetrievalResult(
                    isbn13=str(isbn),
                    title=meta.get("title", ""),
                    score=score,
                    rank=rank,
                )
            )

        return results
