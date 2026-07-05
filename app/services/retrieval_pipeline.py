from loguru import logger
from app.services.embeddings import embedding
from app.database import db
from google import genai
from app.config import settings


def retrieval(user_id: str, query: str, top_k=5):
    query_embedding = embedding.embed(query)
    logger.info("Query Successfully embedded")

    retrieved_chunks = db.vector_search(user_id, query_embedding, top_k)
    logger.info(f"found {len(retrieved_chunks)} matching chunks")

    chunk_texts = [chunk["chunk"] for chunk in retrieved_chunks]
    context = "\n\n".join(chunk_texts)

    prompt = f"Answer the question: {query}\n\nUsing this context:\n{context}"

    google_client = genai.Client(api_key=settings.gemini_api_key)
    response = google_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return {
        "answer": response.text,
        "chunks": retrieved_chunks
    }