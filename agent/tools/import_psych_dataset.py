"""
Import the local psychology / education dataset into the default RAG collection.

This script normalizes the external dataset folder into loader-compatible
documents, adds structured metadata, and ingests everything into the shared
`knowledge_base` collection that the agent already queries.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIR = PROJECT_ROOT.parent / "心理教育数据集收集"
AGENT_ROOT = PROJECT_ROOT / "agent"

if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from loader import Document, load_md, load_txt


def infer_user_type(path: Path) -> str:
    name = path.stem + " " + str(path.parent)
    if "家长" in name:
        return "parent"
    if "教师" in name:
        return "teacher"
    return "student"


def infer_category(path: Path) -> str:
    parts = [part for part in path.parts]
    if "knowledge_base" in parts:
        return "knowledge_base"
    if "case_library" in parts:
        return "case_library"
    if "terminology" in parts:
        return "terminology"
    if "reference_documents" in parts:
        return "reference_document"
    if "user_profiles" in parts:
        return "user_profiles"
    return path.suffix.lstrip(".") or "document"


def read_text_documents(dataset_dir: Path) -> List[Document]:
    documents: List[Document] = []
    for path in dataset_dir.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".md", ".txt"}:
            continue

        relative_path = path.relative_to(dataset_dir)
        loaded = load_md(str(path)) if suffix == ".md" else load_txt(str(path))
        for doc in loaded:
            doc.metadata.update(
                {
                    "dataset_group": infer_category(path),
                    "dataset_user_type": infer_user_type(path),
                    "dataset_relative_path": str(relative_path).replace("\\", "/"),
                    "dataset_source": "psychology_education_dataset",
                }
            )
            documents.append(doc)
    return documents


def _term_entry_to_document(
    *,
    group_name: str,
    entry: Dict[str, Any],
    source_path: Path,
    dataset_dir: Path,
) -> Document:
    term = entry.get("term", "未命名术语")
    definition = entry.get("definition", "")
    plain_explanation = entry.get("通俗解释", "")
    related_terms = entry.get("related_terms", [])
    content = "\n".join(
        [
            f"术语：{term}",
            f"分类：{group_name}",
            f"定义：{definition}",
            f"通俗解释：{plain_explanation}",
            f"相关术语：{', '.join(related_terms)}" if related_terms else "相关术语：",
        ]
    ).strip()
    return Document(
        page_content=content,
        metadata={
            "source": str(source_path),
            "page": 1,
            "type": "json_term",
            "file_name": source_path.name,
            "dataset_group": "terminology",
            "dataset_user_type": "all",
            "dataset_relative_path": str(source_path.relative_to(dataset_dir)).replace("\\", "/"),
            "dataset_source": "psychology_education_dataset",
            "term": term,
            "term_group": group_name,
            "related_terms": related_terms,
        },
    )


def _case_entry_to_document(
    *,
    entry: Dict[str, Any],
    source_path: Path,
    dataset_dir: Path,
) -> Document:
    content = "\n".join(
        [
            f"案例ID：{entry.get('id', '')}",
            f"场景类型：{entry.get('scenario_type', '')}",
            f"用户类型：{entry.get('user_type', '')}",
            f"用户输入：{entry.get('user_input', '')}",
            f"识别情绪：{entry.get('emotion_detected', '')}",
            f"情绪强度：{entry.get('emotion_intensity', '')}",
            f"风险等级：{entry.get('risk_level', '')}",
            f"AI回复示例：{entry.get('ai_response', '')}",
            f"干预方式：{entry.get('intervention_type', '')}",
            f"关键词：{', '.join(entry.get('keywords', []))}",
            f"关联知识：{entry.get('related_knowledge', '')}",
        ]
    ).strip()
    return Document(
        page_content=content,
        metadata={
            "source": str(source_path),
            "page": 1,
            "type": "json_case",
            "file_name": source_path.name,
            "dataset_group": "case_library",
            "dataset_user_type": entry.get("user_type", "student"),
            "dataset_relative_path": str(source_path.relative_to(dataset_dir)).replace("\\", "/"),
            "dataset_source": "psychology_education_dataset",
            "scenario_type": entry.get("scenario_type", ""),
            "risk_level": entry.get("risk_level", ""),
            "emotion_detected": entry.get("emotion_detected", ""),
            "keywords": entry.get("keywords", []),
        },
    )


def _generic_json_to_document(
    *,
    data: Dict[str, Any],
    source_path: Path,
    dataset_dir: Path,
) -> Document:
    pretty_json = json.dumps(data, ensure_ascii=False, indent=2)
    return Document(
        page_content=pretty_json,
        metadata={
            "source": str(source_path),
            "page": 1,
            "type": "json_generic",
            "file_name": source_path.name,
            "dataset_group": infer_category(source_path),
            "dataset_user_type": infer_user_type(source_path),
            "dataset_relative_path": str(source_path.relative_to(dataset_dir)).replace("\\", "/"),
            "dataset_source": "psychology_education_dataset",
        },
    )


def read_json_documents(dataset_dir: Path) -> List[Document]:
    documents: List[Document] = []
    for path in dataset_dir.rglob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if path.name == "心理陪伴对话库.json":
            for entry in data.get("conversation_library", []):
                documents.append(
                    _case_entry_to_document(entry=entry, source_path=path, dataset_dir=dataset_dir)
                )
        elif path.name == "术语词典.json":
            terms = data.get("psychology_terms", {})
            for group_name, entries in terms.items():
                for entry in entries:
                    documents.append(
                        _term_entry_to_document(
                            group_name=group_name,
                            entry=entry,
                            source_path=path,
                            dataset_dir=dataset_dir,
                        )
                    )
        else:
            documents.append(
                _generic_json_to_document(data=data, source_path=path, dataset_dir=dataset_dir)
            )
    return documents


def build_dataset_documents(dataset_dir: Path) -> List[Document]:
    documents = []
    documents.extend(read_text_documents(dataset_dir))
    documents.extend(read_json_documents(dataset_dir))
    return documents


def summarize_documents(documents: Iterable[Document]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for doc in documents:
        group = str(doc.metadata.get("dataset_group", "unknown"))
        summary[group] = summary.get(group, 0) + 1
    return summary


def import_dataset(
    dataset_dir: Path,
    *,
    persist_dir: str = "data/chroma",
    collection_name: str = "knowledge_base",
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    reset: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if not dataset_dir.exists():
        raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")

    documents = build_dataset_documents(dataset_dir)
    summary = summarize_documents(documents)
    result: Dict[str, Any] = {
        "dataset_dir": str(dataset_dir),
        "document_count": len(documents),
        "group_summary": summary,
        "collection_name": collection_name,
        "persist_dir": persist_dir,
    }

    if dry_run:
        result["dry_run"] = True
        return result

    from vectorstore import ingest_to_chroma, reset_collection

    if reset:
        reset_collection(persist_dir=persist_dir, collection_name=collection_name)

    ingest_result = ingest_to_chroma(
        documents,
        persist_dir=persist_dir,
        collection_name=collection_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    result["ingest_result"] = ingest_result
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import psychology dataset into ChromaDB.")
    parser.add_argument(
        "--dataset-dir",
        default=str(DEFAULT_DATASET_DIR),
        help="Path to the external dataset directory.",
    )
    parser.add_argument("--persist-dir", default="data/chroma", help="Chroma persistence directory.")
    parser.add_argument("--collection-name", default="knowledge_base", help="Target collection name.")
    parser.add_argument("--chunk-size", type=int, default=500, help="Chunk size for ingestion.")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="Chunk overlap for ingestion.")
    parser.add_argument("--reset", action="store_true", help="Reset the target collection before import.")
    parser.add_argument("--dry-run", action="store_true", help="Only parse and summarize the dataset.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = import_dataset(
        Path(args.dataset_dir),
        persist_dir=args.persist_dir,
        collection_name=args.collection_name,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        reset=args.reset,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
