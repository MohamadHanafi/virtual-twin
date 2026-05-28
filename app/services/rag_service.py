from functools import lru_cache
import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.constants.paths import PROJECT_ROOT
from app.constants.rag import (
    CHROMA_DIR,
    COLLECTION_NAME,
    EMBEDDING_DEVICE,
    EMBEDDING_MODEL,
    HF_TOKEN_ENV,
    NORMALIZE_EMBEDDINGS,
)
from app.models import Source

load_dotenv(PROJECT_ROOT / ".env")


@lru_cache(maxsize=1)
def get_embedding_model():
    model_kwargs = {"device": EMBEDDING_DEVICE}
    hf_token = os.getenv(HF_TOKEN_ENV)
    if hf_token:
        model_kwargs["token"] = hf_token

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs=model_kwargs,
        encode_kwargs={"normalize_embeddings": NORMALIZE_EMBEDDINGS},
    )


@lru_cache(maxsize=1)
def get_vector_store():
    if not CHROMA_DIR.exists():
        raise FileNotFoundError(f"Chroma vector database not found: {CHROMA_DIR}")

    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(CHROMA_DIR),
        embedding_function=get_embedding_model(),
    )


def retrieve_context(query: str, k: int = 5):
    vector_store = get_vector_store()
    mmr_documents = vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": k, "fetch_k": max(k * 4, 12)},
    ).invoke(query)
    similarity_documents = vector_store.similarity_search(query, k=k)

    documents = []
    seen = set()

    for document in [*similarity_documents, *mmr_documents]:
        key = (
            document.metadata.get("source_file"),
            document.metadata.get("page"),
            document.metadata.get("chunk_index"),
            document.page_content[:120],
        )
        if key in seen:
            continue

        seen.add(key)
        documents.append(document)

        if len(documents) >= k:
            break

    return documents


def format_documents_for_prompt(documents) -> str:
    context_blocks = []

    for index, document in enumerate(documents, start=1):
        source = document.metadata.get("source_file", "unknown source")
        page = document.metadata.get("page", "unknown page")
        text = document.page_content.strip()
        context_blocks.append(f"[Source {index}: {source}, page {page}]\n{text}")

    return "\n\n".join(context_blocks)


def document_sources(documents) -> list[Source]:
    return [
        Source(
            source_file=document.metadata.get("source_file"),
            page=document.metadata.get("page"),
            chunk_index=document.metadata.get("chunk_index"),
        )
        for document in documents
    ]
