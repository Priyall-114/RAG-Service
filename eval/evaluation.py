from dotenv import load_dotenv #direct reading from .env file
import os
import pandas as pd
from ragas import EvaluationDataset
from ragas.llms import LangchainLLMWrapper
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.embeddings import LangchainEmbeddingsWrapper
import requests
import time
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
from ragas.run_config import RunConfig


FASTAPI_BASE_URL = "http://127.0.0.1:8000"
QUERY_ENDPOINT = f"{FASTAPI_BASE_URL}/documents/query"
USER_ID="6a97b334f3db8e39d2008f4f"
TOP_K=3
TESTSET_CSV="testset_output_updated.csv"
OUTPUT_CSV_FINAL="eval_results2.csv"
SLEEP_BETWEEN_CALLS = 20 #Saftey margin so that the gemini limit does not reach immediately




load_dotenv(dotenv_path="../.env")
api_key=os.getenv("groq_api_key")
api_key_sh=os.getenv("shreya_groq_api_key")


evaluator_embeddings = LangchainEmbeddingsWrapper(
    HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
)

# naye instances, strictness=1 taaki Groq ka n=1-only limit respect ho
faithfulness_m = Faithfulness()
answer_relevancy_m = AnswerRelevancy(strictness=1)
context_precision_m = ContextPrecision()
context_recall_m = ContextRecall()

evaluator_llm_1 = LangchainLLMWrapper(
    ChatGroq(model="openai/gpt-oss-120b", groq_api_key=api_key,max_tokens=4096,
             model_kwargs={"response_format": {"type": "json_object"}})
)


evaluator_llm_2 = LangchainLLMWrapper(
    ChatGroq(model="openai/gpt-oss-120b", groq_api_key=api_key_sh,max_tokens=4096,
             model_kwargs={"response_format": {"type": "json_object"}})
)



#calling my doc-flow rag service i.e. query endpoint for the questions in testset
def call_rag(question:str) -> dict:
    params={
        "user_id": USER_ID,
        "question": question,
        "top_k": TOP_K
    }
    resp = requests.get(QUERY_ENDPOINT, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    answer = data["response"]["answer"]
    chunks = data["response"]["chunks"]
    chunk_texts = []
    for c in chunks:
        chunk_texts.append(c["chunk"])
    return {"answer": answer, "contexts": chunk_texts}

#looping questions from testeset
def build_eval_rows(testset_df:pd.DataFrame)->list[dict]:
    rows=[]
    total=len(testset_df)
    #i-->row index  row-->complete row
    for i, row in testset_df.iterrows():
        question = row["user_input"]
        reference = row["reference"]
        print(f"[{i+1}/{total}] Querying: {question[:60]}...")
        try:
            result=call_rag(question)
        except Exception as e:
            print(f"!! failed: {e}")
            continue

        rows.append({
            "user_input": question,
            "retrieved_contexts": result["contexts"],
            "response": result["answer"],
            "reference": reference,
        })
        time.sleep(SLEEP_BETWEEN_CALLS)
    return rows


def main():
    testset_df = pd.read_csv(TESTSET_CSV)
    print(f"Loaded testset: {len(testset_df)} questions")

    eval_rows = build_eval_rows(testset_df)
    print(f"Successfully queried {len(eval_rows)}/{len(testset_df)} questions")

    eval_df = pd.DataFrame(eval_rows)
    #Ragas compatible
    eval_dataset = EvaluationDataset.from_pandas(eval_df)


    #Finally evaluating part1 faithfulness and answer relevancy 
    print("Running RAGAS metrics faithfulness_m, answer_relevancy_m")
    result1 = evaluate(
    dataset=eval_dataset,
    metrics=[faithfulness_m, answer_relevancy_m],
    llm=evaluator_llm_1,
    embeddings=evaluator_embeddings,
    run_config=RunConfig(max_workers=2, timeout=300)    
        )

    #Finally evaluating part2 precesion and recall
    result2 = evaluate(
    dataset=eval_dataset,
    metrics=[context_precision_m, context_recall_m],
    llm=evaluator_llm_2,
    embeddings=evaluator_embeddings,
    run_config=RunConfig(max_workers=2, timeout=300)
        )

    result1_df = result1.to_pandas()
    result2_df = result2.to_pandas()

    result_df = pd.concat(
        [
            result1_df,
            result2_df[["context_precision", "context_recall"]]
        ],
        axis=1
    )


   
    result_df.to_csv(OUTPUT_CSV_FINAL, index=False, encoding="utf-8-sig")
    print(f"Saved eval results to {OUTPUT_CSV_FINAL}")
    print(result_df[["faithfulness", "answer_relevancy", "context_precision", "context_recall"]].mean())


main()