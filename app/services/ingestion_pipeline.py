from app.services.chunking import chunker
from app.services.embeddings import embedding
from loguru import logger
from app.services.PdfExtractor import S3connect
from app.services.PdfExtractor import extract_text
from app.database import db
import os
def process_document(user_id:str,file_id:str,s3_key:str,fileName:str):
    tmp_path=None
    try:
        logger.info(f"[background] Processing started for file={file_id}")
        
        tmp_path=S3connect(s3_key)
        file_content=extract_text(tmp_path)

        if not file_content:
            logger.error(f"[background] No text extracted from {file_id}")
            db.update_file_status(file_id,"Failed")
            return


        #Now sending the content to get chunked

        chunks=chunker.chunking(file_content)
        embeddings=embedding.batch_embed(chunks)
        

        db.store_chunks(user_id,file_id,chunks,embeddings,fileName)
        db.update_file_status(file_id,"Completed")

        logger.info(f"[background] Processing done for file={file_id}, {len(chunks)} chunks")
        
    except Exception as e:
        logger.error(f"[background] Processing failed for file={file_id}: {e}")
        db.update_file_status(file_id, status="failed")

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)



