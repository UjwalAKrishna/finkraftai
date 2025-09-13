# Vector embedding store using FAISS for semantic memory search

import faiss
import numpy as np
import pickle
import os
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from database.connection import db_manager
import json
import logging

class VectorStore:
    """FAISS-based vector store for semantic memory search"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_file: str = "memory_index.faiss"):
        """
        Initialize vector store with sentence transformer model
        
        Args:
            model_name: HuggingFace sentence transformer model
            index_file: FAISS index file path
        """
        self.model_name = model_name
        self.index_file = index_file
        self.metadata_file = index_file.replace('.faiss', '_metadata.pkl')
        
        # Initialize sentence transformer
        print(f"Loading sentence transformer model: {model_name}")
        self.encoder = SentenceTransformer(model_name)
        self.embedding_dim = self.encoder.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        self.index = None
        self.id_to_metadata = {}
        self.next_id = 0
        
        # Load existing index if available
        self.load_index()
        
        # Create new index if none exists
        if self.index is None:
            self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
            print(f"Created new FAISS index with dimension {self.embedding_dim}")
    
    def encode_text(self, text: str) -> np.ndarray:
        """Encode text to vector embedding"""
        embedding = self.encoder.encode([text], normalize_embeddings=True)
        return embedding[0]
    
    def encode_batch(self, texts: List[str]) -> np.ndarray:
        """Encode multiple texts to vector embeddings"""
        embeddings = self.encoder.encode(texts, normalize_embeddings=True)
        return embeddings
    
    def add_embedding(self, text: str, metadata: Dict[str, Any]) -> int:
        """
        Add text embedding to the index
        
        Args:
            text: Text to embed and store
            metadata: Associated metadata (conversation_id, user_id, etc.)
            
        Returns:
            Assigned vector ID
        """
        # Generate embedding
        embedding = self.encode_text(text)
        
        # Add to FAISS index
        vector_id = self.next_id
        self.index.add(embedding.reshape(1, -1))
        
        # Store metadata
        self.id_to_metadata[vector_id] = {
            'text': text,
            'metadata': metadata,
            'vector_id': vector_id
        }
        
        self.next_id += 1
        
        # Also store in database for persistence
        self._store_embedding_in_db(text, embedding, metadata, vector_id)
        
        return vector_id
    
    def add_batch(self, texts: List[str], metadata_list: List[Dict[str, Any]]) -> List[int]:
        """Add multiple embeddings in batch for efficiency"""
        
        if len(texts) != len(metadata_list):
            raise ValueError("texts and metadata_list must have same length")
        
        # Generate embeddings in batch
        embeddings = self.encode_batch(texts)
        
        # Add to FAISS index
        vector_ids = []
        vectors_to_add = []
        
        for i, (text, metadata) in enumerate(zip(texts, metadata_list)):
            vector_id = self.next_id + i
            vectors_to_add.append(embeddings[i])
            
            # Store metadata
            self.id_to_metadata[vector_id] = {
                'text': text,
                'metadata': metadata,
                'vector_id': vector_id
            }
            
            vector_ids.append(vector_id)
            
            # Store in database
            self._store_embedding_in_db(text, embeddings[i], metadata, vector_id)
        
        # Add all vectors to FAISS at once
        self.index.add(np.array(vectors_to_add))
        self.next_id += len(texts)
        
        return vector_ids
    
    def search(self, query: str, k: int = 10, filter_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings
        
        Args:
            query: Search query text
            k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of results with scores and metadata
        """
        if self.index.ntotal == 0:
            return []
        
        # Encode query
        query_embedding = self.encode_text(query)
        
        # Search in FAISS
        scores, indices = self.index.search(query_embedding.reshape(1, -1), min(k * 2, self.index.ntotal))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # Invalid index
                continue
                
            if idx in self.id_to_metadata:
                result = self.id_to_metadata[idx].copy()
                result['similarity_score'] = float(score)
                
                # Apply metadata filters
                if filter_metadata:
                    match = True
                    for key, value in filter_metadata.items():
                        if key not in result['metadata'] or result['metadata'][key] != value:
                            match = False
                            break
                    if not match:
                        continue
                
                results.append(result)
                
                if len(results) >= k:
                    break
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:k]
    
    def search_by_conversation(self, query: str, user_id: str, k: int = 10, 
                             exclude_thread: str = None) -> List[Dict[str, Any]]:
        """Search conversations for a specific user"""
        
        filter_metadata = {'user_id': user_id}
        results = self.search(query, k * 2, filter_metadata)
        
        # Filter out current thread if specified
        if exclude_thread:
            results = [r for r in results if r['metadata'].get('thread_id') != exclude_thread]
        
        return results[:k]
    
    def get_conversation_context(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get context for a specific conversation"""
        
        for vector_id, data in self.id_to_metadata.items():
            if data['metadata'].get('conversation_id') == conversation_id:
                return data
        return None
    
    def delete_by_metadata(self, filter_metadata: Dict[str, Any]):
        """Delete embeddings matching metadata criteria"""
        
        # Find matching vector IDs
        ids_to_delete = []
        for vector_id, data in self.id_to_metadata.items():
            match = True
            for key, value in filter_metadata.items():
                if key not in data['metadata'] or data['metadata'][key] != value:
                    match = False
                    break
            if match:
                ids_to_delete.append(vector_id)
        
        # Remove from metadata
        for vector_id in ids_to_delete:
            del self.id_to_metadata[vector_id]
        
        # Note: FAISS doesn't support deletion, so we'd need to rebuild index
        # For now, just mark as deleted in metadata
        print(f"Marked {len(ids_to_delete)} embeddings for deletion")
    
    def save_index(self):
        """Save FAISS index and metadata to disk"""
        
        try:
            # Save FAISS index
            faiss.write_index(self.index, self.index_file)
            
            # Save metadata
            with open(self.metadata_file, 'wb') as f:
                pickle.dump({
                    'id_to_metadata': self.id_to_metadata,
                    'next_id': self.next_id,
                    'embedding_dim': self.embedding_dim
                }, f)
            
            print(f"Saved FAISS index with {self.index.ntotal} vectors")
            
        except Exception as e:
            print(f"Error saving index: {e}")
    
    def load_index(self):
        """Load FAISS index and metadata from disk"""
        
        try:
            if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
                # Load FAISS index
                self.index = faiss.read_index(self.index_file)
                
                # Load metadata
                with open(self.metadata_file, 'rb') as f:
                    data = pickle.load(f)
                    self.id_to_metadata = data['id_to_metadata']
                    self.next_id = data['next_id']
                    
                print(f"Loaded FAISS index with {self.index.ntotal} vectors")
                return True
                
        except Exception as e:
            print(f"Error loading index: {e}")
        
        # Try to rebuild from database
        return self._rebuild_from_database()
    
    def _rebuild_from_database(self) -> bool:
        """Rebuild FAISS index from database embeddings"""
        
        try:
            # Get all embeddings from database
            embeddings_data = db_manager.execute_query("""
                SELECT content_text, embedding_vector, metadata, id
                FROM memory_embeddings
                ORDER BY id
            """)
            
            if not embeddings_data:
                return False
            
            print(f"Rebuilding FAISS index from {len(embeddings_data)} database embeddings")
            
            # Create new index
            self.index = faiss.IndexFlatIP(self.embedding_dim)
            self.id_to_metadata = {}
            self.next_id = 0
            
            vectors = []
            for row in embeddings_data:
                # Deserialize embedding vector
                embedding = pickle.loads(row['embedding_vector'])
                vectors.append(embedding)
                
                # Rebuild metadata
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                self.id_to_metadata[self.next_id] = {
                    'text': row['content_text'],
                    'metadata': metadata,
                    'vector_id': self.next_id,
                    'db_id': row['id']
                }
                self.next_id += 1
            
            # Add all vectors to FAISS
            if vectors:
                self.index.add(np.array(vectors))
                print(f"Rebuilt FAISS index with {len(vectors)} vectors")
                return True
                
        except Exception as e:
            print(f"Error rebuilding from database: {e}")
        
        return False
    
    def _store_embedding_in_db(self, text: str, embedding: np.ndarray, metadata: Dict[str, Any], vector_id: int):
        """Store embedding in database for persistence"""
        
        try:
            # Serialize embedding
            embedding_blob = pickle.dumps(embedding)
            
            # Store in database
            db_manager.execute_query("""
                INSERT INTO memory_embeddings (content_id, content_type, embedding_vector, content_text, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (
                metadata.get('conversation_id', 0),
                metadata.get('content_type', 'message'),
                embedding_blob,
                text,
                json.dumps(metadata)
            ))
            
        except Exception as e:
            print(f"Error storing embedding in database: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'embedding_dimension': self.embedding_dim,
            'model_name': self.model_name,
            'index_file': self.index_file,
            'metadata_entries': len(self.id_to_metadata)
        }

# Global vector store instance
vector_store = VectorStore()