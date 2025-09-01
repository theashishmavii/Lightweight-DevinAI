import os
import tempfile
import requests
from git import Repo
from app.utils.file_utils import list_files
from app.utils.logger import get_logger

logger = get_logger(__name__)

class RepoReader:
    def __init__(self, token=None):
        self.token = token or os.getenv("GITHUB_TOKEN")

    def get_metadata(self, repo_url: str):
        """Fetch repo metadata from GitHub API"""
        repo_name = repo_url.rstrip("/").split("/")[-2:]
        repo_path = "/".join(repo_name)
        api_url = f"https://api.github.com/repos/{repo_path}"

        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        resp = requests.get(api_url, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"GitHub API Error: {resp.text}")
        return resp.json()

    def clone_repo(self, repo_url: str):
        """Clone repo into temp dir and return path"""
        tmp_dir = tempfile.mkdtemp()
        logger.info(f"Cloning {repo_url} into {tmp_dir}")
        Repo.clone_from(repo_url, tmp_dir)
        return tmp_dir

    def process_repo(self, repo_url: str):
        """Return metadata + file structure"""
        metadata = self.get_metadata(repo_url)
        local_path = self.clone_repo(repo_url)
        files = list_files(local_path)

        return {
            "metadata": metadata,
            "files": files
        }
