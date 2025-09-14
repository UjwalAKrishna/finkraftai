import chromadb
from chromadb.config import Settings
import json
import uuid
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteFeatureEmbeddings:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client with separate collections for features and queries
        """
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Separate collections
        self.features_collection_name = "website_features"
        self.queries_collection_name = "common_queries"
        
        # Create/get features collection
        try:
            self.features_collection = self.client.get_collection(
                name=self.features_collection_name,
                embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"
                )
            )
            logger.info(f"Loaded existing features collection: {self.features_collection_name}")
        except chromadb.errors.NotFoundError:
            self.features_collection = self.client.create_collection(
                name=self.features_collection_name,
                embedding_function=chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="paraphrase-multilingual-MiniLM-L12-v2"
                ),
                metadata={"description": "Website features for travel booking platform"}
            )
            logger.info(f"Created new features collection: {self.features_collection_name}")
    
    def prepare_enhanced_feature_text(self, feature: Dict[str, Any]) -> str:
        """
        Create better text representation focusing on searchable content
        """
        text_parts = []
        
        # Feature name (most important)
        feature_name = feature.get('feature_name', '')
        text_parts.append(f"Feature: {feature_name}")
        
        # Category and description
        category = feature.get('category', '')
        text_parts.append(f"Category: {category}")
        
        description = feature.get('description', '')
        if description:
            text_parts.append(f"Description: {description}")
        
        # Key functionality (high weight)
        functionality = feature.get('functionality', [])
        if functionality:
            func_text = " ".join(functionality[:5])  # Limit to top 5
            text_parts.append(f"Key Features: {func_text}")
        
        # User benefits
        benefits = feature.get('user_benefits', [])
        if benefits:
            benefits_text = " ".join(benefits[:3])  # Limit to top 3
            text_parts.append(f"Benefits: {benefits_text}")
        
        # Important technical details only
        tech_details = feature.get('technical_details', {})
        if tech_details:
            important_tech = []
            # Only include most relevant technical aspects
            for key in ['search_speed', 'security_standards', 'languages_supported', 'success_rate']:
                if key in tech_details:
                    important_tech.append(f"{key}: {tech_details[key]}")
            if important_tech:
                text_parts.append(f"Technical: {' '.join(important_tech)}")
        
        return " | ".join(text_parts)
    
    def create_feature_embeddings(self, features_data: Dict[str, Any]) -> bool:
        """
        Create embeddings ONLY for website features (no common queries).
        Will not delete an existing collection; only adds features if not already present.
        """
        try:
            # Prepare data
            documents = []
            metadatas = []
            ids = []
            
            # Process ONLY actual features
            for category, features_list in features_data['website_features'].items():
                logger.info(f"Processing category: {category} ({len(features_list)} features)")
                
                for feature in features_list:
                    # Enhanced text preparation
                    feature_text = self.prepare_enhanced_feature_text(feature)
                    documents.append(feature_text)
                    
                    # Clean metadata
                    metadata = {
                        'feature_id': feature.get('feature_id', ''),
                        'feature_name': feature.get('feature_name', ''),
                        'category': feature.get('category', ''),
                        'main_category': category,
                        'description': feature.get('description', ''),
                        'type': 'website_feature'  # Mark as actual feature
                    }
                    
                    # Add key technical details
                    tech_details = feature.get('technical_details', {})
                    if tech_details:
                        metadata['has_technical_details'] = True
                        for key in ['search_speed', 'security_standards', 'success_rate']:
                            if key in tech_details:
                                metadata[f'tech_{key}'] = str(tech_details[key])[:100]
                    
                    metadatas.append(metadata)
                    ids.append(str(uuid.uuid4()))
                    
                    logger.info(f"Added: {feature.get('feature_name', 'Unknown')}")
            
            # Add to collection (append instead of overwrite)
            self.features_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Successfully created/added {len(documents)} feature embeddings")
            return True
            
        except Exception as e:
            logger.error(f"Error creating feature embeddings: {str(e)}")
            return False
    
 
    
    
def create_embedding():
    """
    Load features, create embeddings, and run test queries
    """
    # Load data
    try:
        with open('DB/product_features.json', 'r', encoding='utf-8') as f:
            features_data = json.load(f)
    except FileNotFoundError:
        logger.error("product_features.json not found")
        return
    
    # Create improved embedder
    embedder = WebsiteFeatureEmbeddings()
    
    # Create clean embeddings (only if not already there)
    logger.info("Creating feature embeddings...")
    success = embedder.create_feature_embeddings(features_data)
    
    if not success:
        logger.error("Failed to create embeddings")
        return




if __name__ == "__main__":
    create_embedding()
