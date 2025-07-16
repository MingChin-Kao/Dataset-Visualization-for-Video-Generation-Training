import os
import pandas as pd
import secrets
import re
from flask import Flask, render_template, jsonify, request, send_file, session, Response
from datetime import datetime

secret_key = secrets.token_hex(16)

app = Flask(__name__)
app.secret_key = secret_key

DATA_DIR = '/app/data'

# 全域變數儲存當前選擇的檔案名稱
current_csv_file = 'stage_one.csv'

def extract_scene_num(id_str):
    match = re.search(r'_scene-?(\d+)', id_str)
    return int(match.group(1)) if match else -1

def extract_scene_num(id_str):
    match = re.search(r'_scene-?(\d+)', id_str)
    return int(match.group(1)) if match else -1

# Load the CSV file
def load_video_data(current_csv_file):
    filepath = os.path.join(DATA_DIR, current_csv_file)
    df = pd.read_csv(filepath)

    if 'modifiedTime' not in df.columns:
        print("modifiedTime 欄位不存在，新增並填充為空字串")
        df['modifiedTime'] = ''

    if 'selectedUser' not in df.columns:
        print("selectedUser 欄位不存在，新增並填充為空字串")
        df['selectedUser'] = ''

    # 轉換為 datetime，錯的轉為 NaT
    df['modifiedTime'] = pd.to_datetime(df['modifiedTime'], errors='coerce')

    # 建立排序欄位：NaT 替代成最小時間（為了 groupby 時排到最後）
    df['modifiedTime_sort'] = df['modifiedTime'].fillna(pd.Timestamp.min)

    # 對每個 id 分組後取最後一筆（即 modifiedTime 最晚的）
    df = df.sort_values(by=['id', 'modifiedTime_sort']).groupby('id', as_index=False).tail(1)

    # 刪除排序用欄位
    df.drop(columns=['modifiedTime_sort'], inplace=True)

    # modifiedTime 轉回字串以利 jsonify
    df['modifiedTime'] = df['modifiedTime'].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')

    # 其他欄位
    df['selectedUser'] = df['selectedUser'].fillna('')
    base_clip_path = '/app/data'
    df['web_path'] = df['path'].fillna('').apply(lambda x: x.replace(base_clip_path + '/', ''))
    df['source_video'] = df['id'].apply(lambda x: x.split('_scene')[0])
    # df['aes'] = df['aes'].apply(lambda x: round(x, 2))

    # 其他處理邏輯
    df['modifiedTime'] = pd.to_datetime(df['modifiedTime'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
    df['selectedUser'] = df['selectedUser'].fillna('')

    # 新增 scene_num 欄位
    df['scene_num'] = df['id'].apply(extract_scene_num)

    # 你可以在回傳前排序
    df = df.sort_values(by=['source_video', 'scene_num'])
    print(f"=== Sort Clipe by scen_num {df.head(5)} ===")  # 除錯訊息
    return df

def get_video_by_id(video_id):
    global video_df
    row = video_df[video_df["id"] == video_id]
    if not row.empty:
        return row.iloc[0].to_dict()
    return {}

@app.route('/home')
def index():
    # 從 session 中取得當前選擇的檔案名稱，預設為 'clips_filter.csv'
    current_csv_file = session.get('current_csv_file', 'stage_one.csv')
    session['current_csv_file'] = current_csv_file  # 確保 session 有值

    # 載入資料
    video_df = load_video_data(current_csv_file)
    videos = video_df.to_dict('records')
    return render_template('home.html', videos=videos, current_csv_file=current_csv_file)

@app.route('/')
def user_selection():
    return render_template('user_selection.html')

@app.route('/get_video/<video_id>')
def get_video(video_id):
    current_csv_file = session.get('current_csv_file', 'stage_one.csv')
    video_df = load_video_data(current_csv_file)

    row = video_df[video_df["id"] == video_id]
    if not row.empty:
        return jsonify(row.iloc[0].to_dict())
    return jsonify({})

@app.route('/filter_videos')
def filter_videos():
    query = request.args.get('query', '').lower()
    min_aes = request.args.get('min_aes', type=float)
    
    videos = load_video_data().to_dict('records')
    
    # Filter videos based on query and aesthetic score
    filtered_videos = [
        video for video in videos 
        if (query in video['id'].lower() or 
            query in video['text'].lower()) and
           (min_aes is None or video['aes'] >= min_aes)
    ]
    
    return jsonify(filtered_videos)

@app.route('/video/<path:filename>')
def serve_video(filename):
    # 使用容器內的 /app/data 作為基礎路徑
    video_path = os.path.join('/app/clips', f"{filename}.mp4")
    print(f"=== vidoe path is {video_path} ===")  # 除錯訊息
    if os.path.exists(video_path):
        print(f"Serving video: {video_path}")  # 除錯訊息
        return send_file(video_path, mimetype='video/mp4')
    else:
        print(f"File not found: {video_path}")  # 檔案不存在
        return "Video not found", 404

# @app.route('/update_caption', methods=['POST'])
# def update_caption():
#     current_csv_file = session.get('current_csv_file', 'clips.csv')
#     data = request.get_json()
#     video_id = data.get('id')
#     updated_text = data.get('text')

#     if not video_id or updated_text is None:
#         return "Invalid data", 400

#     # 載入 CSV 檔案
#     filepath = os.path.join(DATA_DIR, current_csv_file)
#     df = pd.read_csv(filepath)

#     # 更新指定影片的 Caption
#     if video_id in df['id'].values:
#         df.loc[df['id'] == video_id, 'text'] = updated_text
#         df.to_csv(filepath, index=False)
#         return "Caption updated successfully", 200
#     else:
#         return "Video ID not found", 404

@app.route('/update_caption', methods=['POST'])
def update_caption():
    current_csv_file = session.get('current_csv_file', 'stage_one.csv')
    data = request.get_json()
    video_id = data.get('id')
    updated_text = data.get('text')
    selected_user = data.get('selectedUser')  # 從請求中取得 selectedUser

    if not video_id or updated_text is None or not selected_user:
        return "Invalid data", 400

    # 載入 CSV 檔案
    filepath = os.path.join(DATA_DIR, current_csv_file)
    df = pd.read_csv(filepath)

    # 確認 video_id 是否存在於原始資料中
    if video_id in df['id'].values:
        # 取得原始資料的第一筆
        original_row = df[df['id'] == video_id].iloc[0].to_dict()

        # 建立新的資料列，保留原始資料並更新 caption、selectedUser 和修改時間
        new_row = original_row.copy()
        new_row['text'] = updated_text
        new_row['selectedUser'] = selected_user  # 新增 selectedUser 欄位
        new_row['modifiedTime'] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')  # 新增修改時間欄位

        # 將新資料列 append 到 DataFrame
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # 儲存回 CSV 檔案
        df.to_csv(filepath, index=False)
        # 回傳新的一筆資料
        return jsonify(new_row), 200
    else:
        return "Video ID not found", 404


@app.route('/update_is_use', methods=['POST'])
def update_is_use():

    current_csv_file = session.get('current_csv_file', 'stage_one.csv')
    data = request.get_json()
    video_id = data.get('id')
    is_use = data.get('is_use')

    if video_id is None or is_use is None:
        return "Invalid data", 400

    # Load the CSV file
    filepath = os.path.join(DATA_DIR, current_csv_file)
    df = pd.read_csv(filepath)

    if video_id in df['id'].values:
        df.loc[df['id'] == video_id, 'is_use'] = is_use
        df.to_csv(os.path.join(DATA_DIR, current_csv_file), index=False)

        return "is_use updated successfully", 200
    else:
        return "Video ID not found", 404


# 取得檔案清單
@app.route('/get_files', methods=['GET'])
def get_files():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    return jsonify(files)

# 根據檔案名稱載入資料
@app.route('/load_file', methods=['GET'])
def load_file():
    filename = request.args.get('filename')
    if not filename or not filename.endswith('.csv'):
        return jsonify({'error': 'Invalid file name'}), 400

    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    # 更新 session 中的檔案名稱
    session['current_csv_file'] = filename

    # 載入 CSV 資料
    # df = pd.read_csv(filepath)

    df = load_video_data(filepath)
    # df['web_path'] = df['path'].clips_filter.csvapply(lambda x: x.replace('/home/mingchin/video_generation/data_pipeline/clips/', ''))
    df['web_path'] = df['path'].apply(lambda x: x.replace('/home/mingchin/video_generation/data_pipeline/clips/', ''))
    df['source_video'] = df['id'].apply(lambda x: x.split('_scene')[0])
    return jsonify(df.to_dict('records'))

if __name__ == '__main__':
    app.run(debug=True)