# -*- coding: utf-8 -*-
"""
Created on Thu Nov  4 11:46:59 2021

@author: ian.ko
"""
import os
import numpy as np
import pyodbc as po
import pandas as pd
import platform as pf
from datetime import datetime as dt
from package import LOGger
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

#%%
m_print = LOGger.addloger(logfile='', max_len=2000)
m_logfile = os.path.join('log', 'log_%t.txt')
m_addlog = LOGger.addloger(logfile=m_logfile, max_len=2000)
def initial(server, db, uid, pwd, cnxn=None, cursor=None, **kwags):
    """Connect to MsSQL"""
    try:
        driver_tag = po.drivers()[0]
        if(cnxn==None):
            cnxn = po.connect('DRIVER=' + driver_tag + ';SERVER=' + server + ';DATABASE=' + db +
                              ';UID=' + uid + ';PWD='+ pwd + ';TDS_Version=7.0;Port=1433' ,charset='utf8')
        if(cursor==None):
            # 創建游標
            cursor = cnxn.cursor()
    except Exception as e:
        LOGger.exception_process(e,logfile=m_logfile)
        LOGger.addlog('stg:\n', str(e)[:500], logfile='')
    return cnxn, cursor

def close_if_neccessary(*args, is_end=True):
    if(is_end):
        for arg in args:
            getattr(arg,'close')() if(hasattr(arg,'close')) else None
    return True

def load_hive_data(sql=None, host_name = "10.1.3.191", port = 10000, 
                   user = "cloudera", password = "cloudera", database="adgroup",
                   **kwags):
    import jaydebeapi
    sql = sql if(sql) else (kwags['AGPConfig'].sql if(
            'AGPConfig' in kwags.keys()) else {}['no SQL'])
    driver='org.apache.hive.jdbc.HiveDriver'
    jarFile =  ["D:/HiveConn/hive-jdbc-1.1.0-cdh5.13.0.jar"
         , "D:/HiveConn/hadoop-common.jar"
         , "D:/HiveConn/libthrift-0.9.3.jar"
         , "D:/HiveConn/hive-service.jar"
         , "D:/HiveConn/httpclient-4.2.5.jar"
         , "D:/HiveConn/httpcore-4.2.5.jar"
         , "D:/HiveConn/hive-jdbc-1.1.0-cdh5.13.0-standalone.jar"]
    # JDBC connection string
    url=("jdbc:hive2://" + host_name + ":" + str(port) + "/"+ database)
    # Connect to Hive
    conn_hive = jaydebeapi.connect(driver, url, [user, password], jarFile)
    curs_hive = conn_hive.cursor()
    curs_hive.execute(sql)
    results_impNG = curs_hive.fetchall()
    curs_hive.close()
    conn_hive.close()
    log = 'Hive data shape:%s'%(str(np.array(results_impNG).shape))
    print(log)
    
    return results_impNG

def load_data(sql = None, serverMes = "10.1.3.17", dbMes = "MES", 
                  uidMes = "mesuser", pwdMes = "mesuser", charset='utf8',
                  **kwags):
    sql = sql if(sql) else (kwags['AGPConfig'].sql if(
            'AGPConfig' in kwags.keys()) else {}['no SQL'])
    serverMes = kwags['AGPConfig'].serverMes if(
            'AGPConfig' in kwags.keys()) else serverMes
    dbMes = kwags['AGPConfig'].dbMes if(
            'AGPConfig' in kwags.keys()) else dbMes
    uidMes = kwags['AGPConfig'].uidMes if(
            'AGPConfig' in kwags.keys()) else uidMes
    pwdMes = kwags['AGPConfig'].pwdMes if(
            'AGPConfig' in kwags.keys()) else pwdMes
    driver_tag = po.drivers()[0]
    cnxn = po.connect('DRIVER=' + driver_tag + ';SERVER=' + serverMes + ';DATABASE=' + dbMes +
                      ';UID=' + uidMes + ';PWD='+ pwdMes + ';TDS_Version=7.0;Port=1433' ,charset='utf8')
    return pd.read_sql(sql, cnxn)

