import time
import json
import re # 👈 正規表現ライブラリを追加
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException

# ==========================================================
# 🔴 定数定義
# ==========================================================
IFRAME_URL = "https://beyblade.takaratomy.co.jp/beyblade-x/shop_event/manage_jpnew/open_list_all.html"
OUTPUT_JSON_FILENAME = "events.json"
TABLE_SELECTOR = "table.event_list"
WAIT_TIMEOUT = 30 
# ==========================================================


def fetch_schedule_data(url):
    """
    Seleniumを使用して、指定されたURLからイベントデータを抽出する (2列構造対応)
    """
    print(f"スケジュールデータソースに直接アクセス中: {url}")
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--headless')
    
    try:
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"WebDriverの起動に失敗しました: {e}")
        return None

    try:
        driver.get(url)
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        
        print(f"テーブル要素 ('{TABLE_SELECTOR}') のロードを待機中...")
        table_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, TABLE_SELECTOR))
        )
        
        time.sleep(2)
        
        events_data = []
        rows = table_element.find_elements(By.TAG_NAME, 'tr')
        
        if len(rows) <= 1:
            print("🚨 警告: ヘッダー行しか見つかりませんでした。公式サイトで現在イベントが掲載されていない可能性があります。")
            return []
            
        print(f"✅ テーブル内に {len(rows)} 行のデータが見つかりました (ヘッダー含む)。抽出を開始します。")

        # ヘッダー行 (rows[0]) はスキップ
        for i, row in enumerate(rows[1:]):
            row_index = i + 1
            
            cols = row.find_elements(By.TAG_NAME, 'td')
            
            # 構造が2列であることを確認
            if len(cols) != 2:
                print(f"❌ 抽出エラー: {row_index}行目の列数が2ではありません ({len(cols)}列)。スキップします。")
                continue
                    
            try:
                col1_text = cols[0].text.strip()
                col2_text = cols[1].text.strip()
                
                # --- Col 1 Parsing (日付、時間、種別を文字列から抽出) ---
                
                # 1. Date (YYYY年 M月 D日) と Day of Week (曜日)
                # 曜日を含むパターンを優先して検索
                date_day_match = re.search(r'(\d{4}年\s*\d{1,2}月\s*\d{1,2}日)\s*\((.*?)\)', col1_text)
                
                if date_day_match:
                    date_info = date_day_match.group(1).strip()
                    day_of_week = date_day_match.group(2).strip()
                else:
                    # 曜日がない場合
                    date_match = re.search(r'(\d{4}年\s*\d{1,2}月\s*\d{1,2}日)', col1_text)
                    date_info = date_match.group(1).strip() if date_match else "日付不明"
                    day_of_week = "不明"

                # 2. Time (H：MM)
                time_match = re.search(r'(\d{1,2}：\d{2})', col1_text)
                time_info = time_match.group(1).strip() if time_match else "時間不明"
                
                # 3. Type (時間と「詳細はこちら」の間のテキスト)
                type_start_index = col1_text.find(time_info) + len(time_info)
                type_end_index = col1_text.find("詳細はこちら")
                
                if type_start_index != -1 and type_end_index != -1 and type_end_index > type_start_index:
                    raw_type = col1_text[type_start_index:type_end_index].strip()
                    # 不要な文字列(Share, X-TREME)を除去してクリーンアップ
                    event_type = raw_type.replace('Share', '').replace('X-TREME', '').strip()
                else:
                    event_type = "種別不明"

                # --- Col 2 Parsing (イベント名、詳細、住所を改行で分割) ---
                lines2 = col2_text.split('\n')
                
                # 1. Name (一行目)
                event_name = lines2[0].strip() if len(lines2) > 0 else "名前不明"
                
                # 2. Address (最終行)
                address_info = lines2[-1].strip() if len(lines2) > 0 else "住所不明"
                
                # 3. Location/Details (中間の行。イベント名と住所を除いた全て)
                if len(lines2) > 2:
                    # 中間すべての行を結合して詳細とする
                    location_details = "\n".join(lines2[1:-1]).strip()
                elif len(lines2) == 2:
                    # 2行しかない場合 (名前と住所のみで詳細なし、または詳細が2行目)
                    location_details = lines2[1].strip()
                else:
                    location_details = "詳細情報なし"
                
                # locationフィールドは、場所に関する情報として「イベント名」を使用
                location = event_name 

                
                events_data.append({
                    "date": date_info,
                    "day_of_week": day_of_week,
                    "time": time_info,
                    "name": event_name,
                    "location": location,
                    "type": event_type,
                    "details": location_details,
                    "address": address_info 
                })
            except Exception as row_e:
                print(f"❌ 抽出エラー: {row_index}行目の処理中に予期せぬエラーが発生しました: {row_e}")
                continue

        print(f"✅ スケジュールデータ {len(events_data)} 件の抽出に成功しました。")
        return events_data

    except TimeoutException:
        print(f"\n🛑 タイムアウトエラーが発生しました。要素 ('{TABLE_SELECTOR}') が見つかりませんでした。")
        return None
        
    except WebDriverException as e:
        print(f"\n❌ WebDriver通信エラーが発生しました: {e.msg}")
        return None
        
    except Exception as e:
        print(f"\n❌ その他のエラーが発生しました: {e}")
        return None

    finally:
        driver.quit()


def save_to_json(data, filename):
    if not data:
        print("保存するデータがありません。JSONファイルの作成をスキップします。")
        return
        
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ データを正常にJSONファイルに保存しました。ファイル名: {filename}")
    except IOError as e:
        print(f"JSONファイルへの書き込み中にエラーが発生しました: {e}")

if __name__ == "__main__":
    extracted_data = fetch_schedule_data(IFRAME_URL)
    
    if extracted_data is not None:
        save_to_json(extracted_data, OUTPUT_JSON_FILENAME)
