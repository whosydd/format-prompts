from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Source:
    slug: str
    url: str
    adapter: str = "canonical"


SOURCES = (
    Source(
        "bigpeng-awesome-gpt-image-2-prompts",
        "https://raw.githubusercontent.com/BigPengSays/awesome-gpt-image-2-prompts/main/data/gpt-image-2-prompts.json",
        adapter="bigpeng",
    ),
    Source(
        "apimodels-gpt-image-2-5-prompts",
        "https://raw.githubusercontent.com/apimodels/gpt-image-2-5-prompts/main/prompts.json",
        adapter="apimodels",
    ),
    Source(
        "stretchcloud-awesome-gpt-image-prompt-2-5",
        "https://raw.githubusercontent.com/stretchcloud/awesome-gpt-image-prompt-2.5/main/data/prompts.json",
        adapter="stretchcloud",
    ),
)

BIGPENG_PREVIEW_BASE_URL = "https://raw.githubusercontent.com/BigPengSays/awesome-gpt-image-2-prompts/main/"
STRETCHCLOUD_IMAGE_BASE_URL = "https://raw.githubusercontent.com/stretchcloud/awesome-gpt-image-prompt-2.5/main/data/images/"
STRETCHCLOUD_FIGMA_URL = "https://www.figma.com/@devault"

OUTPUT_PATH = Path(__file__).parent / "data" / "prompts.json"


def fetch_records(source: Source) -> list[dict[str, Any]]:
    request = Request(source.url, headers={"User-Agent": "infinite-canvas-prompt-sync"})
    try:
        with urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode("utf-8-sig"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"读取数据源失败：{source.slug}：{exc}") from exc

    if not isinstance(payload, list):
        raise ValueError(f"数据源必须是 JSON 数组：{source.slug}")
    return payload


def _text(record: dict[str, Any], field: str, location: str) -> str:
    value = record.get(field, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{location} 的 {field} 必须是字符串")
    return value.strip()


def _prefixed_id(record: dict[str, Any], field: str, prefix: str, location: str) -> str:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).strip():
        raise ValueError(f"{location} 的 {field} 必须是非空字符串或整数")
    return f"{prefix}-{str(value).strip()}"


def _adapt_bigpeng_record(raw_record: dict[str, Any], location: str) -> dict[str, Any]:
    author_name = _text(raw_record, "author_name", location)
    image_url = _text(raw_record, "image_url", location)
    if image_url and not image_url.startswith(("https://", "http://")):
        raise ValueError(f"{location} 的 image_url 必须是 HTTP(S) 链接")

    if not image_url:
        preview = _text(raw_record, "image", location)
        if preview:
            preview_path = PurePosixPath(preview)
            if preview_path.is_absolute() or ".." in preview_path.parts or not preview_path.parts or preview_path.parts[0] != "previews":
                raise ValueError(f"{location} 的 image 必须指向仓库 previews 目录")
            image_url = BIGPENG_PREVIEW_BASE_URL + quote(preview_path.as_posix(), safe="/")

    adapted = dict(raw_record)
    adapted["author"] = {"name": author_name}
    adapted["model_name"] = "GPT Image 2"
    adapted["model_key"] = "gpt-image-2"
    adapted["model_family"] = "gpt-image"
    adapted["images"] = [image_url] if image_url else []
    return adapted


def _adapt_apimodels_record(raw_record: dict[str, Any], location: str) -> dict[str, Any]:
    original_id = _prefixed_id(raw_record, "id", "apimodels-gpt-image-2-5", location)
    title_en = _text(raw_record, "title_en", location)
    title_zh = _text(raw_record, "title_zh", location)
    image_url = _text(raw_record, "example_image", location)

    adapted = dict(raw_record)
    adapted["id"] = original_id
    adapted["title"] = title_en or title_zh
    adapted["source_record_id"] = str(raw_record["id"])
    adapted["author"] = {"name": _text(raw_record, "author", location)}
    adapted["model_name"] = "GPT Image 2.5"
    adapted["model_key"] = "gpt-image-2.5"
    adapted["model_family"] = "gpt-image"
    adapted["language"] = _text(raw_record, "prompt_language", location)
    adapted["images"] = [image_url] if image_url else []
    return adapted


