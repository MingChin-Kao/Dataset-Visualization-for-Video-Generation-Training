import pandas as pd

# 定義檔案路徑
clips_filter_path = "./data/clips.csv"
# clips_path = "data/clips.csv"

# 新增 is_use 欄位並儲存
def add_is_use_column(file_path):
    df = pd.read_csv(file_path)
    df['is_use'] = True  # 預設值為 False
    df['aes'] = 0
    df.to_csv(file_path, index=False)
    print(f"Added 'is_use' column to {file_path}")

# 對兩個檔案新增欄位
add_is_use_column(clips_filter_path)
# add_is_use_column(clips_path)