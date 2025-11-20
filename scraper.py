import json
import re
import os
# --- ★ここを修正/確認してください★ ---
from playwright.sync_api import sync_playwright 
# ------------------------------------
from bs4 import BeautifulSoup
    
URL = "https://beyblade.takaratomy.co.jp/beyblade-x/event/schedule.html#schedule"

def get_color_class(event_type):
    # ... (この関数は変更なし) ...
    if "G3大会（レギュラー" in event_type or "レギュラークラス" in event_type:
        return 'G3(R)'
    elif "G3大会（オープン" in event_type or "オープンクラス" in event_type:
        return 'G3(O)'
    # ... (その他のロジック) ...
    else:
        return 'その他'

def scrape_beyblade_events_dynamic():
    """Playwrightを使用して動的に読み込まれたイベントデータを抽出する"""
    events_data = []
    
    # 💡 Playwrightのセットアップと実行
    with sync_playwright() as p:
        try:
            # GitHub Actions環境で動作させるために'chromium'を使用
            browser = p.chromium.launch()
            page = browser.new_page()
            
            # ページにアクセス
            # 修正前:
            # page.goto(URL, wait_until="networkidle") 
            
            # 修正後: タイムアウト時間を60秒に延長し、待機条件を "domcontentloaded" に緩和
            print("Navigating with longer timeout...")
            page.goto(URL, wait_until="domcontentloaded", timeout=60000) # 60秒待機
            
            # 💡 イベントリスト要素が出現するのを明示的に待機
            # ページの読み込み後、動的要素（.event-list-item）が表示されるまで待つ
            # タイムアウトは必要に応じて調整してください
            print("Waiting for dynamic content to load...")
            page.wait_for_selector('div.event-list-item', timeout=30000) 
            
            # 完全にロードされたHTMLコンテンツを取得
            content = page.content()
            
            browser.close()

            # Beautiful SoupでHTMLを解析
            soup = BeautifulSoup(content, 'html.parser')
            event_elements = soup.find_all('div', class_='event-list-item')
            
            # ... (ここからBeautifulSoupによるデータ抽出ロジックは前回と同様) ...
            
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
                    print(f"Skipping event due to missing tag: {e}")
            
            return events_data

        except Exception as e:
            print(f"Playwright execution error: {e}")
            return []

def save_data(data):
    """データをdata/events.jsonに保存する"""
    os.makedirs('data', exist_ok=True)
    with open('data/events.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Successfully saved {len(data)} events to data/events.json")


if __name__ == "__main__":
    # ❌ 誤: extracted_data = scrape_beyblade_events()
    # ✅ 正: 修正後の関数名 scrape_beyblade_events_dynamic を呼び出す
    extracted_data = scrape_beyblade_events_dynamic() 
    if extracted_data:
        save_data(extracted_data)


if __name__ == "__main__":
    extracted_data = scrape_beyblade_events()
    if extracted_data:
        save_data(extracted_data)
