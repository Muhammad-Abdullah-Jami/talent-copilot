# services/github_ingestor.py
# Crawls a public GitHub repo via the GitHub REST API.
#
# What it extracts:
#   1. Repo metadata (name, description, stars, language)
#   2. README content
#   3. File tree (top-level + one depth)
#   4. Language breakdown
#   5. Lightweight code snippets from key files
#
# Uses httpx for HTTP requests (async-capable, modern alternative to requests)
# Respects GitHub rate limits with retry/backoff

import json
import time
import httpx
from backend.config import GITHUB_TOKEN


# GitHub API base URL
GITHUB_API = "https://api.github.com"

# Headers for authentication — token increases rate limit from 60 to 5000/hour
HEADERS = {
    "Accept": "application/vnd.github.v3+json"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"


def parse_repo_url(repo_url: str) -> tuple:
    """
    Extract owner and repo name from a GitHub URL.
    
    Examples:
        https://github.com/facebook/react → ("facebook", "react")
        https://github.com/facebook/react/tree/main → ("facebook", "react")
    """
    # Remove trailing slash and .git
    url = repo_url.rstrip("/").replace(".git", "")

    parts = url.split("github.com/")
    if len(parts) != 2:
        raise ValueError(f"Invalid GitHub URL: {repo_url}")

    path_parts = parts[1].split("/")
    if len(path_parts) < 2:
        raise ValueError(f"Cannot extract owner/repo from: {repo_url}")

    owner = path_parts[0]
    repo = path_parts[1]

    return owner, repo


def github_get(url: str, retries: int = 3) -> dict:
    """
    Make a GET request to GitHub API with retry/backoff.
    
    If rate limited (status 403), wait and retry.
    Retries up to 3 times with exponential backoff.
    """
    for attempt in range(retries):
        response = httpx.get(url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 403:
            # Rate limited — wait and retry
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            print(f"Rate limited. Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
        elif response.status_code == 404:
            raise ValueError(f"Repository not found: {url}")
        else:
            raise ValueError(f"GitHub API error {response.status_code}: {response.text}")

    raise ValueError("GitHub API rate limit exceeded. Try again later.")


def get_repo_metadata(owner: str, repo: str) -> dict:
    """Get basic repo info: name, description, stars, language, etc."""
    data = github_get(f"{GITHUB_API}/repos/{owner}/{repo}")

    return {
        "name": data.get("full_name"),
        "description": data.get("description"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "default_branch": data.get("default_branch", "main"),
        "primary_language": data.get("language"),
        "created_at": data.get("created_at"),
        "updated_at": data.get("updated_at")
    }


def get_readme(owner: str, repo: str) -> str:
    """
    Get README content. GitHub API returns it base64 encoded.
    We decode it to plain text.
    """
    try:
        import base64
        data = github_get(f"{GITHUB_API}/repos/{owner}/{repo}/readme")
        content = data.get("content", "")
        # GitHub returns base64-encoded content
        decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        return decoded
    except ValueError:
        return "No README found."


def get_file_tree(owner: str, repo: str, branch: str = "main") -> list:
    """
    Get the file/folder structure of the repo.
    
    Uses the Git Trees API with recursive=1 to get all files.
    We limit to first 100 items to keep it manageable.
    """
    try:
        data = github_get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        )
        tree = data.get("tree", [])

        # Return first 100 items with path and type
        return [
            {"path": item["path"], "type": item["type"]}
            for item in tree[:100]
        ]
    except ValueError:
        return []


def get_languages(owner: str, repo: str) -> dict:
    """
    Get language breakdown (bytes per language).
    Returns like: {"Python": 45000, "JavaScript": 12000}
    """
    try:
        data = github_get(f"{GITHUB_API}/repos/{owner}/{repo}/languages")
        return data
    except ValueError:
        return {}


def detect_stack_signals(file_tree: list, languages: dict) -> list:
    """
    Heuristic detection of tech stack from file names and languages.
    
    Looks for common config files that indicate specific technologies.
    This is a simple pattern-matching approach.
    """
    signals = []
    file_paths = [item["path"].lower() for item in file_tree]

    # Check for common framework/tool indicators
    indicators = {
        "requirements.txt": "Python (pip)",
        "setup.py": "Python package",
        "pyproject.toml": "Python (modern)",
        "package.json": "Node.js / JavaScript",
        "tsconfig.json": "TypeScript",
        "cargo.toml": "Rust",
        "go.mod": "Go",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java/Kotlin (Gradle)",
        "dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        ".github/workflows": "GitHub Actions CI/CD",
        "next.config.js": "Next.js",
        "nuxt.config.js": "Nuxt.js",
        "angular.json": "Angular",
        "vite.config": "Vite",
        "webpack.config": "Webpack",
        "tailwind.config": "Tailwind CSS",
        ".env": "Environment variables",
        "prisma": "Prisma ORM",
        "alembic": "SQLAlchemy Migrations",
        "manage.py": "Django",
        "app.py": "Flask/FastAPI",
    }

    for path_pattern, signal in indicators.items():
        for file_path in file_paths:
            if path_pattern in file_path:
                signals.append(signal)
                break

    # Add top languages
    for lang in list(languages.keys())[:5]:
        signals.append(f"Language: {lang}")

    return list(set(signals))  # remove duplicates


def get_key_file_snippets(owner: str, repo: str, file_tree: list) -> list:
    """
    Extract text from a few key files for retrieval.
    
    We pick important files like README, config files, and
    a few source files. Limited to 5 files, 500 lines each.
    """
    import base64

    # Files we want to read (in priority order)
    priority_files = [
        "readme.md", "readme.txt", "readme",
        "requirements.txt", "package.json", "pyproject.toml",
        "setup.py", "cargo.toml", "go.mod",
        "dockerfile", "docker-compose.yml",
    ]

    # Also grab a few source files
    source_extensions = (".py", ".js", ".ts", ".java", ".go", ".rs", ".rb")

    files_to_fetch = []

    # Add priority files
    for item in file_tree:
        if item["type"] == "blob" and item["path"].lower() in priority_files:
            files_to_fetch.append(item["path"])

    # Add first 3 source files
    source_count = 0
    for item in file_tree:
        if source_count >= 3:
            break
        if item["type"] == "blob" and item["path"].lower().endswith(source_extensions):
            files_to_fetch.append(item["path"])
            source_count += 1

    # Fetch content for each file
    snippets = []
    for file_path in files_to_fetch[:5]:  # max 5 files
        try:
            data = github_get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contents/{file_path}"
            )
            content = data.get("content", "")
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")

            # Limit to 500 lines
            lines = decoded.split("\n")[:500]
            snippets.append({
                "path": file_path,
                "content": "\n".join(lines)
            })
        except (ValueError, Exception):
            continue

    return snippets


def ingest_repo(repo_url: str) -> dict:
    """
    Main ingestion function — called by the job runner.
    
    Orchestrates all the extraction steps and returns
    a complete repo profile ready for DB storage.
    
    This is IDEMPOTENT — running it twice on the same repo
    gives the same result (important for retries).
    """
    owner, repo = parse_repo_url(repo_url)

    # Step 1: Basic metadata
    metadata = get_repo_metadata(owner, repo)

    # Step 2: README
    readme = get_readme(owner, repo)

    # Step 3: File tree
    branch = metadata.get("default_branch", "main")
    file_tree = get_file_tree(owner, repo, branch)

    # Step 4: Languages
    languages = get_languages(owner, repo)

    # Step 5: Stack signals
    stack_signals = detect_stack_signals(file_tree, languages)

    # Step 6: Key file snippets
    snippets = get_key_file_snippets(owner, repo, file_tree)

    return {
        "repo_url": repo_url,
        "repo_name": metadata.get("name"),
        "metadata": metadata,
        "readme_content": readme,
        "file_tree": file_tree,
        "languages": languages,
        "stack_signals": stack_signals,
        "code_snippets": snippets
    }