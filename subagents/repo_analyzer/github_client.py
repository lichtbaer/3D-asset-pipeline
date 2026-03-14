"""GitHub API Wrapper für Repository-Struktur und Dateiinhalte."""

import re
from urllib.parse import urlparse

import httpx

# Relevante Dateien für Stack-Erkennung (max 500 gesamt)
RELEVANT_PATTERNS = [
    r"\.toml$",
    r"\.json$",
    r"\.yaml$",
    r"\.yml$",
    r"Dockerfile",
    r"\.md$",
    r"requirements.*\.txt$",
    r"package\.json$",
    r"package-lock\.json$",
    r"yarn\.lock$",
    r"pnpm-lock\.yaml$",
    r"\.py$",
    r"\.ts$",
    r"\.tsx$",
    r"\.js$",
    r"\.jsx$",
    r"\.go$",
    r"\.rs$",
    r"\.java$",
    r"\.kt$",
    r"Cargo\.toml$",
    r"go\.mod$",
    r"pom\.xml$",
    r"build\.gradle",
    r"\.gradle$",
    r"\.csproj$",
    r"\.sln$",
]

# Kategorien für Code-Samples (max 5 pro Kategorie)
BACKEND_PATTERNS = [r"\.py$", r"\.go$", r"\.rs$", r"\.java$", r"\.kt$", r"\.cs$"]
FRONTEND_PATTERNS = [r"\.tsx?$", r"\.jsx?$", r"\.vue$", r"\.svelte$"]
TEST_PATTERNS = [r"test_.*\.py$", r".*_test\.(py|go|rs|java)$", r"\.test\.(ts|tsx|js)$"]


def _compile_patterns(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _matches_any(path: str, patterns: list[re.Pattern]) -> bool:
    return any(p.search(path) for p in patterns)


def parse_repo_url(repo_url: str) -> tuple[str, str]:
    """Extrahiert owner und repo aus GitHub-URL."""
    # https://github.com/owner/repo oder https://github.com/owner/repo.git
    parsed = urlparse(repo_url)
    path = parsed.path.strip("/").replace(".git", "")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Ungültige Repo-URL: {repo_url}")
    return parts[0], parts[1]


class GitHubClient:
    """Async GitHub API Client."""

    def __init__(self, token: str | None = None, base_url: str = "https://api.github.com"):
        self.token = token
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "repo-analyzer/1.0",
        }
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    async def get_file_tree(self, owner: str, repo: str, max_files: int = 500) -> list[dict]:
        """Lädt den rekursiven Dateibaum (Git Trees API)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Default-Branch holen
            repo_resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=self._headers,
            )
            repo_resp.raise_for_status()
            default_branch = repo_resp.json().get("default_branch", "main")

            # Tree rekursiv laden
            tree_resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/git/trees/{default_branch}",
                headers=self._headers,
                params={"recursive": "1"},
            )
            tree_resp.raise_for_status()
            data = tree_resp.json()
            tree = data.get("tree", [])

        # Nur Dateien (keine Blobs mit type=tree)
        files = [e for e in tree if e.get("type") == "blob"]
        relevant_patterns = _compile_patterns(RELEVANT_PATTERNS)
        relevant = [f for f in files if _matches_any(f.get("path", ""), relevant_patterns)]

        return relevant[:max_files]

    async def get_file_content(self, owner: str, repo: str, path: str) -> str:
        """Lädt den Inhalt einer Datei (Base64-dekodiert)."""
        import base64

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.base_url}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return data.get("content", "")

    def select_code_samples(
        self, files: list[dict], max_per_category: int = 5
    ) -> list[dict]:
        """Wählt max 5 repräsentative Dateien pro Kategorie (Backend, Frontend, Tests)."""
        backend_p = _compile_patterns(BACKEND_PATTERNS)
        frontend_p = _compile_patterns(FRONTEND_PATTERNS)
        test_p = _compile_patterns(TEST_PATTERNS)

        backend: list[dict] = []
        frontend: list[dict] = []
        tests: list[dict] = []

        for f in files:
            path = f.get("path", "")
            if _matches_any(path, test_p):
                if len(tests) < max_per_category:
                    tests.append(f)
            elif _matches_any(path, frontend_p):
                if len(frontend) < max_per_category:
                    frontend.append(f)
            elif _matches_any(path, backend_p):
                if len(backend) < max_per_category:
                    backend.append(f)

        return backend + frontend + tests
