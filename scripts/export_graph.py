"""Export LangGraph chatbot architecture as PNG images."""

import os
import sys
from pathlib import Path

# Add project root to Python path (works from any directory)
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from src.agents.graph import get_graph  # noqa: E402


def main():
    docs_dir = os.path.join(PROJECT_ROOT, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    graph = get_graph()

    for xray, name in [(False, "overview_graph.png"), (True, "detailed_graph.png")]:
        png = graph.get_graph(xray=xray).draw_mermaid_png()
        path = os.path.join(docs_dir, name)
        with open(path, "wb") as f:
            f.write(png)
        print(f"✅ {name}")

    print(f"\nSaved to: {docs_dir}/")


if __name__ == "__main__":
    main()
