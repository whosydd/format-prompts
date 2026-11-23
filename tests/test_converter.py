import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from converter import Source, adapt_source_records, convert_sources


class ConvertSourcesTests(unittest.TestCase):
    def test_maps_source_record_to_infinite_canvas_shape(self):
        result = convert_sources(
            [
                (
                    "awesome-ai-image-prompts",
                    [
                        {
                            "id": "prompt-1",
                            "title": "Sample prompt",
                            "prompt": "  Full original prompt text\n",
                            "category": "product",
                            "model_key": "nano-banana",
                            "model_name": "Nano Banana",
                            "model_family": "nano-banana",
                            "author": {"name": "Author", "handle": "author"},
                            "source_url": "https://example.com/post",
                            "images": ["https://example.com/cover.jpg", "https://example.com/second.jpg"],
                        }
                    ],
                )
            ]
        )

        self.assertEqual(
            set(result[0]),
            {"id", "title", "prompt", "description", "coverUrl", "referenceImageUrls", "tags"},
        )
        self.assertEqual(result[0]["id"], "prompt-1")
        self.assertEqual(result[0]["prompt"], "  Full original prompt text\n")
        self.assertEqual(result[0]["coverUrl"], "https://example.com/cover.jpg")
        self.assertEqual(result[0]["referenceImageUrls"], [])
        self.assertIn("https://example.com/post", result[0]["description"])
        self.assertIn("product", result[0]["tags"])
        self.assertIn("model:nano-banana", result[0]["tags"])

    def test_adapts_bigpeng_records_and_keeps_metadata(self):
        source = Source(
            "bigpeng-awesome-gpt-image-2-prompts",
            "https://example.com/prompts.json",
            adapter="bigpeng",
        )
        records = adapt_source_records(
            source,
            [
                {
                    "id": "prompt_1",
                    "title": "BigPeng prompt",
                    "prompt": "Full prompt text",
                    "category": "Poster",
                    "language": "zh",
                    "quality_grade": "A",
                    "author_name": "@author",
                    "source_url": "https://example.com/source",
                    "image_url": "https://images.example.com/output.jpg",
                    "image": "previews/output.jpg",
                    "source_record_id": "raw_1",
                    "channel": "x",
                    "published_at": "2026-04-23",
                }
            ],
        )

        result = convert_sources([(source.slug, records)])[0]

        self.assertEqual(result["coverUrl"], "https://images.example.com/output.jpg")
        self.assertEqual(result["referenceImageUrls"], [])
        self.assertIn("model:gpt-image-2", result["tags"])
        self.assertIn("language:zh", result["tags"])
        self.assertIn("quality:A", result["tags"])
        self.assertIn("channel:x", result["tags"])
        self.assertIn("作者：@author", result["description"])
        self.assertIn("来源记录：raw_1", result["description"])

    def test_uses_bigpeng_hosted_preview_when_image_url_is_missing(self):
        source = Source("bigpeng", "https://example.com/prompts.json", adapter="bigpeng")
        records = adapt_source_records(
            source,
            [
                {
                    "id": "prompt_2",
                    "title": "Preview fallback",
                    "prompt": "Prompt",
                    "image_url": "",
                    "image": "previews/path with space.jpg",
                }
            ],
        )

        result = convert_sources([(source.slug, records)])[0]

        self.assertEqual(
            result["coverUrl"],
            "https://raw.githubusercontent.com/BigPengSays/awesome-gpt-image-2-prompts/main/previews/path%20with%20space.jpg",
        )

    def test_rejects_bigpeng_preview_paths_outside_previews(self):
        source = Source("bigpeng", "https://example.com/prompts.json", adapter="bigpeng")
        with self.assertRaisesRegex(ValueError, "previews"):
            adapt_source_records(
                source,
                [
                    {
                        "id": "prompt_3",
                        "title": "Invalid preview",
                        "prompt": "Prompt",
                        "image_url": "",
                        "image": "../outside.jpg",
                    }
                ],
            )

    def test_adapts_apimodels_records_and_preserves_bilingual_metadata(self):
        source = Source("apimodels-gpt-image-2-5-prompts", "https://example.com/prompts.json", adapter="apimodels")
        records = adapt_source_records(
            source,
            [
                {
                    "id": 7,
                    "title_en": "English title",
                    "title_zh": "中文标题",
                    "prompt": "Original prompt",
                    "prompt_language": "zh",
                    "category": "image-editing",
                    "author": "OpenAI",
                    "author_url": "https://example.com/author",
                    "source_url": "https://example.com/original",
                    "page": "https://example.com/detail",
                    "example_image": "https://images.example.com/example.webp",
                    "aspect_ratio": "2:3",
                }
            ],
        )

        result = convert_sources([(source.slug, records)])[0]

        self.assertEqual(result["id"], "apimodels-gpt-image-2-5-7")
        self.assertEqual(result["title"], "English title")
        self.assertEqual(result["coverUrl"], "https://images.example.com/example.webp")
        self.assertEqual(result["referenceImageUrls"], [])
        self.assertIn("中文标题", result["description"])
        self.assertIn("https://example.com/detail", result["description"])
        self.assertIn("language:zh", result["tags"])
        self.assertIn("aspect-ratio:2:3", result["tags"])
        self.assertIn("model:gpt-image-2.5", result["tags"])

    def test_leaves_missing_apimodels_example_image_empty(self):
        source = Source("apimodels", "https://example.com/prompts.json", adapter="apimodels")
        records = adapt_source_records(
            source,
            [
                {
                    "id": 8,
                    "title_en": "No image",
                    "title_zh": "无示例图",
                    "prompt": "Prompt",
                    "example_image": None,
                }
            ],
        )

        result = convert_sources([(source.slug, records)])[0]

        self.assertEqual(result["coverUrl"], "")
        self.assertEqual(result["referenceImageUrls"], [])

    def test_adapts_stretchcloud_records_and_links_preview_credit(self):
        source = Source("stretchcloud", "https://example.com/prompts.json", adapter="stretchcloud")
        records = adapt_source_records(
            source,
            [
                {
                    "n": 12,
                    "file": "case-0012.jpg",
                    "category": "exclusive-web",
                    "categoryLabel": "Exclusive Web Design",
                    "name": "Design title",
                    "tagline": "Short description",
                    "summary": "Long design summary",
                    "theme": "dark",
                    "prompt": "Full design prompt",
                }
            ],
        )

        result = convert_sources([(source.slug, records)])[0]

        self.assertEqual(result["id"], "stretchcloud-gpt-image-2-5-12")
        self.assertEqual(result["title"], "Design title")
        self.assertEqual(
            result["coverUrl"],
            "https://raw.githubusercontent.com/stretchcloud/awesome-gpt-image-prompt-2.5/main/data/images/case-0012.jpg",
        )
        self.assertEqual(result["referenceImageUrls"], [])
        self.assertIn("Long design summary", result["description"])
        self.assertIn("https://www.figma.com/@devault", result["description"])
        self.assertIn("theme:dark", result["tags"])
        self.assertIn("category:exclusive-web", result["tags"])
        self.assertIn("model:gpt-image-2.5", result["tags"])

    def test_rejects_stretchcloud_image_paths_outside_data_directory(self):
        source = Source("stretchcloud", "https://example.com/prompts.json", adapter="stretchcloud")
        with self.assertRaisesRegex(ValueError, "file"):
            adapt_source_records(
                source,
                [
                    {
                        "n": 13,
                        "file": "../outside.jpg",
                        "name": "Invalid image",
                        "prompt": "Prompt",
                    }
                ],
            )

    def test_deduplicates_ids_and_combines_source_attribution(self):
        original = {
            "id": "shared-id",
            "title": "Original title",
            "prompt": "Original text",
            "author": {"name": "Author"},
            "source_url": "https://example.com/post",
            "images": [],
        }
        specialized = {**original, "title": "Specialized title", "prompt": "Specialized text"}

        result = convert_sources(
            [
                ("catalog", [original]),
                ("specialized", [specialized]),
            ]
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Original title")
        self.assertEqual(result[0]["prompt"], "Original text")
        self.assertIn("source:catalog", result[0]["tags"])
        self.assertIn("source:specialized", result[0]["tags"])
        self.assertIn("catalog, specialized", result[0]["description"])

    def test_sorts_output_by_id(self):
        records = [
            {"id": "z", "title": "Z", "prompt": "Z"},
            {"id": "a", "title": "A", "prompt": "A"},
        ]

        result = convert_sources([("catalog", records)])

        self.assertEqual([record["id"] for record in result], ["a", "z"])

    def test_rejects_records_without_prompt(self):
        with self.assertRaisesRegex(ValueError, "prompt"):
            convert_sources([("catalog", [{"id": "missing-prompt", "title": "Missing"}])])

    def test_rejects_invalid_image_data(self):
        with self.assertRaisesRegex(ValueError, "images"):
            convert_sources(
                [("catalog", [{"id": "bad-images", "title": "Bad", "prompt": "Text", "images": "url"}])]
            )


if __name__ == "__main__":
    unittest.main()
