"""Vector store backends for local Chroma and Supabase pgvector."""

import logging
import os
from typing import Optional

from supabase import Client, create_client


logger = logging.getLogger(__name__)


class BaseVectorStore:
    """Common interface used by the RAG service."""

    policy_collection_name = "policy_documents"
    complaint_collection_name = "complaints"

    def has_documents(self, collection_name: str) -> bool:
        """Return whether the named collection has any stored documents."""
        raise NotImplementedError

    def upsert_documents(
        self,
        collection_name: str,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Create or update vector records."""
        raise NotImplementedError

    def query(
        self,
        collection_name: str,
        *,
        query_embedding: list[float],
        n_results: int,
    ) -> dict:
        """Return a Chroma-like query payload for callers."""
        raise NotImplementedError


class LocalChromaVectorStore(BaseVectorStore):
    """Local vector storage backed by ChromaDB."""

    def __init__(self, persist_dir: Optional[str] = None):
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError(
                "Local Chroma backend requires the optional 'chromadb' package. "
                "Re-enable it in requirements.txt or switch VECTOR_STORE_BACKEND to supabase."
            ) from exc

        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()

        self.policy_collection = self.client.get_or_create_collection(
            name=self.policy_collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self.complaint_collection = self.client.get_or_create_collection(
            name=self.complaint_collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _get_collection(self, collection_name: str):
        if collection_name == self.policy_collection_name:
            return self.policy_collection
        if collection_name == self.complaint_collection_name:
            return self.complaint_collection
        raise ValueError(f"Unknown vector collection: {collection_name}")

    def has_documents(self, collection_name: str) -> bool:
        return self._get_collection(collection_name).count() > 0

    def upsert_documents(
        self,
        collection_name: str,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        self._get_collection(collection_name).upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self,
        collection_name: str,
        *,
        query_embedding: list[float],
        n_results: int,
    ) -> dict:
        return self._get_collection(collection_name).query(
            query_embeddings=[query_embedding],
            n_results=n_results,
        )


class SupabaseVectorStore(BaseVectorStore):
    """Supabase pgvector storage using the official Python client."""

    def __init__(self):
        url = (os.getenv("SUPABASE_URL") or "").strip()
        key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required when "
                "VECTOR_STORE_BACKEND is set to 'supabase'."
            )

        self.table_name = os.getenv("SUPABASE_VECTOR_TABLE", "vector_documents").strip()
        self.match_function = os.getenv(
            "SUPABASE_VECTOR_MATCH_FUNCTION",
            "match_vector_documents",
        ).strip()
        self.client: Client = create_client(url, key)

    def has_documents(self, collection_name: str) -> bool:
        response = (
            self.client.table(self.table_name)
            .select("document_id")
            .eq("collection_name", collection_name)
            .limit(1)
            .execute()
        )
        return bool(response.data)

    def upsert_documents(
        self,
        collection_name: str,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        rows = []
        for doc_id, document, metadata, embedding in zip(ids, documents, metadatas, embeddings):
            rows.append({
                "collection_name": collection_name,
                "document_id": doc_id,
                "document": document,
                "metadata": metadata or {},
                "embedding": embedding,
            })

        if not rows:
            return

        (
            self.client.table(self.table_name)
            .upsert(
                rows,
                on_conflict="collection_name,document_id",
                returning="minimal",
            )
            .execute()
        )

    def query(
        self,
        collection_name: str,
        *,
        query_embedding: list[float],
        n_results: int,
    ) -> dict:
        response = self.client.rpc(
            self.match_function,
            {
                "query_embedding": query_embedding,
                "match_count": n_results,
                "match_collection": collection_name,
            },
        ).execute()
        rows = response.data or []
        similarities = [float(row.get("similarity") or 0.0) for row in rows]

        return {
            "ids": [[row.get("document_id", "") for row in rows]],
            "documents": [[row.get("document", "") for row in rows]],
            "metadatas": [[row.get("metadata") or {} for row in rows]],
            "distances": [[1.0 - similarity for similarity in similarities]],
        }


def build_vector_store(
    *,
    backend: Optional[str] = None,
    persist_dir: Optional[str] = None,
) -> BaseVectorStore:
    """Build the configured vector store backend."""
    selected_backend = (backend or os.getenv("VECTOR_STORE_BACKEND") or "auto").strip().lower()
    local_persist_dir = persist_dir or (os.getenv("LOCAL_VECTOR_DB_PATH") or "").strip() or None

    if selected_backend == "supabase":
        logger.info("Using Supabase pgvector backend for RAG storage.")
        return SupabaseVectorStore()

    if selected_backend == "auto":
        has_supabase_config = bool(
            (os.getenv("SUPABASE_URL") or "").strip()
            and (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
        )
        if has_supabase_config:
            try:
                logger.info("Using Supabase pgvector backend for RAG storage.")
                return SupabaseVectorStore()
            except Exception:
                logger.exception("Supabase vector store initialization failed. Falling back to local Chroma.")

    logger.info("Using local Chroma backend for RAG storage.")
    return LocalChromaVectorStore(persist_dir=local_persist_dir)
