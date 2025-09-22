## Lightweight DevinAI

An end-to-end, minimal GitHub repository explorer with RAG (Retrieval-Augmented Generation) powered explanations. It lets you:

- Fetch public GitHub repo metadata and structure via a simple web UI
- Visualize the repository tree
- Generate brief summaries for files with an LLM
- Ask questions about the repo using a lightweight RAG pipeline (ChromaDB + Sentence-Transformers + Groq LLM)

Built with Flask, ChromaDB, Sentence-Transformers, and Groq.

---

### Key Features

- GitHub metadata fetch and lightweight clone to temp directory
- File tree visualization with jsTree in a clean Bootstrap UI
- File brief generation via Groq LLM for quick understanding
- RAG pipeline: index selected files, retrieve relevant chunks, generate an answer
- Simple REST endpoints, easy to integrate or extend

---

### Architecture Overview

- `run.py` – Flask app entrypoint; mounts `index.html` UI at `/`.
- `app/__init__.py` – App factory; registers blueprints.
- `app/routes/main_routes.py` – Endpoint to fetch repo metadata and file list.
- `app/routes/rag_routes.py` – Endpoints for file briefs and RAG queries.
- `app/services/repo_reader.py` – Clones GitHub repo to a temp folder, fetches metadata via GitHub API, and lists files.
- `app/models/rag_engine.py` – Core RAG utilities: indexing files with ChromaDB, retrieving top-k context, and calling Groq LLM.
- `app/utils/file_utils.py` – Recursively lists files, skipping common noise.
- `app/utils/logger.py` – Minimal logging setup.
- `app/templates/index.html` – Single-page UI (Bootstrap + jsTree + vanilla JS) to drive the flow.
- `chroma_db/` – Default Chroma persistent store path if you choose to persist outside the per-run temp index.

Data flow at a glance:

1) UI posts a GitHub URL → `/read_repo`
2) Server fetches metadata + clones to temp → returns file list
3) UI displays tree + requests `/rag/file_briefs` with those paths
4) UI can submit a question to `/rag/query` → indexes files, retrieves context, calls LLM, returns an answer

---

### Live Demo Video

Add your demo link here once available:

`[Demo: Lightweight DevinAI in action](https://your-demo-link.example)`

---

### Quickstart

Prerequisites:

- Python 3.10+ (tested with 3.13)
- Git installed (for cloning repos)

Environment variables (create a `.env` at repo root):

```
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=optional_github_token_for_higher_rate_limits
# Optional: where to persist a local Chroma store (used by rag_engine defaults)
CHROMA_DIR=chroma_db
```

Install dependencies:

Option A: Use the provided `requirements.txt` (comprehensive, includes many tools used in broader environments):

```bash
pip install -r requirements.txt
```

Option B: Minimal install for this project only (recommended if you want a lean environment):

```bash
pip install flask requests gitpython python-dotenv chromadb sentence-transformers groq langchain
```

Run the app:

```bash
python run.py
```

Open `http://127.0.0.1:5000/` in your browser.

On Windows PowerShell:

```powershell
py -3 run.py
```

---

### UI Walkthrough

1) Enter a public GitHub repo URL (e.g., `https://github.com/psf/requests`) and click “Fetch Repository”.
2) The app fetches metadata and shows a tree of files.
3) It requests file briefs from the backend (LLM-generated summaries) and lists them.
4) Type a question about the codebase and submit to see a RAG-generated answer.

Notes:

- File briefs and RAG respect a list of supported file extensions (see `SUPPORTED_EXTENSIONS` in `app/models/rag_engine.py`).
- RAG indexing currently re-embeds files on each query for simplicity.

---

### REST API

Base URL: `http://localhost:5000`

- `POST /read_repo`
  - Body:
    ```json
    { "repo_url": "https://github.com/username/repo" }
    ```
  - Response:
    ```json
    {
      "repo_name": "owner/repo",
      "description": "...",
      "files": ["path/to/file1.py", "dir/file2.js", ...]
    }
    ```

- `POST /rag/file_briefs`
  - Body:
    ```json
    { "file_paths": ["path1", "path2", "..."] }
    ```
  - Response:
    ```json
    { "briefs": [ {"path": "...", "extension": ".py", "brief": "..."}, ... ] }
    ```

