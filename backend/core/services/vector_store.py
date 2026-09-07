import os
from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    def upsert(self, ids, vectors, payloads): ...

class QdrantVectorStore(VectorStore):
    def __init__(self):
        from qdrant_client import QdrantClient
        self.client=QdrantClient(url=os.getenv("QDRANT_URL","http://localhost:6333"))
        self.collection=os.getenv("QDRANT_COLLECTION","manaksetu_documents")
    def upsert(self,ids,vectors,payloads):
        from qdrant_client.models import PointStruct
        self.client.upsert(self.collection,[PointStruct(id=i,vector=v,payload=p) for i,v,p in zip(ids,vectors,payloads,strict=True)])

