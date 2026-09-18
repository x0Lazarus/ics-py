from copy import copy
from datetime import datetime
from types import SimpleNamespace

import dateutil.zoneinfo
import pytest

from ics import Calendar, Event
from ics.timezone import UTC, Timezone
from ics.timezone.converters import Timezone_from_dateutil


@pytest.mark.parametrize(
    "alias, canonical",
    [("US/Pacific", "America/Los_Angeles"), ("US/Eastern", "America/New_York")],
)
@pytest.mark.parametrize("prefix", ["", "/usr/share/zoneinfo/"])
@pytest.mark.parametrize("month", [1, 7])
def test_timezone_alias_round_trip(alias, canonical, prefix, month):
    expected = Timezone.from_tzid(canonical)
    actual = Timezone.from_tzid(prefix + alias)
    assert actual == expected
    assert actual.tzid.endswith(canonical)

    # Unix dateutil tzfiles retain the absolute path to the alias file.
    original = copy(dateutil.zoneinfo.get_zonefile_instance().zones[alias])
    original._filename = prefix + alias
    assert Timezone_from_dateutil(original) == expected
    begin = datetime(2014, month, 1, 12, tzinfo=original)
    assert begin.utcoffset() == begin.replace(tzinfo=expected).utcoffset()
    event = Event(begin=begin, dtstamp=datetime(2022, 6, 6, tzinfo=UTC))
    serialized = Calendar(events=[event]).serialize()
    assert f"DTSTART;TZID={expected.tzid}:2014{month:02}01T120000" in serialized
    restored = Calendar(serialized).events[0]
    assert restored.begin == begin
    assert restored.begin.tzinfo == expected
    assert restored == event


@pytest.mark.parametrize("tzid", ["America/Los_Angeles", "Pacific Standard Time"])
def test_timezone_alias_lookup_preserves_existing_precedence(monkeypatch, tzid):
    expected = Timezone.from_tzid("America/Los_Angeles")

    def unexpected_alias_lookup():
        raise AssertionError("existing resources must take precedence over aliases")

    monkeypatch.setattr(
        dateutil.zoneinfo, "get_zonefile_instance", unexpected_alias_lookup
    )
    assert Timezone.from_tzid(tzid) == expected


@pytest.mark.parametrize(
    "aliases",
    [
        {},
        {"Unknown/Zone": SimpleNamespace()},
        {"Unknown/Zone": SimpleNamespace(_filename=None)},
        {"Unknown/Zone": SimpleNamespace(_filename="Unknown/Canonical")},
    ],
)
def test_timezone_alias_without_resource_still_raises(monkeypatch, aliases):
    monkeypatch.setattr(
        dateutil.zoneinfo,
        "get_zonefile_instance",
        lambda: SimpleNamespace(zones=aliases),
    )
    with pytest.raises(
        ValueError, match="no vTimezone.ics file found for Unknown/Zone"
    ):
        Timezone.from_tzid("Unknown/Zone")
