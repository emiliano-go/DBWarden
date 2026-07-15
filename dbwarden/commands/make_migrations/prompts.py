from typing import Any


def _prompt_table_rename_confirmations(
    candidates: list[tuple[str, str, float]],
) -> list[dict[str, str]]:
    confirmed: list[dict[str, str]] = []
    if not candidates:
        return confirmed
    if len(candidates) == 1:
        old, new, ratio = candidates[0]
        answer = input(
            f"Possible table rename detected:\n"
            f"  {old} \u2192 {new}  ({int(ratio * 100):d}% columns match)\n\n"
            f"Treat as rename? [Y/n]: "
        ).strip().lower()
        if answer in ("", "y", "yes"):
            confirmed.append({"old_table": old, "new_table": new})
    else:
        print("Possible table renames detected:")
        for i, (old, new, ratio) in enumerate(candidates, 1):
            print(f"  [{i}] {old} \u2192 {new}     ({int(ratio * 100):d}% columns match)")
        print()
        print("Treat as renames? (default: all yes)")
        print("  - Press Enter to rename all")
        answer = input('  - Type numbers to drop+add instead (e.g. "1" or "1 2"): ').strip()
        if not answer:
            for old, new, _ in candidates:
                confirmed.append({"old_table": old, "new_table": new})
        else:
            decline_indices: set[int] = set()
            for part in answer.split():
                if part.isdigit():
                    decline_indices.add(int(part) - 1)
            for i, (old, new, _) in enumerate(candidates):
                if i not in decline_indices:
                    confirmed.append({"old_table": old, "new_table": new})
    return confirmed


def _detect_table_rename_candidates(
    snapshot: dict[str, Any],
    model_tables: list,
    confirmed_table_intents: set[tuple[str, str]],
) -> list[tuple[str, str, float]]:
    from dbwarden.engine.snapshot import _compute_table_overlap, RENAME_TABLE_OVERLAP_THRESHOLD

    snapshot_tables = set(snapshot.get("tables", {}).keys())
    model_table_names = {t.name for t in model_tables}

    dropped_tables = snapshot_tables - model_table_names
    added_tables = model_table_names - snapshot_tables

    candidates: list[tuple[str, str, float]] = []
    for dropped in dropped_tables:
        for added in added_tables:
            if (dropped, added) in confirmed_table_intents:
                continue
            overlap = _compute_table_overlap(dropped, added, snapshot, model_tables)
            if overlap >= RENAME_TABLE_OVERLAP_THRESHOLD:
                candidates.append((dropped, added, overlap))
    return candidates


def _prompt_rename_confirmations(
    renames: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    confirmed: list[tuple[str, str, str]] = []
    if not renames:
        return confirmed
    if len(renames) == 1:
        tbl, old, new = renames[0]
        answer = input(
            f"Detected rename: {tbl}.{old} \u2192 {tbl}.{new}. Confirm rename? [Y/n]: "
        ).strip().lower()
        if answer in ("", "y", "yes"):
            confirmed.append((tbl, old, new))
    else:
        print("Detected column renames:")
        for i, (tbl, old, new) in enumerate(renames, 1):
            print(f"  [{i}] {tbl}.{old} \u2192 {tbl}.{new}")
        print("  [s] Skip all")
        print("  [a] Accept all")
        answer = input("Select renames to confirm (e.g. 1,3 or a or s): ").strip().lower()
        if answer == "a":
            confirmed.extend(renames)
        elif answer != "s":
            for part in answer.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(renames):
                        confirmed.append(renames[idx])
    return confirmed