# 寫入DB的功能
def MsSqllog(sql, server, db, uid, pwd, **kwags):
    addlog = LOGger.execute('addlog',kwags,default=LOGger.addloger(logfile=''),not_found_alarm=False)
    """Connect to MsSQL"""
    cnxn = po.connect('DRIVER={SQL Server};SERVER=' + server + 
                          ';DATABASE=' + db +
                          ';UID=' + uid + ';PWD='+ pwd, 
                          charset='utf8')
    
    dt_now = dt.now()
    try:                      
        cursor = cnxn.cursor()
        cursor.execute(sql)
        cnxn.commit()
    except Exception as e:
        LOGger.exception_process(e,logile=m_logfile)
        cnxn.rollback()
        label = ' '.join(['[%s:%s]'%t for t in kwags.items()])
        label = '%s---'%label if(label) else ''
        print('%s執行寫入MsSql發生錯誤!!!'%label + '\n%s'%sql)
        return False
    addlog('寫入DB花費時間:%d(s)'%((dt.now()-dt_now).total_seconds()), level=0)
    return True

# 報告table各欄位的資料型態
def getColumnDatatype(server='10.1.3.17', db='AIS', uid='Ais', pwd='ais@1234', talbeName='AI_AC_Weight', cnxn=None, cursor=None, is_end=True, **kwags):
    cnxn, cursor = initial(server, db, uid, pwd, cnxn=cnxn, cursor=cursor, **kwags)
    sql = f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{talbeName}'"
    headerInfrm = pd.read_sql(sql, cnxn)
    close_if_neccessary(cursor, cnxn, is_end=is_end)
    return headerInfrm

# 報告table的主要index        
def getPrimaryColumns(server = "10.1.3.17", db = "AIS", uid = "Ais", pwd = "ais@1234", talbeName='AI_AC_Weight', charset='utf8', 
                      cnxn=None, cursor=None, is_end=True, **kwags):
    cnxn, cursor = initial(server, db, uid, pwd, cnxn=cnxn, cursor=cursor, **kwags)
    
    # 執行 SQL 查詢以獲取表格的主鍵信息
    sql_query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = '{talbeName}'"
    cursor.execute(sql_query)
    # 獲取結果
    primary_key_columns = [row.COLUMN_NAME for row in cursor]
    close_if_neccessary(cursor, cnxn, is_end=is_end)
    return primary_key_columns

def getTables(server = "10.1.3.17", db = "AIS", uid = "Ais", pwd = "ais@1234", charset='utf8', 
                      cnxn=None, cursor=None, is_end=True, **kwags):
    cnxn, cursor = initial(server, db, uid, pwd, cnxn=cnxn, cursor=cursor, **kwags)
    sql_query = f"SELECT TABLE_NAME \
        FROM INFORMATION_SCHEMA.TABLES \
        WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_CATALOG = '{db}';"
    cursor.execute(sql_query)
    # 獲取結果
    # 取得查詢結果
    rows = cursor.fetchall()
    rows = list([x[0] for x in rows])
    close_if_neccessary(cursor, cnxn, is_end=is_end)
    return rows

def getDbs(server = "10.1.3.17", uid = "Ais", pwd = "ais@1234", charset='utf8', 
                      cnxn=None, cursor=None, is_end=True, **kwags):
    cnxn, cursor = initial(server, 'tempdb', uid, pwd, cnxn=cnxn, cursor=cursor, **kwags)
    sql_query = f"SELECT name FROM sys.databases;"
    cursor.execute(sql_query)
    # 獲取結果
    # 取得查詢結果
    rows = cursor.fetchall()
    rows = list([x[0] for x in rows])
    close_if_neccessary(cursor, cnxn, is_end=is_end)
    return rows

