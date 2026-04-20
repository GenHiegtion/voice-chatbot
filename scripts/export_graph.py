"""Export chatbot architecture diagrams to statics/.

Run:
    uv run graph.py
"""

from pathlib import Path

from src.agents.graph import get_graph


def export_graph_images(output_dir: Path) -> None:
    """Render and save overview + detailed graph images."""
    output_dir.mkdir(parents=True, exist_ok=True)

    graph = get_graph()
    renders = [
        (False, "overview_graph.png"),
        (True, "detailed_graph.png"),
    ]

    for xray, name in renders:
        png = graph.get_graph(xray=xray).draw_mermaid_png()
        path = output_dir / name
        path.write_bytes(png)
        print(f"Saved: {path}")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    output_dir = project_root / "statics"
    export_graph_images(output_dir)


if __name__ == "__main__":
    main()
