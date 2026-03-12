from app.core.config import settings
from app.workflows.graphs.resume_graph import run_resume_graph


def test_resume_graph_preserves_ocr_then_pdf_fallback(monkeypatch) -> None:
    # OCR path
    monkeypatch.setattr(settings, "resume_ocr_enabled", True)
    monkeypatch.setattr(
        "app.services.resume_parser.ResumeParser._extract_text_with_ocr",
        staticmethod(lambda _content: "A" * 80),
    )
    monkeypatch.setattr(
        "app.services.resume_parser.ResumeParser.parse_profile",
        staticmethod(lambda text, model=None: type("P", (), {"model_dump": lambda self: {"skills": ["python"], "projects": []}})()),
    )
    ocr_result = run_resume_graph(content=b"%PDF-mock", model="glm-5")
    assert ocr_result["extraction_branch"] == "ocr"
    assert len(ocr_result["resume_text"]) >= 50

    # OCR insufficient -> PDF fallback
    monkeypatch.setattr(
        "app.services.resume_parser.ResumeParser._extract_text_with_ocr",
        staticmethod(lambda _content: "short"),
    )
    monkeypatch.setattr(
        "app.workflows.graphs.resume_graph.PdfReader",
        lambda *_args, **_kwargs: type(
            "R", (), {"pages": [type("P", (), {"extract_text": lambda self: "B" * 90})()]}
        )(),
    )
    pdf_result = run_resume_graph(content=b"%PDF-mock", model="glm-5")
    assert pdf_result["extraction_branch"] == "pdf"
    assert len(pdf_result["resume_text"]) >= 50


from app.services.resume_parser import ResumeParser


def test_extract_text_skips_pdf_reader_for_plain_text(monkeypatch) -> None:
    monkeypatch.setattr(
        'app.services.resume_parser.PdfReader',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('PdfReader should not be called')),
    )
    text = ResumeParser.extract_text(b'Skills: Python, FastAPI')
    assert 'Python' in text
