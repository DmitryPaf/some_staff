import os

import requests
import json

BASE_URL = ""
TOKEN = ""
FOLDER_ID = ""
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
SAVE_DIR = "dashboard"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

response = requests.get(f"{BASE_URL}/api/search?folderIds={FOLDER_ID}", headers=headers)
dashboards = response.json()


def sanitize_filename(name):
    return name.replace("/", " - ").replace("\\", " - ").replace(":", "").replace("*", "").replace("?", "").replace('"',
                                                                                                                    "").replace(
        "<", "").replace(">", "").replace("|", "").strip()


for dashboard in dashboards:
    uid = dashboard['uid']
    title = sanitize_filename(dashboard['title'])

    dashboard_response = requests.get(f"{BASE_URL}/api/dashboards/uid/{uid}", headers=headers)
    dashboard_json = dashboard_response.json()['dashboard']

    save_path = os.path.join(SAVE_DIR, f"{title}.json")
    with open(save_path, "w") as f:
        json.dump(dashboard_json, f, indent=4)

print("Все дашборды из папки успешно сохранены.")
