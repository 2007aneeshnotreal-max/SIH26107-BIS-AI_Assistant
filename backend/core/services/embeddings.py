import hashlib
import math
import os
from abc import ABC, abstractmethod

class EmbeddingService(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class LocalEmbeddingService(EmbeddingService):
    """Deterministic hashing fallback for development; never presented as semantic AI."""
    dimensions = 128
    def embed(self, texts):
        vectors=[]
        for text in texts:
            values=[0.0]*self.dimensions
            for word in text.lower().split():
                digest=hashlib.sha256(word.encode()).digest(); values[int.from_bytes(digest[:2],"big")%self.dimensions]+=1
            norm=math.sqrt(sum(x*x for x in values)) or 1
            vectors.append([x/norm for x in values])
        return vectors

class GeminiEmbeddingService(EmbeddingService):
    def __init__(self):
        from google import genai
        self.client=genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model=os.getenv("GEMINI_EMBEDDING_MODEL","gemini-embedding-001")
    def embed(self,texts):
        response=self.client.models.embed_content(model=self.model,contents=texts)
        return [item.values for item in response.embeddings]

def get_embedding_service():
    return GeminiEmbeddingService() if os.getenv("VECTOR_PROVIDER")=="gemini" and os.getenv("GEMINI_API_KEY") else LocalEmbeddingService()

