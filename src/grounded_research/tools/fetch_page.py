"""Fetch and extract readable text from a web page URL.

Saves full text to disk and returns condensed notes to the model's context,
keeping context lean. The model gets notes (~500 chars) plus an optional
question-targeted key section (~1000 chars). Full text is always persisted to
disk — use read_page(file_path) to read more when notes aren't enough.

Used to follow up on promising search results from search_web() — read the
actual article rather than just the snippet.

Pages are saved to a shared directory configured by set_pages_dir(). If not
configured (e.g. single-phase mode), a temp directory is used automatically.
"""

import hashlib
import io
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Tags whose content is noise — remove entirely including children
_NOISE_TAGS = {
    "script", "style", "noscript", "nav", "footer", "header",
    "aside", "form", "button", "input", "iframe", "svg", "img",
    "figure", "figcaption", "advertisement", "banner",
}

# Content-type substrings that indicate non-HTML we can't parse
_BINARY_CONTENT_TYPES = {"pdf", "zip", "octet-stream", "image/", "audio/", "video/"}

_NOTES_CHARS = 500        # chars returned as notes (always, keeps context lean)
_KEY_SECTION_CHARS = 1000  # chars returned for question-targeted section
_TIMEOUT = 20             # seconds

# Module-level pages directory — set by investigate.py before sub-agent calls.
# Not thread-safe, but research_v2 is single-process async so this is fine.
_pages_dir: Path | None = None
_tmp_pages_dir: Path | None = None


def set_pages_dir(path: Path) -> None:
    """Configure where fetched page full texts are saved.

    Call this before running sub-agents so that fetch_page() saves full text
    to a persistent, run-scoped location (e.g. run_dir/data/pages/).
    """
    global _pages_dir
    _pages_dir = path
    path.mkdir(parents=True, exist_ok=True)


def _get_pages_dir() -> Path:
    """Return the active pages directory, lazily creating a temp dir if needed."""
    global _tmp_pages_dir
    if _pages_dir is not None:
        return _pages_dir
    if _tmp_pages_dir is None:
        _tmp_pages_dir = Path(tempfile.mkdtemp(prefix="research_v2_pages_"))
    return _tmp_pages_dir


def _url_hash(url: str) -> str:
    """16-char hex prefix of SHA-256 of the URL — used as filename."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def _extract_text(html: str) -> str:
    """Strip HTML to clean readable prose."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    body = (
        soup.find("article")
        or soup.find("main")
        or soup.find(id=re.compile(r"content|article|story|body", re.I))
        or soup.find(class_=re.compile(r"content|article|story|body|post", re.I))
        or soup.body
        or soup
    )

    text = body.get_text(separator=" ", strip=True)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_key_section(text: str, question: str, max_chars: int = _KEY_SECTION_CHARS) -> str:
    """Extract the most relevant section of text for a given question.

    Scores paragraphs by keyword overlap with the question, then returns
    the highest-scoring paragraphs (in original order) up to max_chars.
    Falls back to the first max_chars chars if no keywords match.
    """
    if not question or not text:
        return text[:max_chars]

    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to",
        "for", "of", "and", "or", "but", "what", "when", "where", "who", "how",
        "why", "did", "does", "do", "has", "have", "had", "be", "been", "being",
        "this", "that", "which", "it", "its", "with", "from", "by", "as",
    }
    keywords = {
        w.lower().strip(".,?!")
        for w in question.split()
        if w.lower().strip(".,?!") not in stopwords and len(w) > 2
    }

    if not keywords:
        return text[:max_chars]

    paragraphs = [p.strip() for p in re.split(r"\s{3,}|\n{2,}", text) if p.strip()]

    def score(para: str) -> int:
        pl = para.lower()
        return sum(1 for k in keywords if k in pl)

    order = sorted(range(len(paragraphs)), key=lambda i: score(paragraphs[i]), reverse=True)

    selected: set[int] = set()
    total = 0
    for i in order:
        if score(paragraphs[i]) == 0:
            break
        if total + len(paragraphs[i]) > max_chars:
            continue
        selected.add(i)
        total += len(paragraphs[i]) + 2
        if total >= max_chars:
            break

    if not selected:
        return text[:max_chars]

    return "\n\n".join(paragraphs[i] for i in sorted(selected))


async def _fetch_pdf_with_llamaparse(url: str, question: str = "") -> str:
    """Parse a PDF URL using PyMuPDF (local, no API key required).

    Downloads the PDF and extracts text locally. Falls back gracefully
    on corrupted or inaccessible PDFs.
    """
    import httpx

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            pdf_bytes = resp.content
    except Exception as e:
        return json.dumps({
            "url": url,
            "content_type": "pdf",
            "error": f"PDF download failed: {type(e).__name__}: {e}",
            "text": "",
        })

    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = "\n\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        return json.dumps({
            "url": url,
            "content_type": "pdf",
            "error": f"PDF parsing failed: {type(e).__name__}: {e}",
            "text": "",
        })

    pages_dir = _get_pages_dir()
    file_path = pages_dir / f"{_url_hash(url)}.txt"
    file_path.write_text(full_text, encoding="utf-8")

    notes = full_text[:_NOTES_CHARS]
    key_section = extract_key_section(full_text, question) if question else ""

    return json.dumps({
        "url": url,
        "content_type": "pdf",
        "parsed_via": "PyMuPDF",
        "file_path": str(file_path),
        "char_count": len(full_text),
        "notes": notes,
        "key_section": key_section,
        "question": question,
        "note": (
            "PDF parsed via PyMuPDF. Full text saved to file_path. "
            "Use read_page(file_path) for more."
        ),
    })


