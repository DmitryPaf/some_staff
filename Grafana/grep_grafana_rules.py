import json
import re

import gspread
import pandas as pd
import requests
from oauth2client.service_account import ServiceAccountCredentials


def fetch_grafana_alerts(api_url: str, token: str) -> dict:
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.json()


def format_threshold_conditions(condition: dict, reducer: str, operator: str = None, query_name: str = None) -> str:
    formatted_conditions = []
    try:
        formatted_conditions.append(f"{query_name}")
        params = condition['params']
        evaluator = condition['type']
        if evaluator == 'gt':
            formatted_conditions.append(f"{reducer} > {params[0]}")
        elif evaluator == 'lt':
            formatted_conditions.append(f"{reducer} < {params[0]}")
        elif evaluator in ['within_range', 'outside_range']:
            condition_text = f"{reducer} between {params[0]} and {params[1]}" if evaluator == 'within_range' else f"{reducer} not between {params[0]} and {params[1]}"
            formatted_conditions.append(condition_text)
        if operator:
            formatted_conditions.append(f"{operator}")
    except TypeError as e:
        for key, value in condition.items():
            if value:
                formatted_conditions.append(f"{key}: {value}")
        print(e)
        return False
    return " ".join([cond for cond in formatted_conditions if cond is not None])


def parse_grafana_alerts(alerts_data: dict) -> list:
    result = []
    sapi_alerts = alerts_data.get('sapi', [])
    for subfolder in sapi_alerts:
        subfolder_name = subfolder['name']
        interval = subfolder['interval']
        for rule in subfolder['rules']:
            summary = rule['annotations'].get('summary', '')

            link_pattern_find = r'<a href="(.*?)">.*?</a>'
            summary = re.sub(r'\{\{.*?\}\}', '', summary)
            try:
                link_pattern_cut = r'(https:\/\/\S+)"'
                links_dashboard = re.search(link_pattern_find, summary).group(0)
                links_dashboard = re.search(link_pattern_cut, links_dashboard).group(1)
            except AttributeError:
                links_dashboard = ''
            summary = re.sub(link_pattern_find, '', summary).strip()

            grafana_alert = rule['grafana_alert']
            severity = rule.get('labels', {}).get('severity', "")

            rule_data = {
                "Subfolder": subfolder_name,
                "Title": grafana_alert['title'],
                "Interval": interval,
                "Severity": severity,
                "Dashboard": "{} : {}".format(rule['annotations'].get('__dashboardUid__', ''),
                                              rule['annotations'].get('__panelId__', '')),
                "PanelLink": links_dashboard,
                "Last Updated": grafana_alert['updated'],
                "URL": f"https://{}/alerting/grafana/{grafana_alert['uid']}/view",
                "Datasource Type": None,
                "Threshold_conditions": {
                    'reducer': [],
                    'threshold_conditions': [],
                },
                "Relative Time Range": '',
                "Expression": "",
                "Summary": summary,
                "No_data": grafana_alert['no_data_state'],
                "Error_state": grafana_alert['exec_err_state'],
                "Is_paused": grafana_alert['is_paused'],
            }

            for data in grafana_alert['data']:
                try:
                    datasource_type = data['model'].get('datasource', {}).get('type')
                    if datasource_type == '__expr__':
                        rule_data["Datasource Type"] = 'Time Series'
                    else:
                        rule_data["Datasource Type"] = datasource_type
                except KeyError:
                    pass

                model_type = data['model'].get('type', '')
                if model_type == 'threshold':
                    try:
                        rule_data['Threshold_conditions']['threshold_conditions'] = format_threshold_conditions(
                            data['model']['conditions'][0]['evaluator'],
                            data['model']['conditions'][0]['reducer']['type'],
                            query_name=data['model']['conditions'][0]['query']['params']
                        )
                    except Exception as e:
                        print(e)
                    rule_data['Relative Time Range'] = data.get('relativeTimeRange', '')

                elif model_type == 'reduce':
                    rule_data['Threshold_conditions']['reducer'] = data['model'].get('reducer', [])
                elif model_type == 'classic_conditions':
                    for classic_query in data['model'].get('conditions', []):
                        final_threshold_condition = format_threshold_conditions(
                            classic_query['evaluator'],
                            classic_query['reducer']['type'],
                            classic_query['operator']['type'],
                            classic_query['query']['params'][0]
                        )
                        rule_data['Threshold_conditions']['threshold_conditions'].append(final_threshold_condition)
                        rule_data['Relative Time Range'] = data.get('relativeTimeRange', '')
                else:
                    rule_data['Expression'] = data['model'].get('expr', '')

            result.append(rule_data)
    return result


def upload_to_google_sheets(data: pd.DataFrame, sheet_url: str, credentials_json: str):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_json, scope)
    client = gspread.authorize(creds)

    try:
        sheet = client.open_by_url(sheet_url).sheet1
    except Exception as e:
        print(f"An error occurred while opening the Google Sheet: {e}")
        return

    # Clear existing data in the sheet
    sheet.clear()
    # Upload new data to the sheet
    sheet.update([data.columns.values.tolist()] + data.values.tolist())


# Example usage
api_url = ""
token = ""
sheet_url = ""
credentials_json = ""

try:
    # Fetch alerts data from Grafana
    alerts_data = fetch_grafana_alerts(api_url, token)
    # Parse the alerts data
    parsed_alerts = parse_grafana_alerts(alerts_data)
    # Convert parsed alerts to DataFrame
    df = pd.DataFrame(parsed_alerts)
    df = df.applymap(lambda x: json.dumps(x).replace('\\n', '\n').replace('\\"', '"') if isinstance(x, dict) else x)
    print(df)
    # Upload DataFrame to Google Sheets
    upload_to_google_sheets(df, sheet_url, credentials_json)


except requests.RequestException as e:
    print(f"An error occurred: {e}")
