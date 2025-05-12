import os
import pandas as pd
from flask import Flask, render_template, jsonify, request, send_file

app = Flask(__name__)

DATA_DIR = 'data'

# 全域變數儲存當前選擇的檔案名稱
current_csv_file = 'clips_filter.csv'

# Load the CSV file
def load_video_data():
    # 動態載入當前選擇的 CSV 檔案
    filepath = os.path.join(DATA_DIR, current_csv_file)
    df = pd.read_csv(filepath)

    base_clip_path = '/app/data'
    df['web_path'] = df['path'].apply(lambda x: x.replace(base_clip_path + '/', ''))
    
    # Extract source video name from the 'id' column
    df['source_video'] = df['id'].apply(lambda x: x.split('_scene')[0])
    
    # Format Aesthetic Score to 2 decimal places
    df['aes'] = df['aes'].apply(lambda x: round(x, 2))
    
    return df

@app.route('/')
def index():
    videos = load_video_data().to_dict('records')
    return render_template('index.html', videos=videos)

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
    print("hihi")
    video_path = os.path.join('/app/clips', f"{filename}.mp4")
    print(video_path)  # 除錯訊息
    if os.path.exists(video_path):
        print(f"Serving video: {video_path}")  # 除錯訊息
        return send_file(video_path, mimetype='video/mp4')
    else:
        print(f"File not found: {video_path}")  # 檔案不存在
        return "Video not found", 404

@app.route('/update_caption', methods=['POST'])
def update_caption():
    data = request.get_json()
    video_id = data.get('id')
    updated_text = data.get('text')

    if not video_id or updated_text is None:
        return "Invalid data", 400

    # Load the CSV file
    df = load_video_data()

    # Update the text for the specified video ID
    if video_id in df['id'].values:
        df.loc[df['id'] == video_id, 'text'] = updated_text
        df.to_csv('data/clips_filter.csv', index=False)
        return "Caption updated successfully", 200
    else:
        return "Video ID not found", 404

@app.route('/update_is_use', methods=['POST'])
def update_is_use():
    data = request.get_json()
    video_id = data.get('id')
    is_use = data.get('is_use')

    if video_id is None or is_use is None:
        return "Invalid data", 400

    # Load the CSV file
    df = load_video_data()

    # Update the is_use value for the specified video ID
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
    global current_csv_file  # 使用全域變數
    filename = request.args.get('filename')
    if not filename or not filename.endswith('.csv'):
        return jsonify({'error': 'Invalid file name'}), 400

    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404

    # 更新當前選擇的檔案名稱
    current_csv_file = filename

    # 載入 CSV 資料
    df = pd.read_csv(filepath)
    
    # 確保 web_path 與 /video/<path:filename> 的邏輯一致
    df['web_path'] = df['path'].apply(lambda x: x.replace('/home/mingchin/video_generation/data_pipeline/clips/', ''))
    
    print(df.head())  # 除錯：檢查載入的資料
    return jsonify(df.to_dict('records'))

if __name__ == '__main__':
    app.run(debug=True)