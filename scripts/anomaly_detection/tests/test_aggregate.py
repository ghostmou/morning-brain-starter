from scripts.anomaly_detection.aggregate import series_for_metric, sum_by_date


def test_sum_by_date_topic_zapatos():
    rows = [
        {"date": "2026-06-01", "query": "zapatos a", "clicks": "10"},
        {"date": "2026-06-01", "query": "zapatos b", "clicks": "5"},
        {"date": "2026-06-01", "query": "otros", "clicks": "100"},
    ]
    daily = sum_by_date(rows, ["clicks"])
    assert daily["2026-06-01"]["clicks"] == 115.0
    topic = [r for r in rows if "zapatos" in r["query"]]
    daily_t = sum_by_date(topic, ["clicks"])
    assert daily_t["2026-06-01"]["clicks"] == 15.0


def test_empty_collection_rows():
    daily = sum_by_date([], ["clicks"])
    assert daily == {}
    assert series_for_metric(daily, "clicks") == {}
