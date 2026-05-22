"""Generación segura de reportes PDF para PixelForge Studio."""

from datetime import date, datetime
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.auth.rbac import require_role
from src.db import execute, fetch, fetchrow
from src.security_logger import log_security_event


router = APIRouter(prefix="/reports", tags=["reports"])


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def safe_text(value) -> str:
    """Convierte valores a texto seguro para PDF."""
    if value is None:
        return ""
    return str(value).replace("<", "").replace(">", "").strip()


def build_pdf(title: str, sections: List[dict]) -> bytes:
    """
    Construye PDF en memoria.

    sections:
    [
        {"heading": "Datos", "rows": [["Campo", "Valor"], ...]},
        ...
    ]
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        title=title,
        author="PixelForge Studio",
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(safe_text(title), styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(
        Paragraph(
            f"Generado en memoria el {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 18))

    for section in sections:
        story.append(Paragraph(safe_text(section["heading"]), styles["Heading2"]))
        story.append(Spacer(1, 8))

        rows = section.get("rows", [])

        if not rows:
            story.append(Paragraph("Sin datos disponibles.", styles["Normal"]))
            story.append(Spacer(1, 12))
            continue

        safe_rows = [
            [safe_text(cell) for cell in row]
            for row in rows
        ]

        table = Table(safe_rows, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        story.append(table)
        story.append(Spacer(1, 16))

    doc.build(story)

    buffer.seek(0)
    return buffer.read()


def pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def audit_pdf_request(
    requested_by: int,
    report_type: str,
    target_player_id: Optional[int],
    ip_address: str,
) -> None:
    await execute(
        """
        INSERT INTO pdf_audit_logs(requested_by, report_type, target_player_id, ip_address)
        VALUES($1, $2, $3, $4)
        """,
        requested_by,
        report_type,
        target_player_id,
        ip_address,
    )


@router.get("/me/pdf")
async def my_personal_data_pdf(
    request: Request,
    current_user: dict = Depends(require_role("jugador")),
):
    """
    HU-B13.

    PDF de datos personales del jugador autenticado.

    Seguridad:
    - El ID se toma del JWT.
    - No incluye password_hash.
    - No incluye JWT.
    - No incluye secreto TOTP.
    - No incluye CVV.
    - No incluye número completo de tarjeta.
    - Se genera en memoria.
    """
    player_id = current_user["id"]
    ip_address = get_client_ip(request)

    player = await fetchrow(
        """
        SELECT id, nickname, email, role, estado, token_balance,
               mfa_enabled, mfa_method, created_at, last_login
        FROM jugadores
        WHERE id = $1
        """,
        player_id,
    )

    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jugador no encontrado.",
        )

    scores = await fetch(
        """
        SELECT score, level_reached, estado, created_at
        FROM puntuaciones
        WHERE jugador_id = $1
        ORDER BY created_at DESC
        LIMIT 20
        """,
        player_id,
    )

    transactions = await fetch(
        """
        SELECT transaction_type, package_name, item_code, tokens_amount,
               price_cop, result, last4, created_at
        FROM token_transactions
        WHERE jugador_id = $1
        ORDER BY created_at DESC
        LIMIT 20
        """,
        player_id,
    )

    cards = await fetch(
        """
        SELECT last4, brand, exp_month, exp_year, status, created_at
        FROM payment_cards
        WHERE jugador_id = $1
        ORDER BY created_at DESC
        """,
        player_id,
    )

    items = await fetch(
        """
        SELECT item_code, item_name, tokens_spent, created_at
        FROM player_items
        WHERE jugador_id = $1
        ORDER BY created_at DESC
        """,
        player_id,
    )

    sections = [
        {
            "heading": "Datos personales permitidos",
            "rows": [
                ["Campo", "Valor"],
                ["Nickname", player["nickname"]],
                ["Email", player["email"]],
                ["Rol", player["role"]],
                ["Estado", player["estado"]],
                ["Saldo tokens", player["token_balance"]],
                ["MFA activo", player["mfa_enabled"]],
                ["Método MFA", player["mfa_method"]],
                ["Fecha registro", player["created_at"]],
                ["Último login", player["last_login"]],
            ],
        },
        {
            "heading": "Historial reciente de puntajes",
            "rows": [["Puntaje", "Nivel", "Estado", "Fecha"]]
            + [
                [row["score"], row["level_reached"], row["estado"], row["created_at"]]
                for row in scores
            ],
        },
        {
            "heading": "Tarjetas simuladas tokenizadas",
            "rows": [["Últimos 4", "Marca", "Mes", "Año", "Estado", "Fecha"]]
            + [
                [row["last4"], row["brand"], row["exp_month"], row["exp_year"], row["status"], row["created_at"]]
                for row in cards
            ],
        },
        {
            "heading": "Transacciones recientes",
            "rows": [["Tipo", "Paquete", "Ítem", "Tokens", "Precio COP", "Resultado", "Últimos 4", "Fecha"]]
            + [
                [
                    row["transaction_type"],
                    row["package_name"],
                    row["item_code"],
                    row["tokens_amount"],
                    row["price_cop"],
                    row["result"],
                    row["last4"],
                    row["created_at"],
                ]
                for row in transactions
            ],
        },
        {
            "heading": "Ítems activos",
            "rows": [["Código", "Nombre", "Tokens gastados", "Fecha"]]
            + [
                [row["item_code"], row["item_name"], row["tokens_spent"], row["created_at"]]
                for row in items
            ],
        },
    ]

    await audit_pdf_request(player_id, "mis_datos", player_id, ip_address)

    log_security_event(
        event_type="pdf_generated",
        ip_address=ip_address,
        user_id=player_id,
        role=current_user["role"],
        success=True,
        reason="personal_data_pdf",
        extra={"report_type": "mis_datos"},
    )

    pdf_bytes = build_pdf("PixelForge Studio — Mis datos", sections)
    return pdf_response(pdf_bytes, "mis_datos.pdf")


@router.get("/admin/player/{player_id}/pdf")
async def player_history_pdf(
    player_id: int,
    request: Request,
    current_user: dict = Depends(require_role(["admin_juego", "moderador"])),
):
    """
    HU-B07.

    PDF de historial de jugador para admin/moderador.
    """
    ip_address = get_client_ip(request)

    player = await fetchrow(
        """
        SELECT id, nickname, role, estado, token_balance, created_at, last_login
        FROM jugadores
        WHERE id = $1
        """,
        player_id,
    )

    if not player:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jugador no encontrado.",
        )

    stats = await fetchrow(
        """
        SELECT
            COUNT(*) AS total_scores,
            COALESCE(MAX(score), 0) AS max_score,
            COALESCE(AVG(score), 0) AS avg_score
        FROM puntuaciones
        WHERE jugador_id = $1
          AND estado = 'valida'
        """,
        player_id,
    )

    scores = await fetch(
        """
        SELECT score, level_reached, estado, created_at
        FROM puntuaciones
        WHERE jugador_id = $1
        ORDER BY created_at DESC
        LIMIT 50
        """,
        player_id,
    )

    sections = [
        {
            "heading": "Resumen del jugador",
            "rows": [
                ["Campo", "Valor"],
                ["Nickname", player["nickname"]],
                ["Rol", player["role"]],
                ["Estado", player["estado"]],
                ["Saldo tokens", player["token_balance"]],
                ["Fecha registro", player["created_at"]],
                ["Último login", player["last_login"]],
            ],
        },
        {
            "heading": "Estadísticas de puntajes",
            "rows": [
                ["Métrica", "Valor"],
                ["Total partidas/puntajes", stats["total_scores"]],
                ["Puntaje máximo", stats["max_score"]],
                ["Puntaje promedio", round(float(stats["avg_score"]), 2)],
            ],
        },
        {
            "heading": "Historial de puntajes",
            "rows": [["Puntaje", "Nivel", "Estado", "Fecha"]]
            + [
                [row["score"], row["level_reached"], row["estado"], row["created_at"]]
                for row in scores
            ],
        },
    ]

    await audit_pdf_request(current_user["id"], "reporte_jugador", player_id, ip_address)

    log_security_event(
        event_type="pdf_generated",
        ip_address=ip_address,
        user_id=current_user["id"],
        role=current_user["role"],
        success=True,
        reason="admin_player_history_pdf",
        extra={
            "target_player_id": player_id,
            "report_type": "reporte_jugador",
        },
    )

    pdf_bytes = build_pdf("PixelForge Studio — Reporte de jugador", sections)
    return pdf_response(pdf_bytes, "reporte_jugador.pdf")


@router.get("/admin/global/pdf")
async def global_statistics_pdf(
    request: Request,
    start_date: date = Query(...),
    end_date: date = Query(...),
    current_user: dict = Depends(require_role("admin_juego")),
):
    """
    HU-B08.

    PDF estadístico global solo para admin_juego.
    """
    ip_address = get_client_ip(request)

    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango de fechas es inválido.",
        )

    if (end_date - start_date).days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El rango máximo permitido es de 365 días.",
        )

    totals = await fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM jugadores) AS total_players,
            (SELECT COUNT(*) FROM puntuaciones WHERE created_at::date BETWEEN $1 AND $2) AS total_scores,
            (SELECT COALESCE(MAX(score), 0) FROM puntuaciones WHERE created_at::date BETWEEN $1 AND $2) AS max_score,
            (SELECT COALESCE(AVG(score), 0) FROM puntuaciones WHERE created_at::date BETWEEN $1 AND $2) AS avg_score,
            (SELECT COUNT(*) FROM token_transactions WHERE result = 'approved' AND created_at::date BETWEEN $1 AND $2) AS approved_transactions
        """,
        start_date,
        end_date,
    )

    top_scores = await fetch(
        """
        SELECT j.nickname, MAX(p.score) AS best_score
        FROM puntuaciones p
        INNER JOIN jugadores j ON j.id = p.jugador_id
        WHERE p.created_at::date BETWEEN $1 AND $2
          AND p.estado = 'valida'
        GROUP BY j.nickname
        ORDER BY best_score DESC
        LIMIT 10
        """,
        start_date,
        end_date,
    )

    token_summary = await fetch(
        """
        SELECT transaction_type, result, COUNT(*) AS total, COALESCE(SUM(tokens_amount), 0) AS tokens
        FROM token_transactions
        WHERE created_at::date BETWEEN $1 AND $2
        GROUP BY transaction_type, result
        ORDER BY transaction_type, result
        """,
        start_date,
        end_date,
    )

    sections = [
        {
            "heading": "Resumen global",
            "rows": [
                ["Métrica", "Valor"],
                ["Fecha inicial", start_date],
                ["Fecha final", end_date],
                ["Jugadores registrados", totals["total_players"]],
                ["Puntajes registrados", totals["total_scores"]],
                ["Puntaje máximo", totals["max_score"]],
                ["Puntaje promedio", round(float(totals["avg_score"]), 2)],
                ["Transacciones aprobadas", totals["approved_transactions"]],
            ],
        },
        {
            "heading": "Top puntajes",
            "rows": [["Nickname", "Mejor puntaje"]]
            + [
                [row["nickname"], row["best_score"]]
                for row in top_scores
            ],
        },
        {
            "heading": "Resumen de tokens",
            "rows": [["Tipo", "Resultado", "Total transacciones", "Tokens"]]
            + [
                [row["transaction_type"], row["result"], row["total"], row["tokens"]]
                for row in token_summary
            ],
        },
    ]

    await audit_pdf_request(current_user["id"], "reporte_global", None, ip_address)

    log_security_event(
        event_type="pdf_generated",
        ip_address=ip_address,
        user_id=current_user["id"],
        role=current_user["role"],
        success=True,
        reason="admin_global_pdf",
        extra={
            "report_type": "reporte_global",
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
    )

    pdf_bytes = build_pdf("PixelForge Studio — Reporte global", sections)
    return pdf_response(pdf_bytes, "reporte_global.pdf")