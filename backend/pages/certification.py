"""Certification page. The earned certificate follows the TechLearn Academy frame."""

from fastapi import APIRouter, Request
from fastapi.responses import Response

from backend.pages.common import shell, templates

router = APIRouter()


def _certificate_text() -> str:
    return "\n".join(
        [
            "TechLearn Academy",
            "CERTIFICATE OF ACHIEVEMENT",
            "Prithu Lahiri",
            "has successfully completed",
            "Technology foundations",
            "Digital foundations · AI & robotics · Computational thinking",
            "Awarded for completing Modules 01–04",
            "Issued 02 Nov 2026",
            "TLA-7-2026-041",
        ]
    )


@router.get("/certification")
def certification_page(request: Request):
    context = shell("certification")
    return templates.TemplateResponse(request, "pages/certification.html", context)


@router.get("/certification/download")
def download_certification():
    return Response(
        content=_certificate_text(),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=technology-foundations.txt"},
    )
