"""Typed integration models for Huckleberry."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from huckleberry_api.firebase_types import (
    FirebaseChildDocument,
    FirebaseDiaperDocumentData,
    FirebaseFeedDocumentData,
    FirebaseGrowthData,
    FirebaseHealthDocumentData,
    FirebaseSleepDocumentData,
    FirebaseUserChildRef,
)

from .timestamps import as_iso8601_datetime


@dataclass(frozen=True, slots=True)
class HuckleberryChildProfile:
    """Resolved child profile used by the integration."""

    uid: str
    reference: FirebaseUserChildRef
    document: FirebaseChildDocument

    @property
    def name(self) -> str:
        """Return the display name for the child."""
        return self.document.childsName or self.reference.nickname or self.uid

    @property
    def picture(self) -> str | None:
        """Return the profile picture URL if available."""
        return self.document.picture or self.reference.picture

    @property
    def color(self) -> str | None:
        """Return the child color if available."""
        return self.document.color or self.reference.color

    def as_attributes(self) -> dict[str, object]:
        """Return stable profile attributes for Home Assistant entities."""
        attributes: dict[str, object] = {
            "uid": self.uid,
            "name": self.name,
        }

        if self.document.birthdate is not None:
            attributes["birthday"] = self.document.birthdate
        if self.picture is not None:
            attributes["picture"] = self.picture
        if self.document.gender is not None:
            attributes["gender"] = self.document.gender
        if self.color is not None:
            attributes["color"] = self.color
        if self.document.createdAt is not None:
            attributes["created_at"] = as_iso8601_datetime(self.document.createdAt)
        if self.document.nightStart is not None:
            attributes["night_start"] = self.document.nightStart
        if self.document.morningCutoff is not None:
            attributes["morning_cutoff"] = self.document.morningCutoff
        if self.document.naps is not None:
            attributes["expected_naps"] = self.document.naps
        if self.document.categories is not None:
            attributes["categories"] = self.document.categories

        return attributes


@dataclass(slots=True)
class HuckleberryChildState:
    """Runtime state tracked per child."""

    profile: HuckleberryChildProfile
    sleep_status: FirebaseSleepDocumentData | None = None
    feed_status: FirebaseFeedDocumentData | None = None
    health_status: FirebaseHealthDocumentData | None = None
    diaper_status: FirebaseDiaperDocumentData | None = None
    child_document: FirebaseChildDocument | None = None

    @property
    def growth_data(self) -> FirebaseGrowthData | None:
        """Return the latest growth entry from the health document."""
        prefs = self.health_status.prefs if self.health_status is not None else None
        return prefs.lastGrowthEntry if prefs is not None else None


def children_sensor_attributes(
    children: Sequence[HuckleberryChildProfile],
) -> dict[str, object]:
    """Return aggregated children attributes for the global sensor."""
    payload: list[dict[str, object]] = []
    child_ids: list[str] = []
    child_names: list[str] = []

    for child in children:
        payload.append(child.as_attributes())
        child_ids.append(child.uid)
        child_names.append(child.name)

    return {
        "children": payload,
        "child_ids": child_ids,
        "child_names": child_names,
    }