# 一般資料型態到SQL語法中的格式轉換
def parse(x, datatype='int', default='NULL', digit=2):
    if(isinstance(x, type(None)) or LOGger.parse(x).lower().find('nan')>-1 or LOGger.parse(x).lower().find('nat')>-1 or x==''):
        return default
    if(datatype.find('int')>-1):
        try:
            x = '%d'%int(x)
        except:
            x = default
    elif(datatype.find('float')>-1):
        try:
            x = (('%.%df')%digit)%float(x)
        except:
            x = default
    elif(datatype.find('datetime')>-1):
        try:
            x = "'%s'"%(LOGger.parse(x).split('.')[0])
        except:
            x = default
    else:
        x = LOGger.parse(x,digit=digit)
        if(x!='NULL'):
            if(x!=''):
                x = "'"+x if(x[0]!="'") else x
                x = x+"'" if(x[-1]!="'") else x
                x = "''" if(x=="'") else x
            else:
                x = "''"
    return x

def InsertFrameToDB(df, server, db, uid, pwd, talbeName, cnxn=None, cursor=None, order_by=None, **kwags):
    cnxn, cursor = initial(server, db, uid, pwd, cnxn=cnxn, cursor=cursor, **kwags)
    kwags['is_end'] = False
    headerInfrm = getColumnDatatype(server, db, uid, pwd, talbeName=talbeName, cnxn=cnxn, cursor=cursor, **kwags)
    PrimaryColumns = getPrimaryColumns(server, db, uid, pwd, talbeName=talbeName, cnxn=cnxn, cursor=cursor, **kwags)
    
    DB_columns = [x for x in headerInfrm['COLUMN_NAME'].values if not x in PrimaryColumns]
    
    if(isinstance(order_by,str) and order_by in df):   df_sel = df.sort_values(by=order_by)
    for k in DB_columns:
        df_sel[k] = df_sel[k].applymap(
            lambda x:parse(x,headerInfrm[headerInfrm['COLUMN_NAME']==k]['DATA_TYPE'].iloc[0])) if(
                k in df_sel) else np.full(df_sel.shape[0], 'NULL')
    df_sel = df_sel[DB_columns]
    
    df_sel_values = tuple(df_sel.values)
    sql_df_sel_values = ','.join([str(tuple(x)) for x in df_sel_values]).replace(
        "\'",'').replace('"',"'").replace('nan','NULL').replace('None','NULL').strip()
    
    sql_df_sel_keys = '(%s)'%(','.join(DB_columns))
    
    sql_save = f'INSERT INTO {db}.{talbeName} {sql_df_sel_keys} VALUES {sql_df_sel_values}'
    if(not MsSqllog(sql_save, server, db, uid, pwd, **kwags)):
        return False
    close_if_neccessary(cursor, cnxn, is_end=kwags.get('is_end', True))
    return True

def UpdateFrameToDB(df, server, db, uid, pwd, talbeName, cnxn=None, cursor=None, order_by=None, **kwags):
    cnxn, cursor = initial(server, db, uid, pwd, cnxn=cnxn, cursor=cursor, **kwags)
    kwags['is_end'] = False
    headerInfrm = getColumnDatatype(server, db, uid, pwd, talbeName=talbeName, cnxn=cnxn, cursor=cursor, **kwags)
    PrimaryColumns = getPrimaryColumns(server, db, uid, pwd, talbeName=talbeName, cnxn=cnxn, cursor=cursor, **kwags)
    
    DB_columns = [x for x in headerInfrm['COLUMN_NAME'].values if not x in PrimaryColumns]
    
    df_sel = df.copy()
    for k in DB_columns:
        df_sel[k] = df_sel[k].applymap(
            lambda x:parse(x,headerInfrm[headerInfrm['COLUMN_NAME']==k]['DATA_TYPE'].iloc[0])) if(
                k in df_sel) else np.full(df_sel.shape[0], 'NULL')
    df_sel = df_sel[DB_columns]
    
    df_sel_values = tuple(df_sel.values)
    sql_df_sel_values = ','.join([str(tuple(x)) for x in df_sel_values]).replace(
        "\'",'').replace('"',"'").replace('nan','NULL').replace('None','NULL').strip()
    
    sql_df_sel_keys = '(%s)'%(','.join(DB_columns))
    
    sql_save = f'INSERT INTO {db}.{talbeName} {sql_df_sel_keys} VALUES {sql_df_sel_values}'
    if(not MsSqllog(sql_save, server, db, uid, pwd, **kwags)):
        return False
    close_if_neccessary(cursor, cnxn, is_end=kwags.get('is_end', True))
    return True

