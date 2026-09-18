from typing import List, cast

from ics.component import Component
from ics.contentline import Container, ContentLine
from ics.converter.base import AttributeConverter
from ics.types import ContainerItem, ContextDict, ExtraParams, copy_extra_params


class TransparencyConverter(AttributeConverter):
    """Convert the event's boolean transparency to the RFC 5545 TRANSP tokens."""

    @property
    def filter_ics_names(self) -> List[str]:
        return ["TRANSP"]

    def populate(
        self, component: Component, item: ContainerItem, context: ContextDict
    ) -> bool:
        assert isinstance(item, ContentLine)
        if context.get((self, "seen")):
            raise ValueError("attribute TRANSP can only be set once")
        value = item.value.upper()
        if value not in ("OPAQUE", "TRANSPARENT"):
            raise ValueError(f"invalid event transparency {item.value!r}")
        params = copy_extra_params(item.params)
        value_type = params.get("VALUE", ["TEXT"])
        if len(value_type) != 1 or value_type[0].upper() != "TEXT":
            raise ValueError(f"invalid transparency value type {value_type!r}")
        self.set_or_append_value(component, value == "TRANSPARENT")
        self.set_or_append_extra_params(component, params)
        context[(self, "seen")] = True
        return True

    def post_populate(self, component: Component, context: ContextDict):
        context.pop((self, "seen"), None)

    def serialize(self, component: Component, output: Container, context: ContextDict):
        value = self.get_value(component)
        if value is None:
            return
        if not isinstance(value, bool):
            raise ValueError(f"invalid event transparency {value!r}")
        output.append(
            ContentLine(
                name="TRANSP",
                params=copy_extra_params(
                    cast(ExtraParams, self.get_extra_params(component))
                ),
                value="TRANSPARENT" if value else "OPAQUE",
            )
        )
