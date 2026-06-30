"""Task 5 article smoke tests."""

from pathlib import Path

ARTICLE = Path(__file__).resolve().parents[2] / "docs" / "approach-and-decisions.md"


def test_approach_article_exists_and_covers_key_topics():
    assert ARTICLE.exists()
    content = ARTICLE.read_text(encoding="utf-8").lower()
    for topic in ("elt", "dbt", "airflow", "redash", "dbt_expectations", "circuit breaker"):
        assert topic in content, f"Article should mention: {topic}"
