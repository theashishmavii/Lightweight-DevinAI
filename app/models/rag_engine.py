import os
from dotenv import load_dotenv
load_dotenv()

import time
from typing import List, Dict, Tuple, Optional

import chromadb
from chromadb.utils import embedding_functions

import ollama

from langchain.text_splitter import RecursiveCharacterTextSplitter


# ---------------- CONFIG ----------------
SUPPORTED_EXTENSIONS = (".py", ".html", ".js", ".md", ".txt", ".json", ".yaml", ".yml", ".css", ".java",
                        ".c", ".cpp", ".rb", ".go", ".rs", ".ts", ".tsx", ".jsx", ".xml", ".ini", ".cfg",
                        ".toml", ".docx", ".csv", ".ipynb")
CHROMA_DIR_DEFAULT = "chroma_db"
COLLECTION_NAME = "repo_docs"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 100

# ---------------- HELPERS ----------------
def _is_supported(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    return ext in SUPPORTED_EXTENSIONS

def _read_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ Could not read {path}: {e}")
        return None

def _make_text_splitter(chunk_size=DEFAULT_CHUNK_SIZE, chunk_overlap=DEFAULT_CHUNK_OVERLAP):
    if RecursiveCharacterTextSplitter:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        return splitter.split_text
    else:
        # Simple fallback splitter
        def split_text(text: str):
            chunks = []
            i = 0
            L = len(text)
            if L <= chunk_size:
                return [text]
            step = chunk_size - chunk_overlap
            while i < L:
                chunk = text[i : i + chunk_size]
                chunks.append(chunk)
                i += step
            return chunks
        return split_text
    
# ---------------- FILE BRIEFS USING LLM ----------------
def generate_file_briefs(file_paths: List[str]) -> List[Dict]:
    """
    Reads the whole file, asks LLM to summarize it briefly.
    Returns a list of dicts with: path, extension, brief (LLM summary)
    """
    briefs = []
    for path in file_paths:
        if not _is_supported(path) or not os.path.exists(path):
            continue
        content = _read_file(path)
        if not content:
            briefs.append({
                "path": path,
                "extension": os.path.splitext(path)[1],
                "brief": "Could not read file"
            })
            continue

        prompt = f"""
                    You are a helpful AI assistant. Read the following file content and provide a **short, beginner-friendly summary**:
                    Include the purpose of the file and main components. Be concise.

                    File content:
                    {content}

                    Summary:
                    """
        try:
            resp = ollama.chat(
                model="phi3:mini",
                messages=[{"role": "user", "content": prompt}]
            )
            summary = resp["message"]["content"]
        except Exception as e:
            summary = f"Error generating summary: {e}"

        briefs.append({
            "path": path,
            "extension": os.path.splitext(path)[1],
            "brief": summary
        })
    return briefs

# ---------------- CHROMA INIT ----------------
def init_chroma(persist_dir=CHROMA_DIR_DEFAULT):
    """Initialize Chroma persistent client and collection."""
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        embedding_function=ef
    )
    return client, collection

# ---------------- INDEXING ----------------
def index_file_list(
    file_paths: List[str],
    persist_dir: str = CHROMA_DIR_DEFAULT,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> Dict:
    """Read, chunk, and embed files into ChromaDB (re-embedding every run)."""
    client, collection = init_chroma(persist_dir)
    splitter = _make_text_splitter(chunk_size, chunk_overlap)

    added = 0
    skipped = 0
    errors = []

    for path in file_paths:
        if not _is_supported(path):
            skipped += 1
            continue
        if not os.path.exists(path):
            errors.append({"path": path, "error": "not found"})
            continue
        txt = _read_file(path)
        if not txt:
            errors.append({"path": path, "error": "could not read"})
            continue
        chunks = splitter(txt)
        ids, docs, metas = [], [], []
        for i, chunk in enumerate(chunks):
            doc_id = f"{path}::chunk::{i}"
            ids.append(doc_id)
            docs.append(chunk)
            metas.append({"source": path, "chunk_index": i, "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")})
        try:
            collection.add(documents=docs, ids=ids, metadatas=metas)
            added += len(docs)
        except Exception as e:
            errors.append({"path": path, "error": str(e)})

    # Persist collection
    try:
        collection.persist()
    except Exception:
        pass

    return {"added_chunks": added, "skipped_files": skipped, "errors": errors}

# ---------------- RETRIEVAL ----------------
def retrieve_context(query: str, top_k: int = 4, persist_dir: str = CHROMA_DIR_DEFAULT) -> Tuple[List[str], List[Dict]]:
    """Retrieve top-k chunks from ChromaDB for a query."""
    _, collection = init_chroma(persist_dir)
    results = collection.query(query_texts=[query], n_results=top_k)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return docs, metas

# ---------------- LLM ANSWER ----------------
def generate_answer_from_context(query: str, context_docs: List[str]) -> str:
    """Use Ollama chat model to answer query based on retrieved context."""

    context_text = "\n\n---\n\n".join(context_docs) if context_docs else "No context available."

    prompt = f"""
                You are an assistant explaining code and repository contents.
                Use only the context below (no hallucination).
                Provide a short summary, beginner-friendly explanation, and mention file paths used.

                Context:
                {context_text}

                Question:
                {query}

                Answer:
                """
    resp = ollama.chat(
        model="phi3:mini",
        messages=[{"role": "user", "content": prompt}]
    )
    try:
        return resp.get("message", {}).get("content", "")
    except Exception as e:
        return f"Error generating answer: {e}"

# ---------------- FULL PIPELINE ----------------
def rag_query_from_file_list(
    file_paths: List[str],
    query: str,
    persist_dir: str = CHROMA_DIR_DEFAULT,
    top_k: int = 4,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> Dict:
    """
    1) Index files (re-embed)
    2) Retrieve top-k chunks
    3) Ask LLM to answer
    Returns: dict with answer, sources, chunks, index stats
    """
    stats = index_file_list(file_paths, persist_dir, chunk_size, chunk_overlap)
    docs, metas = retrieve_context(query, top_k, persist_dir)
    answer = generate_answer_from_context(query, docs)
    return {"answer": answer, "sources": metas, "chunks": docs, "index_stats": stats}
