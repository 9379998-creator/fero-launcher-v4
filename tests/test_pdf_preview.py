import unittest
from pathlib import Path
from unittest.mock import patch
from app.backend.server import pdf_document_preview

class TestPdfPreview(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("runtime/test_pdf_tmp")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_file = self.test_dir / "sample.pdf"

        import fitz
        doc = fitz.open()
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text((50, 50), "FERO PDF Test Page 1")
        p2 = doc.new_page(width=595, height=842)
        p2.insert_text((50, 50), "FERO PDF Test Page 2")
        doc.save(str(self.pdf_file))
        doc.close()

    def tearDown(self):
        if self.pdf_file.exists():
            self.pdf_file.unlink()
        if self.test_dir.exists():
            for f in self.test_dir.glob("*"):
                f.unlink()
            self.test_dir.rmdir()

    def test_pdf_document_preview_metadata(self):
        meta = pdf_document_preview(self.pdf_file)
        self.assertEqual(meta["name"], "sample.pdf")
        self.assertEqual(meta["pages"], 2)
        self.assertEqual(len(meta["pagesInfo"]), 2)
        self.assertEqual(meta["pagesInfo"][0]["page"], 1)
        self.assertEqual(meta["pagesInfo"][1]["page"], 2)
        self.assertTrue(meta["thumbnailUrl"].endswith("thumb.png"))
        self.assertIn("/api/file/raw?path=", meta["rawUrl"])

    def test_pdf_document_preview_non_pdf(self):
        not_pdf = self.test_dir / "sample.txt"
        not_pdf.write_text("hello")
        with self.assertRaises(ValueError):
            pdf_document_preview(not_pdf)
        not_pdf.unlink()

    def test_pdf_document_preview_missing(self):
        missing = self.test_dir / "non_existent.pdf"
        with self.assertRaises(FileNotFoundError):
            pdf_document_preview(missing)

if __name__ == "__main__":
    unittest.main()
