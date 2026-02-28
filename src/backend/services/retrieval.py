"""Vector retrieval service for evidence-based medical literature search."""

import os
import pickle
from typing import List, Dict, Optional
import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from src.backend.models import EvidenceHit
from src.backend.lib.bedrock_client import BedrockClient


class RetrievalService:
    """
    Service for retrieving evidence from medical literature using vector similarity search.
    
    Supports FAISS index for local demo mode and can be extended for OpenSearch in production.
    Implements caching for embeddings to improve performance in demo mode.
    """
    
    def __init__(self, index_path: str, bedrock_client: BedrockClient):
        """
        Initialize retrieval service with vector index and Bedrock client.
        
        Args:
            index_path: Path to FAISS index file or directory containing index and metadata
            bedrock_client: BedrockClient instance for generating query embeddings
        """
        # Download index from S3 if needed (Lambda environment)
        self._load_index_from_s3_if_needed()
        
        self.bedrock_client = bedrock_client
        self.index_path = index_path
        self.index = None
        self.documents = []  # List of document metadata
        self.embedding_cache: Dict[str, List[float]] = {}  # Cache for query embeddings
        
        # Load or create index
        self._load_index()
    
    def _load_index_from_s3_if_needed(self):
        """Download FAISS index from S3 to /tmp if not already present."""
        import os
        local_index = "/tmp/faiss_index/faiss_index.index"
        local_meta = "/tmp/faiss_index/faiss_index_metadata.pkl"
        
        if os.path.exists(local_index) and os.path.exists(local_meta):
            return  # Already cached in /tmp
        
        corpus_bucket = os.environ.get("CORPUS_BUCKET")
        if not corpus_bucket:
            return  # No S3 bucket configured, use local path
        
        os.makedirs("/tmp/faiss_index", exist_ok=True)
        
        try:
            import boto3
            s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            s3.download_file(corpus_bucket, "corpus/faiss_index.index", local_index)
            s3.download_file(corpus_bucket, "corpus/faiss_index_metadata.pkl", local_meta)
            print(f"Successfully downloaded FAISS index from S3 bucket: {corpus_bucket}")
        except Exception as e:
            print(f"Warning: Could not download corpus from S3: {e}")
            return
    
    def _load_index(self):
        """Load FAISS index from file or create empty index."""
        if faiss is None:
            raise ImportError("faiss-cpu is required for RetrievalService. Install with: pip install faiss-cpu")
        
        # Check if S3-downloaded index exists in /tmp
        tmp_index_path = "/tmp/faiss_index"
        if os.path.exists(os.path.join(tmp_index_path, "faiss_index.index")):
            # Use the S3-downloaded index from /tmp
            index_file = os.path.join(tmp_index_path, "faiss_index.index")
            metadata_file = os.path.join(tmp_index_path, "faiss_index_metadata.pkl")
        else:
            # Fall back to the configured index_path
            index_file = self.index_path if self.index_path.endswith('.index') else os.path.join(self.index_path, 'faiss_index.index')
            metadata_file = index_file.replace('.index', '_metadata.pkl')
        
        if os.path.exists(index_file):
            try:
                # Load existing index
                self.index = faiss.read_index(index_file)
                
                # Load document metadata if available
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'rb') as f:
                        self.documents = pickle.load(f)
                else:
                    # Create empty metadata list matching index size
                    self.documents = [self._create_placeholder_doc(i) for i in range(self.index.ntotal)]
                
            except Exception as e:
                print(f"Warning: Failed to load index from {index_file}: {e}")
                self._create_empty_index()
        else:
            # Create empty index
            self._create_empty_index()
    
    def _create_empty_index(self):
        """Create an empty FAISS index with 1536 dimensions (Bedrock embedding size)."""
        if faiss is None:
            raise ImportError("faiss-cpu is required")
        
        # Create flat L2 index for cosine similarity (after normalization)
        dimension = 1536  # Bedrock Titan embeddings dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        self.documents = []
    
    def _create_placeholder_doc(self, idx: int) -> Dict:
        """Create placeholder document metadata."""
        return {
            "title": f"Medical Literature Document {idx + 1}",
            "pmcid": f"PMC{1000000 + idx}",
            "doi": f"10.1000/placeholder.{idx}",
            "content": "Placeholder medical literature content for demo purposes.",
            "snippet": "Placeholder medical literature content for demo purposes."[:200]
        }
    
    def search(self, query: str, top_k: int = 3) -> List[EvidenceHit]:
        """
        Perform vector similarity search for medical evidence.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default 3)
            
        Returns:
            List of EvidenceHit objects sorted by cosine_similarity descending
            
        Implementation:
            1. Generate query embedding via bedrock_client.get_embeddings()
            2. Compute cosine similarity with all index vectors
            3. Return top_k results with similarity >= 0.0
        """
        # Check for cached embedding
        if query in self.embedding_cache:
            query_embedding = self.embedding_cache[query]
        else:
            # Generate query embedding
            query_embedding = self.bedrock_client.get_embeddings(query)
            # Cache the embedding
            self.embedding_cache[query] = query_embedding
        
        # Convert to numpy array and normalize for cosine similarity
        query_vector = np.array([query_embedding], dtype=np.float32)
        
        # Normalize vector for cosine similarity (using inner product index)
        faiss.normalize_L2(query_vector)
        
        # Handle empty index case
        if self.index.ntotal == 0:
            return []
        
        # Ensure we don't request more results than available
        k = min(top_k, self.index.ntotal)
        
        # Search index
        similarities, indices = self.index.search(query_vector, k)
        
        # Convert results to EvidenceHit objects
        results = []
        for i in range(k):
            idx = indices[0][i]
            similarity = float(similarities[0][i])
            
            # Get document metadata
            if idx < len(self.documents):
                doc = self.documents[idx]
            else:
                doc = self._create_placeholder_doc(idx)
            
            # Create EvidenceHit
            evidence = EvidenceHit(
                title=doc.get("title", "Unknown Title"),
                pmcid=doc.get("pmcid", "PMC0000000"),
                doi=doc.get("doi", "10.0000/unknown"),
                snippet=doc.get("snippet", doc.get("content", "")[:200]),
                cosine_similarity=max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            )
            results.append(evidence)
        
        return results
    
    def add_documents(self, documents: List[Dict], embeddings: List[List[float]]):
        """
        Add documents to the index.
        
        Args:
            documents: List of document metadata dicts with keys: title, pmcid, doi, content
            embeddings: List of embedding vectors corresponding to documents
        """
        if not documents or not embeddings:
            return
        
        if len(documents) != len(embeddings):
            raise ValueError("Number of documents must match number of embeddings")
        
        # Convert embeddings to numpy array
        vectors = np.array(embeddings, dtype=np.float32)
        
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(vectors)
        
        # Add to index
        self.index.add(vectors)
        
        # Add document metadata
        self.documents.extend(documents)
    
    def save_index(self, output_path: Optional[str] = None):
        """
        Save FAISS index and metadata to disk.
        
        Args:
            output_path: Path to save index (defaults to self.index_path)
        """
        if output_path is None:
            output_path = self.index_path
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        
        # Save index
        index_file = output_path if output_path.endswith('.index') else os.path.join(output_path, 'faiss_index.index')
        faiss.write_index(self.index, index_file)
        
        # Save metadata
        metadata_file = index_file.replace('.index', '_metadata.pkl')
        with open(metadata_file, 'wb') as f:
            pickle.dump(self.documents, f)

    def _load_index_from_s3_if_needed(self):
        """Download FAISS index from S3 to /tmp if not already present."""
        import os
        local_index = "/tmp/faiss_index/faiss_index.index"
        local_meta = "/tmp/faiss_index/faiss_index_metadata.pkl"

        if os.path.exists(local_index) and os.path.exists(local_meta):
            return  # Already cached in /tmp

        corpus_bucket = os.environ.get("CORPUS_BUCKET")
        if not corpus_bucket:
            return  # No S3 bucket configured, use local path

        os.makedirs("/tmp/faiss_index", exist_ok=True)

        try:
            import boto3
            s3 = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            s3.download_file(corpus_bucket, "corpus/faiss_index.index", local_index)
            s3.download_file(corpus_bucket, "corpus/faiss_index_metadata.pkl", local_meta)
            print(f"Successfully downloaded FAISS index from S3 bucket: {corpus_bucket}")
        except Exception as e:
            print(f"Warning: Could not download corpus from S3: {e}")
            return

