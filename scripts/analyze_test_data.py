"""Analyze chat export from export_dynamodb_table.py."""
from __future__ import annotations
from pathlib import Path

import pandas as pd

from dynamodb_export_to_pandas import load_dynamodb_export_json
from export_dynamodb_table import export_dynamodb_table


# Script: __file__ is set. IPython / notebook: __file__ is missing — use cwd or set ROOT.
try:
    ROOT = Path(__file__).resolve().parent.parent
except NameError:
    ROOT = Path.cwd()

EXPORT_JSON = ROOT / "yougov-ai-export_final-dataset.json"

export_dynamodb_table(output=EXPORT_JSON)
final_chat_data = load_dynamodb_export_json(EXPORT_JSON)
df = final_chat_data

# --- your analysis below ---
_created = pd.to_datetime(df["created_at"], errors="coerce")
# "After 2026-04-08" = from start of 2026-04-09 (exclude the whole calendar day 2026-04-08)
_cutoff = pd.Timestamp("2026-04-09")
df_after_2026_04_08 = df[_created >= _cutoff].copy()

print(df.info())
print(df.head())
print(f"df_after_2026_04_08: {len(df_after_2026_04_08)} rows (from {len(df)} total)")
print(df_after_2026_04_08.head())


def format_chat_messages(messages, *, skip_system: bool = False) -> str:
    """Turn stored message list (role + content) into readable plain text."""
    if messages is None or (isinstance(messages, float) and pd.isna(messages)):
        return "(no messages)"
    if not isinstance(messages, list):
        return repr(messages)
    blocks = []
    n = 0
    for msg in messages:
        if not isinstance(msg, dict):
            blocks.append(f"[?] {msg!r}")
            continue
        role = msg.get("role", "?")
        if skip_system and role == "system":
            continue
        n += 1
        content = msg.get("content", "")
        blocks.append(f"--- {n}. {role.upper()} ---\n{content}")
    return "\n\n".join(blocks) if blocks else "(empty after filters)"


# User/assistant only (no system prompt). Use skip_system=False to include system messages.
df_after_2026_04_08 = df_after_2026_04_08.assign(
    messages_formatted=lambda d: d["messages"].apply(
        lambda m: format_chat_messages(m, skip_system=True)
    )
)

df_treatment_chats = df_after_2026_04_08.loc[
    df_after_2026_04_08["treatment"].eq("treatment")
].reset_index(drop=True)

# Same row order as TREATMENT_CHAT_INDEX (0, 1, 2, …)
print("\nYouGov IDs (treatment chats):")
for _i, _yid in enumerate(df_treatment_chats["yougov_id"]):
    _label = _yid if pd.notna(_yid) and str(_yid).strip() else "(missing)"
    print(f"  [{_i}]  {_label}")

# Change only this index to step through treatment chats one at a time (0-based).
TREATMENT_CHAT_INDEX = 3

_n = len(df_treatment_chats)
if _n == 0:
    print("No treatment chats in df_after_2026_04_08.")
elif not 0 <= TREATMENT_CHAT_INDEX < _n:
    print(
        f"TREATMENT_CHAT_INDEX={TREATMENT_CHAT_INDEX} is out of range; "
        f"use 0 .. {_n - 1} ({_n} treatment chats)."
    )
else:
    row = df_treatment_chats.iloc[TREATMENT_CHAT_INDEX]
    print(
        f"\nTreatment chat {TREATMENT_CHAT_INDEX + 1}/{_n}  "
        f"(index {TREATMENT_CHAT_INDEX})\n"
    )
    print("=" * 72)
    print(
        f"yougov_id={row.get('yougov_id')!s}  chat_id={row.get('chat_id')}  "
        f"user_id={row.get('user_id')}  created_at={row.get('created_at')}  "
        f"treatment={row.get('treatment')}"
    )
    print("=" * 72)
    print(row["messages_formatted"])

# Simple direct lookup by yougov_id: show treatment + messages

target = df.loc[df["yougov_id"].eq("vRnp8zgfdMh8wX"), ["treatment", "messages"]]
print("\nRows for yougov_id == 'vRnp8zgfdMh8wX':")
print(target if not target.empty else "No rows found.")