def create_SQLS_engine(server, db, uid, pwd, pool_size=10, max_overflow=5, pool_timeout=30, pool_recycle=1800, **kwags):
    engine = create_engine(
        f"mssql+pyodbc://{uid}:{pwd}@{server}/{db}?driver=ODBC+Driver+17+for+SQL+Server",
        pool_size=pool_size,        # 最大連線數
        max_overflow=max_overflow,      # 超過 pool_size 時允許額外連線
        pool_timeout=pool_timeout,     # 30 秒內未取得連線則拋錯
        pool_recycle=pool_recycle    # 1800 秒（30 分鐘）後重置連線
    )
    # 設定 Scoped Session（確保多執行緒安全）
    SessionLocal = scoped_session(sessionmaker(bind=engine))
    return engine, SessionLocal

# 執行SQL語法
def execute(sqlsa, sql, ret=None, **kwags):
    try:
        if(not sqlsa.Session):
            m_addlog('no SessionClass!!!', stamps=sqlsa.stamps)
            return False
        dbs = sqlsa.Session()
        result = dbs.execute(sql)
        dbs.commit()
        if (isinstance(ret,dict)):  
            ret['res'] = result.fetchall()
    except Exception as e:
        dbs.rollback()
        LOGger.exception_process(e,logfile=m_logfile)
        m_addlog('sql:%s'%sql, colora=LOGger.FAIL, stamps=['execute'])
        return False
    finally:
        dbs.close()
    return True

# 從.sql檔執行SQL語法
def executeFile(sqlsa, file, encoding=None, ret=None, **kwags):
    sql = sqlsa.getSQLsFromFile(file, encoding=encoding, **kwags)
    for i,sqlCommand in enumerate(sql.split(';')):
        if(sqlCommand.strip()[:6].lower()=='select'):
            print('read %d-th sql:%s...'%(i,sqlCommand[:50]))
            df = readDF(sqlsa, sqlCommand, **kwags)
            if(isinstance(ret, dict)):
                ret['df_%d'%i] = LOGger.dcp(df)
            else:
                print(df)
            if(df is None):
                m_addlog('df is None!!!!', colora=LOGger.FAIL, stamps=['executeFile'])
                return False
        else:
            print('execute %d-th sql:%s...'%(i,sqlCommand[:50]))
            if(not sqlsa.execute(sqlCommand)):
                return False
    return True

# 讀取table內容
def readDF(sqlsa, sql, **kwags):
    try:
        if(not sqlsa.engine):
            m_addlog('no sql engine!!!', stamps=sqlsa.stamps)
            return None
        with sqlsa.engine.connect() as conn:
            df = pd.read_sql(sql, con=conn)
    except Exception as e:
        LOGger.exception_process(e,logfile=m_logfile)
        m_addlog('df is None!!!! sql:%s'%sql, colora=LOGger.FAIL, stamps=['readDF'])
        return None
    return df

#從.sql檔讀取table內容
def readDFfromFile(sqlsa, file, encoding=None, **kwags):
    sql = sqlsa.getSQLsFromFile(file, encoding=encoding, **kwags)
    df = sqlsa.readDF(sql, **kwags)
    return df

#讀取.sql檔中的語法
def getSQLsFromFile(file, encoding=None, **kwags):
    encoding = encoding if(LOGger.isinstance_not_empty(encoding, str)) else LOGger.detect_txt_encoding(file)
    with open(file, "r", encoding=encoding) as file:
        sql_script = file.read()
    return sql_script