def _adapt_stretchcloud_record(raw_record: dict[str, Any], location: str) -> dict[str, Any]:
    record_id = _prefixed_id(raw_record, "n", "stretchcloud-gpt-image-2-5", location)
    file_name = _text(raw_record, "file", location)
    image_url = ""
    if file_name:
        image_path = PurePosixPath(file_name)
        if image_path.is_absolute() or ".." in image_path.parts:
            raise ValueError(f"{location} 的 file 必须是安全的相对路径")
        image_url = STRETCHCLOUD_IMAGE_BASE_URL + quote(image_path.as_posix(), safe="/")

    adapted = dict(raw_record)
    adapted["id"] = record_id
    adapted["title"] = _text(raw_record, "name", location)
    adapted["category"] = _text(raw_record, "categoryLabel", location) or _text(raw_record, "category", location)
    adapted["category_key"] = _text(raw_record, "category", location)
    adapted["source_record_id"] = file_name
    adapted["source_url"] = "https://github.com/stretchcloud/awesome-gpt-image-prompt-2.5"
    adapted["page"] = "https://github.com/stretchcloud/awesome-gpt-image-prompt-2.5/blob/main/data/prompts.json"
    adapted["author"] = {"name": "Devault"}
    adapted["author_url"] = STRETCHCLOUD_FIGMA_URL
    adapted["image_credit_url"] = STRETCHCLOUD_FIGMA_URL
    adapted["model_name"] = "GPT Image 2.5"
    adapted["model_key"] = "gpt-image-2.5"
    adapted["model_family"] = "gpt-image"
    adapted["images"] = [image_url] if image_url else []
    return adapted


