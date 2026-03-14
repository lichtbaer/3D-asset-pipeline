"""Repository-Analyse-Logik in 3 Phasen."""

import os

from github_client import GitHubClient, parse_repo_url
from llm_client import LLMClient
from schemas import Finding, RepoAnalysisOutput, RepoAnalyzerInput


async def analyze(input_payload: dict) -> RepoAnalysisOutput:
    """Führt die 3-Phasen-Analyse durch."""
    inp = RepoAnalyzerInput.model_validate(input_payload)
    owner, repo = parse_repo_url(inp.repo_url)

    gh = GitHubClient(token=os.getenv("GITHUB_TOKEN"))
    llm = LLMClient()

    # Phase 1: Repository-Struktur laden
    files = await gh.get_file_tree(owner, repo, max_files=500)
    file_list = "\n".join(f.get("path", "") for f in files)

    # Code-Samples laden (max 5 pro Kategorie)
    samples = gh.select_code_samples(files, max_per_category=5)
    sample_contents: list[str] = []
    for s in samples:
        path = s.get("path", "")
        try:
            content = await gh.get_file_content(owner, repo, path)
            sample_contents.append(f"--- {path} ---\n{content[:8000]}")
        except Exception:
            sample_contents.append(f"--- {path} ---\n[Fehler beim Laden]")

    samples_text = "\n\n".join(sample_contents)

    # Phase 2: LLM-Analyse (3 Chunks)
    from llm_client import CHUNK1_PROMPT, CHUNK2_PROMPT, CHUNK3_PROMPT

    chunk1_ctx = f"Dateibaum:\n{file_list}\n\n"
    # Einige Konfig-Dateien laden für Chunk 1
    config_files = [f for f in files if any(x in f.get("path", "") for x in ["requirements", "package.json", "pyproject", "Cargo.toml", "go.mod", "Dockerfile"])][:10]
    for cf in config_files:
        try:
            chunk1_ctx += f"\n--- {cf['path']} ---\n"
            chunk1_ctx += (await gh.get_file_content(owner, repo, cf["path"]))[:4000]
        except Exception:
            pass

    r1 = await llm.analyze_chunk(CHUNK1_PROMPT, chunk1_ctx)
    detected_stack = r1.get("detected_stack", [])
    architecture_patterns = r1.get("architecture_patterns", [])

    r2 = await llm.analyze_chunk(CHUNK2_PROMPT, samples_text)
    architecture_patterns = list(dict.fromkeys(architecture_patterns + r2.get("architecture_patterns", [])))

    chunk3_ctx = f"Stack: {detected_stack}\nPatterns: {architecture_patterns}\n\nCode-Samples:\n{samples_text[:30000]}"
    r3 = await llm.analyze_chunk(CHUNK3_PROMPT, chunk3_ctx)
    findings_raw = r3.get("findings", [])
    summary = r3.get("summary", "")

    # Phase 3: Output strukturieren
    findings = [
        Finding(
            title=f.get("title", ""),
            description=f.get("description", ""),
            severity=f.get("severity", "medium"),
            category=f.get("category", "maintainability"),
            file_path=f.get("file_path"),
        )
        for f in findings_raw
    ]

    return RepoAnalysisOutput(
        detected_stack=detected_stack,
        architecture_patterns=architecture_patterns,
        findings=findings,
        summary=summary,
    )
