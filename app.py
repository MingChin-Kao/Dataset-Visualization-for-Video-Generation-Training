import os
import pandas as pd
from flask import Flask, render_template, jsonify, request, send_file

app = Flask(__name__)

# Load the CSV file
def load_video_data():
    # Adjust the path to where your CSV is located
    df = pd.read_csv('data/clips.csv')
    
    # Convert paths to be web-friendly
    df['web_path'] = df['path'].apply(lambda x: x.replace('/home/mingchin/video_generation/data_pipeline/clips/', ''))
    
    return df.to_dict('records')

@app.route('/')
def index():
    videos = load_video_data()
    return render_template('index.html', videos=videos)

@app.route('/filter_videos')
def filter_videos():
    query = request.args.get('query', '').lower()
    min_aes = request.args.get('min_aes', type=float)
    
    videos = load_video_data()
    
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
    # Find the full path of the video
    videos = load_video_data()
    video = next((v for v in videos if v['id'] == filename), None)
    
    if video and os.path.exists(video['path']):
        return send_file(video['path'], mimetype='video/mp4')
    else:
        return "Video not found", 404

if __name__ == '__main__':
    app.run(debug=True)