def clean_sql_default_value(default_val):
    """
    清理 SQL Server 預設值字串，移除所有引號和括號
    
    參數:
        default_val: 原始預設值（可能是字串、數字或 None）
    
    返回:
        str: 清理後的預設值字串，如果輸入為 None 或空則返回 None
    
    範例:
        '"(0)"' -> '0'
        '('R')' -> 'R'
        '(getdate())' -> 'getdate()'
    """
    if pd.isna(default_val) or not str(default_val).strip():
        return None
    
    default_val_str = str(default_val).strip()
    
    # 循環移除所有引號和括號，直到乾淨為止
    max_iterations = 10  # 防止無限循環
    iteration = 0
    while iteration < max_iterations and default_val_str:
        iteration += 1
        changed = False
        
        # 移除雙引號
        if len(default_val_str) >= 2 and default_val_str.startswith('"') and default_val_str.endswith('"'):
            default_val_str = default_val_str[1:-1].strip()
            changed = True
        
        # 移除單引號
        if len(default_val_str) >= 2 and default_val_str.startswith("'") and default_val_str.endswith("'"):
            default_val_str = default_val_str[1:-1].strip()
            changed = True
        
        # 移除括號
        if len(default_val_str) >= 2 and default_val_str.startswith('(') and default_val_str.endswith(')'):
            default_val_str = default_val_str[1:-1].strip()
            changed = True
        
        # 如果沒有變化，跳出循環
        if not changed:
            break
    
    return default_val_str if default_val_str else None

