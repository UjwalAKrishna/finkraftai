"""This return matching results from our chromaDb based on user_query"""
import chromadb
from chromadb.utils import embedding_functions
import configparser

config = configparser.ConfigParser()
config.read("config.properties")

persist_directory = config["Embedding"]["persist_directory"]
collection_name = config["Embedding"]["collection_name"]
model_name = config["Embedding"]["model_name"]

# Initialize client with persistence
client = chromadb.PersistentClient(path=persist_directory)

# Define embedding function
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=model_name
)

collection = client.get_or_create_collection(
    name=collection_name,
    embedding_function=embedding_func
)

def getResult(user_query: str, k: int = 3):
    """
    Query the ChromaDB collection and return top-k matches.
    """
    print('Fetching results from your DB')
    results = collection.query(
        query_texts=[user_query],
        n_results=k
    )
    
    matches = []
    for i in range(len(results["ids"][0])):
        matches.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "score": results["distances"][0][i],
            "metadata": results["metadatas"][0][i] if results["metadatas"][0] else None
        })
    print("Result Matched",matches)
    return matches


"""if __name__ == "__main__":
    user_query = "Location-based suggestions?"
    k = 5
    top_k_results = getResult(user_query, k)
    for r in top_k_results:
        print(r)"""

"""print("Collection name:", collection_name)
print("Persist directory:", persist_directory)
print("Total docs in collection:", collection.count())

all_docs = collection.peek()  
print("Sample docs:", all_docs)"""
