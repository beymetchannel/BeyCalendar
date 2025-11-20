import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

# ターゲットURL
URL = "https://beyblade.takaratomy.co.jp/beyblade-x/event/schedule.html#schedule"

def get_color_class(event_type):
    """イベント種別に基づいてカラーラベルを決定（JSロジックと同期）"""
    if "G3大会（レギュラー" in event_type or "レギュラークラス" in event_type:
        return 'G3(R)'
    elif "G3大会（オープン" in event_type or "オープンクラス" in event_type:
        return 'G3(O)'
    elif "S1イベント" in event_type:
        return 'S1'
    elif "アンバサダーイベント" in event_type:
        return 'Amb'
    elif "G2大会" in event_type:
        return 'G2'
    elif "G1大会" in event_type:
        return 'G1'
    else:
        return 'その他'

def scrape_beyblade_events():
    """イベントスケジュールページからデータを抽出する"""
    try:
        response = requests.get(URL)
        response.raise_for_status() # HTTPエラーを確認
    except requests.exceptions.RequestException as e:
        print(f"Error accessing URL: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # イベント要素を全て取得 (構造は前回抽出時と同じ前提)
    event_elements = soup.find_all('div', class_='event-list-item')
    
    events_data = []
    
    for item in event_elements:
        try:
            date_time_str = item.find('p', class_='date-time').text.strip()
            
            # 日付と時刻を分離
            date_match = re.search(r'(\d{4}年\s*\d{1,2}月\d{1,2}日)', date_time_str)
            time_match = re.search(r'(\d{1,2}：\d{2})', date_time_str)
            
            date_str = date_match.group(1).strip() if date_match else "日付不明"
            time_str = time_match.group(1).strip() if time_match else "時間不明"

            event_type = item.find('p', class_='event-name').text.strip()
            name_location = item.find('p', class_='name-location').text.strip()
            address = item.find('p', class_='address').text.strip()
            
            # 詳細情報 (参加費、定員など) は、複数のテキストノードを結合して取得
            details = ' '.join([p.text.strip() for p in item.find_all('p', class_='text-style-01')]).replace('\n', ' ')
            
            
            # 参加方法などの詳細を取得 (今回は簡略化し、detailsにまとめる)
            reception_methods = [
                p.text.strip() for p in item.find_all('div', class_='text-set')
                if '参加方法' in p.text
            ]
            reception = reception_methods[0] if reception_methods else "情報なし"

            # 参加費と定員を抽出
            fee_match = re.search(r'参加費：([^\s]+)', details)
            capacity_match = re.search(r'定員数\s*(\d+名)', details)

            
            events_data.append({
                "date": date_str,
                "time": time_str,
                "type": event_type,
                "name": name_location,
                "location": name_location, # 会場名は name_location から抽出が必要だがここでは簡略化
                "address": address,
                "details": details,
                "entry_fee": fee_match.group(1) if fee_match else "不明",
                "capacity": capacity_match.group(1) if capacity_match else "不明",
                "reception": reception,
                "color_label": get_color_class(event_type) # JSでのフィルタリングに使わないがデバッグ用
            })
            
        except AttributeError as e:
            # 必要なタグが見つからなかった場合、そのイベントはスキップ
            print(f"Skipping event due to missing tag: {e}")
        
    return events_data

def save_data(data):
    """データをdata/events.jsonに保存する"""
    # dataフォルダがない場合は作成
    import os
    os.makedirs('data', exist_ok=True)
    
    # JSONファイルとして保存
    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved {len(data)} events to data/events.json")


if __name__ == "__main__":
    extracted_data = scrape_beyblade_events()
    if extracted_data:
        save_data(extracted_data)
