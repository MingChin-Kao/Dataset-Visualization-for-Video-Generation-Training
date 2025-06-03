import pandas as pd
import os
import sys
from datetime import datetime

def extract_latest_records(input_csv_path):
    # 讀取原始 CSV
    df = pd.read_csv(input_csv_path)

    # 若欄位不存在就補上
    if 'modifiedTime' not in df.columns:
        df['modifiedTime'] = ''
    if 'selectedUser' not in df.columns:
        df['selectedUser'] = ''

    # 將 modifiedTime 轉為 datetime，錯誤轉為 NaT
    df['modifiedTime'] = pd.to_datetime(df['modifiedTime'], errors='coerce')

    # 輔助欄位：NaT 替代成最小時間（確保未修改的排前面）
    df['modifiedTime_sort'] = df['modifiedTime'].fillna(pd.Timestamp.min)

    # 每個 id 保留最後一筆（最新一筆）
    latest_df = df.sort_values(by=['id', 'modifiedTime_sort']).groupby('id', as_index=False).tail(1)

    # 移除排序用欄位
    latest_df.drop(columns=['modifiedTime_sort'], inplace=True)

    # 產出輸出檔名：原始檔名 + 當天日期
    today_str = datetime.today().strftime('%Y%m%d')
    base_name = os.path.splitext(os.path.basename(input_csv_path))[0]
    output_file = f"{base_name}_latest_{today_str}.csv"

    latest_df.to_csv(output_file, index=False)
    print(f"✅ 已產出最新記錄檔案：{output_file}")
    print(f"✅ 原始筆數：{len(df)}，保留筆數：{len(latest_df)}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("❌ 請提供輸入檔案路徑：\n用法: python extract_latest_records.py <your_csv_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        print(f"❌ 檔案不存在：{input_file}")
        sys.exit(1)

    extract_latest_records(input_file)
