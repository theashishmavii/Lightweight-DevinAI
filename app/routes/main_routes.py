from flask import Blueprint, request, jsonify
from app.services.repo_reader import RepoReader

main_bp = Blueprint("main", __name__)

@main_bp.route("/read_repo", methods=["POST"])
def read_repo():
    data = request.json
    repo_url = data.get("repo_url")

    if not repo_url:
        return jsonify({"error": "repo_url is required"}), 400

    reader = RepoReader()
    try:
        result = reader.process_repo(repo_url)
        return jsonify({
            "repo_name": result["metadata"].get("name"),
            "description": result["metadata"].get("description"),
            "files": result["files"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
