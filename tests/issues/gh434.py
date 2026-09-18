import pytest

from ics import Calendar, Event
from ics.event import deterministic_event_data


def parse_event(*properties):
    return Calendar(
        "\r\n".join(
            [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:transparency-test",
                "BEGIN:VEVENT",
                "UID:transparency@example.org",
                "DTSTAMP:20000101T120000Z",
                *properties,
                "END:VEVENT",
                "END:VCALENDAR",
            ]
        )
    ).events[0]


@deterministic_event_data()
@pytest.mark.parametrize(
    "transparent, expected", [(False, "OPAQUE"), (True, "TRANSPARENT"), (None, None)]
)
def test_transparency_round_trip(transparent, expected):
    event = Event(transparent=transparent)
    serialized = Calendar(events=[event]).serialize()
    assert "TRANSPARENT:" not in serialized
    properties = [
        line for line in serialized.splitlines() if line.startswith("TRANSP:")
    ]
    assert properties == ([] if expected is None else [f"TRANSP:{expected}"])
    assert Calendar(serialized).events[0].transparent is transparent


@pytest.mark.parametrize(
    "value, expected",
    [
        ("OPAQUE", False),
        ("TRANSPARENT", True),
        ("opaque", False),
        ("Transparent", True),
    ],
)
def test_parse_transparency(value, expected):
    event = parse_event(f"TRANSP:{value}")
    assert event.transparent is expected
    assert not event.extra["TRANSP"]


def test_unspecified_transparency():
    event = parse_event()
    assert event.transparent is None
    assert "TRANSP" not in event.serialize()


def test_update_transparency():
    event = parse_event("TRANSP:TRANSPARENT")
    event.transparent = False
    assert "TRANSP:OPAQUE" in event.serialize()
    assert "TRANSP:TRANSPARENT" not in event.serialize()
    event.transparent = None
    assert "TRANSP" not in event.serialize()


@pytest.mark.parametrize("value, expected", [("OPAQUE", False), ("TRANSPARENT", True)])
@pytest.mark.parametrize("parameter", ["VALUE", "value", "VaLuE"])
def test_transparency_parameters_and_other_values(value, expected, parameter):
    event = parse_event(
        f"TRANSP;{parameter}=tExT;X-TEST=retained:{value}",
        "SUMMARY;VALUE=TEXT:Ordinary text",
        "ATTENDEE;RSVP=TRUE:mailto:guest@example.org",
    )
    assert event.transparent is expected
    assert event.summary == "Ordinary text"
    assert event.attendees[0].rsvp is True
    serialized = event.serialize()
    assert f"TRANSP;{parameter}=tExT;X-TEST=retained:{value}" in serialized
    assert "SUMMARY:Ordinary text" in serialized
    assert "RSVP=TRUE" in serialized
    restored = Calendar(Calendar(events=[event]).serialize()).events[0]
    assert restored.transparent is expected
    assert restored.extra_params["TRANSPARENT"] == event.extra_params["TRANSPARENT"]


@pytest.mark.parametrize("value", ["BOOLEAN", "TEXT,BOOLEAN"])
@pytest.mark.parametrize("parameter", ["VALUE", "value", "VaLuE"])
def test_invalid_transparency_value_type(value, parameter):
    with pytest.raises(ValueError, match="transparency value type"):
        parse_event(f"TRANSP;{parameter}={value}:OPAQUE")


@pytest.mark.parametrize(
    "parameters",
    ["VALUE=TEXT;value=TEXT", "VaLuE=TEXT;VALUE=BOOLEAN", "value=BOOLEAN;VaLuE=TEXT"],
)
def test_duplicate_transparency_value_type(parameters):
    with pytest.raises(ValueError, match="transparency value type"):
        parse_event(f"TRANSP;{parameters}:OPAQUE")


@pytest.mark.parametrize("value", [0, 1, "OPAQUE"])
def test_invalid_transparency_attribute(value):
    with pytest.raises(ValueError):
        Event(transparent=value).serialize()


@deterministic_event_data()
def test_multiple_event_transparencies():
    values = [False, True, None, False]
    calendar = Calendar(events=[Event(transparent=value) for value in values])
    restored = Calendar(calendar.serialize())
    assert [event.transparent for event in restored.events] == values


def test_duplicate_transparency():
    with pytest.raises(ValueError, match="TRANSP.*once"):
        parse_event("TRANSP:OPAQUE", "TRANSP:TRANSPARENT")


@pytest.mark.parametrize("value", ["TRUE", "FALSE", "unknown"])
def test_invalid_transparency(value):
    with pytest.raises(ValueError, match="transparency"):
        parse_event(f"TRANSP:{value}")
