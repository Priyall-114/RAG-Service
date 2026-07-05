from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self):
        self.model=SentenceTransformer('all-MiniLM-L6-v2')
    

    def embed(self,text:str):
        return self.model.encode(text)

    def batch_embed(self,chunks:list):
        all_embeddings=[]
        for piece in chunks:
            embeddings=self.embed(piece)
            all_embeddings.append(embeddings)
        return all_embeddings

embedding=EmbeddingService()
