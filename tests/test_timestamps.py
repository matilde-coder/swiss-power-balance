"""Unit tests for timestamp handling (no data download needed)."""

import pandas as pd
import pytest

from pipeline.load import check_labels, interval_starts


def test_leap_year_has_366_days_of_intervals():
    starts = interval_starts(2024, 366 * 96)
    assert starts[0] == pd.Timestamp("2023-12-31 23:00", tz="UTC")  # midnight CET
    assert starts.is_unique and starts.is_monotonic_increasing


def test_wrong_row_count_is_rejected():
    with pytest.raises(ValueError):
        interval_starts(2023, 365 * 96 - 1)


def test_dst_days_have_92_and_100_intervals_in_local_time():
    local = interval_starts(2024, 366 * 96).tz_convert("Europe/Zurich")
    per_day = pd.Series(1, index=local).groupby(local.date).count()
    assert per_day[pd.Timestamp("2024-03-31").date()] == 92   # clocks go forward
    assert per_day[pd.Timestamp("2024-10-27").date()] == 100  # clocks go back
    assert per_day.drop([pd.Timestamp("2024-03-31").date(), pd.Timestamp("2024-10-27").date()]).eq(96).all()


@pytest.mark.parametrize("label_offset", ["0min", "15min"])
def test_both_swissgrid_label_conventions_are_accepted(label_offset):
    starts = interval_starts(2023, 365 * 96)
    local = starts.tz_convert("Europe/Zurich").tz_localize(None) + pd.Timedelta(label_offset)
    labels = pd.Series(local.strftime("%d.%m.%Y %H:%M"))
    check_labels(2023, labels, starts)  # should not raise


def test_misaligned_labels_are_rejected():
    starts = interval_starts(2023, 365 * 96)
    local = starts.tz_convert("Europe/Zurich").tz_localize(None) + pd.Timedelta("1h")
    with pytest.raises(ValueError):
        check_labels(2023, pd.Series(local.strftime("%d.%m.%Y %H:%M")), starts)
