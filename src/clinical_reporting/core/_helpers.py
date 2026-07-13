"""Small shared helpers for the core domain models."""

from __future__ import annotations

from typing import List, Optional, Sequence, TypeVar

T = TypeVar("T")


def move_item(
    item: T,
    source: Optional[List[T]],
    target: Optional[List[T]],
    order: Optional[Sequence[T]] = None,
) -> bool:
    """Move ``item`` from ``source`` to ``target`` while avoiding duplicates.

    Either list may be ``None`` to skip that side (remove-only or add-only).
    When ``order`` is provided, ``item`` is inserted into ``target`` at the
    position that keeps ``target`` consistent with that reference ordering
    (items unknown to ``order`` sink to the end); otherwise it is appended.
    Returns ``True`` when either list changed.
    """
    changed = False
    if source is not None and item in source:
        source.remove(item)
        changed = True

    if target is not None and item not in target:
        _insert_in_order(target, item, order)
        changed = True

    return changed


def _insert_in_order(target: List[T], item: T, order: Optional[Sequence[T]]) -> None:
    """Insert ``item`` into ``target`` at the slot implied by ``order``."""
    rank = None
    if order:
        try:
            rank = order.index(item)
        except ValueError:
            rank = None

    if rank is None:
        target.append(item)
        return

    for position, existing in enumerate(target):
        try:
            existing_rank = order.index(existing)
        except ValueError:
            # Entries missing from the reference order live at the end, so a
            # ranked item always goes before them.
            target.insert(position, item)
            return
        if existing_rank > rank:
            target.insert(position, item)
            return
    target.append(item)
