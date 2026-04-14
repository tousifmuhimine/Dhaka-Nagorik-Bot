"""RAG (Retrieval-Augmented Generation) service for policy documents."""

import hashlib
import re
from pathlib import Path
from typing import List, Optional

import chromadb
import numpy as np
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer


class RAGService:
    """Service for retrieving policy context and similar complaints."""

    EMBEDDING_DIMENSION = 384

    def __init__(self, persist_dir: Optional[str] = None):
        """Initialize Chroma and an embedding backend that works offline."""
        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()

        self.policy_collection = self.client.get_or_create_collection(
            name="policy_documents",
            metadata={"hnsw:space": "cosine"}
        )
        self.complaint_collection = self.client.get_or_create_collection(
            name="complaints",
            metadata={"hnsw:space": "cosine"}
        )

        self.embedder = self._load_embedder()
        self.policy_loaded = self.policy_collection.count() > 0

    def _load_embedder(self):
        """Prefer a local multilingual model, but stay usable offline."""
        try:
            return SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                local_files_only=True,
            )
        except Exception:
            return None

    def _hash_embed(self, text: str) -> List[float]:
        """Fallback embedding for offline development environments."""
        vector = np.zeros(self.EMBEDDING_DIMENSION, dtype=float)
        tokens = re.findall(r"\w+", (text or "").lower(), flags=re.UNICODE)

        if not tokens:
            vector[0] = 1.0
        else:
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
                index = int(digest, 16) % self.EMBEDDING_DIMENSION
                vector[index] += 1.0

        norm = np.linalg.norm(vector)
        if norm:
            vector /= norm
        return vector.tolist()

    def _embed_text(self, text: str) -> List[float]:
        """Create embeddings with the best available backend."""
        if self.embedder is not None:
            return self.embedder.encode(text or "", convert_to_tensor=False).tolist()
        return self._hash_embed(text)

    def _chunk_text(self, text: str, chunk_size: int = 1200, overlap: int = 200) -> List[str]:
        """Split long policy text into overlapping chunks for retrieval."""
        clean_text = " ".join((text or "").split())
        if not clean_text:
            return []

        chunks = []
        start = 0
        while start < len(clean_text):
            end = min(len(clean_text), start + chunk_size)
            chunks.append(clean_text[start:end])
            if end >= len(clean_text):
                break
            start = max(0, end - overlap)
        return chunks

    def _guess_category(self, source_name: str, text: str) -> str:
        """Assign a rough policy category for retrieval metadata."""
        haystack = f"{source_name} {text}".lower()
        if any(term in haystack for term in ("road", "pothole", "street", "traffic")):
            return "roads"
        if any(term in haystack for term in ("water", "drain", "drainage", "flood", "sewer")):
            return "water"
        if any(term in haystack for term in ("electric", "power", "light", "streetlight")):
            return "electricity"
        if any(term in haystack for term in ("waste", "garbage", "pollution", "environment")):
            return "environment"
        if any(term in haystack for term in ("health", "hospital", "clinic", "mosquito", "sanitation")):
            return "health"
        return "other"

    def _load_pdf_policies(self, pdf_dir: Path) -> bool:
        """Read policy PDFs from disk and index them into Chroma."""
        pdf_paths = sorted(pdf_dir.glob("*.pdf"))
        if not pdf_paths:
            return False

        ids = []
        documents = []
        metadatas = []
        embeddings = []

        for pdf_path in pdf_paths:
            try:
                reader = PdfReader(str(pdf_path))
                pages_text = []
                for page in reader.pages:
                    pages_text.append(page.extract_text() or "")
                full_text = "\n".join(pages_text).strip()
            except Exception:
                continue

            if len(full_text) < 200:
                continue

            chunks = self._chunk_text(full_text)[:18]
            category = self._guess_category(pdf_path.stem, full_text[:5000])

            for index, chunk in enumerate(chunks, start=1):
                ids.append(f"{pdf_path.stem.lower()}_{index}")
                documents.append(chunk)
                metadatas.append({
                    "title": pdf_path.stem.upper(),
                    "title_en": pdf_path.stem.upper(),
                    "category": category,
                    "source_file": pdf_path.name,
                })
                embeddings.append(self._embed_text(chunk))

        if not documents:
            return False

        self.policy_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        return True

    def _load_sample_policies(self) -> None:
        """Fallback seed policies when PDFs are unavailable."""
        sample_policies = [
            {
                "id": "policy_road_01",
                "title": "Dhaka Road Maintenance Policy",
                "title_en": "Dhaka Road Maintenance Policy",
                "content": (
                    "Potholes and damaged road surfaces should be inspected quickly and "
                    "high-risk repairs should be prioritized within 24 to 48 hours."
                ),
                "category": "roads",
            },
            {
                "id": "policy_water_01",
                "title": "Dhaka Water and Drainage Policy",
                "title_en": "Dhaka Water and Drainage Policy",
                "content": (
                    "Drainage lines should be cleaned regularly, especially before monsoon, "
                    "to reduce waterlogging and protect neighborhoods from flooding."
                ),
                "category": "water",
            },
            {
                "id": "policy_env_01",
                "title": "Dhaka Waste Management Policy",
                "title_en": "Dhaka Waste Management Policy",
                "content": (
                    "Waste collection should happen on a routine schedule and unmanaged "
                    "garbage buildup should be addressed to reduce environmental hazards."
                ),
                "category": "environment",
            },
        ]

        self.policy_collection.add(
            ids=[policy["id"] for policy in sample_policies],
            documents=[policy["content"] for policy in sample_policies],
            metadatas=[{
                "title": policy["title"],
                "title_en": policy["title_en"],
                "category": policy["category"],
            } for policy in sample_policies],
            embeddings=[self._embed_text(policy["content"]) for policy in sample_policies],
        )

    def load_policies_from_pdfs(self, pdf_dir: str = None) -> bool:
        """Load policy documents into Chroma once per process."""
        if self.policy_loaded:
            return True

        if self.policy_collection.count() > 0:
            self.policy_loaded = True
            return True

        root = Path(pdf_dir) if pdf_dir else Path(__file__).resolve().parent.parent.parent / "_archive"

        loaded = self._load_pdf_policies(root)
        if not loaded:
            self._load_sample_policies()

        self.policy_loaded = True
        return True

    def retrieve_relevant_policies(self, query: str, top_k: int = 3) -> List[dict]:
        """Retrieve policy chunks relevant to a complaint query."""
        if not query:
            return []

        if not self.policy_loaded:
            self.load_policies_from_pdfs()

        query_embedding = self._embed_text(query)
        results = self.policy_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
        )

        policies = []
        if results.get("documents") and results["documents"][0]:
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                policies.append({
                    "title": metadata.get("title", ""),
                    "title_en": metadata.get("title_en", ""),
                    "content": doc,
                    "category": metadata.get("category", ""),
                    "source_file": metadata.get("source_file", ""),
                    "relevance": "high",
                })
        return policies

    def store_complaint_summary(self, complaint_id: str, summary: str, category: str) -> None:
        """Store complaint summaries for future similarity lookup."""
        self.complaint_collection.add(
            ids=[complaint_id],
            documents=[summary],
            metadatas=[{"category": category}],
            embeddings=[self._embed_text(summary)],
        )

    def find_similar_complaints(self, complaint_summary: str, top_k: int = 3) -> List[dict]:
        """Find previous complaint summaries similar to the current one."""
        if not complaint_summary or self.complaint_collection.count() == 0:
            return []

        results = self.complaint_collection.query(
            query_embeddings=[self._embed_text(complaint_summary)],
            n_results=top_k,
        )

        similar_complaints = []
        if results.get("documents") and results["documents"][0]:
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                similar_complaints.append({
                    "summary": doc,
                    "category": metadata.get("category", ""),
                })
        return similar_complaints

    def get_policy_for_category(self, category: str) -> List[dict]:
        """Convenience lookup for a complaint category."""
        return self.retrieve_relevant_policies(category, top_k=5)
