import json
import logging
import signal
import sys
import time
from datetime import datetime

import gspread
import pandas as pd
import pytz
import requests
from gspread_formatting import *
from oauth2client.service_account import ServiceAccountCredentials

=logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def signal_handler(sig, frame):
    logging.info("Программа остановлена")
    sys.exit(0)


def initialize_gsheets(creds_file, spreadsheet_url):
    current_date = get_msk_time().strftime('%Y-%m-%d')
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(spreadsheet_url)
    try:
        worksheet = spreadsheet.worksheet(current_date)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=current_date, rows="500", cols="20")
    print(spreadsheet.worksheets())
    spreadsheet.reorder_worksheets([worksheet])
    print(spreadsheet.worksheets())
    # форматирование
    format_cell_range(worksheet, '1:1', CellFormat(textFormat=TextFormat(bold=True)))
    set_column_widths(worksheet,
                      [('A:B', 100), ('C:D', 200), ('E:F', 175), ('G', 200), ('H', 150), ('I', 200), ('J', 450)])

    format_cell_range(worksheet, 'E:I', CellFormat(wrapStrategy='WRAP'))
    format_cell_range(worksheet, 'C', CellFormat(wrapStrategy='WRAP'))
    format_cell_range(worksheet, 'A1:Z100', CellFormat(horizontalAlignment='CENTER', verticalAlignment='MIDDLE'))

    logging.info(f"Поздравляю! Сегодняшняя дата: {current_date}")
    return worksheet


def fetch_grafana_data(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        logging.info("Запрос в графану выполнен успешно")
        return response.json()
    else:
        logging.error(f"Ошибка при получении данных: {response.status_code}")
        return None


def process_data(data):
    # split and anti NaN
    df = pd.json_normalize(data, sep='_')
    df = df.fillna('')
    return df


def compare_dataframes(old_df, new_df):
    print()
    if old_df.empty:
        print()
        return pd.DataFrame()  # Только новые алерты, вернем пустой дф
    if new_df.empty:
        print()
        return old_df  # Если новый пустой, возвращаем старый
    mask = ~old_df['fingerprint'].isin(new_df['fingerprint'])
    missing_in_new = old_df[mask]
    return missing_in_new


def merge_unique(series):
    # возвращает значения, отделенные запятыми, если ячейка не пустая и уникальная
    return ', '.join(series[series.astype(bool)].astype(str).unique())


def process_json_string(json_string):
    try:
        # Разделяем строку на отдельные JSON объекты, используя запятую как разделитель
        json_objects = json_string.split('}, ')
        processed_objects = []

        for obj in json_objects:
            # Добавляем недостающую фигурную скобку, если она отсутствует
            if not obj.endswith('}'):
                obj += '}'
            parsed_obj = json.loads(obj)
            # Округляем значения и форматируем
            formatted_obj = {k: round(v, 3) for k, v in parsed_obj.items()}
            processed_objects.append(json.dumps(formatted_obj, separators=(',', ':')))

        return ', '.join(processed_objects)
    except json.JSONDecodeError as e:
        return str(e)


def write_to_gsheets(worksheet, dataframe):
    # тут склеиваются строки дф, в которых совпадают значения и старт
    grouped_df = dataframe.groupby(['labels___alert_rule_uid__', 'startsAt']).agg(merge_unique).reset_index()
    columns_dict = ['startsAt', 'endsAt', 'labels_alertname', 'annotations_summary', 'annotations___values__',
                    'generatorURL', 'labels_kubernetes_pod_name', 'labels_cluster', 'labels_path',
                    'comment']
    # добавляем ненайденные названия колонок в дф, чтобы обойти key-error
    missing_columns = [col for col in columns_dict if col not in grouped_df.columns]
    for col in missing_columns:
        grouped_df[col] = None

    grouped_df['startsAt'] = pd.to_datetime(grouped_df['startsAt'], utc=True)
    grouped_df['endsAt'] = pd.to_datetime(grouped_df['endsAt'], utc=True)

    grouped_df['startsAt'] = grouped_df['startsAt'].dt.tz_convert('Europe/Moscow')
    grouped_df['endsAt'] = grouped_df['endsAt'].dt.tz_convert('Europe/Moscow')
    # Приводим к формату "чч.мм.сс"

    grouped_df['startsAt'] = grouped_df['startsAt'].dt.strftime('%H:%M:%S')
    grouped_df['endsAt'] = grouped_df['endsAt'].dt.strftime('%H:%M:%S')

    grouped_df['annotations_summary'], grouped_df['panel_link'] = zip(*grouped_df['annotations_summary'].apply(remove_links))

    # обрезаем до 3 символов после точки
    grouped_df['annotations___values__'] = grouped_df['annotations___values__'].apply(process_json_string)

    # заголовок
    worksheet.update([grouped_df[columns_dict].columns.values.tolist()], 'A1:1')

    # считаем строки
    existing_records = worksheet.get_all_records()
    num_existing_rows = len(existing_records)
    if not dataframe.empty:
        worksheet.append_rows(grouped_df[columns_dict].values.tolist(), table_range=f"A{num_existing_rows + 1}")
    logging.info(f"Данные успешно записаны в Google Sheets, начиная с строки {num_existing_rows + 1}")
    return


def get_msk_time():
    msk_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(msk_tz)

def remove_links(text):
    removed_parts = re.findall(r'<a.*?>(.*?)</a>', text)
    cleaned_text = re.sub(r'<a.*?>.*?</a>', '', text)
    # чистое, потом удаленное
    return cleaned_text, ', '.join(removed_parts)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    url = ''
    headers = {'Authorization': 'Bearer'}
    creds_file = 'grafana-api-creds.json'
    spreadsheet_url = 'https://docs.google.com/spreadsheets/d/{}/edit'

    current_day = get_msk_time().day
    # заполняем первый раз старые данные и открываем Google Sheet
    old_data = process_data(fetch_grafana_data(url, headers))
    worksheet = initialize_gsheets(creds_file, spreadsheet_url)

    while True:
        try:
            data = fetch_grafana_data(url, headers)
            if data or not old_data.empty:
                new_data = process_data(data)
                logging.info(f"Новая инфа {new_data}!")
                logging.info(f"Старая инфа {old_data}!")
                missing_data = compare_dataframes(old_data, new_data)
                logging.info(f'Изменилось {missing_data}')
                old_data = new_data
                if missing_data.empty:
                    logging.info(f"Алерт как предыдущий!")
                else:
                    write_to_gsheets(worksheet, missing_data)

            else:
                logging.info(f"Алертов нет!")
            time.sleep(15)

        except Exception as e:
            logging.error(e)

        # проверка даты на сегодня, если следующий день - новый Google Sheet и новое счастье
        msk_time = get_msk_time()
        if msk_time.day != current_day:
            current_day = msk_time.day
            worksheet = initialize_gsheets(creds_file, spreadsheet_url)


if __name__ == "__main__":
    main()
#TODO  убрать бойлербдейт, обернуть в эксепшены

