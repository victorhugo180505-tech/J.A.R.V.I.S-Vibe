from __future__ import annotations


def filter_repo_names(items: list[dict], names: list[str], visibility: str) -> list[str]:
    vis = (visibility or "ALL").upper()
    if vis not in {"PUBLIC", "PRIVATE"}:
        return [str(n) for n in names if str(n).strip()]
    if not isinstance(items, list):
        return []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        item_vis = str(item.get("visibility") or "UNKNOWN").strip().upper()
        if name and item_vis == vis:
            result.append(name)
    return result


def build_cached_repos_response(items: list[dict], names: list[str], visibility: str) -> tuple[str, str]:
    selected = filter_repo_names(items, names, visibility)
    if not selected:
        return (
            "Aún no he consultado GitHub en esta sesión. Pídeme ‘lista mis repositorios’.",
            "",
        )

    preview = selected[:8]
    if len(selected) > 8:
        speech = f"{', '.join(preview)} y {len(selected) - 8} más."
    else:
        speech = ", ".join(preview)
    verbose = "\n".join(f"- {name}" for name in selected[:13])
    return speech, verbose
