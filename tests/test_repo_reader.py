import pytest

import sys
import os

sys.path.append(os.path.abspath('C:/GithubProject/Lightweight-DevinAI'))  # Adjust the relative path

from app.services.repo_reader import RepoReader

def test_metadata_fetch():
    reader = RepoReader()
    data = reader.get_metadata("https://github.com/psf/requests")
    print("Fetched metadata:", data)
    assert "name" in data
    assert data["name"] == "requests"

