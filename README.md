# RAG Service

A Retrieval-Augmented Generation (RAG) microservice built from scratch in Python — no LangChain, no LlamaIndex. Every piece of the pipeline (chunking, embedding, retrieval, generation) is implemented manually to understand the internals and defend design decisions in depth.

This service powers document Q&A for **DocFlow**, a document management platform. It runs as an independent FastAPI microservice that a separate Java Spring Boot backend calls over HTTP.

## What it does

Upload a PDF → the service extracts text, chunks it, generates embeddings, and stores it in a vector database. Ask a question → the service embeds the question, finds the most relevant chunks via vector similarity search, and uses an LLM to generate a grounded answer with cited sources.

## Architecture

```
                 +---------------------+
   PDF Upload    |                     |
  -------------> |   FastAPI Service   |
                 |                     |
                 +----------+----------+
                            |
              +-------------+-------------+
              v             v             v
        S3 Download    Text Extract    Chunking
        (boto3)        (pdfplumber)    (custom recursive
                                        chunker w/ overlap)
                            |
                            v
                    Sentence Transformers
                    (all-MiniLM-L6-v2, local)
                            |
                            v
                  MongoDB Atlas Vector Search
                  (384-dim, cosine similarity,
                   user_id filtering)


                 +---------------------+
   Question      |                     |
  -------------> |   FastAPI Service   |
                 |                     |
                 +----------+----------+
                            |
                            v
                  Embed query -> Vector search
                  -> Top-k chunks retrieved
                            |
                            v
                    LLM (Groq / Gemini)
                  (context-grounded answer
                   generation)
                            |
                            v
              Answer + source chunks returned
```

## Tech stack

| Component | Choice | Why |
|---|---|---|
| API framework | FastAPI | Async support, background task processing, minimal boilerplate |
| PDF extraction | pdfplumber | Reliable text extraction, page-aware |
| Chunking | Custom recursive chunker | Built manually with current chunk-size:509 and Overlap of 90 characters(Left Overlapping)|
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) | Free, runs locally, 384-dim vectors, good quality-to-cost ratio for development |
| Vector store | MongoDB Atlas Vector Search | Same cluster as the main application database — no extra infra; HNSW-based ANN search |
| LLM | Gemini 2.5 Flash | Fast, inexpensive, sufficient for grounded short-context Q&A |
| Storage | AWS S3 (via boto3) | Source PDFs are pulled directly from S3 |

No LangChain or LlamaIndex — chunking, embedding orchestration, prompt construction, and retrieval logic are all custom-built.

## How it works

### 1. Ingestion (`POST /documents/upload`)

- File is downloaded from S3 using a provided key
- Text is extracted page-by-page with `pdfplumber` and cleaned (collapsing repeated whitespace/newlines)
- Text is split using a custom **recursive chunker**: it tries splitting on paragraph breaks first, falling back to sentence breaks, then word breaks, only recursing further when a chunk still exceeds the size limit. Adjacent chunks share a small overlap to preserve context across boundaries.
- Each chunk is embedded locally via Sentence Transformers
- Chunks + embeddings + metadata (`user_id`, `file_id`, `fileName`) are stored in MongoDB
- Processing runs as a **FastAPI background task** — the upload endpoint returns immediately, and a status field is updated on completion/failure so the caller isn't blocked waiting on embedding generation

### 2. Retrieval (`GET /documents/query`)

- The incoming question is embedded using the same model used for ingestion (embedding spaces must match)
- MongoDB's `$vectorSearch` aggregation stage retrieves the top-k most similar chunks, **filtered by `user_id`** so users only ever retrieve their own documents
- Retrieved chunk texts are joined into a context block
- The context and question are combined into a prompt and sent to the LLM
- The response returns both the generated answer **and** the source chunks (with file name, chunk text, and similarity score) for transparency/citation

## Key design decisions

- **User isolation at the vector index level** — the Atlas Vector Search index includes a filter field on `user_id`, so retrieval is scoped per-user at the database layer, not just in application logic.
- **Background processing for ingestion** — embedding generation is the slowest step; running it as a background task keeps the upload endpoint responsive.
- **Status tracking across services** — since this service is called by a separate Java backend, it writes processing status (`completed` / `failed`) directly back to the shared MongoDB `File` collection so the calling application can track ingestion progress without polling this service.
- **No RAG framework** — chunking strategy, embedding batching, and prompt construction are all hand-written to make deliberate tradeoffs (e.g., recursive chunking with overlap) rather than relying on framework defaults.

## Evaluation

