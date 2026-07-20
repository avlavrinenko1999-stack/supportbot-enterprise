from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account_organizational_unit_membership import (
    AccountOrganizationalUnitMembership,
)
from app.models.organization import Organization
from app.models.organizational_unit import OrganizationalUnit


@dataclass
class StructureNode:
    id: int
    parent_id: int | None
    name: str
    description: str | None
    supervisor: str
    deputies: list[str]
    employees: list[str]
    children: list["StructureNode"] = field(default_factory=list)
    x: float = 0
    y: float = 0
    span: int = 1


class CompanyStructurePdfService:
    MAX_FILE_AGE_SECONDS = 30 * 60
    CARD_WIDTH = 230
    CARD_HEIGHT = 126
    HORIZONTAL_GAP = 34
    VERTICAL_GAP = 76
    MARGIN = 42
    HEADER_HEIGHT = 42

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate(self, organization_id: int) -> tuple[bytes, str]:
        organization = await self.session.get(
            Organization,
            organization_id,
        )
        if organization is None:
            raise ValueError("Организация не найдена.")

        units = list(
            await self.session.scalars(
                select(OrganizationalUnit)
                .where(
                    OrganizationalUnit.organization_id
                    == organization_id
                )
                .options(
                    selectinload(OrganizationalUnit.owner),
                    selectinload(
                        OrganizationalUnit.account_memberships
                    ).selectinload(
                        AccountOrganizationalUnitMembership.account
                    ),
                )
                .order_by(OrganizationalUnit.id)
            )
        )
        roots = self._build_tree(units)
        self._layout(roots)
        buffer = BytesIO()
        self._draw_pdf(buffer, organization.name, roots)
        safe_name = "".join(
            character
            if character.isalnum() or character in "-_"
            else "_"
            for character in organization.name
        ).strip("_")
        return buffer.getvalue(), f"Структура_{safe_name or 'организации'}.pdf"

    @classmethod
    def _build_tree(
        cls,
        units: list[OrganizationalUnit],
    ) -> list[StructureNode]:
        nodes: dict[int, StructureNode] = {}
        for unit in units:
            active_memberships = [
                membership
                for membership in unit.account_memberships
                if membership.is_active
                and membership.account is not None
            ]
            nodes[unit.id] = StructureNode(
                id=unit.id,
                parent_id=unit.parent_id,
                name=unit.name,
                description=unit.description,
                supervisor=(
                    unit.owner.full_name
                    if unit.owner is not None
                    else "Не назначен"
                ),
                deputies=[
                    membership.account.full_name
                    for membership in active_memberships
                    if membership.position_name
                    == "Заместитель руководителя"
                ],
                employees=[
                    membership.account.full_name
                    for membership in active_memberships
                    if membership.account_id
                    != unit.owner_account_id
                    and membership.position_name
                    != "Заместитель руководителя"
                ],
            )

        roots: list[StructureNode] = []
        for node in nodes.values():
            parent = nodes.get(node.parent_id or -1)
            if parent is None:
                roots.append(node)
            else:
                parent.children.append(node)
        for node in nodes.values():
            node.children.sort(key=lambda child: child.name.casefold())
        roots.sort(key=lambda root: root.name.casefold())
        return roots

    @classmethod
    def _layout(cls, roots: list[StructureNode]) -> None:
        leaf_cursor = 0

        def visit(node: StructureNode, depth: int) -> None:
            nonlocal leaf_cursor
            node.y = depth * (
                cls.CARD_HEIGHT + cls.VERTICAL_GAP
            )
            if not node.children:
                node.span = 1
                node.x = leaf_cursor * (
                    cls.CARD_WIDTH + cls.HORIZONTAL_GAP
                )
                leaf_cursor += 1
                return
            for child in node.children:
                visit(child, depth + 1)
            node.span = sum(child.span for child in node.children)
            node.x = (
                node.children[0].x
                + node.children[-1].x
            ) / 2

        for root in roots:
            visit(root, 0)

    @classmethod
    def _draw_pdf(
        cls,
        target,
        organization_name: str,
        roots: list[StructureNode],
    ) -> None:
        nodes = cls._flatten(roots)
        leaf_count = max(
            1,
            sum(node.span for node in roots),
        )
        max_depth = max(
            (cls._depth(node) for node in roots),
            default=1,
        )
        page_width = max(
            842,
            cls.MARGIN * 2
            + leaf_count * cls.CARD_WIDTH
            + max(0, leaf_count - 1) * cls.HORIZONTAL_GAP,
        )
        page_height = max(
            595,
            cls.MARGIN * 2
            + 80
            + max_depth * cls.CARD_HEIGHT
            + max(0, max_depth - 1) * cls.VERTICAL_GAP,
        )
        canvas = Canvas(
            target,
            pagesize=(page_width, page_height),
        )
        font_name = cls._register_font()
        canvas.setFillColor(colors.HexColor("#F5F7FA"))
        canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        canvas.setFont(font_name, 20)
        canvas.setFillColor(colors.HexColor("#1F2937"))
        canvas.drawString(
            cls.MARGIN,
            page_height - cls.MARGIN,
            f"Структура компании · {organization_name}",
        )
        top = page_height - cls.MARGIN - 70

        for node in nodes:
            for child in node.children:
                parent_x = cls.MARGIN + node.x + cls.CARD_WIDTH / 2
                parent_y = top - node.y - cls.CARD_HEIGHT
                child_x = cls.MARGIN + child.x + cls.CARD_WIDTH / 2
                child_y = top - child.y
                middle_y = (parent_y + child_y) / 2
                canvas.setStrokeColor(colors.HexColor("#2FC6F6"))
                canvas.setLineWidth(2)
                canvas.line(parent_x, parent_y, parent_x, middle_y)
                canvas.line(parent_x, middle_y, child_x, middle_y)
                canvas.line(child_x, middle_y, child_x, child_y)

        for node in nodes:
            cls._draw_card(
                canvas,
                node,
                cls.MARGIN + node.x,
                top - node.y - cls.CARD_HEIGHT,
                font_name,
            )

        if not nodes:
            canvas.setFont(font_name, 14)
            canvas.drawString(
                cls.MARGIN,
                top,
                "Подразделения пока не созданы.",
            )
        canvas.save()

    @classmethod
    def _draw_card(
        cls,
        canvas: Canvas,
        node: StructureNode,
        x: float,
        y: float,
        font_name: str,
    ) -> None:
        canvas.setFillColor(colors.white)
        canvas.setStrokeColor(colors.HexColor("#D8DEE9"))
        canvas.roundRect(
            x,
            y,
            cls.CARD_WIDTH,
            cls.CARD_HEIGHT,
            10,
            fill=1,
            stroke=1,
        )
        canvas.setFillColor(colors.HexColor("#2FC6F6"))
        canvas.roundRect(
            x,
            y + cls.CARD_HEIGHT - cls.HEADER_HEIGHT,
            cls.CARD_WIDTH,
            cls.HEADER_HEIGHT,
            10,
            fill=1,
            stroke=0,
        )
        title_style = ParagraphStyle(
            "unit-title",
            fontName=font_name,
            fontSize=11,
            leading=13,
            textColor=colors.white,
            alignment=TA_LEFT,
        )
        body_style = ParagraphStyle(
            "unit-body",
            fontName=font_name,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#364152"),
            alignment=TA_LEFT,
        )
        title = Paragraph(escape(node.name), title_style)
        title.wrapOn(canvas, cls.CARD_WIDTH - 20, 34)
        title.drawOn(
            canvas,
            x + 10,
            y + cls.CARD_HEIGHT - 32,
        )
        deputies = ", ".join(node.deputies) or "—"
        description = node.description or "Описание не указано"
        body = Paragraph(
            f"<b>Руководитель:</b> {escape(node.supervisor)}<br/>"
            f"<b>Заместители:</b> {escape(deputies)}<br/>"
            f"<b>Сотрудники:</b> {len(node.employees)}<br/>"
            f"{escape(description[:120])}",
            body_style,
        )
        body.wrapOn(canvas, cls.CARD_WIDTH - 20, 72)
        body.drawOn(canvas, x + 10, y + 10)

    @staticmethod
    def _register_font() -> str:
        font_name = "DejaVuSans"
        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont(
                    font_name,
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                )
            )
        return font_name

    @classmethod
    def _flatten(
        cls,
        roots: list[StructureNode],
    ) -> list[StructureNode]:
        result: list[StructureNode] = []
        stack = list(reversed(roots))
        while stack:
            node = stack.pop()
            result.append(node)
            stack.extend(reversed(node.children))
        return result

    @classmethod
    def _depth(cls, node: StructureNode) -> int:
        return 1 + max(
            (cls._depth(child) for child in node.children),
            default=0,
        )