- `POST /rag/query`
  - Body:
    ```json
    { "file_paths": ["path1", "path2", "..."], "query": "Your question" }
    ```
  - Response:
    ```json
    {
      "answer": "...",
      "sources": [{"source": "path", "chunk_index": 0, ...}, ...],
      "chunks": ["text chunk 1", "text chunk 2", ...],
      "index_stats": {"added_chunks": N, "skipped_files": M, "errors": []}
    }
    ```

Example cURL calls:

```bash
curl -X POST http://localhost:5000/read_repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/psf/requests"}'

curl -X POST http://localhost:5000/rag/file_briefs \
  -H "Content-Type: application/json" \
  -d '{"file_paths":["README.md","src/__init__.py"]}'

curl -X POST http://localhost:5000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"file_paths":["README.md"],"query":"What does this project do?"}'
```

---

### RAG Internals

- Embeddings: `all-MiniLM-L6-v2` via `SentenceTransformerEmbeddingFunction`.
- Vector store: Chroma persistent client (`app/models/rag_engine.py::init_chroma`).
- Chunking: `RecursiveCharacterTextSplitter` (fallback splitter included) with defaults:
  - `DEFAULT_CHUNK_SIZE = 800`
  - `DEFAULT_CHUNK_OVERLAP = 100`
- Retrieval: `collection.query(n_results=top_k)` with `top_k` default 4.
- LLM: Groq chat completions (`llama-3.1-8b-instant` by default).

You can tune chunk size/overlap and `top_k` via function params in `rag_engine.py` or by adjusting defaults.

---

### Configuration and Environment

- `GROQ_API_KEY` – Required for Groq LLM calls.
- `GITHUB_TOKEN` – Optional; increases GitHub API rate limits and allows private repos if permitted.
- `CHROMA_DIR` – Optional; directory to persist Chroma data. Defaults to `chroma_db`.

Supported file extensions are defined in `SUPPORTED_EXTENSIONS` and include common code and text formats (e.g., `.py`, `.js`, `.ts`, `.md`, `.json`, `.yaml`, `.java`, `.cpp`, `.ipynb`, etc.).

---

### Testing

Pytest example included for GitHub metadata fetch:

```bash
pytest -q
```

Test file: `tests/test_repo_reader.py`.

Note: This test hits the live GitHub API. Provide `GITHUB_TOKEN` to avoid rate-limits.

---

### Development Notes

- The UI uses jsTree for rendering the repo structure and Bootstrap for styling.
- `RepoReader` uses GitPython to clone repos to a temp directory, then `file_utils.list_files` to enumerate paths.
- The RAG `/rag/query` endpoint re-indexes on each call to keep logic simple. For performance, you could cache per-repo indices.
- Logging is basic and prints INFO-level logs.

---

### Troubleshooting

- Groq errors or empty summaries: ensure `GROQ_API_KEY` is set and valid.
- GitHub API errors: set `GITHUB_TOKEN` or wait for rate-limit reset.
- Missing modules: if `pip install -r requirements.txt` doesn’t include some libraries, run the minimal install command shown above. Ensure these are installed: `flask`, `requests`, `gitpython`, `python-dotenv`, `chromadb`, `sentence-transformers`, `groq`, `langchain`.
- Windows path issues in tests: adjust `sys.path.append(...)` in `tests/test_repo_reader.py` to your local repo path if needed.

---

### Extending

- Swap embeddings: change `SentenceTransformerEmbeddingFunction` model.
- Swap vector store: replace Chroma with another store (e.g., Qdrant).
- Add auth/rate limiting to endpoints.
- Persist per-repo indices and introduce cache invalidation.
- Add file content previews and selective indexing from the UI.

---

### Security Considerations

- Do not expose your `GROQ_API_KEY` publicly.
- Cloned repos are stored in temp directories; clear them if running long-lived servers.
- Validate input URLs and consider restricting to github.com domain.

---

### License

Add your license of choice here (e.g., MIT). If you include a `LICENSE` file, reference it here.

---

### Acknowledgments

- ChromaDB team for the vector database
- Sentence-Transformers for embeddings
- Groq for the LLM API
- Flask and the broader Python ecosystem

