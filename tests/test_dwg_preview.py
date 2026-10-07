import unittest
from pathlib import Path
from app.backend.server import pdf_document_preview

class TestDwgToPdfPreview(unittest.TestCase):
    def test_dwg_preview_resolves_pdf(self):
        sample_dwg = Path(r"C:\Users\a9379\.gemini\antigravity\scratch\facades\47-УП-22-ОД150-Б-АР_л26_План 3-6 этажей (кладочный).dwg")
        if not sample_dwg.exists():
            self.skipTest("Sample DWG not found")
        meta = pdf_document_preview(sample_dwg)
        self.assertEqual(meta["sourceType"], "DWG")
        self.assertEqual(meta["name"], sample_dwg.name)
        self.assertEqual(meta["nativePath"], str(sample_dwg))
        self.assertTrue(meta["path"].endswith(".pdf"))
        self.assertTrue(Path(meta["path"]).exists())
        self.assertGreater(meta["pages"], 0)
        self.assertTrue(meta["rawUrl"].startswith("/api/file/raw?path="))

if __name__ == "__main__":
    unittest.main()
