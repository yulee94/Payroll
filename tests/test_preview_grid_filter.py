"""Excel 미리보기 그리드 필터."""

from __future__ import annotations

import unittest

from services.preview_export import GridRow
from services.preview_grid_filter import (
    EMPTY_LABEL,
    apply_grid_filters,
    column_distinct_values,
    filterable_columns,
    format_filter_summary,
    is_column_filterable,
)


def _grid() -> list[GridRow]:
    header = GridRow(
        index=1,
        role="header",
        cells=["성명", "계열사", "사업장", "총지급"],
        aligns=["center"] * 4,
    )
    rows = [
        GridRow(index=2, role="data", cells=["김A", "(주)코스", "한국앰코", "3,000,000"], aligns=["w"] * 4),
        GridRow(index=3, role="data", cells=["이B", "(주)코스", "한국앰코생산", "2,500,000"], aligns=["w"] * 4),
        GridRow(index=4, role="data", cells=["박C", "비트윈", "본사", "4,000,000"], aligns=["w"] * 4),
    ]
    return [header, *rows]


class TestPreviewGridFilter(unittest.TestCase):
    def test_distinct_values(self) -> None:
        vals = column_distinct_values(_grid(), 1)
        self.assertEqual(vals, ["(주)코스", "비트윈"])

    def test_affiliate_column_filterable(self) -> None:
        self.assertTrue(is_column_filterable(_grid(), 1))

    def test_apply_single_affiliate(self) -> None:
        filtered = apply_grid_filters(_grid(), {1: frozenset(["(주)코스"])})
        data = [g for g in filtered if g.role == "data"]
        self.assertEqual(len(data), 2)
        self.assertTrue(all("코스" in g.cells[1] for g in data))

    def test_empty_value_label(self) -> None:
        grid = _grid()
        grid.append(
            GridRow(index=5, role="data", cells=["최D", "", "본사", "1,000,000"], aligns=["w"] * 4)
        )
        vals = column_distinct_values(grid, 1)
        self.assertIn(EMPTY_LABEL, vals)

    def test_filter_summary(self) -> None:
        filters = {1: frozenset(["(주)코스"])}
        visible = apply_grid_filters(_grid(), filters)
        text = format_filter_summary(_grid(), filters, visible_rows=visible)
        self.assertIn("계열사", text)
        self.assertIn("2/3", text)

    def test_filterable_columns_detect(self) -> None:
        cols = filterable_columns(_grid(), 4)
        self.assertIn(1, cols)
        self.assertIn(2, cols)


if __name__ == "__main__":
    unittest.main()
