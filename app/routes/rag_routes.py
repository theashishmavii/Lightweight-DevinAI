from flask import Blueprint, request, jsonify
from app.models.rag_engine import generate_file_briefs, rag_query_from_file_list

bp = Blueprint("rag", __name__, url_prefix="/rag")

# ---------------- Endpoint: File Briefs ----------------
@bp.route("/file_briefs", methods=["POST"])
def file_briefs():
    """
    JSON input:
    {
        "file_paths": ["path1", "path2", ...]
    }
    Returns list of file briefs.
    """
    data = request.get_json()
    file_paths = data.get("file_paths", [])

    if not file_paths:
        return jsonify({"error": "No file paths provided"}), 400

    briefs = generate_file_briefs(file_paths)
    return jsonify({"briefs": briefs})


# ---------------- Endpoint: RAG Query ----------------
@bp.route("/query", methods=["POST"])
def rag_query():
    """
    JSON input:
    {
        "file_paths": ["path1", "path2", ...],
        "query": "Your question"
    }
    Returns RAG pipeline result.
    """
    data = request.get_json()
    file_paths = data.get("file_paths", [])
    query = data.get("query", "")

    if not file_paths or not query:
        return jsonify({"error": "File paths or query missing"}), 400

    result = rag_query_from_file_list(file_paths, query)
    return jsonify(result)