def adapt_source_records(source: Source, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adapters = {
        "bigpeng": _adapt_bigpeng_record,
        "apimodels": _adapt_apimodels_record,
        "stretchcloud": _adapt_stretchcloud_record,
    }
    if source.adapter == "canonical":
        return records
    adapter = adapters.get(source.adapter)
    if adapter is None:
        raise ValueError(f"未知的数据源格式：{source.adapter}")

    adapted = []
    for index, raw_record in enumerate(records):
        location = f"{source.slug}[{index}]"
        if not isinstance(raw_record, dict):
            raise ValueError(f"{location} 必须是 JSON 对象")
        adapted.append(adapter(raw_record, location))
    return adapted


def _validate_record(record: Any, source_slug: str, index: int) -> dict[str, Any]:
    location = f"{source_slug}[{index}]"
    if not isinstance(record, dict):
        raise ValueError(f"{location} 必须是 JSON 对象")

    for field in ("id", "title", "prompt"):
        if not _text(record, field, location):
            raise ValueError(f"{location} 缺少必填字段 {field}")

    images = record.get("images") or []
    if not isinstance(images, list) or any(not isinstance(image, str) for image in images):
        raise ValueError(f"{location} 的 images 必须是字符串数组")

    author = record.get("author") or {}
    if not isinstance(author, dict):
        raise ValueError(f"{location} 的 author 必须是 JSON 对象")

    validated = dict(record)
    validated["id"] = _text(record, "id", location)
    validated["title"] = _text(record, "title", location)
    validated["prompt"] = record["prompt"]
    validated["images"] = [image.strip() for image in images if image.strip()]
    validated["author"] = author
    return validated


def _converted_record(record: dict[str, Any], source_slugs: list[str]) -> dict[str, Any]:
    author = record["author"]
    author_name = author.get("name", "")
    author_handle = author.get("handle", "")
    if not isinstance(author_name, str) or not isinstance(author_handle, str):
        raise ValueError(f"记录 {record['id']} 的作者信息必须是字符串")

    author_text = author_name.strip()
    handle_text = author_handle.strip()
    if handle_text:
        author_text = f"{author_text} (@{handle_text.lstrip('@')})" if author_text else f"@{handle_text.lstrip('@')}"

    model_name = _text(record, "model_name", record["id"])
    model_key = _text(record, "model_key", record["id"])
    model_family = _text(record, "model_family", record["id"])
    category = _text(record, "category", record["id"])
    source_url = _text(record, "source_url", record["id"])
    channel = _text(record, "channel", record["id"])
    published_at = _text(record, "published_at", record["id"])
    source_record_id = _text(record, "source_record_id", record["id"])
    language = _text(record, "language", record["id"])
    quality_grade = _text(record, "quality_grade", record["id"])
    category_key = _text(record, "category_key", record["id"])
    theme = _text(record, "theme", record["id"])
    aspect_ratio = _text(record, "aspect_ratio", record["id"])

    description_parts = []
    if author_text:
        description_parts.append(f"作者：{author_text}")
    if model_name:
        description_parts.append(f"模型：{model_name}")
    if source_url:
        description_parts.append(f"原帖：{source_url}")
    if channel:
        description_parts.append(f"渠道：{channel}")
    if published_at:
        description_parts.append(f"日期：{published_at}")
    if source_record_id:
        description_parts.append(f"来源记录：{source_record_id}")
    for field, label in (
        ("title_zh", "中文标题"),
        ("author_url", "作者页"),
        ("page", "详情页"),
        ("collected_via", "收集渠道"),
        ("collected_via_url", "收集渠道链接"),
        ("aspect_ratio", "画幅"),
        ("tagline", "简介"),
        ("summary", "摘要"),
        ("image_credit_url", "图片署名"),
    ):
        value = _text(record, field, record["id"])
        if value:
            description_parts.append(f"{label}：{value}")
    description_parts.append(f"数据源：{', '.join(source_slugs)}")

    tags = []
    for tag in (
        category,
        f"category:{category_key}" if category_key else "",
        f"model:{model_key}" if model_key else "",
        f"family:{model_family}" if model_family else "",
        f"language:{language}" if language else "",
        f"quality:{quality_grade}" if quality_grade else "",
        f"channel:{channel}" if channel else "",
        f"theme:{theme}" if theme else "",
        f"aspect-ratio:{aspect_ratio}" if aspect_ratio else "",
        *(f"source:{slug}" for slug in source_slugs),
    ):
        if tag and tag not in tags:
            tags.append(tag)

    image_urls = record["images"]
    return {
        "id": record["id"],
        "title": record["title"],
        "prompt": record["prompt"],
        "description": "；".join(description_parts),
        "coverUrl": image_urls[0] if image_urls else "",
        "referenceImageUrls": [],
        "tags": tags,
    }


def convert_sources(sources: Iterable[tuple[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    origins: dict[str, list[str]] = {}

    for source_slug, records in sources:
        if not isinstance(records, list):
            raise ValueError(f"数据源必须是 JSON 数组：{source_slug}")
        for index, raw_record in enumerate(records):
            record = _validate_record(raw_record, source_slug, index)
            record_id = record["id"]
            if record_id not in selected:
                selected[record_id] = record
                origins[record_id] = []
            if source_slug not in origins[record_id]:
                origins[record_id].append(source_slug)

    return [
        _converted_record(selected[record_id], origins[record_id])
        for record_id in sorted(selected)
    ]


def sync(output_path: Path = OUTPUT_PATH) -> int:
    sources = []
    for source in SOURCES:
        print(f"正在读取：{source.slug}")
        records = fetch_records(source)
        sources.append((source.slug, adapt_source_records(source, records)))

    converted = convert_sources(sources)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(converted, ensure_ascii=False, indent=2) + "\n"
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        temporary_path.write_text(encoded, encoding="utf-8")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    print(f"已写入 {len(converted)} 条记录：{output_path}")
    return len(converted)


def main() -> None:
    parser = argparse.ArgumentParser(description="同步并转换 Infinite Canvas prompts")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    arguments = parser.parse_args()
    sync(arguments.output)


if __name__ == "__main__":
    main()
