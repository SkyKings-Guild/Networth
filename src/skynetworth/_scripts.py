from pathlib import Path
import subprocess


def export_docs_requirements() -> None:
    """Export the docs dependency group for external build environments."""
    repository_root = Path(__file__).resolve().parents[2]
    subprocess.run(
        [
            "uv",
            "export",
            "--group",
            "docs",
            "--no-emit-project",
            "--format",
            "requirements.txt",
            "--output-file",
            "docs/requirements.txt",
        ],
        cwd=repository_root,
        check=True,
    )
