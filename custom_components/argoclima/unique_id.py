from __future__ import annotations

import hashlib
import uuid
from collections.abc import Collection

# Part of every unique_id format; renaming one orphans its entities.
ENTITY_NAMES = (
    "Climate",
    "Device Light",
    "Use Remote Temperature",
    "Eco Mode Power Limit",
    "Display Unit",
    "Active Timer",
    "Firmware",
    "WiFi Firmware",
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

    Legacy formats:
    - up to 1.1.4 (nyffchanium/argoclima-integration):
      md5(entry_id + "<title> <entity name>")
    - interim versions: md5("<cpu_id>:<entity name>")

    Entities that already have a current unique_id are left untouched.
    """
    migrations = {}
    for name in ENTITY_NAMES:
        new_id = entity_unique_id(entry_id, name)
        if new_id in registered_ids:
            continue
        candidates = []
        if cpu_id:
            candidates.append(entity_unique_id(cpu_id, name))
        candidates.append(_md5_uuid_hex(f"{entry_id}{title} {name}"))
        for old_id in candidates:
            if old_id in registered_ids:
                migrations[old_id] = new_id
                break
    return migrations
