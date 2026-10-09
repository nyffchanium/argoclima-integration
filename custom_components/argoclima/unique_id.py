"""Entity unique_id helpers.

Kept free of Home Assistant imports so the id formats (current and
legacy) can be tested directly.
"""
from __future__ import annotations

import hashlib
import uuid
from collections.abc import Collection

# Every entity name passed to ArgoEntity.__init__. These are also part of
# the legacy unique_id formats, so renaming one orphans its entities.
ENTITY_NAMES = (
    "Climate",
    "Device Light",
    "Use Remote Temperature",
    "Eco Mode Power Limit",
    "Display Unit",
    "Active Timer",
)


def _md5_uuid_hex(value: str) -> str:
    return uuid.UUID(hashlib.md5(value.encode("utf-8")).hexdigest()).hex


def entity_unique_id(device_id: str, entity_name: str) -> str:
    """Return the unique_id of an entity of a device."""
    return _md5_uuid_hex(f"{device_id}:{entity_name}")


def legacy_unique_id_migrations(
    entry_id: str,
    title: str,
    cpu_id: str | None,
    registered_ids: Collection[str],
) -> dict[str, str]:
    """Map legacy unique_ids of a standalone device entry to the current ones.

    Two older formats exist for standalone devices:
    - nyffchanium/argoclima-integration (up to 1.1.4):
      md5(entry_id + "<title> <entity name>")
    - interim fork versions: md5("<cpu_id>:<entity name>") once the
      CPU_ID was known

    Only ids present in `registered_ids` are migrated, at most one per
    entity, and never onto an id that's already registered (that would
    be rejected by the entity registry - the user already has a current
    entity in that case, which is left alone).
    """
    migrations = {}
    for name in ENTITY_NAMES:
        new_id = entity_unique_id(entry_id, name)
        if new_id in registered_ids:
            continue
        # Most recent format first, so the entity the user last had
        # wins if more than one legacy entity is still registered.
        candidates = []
        if cpu_id:
            candidates.append(entity_unique_id(cpu_id, name))
        candidates.append(_md5_uuid_hex(f"{entry_id}{title} {name}"))
        for old_id in candidates:
            if old_id in registered_ids:
                migrations[old_id] = new_id
                break
    return migrations
