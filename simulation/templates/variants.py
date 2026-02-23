"""Priority list transformation functions for generating build variants.

Pure functions that transform priority lists to produce different XP spending
orders. Variants are generated on-the-fly as CharacterConfigs — no variant
YAML files are stored.
"""

PriorityList = list[tuple[str, str, int]]
PriorityItem = tuple[str, str, int]


def identity(priorities: PriorityList) -> PriorityList:
    """Return a copy of the priority list (baseline transform)."""
    return list(priorities)


def swap_positions(
    priorities: PriorityList,
    item_a: PriorityItem,
    item_b: PriorityItem,
) -> PriorityList:
    """Swap the positions of two items in the priority list.

    Raises ValueError if either item is not found.
    """
    result = list(priorities)
    try:
        idx_a = result.index(item_a)
    except ValueError:
        raise ValueError(f"Item not found in priority list: {item_a}")
    try:
        idx_b = result.index(item_b)
    except ValueError:
        raise ValueError(f"Item not found in priority list: {item_b}")
    result[idx_a], result[idx_b] = result[idx_b], result[idx_a]
    return result


def move_before(
    priorities: PriorityList,
    item: PriorityItem,
    before: PriorityItem,
) -> PriorityList:
    """Move item to just before the target item.

    Raises ValueError if either item is not found.
    """
    result = list(priorities)
    try:
        result.remove(item)
    except ValueError:
        raise ValueError(f"Item not found in priority list: {item}")
    try:
        target_idx = result.index(before)
    except ValueError:
        raise ValueError(f"Target item not found in priority list: {before}")
    result.insert(target_idx, item)
    return result


def move_block_before(
    priorities: PriorityList,
    block: list[PriorityItem],
    before: PriorityItem,
) -> PriorityList:
    """Move a block of items to just before a target item.

    Items in the block are removed from their current positions and inserted
    in order just before the target. The block items do not need to be
    contiguous in the original list.

    Raises ValueError if any block item or the target is not found.
    """
    result = list(priorities)
    for item in block:
        try:
            result.remove(item)
        except ValueError:
            raise ValueError(f"Block item not found in priority list: {item}")
    try:
        target_idx = result.index(before)
    except ValueError:
        raise ValueError(f"Target item not found in priority list: {before}")
    for i, item in enumerate(block):
        result.insert(target_idx + i, item)
    return result
