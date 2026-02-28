#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
時間處理模塊，提供統一的時間型態資料處理功能
"""
import numpy as np
import pandas as pd
import datetime as dtC
from datetime import datetime as dt

class DateTimeHandler:
    """
    統一處理時間型態資料的模塊
    
    提供兩種主要功能：
    1. 將時間型態資料轉換為浮點數（用於數據分析和計算）
    2. 將時間型態資料轉換為字符串（用於顯示和序列化）
    """
    
    @staticmethod
    def to_float(x, default=None, **kwags):
        """
        將時間型態資料轉換為浮點數
        
        用途：
        - 數據分析和處理
        - 時間序列計算
        - 特徵工程
        
        參數：
        - x: 要轉換的時間型態資料
        - default: 轉換失敗時的默認值
        - **kwags: 其他參數
        
        返回：
        - float: 轉換後的浮點數
        - default: 轉換失敗時返回默認值
        """
        try:
            # 處理 None 值
            if x is None:
                return default
                
            # 處理 pandas.Timestamp (必須在 datetime.datetime 之前檢查，因為 Timestamp 是 datetime 的子類)
            if isinstance(x, pd.Timestamp):
                # Pandas Timestamp 轉換為 UNIX timestamp
                return x.timestamp()
            
            # 處理 datetime.datetime
            elif isinstance(x, dtC.datetime):
                # datetime 轉換為 UNIX timestamp（以秒為單位）
                return (x - dtC.datetime(1970, 1, 1)).total_seconds()
            
            # 處理 datetime.time
            elif isinstance(x, dtC.time):
                # 時間轉換為秒數
                return x.hour * 3600 + x.minute * 60 + x.second + x.microsecond / 1e6
            
            # 處理 datetime.date
            elif isinstance(x, dtC.date):
                # 日期轉換為 UNIX timestamp（以日期為單位）
                return (x - dtC.date(1970, 1, 1)).days
            
            # 處理 numpy datetime64
            elif isinstance(x, np.datetime64):
                # numpy datetime64 轉換為 UNIX timestamp
                return pd.Timestamp(x).timestamp()
                
            # 處理字符串
            elif isinstance(x, str):
                try:
                    # 擴充更多常見時間格式
                    formats = [
                        # 標準格式
                        '%Y-%m-%d %H:%M:%S',     # 2024-03-19 10:30:00
                        '%Y/%m/%d %H:%M:%S',     # 2024/03/19 10:30:00
                        '%Y-%m-%d',              # 2024-03-19
                        '%Y%m%d',                # 20240319
                        '%H:%M:%S',              # 10:30:00
                        '%Y-%m-%dT%H:%M:%S',     # 2024-03-19T10:30:00 (ISO format)
                        '%Y-%m-%d %H:%M:%S.%f',  # 2024-03-19 10:30:00.123456
                        
                        # 增加更多常見格式
                        '%Y%m%d%H%M%S',          # 20240319103000
                        '%Y%m%d%H%M',            # 202403191030
                        '%Y-%m-%d %H:%M',        # 2024-03-19 10:30
                        '%Y/%m/%d %H:%M',        # 2024/03/19 10:30
                        '%m/%d/%Y %H:%M:%S',     # 03/19/2024 10:30:00
                        '%d/%m/%Y %H:%M:%S',     # 19/03/2024 10:30:00
                        '%Y.%m.%d %H:%M:%S',     # 2024.03.19 10:30:00
                        
                        # 時間格式
                        '%H:%M',                 # 10:30
                        '%H%M%S',                # 103000
                        '%H%M',                  # 1030
                        
                        # 含時區的格式
                        '%Y-%m-%d %H:%M:%S%z',   # 2024-03-19 10:30:00+0800
                        '%Y-%m-%dT%H:%M:%S%z',   # 2024-03-19T10:30:00+0800
                        '%Y-%m-%d %H:%M:%S.%f%z' # 2024-03-19 10:30:00.123456+0800
                    ]
                    
                    for fmt in formats:
                        try:
                            ts = pd.to_datetime(x, format=fmt)
                            
                            # 特殊處理純時間格式
                            if fmt in ['%H:%M:%S', '%H:%M', '%H%M%S', '%H%M']:
                                time_parts = ts.time()
                                return time_parts.hour * 3600 + time_parts.minute * 60 + \
                                    (time_parts.second if hasattr(time_parts, 'second') else 0) + \
                                    (time_parts.microsecond / 1e6 if hasattr(time_parts, 'microsecond') else 0)
                            
                            # 其他格式返回 timestamp
                            return ts.timestamp()
                        except ValueError:
                            continue
                        except Exception as e:
                            print(f'格式 {fmt} 解析失敗: {str(e)}')
                            continue
                    
                    # 在所有格式都失敗後，嘗試一些特殊處理
                    try:
                        # 嘗試移除多餘的字符
                        cleaned_x = ''.join(c for c in x if c.isdigit() or c in ':-/.T ')
                        ts = pd.to_datetime(cleaned_x)
                        return ts.timestamp()
                    except:
                        # 如果還是失敗，記錄詳細資訊
                        print(f'無法解析時間字串: {x}')
                        return default
                        
                except Exception as e2:
                    print(f'時間字串轉換過程發生錯誤: {str(e2)}')
                    return default
            
            # 如果都不是上述類型，嘗試轉換為浮點數
            try:
                return float(x)
            except:
                return default
                
        except Exception as e:
            print(f'時間轉換失敗: {str(e)}')
            return default
    
    @staticmethod
    def to_string(x, default=None, **kwags):
        """
        將時間型態資料轉換為字符串
        
        用途：
        - 顯示和格式化
        - JSON 序列化
        - 日誌記錄
        
        參數：
        - x: 要轉換的時間型態資料
        - default: 轉換失敗時的默認值
        - **kwags: 其他參數
        
        返回：
        - str: 轉換後的字符串
        - default: 轉換失敗時返回默認值
        """
        try:
            # 處理 None 值
            if x is None:
                return default
            
            # 處理 pandas.Timestamp 和 is_datetime64_any_dtype
            if pd.api.types.is_datetime64_any_dtype(type(x)):
                return x.strftime('%Y-%m-%d %H:%M:%S')
                
            # 處理 numpy datetime64
            elif isinstance(x, np.datetime64):
                return pd.Timestamp(x).strftime('%Y-%m-%d %H:%M:%S')
            
            # 處理 datetime.datetime
            elif isinstance(x, dtC.datetime):
                return x.strftime('%Y-%m-%d %H:%M:%S')
            
            # 處理 datetime.date
            elif isinstance(x, dtC.date):
                return x.strftime('%Y-%m-%d')
            
            # 處理 datetime.time
            elif isinstance(x, dtC.time):
                return x.strftime('%H:%M:%S')
            
            # 其他類型轉為字符串
            return str(x)
        
        except Exception as e:
            print(f'時間轉字符串失敗: {str(e)}')
            return default if default is not None else str(x)
    
    @staticmethod
    def to_json_serializable(x, default=None, **kwags):
        """
        將時間型態資料轉換為 JSON 可序列化的格式
        
        用途：
        - JSON 序列化
        - API 回應
        
        參數：
        - x: 要轉換的時間型態資料
        - default: 轉換失敗時的默認值
        - **kwags: 其他參數
        
        返回：
        - 基本類型: 轉換後的 JSON 可序列化類型
        - default: 轉換失敗時返回默認值
        """
        return DateTimeHandler.to_string(x, default, **kwags)

# 為了向後兼容，提供與 dataframeprocedure.py 中相同的函數
def datetime_to_float(x, default=None, **kwags):
    """
    將時間型態資料轉換為浮點數（包裝 DateTimeHandler.to_float）
    
    為了向後兼容，保留此函數
    """
    return DateTimeHandler.to_float(x, default, **kwags)