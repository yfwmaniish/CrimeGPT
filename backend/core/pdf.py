"""
docx -> PDF conversion via LibreOffice headless (Track C).

LibreOffice (``soffice``) is installed in the container. We shell out to it with
an isolated HOME per call so concurrent conversions don't fight over the user
profile / lock files.
"""
import os
import subprocess
import tempfile


class PdfConversionError(RuntimeError):
    pass


def convert_docx_to_pdf(docx_bytes: bytes, *, timeout: int = 120) -> bytes:
    """Convert a .docx (as bytes) to PDF (as bytes) using LibreOffice headless."""
    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "document.docx")
        out_path = os.path.join(tmp, "document.pdf")
        with open(in_path, "wb") as fh:
            fh.write(docx_bytes)

        try:
            result = subprocess.run(
                [
                    "soffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmp,
                    in_path,
                ],
                capture_output=True,
                timeout=timeout,
                # Isolate the LibreOffice profile to this temp dir (avoids the
                # shared ~/.config lock that breaks concurrent conversions).
                env={**os.environ, "HOME": tmp},
            )
        except FileNotFoundError as exc:  # soffice not installed
            raise PdfConversionError(
                "LibreOffice (soffice) is not available in this environment."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise PdfConversionError("LibreOffice conversion timed out.") from exc

        if not os.path.exists(out_path):
            raise PdfConversionError(
                "LibreOffice did not produce a PDF. "
                f"stderr: {result.stderr.decode(errors='replace')[:500]}"
            )
        with open(out_path, "rb") as fh:
            return fh.read()
