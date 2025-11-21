import json
import re
import os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

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

def scrape_beyblade_events_dynamic():
    """Playwrightを使用して動的に読み込まれたイベントデータを抽出する"""
    events_data = []
    
    # ★重要な修正点: tryブロックの位置を調整★
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            
            print(f"Navigating to {URL}...")
            
            # タイムアウトを60秒に延長し、待機条件を緩和
            page.goto(URL, wait_until="domcontentloaded", timeout=60000) 
            
            # スケジュール全体を囲むコンテナ要素が出現するのを明示的に待機
            print("Waiting for schedule container (div.schedule-container)...")
            page.wait_for_selector('div.schedule-container', timeout=30000) 
            
            # 完全にロードされたHTMLコンテンツを取得
            content = page.content()
            browser.close()

            soup = BeautifulSoup(content, 'html.parser')
            
            # イベント要素を全て取得
            event_elements = soup.find_all('div', class_='event-list-item')
            
            # 💡 デバッグログ：要素の発見数を出力
            print(f"DEBUG: Found {len(event_elements)} raw event elements.")
            
            if not event_elements:
                print("Warning: No event elements found, possibly due to maintenance or no schedule.")
                return []
            
            # データ抽出ループ
            for item in event_elements:
                try:
                    date_time_str = item.find('p', class_='date-time').text.strip()
                    date_match = re.search(r'(\d{4}年\s*\d{1,2}月\d{1,2}日)', date_time_str)
                    time_match = re.search(r'(\d{1,2}：\d{2})', date_time_str)
                    
                    date_str = date_match.group(1).strip() if date_match else "日付不明"
                    time_str = time_match.group(1).strip() if time_match else "時間不明"

                    event_type = item.find('p', class_='event-name').text.strip()
                    name_location = item.find('p', class_='name-location').text.strip()
                    address = item.find('p', class_='address').text.strip()
                    details = ' '.join([p.text.strip() for p in item.find_all('p', class_='text-style-01')]).replace('\n', ' ')

                    events_data.append({
                        "date": date_str,
                        "time": time_str,
                        "type": event_type,
                        "name": name_location,
                        "location": name_location,
                        "address": address,
                        "details": details,
                        "color_label": get_color_class(event_type) 
                    })
                    
                except AttributeError as e:
                    # 要素はあったが、データ取得に必要なタグが欠けていた場合
                    print(f"Skipping event due to missing tag in inner loop: {e}")
            
            # 💡 デバッグログ：構造化されたデータの件数を出力
            print(f"DEBUG: Successfully processed {len(events_data)} structured events.")
            return events_data

        # Playwrightのタイムアウトやその他の予期せぬエラー
    except Exception as e:
        print(f"CRITICAL ERROR in Playwright execution: {e}")
        return []

def save_data(data):
    """データをdata/events.jsonに保存する"""
    os.makedirs('data', exist_ok=True)
    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved {len(data)} events to data/events.json")


if __name__ == "__main__":
    extracted_data = scrape_beyblade_events_dynamic() 
    if extracted_data is not None:
        save_data(extracted_data)