The pipeline is evaluated using [RAGAS](https://github.com/GoldSharon/ragas) (community fork — the official package hit a `google-vertexai` module error in this setup) rather than eyeballing outputs manually.

### Testset generation

- A synthetic testset (question + reference answer pairs) is generated directly from the source PDFs using RAGAS's testset generator, instead of hand-writing one.
- Source documents: 5–7 OS/DSA lecture-slide PDFs — fairly shallow, bullet-point content rather than detailed prose. This matters for interpreting the results below.
- RAGAS's default `HeadlinesExtractor` transform crashed on these PDFs (they lack clear section headings), so headline-based transforms were filtered out of `default_transforms` and the knowledge graph (`DOCUMENT`/`CHUNK` nodes + parent-child relationships) was built manually instead.
- Testset similarity linking uses the same `all-MiniLM-L6-v2` embeddings as production (not the generation LLM's embeddings), so evaluation stays consistent with what's actually deployed.
- Testset size: 20–30 questions.

### Running the evaluation

RAGAS metric classes are instantiated manually (e.g. `AnswerRelevancy(strictness=1)`) rather than using the default instances, since some LLM providers only support `n=1`.

```bash
python eval/testset_generation.py   # generates the synthetic testset
python eval/evaluation.py           # runs RAGAS metrics against the testset
```

### Results

| Metric | Score |
|---|---|
| Faithfulness | 0.795 |
| Answer Relevancy | 0.572 |
| Context Precision | 0.679 |
| Context Recall | 0.464 |

**Reading the numbers:**
- **Answer relevancy** is the strongest signal — generated answers are consistently on-topic and address the question asked.
- **Context precision/recall** are lower mainly because the source PDFs are shallow (slide titles with little explanatory text), leaving retrieval without enough substantive chunk content to score highly against reference answers — confirmed by manually inspecting failing cases, not just inferred from the score.
- **Planned next step**: author supplementary paragraphs covering identified content gaps in the source material and re-run evaluation to isolate how much of the precision/recall gap closes once source content is less shallow, versus what's attributable to retrieval itself.

## Setup

```bash
# Clone and enter the project
cd docflow-rag-service

# Create and activate a virtual environment
python -m venv docflow_env
docflow_env\Scripts\activate      # Windows
source docflow_env/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):

```
MONGODB_URI=your_mongodb_connection_string
MONGODB_DATABASE=your_database_name
MONGODB_COLLECTION=your_collection_name
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_BUCKET_NAME=your_bucket_name
GEMINI_API_KEY=your_gemini_api_key
APP_NAME=DocFlow RAG
APP_VERSION=1.0.0
DEBUG=True
```

For running RAGAS evaluation, a separate virtual environment is recommended (RAGAS's dependency set differs from the production service):

```bash
python -m venv ragas-env
ragas-env\Scripts\activate
pip install -r eval/requirements.txt
pip install git+https://github.com/GoldSharon/ragas.git
```

Run the service:

```bash
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`.

### MongoDB Atlas Vector Search Index

The vector search index must be created manually via the Atlas UI (Search → Create Search Index → JSON Editor):

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 384,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "user_id"
    }
  ]
}
```

## API Reference

**`POST /documents/upload`**
Triggers ingestion for a document already uploaded to S3.

| Param | Type | Description |
|---|---|---|
| `user_id` | string | Owner of the document |
| `file_id` | string | Unique identifier for the file |
| `s3_key` | string | S3 object key for the source PDF |
| `fileName` | string | Original filename, stored for display in retrieval results |

**`GET /documents/query`**
Retrieves an answer grounded in a user's documents.

| Param | Type | Description |
|---|---|---|
| `user_id` | string | Scopes retrieval to this user's documents only |
| `question` | string | The natural language question |
| `top_k` | int (optional, default 5) | Number of chunks to retrieve |

Returns:
```json
{
  "answer": "...",
  "chunks": [
    {"file_id": "...", "fileName": "...", "chunk": "...", "score": 0.87}
  ]
}
```

## Project structure

```
docflow-rag-service/
├── main.py
├── app/
│   ├── config.py           # Settings loaded from .env
│   ├── database.py         # MongoDB connection, vector search, status updates
│   ├── routers/
│   │   └── documents.py    # Upload & query endpoints
│   └── services/
│       ├── chunking.py         # Custom recursive chunker
│       ├── embeddings.py       # Sentence Transformers wrapper
│       ├── pdf_extractor.py    # S3 download + text extraction
│       ├── ingestion_pipeline.py   # Orchestrates upload → chunk → embed → store
│       └── retrieval_pipeline.py   # Orchestrates query → retrieve → generate
├── eval/
│   ├── testset_generation.py   # RAGAS synthetic testset generation
│   └── evaluation.py           # RAGAS metric evaluation
└── requirements.txt
```

## Notes

This service is part of a larger project, **DocFlow**, and is designed to be called internally by an authenticated backend rather than exposed directly to end users — authentication and authorization are handled upstream.
