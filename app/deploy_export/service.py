from __future__ import annotations

from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from app.schemas import DeployExportRequest
from app.services.portfolio import render_portfolio_html


def build_deploy_package(payload: DeployExportRequest) -> bytes:
    html = render_portfolio_html(payload.portfolio)
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("index.html", html)
        if payload.provider == "netlify":
            archive.writestr("netlify.toml", "[build]\npublish = '.'\n")
        else:
            archive.writestr("vercel.json", '{"cleanUrls": true}')
    return buffer.getvalue()