def safe_to_sql(sqla, df, table_name, primary_keys=None, if_exists='skip_duplicates', 
                index=False, stamps=None, addlog=None, ret=None, use_defaults=True, **kwargs):
    """
    安全的 to_sql 函數，自動處理重複鍵值問題
    
    參數:
        df: pandas DataFrame - 要上傳的資料
        table_name: str - 目標表名
        primary_keys: list - 主鍵欄位列表，None 表示自動檢測
        if_exists: str - 處理模式 ('append', 'replace', 'skip_duplicates')
        index: bool - 是否包含索引
        stamps: list - 日誌標記
        addlog: function - 日誌函數
        use_defaults: bool - 是否使用資料表的預設值替換 NaN（預設 True）
        **kwargs: 其他參數傳遞給 to_sql
    
    返回:
        dict: {'success': bool, 'inserted': int, 'skipped': int, 'message': str, 'primary_keys': list}
    """
    if addlog is None:
        addlog = m_print
    
    stamps = stamps if isinstance(stamps, list) else sqla.stamps
    ret = ret if(isinstance(ret, dict)) else {}
    try:
        if df is None or df.empty:
            ret.update({'success': True, 'inserted': 0, 'skipped': 0, 'message': '沒有資料需要上傳', 'primary_keys': []})
            return False
        
        # 讀取資料表欄位資訊（包含預設值）並替換 NaN
        if use_defaults:
            try:
                retTemp = {}
                sqla.getColumnDatatype(talbeName=table_name, ret=retTemp)
                columnInfo = retTemp.get('columnDataType', pd.DataFrame())
                
                if not columnInfo.empty and 'COLUMN_DEFAULT' in columnInfo.columns:
                    # 建立欄位預設值對應表
                    default_values = {}
                    for idx in columnInfo.index:
                        col_name = columnInfo.loc[idx, 'COLUMN_NAME']
                        default_val = columnInfo.loc[idx, 'COLUMN_DEFAULT']
                        data_type = str(columnInfo.loc[idx, 'DATA_TYPE']).lower() if 'DATA_TYPE' in columnInfo.columns else ''
                        
                        # 處理 SQL Server 預設值格式
                        if pd.notna(default_val) and str(default_val).strip():
                            # 使用 clean_sql_default_value 函數清理預設值字串
                            default_val_str = clean_sql_default_value(default_val)
                            
                            if default_val_str is None:
                                continue
                            
                            # 處理特殊函數（例如: (getdate()), (0) 等）
                            if default_val_str.lower() in ['getdate()', 'getutcdate()', 'sysdatetime()']:
                                # 日期函數由資料庫處理，不加入預設值列表
                                continue
                            elif 'datetime' in data_type or 'date' in data_type or 'time' in data_type:
                                # 日期類型暫時不處理，由資料庫處理
                                continue
                            elif default_val_str:
                                # 嘗試轉換為適當的類型
                                try:
                                    # 根據資料類型轉換
                                    if 'int' in data_type:
                                        default_values[col_name] = int(default_val_str)
                                    elif 'decimal' in data_type or 'float' in data_type or 'real' in data_type or 'numeric' in data_type:
                                        default_values[col_name] = float(default_val_str)
                                    elif 'bit' in data_type:
                                        default_values[col_name] = bool(int(default_val_str))
                                    else:
                                        # 字串類型
                                        default_values[col_name] = default_val_str
                                    
                                    # 記錄成功解析的預設值
                                    addlog(f'欄位 {col_name} ({data_type}): 預設值 "{default_val}" -> {default_values[col_name]} ({type(default_values[col_name]).__name__})', 
                                          stamps=stamps, colora=LOGger.OKBLUE)
                                          
                                except (ValueError, TypeError) as e:
                                    # 如果轉換失敗，記錄錯誤並跳過此欄位
                                    addlog(f'欄位 {col_name} 預設值轉換失敗: "{default_val_str}" -> {str(e)}', 
                                          stamps=stamps, colora=LOGger.WARNING)
                    
                    # 將 DataFrame 中的 NaN 替換為預設值
                    replaced_count = 0
                    for col in df.columns:
                        if col in default_values and df[col].isna().any():
                            nan_count = df[col].isna().sum()
                            df[col] = df[col].fillna(default_values[col])
                            replaced_count += nan_count
                            addlog(f'欄位 {col}: 將 {nan_count} 個 NaN 替換為預設值 {default_values[col]}', 
                                  stamps=stamps, colora=LOGger.OKBLUE)
                    
                    if replaced_count > 0:
                        addlog(f'總共將 {replaced_count} 個 NaN 值替換為資料表預設值', stamps=stamps, colora=LOGger.OKGREEN)
                        
            except Exception as e:
                addlog(f'讀取資料表預設值時發生錯誤: {str(e)}，將使用 NULL', 
                      stamps=stamps, colora=LOGger.WARNING)
        
        # 自動檢測主鍵
        if primary_keys is None:
            retTemp = {}
            sqla.getPrimaryColumns(table_name, ret=retTemp)
            primary_keys = retTemp.get('primaryColumns', [])
            if primary_keys:
                addlog(f'自動檢測到主鍵: {primary_keys}', stamps=stamps, colora=LOGger.OKGREEN)
            else:
                addlog(f'無法檢測到主鍵，將使用普通 {if_exists} or append 模式', stamps=stamps, colora=LOGger.WARNING)
        
        # 如果不是 skip_duplicates 模式，或沒有主鍵，直接使用原始 to_sql
        if not primary_keys:
            if not if_exists in ['skip_duplicates']:
                df.to_sql(table_name, sqla.engine, if_exists=if_exists, index=index, **kwargs)
                ret.update({'success': True, 'inserted': len(df), 'skipped': 0, 
                            'message': f'成功上傳 {len(df)} 筆資料', 'primary_keys': primary_keys or []})
                return False
            else:
                df.to_sql(table_name, sqla.engine, if_exists='append', index=index, **kwargs)
                ret.update({'success': True, 'inserted': len(df), 'skipped': 0, 
                            'message': f'成功上傳 {len(df)} 筆資料', 'primary_keys': primary_keys or []})
                return True
        
        # skip_duplicates 模式：檢查重複鍵值
        # 檢查 DataFrame 是否包含所有主鍵欄位
        missing_keys = [pk for pk in primary_keys if pk not in df.columns]
        if missing_keys:
            ret.update({'success': False, 'inserted': 0, 'skipped': 0, 
                        'message': f"DataFrame 缺少主鍵欄位: {missing_keys}", 'primary_keys': primary_keys or []})
            return False
        
        # 建立主鍵條件查詢
        pk_values = set()
        
        for _, row in df.iterrows():
            pk_tuple = tuple(row[pk] for pk in primary_keys)
            pk_values.add(pk_tuple)
        
        if not pk_values:
            ret.update({'success': True, 'inserted': 0, 'skipped': 0, 'message': '沒有有效的主鍵值', 'primary_keys': primary_keys})
            return False
        
        # 查詢現有的主鍵組合
        pk_conditions_sql = []
        for pk_tuple in pk_values:
            condition_parts = []
            for i, pk_col in enumerate(primary_keys):
                if isinstance(pk_tuple[i], str):
                    # 處理字串中的單引號
                    escaped_value = str(pk_tuple[i]).replace("'", "''")
                    condition_parts.append(f"{pk_col} = '{escaped_value}'")
                elif pk_tuple[i] is None:
                    condition_parts.append(f"{pk_col} IS NULL")
                else:
                    condition_parts.append(f"{pk_col} = {pk_tuple[i]}")
            pk_conditions_sql.append(f"({' AND '.join(condition_parts)})")
        
        existing_keys_sql = f"""
        SELECT {', '.join(primary_keys)} 
        FROM {table_name} 
        WHERE {' OR '.join(pk_conditions_sql)}
        """
        
        # 執行查詢
        existing_keys_df = sqla.readDF(existing_keys_sql)
        
        # 建立現有鍵值的集合
        existing_keys = set()
        if existing_keys_df is not None and not existing_keys_df.empty:
            for _, row in existing_keys_df.iterrows():
                key = tuple(row[pk] for pk in primary_keys)
                existing_keys.add(key)
        
        # 過濾掉重複的資料
        new_data_list = []
        duplicate_count = 0
        
        for _, row in df.iterrows():
            key = tuple(row[pk] for pk in primary_keys)
            if key not in existing_keys:
                new_data_list.append(row)
            else:
                duplicate_count += 1
        
        # 上傳新資料
        if new_data_list:
            new_df = pd.DataFrame(new_data_list)
            new_df.to_sql(table_name, sqla.engine, if_exists='append', index=index, **kwargs)
            
            message = f'成功上傳 {len(new_data_list)} 筆新資料，跳過 {duplicate_count} 筆重複資料'
            addlog(message, stamps=stamps, colora=LOGger.OKGREEN)
            ret.update({'success': True, 'inserted': len(new_data_list), 'skipped': duplicate_count, 
                        'message': message, 'primary_keys': primary_keys})
            return True
        else:
            message = f'所有 {duplicate_count} 筆資料都已存在，跳過上傳'
            addlog(message, stamps=stamps, colora=LOGger.WARNING)
            ret.update({'success': True, 'inserted': 0, 'skipped': duplicate_count, 
                        'message': message, 'primary_keys': primary_keys})
            return True
            
    except Exception as e:
        error_msg = f'安全上傳失敗: {str(e)}'
        addlog(error_msg, stamps=stamps, colora=LOGger.FAIL)
        LOGger.exception_process(e, logfile=m_logfile, stamps=stamps)
        ret.update({'success': False, 'inserted': 0, 'skipped': 0, 'message': error_msg, 'primary_keys': primary_keys or []})
        return False

