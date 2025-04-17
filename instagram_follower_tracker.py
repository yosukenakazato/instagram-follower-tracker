import os
import datetime
import instagrapi
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_follower_count(username, login_user, login_password):
    """インスタグラムのフォロワー数を取得する関数"""
    # instagrapiのインスタンスを作成
    L = instagrapi.instagrapi()
    
    try:
        # ログイン
        L.login(login_user, login_password)
        
        # プロフィール情報を取得
        profile = instagrapi.Profile.from_username(L.context, username)
        
        # フォロワー数を取得
        follower_count = profile.followers
        
        return follower_count
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
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
        instagram_login_user = os.environ.get('INSTAGRAM_LOGIN_USER')
        instagram_login_password = os.environ.get('INSTAGRAM_LOGIN_PASSWORD')
        spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        
        # デバッグ情報をログに記録（パスワードは表示しない）
        print(f"対象アカウント: {instagram_username}")
        print(f"ログインアカウント: {instagram_login_user}")
        print(f"スプレッドシートID: {spreadsheet_id}")
        
        # 今日の日付を取得
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        print(f"実行日: {today}")
        
        # フォロワー数を取得
        follower_count = get_follower_count(instagram_username, instagram_login_user, instagram_login_password)
        
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
