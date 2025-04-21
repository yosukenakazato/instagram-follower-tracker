import os
import re
import json
import datetime
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_follower_count(username):
    """インスタグラムのフォロワー数を取得する関数（単純なHTTPリクエスト）"""
    try:
        print(f"インスタグラムのプロフィール取得を開始: {username}")
        # インスタグラムのユーザープロフィールページにアクセス
        url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/json',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://www.instagram.com/',
        }
        
        print(f"URLにアクセス中: {url}")
        response = requests.get(url, headers=headers)
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code != 200:
            print(f"ページの取得に失敗しました。ステータスコード: {response.status_code}")
            # 失敗した場合は別のURLを試す
            url = f"https://www.instagram.com/{username}/"
            print(f"別のURLを試行中: {url}")
            response = requests.get(url, headers=headers)
            print(f"新しいステータスコード: {response.status_code}")
            
            if response.status_code != 200:
                return None
        
        # レスポンスがJSONの場合
        try:
            print("JSONレスポンスの解析を試みます")
            data = response.json()
            if 'graphql' in data and 'user' in data['graphql']:
                follower_count = data['graphql']['user']['edge_followed_by']['count']
                print(f"JSON応答からフォロワー数を取得: {follower_count}")
                return follower_count
        except:
            print("JSONではありません、HTMLとして解析を続行")
            
        print("レスポンスのHTMLテキスト解析中...")
        # 様々なパターンを試して最適な抽出方法を見つける
        patterns = [
            r'<script type="application/json" data-sjs>({.*?})</script>',
            r'<script type="text/javascript">window\._sharedData = ({.*?});</script>',
            r'"edge_followed_by":{"count":(\d+)}'
        ]
        
        for pattern in patterns:
            print(f"パターン試行中: {pattern}")
            match = re.search(pattern, response.text)
            if match:
                print("マッチしました")
                if pattern.endswith('(\d+)}'):
                    # 直接数値を取得する場合
                    follower_count = int(match.group(1))
                    print(f"直接フォロワー数を抽出: {follower_count}")
                    return follower_count
                else:
                    # JSONとして解析する場合
                    try:
                        json_data = json.loads(match.group(1))
                        print("JSONデータの解析に成功")
                        # 様々なJSON構造に対応
                        if 'entry_data' in json_data and 'ProfilePage' in json_data['entry_data']:
                            user_data = json_data['entry_data']['ProfilePage'][0]['graphql']['user']
                            follower_count = user_data['edge_followed_by']['count']
                            print(f"従来のJSON構造からフォロワー数を抽出: {follower_count}")
                            return follower_count
                        # その他の構造も試す
                        # ...
                    except Exception as e:
                        print(f"JSONデータの解析に失敗: {e}")
        
        print("すべての方法でフォロワー数の抽出に失敗しました")
        print(f"レスポンスの一部: {response.text[:1000]}...")
        return None
        
    except Exception as e:
        import traceback
        print(f"エラーが発生しました: {e}")
        print(f"詳細なエラー: {traceback.format_exc()}")
        return None
def update_spreadsheet(spreadsheet_id, date, follower_count):
    """Google スプレッドシートにデータを追加する関数"""
    # 認証情報の取得
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    
    # GitHub Secretsから取得した認証情報の文字列をJSONファイルに書き込む
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    with open('credentials.json', 'w') as f:
        f.write(creds_json)
    
    # 認証情報の読み込み
    creds = service_account.Credentials.from_service_account_file(
        'credentials.json', scopes=SCOPES)
    
    # Google Sheets APIを使用
    service = build('sheets', 'v4', credentials=creds)
    
    # 最終行を取得
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='Sheet1!A:A'
    ).execute()
    values = result.get('values', [])
    next_row = len(values) + 1
    
    # 値を更新
    values = [
        [date, follower_count]
    ]
    body = {
        'values': values
    }
    
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f'Sheet1!A{next_row}:B{next_row}',
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    
    print(f"{date}のフォロワー数({follower_count})を記録しました。")

def main():
    try:
        # 環境変数から値を取得
        instagram_username = os.environ.get('INSTAGRAM_USERNAME')
        spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        
        # デバッグ情報をログに記録
        print(f"対象アカウント: {instagram_username}")
        print(f"スプレッドシートID: {spreadsheet_id}")
        
        # 今日の日付を取得
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        print(f"実行日: {today}")
        
        # フォロワー数を取得
        follower_count = get_follower_count(instagram_username)
        
        if follower_count is not None:
            print(f"フォロワー数取得成功: {follower_count}")
            # スプレッドシートを更新
            update_spreadsheet(spreadsheet_id, today, follower_count)
        else:
            print("フォロワー数の取得に失敗しました。エラーとして記録します。")
            # エラーをスプレッドシートに記録
            update_spreadsheet(spreadsheet_id, today, "取得失敗")
    
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        # 可能であればエラーもスプレッドシートに記録
        try:
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            spreadsheet_id = os.environ.get('SPREADSHEET_ID')
            update_spreadsheet(spreadsheet_id, today, f"エラー: {str(e)}")
        except:
            print("エラー情報の記録にも失敗しました")

if __name__ == "__main__":
    main()
