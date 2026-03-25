"""Tests for local page fetching helpers."""

from __future__ import annotations

import base64
import importlib.util
import json

import pytest

from grounded_research.tools.fetch_page import _extract_pdf_text_locally, fetch_page


_SAMPLE_PDF_BASE64 = (
    "JVBERi0xLjcKJcK1wrYKJSBXcml0dGVuIGJ5IE11UERGIDEuMjcuMgoKMSAwIG9iago8PC9UeXBl"
    "L0NhdGFsb2cvUGFnZXMgMiAwIFIvSW5mbzw8L1Byb2R1Y2VyKE11UERGIDEuMjcuMik+Pj4+CmVu"
    "ZG9iagoKMiAwIG9iago8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1s0IDAgUl0+PgplbmRvYmoK"
    "CjMgMCBvYmoKPDwvRm9udDw8L2hlbHYgNSAwIFI+Pj4+CmVuZG9iagoKNCAwIG9iago8PC9UeXBl"
    "L1BhZ2UvTWVkaWFCb3hbMCAwIDU5NSA4NDJdL1JvdGF0ZSAwL1Jlc291cmNlcyAzIDAgUi9QYXJl"
    "bnQgMiAwIFIvQ29udGVudHNbNiAwIFJdPj4KZW5kb2JqCgo1IDAgb2JqCjw8L1R5cGUvRm9udC9T"
    "dWJ0eXBlL1R5cGUxL0Jhc2VGb250L0hlbHZldGljYS9FbmNvZGluZy9XaW5BbnNpRW5jb2Rpbmc+"
    "PgplbmRvYmoKCjYgMCBvYmoKPDwvTGVuZ3RoIDEyMi9GaWx0ZXIvRmxhdGVEZWNvZGU+PgpzdHJl"
    "YW0KeNodjDEOQjEMQ/ecIjegSVtblRAD0l/YkLohptKKAQYWzk8+8vLi2JaPnLuYppApXcmk/S2H"
    "53x91Uz70tuxVkw0ApXODMPwBIcFN+TgFv+MhQeqJ+73wGIJ9uhkVgwW7kmEEzlPBf/WiLWJ4vN0"
    "7xfZulzlB6NOIeUKZW5kc3RyZWFtCmVuZG9iagoKeHJlZgowIDcKMDAwMDAwMDAwMCA2NTUzNSBm"
    "IAowMDAwMDAwMDQyIDAwMDAwIG4gCjAwMDAwMDAxMjAgMDAwMDAgbiAKMDAwMDAwMDE3MiAwMDAw"
    "MCBuIAowMDAwMDAwMjEzIDAwMDAwIG4gCjAwMDAwMDAzMjAgMDAwMDAgbiAKMDAwMDAwMDQwOSAw"
    "MDAwMCBuIAoKdHJhaWxlcgo8PC9TaXplIDcvUm9vdCAxIDAgUi9JRFs8NDhDMjkyNzRDMkIzNEFD"
    "M0E0NzNDM0IwQzM5NEMzODY+PERERDNCMkI3NEMyQkIzM0ZENDBGODRCNjlEREI1NTIwPl0+Pgpz"
    "dGFydHhyZWYKNjAwCiUlRU9GCg=="
)


def test_extract_pdf_text_locally_reads_generated_pdf() -> None:
    """Local PDF extraction should recover text without cloud parsing."""
    if not any(importlib.util.find_spec(mod) for mod in ("pypdf", "pymupdf")):
        pytest.skip("No local PDF parser installed in this interpreter")

    pdf_bytes = base64.b64decode(_SAMPLE_PDF_BASE64)

    text, parsed_via = _extract_pdf_text_locally(pdf_bytes)

    assert "Universal basic income" in text
    assert parsed_via in {"pypdf", "pymupdf"}


@pytest.mark.asyncio
async def test_fetch_page_uses_local_pdf_parser_before_cloud(monkeypatch: pytest.MonkeyPatch) -> None:
    """PDF fetch should return the successful local parse without needing cloud parsing."""
    async def fake_fetch_pdf_locally(url: str, question: str = "") -> str:
        return json.dumps({
            "url": url,
            "content_type": "pdf",
            "parsed_via": "pypdf",
            "file_path": "/tmp/fake.txt",
            "char_count": 123,
            "notes": "Local PDF notes",
            "key_section": "Local PDF key section",
            "question": question,
            "note": "PDF parsed locally.",
        })

    async def fake_fetch_pdf_with_llamaparse(url: str, question: str = "") -> str:  # pragma: no cover
        raise AssertionError("Should not call LlamaParse when local parsing succeeds")

    monkeypatch.setattr(
        "grounded_research.tools.fetch_page._fetch_pdf_locally",
        fake_fetch_pdf_locally,
    )
    monkeypatch.setattr(
        "grounded_research.tools.fetch_page._fetch_pdf_with_llamaparse",
        fake_fetch_pdf_with_llamaparse,
    )

    result = json.loads(await fetch_page("https://example.com/paper.pdf", question="What did the pilot show?"))

    assert result["parsed_via"] == "pypdf"
    assert result["content_type"] == "pdf"
