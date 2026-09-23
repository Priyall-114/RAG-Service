from dotenv import load_dotenv #direct reading from .env file
import os
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
import pdfplumber
import re
from langchain_core.documents import Document
from ragas.testset import TestsetGenerator
from ragas.testset.transforms import default_transforms,apply_transforms
from ragas.testset.graph import KnowledgeGraph,Node,NodeType,Relationship
from langchain_text_splitters import RecursiveCharacterTextSplitter
import logging


load_dotenv(dotenv_path="../.env")

api_key=os.getenv("groq_api_key")
print("key loaded",api_key is not None)
generator_llm = LangchainLLMWrapper(
    ChatGroq(model="openai/gpt-oss-120b", groq_api_key=api_key,  model_kwargs={"response_format": {"type": "json_object"}})
)
generator_embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
)

print("LLM ready:", generator_llm is not None)
print("Embeddings ready:", generator_embeddings is not None)




def _clean_text(text: str) -> str:
    
    text = re.sub(r'\n{3,}', '\n\n', text)#removes 3 or more newlines
    text = re.sub(r' {2,}', ' ', text)#removes multiple in  between spaces
    text = re.sub(r'[\uE000-\uF8FF]', '', text)
    return text.strip()

# RAGAS ka TestsetGenerator LangChain ke Document type expect karta hai
def load_pdfs_as_document(folder_path:str) -> list[Document]:
    documents=[]
    for filename in os.listdir(folder_path):
        if not filename.endswith(".pdf"):
            continue
        filepath=os.path.join(folder_path,filename)
        full_content=""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_content += _clean_text(text) + "\n"
        documents.append(
            Document(page_content=full_content.strip(), metadata={"source": filename})
        )
    return documents

docs = load_pdfs_as_document("sample_docs")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100
)




kg=KnowledgeGraph()

for doc in docs:
    # Poori PDF ka apna DOCUMENT node — SummaryExtractor isi pe chalega
    doc_node = Node(
        type=NodeType.DOCUMENT,
        properties={
            "page_content": doc.page_content,
            "document_metadata": doc.metadata
        }
    )
    kg.nodes.append(doc_node)



    chunks = splitter.split_text(doc.page_content)
    for chunk in chunks:
        chunk_node = Node(
                type=NodeType.CHUNK,
                properties={
                    "page_content": chunk,
                    "document_metadata": doc.metadata
                }
            )
        kg.nodes.append(chunk_node)



#Making up the missing relationship between chunk and document it belongs since removing Healdine tranformation removed this step too
        kg.relationships.append(
            Relationship(
            source=doc_node,
            target=chunk_node,
            type="child",
            properties={}
            )
        )

logging.info("Parent-child relationships created!")



transforms=default_transforms(
    documents=docs,
    llm=generator_llm,
    embedding_model=generator_embeddings,
    

)

transforms = [t for t in transforms if "Headline" not in type(t).__name__]
# #for checking purpose----
# for t in transforms:
#     print(type(t).__name__)

#     if hasattr(t, "transforms"):
#         for sub_t in t.transforms:
#             print("   ->", type(sub_t).__name__)



apply_transforms(kg, transforms)
print("Total nodes in graph:", len(kg.nodes))
for node in kg.nodes:
    print(node.type, list(node.properties.keys()))

generator=TestsetGenerator(
    llm=generator_llm,
    embedding_model=generator_embeddings,
    knowledge_graph=kg
)
testset = generator.generate(testset_size=10)
#view what dataset has been  generated
df=testset.to_pandas()
df.to_csv("testset_output_updated.csv",index=False)
print("Testset generated,rows:",testset.to_pandas())
