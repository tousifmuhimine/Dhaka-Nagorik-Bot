"""RAG (Retrieval-Augmented Generation) service using ChromaDB for policy documents."""
import os
import json
from pathlib import Path
from typing import Optional, List
import chromadb
from sentence_transformers import SentenceTransformer


class RAGService:
    """Service for RAG with ChromaDB using policy documents."""
    
    def __init__(self, persist_dir: Optional[str] = None):
        """
        Initialize RAG service with ChromaDB.
        
        Args:
            persist_dir: Directory to persist ChromaDB data. If None, uses in-memory.
        """
        # Initialize ChromaDB client
        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()
        
        # Collection for policy documents
        self.policy_collection = self.client.get_or_create_collection(
            name="policy_documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Collection for complaint templates
        self.complaint_collection = self.client.get_or_create_collection(
            name="complaints",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Sentence transformer for embeddings
        self.embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        self.policy_loaded = False
    
    def load_policies_from_pdfs(self, pdf_dir: str = None) -> bool:
        """
        Load policy documents from PDFs in a directory.
        Currently validates structure; actual PDF loading would require PyPDF2.
        
        Args:
            pdf_dir: Directory containing policy PDFs (Bangla + English)
            
        Returns:
            True if policies loaded successfully
        """
        if pdf_dir is None:
            pdf_dir = Path(__file__).parent.parent.parent / "_archive"
        
        # For now, add sample policy documents in Bangla and English
        sample_policies = [
            {
                "id": "policy_01",
                "title": "ঢাকা নগর সড়ক রক্ষণাবেক্ষণ নীতি",
                "title_en": "Dhaka City Road Maintenance Policy",
                "content": """রাস্তার গর্ত এবং ক্ষতিগ্রস্ত আস্ফালটিং মেরামত করা হবে ২৪-৪৮ ঘণ্টার মধ্যে।
দুর্ঘটনার ঝুঁকি কমাতে জরুরি মেরামত অগ্রাধিকার পাবে।""",
                "category": "road_maintenance"
            },
            {
                "id": "policy_02",
                "title": "জল ব্যবস্থাপনা এবং নিকাশি নীতি",
                "title_en": "Water Management and Drainage Policy",
                "content": """জলাবদ্ধতা এবং পরিবেশগত সমস্যা সমাধান করা হবে বর্ষাকালের আগে।
নিকাশি সিস্টেম নিয়মিত পরিষ্কার করা হবে।""",
                "category": "water_drainage"
            },
            {
                "id": "policy_03",
                "title": "বর্জ্য ব্যবস্থাপনা নীতি",
                "title_en": "Waste Management Policy",
                "content": """প্রতিটি এলাকায় বর্জ্য সংগ্রহ দৈনিক হবে।
পরিবেশ বান্ধব বর্জ্য ব্যবস্থাপনা নিশ্চিত করা হবে।""",
                "category": "waste_management"
            }
        ]
        
        # Add policies to collection
        for policy in sample_policies:
            content = policy['content']
            embedding = self.embedder.encode(content, convert_to_tensor=False)
            
            self.policy_collection.add(
                ids=[policy['id']],
                documents=[content],
                metadatas=[{
                    "title": policy['title'],
                    "title_en": policy['title_en'],
                    "category": policy['category']
                }],
                embeddings=[embedding.tolist()]
            )
        
        self.policy_loaded = True
        return True
    
    def retrieve_relevant_policies(self, query: str, top_k: int = 3) -> List[dict]:
        """
        Retrieve relevant policy documents for a query.
        
        Args:
            query: Query text (can be Bangla or English)
            top_k: Number of top results to return
            
        Returns:
            List of relevant policies
        """
        if not self.policy_loaded:
            self.load_policies_from_pdfs()
        
        results = self.policy_collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        policies = []
        if results['documents'] and results['documents'][0]:
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                policies.append({
                    'title': metadata.get('title', ''),
                    'title_en': metadata.get('title_en', ''),
                    'content': doc,
                    'category': metadata.get('category', ''),
                    'relevance': 'high'
                })
        
        return policies
    
    def store_complaint_summary(self, complaint_id: str, summary: str, category: str):
        """
        Store a complaint summary in the database for future retrieval.
        
        Args:
            complaint_id: Unique ID for the complaint
            summary: Summary text of the complaint
            category: Complaint category
        """
        embedding = self.embedder.encode(summary, convert_to_tensor=False)
        
        self.complaint_collection.add(
            ids=[complaint_id],
            documents=[summary],
            metadatas=[{
                "category": category,
            }],
            embeddings=[embedding.tolist()]
        )
    
    def find_similar_complaints(self, complaint_summary: str, top_k: int = 3) -> List[dict]:
        """
        Find similar complaints that have been filed before.
        
        Args:
            complaint_summary: Current complaint summary
            top_k: Number of similar complaints to return
            
        Returns:
            List of similar complaints
        """
        results = self.complaint_collection.query(
            query_texts=[complaint_summary],
            n_results=top_k
        )
        
        similar_complaints = []
        if results['documents'] and results['documents'][0]:
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                similar_complaints.append({
                    'summary': doc,
                    'category': metadata.get('category', ''),
                })
        
        return similar_complaints
    
    def get_policy_for_category(self, category: str) -> List[dict]:
        """
        Get all policies related to a complaint category.
        
        Args:
            category: Complaint category (e.g., "road", "water", "waste")
            
        Returns:
            List of relevant policies
        """
        if not self.policy_loaded:
            self.load_policies_from_pdfs()
        
        # Query for policies in this category
        results = self.policy_collection.query(
            query_texts=[category],
            n_results=5
        )
        
        policies = []
        if results['documents'] and results['documents'][0]:
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                if category.lower() in metadata.get('category', '').lower():
                    policies.append({
                        'title': metadata.get('title', ''),
                        'title_en': metadata.get('title_en', ''),
                        'content': doc,
                        'category': metadata.get('category', '')
                    })
        
        return policies
