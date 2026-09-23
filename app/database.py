#establishing connection to mongodb
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from app.config import settings
from loguru import logger
from bson import ObjectId
from bson.errors import InvalidId


class MongoConnection:
    def __init__(self):
        self.client:MongoClient=None #yha self use krne s client naam ka ek class level variable bangya jisko hum puri class k kisi bhi method mein use krskte hain
        self.database:Database=None
        self.chunks_collection:Collection=None


    def connect(self):
        self.client=MongoClient(settings.mongodb_uri)#Return type of this is `object` python hai tou udhr likha nhai kya object buss
        self.database=self.client[settings.mongodb_database]
        #java equivalent:this.database = this.client.getDatabase(settings.getMongodbDatabase());
        self.chunks_collection=self.database[settings.mongodb_collection]
        self.client.admin.command('ping')
        logger.info("MongoDB connected!")
    
    def disconnect(self):
        if self.client:
            self.client.close()

    def get_chunks_collection(self):
        return self.chunks_collection
    

    def store_chunks(self,user_id:str,file_id:str,chunks,embeddings,fileName:str):
        logger.info(f"DEBUG: received fileName = '{fileName}'") 
        documents=[]
        for chunk,embedding in zip(chunks,embeddings):
            doc={
                "user_id": user_id,
            "file_id": file_id,
            "fileName":fileName,
            "chunk": chunk,
            "embedding": embedding.tolist() #numpy array to python list
            }
            documents.append(doc)

        self.chunks_collection.insert_many(documents)
        logger.info(f"stored {len(documents)} chunks for {file_id}")



    def update_file_status(self,file_id:str,status:str):
        files_collection=self.database["File"]
        try:
            Object_id=ObjectId(file_id)
        except InvalidId:
            logger.error(f"Invalid file_id format: {file_id}")
            return
        result=files_collection.update_one(
            {"_id":Object_id},
            {"$set":{"EmbeddingStatus":status}}
        )
        if result.matched_count == 0:
            logger.warning(f"No file found with id: {file_id}")
        else:
            logger.info(f"Updated file {file_id} EmbeddingStatus to '{status}'")


    
    def vector_search(self,user_id:str,query_embedding,top_k:int=4):
        results=self.chunks_collection.aggregate([
            {
                "$vectorSearch":{
                    "index":"Docflow_index",
                    "path":"embedding",
                    "queryVector":query_embedding.tolist(),
                    "numCandidates":200,
                    "limit":top_k,
                    "filter":{"user_id":user_id}
                }
            },
            {
                "$project": {
                    "_id":0,
                    "chunk":1,
                    "file_id":1,
                    "fileName":1,
                    "score":{"$meta": "vectorSearchScore"}
                    
            }
            }
        ])
        return list(results)

db=MongoConnection()