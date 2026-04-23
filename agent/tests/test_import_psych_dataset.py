import json
from pathlib import Path

from tools.import_psych_dataset import (
    build_dataset_documents,
    infer_category,
    infer_user_type,
    summarize_documents,
)


def test_infer_user_type() -> None:
    assert infer_user_type(Path("学生心理知识库.md")) == "student"
    assert infer_user_type(Path("家长心理知识库.md")) == "parent"
    assert infer_user_type(Path("教师心理知识库.md")) == "teacher"


def test_infer_category() -> None:
    assert infer_category(Path("data/knowledge_base/学生心理知识库.md")) == "knowledge_base"
    assert infer_category(Path("data/case_library/心理陪伴对话库.json")) == "case_library"
    assert infer_category(Path("data/terminology/术语词典.json")) == "terminology"


def test_build_dataset_documents(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "心理教育数据集收集"
    (dataset_dir / "data" / "knowledge_base").mkdir(parents=True)
    (dataset_dir / "data" / "case_library").mkdir(parents=True)
    (dataset_dir / "data" / "terminology").mkdir(parents=True)

    (dataset_dir / "data" / "knowledge_base" / "学生心理知识库.md").write_text(
        "# 学生心理知识\n关于考试焦虑的内容", encoding="utf-8"
    )

    case_data = {
        "conversation_library": [
            {
                "id": "case_001",
                "scenario_type": "学习压力",
                "user_type": "student",
                "user_input": "我最近压力很大",
                "emotion_detected": "anxious",
                "emotion_intensity": 0.8,
                "risk_level": "low",
                "ai_response": "我理解你的压力。",
                "intervention_type": "共情倾听",
                "keywords": ["学习压力"],
                "related_knowledge": "考试焦虑_CBT",
            }
        ]
    }
    (dataset_dir / "data" / "case_library" / "心理陪伴对话库.json").write_text(
        json.dumps(case_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    term_data = {
        "psychology_terms": {
            "basic_concepts": [
                {
                    "term": "自尊",
                    "definition": "个体对自我价值的总体评价",
                    "通俗解释": "觉得自己值不值得被喜欢",
                    "related_terms": ["自信"],
                }
            ]
        }
    }
    (dataset_dir / "data" / "terminology" / "术语词典.json").write_text(
        json.dumps(term_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    documents = build_dataset_documents(dataset_dir)
    summary = summarize_documents(documents)

    assert len(documents) == 3
    assert summary["knowledge_base"] == 1
    assert summary["case_library"] == 1
    assert summary["terminology"] == 1

    case_doc = next(doc for doc in documents if doc.metadata["dataset_group"] == "case_library")
    assert case_doc.metadata["risk_level"] == "low"
    assert "AI回复示例" in case_doc.page_content

    term_doc = next(doc for doc in documents if doc.metadata["dataset_group"] == "terminology")
    assert term_doc.metadata["term"] == "自尊"
    assert "通俗解释" in term_doc.page_content
