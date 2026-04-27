from pathlib import Path

try:
    from dynamodb_export_to_pandas import load_dynamodb_export_json
except ModuleNotFoundError:
    from scripts.dynamodb_export_to_pandas import load_dynamodb_export_json

ROOT = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd()
final_chat_data = load_dynamodb_export_json(ROOT / "yougov-ai-export_final-dataset.json")
df = final_chat_data
unique_user_count = df["user_id"].nunique(dropna=True)

print("Unique users:", unique_user_count)
