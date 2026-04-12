"""Advanced RAG service with semantic embeddings and FAISS vector search."""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Global singleton instance
_advanced_rag_service: AdvancedRAGService | None = None


class AdvancedRAGService:
    """
    Advanced RAG service with semantic embeddings.
    Uses sentence-transformers for embeddings and FAISS for vector search.
    """

    def __init__(self):
        """Initialize the advanced RAG service."""
        self.model_name = "all-MiniLM-L6-v2"  # Lightweight model (33M params)
        self.model = None
        self.index = None
        self.documents = []
        self.embeddings = None
        self._initialized = False

        logger.info(f"Advanced RAG initialized with model: {self.model_name}")

    async def initialize(self) -> bool:
        """
        Initialize embedding model and FAISS index.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if self._initialized:
                logger.debug("Advanced RAG already initialized")
                return True

            # Load sentence transformer model
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)

            # Initialize FAISS index
            try:
                import faiss

                embedding_dim = self.model.get_sentence_embedding_dimension()
                self.index = faiss.IndexFlatL2(embedding_dim)
                logger.info(f"FAISS index initialized with dimension {embedding_dim}")
            except ImportError:
                logger.warning("FAISS not available, using in-memory search")
                self.index = None

            self._initialized = True
            logger.info("Advanced RAG service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Advanced RAG: {e}")
            return False

    async def add_documents(self, documents: list[dict[str, str]]) -> bool:
        """
        Add documents to the vector store.

        Args:
            documents: List of documents with 'id', 'content', and optional 'metadata'

        Returns:
            True if successful
        """
        try:
            if not self._initialized:
                await self.initialize()

            if not self.model:
                logger.warning("Model not initialized, cannot add documents")
                return False

            # Extract text from documents
            texts = [doc.get("content", "") for doc in documents]
            if not texts:
                logger.warning("No text content in documents")
                return False

            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} documents")
            embeddings = self.model.encode(texts, convert_to_numpy=True)

            # Add to FAISS index
            if self.index is not None:
                embeddings = embeddings.astype(np.float32)
                self.index.add(embeddings)

            # Store documents and embeddings
            self.documents.extend(documents)
            if self.embeddings is None:
                self.embeddings = embeddings
            else:
                self.embeddings = np.vstack([self.embeddings, embeddings])

            logger.info(f"Added {len(documents)} documents to vector store")
            return True

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search for relevant documents.

        Args:
            query: Search query
            top_k: Number of top results to return

        Returns:
            List of relevant documents with similarity scores
        """
        try:
            if not self._initialized or not self.model:
                logger.warning("Service not initialized, cannot search")
                return []

            if not self.documents:
                logger.info("No documents in vector store")
                return []

            # Encode query
            query_embedding = self.model.encode([query], convert_to_numpy=True).astype(np.float32)

            # Search in FAISS index
            if self.index is not None:
                distances, indices = self.index.search(query_embedding, min(top_k, len(self.documents)))
                results = []

                for idx, distance in zip(indices[0], distances[0]):
                    if idx < len(self.documents):
                        doc = self.documents[int(idx)].copy()
                        # L2 distance -> similarity score (0-1)
                        doc["similarity_score"] = float(1 / (1 + distance))
                        results.append(doc)

                logger.info(f"Found {len(results)} relevant documents for query")
                return results
            else:
                # Fallback: in-memory cosine similarity
                return await self._search_inmemory(query_embedding, top_k)

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def _search_inmemory(self, query_embedding: np.ndarray, top_k: int) -> list[dict[str, Any]]:
        """
        Fallback in-memory search using cosine similarity.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results

        Returns:
            List of relevant documents
        """
        from sklearn.metrics.pairwise import cosine_similarity

        if self.embeddings is None:
            return []

        # Compute cosine similarity
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc = self.documents[int(idx)].copy()
            doc["similarity_score"] = float(similarities[idx])
            results.append(doc)

        return results

    async def search_policies(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Search policy documents for complaint context.

        Args:
            query: Complaint description or policy question
            top_k: Number of top policy documents

        Returns:
            List of relevant policy documents
        """
        results = await self.search(query, top_k)

        # Filter to policy-related docs
        policy_results = [r for r in results if r.get("type") == "policy"]

        if not policy_results and results:
            # Fallback to all results if no explicit policies
            policy_results = results[:top_k]

        logger.info(f"Found {len(policy_results)} relevant policies")
        return policy_results

    async def search_similar_complaints(
        self, complaint_description: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search for similar historical complaints.

        Args:
            complaint_description: Description of current complaint
            top_k: Number of top similar complaints

        Returns:
            List of similar complaint documents
        """
        results = await self.search(complaint_description, top_k)

        # Filter to complaint-related docs
        complaint_results = [r for r in results if r.get("type") == "complaint"]

        if not complaint_results and results:
            complaint_results = results[:top_k]

        logger.info(f"Found {len(complaint_results)} similar complaints")
        return complaint_results

    async def get_context_for_extraction(self, complaint_text: str, top_k: int = 3) -> str:
        """
        Get relevant context for complaint extraction.

        Args:
            complaint_text: Complaint description
            top_k: Number of context documents

        Returns:
            Formatted context string for AI extraction
        """
        try:
            # Search for relevant policies and similar complaints
            policy_results = await self.search_policies(complaint_text, top_k=top_k)
            complaint_results = await self.search_similar_complaints(complaint_text, top_k=top_k)

            context_parts = []

            if policy_results:
                context_parts.append("**Relevant Policies:**")
                for doc in policy_results:
                    context_parts.append(f"- {doc.get('content', '')} (relevance: {doc.get('similarity_score', 0):.2%})")

            if complaint_results:
                context_parts.append("\n**Similar Historical Complaints:**")
                for doc in complaint_results:
                    context_parts.append(f"- {doc.get('content', '')} (similarity: {doc.get('similarity_score', 0):.2%})")

            context = "\n".join(context_parts) if context_parts else ""
            logger.debug(f"Generated context ({len(context)} chars) for extraction")
            return context

        except Exception as e:
            logger.error(f"Failed to get context for extraction: {e}")
            return ""

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "initialized": self._initialized,
            "model": self.model_name,
            "documents_count": len(self.documents),
            "has_faiss_index": self.index is not None,
            "embeddings_shape": self.embeddings.shape if self.embeddings is not None else None,
        }


async def get_advanced_rag_service() -> AdvancedRAGService:
    """Get or create advanced RAG service singleton."""
    global _advanced_rag_service
    if _advanced_rag_service is None:
        _advanced_rag_service = AdvancedRAGService()
        await _advanced_rag_service.initialize()
    return _advanced_rag_service
