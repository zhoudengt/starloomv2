"""Unit tests for markdown_to_ir (stdlib unittest, no pytest required)."""

import unittest

from app.services.ir_converter import markdown_to_ir


class TestIrConverter(unittest.TestCase):
    def test_headings_and_paragraphs(self) -> None:
        md = """## 开篇

第一段内容。

### 小节

第二段。
"""
        ir = markdown_to_ir(md, {"title": "T"})
        self.assertEqual(ir["version"], "1")
        self.assertEqual(ir["meta"]["title"], "T")
        self.assertTrue(ir["meta"].get("reading_minutes", 0) >= 1)
        types = [b["type"] for b in ir["blocks"]]
        self.assertIn("heading", types)
        self.assertIn("paragraph", types)

    def test_list_and_quote(self) -> None:
        md = """- item one
- item two

> quote line
"""
        ir = markdown_to_ir(md)
        blocks = ir["blocks"]
        self.assertTrue(any(b["type"] == "list" for b in blocks))
        self.assertTrue(any(b["type"] == "quote" for b in blocks))

    def test_divider(self) -> None:
        ir = markdown_to_ir("before\n\n---\n\nafter")
        types = [b["type"] for b in ir["blocks"]]
        self.assertIn("divider", types)

    def test_callout_emoji(self) -> None:
        ir = markdown_to_ir("💡 这是一条提示")
        blocks = ir["blocks"]
        self.assertEqual(blocks[0]["type"], "callout")
        self.assertEqual(blocks[0]["style"], "tip")

    def test_empty(self) -> None:
        ir = markdown_to_ir("")
        self.assertEqual(ir["blocks"], [])
        self.assertEqual(ir["meta"]["reading_minutes"], 0)


if __name__ == "__main__":
    unittest.main()
