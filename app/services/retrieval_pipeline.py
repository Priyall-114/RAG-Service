from loguru import logger
from app.services.embeddings import embedding
from app.database import db
from google import genai
from app.config import settings
from google.genai import types
from groq import Groq

def retrieval(user_id: str, query: str, top_k=4):
    query_embedding = embedding.embed(query)
    logger.info("Query Successfully embedded")

    retrieved_chunks = db.vector_search(user_id, query_embedding, top_k)
    logger.info(f"found {len(retrieved_chunks)} matching chunks")

    chunk_texts = [chunk["chunk"] for chunk in retrieved_chunks]
    context = "\n\n".join(chunk_texts)

    prompt = f"Answer the question as directly and specifically as possible using ONLY the information present in the provided context — do not add facts, explanations, or details not stated in the context even if you know them; if the context only partially covers the question, answer with what it does cover instead of skipping it, and only say information is missing if the context has almost nothing relevant, keeping the response concise without long multi-section explanations or tables beyond what the context supports. {query}\n\nUsing this context:\n{context}"

    # google_client = genai.Client(api_key=settings.gemini_api_key)
    # response = google_client.models.generate_content(
    #     #model="gemini-2.5-flash",
    #     model="gemini-3.6-flash", #switching to new acocund model
    #     contents=prompt,
    #     config=types.GenerateContentConfig(temperature=0)
    # )



    #Now switching to groq
    groq_client=Groq(api_key=settings.groq_retrieval_api_key)
    response=groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return {

        "answer":response.choices[0].message.content,
        "chunks": retrieved_chunks
    }