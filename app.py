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
    
    # Convert paths to be web-friendly
    df['web_path'] = df['path'].apply(lambda x: x.replace('/home/mingchin/video_generation/data_pipeline/clips/', ''))
    
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
    videos = load_video_data().to_dict('records')
    video = next((v for v in videos if v['id'] == filename), None)
    
    if video:
        print(f"Serving video: {video['path']}")  # 除錯訊息
        if os.path.exists(video['path']):
            return send_file(video['path'], mimetype='video/mp4')
        else:
            print(f"File not found: {video['path']}")  # 檔案不存在
    else:
        print(f"Video ID not found: {filename}")  # 找不到影片 ID
    
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