#%%
#SQL server connection 經理者
class mySQLSAgent:
    engineMap = {}
    sessionMap = {}
    
    def __new__(cls, server, uid, pwd, db='tempdb', pool_size=10, max_overflow=5, pool_timeout=30, pool_recycle=1800, **kwags):
        key = (server, db)
        if not key in cls.engineMap:
            cls.engineMap[key], cls.sessionMap[key] = create_SQLS_engine(server, db, uid, pwd, 
                                                                         pool_size=pool_size, max_overflow=max_overflow, 
                                                                         pool_timeout=pool_timeout, pool_recycle=pool_recycle, **kwags)
            m_print('__new__ engine!!!', stamps=[*key])
        return super().__new__(cls)
    
    def __init__(self, server, uid, pwd, db='tempdb', stamps=None, activateNow=True, pool_size=10, max_overflow=5, pool_timeout=30, pool_recycle=1800, **kwags):
        self.server = server
        self.uid = uid
        self.pwd = pwd
        self.db = db
        
        self.pool_size=pool_size
        self.max_overflow=max_overflow
        self.pool_timeout=pool_timeout
        self.pool_recycle=pool_recycle
        
        self.stamps = stamps if(isinstance(stamps, list)) else []
        self.columnsExplainer = pd.DataFrame()
        
        self.activate()
    
    def activate(self, **kwags):
        """🔹 重新啟動連線（如果 `engine` 已關閉）"""
        key = (self.server, self.db)
        if key not in mySQLSAgent.engineMap:
            m_print(f'🔹 Activating engine for {self.server}/{self.db} (User: {self.uid})')
            mySQLSAgent.engineMap[key], mySQLSAgent.sessionMap[key] = create_SQLS_engine(
                self.server, self.db, self.uid, self.pwd, pool_size=self.pool_size, max_overflow=self.max_overflow, 
                pool_timeout=self.pool_timeout, pool_recycle=self.pool_recycle)
        self.engine = mySQLSAgent.engineMap[key]
        self.Session = mySQLSAgent.sessionMap[key]
        return True
    
    def execute(self, sql, **kwags):
        if(not execute(self, sql, **kwags)):
            return False
        return True
    
    def executeFile(self, file, encoding=None, **kwags):
        if(not executeFile(self, file, encoding=encoding, **kwags)):
            return False
        return True
    
    def readDF(self, sql, **kwags):
        df = readDF(self, sql, **kwags)
        return df
    
    def readDFfromFile(self, file, encoding=None, **kwags):
        df = readDFfromFile(self, file, encoding=encoding, **kwags)
        return df
    
    def getColumnDatatype(self, talbeName, db=None, ret=None, **kwags):
        # server='10.1.3.17', db='AIS', uid='Ais', pwd='ais@1234', talbeName='AI_AC_Weight', 
        kwags['is_end'] = True
        ret = ret if(isinstance(ret, dict)) else {}
        infrmTB = getColumnDatatype(server = self.server, 
                                    db = db if(LOGger.isinstance_not_empty(db, str)) else self.db, 
                                    uid = self.uid, pwd = self.pwd, 
                                    talbeName=talbeName, **kwags)
        ret['columnDataType'] = infrmTB
        m_print(tuple(infrmTB['COLUMN_NAME'].values))
        m_print(str(infrmTB))
        return True
    
    def getPrimaryColumns(self, talbeName, db=None, charset='utf8', ret=None, **kwags):
        kwags['is_end'] = True
        ret = ret if(isinstance(ret, dict)) else {}
        # 執行 SQL 查詢以獲取表格的主鍵信息
        primary_key_columns = getPrimaryColumns(server = self.server, 
                                                db = db if(LOGger.isinstance_not_empty(db, str)) else self.db, 
                                                uid = self.uid, pwd = self.pwd, talbeName=talbeName, 
                                                charset=charset, **kwags)
        ret['primaryColumns'] = primary_key_columns
        m_print(str(primary_key_columns))
        return True
    
    def getTables(self, db='tempdb', ret=None, **kwags):
        kwags['is_end'] = True
        ret = ret if(isinstance(ret, dict)) else {}
        tables =  getTables(server = self.server, 
                  db = db if(LOGger.isinstance_not_empty(db, str)) else self.db, 
                  uid = self.uid, pwd = self.pwd, **kwags)
        ret['tables'] = tables
        m_print(tables)
        return True
    
    def getDbs(self, ret=None, **kwags):
        kwags['is_end'] = True
        ret = ret if(isinstance(ret, dict)) else {}
        dbs =  getDbs(server = self.server, 
                      uid = self.uid, pwd = self.pwd, **kwags)
        ret['dbs'] = dbs
        m_print(dbs)
        return True
        
    def getSQLsFromFile(self, file, encoding=None, **kwags):
        return getSQLsFromFile(file, encoding=encoding, **kwags)

    def safe_to_sql(self, df, table_name, primary_keys=None, if_exists='skip_duplicates', 
                    index=False, stamps=None, addlog=None, ret=None, **kwargs):
        if not safe_to_sql(self, df, table_name, primary_keys=primary_keys, if_exists=if_exists, 
                           index=index, stamps=stamps, addlog=addlog, ret=ret, **kwargs):
            return False
        return True

    def close(self):
        key = (self.server, self.db)
        if(key in mySQLSAgent.engineMap):
            m_print(f'Closing engine for {self.server}/{self.db} (User: {self.uid})')
            mySQLSAgent.engineMap[key].dispose()
            del mySQLSAgent.engineMap[key]
            del mySQLSAgent.sessionMap[key]
        return True