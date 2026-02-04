from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import trafilatura
from newspaper import Article


def _to_ascii(value: str) -> str:
    return (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )


def _clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def _slugify(value: str) -> str:
    ascii_value = _to_ascii(value).lower()
    ascii_value = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    ascii_value = re.sub(r"-+", "-", ascii_value).strip("-")
    return ascii_value or "reference"


def _detect_type(url: str) -> str:
    lower_url = url.lower()
    if "github.com" in lower_url:
        return "repo"
    if "arxiv.org" in lower_url or "doi.org" in lower_url or lower_url.endswith(".pdf"):
        return "paper"
    if any(
        token in lower_url
        for token in ["docs.", "/docs", "documentation", "readthedocs"]
    ):
        return "docs"
    if any(token in lower_url for token in ["news.ycombinator.com", "reddit.com"]):
        return "post"
    return "article"


def _extract_domain_tag(url: str) -> str | None:
    netloc = urlparse(url).netloc.split(":")[0].lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if not netloc:
        return None
    primary = netloc.split(".")[0]
    return primary or None


def _select_summary(extracted_text: str, article_summary: str | None) -> str:
    if article_summary:
        return _clean_whitespace(article_summary)
    sentences = _split_sentences(extracted_text)
    return _clean_whitespace(" ".join(sentences[:2]))


def _select_key_insights(extracted_text: str, fallback_summary: str) -> list[str]:
    sentences = _split_sentences(extracted_text)
    if sentences:
        return [s for s in sentences[:3]]
    if fallback_summary:
        return [fallback_summary]
    return ["Extracted content is available for review."]


def _ensure_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        data = {"version": "1.0", "references": []}
        index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    return json.loads(index_path.read_text(encoding="utf-8"))


def _unique_slug(references_dir: Path, slug: str) -> str:
    candidate = slug
    counter = 2
    while (references_dir / f"{candidate}.md").exists():
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate


async def process_feed(
    url: str,
    note: str | None,
    via: str,
    references_dir: Path,
) -> dict[str, Any]:
    try:
        references_dir.mkdir(parents=True, exist_ok=True)
        index_path = references_dir / "index.json"

        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return {"error": "Failed to fetch URL"}

        metadata = trafilatura.extract_metadata(downloaded)
        extracted_text = (
            trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                include_links=False,
            )
            or ""
        )

        title = metadata.title if metadata and metadata.title else url

        article_summary: str | None = None
        keywords: list[str] = []
        try:
            article = Article(url)
            article.download()
            article.parse()
            try:
                article.nlp()
            except Exception:
                pass
            article_summary = article.summary if article.summary else None
            if isinstance(article.keywords, list):
                keywords = [keyword for keyword in article.keywords if keyword]
        except Exception:
            pass

        summary = _select_summary(extracted_text, article_summary)
        key_insights = _select_key_insights(extracted_text, summary)

        ref_type = _detect_type(url)
        tags: set[str] = set()
        for keyword in keywords:
            clean_keyword = _to_ascii(keyword.lower()).strip()
            if clean_keyword:
                tags.add(clean_keyword)

        type_tag = ref_type
        if type_tag:
            tags.add(type_tag)

        domain_tag = _extract_domain_tag(url)
        if domain_tag:
            tags.add(domain_tag)

        if "github.com" in url.lower():
            tags.add("github")
        if "arxiv.org" in url.lower():
            tags.add("arxiv")

        tag_list = sorted(tags)

        timestamp = datetime.now(timezone.utc)
        date_prefix = timestamp.strftime("%Y-%m-%d")
        slug_base = _slugify(title)
        slug = _unique_slug(references_dir, f"{date_prefix}-{slug_base}")

        title_ascii = _to_ascii(title)
        summary_ascii = _to_ascii(summary)
        note_ascii = _to_ascii(note or "")

        markdown_lines = [
            f"# {title_ascii or 'Untitled'}",
            "",
            f"**Source**: {url}",
            f"**Type**: {ref_type}",
            f"**Ingested**: {timestamp.isoformat().replace('+00:00', 'Z')}",
            f"**Tags**: {', '.join(tag_list)}",
            f"**Note**: {note_ascii or 'None'}",
            f"**Via**: {via}",
            "",
            "---",
            "",
            "## Summary",
            "",
            summary_ascii
            or "Summary unavailable; extraction succeeded but content was sparse.",
            "",
            "## Key Insights",
            "",
        ]

        for insight in key_insights:
            insight_ascii = _to_ascii(insight)
            if insight_ascii:
                markdown_lines.append(f"- {insight_ascii}")

        markdown_lines += [
            "",
            "## Relevance to Our Work",
            "",
            "Review and connect this reference to current astraeus or galaxy-protocol efforts.",
            "",
            "## Applicable Patterns",
            "",
            "Identify any concrete patterns or practices worth adopting.",
            "",
        ]

        file_name = f"{slug}.md"
        file_path = references_dir / file_name
        file_path.write_text("\n".join(markdown_lines), encoding="utf-8")

        index_data = _ensure_index(index_path)
        reference_entry = {
            "slug": slug,
            "url": url,
            "title": title_ascii or "Untitled",
            "type": ref_type,
            "tags": tag_list,
            "note": note_ascii or None,
            "shared_at": timestamp.isoformat().replace("+00:00", "Z"),
            "shared_via": via,
            "file": file_name,
        }
        index_data.setdefault("references", []).append(reference_entry)
        index_path.write_text(json.dumps(index_data, indent=2), encoding="utf-8")

        return {
            "slug": slug,
            "title": title_ascii or "Untitled",
            "tags": tag_list,
            "type": ref_type,
            "file_path": str(file_path),
        }
    except Exception as exc:
        return {"error": str(exc)}
