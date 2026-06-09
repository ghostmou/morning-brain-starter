import pytest

from scripts.anomaly_detection.config import CollectionSpec, FilterSpec
from scripts.anomaly_detection.filters import filter_rows, row_matches_collection


@pytest.mark.parametrize(
    "ftype,value,text,expected",
    [
        ("contains", "zapatos", "comprar zapatos online", True),
        ("contains", "ZAPATOS", "zapatos", True),
        ("starts_with", "comprar", "comprar zapatos", True),
        ("starts_with", "comprar", "zapatos comprar", False),
        ("ends_with", "online", "zapatos online", True),
    ],
)
def test_filter_types(ftype, value, text, expected):
    coll = CollectionSpec(
        id="t",
        label="T",
        match_mode="any",
        filters=[FilterSpec(type=ftype, value=value)],
    )
    assert row_matches_collection({"query": text}, coll, dimension_key="query") is expected


def test_match_mode_all():
    coll = CollectionSpec(
        id="t",
        label="T",
        match_mode="all",
        filters=[
            FilterSpec(type="contains", value="zapatos"),
            FilterSpec(type="contains", value="running"),
        ],
    )
    assert row_matches_collection({"query": "zapatos running"}, coll, dimension_key="query")
    assert not row_matches_collection({"query": "zapatos only"}, coll, dimension_key="query")


def test_regex_filter():
    coll = CollectionSpec(
        id="p",
        label="P",
        match_mode="any",
        filters=[FilterSpec(type="regex", pattern=r"^/landing-[a-z]+")],
    )
    assert row_matches_collection({"page_path": "/landing-abc"}, coll, dimension_key="page_path")
    assert not row_matches_collection({"page_path": "/other"}, coll, dimension_key="page_path")


def test_invalid_regex_raises():
    with pytest.raises(ValueError, match="Invalid regex"):
        FilterSpec(type="regex", pattern="[unclosed").compile_regex()


def test_filter_rows_batch():
    coll = CollectionSpec(id="t", label="T", match_mode="any", filters=[FilterSpec(type="contains", value="zap")])
    rows = [{"query": "a zap"}, {"query": "nope"}]
    out = filter_rows(rows, coll, dimension_key="query")
    assert len(out) == 1
