from fastapi import APIRouter , BackgroundTasks
from app.services.ingestion_pipeline import process_document
from app.services.retrieval_pipeline import retrieval

router=APIRouter(prefix="/documents",tags=["documents"])

# convention yeh hai ki FastAPI mein route handlers by default async def rakhte hain 
#1.Agar kal tumne isme koi await db.something() add kiya, to already async hone se easy hoga.
#2.FastAPI ka poora ecosystem async-first design hai.


@router.post("/upload")
async def upload_document( user_id:str,file_id:str,s3_key:str,fileName:str,background_tasks:BackgroundTasks):
    background_tasks.add_task(process_document,user_id,file_id,s3_key,fileName)
    return {
        "status": "processing_started",
        "file_id": file_id
    }

@router.get("/query")
async def query_documents(user_id:str,question:str,top_k:int=5):
    results=retrieval(user_id,question,top_k)

    return{
        "query":question,
        "response":results
    }