def _extract_pdf_text_locally(pdf_bytes: bytes) -> tuple[str, str]:
    """Extract PDF text using locally available parsers.

    The standard dev environment should be able to read research PDFs without
    requiring an external parsing API. Try simple, observable local parsers
    first and return both the extracted text and the parser name.
    """
    errors: list[str] = []

    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        if text:
            return text, "pypdf"
        errors.append("pypdf returned no text")
    except Exception as exc:
        errors.append(f"pypdf failed: {type(exc).__name__}: {exc}")

    try:
        import pymupdf

        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            text = "\n\n".join(page.get_text("text").strip() for page in doc).strip()
        if text:
            return text, "pymupdf"
        errors.append("pymupdf returned no text")
    except Exception as exc:
        errors.append(f"pymupdf failed: {type(exc).__name__}: {exc}")

    raise ValueError("; ".join(errors))


def _build_pdf_result(url: str, full_text: str, question: str, parsed_via: str) -> str:
    """Build the shared JSON result for a successfully parsed PDF."""
    pages_dir = _get_pages_dir()
    file_path = pages_dir / f"{_url_hash(url)}.txt"
    file_path.write_text(full_text, encoding="utf-8")

    notes = full_text[:_NOTES_CHARS]
    key_section = extract_key_section(full_text, question) if question else ""

    return json.dumps({
        "url": url,
        "content_type": "pdf",
        "parsed_via": parsed_via,
        "file_path": str(file_path),
        "char_count": len(full_text),
        "notes": notes,
        "key_section": key_section,
        "question": question,
        "note": (
            f"PDF parsed via {parsed_via}. Full text saved to file_path. "
            "Use read_page(file_path) for more."
        ),
    })


async def _fetch_pdf_locally(url: str, question: str = "") -> str:
    """Download and parse a PDF using local libraries only."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; InvestigativeResearchBot/1.0; "
            "+https://github.com/BrianMills2718/research_v2)"
        ),
        "Accept": "application/pdf,*/*;q=0.8",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_TIMEOUT,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        return json.dumps({
            "url": url,
            "content_type": "pdf",
            "error": f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}",
            "text": "",
        })
    except httpx.RequestError as exc:
        return json.dumps({
            "url": url,
            "content_type": "pdf",
            "error": f"Request failed: {type(exc).__name__}: {exc}",
            "text": "",
        })

    try:
        full_text, parsed_via = _extract_pdf_text_locally(response.content)
    except ValueError as exc:
        return json.dumps({
            "url": url,
            "content_type": "pdf",
            "error": f"Local PDF parsing failed: {exc}",
            "text": "",
        })

    return _build_pdf_result(url, full_text, question, parsed_via)


async def fetch_page(url: str, question: str = "") -> str:
    """Fetch a web page, save full text to disk, return notes for context.

    Use this to read content from a URL found via search_web() when the
    snippet looks relevant. Returns condensed notes (~500 chars) to keep
    context lean. If a question is provided, also returns the most relevant
    ~1000-char section targeted to that question.

    Full text is saved to disk at file_path. Use read_page(file_path) or
    read_page(file_path, focus=question) to read more when notes aren't enough.

    Args:
        url: The URL to fetch (http or https).
        question: Optional question to guide extraction of the key section.
                  Passed to read_page later if you need deeper context.
    """
    if _is_pdf_url(url):
        local_result = json.loads(await _fetch_pdf_locally(url, question))
        if "error" not in local_result:
            return json.dumps(local_result)

        api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
        if api_key:
            try:
                remote_result = json.loads(await _fetch_pdf_with_llamaparse(url, question))
                if "error" not in remote_result:
                    return json.dumps(remote_result)
                local_result["llamaparse_error"] = remote_result["error"]
            except Exception as exc:
                local_result["llamaparse_error"] = (
                    f"LlamaParse fallback failed: {type(exc).__name__}: {exc}"
                )

        return json.dumps(local_result)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; InvestigativeResearchBot/1.0; "
            "+https://github.com/BrianMills2718/research_v2)"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=_TIMEOUT,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "").lower()

            if any(b in content_type for b in _BINARY_CONTENT_TYPES):
                return json.dumps({
                    "url": url,
                    "content_type": content_type,
                    "note": f"Non-text content ({content_type}) — cannot extract text.",
                    "text": "",
                })

            full_text = _extract_text(response.text)

            # Save full text to disk for read_page() access
            pages_dir = _get_pages_dir()
            file_path = pages_dir / f"{_url_hash(url)}.txt"
            file_path.write_text(full_text, encoding="utf-8")

            notes = full_text[:_NOTES_CHARS]
            key_section = extract_key_section(full_text, question) if question else ""

            return json.dumps({
                "url": url,
                "final_url": str(response.url),
                "status_code": response.status_code,
                "content_type": content_type,
                "file_path": str(file_path),
                "char_count": len(full_text),
                "notes": notes,
                "key_section": key_section,
                "question": question,
                "note": (
                    "Full text saved to file_path. "
                    "Use read_page(file_path) for more, or "
                    "read_page(file_path, focus=your_question) for a targeted section."
                ),
            })

    except httpx.HTTPStatusError as e:
        return json.dumps({
            "url": url,
            "error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}",
            "text": "",
        })
    except httpx.RequestError as e:
        return json.dumps({
            "url": url,
            "error": f"Request failed: {type(e).__name__}: {e}",
            "text": "",
        })
