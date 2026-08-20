from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from public_record_versioned.djvu import parse_djvu_pages


FIXTURE = """<?xml version="1.0"?>
<DjVuXML><BODY>
  <OBJECT width="1000" height="1200">
    <HIDDENTEXT><PAGECOLUMN><REGION><PARAGRAPH>
      <LINE><WORD coords="10,1100,200,1000" x-confidence="90">WATER</WORD></LINE>
      <LINE><WORD coords="10,900,100,850" x-confidence="80">Body</WORD><WORD coords="110,900,200,850" x-confidence="70">text</WORD></LINE>
    </PARAGRAPH></REGION></PAGECOLUMN></HIDDENTEXT>
  </OBJECT>
  <OBJECT width="1000" height="1200">
    <HIDDENTEXT><PAGECOLUMN><REGION><PARAGRAPH>
      <LINE><WORD coords="10,1100,250,980" x-confidence="88">FORESTS</WORD></LINE>
    </PARAGRAPH></REGION></PAGECOLUMN></HIDDENTEXT>
  </OBJECT>
</BODY></DjVuXML>
"""


class DjvuParserTests(unittest.TestCase):
    def test_parses_page_separated_lines_and_typography(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.xml"
            path.write_text(FIXTURE, encoding="utf-8")
            pages = parse_djvu_pages(path)

        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0].lines[0].text, "WATER")
        self.assertEqual(pages[0].lines[1].text, "Body text")
        self.assertGreater(pages[0].lines[0].mean_word_height, 0)
        self.assertEqual(pages[1].index, 1)


if __name__ == "__main__":
    unittest.main()
