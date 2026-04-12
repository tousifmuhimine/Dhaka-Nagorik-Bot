from __future__ import annotations

from datetime import datetime

import flet as ft

from app.schemas.complaint import ComplaintRecord


def metric_card(title: str, value: str, color: str) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Text(title, size=14, color=ft.Colors.GREY_700),
                ft.Text(value, size=28, weight=ft.FontWeight.BOLD, color=color),
            ],
            tight=True,
        ),
        padding=16,
        border_radius=18,
        bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(blur_radius=18, color=ft.Colors.with_opacity(0.08, ft.Colors.BLACK)),
    )


def timeline(complaint: ComplaintRecord) -> ft.Column:
    in_progress_done = complaint.status in {"In Progress", "Done", "Resolved", "Rejected"}
    done_done = complaint.status in {"Done", "Resolved", "Rejected"} or complaint.completed_at is not None
    confirmed_done = complaint.status == "Resolved" or complaint.user_confirmed_at is not None
    steps = [
        ("Submitted", complaint.created_at, True),
        ("Acknowledged", complaint.acknowledged_at, complaint.acknowledged_at is not None),
        ("In Progress", None, in_progress_done),
        ("Done", complaint.completed_at, done_done),
        ("Confirmed", complaint.user_confirmed_at, confirmed_done),
    ]
    controls: list[ft.Control] = []
    for label, ts, is_done in steps:
        controls.append(
            ft.Row(
                [
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE if is_done else ft.Icons.RADIO_BUTTON_UNCHECKED,
                        color=ft.Colors.GREEN_600 if is_done else ft.Colors.GREY_500,
                    ),
                    ft.Text(label, width=140, weight=ft.FontWeight.W_600),
                    ft.Text(_format_ts(ts) if ts else ("Status reached" if is_done else "Not set"), color=ft.Colors.GREY_700),
                ]
            )
        )
    controls.append(ft.Text(f"Current status: {complaint.status}", weight=ft.FontWeight.BOLD))
    return ft.Column(controls, spacing=8)


def complaint_card(complaint: ComplaintRecord) -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(complaint.category, size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(
                            content=ft.Text(complaint.status, color=ft.Colors.WHITE),
                            bgcolor=ft.Colors.BLUE_700,
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=999,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Text(f"{complaint.thana} | {complaint.area}"),
                ft.Text(complaint.summary, color=ft.Colors.GREY_800),
                timeline(complaint),
                ft.Text(
                    f"Compliance: {complaint.compliance_status} | Inconsistency: {complaint.inconsistency_score}",
                    color=ft.Colors.GREY_700,
                ),
            ],
            spacing=10,
        ),
        padding=18,
        border_radius=20,
        bgcolor=ft.Colors.with_opacity(0.98, ft.Colors.WHITE),
        shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.with_opacity(0.06, ft.Colors.BLACK)),
    )


def _format_ts(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M") if value else "Not set"
