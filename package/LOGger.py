# -*- coding: utf-8 -*-
"""
Created on Thu Jan 21 09:34:26 2021

@author: ian.ko
"""
# import pyodbc
import os
import sys
import traceback
import threading
from datetime import datetime as dt
import datetime as dtC
import time
from datetime import date
from datetime import timedelta as td
import keyboard as kb
import numpy as np
from copy import deepcopy as dcp
import shutil
import pandas as pd
import json
from PIL import ImageFont
import argparse
import smtplib
from email.mime.text import MIMEText
import psutil
import queue
import socket
import chardet as chd
from dateutil import parser as dtp
from colorama import Fore, Style, init
import joblib
# 初始化 colorama
init(autoreset=True)
#%%
m_create_retry_ubd = 1
m_create_rename_if_retry = False
m_dont_print = False
m_path_sep = os.path.join('a','b')[1]
m_input_translation = {' ':'', '-none':None}
m_json_admit_types = [str, int, float, bool, type(None), list, dict, tuple]
log_level_judge = lambda l:l<=0
log_function_judge = lambda f:not f in ['log', 'err', 'warn']
cur_file_dir = os.path.dirname(__file__)
stgtoday = date.today().strftime('%Y%m%d')
# main_logfile = os.path.join(cur_file_dir, 'log','log_%s.txt'%stgtoday) if(cur_file_dir.find('site-package')==-1) else ''
main_logfile = os.path.join('log','log_%s.txt'%stgtoday) if(os.getcwd().find('site-package')==-1) else ''


HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKCYAN = '\033[96m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m' #'\x1b[31m' Fore.RED
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
#%%

ID_record = {}
exits = {}

class myJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        
        # 处理numpy标量
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        # 处理datetime
        elif isinstance(obj, dt):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif callable(getattr(obj, 'tolist', None)):
            return obj.tolist()
        elif(callable(getattr(getattr(obj, 'values', None), 'tolist', None))):
            return {'values': obj.values.tolist(),
                    'columns': getattr(obj, 'columns', None),
                    'index': getattr(obj, 'index', None)}
        elif(hasattr(obj, 'read')):
            return {'filename':getattr(obj,'name','?'), 'mode':getattr(obj,'mode','?')}
        # 处理其他类型
        return super().default(obj)

def add_exit(key=None):
    global exits
    if(key==None):
        dcnlg = len(exits)
        key =  '%d'%dcnlg
    exits[key] = (exits[key] + 1) if(key in exits) else 1

def add_ID_record(ID, mark, memo='', **kwags):
    global ID_record
    ID_record.update({ID:{}}) if(not ID in ID_record) else None
    new_data = dcp(locals())
    new_data.pop('ID')
    for k in new_data:
        ID_record[ID][k] = kwags[k]
        
def CreateContainer(path, maxpathlen=10):
    path = path.replace('<','〈').replace('>','〉')
    stg = str(path)
    if(stg.find('.')>-1):
        stg = os.path.dirname(stg)
        if(stg==''):
            return ''
    if(path.find('\\')==-1 and path.find('/')==-1):
        test = os.path.join('a','b')
        c = test[test.find(os.path.dirname(test))+len(os.path.dirname(test))]
    else:
        c = path[path.find(os.path.dirname(path))+len(os.path.dirname(path))]
    if(stg[-1]==c):
        stg = path[:-1]
    
    pathlist = stg.split(c)
    # print('創建資料夾路徑:%s[最多%d層]'%(stg, maxpathlen)) if(not m_dont_print) else None
    if(not stg[-1]==c):
        stg += c
    container=''
    ii=0
    create_count = 0
    while(stg.find(c,len(c))>-1 and ii < maxpathlen):
        
        container += stg[:stg.find(c,len(c))]
        if not os.path.isdir(container):
            print('create:%s '%container) if(not m_dont_print) else None
            os.mkdir(container)
        stg = stg[stg.find(c,len(c)):]
        create_count += 1
        ii+=1
    if(not len(pathlist)==create_count):
        print('[CreateContainer]審查次數[%d]與路徑層數[%d]'%(create_count, len(pathlist))) if(not m_dont_print) else None
    return container

def CreateFile(path, method, maxpathlen=10, retry_ubd=None, retry_slt_method=np.random.random, rename_if_retry=None):
    stg = str(path).replace('<','〈').replace('>','〉')
    if(stg.find('.')==-1):
        CreateContainer(stg, maxpathlen)
        return stg, ''
    else:
        stg = os.path.dirname(stg)
    if(path.find('\\')==-1 and path.find('/')==-1):
        test = os.path.join('a','b')
        c = test[test.find(os.path.dirname(test))+len(os.path.dirname(test))]
    else:
        c = path[path.find(os.path.dirname(path))+len(os.path.dirname(path))]
    filename = path[(path.rfind(c)+len(c)):]
    CreateContainer(path, maxpathlen)
    
    dirname = os.path.dirname(path)
    fn = '.'.join(os.path.basename(path).split('.')[:-1])
    ext = os.path.basename(path).split('.')[-1]
    retry_ubd = retry_ubd if(retry_ubd!=None) else m_create_retry_ubd
    rename_if_retry = rename_if_retry if(rename_if_retry!=None) else m_create_rename_if_retry
    tried = 0
    while(tried<retry_ubd + 1):
        try:
            if(tried>0):
                sleep_time = float(retry_slt_method())
                time.sleep(sleep_time)
                if(rename_if_retry):    path = dcp(os.path.join(dirname, '%s.%s'%(stamp_process('',[fn,tried],'','','','_RETRY'), ext)))
            method(path)
        except Exception as e:
            exception_process(e,logfile='',stamps=['tried',tried])
        tried += 1
    return stg, filename
#TODO:np_isnan
def np_isnan(x, default=True):
    ret = None
    try:
        ret = np.isnan(x)
    except:
        ret = default
    return ret
#TODO:isiterable
def isiterable(a, exceptions=[str, dict], type_stg_exceptions=[]):
    if(sum([isinstance(a, ecpn)+0 for ecpn in exceptions])>0):
        return False
    if(sum([(str(type(a)).find(ecpn)>-1)+0 for ecpn in type_stg_exceptions])>0):
        return False
    try:
        iter(a)
        return True
    except:
        return False
#TODO:parse
def parse(x, digit=2, stg_max_length=200, be_instinct=False, default_value=None, 
          conjunction=None, max_item_count=10, **kwags):
    try:
        if(isiterable(x)):
            if(hasattr(x, 'shape')):
                return stamp_process('',[type_string(x), str(x.shape)])
            elif(np.array(x).shape[0]<=max_item_count):
                return '%s|%s'%(type_string(x), '`%s`'%stamp_process('',list(map(str, x)),'','','',', '))
            else:
                return stamp_process('',[type_string(x), len(x)])
        elif(isinstance(x, dict)):
            return stamp_process('',[type_string(x), len(x)])
        elif(isnonnumber(x)):
            return str(x)[:stg_max_length]
        else:
            if(be_instinct):
                return int(x) if(float(x)//1==float(x)) else float(('%%.%df'%digit)%float(x))
            else:
                return '%d'%float(x) if(float(x)//1==float(x)) else ('%%.%df'%digit)%float(x)
    except:
        print('parse fail...:%s'%str(x)[:stg_max_length])
        return (x if(be_instinct) else str(x)) if(default_value=='self') else default_value

#TODO:isnonnumber()
def isnonnumber(x, **kwags):
    b = True
    try:
        float(x)
        b = False
    except:
        pass
    return b
#TODO:dearray_process
#method can only pass non-iterable object
def dearray_process(*args, method=None, criterion=None, initial=None, **kwags):
    criterion = criterion if(criterion!=None) else (lambda arg, **kwags:True) 
    ret = [] if(isinstance(initial, type(None))) else initial
    for arg in args:
        if(isiterable(arg)):
            ret += dearray_process(*arg, method=method, **kwags)
        else:
            ret += [method(arg, **kwags) if(method!=None) else arg] if(criterion(arg)) else []
    return ret

#TODO:get_all_values
def get_all_values(*args, only_numbers=0, **kwags):
    criterion=(lambda arg:(str(type(arg)).find('float')>-1)|(str(type(arg)).find('int')>-1)) if(
            only_numbers) else (lambda arg, **kwags:True)
    ret = dearray_process(*args, method=None, criterion=criterion, **kwags)
    ret = (list(set(ret)) if(kwags['uniquify']) else ret) if('uniquify' in kwags) else ret
    return ret 

#TODO:replace_all
def replace_all(stg, old_ch, new_ch):
    return stg.replace(old_ch, new_ch, stg.count(old_ch))

#TODO:path_sep_correcting
def path_sep_correcting(stg):
    path_seq = os.path.join('a','b')[1]
    stg = replace_all(stg, '/', path_seq)
    stg = replace_all(stg, '\\', path_seq)
    return stg

#TODO:mystr
class mystr(str):
    def brackets(self, l, r, strickly=False):
        labels_exist = self.find(l)>-1 and self.find(r)>-1
        if(labels_exist):
            return self[(self.find(l)+len(l)):self.find(r)]
        else:
            return '' if(strickly) else dcp(self)
        
    def set(self, key, value):
        setattr(self, key, value)
    
    def add(self, **kwags):
        for k, v in kwags.items():
            setattr(self, k, v)
        return self
    
    def get(self, key, default_value=None):
        return getattr(self, key, default_value)
    
    def get_behind(self, ch):
        return self[(self.find(ch)+len(ch)):] if(self.find(ch)>-1) else self
    
    def get_front(self, ch):
        return self[:self.find(ch)] if(ch!='' and self.find(ch)>-1) else self
    
    def get_interval(self, ch, start=0, default='self'):
        if(self.count(ch)<2):
            return self if(default=='self') else default
        temp = self[start:]
        temp = temp[(temp.find(ch)+1):]
        temp = temp[:temp.find(ch)]
        return temp
    
    def get_intervals(self, ch, start=0):
        ret = []
        temp = self[start:]
        while(temp.count(ch)>1):
            content = mystr(temp).get_interval(ch)
            ret.append(content)
            temp = temp[(temp.find(content+ch)+len(content+ch)):]
        return ret
    
    def replace_refered_words(self, ch='$', reference={}, default_stg=None, start=0):
        ret = str(self)
        words = self.get_intervals(ch)
        for word in words:
            ret = ret.replace('%s%s%s'%(ch, word, ch), str(reference.get(word, (word if(default_stg==None) else default_stg))), 
                        ret.count('%s%s%s'%(ch, word, ch)))
        return ret
    
    def replace_with_conjunction(self, null_words=[], reference={}, conj='_', new_conj='_'):
        stg = str(self)
        ret_ls = stg.split(conj)
        new_ret_ls = [reference[v] if(v in reference) else v for v in ret_ls if v not in null_words]
        new_stg = new_conj.join(new_ret_ls)
        return new_stg
    
    def replace_all(self, old_ch, new_ch):
        return mystr(self.replace(old_ch, new_ch, self.count(old_ch)))
        
    
    def path_sep_correcting(self):
        path_seq = os.path.join('a','b')[1]
        stg = self.replace_all('/', path_seq)
        return mystr(stg).replace_all('\\', path_seq)
    
    def config_evaluation(self, eva_bck='$', key_bck=':', parse_method=str, replace_self=False, return_stg=True, 
                          preserve_when_except=False, **kwags):
        """
        replace stgs in a particular range to the value of old stg point to, determine in kwags

        Parameters
        ----------
        eva_bck : TYPE, optional
            DESCRIPTION. The default is '$'.
        key_bck : TYPE, optional
            DESCRIPTION. The default is ':'.
        parse_method : TYPE, optional
            DESCRIPTION. The default is str.
        replace_self : TYPE, optional
            DESCRIPTION. The default is False.
        return_stg : TYPE, optional
            DESCRIPTION. The default is True.
        preserve_when_except : TYPE, optional
            DESCRIPTION. The default is False.
        **kwags : TYPE
            DESCRIPTION.

        Returns
        -------
        new_STG : TYPE
            DESCRIPTION.

        """
        new_STG = dcp(self)
        locals().update(kwags)
        stgs = self.get_intervals(eva_bck)
        for stg in stgs:
            try:
                new_stg = parse_method(eval(stg))
            except:
                if(not preserve_when_except):
                    parse_method(eval(stg))
                continue
            new_STG = new_STG.replace_all('%s%s%s'%(eva_bck, stg, eva_bck), new_stg)
        if(replace_self):
            self = new_STG
        if(return_stg):
            return new_STG

    def report(self, loggers=None, methods=None, **kwags):
        try:
            if(isiterable(loggers)):
                for logger in loggers:
                        logger.addlog(self, **kwags)
            if(isiterable(methods)):
                for method in methods:
                    if(callable(method)):
                        method(self, **kwags)
        except Exception as e:
            exception_process(e, logfile='',stamps=[self, 'report'])
        return True

def stripToNumFrom(stg):
    while astype(stg[0], default=None)==None and not stg[0] in ['-','.']:
        stg = stg[1:]
    while astype(stg[-1], default=None)==None and not stg[-1] in ['-','.']:
        stg = stg[:-1]
    return stg

#TODO:mystr2dict
def mystr2dict(mystrobj, admit_key_names=None, admit_value_types=None, **kwags):
    return transform_class2dict(mystrobj, admit_key_names, admit_value_types, **kwags)

#TODO:mystr2dict
def dict2mystr(mystrobj, admit_key_names=None, admit_value_types=None, **kwags):
    return transform_dict2class(mystrobj, admit_key_names, admit_value_types, **kwags)
    
def item_to_object(key, dict_value, deep=True):
    if(not (isinstance(key,str) and isinstance(dict_value, dict))):
        return mystr()
    key = mystr(key)
    for k,v in dict_value.items():
        s = dcp(item_to_object(k, v) if(deep) else v)
        key.set(k, v if(s=='') else s)
    return key
    
#TODO:mylist
class mylist(list):
    def __init__(self, *args, default=None, **kwags):
        super().__init__(*args, **kwags)
        self.default = default
    
    def __getitem__(self, index):
        if isinstance(index, slice):  # 處理切片
            return super().__getitem__(index)
        if(astype(index, d_type=int) is None):
            return self.default
        index = astype(index, d_type=int)
        if(index>=len(self) or index<-len(self)):
            return self.default
        return super().__getitem__(index)
    
    def __add__(self, other):
        if isinstance(other, mylist) or isinstance(other, list):
            return mylist(super().__add__(other))
        return NotImplemented
    
    def set(self, new_obj, index=None, immunity_case=[''], start_index=0, direction=1):
        if(index!=None):
            self.pop(index)
            self.insert(index, new_obj)
        else:
            if(direction>=0):
                index=int(start_index)
                while(index<len(self)):
                    a_dir = self[index]
                    if(not a_dir in immunity_case):
                        self.set(new_obj, index)
                        break
                    index += 1
            else:
                self.reverse()
                self.set(new_obj, index=index, immunity_case=immunity_case, 
                                     start_index=start_index, direction=1)
                self.reverse()
    def map(self, method, max_iter=20000):
        n_iter = 0
        for i, v in enumerate(self):
            if(n_iter>max_iter):
                break
            self.set(method(v, i=i), index=i)
            n_iter += 1
    
    def find(self, thing, default=None, strictly=False):
        if(strictly):
            return self.index(thing) if(thing in self) else default
        else:
            if(isinstance(thing, str)):
                #尋找list裡面有沒有包含thing這個字串的元素?? strictly就是index()
                stg_index = -1
                for i, v in enumerate(self):
                    stg_index = v.find(thing)
                    if(not stg_index in [-1]):
                        break
                return (i, *get_all_values(stg_index)) if(not stg_index in [-1]) else -1
            else:
                return self.index(thing) if(thing in self) else default
        
    def find_strictly(self, thing):
        if(isinstance(thing, 'str')):
            #尋找list裡面有沒有包含thing這個字串的元素??
            stg_index = -1
            for i, v in enumerate(self):
                stg_index = v.find(thing)
                if(not stg_index in [-1]):
                    break
            return (i, *get_all_values(stg_index)) if(not stg_index in [-1]) else -1
        else:
            return self.index(thing)
        
    def index_default(self, thing, default=-1):
        return self.index(thing) if(thing in self) else default
    
    def get(self, index=None, default_value=None, inherit=False):
        if(index==None):
            return self if(len(self)>1) else self[0]
        elif(str(type(index)).find('int')>-1):
            if(index<len(self) and index>=-len(self)):
                return self[index]
            elif(inherit and len(self)>0):
                return '%s_%d'%(self[0], index)
        return default_value
    
    def get_all(self, *args, only_numbers=1, **kwags):
        return mylist(get_all_values(self, *args, only_numbers=1, **kwags))
    
    def concatenate(self, *args, only_numbers=1, **kwags):
        return self.get_all(*args, only_numbers=only_numbers, **kwags)
    
    def get_in_axis(self, *args, axis=1, only_numbers=0, dtype=list, **kwags):
        return mylist(get_in_axis(self, *args, axis=axis, only_numbers=only_numbers, dtype=dtype, **kwags))
    
    def replace(self, old_stg, new_stg, max_iter=20000, max_iter_in_stg=20000, strictly=False, export=False):
        return self.replace_strictly(old_stg, new_stg, export=export) if(strictly
            ) else self.replace_generously(old_stg, new_stg, max_iter_in_stg=max_iter_in_stg, export=export)
    
    def replace_generously(self, key_stg, new_stg, max_iter=20000, max_iter_in_stg=20000, export=False):
        method = lambda s, **kwags:s.replace(key_stg, new_stg, max_iter_in_stg)
        if(export):
            self_ = dcp(self)
            self_.map(method, max_iter=max_iter)
            return self_
        else:
            self.map(method, max_iter=max_iter)
            return None
        
    def replace_strictly(self, old_stg, new_stg, max_iter=20000, export=False):
        method = lambda s, **kwags: new_stg if(s==old_stg) else s
        if(export):
            self_ = dcp(self)
            self_.map(method, max_iter=max_iter)
            return self_
        else:
            self.map(method, max_iter=max_iter)
            return None

class myCycle(mylist):
    def __getitem__(self, index):
        if isinstance(index, slice):  # 處理切片
            start, stop, step = index.start, index.stop, index.step or 1
            
            # 計算原始索引範圍，不做 `len(self)` 限制
            if start is None:
                start = 0
            if stop is None:
                stop = len(self)

            # 生成索引範圍
            indices = list(range(start, stop, step))
            # 生成循環索引
            result = myCycle([self[i % len(self)] for i in indices])
            return result
        if(len(self)==0):
            return self.default
        index = index % len(self)
        return super().__getitem__(index)

#TODO:mylisting
def mylisting(*args, criterion=None, ret=mylist(), **kwags):
    criterion = criterion if(criterion!=None) else (lambda arg, **kwags:True) 
    for arg in args: #for 1, [1] in args
        if(isiterable(arg)):
            new_arg = mylist()
            mylisting(*arg, criterion=criterion, ret=new_arg, **kwags)
            ret.append(new_arg)
        else:
            ret.append(arg)

#TODO:flattern_list
def flattern_list(ls):
    if(hasattr(ls,'concatenate')):
        return ls.concatenate()
    elif(hasattr(ls,'get_all')):
        return ls.get_all()
    else:
        return ls
    
def parse_or_eval(x, eval_keyword='_', eval_to=None, eval_method=lambda x:eval(x)):
    if(isinstance(eval_keyword, str)):
        return parse(x) if(x!=eval_keyword) else (eval_method(x) if(eval_method) else eval_to)
    else:
        try:
            ret = eval_method(x) if(eval_method) else eval_to
        except:
            ret = eval_to
        return ret

def parse_or_None(x):
    return parse_or_eval(x, eval_keyword='_', eval_to=None, eval_method=None)
    
#TODO:get_in_axis
def get_in_axis(*args, axis=1, only_numbers=0, tomylist=True, **kwags):
    all_values = get_all_values(*args, only_numbers=only_numbers, **kwags)
    array_dtype_np = np.array(all_values).reshape(-1, 1) if(axis==1) else np.array(all_values).reshape(1, -1)
    if(tomylist):
        ret = mylist()
        mylisting(*array_dtype_np, ret=ret)
        return ret
    return array_dtype_np
#TODO:get_classbasename
def get_classbasename(obj):
    if(isinstance(obj, str)):
        return obj
    str_type_self = str(type(obj))
    stg = dcp(str_type_self)
    if(stg.lower().find('keras')>-1):
        return 'MLPmodel'
    if(stg.find("<")>-1 and stg.find(">")>stg.find("<")):
        stg = stg[(stg.find("<")+1):stg.rfind(">")]
    if(stg.count("'")>1):
        stg = stg[(stg.find("'"))+1:stg.rfind("'")]
#        stg.replace('modeling.', '')
    stg = stg.split('.')[-1]
    return stg

#TODO:set_dir
def set_dir(new_dir, source_path, index=None, immunity_case=[''], direction=1, sep = os.path.join('a','b')[1], start_index=0):
    source_path_destructure = mylist(source_path.split(sep))
    source_path_destructure.set(new_dir, index=index, immunity_case=immunity_case, start_index=start_index, direction=direction)
    return sep.join(source_path_destructure)

#TODO:abspath
def abspath(path, abs_root=None, for_excel=False, sep=None):
    sep = os.path.join('a','b')[1] if(sep==None) else sep
    abs_source = os.path.abspath(path)
    if(abs_root!=None):
        abs_source = set_dir(abs_root, abs_source)
    abs_source = (sep + abs_source) if(for_excel) else abs_source #excel絕對路徑超連結的格式需要在最前面多個sep
    return abs_source
#TODO:for_file_process
def for_file_process(stamps):
    if(isinstance(stamps, list)):
        stamps = list(map(lambda s:s.replace('<','〈').replace('>','〉'), stamps))
    elif(isinstance(stamps, dict)):
        stamps = {k.replace('<','〈').replace('>','〉'):v.replace('<','〈').replace('>','〉') for (k,v) in stamps.items()}
    elif(isinstance(stamps, str)):
        stamps = mystr(stamps).replace_all('<','〈').replace_all('>','〉')
    return stamps
#TODO:type_string
def type_string(obj, index=-1, sep='.'):
    a_type = mystr(type(obj))
    a_type1 = a_type.brackets("<class '", "'>")
    return str(a_type1.split(sep)[index] if(index!=None) else a_type1)
    

#TODO:strictly_list
def strictly_list(obj, ismy=True):
    form1 = [obj] if(isinstance(obj, str)) else list(obj)
    if(ismy):
        ret=mylist()
        mylisting(*form1, ret=ret)
        return ret
    return form1

#TODO:stamp_process
def stamp_process(stg='', stamps=[], stamp_sep=':', stamp_left='[', stamp_right=']', 
                  adjoint_sep='', outer_stamp_left='', outer_stamp_right='', location=1, 
                  exceptions = [''], annih_when_stamps_empty=True, for_file=False, max_len=200, digit=2, **kwags):
    stamp = ''
    if(isinstance(stamps, dict)):
        stamp = adjoint_sep.join(list(map(lambda t:('%s%s%s%s%s'%(stamp_left,
                parse(t[0], stg_max_length=200, digit=digit), stamp_sep, parse(
                    t[1], stg_max_length=max_len, digit=digit), stamp_right) if(t[1]!='') else ''), tuple(stamps.items()))))
    elif((stamps!='') if(isinstance(stamps, str)) else False):
        stamp = '%s%s%s'%(stamp_left, stamps, stamp_right)
    elif((np.array(stamps).shape[0]>0) if(len(np.array(stamps).shape)>0) else False):
        stamps = [v for v in stamps if (not v in [''] if(isinstance(v, str)) else True)]
        stamp = adjoint_sep.join(list(map(lambda s:('%s%s%s'%(stamp_left, parse(s, stg_max_length=max_len, digit=digit), stamp_right)), stamps)))
    if(annih_when_stamps_empty and stamp==''):
        return ''
    stamp = outer_stamp_left + stamp + outer_stamp_right if(stamp!='') else ''
    stg = (stamp + stg if(location>0) else stg + stamp) if(location!=0) else stg
    stg = for_file_process(stg) if(for_file) else stg
    return stg

#TODO:addlog
ALIGN_CENTER = 0
ALIGN_LEFT = -1
ALIGN_RIGHT = 1
def addlog(*log, max_len=None, level=1, function='log', stamps=None, click=None, click_anchor=None, click_stamp=None,
           log_counter=None, log_counter_stamp=None, log_counter_stamps=None, log_counter_ubd=5, log_counter_ubds={}, 
           reset_log_counter=False, reset_log_counter_value=0, log_when_unreset=False, colora='', encoding='utf-8',
           error_counter=None, max_logfile_error=10, dont_print=False, parse_digit=2, adjoint_sep=' ', handler=None, 
           fill_char=' ', fill_width=None, align=ALIGN_CENTER, **kwags):
    if(log_level_judge(level)):
        return
    if(log_function_judge(function)):
        return
    log = [parse(lg, parse_digit, stg_max_length=max_len) for lg in log if ((lg!='' and lg!='\n') if(isinstance(lg, str)) else True)]
    log_rawstg = stamp_process('',list(map(lambda x:x, log)) ,'' ,'' ,'' ,adjoint_sep, max_len=max_len)
    # 處理填充和對齊
    if fill_width is not None and isinstance(log_rawstg, str):
        if align == ALIGN_CENTER:
            log_rawstg = log_rawstg.center(fill_width, fill_char)
        elif align < 0:
            log_rawstg = log_rawstg.ljust(fill_width, fill_char)
        elif align > 0:
            log_rawstg = log_rawstg.rjust(fill_width, fill_char)
    stamps = stamps if(isinstance(stamps, list) or isinstance(stamps, dict)) else []
    kwags['annih_when_stamps_empty'] = kwags.get('annih_when_stamps_empty', False)
    log = stamp_process(log_rawstg, stamps=stamps, max_len=max_len, **kwags)
    if(log):
        if(log_when_unreset and isinstance(log_counter, dict)):
            if(isinstance(log_counter_stamps, (list, dict))):
                for lc_stamp in log_counter_stamps:
                    if(log_counter.get(lc_stamp, reset_log_counter_value)==reset_log_counter_value):
                        return
            if(log_counter.get(log_counter_stamp, reset_log_counter_value)==reset_log_counter_value):
                return
        if(not reset_log_counter and isinstance(log_counter_ubds, dict) and isinstance(log_counter, dict)):
            if(isinstance(log_counter_stamps, (list, dict))):
                for lc_stamp in log_counter_stamps:
                    ubd = log_counter_ubds.get(lc_stamp, log_counter_ubd)
                    if(log_counter.get(lc_stamp, 0)>ubd):
                        return
            ubd = log_counter_ubds.get(log_counter_stamp, log_counter_ubd)
            if(log_counter.get(log_counter_stamp, 0)>ubd):
                return
        display_max_columns_single = kwags.get('display_max_columns_single', '')
        display_max_rows_single = kwags.get('display_max_rows_single', '')
        if(display_max_columns_single!=''):
            pd.set_option('display.max_columns', display_max_columns_single)
        if(display_max_rows_single!=''):
            pd.set_option('display.max_rows', display_max_rows_single)
        if('longstgs' in kwags):
            longstgs = kwags['longstgs']
            longstgs = {s:200 for s in longstgs} if(type(longstgs)!=dict) else longstgs
            stgs_count = len(longstgs)
            format_count = log.count('%s')
            log = log%(*tuple([s[:longstgs[s]] for s in longstgs][:format_count]), 
                       *tuple(['%s']*(format_count - stgs_count)))
        #計時
        log = log[:max_len] if(isinstance(max_len, int)) else log
        dt_format = kwags.get('total_sec_digit', '%.2f(s)')
        if(isinstance(click, dict)):
            log_click = dcp(log)
            click_stamp = click_stamp if(isinstance(click_stamp, str)) else log_counter_stamp
            click_copy = click.copy()
            for k,v in click_copy.items():
                if(not isinstance(v, dt)):
                    continue
                dt_stg = '....%s費時%s'%(('[stamp:%s]'%k if(k!='') else ''), dt_format%((dt.now()-v).total_seconds()))
                log_click += dt_stg
                click[k] = dt.now()
            click.update({click_stamp:dt.now()}) if(not click_stamp in click) else None
        if(isinstance(click_anchor, dict)):
            log_click = dcp(log if(not isinstance(click, dict)) else log_click)
            click_stamp = click_stamp if(isinstance(click_stamp, str)) else log_counter_stamp
            for k,v in click_anchor.items():
                if(not isinstance(v, dt)):
                    continue
                dt_stg = '....%s費時%s'%(('[stamp:%s]'%k if(k!='') else ''), dt_format%((dt.now()-v).total_seconds()))
                log_click += dt_stg
            click_anchor.update({click_stamp:dt.now()}) if(not click_stamp in click_anchor) else None
        dont_print = dont_print if(isinstance(dont_print, bool)) else m_dont_print
        #存儲
        logfile = kwags.get('logfile', main_logfile)
        logOutput = dcp(log_click if(isinstance(click, dict) or isinstance(click_anchor, dict)) else log)
        print(colora + logOutput) if(not dont_print and logfile!=None and not isinstance(handler, str)) else None
        if(isinstance(handler, str)):
            setattr(handler, 'msgs', getattr(handler,'msgs',[]) + [logOutput])
        if(isinstance(log_counter, dict)):
            for log_counter_stamp_i in ((log_counter_stamps if(isinstance(log_counter_stamps, list)) else [])+[log_counter_stamp]):
                log_counter[log_counter_stamp_i] = log_counter.get(log_counter_stamp_i, 0) + 1
        if(isinstance_not_empty(logfile, str)):
            logfile = (logfile.replace('%t','%s'))%dt.now().strftime('%Y%m%d') if(
                                                logfile.find('%t')>-1) else logfile
            log_among_time = dcp(log_click if('click' in kwags or 'click_anchor' in kwags) else log)
            stg_now = dt.now().strftime('%Y-%m-%d %H:%M:%S\t')
            log_among_time = (stg_now + log_among_time + '\n') if (
                not log_among_time[-1]=='\n' if(len(log_among_time)>0) else True) else log_among_time
            try:
                error_counter = error_counter if(isinstance(error_counter, dict)) else {}
                with open(logfile ,'a', encoding=encoding) as f:
    	            f.write(log_among_time)
                error_counter.update({'logfile':0}) if('logfile' in error_counter) else None
            except:
                if(error_counter.get('logfile',0) < max_logfile_error):
                    print(colora + '[%d]logfile_error:%s.......'%(error_counter.get('logfile',0)+1, logfile))
                    error_counter['logfile'] = error_counter.get('logfile', 0) + 1
        if('display_max_columns_single' in kwags):
            pd.set_option('display.max_columns', 0)
        if('display_max_rows_single' in kwags):
            pd.set_option('display.max_rows', 0)
        if('abort_infrm' in kwags):
            abort_infrm = kwags['abort_infrm']
            i = len(abort_infrm)
            if(isinstance(stamps, dict)):
                abort_infrm[i] = dcp(stamps)
            elif(isiterable(stamps)):
                keys_dict = {i:stamps[i] for i in range(len(stamps))}
                abort_infrm[i] = {'key%d'%t[0]:'%s'%t[1] for t in keys_dict.items()}
            else:
                stamps = [stamps]
                keys_dict = {i:stamps[i] for i in range(len(stamps))}
                abort_infrm[i] = {'key%d'%t[0]:'%s'%t[1] for t in keys_dict.items()}
            abort_infrm[i]['msg'] = log_rawstg[:100]
    if(reset_log_counter and isinstance(log_counter, dict)):
        if(isinstance(log_counter_stamps, dict)):
            for k in log_counter_stamps: 
                log_counter.update({k:reset_log_counter_value}) if(k in log_counter and k!=None) else None
        else:
            if(log_counter_stamp==None):
                for k in log_counter: log_counter[k] = reset_log_counter_value
            else:
                log_counter.update({log_counter_stamp:reset_log_counter_value}) if(log_counter_stamp in log_counter) else None
        return

def addloger(**kwags):
    return lambda *s,**kws:addlog(*s,**kwags,**kws)

def addDebug(*logs, logfile='', **kwags):
    kwags['colora'] = '\033[93m'
    return addlog(*logs, logfile=logfile, **kwags)

def gatelog(stop_criterion, log_counter, log_counter_stamp, 
            stop_message=None, pass_message=None, delay_timeout=None, log_when_unreset=True, **kwags):
    addlog_ = kwags.get('addlog', addloger(logfile=kwags.get('logfile','')))
    log_counter = log_counter if(isinstance(log_counter, dict)) else {}
    lcv = dcp({k:v for k,v in locals().items() if not k in [gatelog.__name__, 'kwags']})
    lcv.update(kwags)
    if(not isinstance(delay_timeout, type(None))):
        ta = dt.now()
        lcv.update({'ta':ta})
        while((dt.now() - ta).total_seconds()<delay_timeout):
            if(not stop_criterion(**lcv)):
                break
    if(stop_criterion(**lcv)):
        stop_message = stop_message if(isinstance(stop_message, str)) else '%s failed'%log_counter_stamp
        addlog_(stop_message, log_counter=log_counter, log_counter_stamp=log_counter_stamp)
        return False
    pass_message = pass_message if(isinstance(pass_message, str)) else '%s pass'%log_counter_stamp
    addlog_(pass_message, log_counter=log_counter, log_counter_stamp=log_counter_stamp, 
            reset_log_counter=True, log_when_unreset=log_when_unreset)
    return True



def is_timestamp(data):
    try:
        pd.to_datetime(data)
        if(not np.array(tuple(map(lambda s:np.log10(s)>=10, data))).any()):
            return False
        return True
    except ValueError:
        return False

#show_vector
def show_vector(v, conjuction=':', max_show_count=20, is_end=True, **kwags):
    show_vector_addlog = kwags.get('addlog', addlog)
    V = flattern_list(mylist(tuple(v)).get_all())
    V_stg = ','.join(list(map(parse, V[:max_show_count])))
    V_stg = 'shape:%s'%(str(np.array(v).shape)) + conjuction + V_stg
    if(is_end):
        show_vector_addlog(V_stg, **kwags)
    else:
        return V_stg

#export_counter
def export_counter(ls):
    return dict(zip(*np.unique(ls, return_counts=1)))

#TODO:extract
def extract(container, index=0, key='', default=None, default_method=None, _type=None, **kwags):
    addlog_ = kwags.get('addlog', addloger(logfile=kwags.get('logfile',None)))
    try:
        if(isiterable(container)):
            shape = np.array(container).shape
            addlog_('[extract][index:%s][container shape:%s]'%(str(index)[:200], shape), 
                    level=kwags.get('level',5), **kwags)
            ret = np.array(container[np.array(index)]) if(isiterable(index)) else (
                    container[index] if(index<shape[0] or -index<=shape[0]) else default)
            return ret if(isinstance(ret, _type) if(isinstance(_type, type)) else True) else default
        elif(isinstance(container, dict)):
            addlog_('[extract][key:%s][container length:%d]'%(key, len(container)), 
                    level=kwags.get('level',5), **kwags)
            ret = container.get(key, default)
            return ret if(isinstance(ret, _type) if(isinstance(_type, type)) else True) else default
    except:
        pass
    if(default_method!=None):
        default = default_method(container, **kwags)
    return default

#TODO:extract_or_self
def extract_or_self(container, index=0, key='', default=None, default_method=None, _type=None, **kwags):
    default = default if(not isinstance(container, _type) if(isinstance(_type, type)) else False) else container
    return extract(container, index=index, key=key, default=default, default_method=default_method, **kwags)

def extract_or_self_intype(container, _type, index=0, key='', default=None, default_method=None, **kwags):
    ret = extract(container, index=index, key=key, default=container, **kwags)
    return ret if(isinstance(ret, _type)) else default

def exception_process(e, logfile=os.path.join('log_%t.txt'), stamps=None, max_len_stack=200, handler=None, colora=FAIL, **kwags):
    stamps = stamps if(isinstance(stamps, list)) else []
    exc_type, exc_obj, ex_stack = sys.exc_info()
    ex_stamps = {'lineno':'%d'%e.__traceback__.tb_lineno,
                 'name':'%s'%e.__traceback__.tb_frame.f_code.co_name,
                 'type':'%s'%exc_type}
    msg = '[ERROR]%s\n%s%s\n%s'%(e.__traceback__.tb_frame.f_code.co_filename,
        stamp_process('',ex_stamps), stamp_process('', stamps), '錯誤訊息:\n%s\n'%str(e))
    None if(isinstance(handler,mystr)) else addlog('--------------------------------------------------', logfile=logfile, colora=colora)
    traceback_things = traceback.extract_tb(ex_stack)
    for stack in traceback.extract_tb(ex_stack):
        addlog(str(stack)[:max_len_stack], logfile=logfile, handler=handler, colora=colora, **kwags)
    None if(isinstance(handler,mystr)) else addlog('--------------------------------------------------', logfile=logfile, colora=colora)
    kwags.update({'annih_when_stamps_empty':False})
    addlog(msg, logfile=logfile, handler=handler, colora=colora, **kwags)
    if(isinstance(kwags.get('messenger'), Messenger) and isinstance_not_empty(kwags.get('recipient'), str)):
        messenger = kwags.get('messenger')
        recipient = kwags.get('recipient')
        body = execute('body', recipient, kwags, default='', not_found_alarm=False)
        body = stamp_process('',[msg, body]+list(map(lambda s:str(s)[:200], traceback_things)),'','','','\n')
        try:
            messenger.send_email(recipient=recipient, body=body, 
                             subject=execute('subject', recipient, kwags, 
                                             default=stamp_process('',[os.path.basename(os.getcwd()), exc_type],'','','','||'), 
                                             not_found_alarm=False))
        except Exception as e2:
            exception_process(e2, logfile=logfile, stamps=stamps, handler=handler, **kwags)
    
def copyfile(source, destination, non_file_non_dir_answer=False):
    """
    複製檔案。如果目標檔案非檔案也非資料夾，要回復第3參數

    Parameters
    ----------
    source : TYPE
        DESCRIPTION.
    destination : TYPE
        DESCRIPTION.
    non_file_non_dir_answer : TYPE, optional
        DESCRIPTION. The default is False.

    Returns
    -------
    TYPE
        DESCRIPTION.

    """
    try:
        if(source=='' or destination==''):
            return False
        if(not os.path.exists(source)):
            print('來源檔案不存在:%s'%source)
            return False
        if(os.path.isfile(source)):
            if(os.path.isdir(destination) if(os.path.exists(destination)) else False):
                destination = os.path.join(destination, os.path.basename(source))
            shutil.copyfile(source, destination)
        elif(os.path.isdir(source)):
            shutil.copytree(source, destination)
        else:
            print('非檔案也非資料夾:%s'%source)
            return non_file_non_dir_answer
    except Exception as e:
        exception_process(e, stamps=['copyfile'])
        return False
    return True

#TODO:removefile
def removefile(path, non_file_non_dir_answer=False):
    try:
        if(path==''):
            return False
        if(not os.path.exists(path)):
            print('欲刪除的檔案不存在:%s'%path)
            return False
        if(os.path.isfile(path)):
            os.remove(path)
        elif(os.path.isdir(path)):
            shutil.rmtree(path)
        else:
            print('欲刪除的非檔案也非資料夾:%s'%path)
            return non_file_non_dir_answer
    except Exception as e:
        exception_process(e, stamps=['removefile'])
        return False
    return True

def removefile_in_region(target, period_seconds=24*60*60, is_target_selfdelete=False, target_extfiletype=None, **kwags):
    addlog_ = execute('addlog', kwags, default=addloger(logfile=''), not_found_alarm=False)
    addlog_('remove target region:%s'%target)
    if(not isinstance_not_empty(target, str)):
        pass
    if(not os.path.exists(target)):
        pass
    elif(os.path.isdir(target)):
        if(is_target_selfdelete):
            timestamp = os.path.getmtime(target)
            modify_time = dt.fromtimestamp(timestamp)
            if((dt.now() - modify_time).total_seconds() <= period_seconds):
                return True
            addlog_('is_target_selfdelete remove %s'%target)
            removefile(target)
        else:
            allfiles, alldfolders = explore_folder(target)
            alldfolders = sorted([v for v in alldfolders if v!=target], key=lambda x:len(x.split(m_path_sep)),reverse=True)
            for file in allfiles:
                if(isinstance(target_extfiletype, list)):
                    extfiletype = file[file.rfind('.')+1:]
                    if(not extfiletype in target_extfiletype):
                        continue
                if(not os.path.exists(file)):
                    continue
                timestamp = os.path.getmtime(file)
                modify_time = dt.fromtimestamp(timestamp)
                if((dt.now() - modify_time).total_seconds() <= period_seconds):
                    continue
                addlog_('remove %s'%file)
                removefile(file)
            for folder in alldfolders:
                allfiles, alldfolders = explore_folder(folder)
                if(len(allfiles)>0):
                    continue
                if(not os.path.exists(folder)):
                    continue
                timestamp = os.path.getmtime(folder)
                modify_time = dt.fromtimestamp(timestamp)
                if((dt.now() - modify_time).total_seconds() <= period_seconds):
                    continue
                addlog_('remove %s'%folder)
                removefile(folder)
    elif(os.path.isfile(target)):
        if(isinstance(target_extfiletype, list)):
            extfiletype = target[target.rfind('.')+1:]
            if(not extfiletype in target_extfiletype):
                return True
        if(not os.path.exists(file)):
            return True
        timestamp = os.path.getmtime(target)
        modify_time = dt.fromtimestamp(timestamp)
        if((dt.now() - modify_time).total_seconds() <= period_seconds):
            return True
        addlog_('remove %s'%target)
        removefile(target)
    return True

def constructOutputDiretory(handler):
    if(getattr(handler, 'rewrite', False)):
        shutil.rmtree(handler.exp_fd) if(os.path.isdir(handler.exp_fd) and handler.exp_fd!='.') else None
    if(not os.path.isdir(handler.exp_fd)):
        CreateContainer(handler.exp_fd)
    return True

def checkConfigAvailable(config_file):
    if(not isinstance_not_empty(config_file, str)):
        print("config_file err: %s"%config_file)
        return False
    if(not os.path.exists(config_file)):
        print("config_file doesn't exists: %s"%config_file)
        return False
    return True

def configFromFile(config_file):
    if(not checkConfigAvailable(config_file)):
        return {}
    config = load_json(config_file)
    return config

def loadConfigFromFileStandard(handler, config_file, eva_bck='$', **kwags):
    config = configFromFile(config_file)
    method = handler.loadConfig if(hasattr(handler, 'loadConfig')) else lambda *args, **kkwags:loadConfigStandard(handler, *args, **kkwags)
    if(not method(config, eva_bck=eva_bck)):
        return False
    return True
    
def loadConfigStandard(handler, config, eva_bck='$', **kwags):
    handler.config = {}
    for k,v in config.items():
         v = dcp(mystr(v).config_evaluation(eva_bck=eva_bck, **config) if(isinstance(v, str)) else v)
         handler.config[k] = v
    return True

def setProperty(handler, topic, default=None):
    if(not hasattr(handler, '%sProperty'%topic.lower())):
        handler.addlog("no 'propertyTopic!!!!!!!!", colora=FAIL)
        return False
    # LOGger.addDebug(str(mdl.config))
    properties = getattr(handler, '%sProperty'%topic.lower())
    for k in properties:
        pDefault = dcp(default)
        if(k in properties):   pDefault = dcp(properties[k])
        p = handler.config.get(k, pDefault)
        if(isinstance_not_empty(p, str)):
            p = mystr(p).config_evaluation(**handler.config)
        setattr(handler, k, p)
        handler.addlog("set %s:%s"%(k, parse(p)), stamps=[topic])
    return True

#TODO:pathrpt
def pathrpt(apath, sep='_', path_sep=m_path_sep):
    adir, abanme = os.path.split(apath)
    eext = (path_sep if abanme[-1]==path_sep else '') if(abanme.find('.')==-1) else abanme[abanme.rfind('.'):]
    cond = lambda p: os.path.isfile(p) if eext!='' else os.path.isdir(p)
    p = (apath[:-1] if apath[-1]==path_sep else apath) if eext=='' else apath[:apath.rfind('.')]
    while(cond('%s%s'%(p, eext) if eext!='' else p)):
        '''如果p已存在，則繼續修改..........'''
        final_loc = p[p.rfind(path_sep)+1:]
        if (final_loc.rfind(sep)==-1 or (not final_loc[(final_loc.rfind(sep)+1):].isnumeric())):
            '''最內一層「沒有「<_sep_>」字元存在 或者 <_sep_>後面接著不是純數目」的話'''
            p = p+sep+'1'
        else:
            '''最內一層「有「<_sep_>」字元存在 且 <_sep_>後面接著是純數目」的話'''
            n = int(p[(p.rfind(sep)+1):]) + 1 #找出已存在複本的編序，然後+1
            rpstr = p[p.rfind(sep):] #找出要修改的名稱段落
            p = p[:p.rfind(path_sep)+1] + final_loc.replace(rpstr, '%s%d'%(sep,n)) 
    return '%s%s'%(p, eext)

#TODO:make_exp_fd
def make_exp_fd(head_exp_fds=None, common_name = 'round'):
    head_exp_fds = head_exp_fds if(isinstance(head_exp_fds, list)) else []
    return pathrpt(os.path.join(*head_exp_fds, common_name))

#TODO:explore_folder
#all_files, all_dirs = explore_folder(folder)
def explore_folder(folder, conditions=None, full=True):
    all_files, all_dirs = [], []
    for dirPath, dirNames, fileNames in os.walk(folder):
        dirct = os.path.join(dirPath)
        if(conditions(path=dirct) if(conditions) else True):
            all_dirs.append(dirct)
        for f in fileNames:
            file = dcp(os.path.join(dirPath, f) if(full) else f)
            if(conditions(path=file) if(conditions) else True):
                all_files.append(file)
    return all_files, all_dirs
    
#TODO:set_attr_into_project_buffer....
def set_attr_into_project_buffer(attr_name_reference, attr_name, attr_type=str, default_value=type(None), project_buffer=None,
                                 criterion=None):
    attr = attr_name_reference[attr_name]
    default_value = eval('m_%s'%attr_name) if(default_value==type(None)) else default_value #TODO:這裡的寫法不確定有沒有問題....
    project_buffer = project_buffer if(isinstance(project_buffer, dict)) else {}
    criterion = criterion if(criterion!=None) else lambda v:isinstance(v, attr_type)
    attr = attr if(criterion(attr)) else default_value
    project_buffer[attr_name] = attr
    return attr

#TODO:get_basename()
def get_basename(path):
    base_path = os.path.basename(path)
    return '.'.join(base_path.split('.')[:-1]) if(base_path.find('.')>-1) else base_path

def extend_basefilename(path, extends=None, path_sep = os.path.join('a','b')[1]):
    if(not isinstance(extends, list)):
        return path
    if(path==''):
        return stamp_process('',extends,'','','','_')
    path_structure = path.split(path_sep)
    basename = path_structure.pop(-1)
    ext = basename.split('.')[-1] if(basename.find('.')>-1) else ''
    basefilename = '.'.join(basename.split('.')[:-1]) if(basename.find('.')>-1) else basename
    new_basefilename = stamp_process('', [basefilename] + extends, '','','','_')
    new_basename = stamp_process('',[new_basefilename, ext], '', '', '', '.') if(basename.find('.')>-1) else new_basefilename
    path_structure.append(new_basename)
    return path_sep.join(path_structure)

#astype(maxdot, d_type=lambda x:x+0, default=0)
def astype(*args, criterion=None, d_type=float, default=None, default_method=None, **kwags):
    kwags.update({k:v for k,v in locals().items() if k!='args' and k!='kwags'})
    def method(arg, **kwags):
        try:
            arg = d_type(arg)
        except:
            arg = default_method(arg) if(default_method!=None) else default if(default!='self') else arg
        return arg
    ret = dearray_process(*args, method=method, **kwags)
    return ret[0] if(len(ret)==1) else ret

def mode_statistics(A=(np.random.random(10,)*10//1).astype(int), default=np.nan, return_index_when_multi=0, axis=None, 
                    return_count=False, return_ratio=False, return_value_only=False, ret=None, **kwags):
    try:
        if(isiterable(A) and axis!=None):
            return np.apply_along_axis(lambda x:mode_statistics(
                x,default,return_index_when_multi,return_count=return_count,return_ratio=return_ratio,return_value_only=return_value_only), 
                np.array(A), axis=axis)
        uni_values = tuple(set(A))
        every_counts = [np.sum(np.array(A)==x) for x in uni_values]
        max_count = np.max(every_counts)
        all_modes = list(tuple(np.array(uni_values)[np.array(every_counts)==max_count]))
        value = all_modes[return_index_when_multi%len(all_modes)] if(isinstance(return_index_when_multi, int)) else all_modes
        if(return_value_only):
            returned = value
        else:
            returned = (value,)
            if(return_count):
                returned = (*returned, max_count)
            if(return_ratio):
                returned = (*returned, max_count/len(mylist(tuple(A)).get_all()))
    except Exception as e:
        exception_process(e, logfile='')
        if isinstance(ret, dict): ret['message'] = str(e)
        if(return_value_only):
            returned = value
        else:
            returned = (default,)
            if(return_count):
                returned = (*returned, -1)
            if(return_ratio):
                returned = (*returned, -1)
    return returned

def mode_statistics_only_value(A, default=np.nan, return_index_when_multi=0, axis=None, return_count=False, return_ratio=False, **kwags):
    return mode_statistics(A, default=default, return_index_when_multi=return_index_when_multi, axis=axis, return_count=return_count, 
                           return_ratio=return_ratio, return_value_only=True, **kwags)

def counts_statistics(A, axis=None, **kwags):
    return len(mylist(tuple(A)).get_all()) if(axis==None or not hasattr(A, 'shape')) else A.shape[axis]

def statistics_properties(data, methods=None, axis=None, ret=None, stamps=None, default=np.nan, 
                          method_name_stamps = None, parse_method=None, **kwags):
    method_name_stamps = method_name_stamps if(isinstance(method_name_stamps, list)) else []
    stamps = stamps if(isinstance(stamps, list)) else []
    parse_method = parse if(parse_method=='auto') else parse_method
    if(isinstance(ret, dict)):
        stamp = stamp_process('', stamps, '','','','_')
        method_name_stamp = stamp_process('', method_name_stamps, '','','','_')
        meth = lambda x,**kwags:mode_statistics_only_value(x,**kwags)
        meth.__name__ = 'mode_statistics'
        count = lambda x,**kwags:counts_statistics(x,**kwags)
        count.__name__ = 'count'
        methods = [meth, np.max, np.min, np.median, np.std, count] if(
            not isinstance(methods, list)) else methods
        if(len(stamps)==0):
            for method in methods:
                try:
                    value = method(data, axis=axis)
                except:
                    try:
                        value = method(astype(data, default=default), axis=axis)
                    except:
                        value = np.nan
                if(parse_method!=None): value = parse_method(value)
                ultimate_stamp = getattr(method, '__name__', 'method_%s'%len(ret))
                ultimate_stamp = stamp_process(
                    '', [getattr(method, '__name__', 'method_%s'%len(ret)),method_name_stamp], '','','','_') if(
                        method_name_stamp) else ultimate_stamp
                ret.update({ultimate_stamp:value})
        else:
            ret_stamp = {}
            ret.update({stamp:ret_stamp})
            statistics_properties(data, methods=methods, axis=axis, ret=ret_stamp, stamps=None, default=default, 
                                  method_name_stamps=method_name_stamps, parse_method=parse_method, **kwags)
    else:
        ret = {}
        statistics_properties(data, methods=methods, axis=axis, ret=ret, stamps=stamps, default=default, 
                              method_name_stamps=method_name_stamps, parse_method=parse_method, **kwags)
        return ret
    
def range_datetime(sd, ed, days=1, sd_format='%Y-%m-%d %H:%M:%S', ed_format='%Y-%m-%d %H:%M:%S', tdunit=None, **kwags):
    if(isinstance(sd, str) or isinstance(ed, str)):
        if(isinstance(sd, str)):
            sd = dt.strptime(sd, sd_format)
        if(isinstance(ed, str)):
            ed = dt.strptime(ed, ed_format)
        return range_datetime(sd, ed, tdunit=tdunit)
    # 初始化日期列表
    date_list = []
    tdunit = tdunit if(isinstance(tdunit, dict)) else {'days':days}
    # 從起始日期開始迴圈，直到結束日期
    current_date = dcp(sd)
    while current_date <= ed:
        date_list.append(current_date)
        current_date += td(**tdunit)
    return date_list
    
#TODO:uniquifying
def uniquifying(ar, **unique_kwags):
    org_type = type(ar)
    org_type = (lambda x:np.array(x)) if(org_type==np.ndarray) else org_type
    org_type = (lambda x:pd.DataFrame(x)) if(str(org_type).find('pandas.core.frame')>-1) else org_type
    org_type = (lambda x:pd.Series(x)) if(str(org_type).find('pandas.core.series')>-1) else org_type
    ar_list = list(tuple(ar))
    ar_list = sorted(np.unique(ar, **unique_kwags), key=lambda x:ar_list.index(x))
    return org_type(ar_list)
#TODO:inherit
def inherit(object_):
    print(object_)
    dtype = type(object_)
    if(issubclass(dtype, (list, tuple, dict, str))):
        return dtype
    elif(dtype==np.ndarray ):
        return np.array
    elif(dtype==pd.core.frame.DataFrame):
        return pd.DataFrame
    elif(dtype==pd.core.series.Series):
        return pd.Series
    else:
        return type(None)
#TODO:transform_dict2class
def transform_dict2class(dic, admit_key_names=None, init_args=None, init_kwags=None, show_detail=False, 
                         activate_key='core', default=None, default_method=None,
                         exception_criterion=(lambda v,**kkwags:isinstance(v, str) or isinstance(v, list)),
                         exception_method=(lambda v,**kkwags:eval('my%s'%(mystr(type_string(v)).replace_all('my','')))(v)), 
                         **kwags):
    dic_copy = dcp(dic)
    if(exception_criterion(dic, **kwags)): return exception_method(dic, **kwags) #如果dic是字串或陣列，就改造成my系列再送出去
    if(not isinstance(dic, dict)):
        return default if(default_method==None) else default_method(dic, **kwags)
    # dic是字典，比較複雜...
    _addlog = kwags.get('addlog', addloger(logfile='')) if(show_detail) else (lambda *args, **kwags:None)
    init_kwags = init_kwags if(isinstance(init_kwags, dict)) else {}
    init_args = init_args if(isinstance(init_args, list)) else []
    try:
        references = dic_copy
        if(activate_key in dic_copy):
            # 如果dic中有關鍵鍵值(`activate_key`)，那就是核心主體(core)
            core = dic_copy.pop(activate_key)
            core = load_json(core) if(core[-5:]=='.json' if(isinstance(core, str)) else False) else core #如果核心主體是.json路徑，要加載
            class_type = eval('my%s'%(mystr(type_string(core)).replace_all('my','')))
            init_args.insert(0, core)
        elif((isinstance(tuple(dic_copy.keys())[0], str) and isinstance(tuple(dic_copy.values())[0], dict)) if(
                len(dic_copy)==1) else False):
            # {'stamp': {p1:..., p2:..., p3:...}} 比較像是給activation, lossmethod, layer轉化用的
            core = tuple(dic_copy.keys())[0]
            class_type = mystr
            init_args.insert(0, core)
            references = tuple(dic_copy.values())[0]
        else:
            return dic_copy
            # class_type = eval(dic_copy.pop('Type', 'mystr'))
        #dic內部一樣有需要轉化為class的物件，通過admit_key_names進行篩選
        instance = class_type(*init_args, **init_kwags)
        admit_key_names = admit_key_names if(isinstance(admit_key_names, list)) else references.keys()
        for k,v in references.items():
            if(k in admit_key_names):
                v = transform_dict2class(v, admit_key_names=admit_key_names, 
                                         show_detail=show_detail, activate_key=activate_key, default=default, default_method=lambda x, **kwags:x,
                                         exception_criterion=exception_criterion, exception_method=exception_method, **kwags)
                _addlog(str(v)[:200], stamps=[k])
                setattr(instance, k, v)
        return instance
    except Exception as e:
        exception_process(e, logfile=kwags.get('logfile', ''), stamps=kwags.get('stamps', []))
        return None
#TODO:transform_class2dict
def transform_class2dict(obj, admit_key_names=None, admit_value_types=None, 
                         activate_key='core', 
                         exception_criterion=(lambda v,**kwags:type_string(v)[:2]!='my'), 
                         exception_method=(lambda v,**kwags:v), **kwags):
    if(exception_criterion(obj, **kwags)): return exception_method(obj, **kwags)
    dic = {}
    admit_key_names = admit_key_names if(isinstance(admit_key_names, list)) else [k for k in dir(obj) if k[:2]!='__' or k[-2:]!='__']
    admit_value_types = admit_value_types if(isinstance(admit_value_types, list)) else m_json_admit_types
    try:
        dic['Type'] = type_string(obj)
        if('my'==dic['Type'][:2]):
            naturalized = eval(dic['Type'][2:])(obj)
            dic[activate_key] = naturalized
        else:
            dic[activate_key] = ''
        for k in admit_key_names:
            if(hasattr(obj, k)):
                v = getattr(obj, k)
                dic.update({k:v}) if(
                    np.array(tuple(map(lambda ts: isinstance(v, ts), admit_value_types))).any()) else None
        return dic
    except Exception as e:
        exception_process(e, logfile=kwags.get('logfile', ''), stamps=kwags.get('stamps', []))
        return None

#TODO:mydict
class mydict(dict):
    def __init__(self, dict_root={}, **stg_dict_root):
        self.update(dict_root)
        self.update(stg_dict_root)
        
    def valueGet(self, key='', default=None):
        if(not key in self):
            if(len(self.keys())==1):
                return tuple(self.values)[0]
            elif(len(self.keys())!=1):
                return default
        else:
            return self[key]
        
    def tryGet(self, key):
        return self.get(key, key)
        
    def concatenate(self, dtype=None, rewrite=False, return_self=False, **kwags):
        printer = kwags.get('printer', print) if(not m_dont_print) else (lambda *args, **kwags:None)
        item_inlist = list(self.values())
        if(dtype==None):
            dtype = np.array
            uniquifying_dtypes_instg = uniquifying(list(map(lambda x:str(type(x)), item_inlist)))
            dtypes = list(map(inherit, item_inlist))
            if(len(uniquifying_dtypes_instg)==1):
                dtype = dtypes[0]
                printer('using common dtype:%s!!!'%str(dtype))
        kwags['axis'] = kwags.get('axis', 1)
        if(dtype==dict):
            contents_key_inlist = get_all_values([list(tuple(d.keys())) for item_key,d in self.items()])
            if(np.unique(contents_key_inlist).shape[0]<len(contents_key_inlist)):
                printer('contents keys duplicated!!!!')
                if(not rewrite):
                    return {}
            ret = {}
            for item_key,d in self.items():
                ret.update(d)
            return ret
        elif(issubclass(dtype, tuple)):
            item_inlist_flatten = get_all_values(item_inlist)
            return tuple(uniquifying(item_inlist_flatten) if(rewrite) else item_inlist_flatten)
        elif(issubclass(dtype, list)):
            item_inlist_flatten = get_all_values(item_inlist)
            return dtype(tuple(uniquifying(item_inlist_flatten) if(rewrite) else item_inlist_flatten))
        elif(issubclass(dtype, str)):
            stg_sep = kwags.get('stg_sep', '||')
            item_inlist_flatten = get_all_values(item_inlist)
            item_inlist_flatten = list(tuple(uniquifying(item_inlist_flatten) if(
                                    rewrite) else item_inlist_flatten))
            return stg_sep.join(list(map(str, tuple(item_inlist_flatten))))
        elif(issubclass(dtype, np.ndarray)):
            return np.concatenate(item_inlist, **kwags)
        elif(dtype in [pd.DataFrame, pd.Series]):
            return pd.concat(item_inlist, **kwags)
        if(return_self):
            return self
        return None
 
def instances_method_process(*args, method_name='stop', method_kwags_list=None, method_args_list=None):
    method_kwags_list = mylist(method_kwags_list if(isinstance(method_kwags_list, list)) else [])
    method_args_list = mylist(method_args_list if(isinstance(method_args_list, list)) else [])
    for i,arg in enumerate(args):
        getattr(arg, method_name)(*method_args_list.get(i, []), **method_kwags_list.get(i, {})) if(
            hasattr(arg, method_name)) else None
 
def dirname(p):
    if(not isinstance(p, str)):
        return ''
    if(p==''):
        return ''
    if(os.path.dirname(p)==''):
        return '.'
    return os.path.dirname(p)

def super_delete(folder):
    mission_count, fail_paths = 0, []
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        mission_count += 1
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            addlog('Failed to delete %s. Reason: %s' % (file_path, e), logfile=os.path.join('log', 'log_%s.txt'))
            fail_paths.append(file_path)
    return mission_count, fail_paths

def load_json(file, chardetCount_ubd=5000, encoding=None, **kwags):
    if(not os.path.exists(file)):
        return {}
    encodingDefault = detect_txt_encoding(file, chardetCount_ubd=chardetCount_ubd)
    encoding = encoding if(isinstance_not_empty(encoding, str)) else encodingDefault
    with open(file, encoding=encoding) as f:
        data = json.load(f)
        f.close()
    return data
    
def fit_type_for_json(v):
    if(isinstance(v, np.bool_)):
        return bool(v)
    ret = dcp(v)
    if(not isnonnumber(v)):
        try:
            ret = int(v) if(float(v)//1==float(v)) else float(v)
        except:
            ret = float(v)
    return ret

def str_pix_len(stg, font_name='msjh.ttc', font_size=12):
    font = ImageFont.truetype(font_name, font_size)
    total_width = 0
    for char in stg:
        char_width, _ = font.getsize(char)
        total_width += char_width
    return total_width

def press_and_record_time(hotkey='space', time_format='%Y%m%d %H:%M:%S.%f', outfile='time_points.json', **kwags):
    try:
        timestamps = []
        while(True):
            kb.wait(hotkey)
            cur_tp_stg = dt.now().strftime(time_format)
            print(cur_tp_stg)
            timestamps.append(cur_tp_stg)
    except:
        print('timestamps len:%d'%len(timestamps))
    finally:
        if(isinstance_not_empty(outfile, str)):
            save_json(timestamps, outfile)
            return True
        else:
            return timestamps

#TODO:execute
def execute(name, *containers, default=None, dominator=type(None), print_finded_label=False, print_value=False, 
            criterion=None, not_found_alarm=True, **specific_containers):
    try:
        old_default = dcp(default)
    except:
        old_default = default
    finded_label = None
    if(dominator!=type(None)):
        try:
            default = dcp(dominator)
            finded_label = '--dominated'
        except:
            default = dominator
    if(finded_label==None):
        for k,v in specific_containers.items():
            v = v if(isinstance(v, dict)) else {}
            if(name in v):
                default = v[name]
                finded_label = dcp(stamp_process('',['specific_containers',k],'','','',' '))
                break
    if(finded_label==None):
        for i,v in enumerate(containers):
            if(isinstance(v, dict)):
                if('m_%s'%name in v):
                    default = v['m_%s'%name]
                    finded_label = dcp(i)
                    break
                elif(name in v):
                    default = v[name]
                    finded_label = dcp(i)
                    break
            elif(hasattr(v, name)):
                default = getattr(v, name)
                finded_label = dcp(i)
                break
    print(finded_label) if(print_finded_label) else None
    (addlog('`%s`'%(str(default)[:200]), stamps=[name]) if(
        not isiterable(default)) else show_vector(default, stamps=[name])) if(print_value) else None
    if(finded_label==None):
        if(not_found_alarm):
            print('`%s` execute error:\n`%s`'%(name, str(default)[:200]))
            sys.exit(1)
        return default
    if(criterion!=None):
        if(not criterion(default)):
            if(not_found_alarm):
                print('`%s` execute error with criterion:\n`%s`'%(name, str(default)[:200]))
                sys.exit(1)
            return old_default
    specific_containers.get('project_buffer',{}).update({name:default})
    return default

def executeEasy(name, *args, default=None, not_found_alarm=False, **kwags):
    return execute('addlog', *args, default=default, not_found_alarm=not_found_alarm)

#TODO:is_variable_accessible
def is_variable_accessible(name, *containers, default=None, criterion=None, **kwags):
    addlog_ = execute('addlog', kwags, default=addlog, not_found_alarm=False)
    accessible =False
    for i,v in enumerate(containers):
        if(isinstance(v, dict)):
            if('m_%s'%name in v):
                default = v['m_%s'%name]
                accessible = True
                break
            elif(name in v):
                default = v[name]
                accessible = True
                break
        elif(hasattr(v, name)):
            default = getattr(v, name)
            accessible = True
            break
    if(criterion!=None):
        if(not criterion(default)):
            addlog_('variable criterion failed!!!'%name, stamps=[name], logfile='')
            return False
        return True
    if(not accessible):
        addlog_('variable not found!!!'%name, stamps=[name], logfile='')
        return False
    return True

def is_variables_accessible(names, *containers, default=None, criterion=None, defaults=None):
    defaults = defaults if(isinstance(defaults, dict)) else {}
    for name in names:
        if(not is_variables_accessible(name, *containers, default=defaults.get(name, default))):
            return False
    return True

def isinstance_or_None(value, _type):
    return (isinstance(value, _type) if(isinstance(_type, type)) else bool(_type(value))) or isinstance(value, type(None))

def isinstances(value, *_types, method=None):
    method = method if(method!=None) else isinstance
    ret = False
    for t in _types:
        ret |= method(value, t)
    return ret

def isinstance_not_empty(value, _type):
    if(isinstance(_type, tuple)):
        for x in _type:
            if(isinstance_not_empty(value, x)):
                return True
        return False
    return (isinstance(value, _type) if(isinstance(_type, type)) else bool(_type(value))) and (not(not value))

def isinstance_of_time(value, time_format='%s'):
    try:
        value.strftime(time_format)
        return True
    except:
        return False

def key_stgs_process(attr_name, obj, key_stgs=None, default=None, key_stgs_translation=None):
    key_stgs = key_stgs if(isinstance(key_stgs, list)) else ['None','np.nan','np.inf','-np.inf']
    key_stgs_referecnce = key_stgs_translation if(isinstance(key_stgs_translation, dict)) else {}
    arg = execute(attr_name, obj, default='None')
    if(isinstance(arg, str)):
        for key_stg in key_stgs:
            if(key_stg==arg):
                try:
                    arg = key_stgs_referecnce.get(arg, eval(arg))
                except:
                    arg = default
    if(isinstance(obj, dict)):
        obj.update({attr_name:arg})
    else:
        setattr(obj, attr_name, arg)
    return True
    

def getattr_intype(*args, attr_type=None):
    ret = getattr(*args[:3])
    attr_type = mylist(args).get(3, None) if(attr_type==None) else attr_type
    attr_type = type(mylist(args).get(2, None)) if(attr_type==None) else attr_type
    if(attr_type!=None):
        if(isinstance(ret, attr_type)):
            return ret
        return args[2]

def getattr_not_empty(*args, attr_type=None):
    ret = getattr(*args[:3])
    attr_type = mylist(args).get(3, None) if(attr_type==None) else attr_type
    attr_type = type(mylist(args).get(2, None)) if(attr_type==None) else attr_type
    if(attr_type!=None):
        if(isinstance_not_empty(ret, attr_type)):
            return ret
        return args[2]
        
def getattr_or_None(*args, attr_type=None):
    ret = getattr(*args[:3])
    attr_type = mylist(args).get(3, None) if(attr_type==None) else attr_type
    attr_type = type(mylist(args).get(2, None)) if(attr_type==None) else attr_type
    if(attr_type!=None):
        if(isinstance_or_None(ret, attr_type)):
            return ret
        return args[2]

def data_sieve(data, permissive_types=[int, str, float, type(None), bool], 
               fit_type_for_json_method=fit_type_for_json, stamps=None, **kwags):
    addlog_ = kwags.get('addlog', addlog)
    if(isinstance(data, dict)):
        data_keys = tuple(data.keys())
    if(isiterable(data)):
        data_keys = range(len(data))
    stamps = stamps if(isinstance(stamps, list)) else []
    for k in reversed(data_keys):
        try:
            v = dcp(data[k])
        except:
            addlog('dcp failed!!', stamps=[*stamps, str(k)])
            v = data[k]
        # addlog(str(v))
        if(isinstance(v, dict) or isiterable(v, exceptions=[str, dict, pd.Series, pd.DataFrame])):
            # addlog('dig it!!', stamps=[str(k)])
            data_sieve(v, permissive_types=permissive_types, fit_type_for_json_method=fit_type_for_json_method, 
                        stamps=[*stamps, str(k)])
        else:
            preserve = False
            for T in permissive_types:
                preserve |= isinstance(v, T)
                data.update({k:fit_type_for_json_method(v)}) if(
                    isinstance(v,T) and T!=type(None) and isinstance(data,dict)) else None
            if(not preserve):
                if(isinstance(data, dict)):
                    data.pop(k)
                addlog_('detect invalid json contents!! type:%s; value:\n%s'%(type(v), str(v)[:200]), stamps=[*stamps, str(k)])
    

def save_json(data, file, mode='w', indent=4, data_sieve_method=None, ensure_ascii=False, encoding='utf-8'):
    try:
        data_sieve_method(data) if(data_sieve_method!=None) else None
        with open(file, mode, encoding=encoding) as json_file:
            json.dump(data, json_file, indent=indent, cls=myJSONEncoder, ensure_ascii=ensure_ascii)
    except Exception as e:
        exception_process(e, stamps=['save_json'])
        return False
    return True
    
def save(data, fn, save_types=None, exp_fd=None, rewrite=False, **kwags):
    exp_fd = exp_fd if(isinstance(exp_fd, str)) else '.'
    file = os.path.join(exp_fd, fn) if(rewrite) else pathrpt(os.path.join(exp_fd, fn))
    save_types = save_types if(isinstance(save_types, list)) else []
    if('pkl' in save_types):
        save_file = pathrpt('%s.pkl'%file)
        save_file = save_file if(rewrite) else pathrpt(save_file)
        data.to_pickle(save_file)
    if('json' in save_types):
        save_file = '%s.json'%file
        save_file = save_file if(rewrite) else pathrpt(save_file)
        save_json(data, save_file, **kwags)
    if('png' in save_types):
        save_file = '%s.png'%file
        save_file = save_file if(rewrite) else pathrpt(save_file)
        data.savefig(save_file)
        
#TODO:chdir_process
def chdir_process(exe_file, json_file='', create_exp_fd=True, **kwags):
    json_file = '%s_buffer.json'%os.path.basename(exe_file.replace('.py','')) if(json_file=='__file__') else json_file
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cur_dir if(cur_dir.find('site-package')==-1) else '.')
    print('目前工作路徑:%s'%os.getcwd())
    buffer = load_json(json_file) if(os.path.exists(json_file)) else {}
    wkspace = questioning('指定工作路徑', 'wkspace', '', buffer, json_file)
    wkspace = mystr(wkspace).path_sep_correcting()
    os.chdir(wkspace)
    print('現在工作路徑:%s'%os.getcwd())
    project_buffer = load_json(json_file) if(os.path.exists(json_file)) else {}
    
    reference = dcp(buffer)
    reference.update(project_buffer)
    for k,v in kwags.items():
        value = mystr(v).replace_refered_words('$', reference)
        project_buffer[k] = value
        
    exp_fd = questioning('指定分析輸出處:', 'exp_fd', 'test', project_buffer, json_file)
    CreateContainer(exp_fd) if(create_exp_fd) else None
    project_buffer['exp_fd'] = exp_fd
    project_buffer['wkspace'] = wkspace
    return project_buffer
#TODO:buffering
def buffering(name, value, buffer={}, case_avoid=None, save_json_file='', translation=m_input_translation):
    translation = translation if(isinstance(translation, dict)) else {}
    if(value!=case_avoid and value!=buffer.get(name, case_avoid)):
        print('`%s`'%name)
        buffer.update({name:(translation.get(value, value) if(isinstance(value, str)) else value)})
        print('`%s`'%buffer[name])
    if(save_json_file):
        save_json(buffer, save_json_file, data_sieve_method=None)
#TODO:questioning
def questioning(question, name='', default_value=None, buffer={}, json_file='', case_avoid=None, read_history=False, 
                pop_from_buffer=False, **kwags):
    answer = ''
    if(name==''):
        return answer
    read_history_ready = False
    if(read_history):
        if(name in buffer):
            addlog('[%s]使用歷史紀錄:%s'%(name, str(buffer[name])[:200]))
            answer = buffer.pop(name) if(pop_from_buffer) else buffer[name]
            read_history_ready = True
    if(not read_history_ready if(read_history) else True):
        answer = (input('%s%s'%(question, stamp_process(':', [buffer.get(name, str(default_value))]))) or 
                       buffer.get(name, default_value)) if(buffer.get(name, default_value)!=None) else input(question)
        if(answer[0]=='-' if(isinstance(answer, str) and not answer in ['','-none']) else False):
            return answer
        buffering(name, answer, buffer, case_avoid=case_avoid, save_json_file=json_file)
        answer = buffer[name]
        buffer.pop(name) if(pop_from_buffer) else None
    return answer

#TODO:recursive_questioning....
def recursive_questioning(question, success_answer, name='', default_value=None, abort_answer=None, 
                          buffer={}, json_file='', case_avoid=None, max_iter=5, read_history=False, **kwags):
    n_iter = 0
    answer = False if(success_answer!=False) else True
    while(answer!=success_answer or n_iter==0):
        read_history &= (n_iter==0)
        answer = questioning(question, name=name, default_value=default_value, 
                             buffer=({name:buffer[name]} if(name in buffer) else {}),
                             case_avoid=case_avoid, read_history=read_history, **kwags)
        if((answer==abort_answer if(abort_answer!=None) else False) or (n_iter>max_iter)):
            return False
        n_iter += 1
    buffering(name, answer, buffer, case_avoid=case_avoid, save_json_file=json_file)
    return True
#TODO:dictionary_constructing
def dictionary_constructing(buffer={}, abort_answer='-q', finish_answer='-f', question='', name='', read_history=False, 
                            **kwags):
    i, answer=0, {}
#    while(questioning('[%s]continue setting?'%name, name='iscontinue', default_value='y', **kwags)=='y' if(i>0) else True):
    while(True):
        key = questioning('%s[%s:key setting...]'%(question, name), name='%s-key'%name, **kwags)
        if(key==finish_answer):
            break
        elif(key==abort_answer):
            return False
        elif('-p' in key.split(' ')):
            pop_key = key.replace(' -p','').replace('-p ','').strip()
            answer.pop(pop_key)
            continue
        elif('-r' in key.split(' ')):
            answer={}
            continue
        elif('-sh' in key.split(' ')):
            addlog('answer now....:\n%s'%answer)
            continue
        elif(key.find('-')>-1):
            continue
        else:
            buffer1 = {}
            if(not recursive_questioning_and_check('%s[%s:value setting...]'%(question, name), 
                                            checking=lambda answer, **kwags:True, name='%s-value'%name,
                                            default_value=None, abort_answer=abort_answer, buffer=buffer1,
                                            **kwags)):
                continue
            value = typing_stg(buffer1['%s-value'%name])
            answer[key] = value
        i += 1
    if(questioning('[%s] accept setting?'%name, name='iscontinue', default_value='y', **kwags)!='y'):
        return False
    buffer['answer'] = answer
    return True
#TODO:recursive_questioning
def recursive_questioning_and_check(question, checking, success_answer=True, name='', 
                                    default_value=None, abort_answer=None, buffer={}, 
                                    json_file='', case_avoid=None, max_iter=5, read_history=False, 
                                    **kwags):
    n_iter = 0
    answer = None
    while(checking(answer, **kwags)!=success_answer or n_iter==0):
        read_history &= (n_iter==0)
        answer = questioning(question, name=name, default_value=default_value, 
                             buffer=({name:buffer[name]} if(name in buffer) else {}),
                             case_avoid=case_avoid, read_history=read_history, **kwags)
        if((answer==abort_answer if(abort_answer!=None) else False) or (n_iter>max_iter)):
            return False
        if(answer=='-d'):
            buffer1 = {}
            if(not dictionary_constructing(buffer=buffer1, question=question, name=name, **kwags)):
                return False
            answer = buffer1['answer']
        n_iter += 1
    buffering(name, answer, buffer, case_avoid=case_avoid, save_json_file=json_file)
    return True

def selectionSynch(*args, method, default=None):
    outputs = []
    for arg in args:
        if(not isiterable(arg)):
            outputs.append(arg)
            continue
        try:
            output = method(arg)
        except:
            output = default
        outputs.append(output)
    return tuple(outputs)

def make_hyperlink(destination, start_location='.', supervise_root=None, title=None, **kwags):
    kwags['path_sep'] = kwags.get('path_sep', '\\')
    path_sep = execute('path_sep', kwags, default=m_path_sep, not_found_alarm=False)
    destination = (supervise_root + m_path_sep + destination) if(
        isinstance_not_empty(supervise_root, str)) else os.path.relpath(os.path.abspath(destination), os.path.abspath(start_location))
    stg = '=HYPERLINK("%s", "%s")'%(destination, (os.path.basename(destination) if(not isinstance_not_empty(title, str)) else title))
    return stg.replace('/', path_sep).replace('\\', path_sep)

def typing_stg(value, dtype='s'):
    ret = None
    buffer = {}
    if(not recursive_questioning_and_check('設定型態:[s:str/n:num/l:list/d:dict/e:exec]:',
                                                      lambda s: s in ['s','p','i','n','l','d','e','v'], True,
                                                      'dtype', dtype, '-q', buffer=buffer)):
        return ret
    dtype = buffer['dtype']
    if(dtype=='s'):
        return value
    elif(dtype=='p'):
        return mystr(str(value)).path_sep_correcting()
    elif(dtype=='i'):
        return int(value)
    elif(dtype=='n'):
        return float(value)
    elif(dtype=='l'):
        if(questioning('deeply dtyping', 'name', 'n')!='y'):
            return list(map(lambda s:s.strip(), value.split(','))) if(isinstance(value, str)) else list(value)
        dtype_next = questioning('list default dtype', 'dtype_next', 's')
        a_list = []
        for v in list(map(lambda s:s.strip(), value.split(','))):
            addlog('設定[%s]資料型態'%v)
            a_list.append(typing_stg(v, dtype_next))
        return a_list
    elif(dtype=='d'):
        if(isinstance(value, dict)):
            return value
        list_config_value = list(map(lambda s:s.strip(), value.split(','))) if(isinstance(value, str)) else list(value)
        dict_config_value = dict(zip(*list(map(
                lambda s:list(map(lambda s_:s_.strip(), s.split(':'))), list_config_value))))
        if(questioning('deeply dtyping', 'name', 'n')!='y'):
            return dict_config_value
        dtype_next = questioning('list default dtype', 'dtype_next', 's')
        a_dict = {}
        for k,v in dict_config_value.items():
            a_dict[k] = typing_stg(v, dtype_next)
        return a_dict
    elif(dtype=='e'):
        try:
            exec('ret = %s'%value)
            value = ret
        except Exception as e:
            addlog('%s... exec使用失敗'%(str(value)[:200]))
            addlog('錯誤訊息:%s'%str(e))
            value = typing_stg(value, dtype='s')
        return value
    else:
        return value
    
#TODO:recursive_questioning
def recursive_questioning_and_check_typing(question, checking, success_answer=True, name='', 
                                    default_value=None, abort_answer=None, buffer={}, 
                                    json_file='', case_avoid='', max_iter=5, dtype='s',
                                    read_history=False, display_checking=False, **kwags):
    n_iter = 0
    answer = None
    def criterion(answer, **kwags):
        print(answer) if(display_checking) else None
        return checking(answer, **kwags)
    while(criterion(answer, **kwags)!=success_answer or n_iter==0):
        read_history &= (n_iter==0)
        answer = questioning(question, name=name, default_value=default_value, 
                             buffer=({name:buffer[name]} if(name in buffer) else {}),
                             case_avoid=case_avoid, read_history=read_history, **kwags)
        if((answer==abort_answer if(abort_answer!=None) else False) or (n_iter>max_iter)):
            return False
        if(answer=='-d'):
            buffer1 = {}
            if(not dictionary_constructing(buffer=buffer1, question=question, name=name, **kwags)):
                return False
            answer = buffer1['answer']
        elif('-type' in answer.split(' ') if(isinstance(answer, str)) else False):
            obj_stg = answer.split(' ')[0]
            obj = typing_stg(answer, dtype=dtype) if(not read_history) else answer
            print('obj_stg:%s'%obj_stg)
            print('obj:%s'%str(obj)[:200])
            print('obj:%s'%str(type(obj)))
            continue
        answer = typing_stg(answer, dtype=dtype) if(not read_history) else answer
        addlog('`%s`'%(str(answer)[:200]), logfile='', stamps=['after typing stg', type_string(answer)])
        n_iter += 1
    buffering(name, answer, buffer, case_avoid=case_avoid, save_json_file=json_file)
    return True

def introduce(something, show_content_number=3, show_dict_values=False, **kwags):
    if(hasattr(something, 'shape')):
        shape = something.shape
        if(len(shape)<1):
            return introduce(parse(something), show_content_number=show_content_number, **kwags)
        elif(len(shape)==1):
            return introduce(list(map(lambda x:x, something)), show_content_number=show_content_number, **kwags)
        else:
            return '%s\n%s'%(stamp_process('',{'shape':something.shape}), pd.DataFrame(something).iloc[:show_content_number])
    elif(isiterable(something)):
        kwags.update({'is_end':False, 'max_show_count':show_content_number})
        return show_vector(something, **kwags)
    elif(isinstance(something, dict)):
        contents = {'keys':','.join(list(map(str, list(something.keys())[:show_content_number])))}
        contents.update({'values':'\n'.join(list(map(lambda x:introduce(parse(x)), list(something.values())[:show_content_number])))}) if(
            show_dict_values) else None
        contents_stamp = stamp_process('',contents)
        return '[dict] size:%d\n%s'%(len(something, contents_stamp))
    else:
        return '(%s)%s'%(type_string(something), parse(something, **kwags))
  
def queue_append(q, new_content):
    if not q.empty():
        try:
            q.get_nowait()   # discard previous (unprocessed) frame
        except queue.Empty:
            return False
    q.put(new_content)
    return True    

def queue2list(q):
    # 从队列中提取数据
    queue_data = []
    while not q.empty():
        queue_data.append(q.get())
    return queue_data

def get_live_params(json_file, *objects, renew_passtime=30*60, default=None, not_found_alarm=False, log_when_renew=True, 
                    click=None, click_stamp=None, renew_passtimes=None, config_keys=None, stamps=None, prev_json_time=None, **kwags):
    _addlog = kwags.get('addlog', addloger(logfile=''))
    stamps = stamps if(isinstance(stamps, list)) else []
    renew_passtimes = renew_passtimes if(isinstance(renew_passtimes, dict)) else {}
    if(isinstance(prev_json_time, dt)):
        timestamp = os.path.getmtime(json_file)
        modify_time = dt.fromtimestamp(timestamp)
        if(modify_time == prev_json_time):
            return True
        kwags.get('ret', {}).update({'prev_json_time':modify_time})
    if(isinstance(click, dict)):
        if(isinstance(click_stamp, str)):
            if(click_stamp in click):
                delta_t = (dt.now() - click[click_stamp]).total_seconds()
                if(delta_t < renew_passtimes.get(click_stamp, renew_passtime)):
                    return True
        else:
            success = len(click)>0
            for k,v in click.items():
                success &= get_live_params(json_file, *objects, renew_passtime=renew_passtimes.get(k, renew_passtime), 
                                           default=default, not_found_alarm=not_found_alarm, click=click, click_stamp=k, 
                                           renew_passtimes={}, config_keys=config_keys, log_when_renew=log_when_renew, **kwags)
                if(not success and not_found_alarm):
                    return False
            return success
    if(not isinstance_not_empty(json_file, str)):
        _addlog('json_file not str:`%s`'%json_file)
        return False
    if(not os.path.exists(json_file)):
        _addlog("json_file doesn't exist':`%s`"%json_file)
        return False
    if(not json_file[:4]!='json'):
        _addlog("json_file doesn't legal':`%s`"%json_file)
        return False
    config = load_json(json_file)
    for obj in objects:
        if(isinstance(obj, dict)):
            for k,v in config.items():
                if(not k in config_keys if(isinstance(config_keys, list)) else False):
                    continue
                obj.update({k:v})
        elif(isinstance(obj, type(None))):
             continue
        else:
            try:
                for k,v in config.items():
                    if(not k in config_keys if(isinstance(config_keys, list)) else False):
                        continue
                    setattr(obj, k, v)
            except Exception as e:
                exception_process(e, logfile=execute('logfile', kwags, default='', not_found_alarm=False))
                if(not_found_alarm):
                    return False
    _addlog('params renew~', stamps=stamps, click=click, click_stamp=click_stamp) if(
        log_when_renew) else (click.update({click_stamp:dt.now()}) if(isinstance(click, dict)) else None)
    return True

def check_script_running(script_name, exec_name=None, script_name_index=-1, strictly=True):
    """Check if there is any running process that contains the given name."""
    # Iterate over all running process
    consider_exec_name = isinstance(exec_name, str)
    by_index = isinstance(script_name_index, int)
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        script_names = mylist(proc.info['cmdline'])
        if(len(script_names)==0):
            continue
        if(consider_exec_name):
            if(script_names.get(0, '').lower()!=exec_name.lower()):
                # print('script_names.get(0, '').lower()', script_names.get(0, '').lower(), 'exec_name.lower()', exec_name.lower())
                continue
        if(by_index):
            if(strictly):
                if(script_names.get(script_name_index, '')==script_name):
                    return True
            else:
                if(script_names.get(script_name_index, '').find(script_name)>-1):
                    return True
        else:
            for s in script_names:
                if(strictly):
                    if(s==script_name):
                        return True
                else:
                    if(s.find(script_name)>-1):
                        return True
    return False

def script_monitor(script_name, exec_name=None, sleep_time=10, messenger=None, strictly=True, **kwags):
    if(not isinstance_not_empty(script_name, str)):
        return
    addlog = kwags.get('addlog', addloger(logfile=kwags.get('logfile','')))
    addlog('start monitor:%s'%script_name)
    log_counter = {}
    while True:
        if check_script_running(script_name, exec_name, strictly=strictly):
            addlog(f"{script_name} is running", log_counter=log_counter, log_counter_stamp='exem', 
                    reset_log_counter=True, log_when_unreset=True)
        else:
            now = dt.now().strftime('%Y%m%d %H:%M:%S')
            addlog(f"{script_name} is not running", stamps=[now], log_counter=log_counter, log_counter_stamp='exem')
            if(kwags.get('recipient')):
                recipient = kwags.get('recipient', '')
                messenger = messenger if(isinstance(kwags.get('messenger'), Messenger)) else m_messenger
                try:
                    messenger.send_email(recipient, '[%s]exe aborted!!!'%script_name,'[%s]unknown reason....'%now)
                except:
                    addlog('sending failed!!!!', log_counter=log_counter, log_counter_stamp='send failed')
                else:
                    addlog('sending successful!!!!', log_counter=log_counter, log_counter_stamp='send failed',
                            reset_log_counter=True, log_when_unreset=True)
        time.sleep(sleep_time)  # 每10秒檢查一次
        
def detect_txt_encoding(file, encoding_default=None, chardetCount_ubd=5000):
    if(not isinstance(encoding_default, str)):
        try:
            with open(file, 'rb') as f:
                raw_data = f.read(chardetCount_ubd)  # 读取一部分文件内容用于编码检测
                resault = chd.detect(raw_data)
            return resault['encoding']
        except Exception as e:
            exception_process(e,logfile='')
            return encoding_default
    return encoding_default
        
def read_txt(file, lines=None, encoding=None, chardetCount_ubd=5000, front_sym_inLine=None, back_sym_inLine=None, **kwargs):
    if(not isinstance(encoding, str)):
        try:
            with open(file, 'rb') as f:
                raw_data = f.read(chardetCount_ubd)  # 读取一部分文件内容用于编码检测
                result = chd.detect(raw_data)
                encoding = result['encoding']
                print(f"Detected encoding: {encoding}")
        except Exception as e:
            exception_process(e,logfile='')
            return False
    lines = lines if(isinstance(lines, list)) else []
    # 使用with语句打开文件
    with open(file, 'r', encoding=encoding) as f:
        # 使用循环逐行读取文件内容
        while True:
            line = f.readline()
            # 如果返回空字符串，说明文件已经读完
            if not line:
                break
            # 去除行末尾的换行符和空白字符，并将行存入列表
            line_cleaned = line.strip()
            if front_sym_inLine:   line_cleaned = f'{front_sym_inLine}{line_cleaned}'
            if back_sym_inLine:    line_cleaned = f'{line_cleaned}{back_sym_inLine}'
            myline = dcp(line_cleaned)
            lines.append(myline)
    return True

def read_txt_all(file, handler=None, encoding=None, chardetCount_ubd=5000):
    if(not isinstance(encoding, str)):
        try:
            with open(file, 'rb') as f:
                raw_data = f.read(chardetCount_ubd)  # 读取一部分文件内容用于编码检测
                result = chd.detect(raw_data)
                encoding = result['encoding']
                print(f"Detected encoding: {encoding}")
        except Exception as e:
            exception_process(e,logfile='')
            return False
    handler = handler if(isinstance(handler, mystr)) else mystr()
    # 使用with语句打开文件
    with open(file, 'r', encoding=encoding) as f:
        content = f.read()
    handler.content = content
    return True

def make_tmline_ticks(tmline, t0=dt.now(), datetime_format='%H:%M\n%m/%d', gap_length=6, unit='hours', **kwags):
    tmline_dt = np.array(sorted(tmline))
    if(tmline.shape[0]<1):
        return [], []
    xticks = list(np.arange(tmline_dt[0],tmline_dt[-1],gap_length))
    # xticks = list(range(int(tmline[0])-1,int(tmline[-1])+1,gap_length))
    xticklabels = list(map(lambda x:(t0+td(**{unit:x})).strftime(datetime_format), xticks))
    return xticks, xticklabels
    

def read_pid_file(pid_file, default=None):
    pid = default
    if(isinstance_not_empty(pid_file, str)):
        return pid
    if(not os.path.isfile(pid_file)):
        return pid
    # 打开文件，读取内容，然后关闭文件
    with open(pid_file, 'r') as file:
        pid = file.read().strip()
    
    try:
        # 将读取的字符串转换为整数
        pid = int(pid)
        print(f"The PID read from the file {pid_file} is: {pid}")
    except:
        pass
    return pid

def check_pid_running(pid, pid_file=None):
    """Check if there is any running process that contains the given name."""
    pid = pid if(isinstance(pid, int)) else read_pid_file(pid_file)
    for proc in psutil.process_iter(['pid']):
        try:
            if proc.info['pid']==pid:
                return True
        except:
            pass
    return False

def socket_send_data_to_server(data, server_ip, server_port, unicode='utf-8', max_str_len=1024):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    client_socket.sendall(json.dumps(data).encode(unicode))
    client_socket.close()
    return True

def socket_send_data_to_server_and_recieve(data, server_ip, server_port, unicode='utf-8', max_str_len=1024):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    client_socket.sendall(json.dumps(data).encode(unicode))
    response = client_socket.recv(max_str_len)
    print("Received from server:", str(response.decode(unicode))[:200])
    client_socket.close()
    return response.decode(unicode)

def pid_monitor(pid, pid_file=None, sleep_time=10, messenger=None, **kwags):
    # print(*sorted(list(map(lambda x: (x.info['cmdline'], LOGger.mylist(x.info['cmdline']).find(process_to_monitor, strictly=True)!=None), 
    #                                          psutil.process_iter(['pid', 'name','cmdline'])))), sep='\n')
    pid = pid if(isinstance(pid, int)) else read_pid_file(pid_file)
    if(not isinstance(pid, int)):
        return
    messenger = messenger if(isinstance(kwags.get('messenger'), Messenger)) else m_messenger
    addlog = kwags.get('addlog', addloger(logfile=kwags.get('logfile','')))
    addlog('start monitor:%s'%pid)
    log_counter = {}
    while True:
        if check_pid_running(pid, pid_file=pid_file):
            addlog(f"{pid} is running", log_counter=log_counter, log_counter_stamp='exem', 
                   reset_log_counter=True, log_when_unreset=True)
        else:
            now = dt.now().strftime('%Y%m%d %H:%M:%S')
            addlog(f"{pid} is not running", stamps=[now], log_counter=log_counter, log_counter_stamp='exem')
            if(kwags.get('recipient')):
                recipient = kwags.get('recipient', '')
                try:
                    messenger.send_email(recipient, '[%s]exe aborted!!!'%pid,'[%s]unknown reason....'%now)
                except:
                    addlog('sending failed!!!!', log_counter=log_counter, log_counter_stamp='send failed')
                else:
                    addlog('sending successful!!!!', log_counter=log_counter, log_counter_stamp='send failed',
                           reset_log_counter=True, log_when_unreset=True)
        time.sleep(sleep_time)  # 每10秒檢查一次
#%%
class STRUCTURE:
    def __init__(self, **kwags):
        for k,v in kwags.items():
            setattr(self, k, v)
            
class myArgParser(argparse.ArgumentParser):
    def __init__(self, key_stgs=None):
        super().__init__()
        self.key_stgs = key_stgs
        self.containing_transform = {}
        self.criterion = {}
        
    def add_argument(self, *args, arg_full_name_stamp='--', criterion=None, criterion_kwags=None, criterion_return=True, transform=None, 
                     transform_kwags=None, item_sep='=', **kwags):
        arg_name = None
        for arg in args:
            if(arg.find(arg_full_name_stamp)>-1):
                arg_name = arg.replace(arg_full_name_stamp, '')
                break
        if(not isinstance(arg_name, str)):
            return
        #設定防呆
        criterion = (lambda x:os.path.exists(x) if(isinstance_not_empty(x, str)) else x) if(
            (kwags.get('type', None) in ['path','dir','file']) and criterion==None) else criterion
        if(criterion):
            criterion_kwags = criterion_kwags if(isinstance(criterion_kwags, dict)) else {}
            self.criterion.update({arg_name:lambda x:criterion(x, **criterion_kwags)})
        #設定要轉換字典
        if(kwags.get('action')=='dict'):
            self.containing_transform.update({arg_name:self.dict_transfrom})
            kwags.update({'action':'append'})
            type_trans_byterm = kwags.get('type', str)
            def type_trans(s):
                k,v = (s.split(item_sep)[:2] if(len(s.split(item_sep))>1) else (s,s)) if(item_sep in s) else (s,s)
                return {k:type_trans_byterm(v)}
            kwags.update({'type':type_trans})
        #設定遇到關鍵字要轉換
        key_stgs = execute('key_stgs', kwags, self, not_found_alarm=False, default=None)
        key_stgs_translation = execute('key_stgs_translation', kwags, self, not_found_alarm=False, default=None)
        if(key_stgs):
            self.containing_transform.update({arg_name:self.dict_transfrom})
            key_stgs_process(arg_name, self, key_stgs=key_stgs, key_stgs_translation=key_stgs_translation)
        #設定自定義轉換
        if(transform):
            transform_kwags = transform_kwags if(isinstance(transform_kwags, dict)) else {}
            self.containing_transform.update({arg_name:(lambda x:transform(x, **transform_kwags))})
        super().add_argument(*args, **kwags)
            
    def dict_transfrom(self, container):
        ret = {}
        for item in container:
            ret.update(item)
        return ret
        
    def parse_args(self):
        args = super().parse_args()
        
        check_list = []
        check_list += list(self.criterion.keys())
        check_list += list(self.containing_transform.keys())
        check_list = np.unique(check_list)
        
        for k in check_list:
            if(not isinstance(self.containing_transform.get(k), type(None)) and hasattr(args, k)):
                arg = getattr(args, k)
                try:
                    setattr(args, k, self.containing_transform[k](arg))
                except Exception as e:
                    exception_process(e, logfile='',stamps=['parse_args', k])
            if(not isinstance(self.criterion.get(k), type(None)) and hasattr(args, k)):
                arg = getattr(args, k)
                if(not self.criterion[k](arg)):
                    addlog('add_argument criterion error:\n%s'%(str(arg)[:200]), logfile='', stamps=[k])
                    sys.exit(1)
        return args

class ConfigAgent:
    def __init__(self, config_source_file, config_keys, *objects, renew_passtime=30*60, renew_passtimes=None,
                 not_found_alarm=False, stamps=None, log_when_renew=True, **kwags):
        self.stamps = stamps
        self.config_keys = config_keys if(isinstance(config_keys, list)) else (
            load_json(config_source_file).keys() if(os.path.exists(config_source_file)) else [])
        self.objects = objects
        self.not_found_alarm = not_found_alarm
        # self.click = click
        # self.click_stamp = click_stamp if(isinstance(click_stamp, str)) else stamp_process('',self.stamps,'','','','_')
        self.config_source_file = config_source_file
        timestamp = os.path.getmtime(self.config_source_file)
        self.prev_json_time = dt.fromtimestamp(timestamp)
        self.applicated = False
        self.addlog = kwags.get('addlog', addloger(logfile=kwags.get('logfile','')))
        self.log_when_renew = log_when_renew
        self.stop_flag = False
        self.start(renew_passtime=renew_passtime)
        
    def give(self, *objects):
        objects = objects if(objects) else self.objects
        ret = {}
        get_live_params(self.config_source_file, *objects, not_found_alarm = self.not_found_alarm, 
                        prev_json_time=self.prev_json_time,#dt.fromtimestamp(os.path.getmtime(self.config_source_file)),
                        config_keys=self.config_keys, stamps=self.stamps, log_when_renew=self.log_when_renew, ret=ret)
        if(isinstance(ret.get('prev_json_time'), dt)):
            self.prev_json_time = dcp(ret['prev_json_time'])
            self.applicated = False
        
    def give_periodly(self):
        start_time = dt.now() if(self.renew_passtime) else None
        while(not self.stop_flag):
            if(self.renew_passtime):
                if((dt.now() - start_time).total_seconds() < self.renew_passtime):
                    continue
                start_time = dt.now()
            self.give()
            
    def stop(self):
        self.stop_flag = True
        self.g.join()
        
    def start(self, **kwags):
        renew_passtime = kwags.get('renew_passtime', getattr(self, 'renew_passtime', None))
        if(not isinstance(astype(renew_passtime), type(None))):
            self.stop_flag = False
            self.renew_passtime = astype(renew_passtime)
            self.renew_passtime = max(self.renew_passtime, 10)
            self.g = threading.Thread(target=self.give_periodly)
            self.g.start()
            return True
        else:
            return False
    
    def restart(self, **kwags):
        self.stop()
        self.start(**kwags)
        

class myAttributeAgent:
    def __init__(self, buffer=None, stamps=None, buffer_ubd=None, first_pop_index=0, exp_fd='.', save_types=None,
                 cleaning_waitng_time=1, rewrite=True, **kwags):
        self.stamps = stamps if(isinstance(stamps, list)) else []
        self.buffer = buffer if(isinstance(buffer, dict)) else {}
        self.buffer_list = mylist([])
        self.addlog = execute('addlog', kwags, default=addloger(logfile=''), not_found_alarm=False)
        self.buffer_ubd = buffer_ubd
        self.first_pop_index = first_pop_index
        self.exp_fd = exp_fd if(isinstance(exp_fd, str)) else '.'
        self.save_types = save_types if(isinstance(save_types, list)) else ['csv']
        self.rewrite = rewrite
        self.buffer_locked = False
        self.stop_flag = False
        self.cleaning_waitng_time = astype(cleaning_waitng_time, d_type=float, default=1.0)
        self.start(cleaning_waitng_time=cleaning_waitng_time)
            
    def update(self, stamp, *args, package=None, stamps=None, inplace_index=0, inplace_stamp=None, stamp_for_file=False):
        if(self.buffer_locked):
            return True
        stamp = stamp_process('',stamps,'','','','_',for_file=stamp_for_file) if(isinstance(stamps, list)) else stamp
        stamp = stamp if(isinstance(stamp, str)) else ''
        if(len(args)==1):
            if(isinstance(args[0], dict)):
                package = args[0]
            else:
                return False
        if(package==None):
            if(len(args)/2!=len(args)//2):
                self.addlog('len of args not even:%d'%len(args), stamps=self.stamps+[stamp])
                return False
            keys = args[0:len(args):2]
            np_args = np.array(keys)
            key_ill = np.array([not isinstance(k,str) and astype(k,defualt=None)==None for k in keys])
            if(key_ill.any()):
                self.addlog('there is nonnumber and non str in keys:%s'%np_args[np.where(key_ill)[0]], 
                            stamps=self.stamps+[stamp])
                return False
            values = args[1:len(args):2]
            package = dict(zip(*(keys, values)))
        if(stamp in self.buffer):
            self.buffer.get(stamp).update(package)
        else:
            if(isinstance(self.buffer_ubd, int)):
                self.pop(index=inplace_index, stamp=inplace_stamp)
            self.buffer.update({stamp:package})
            self.buffer_list.append(stamp)
        return True
    
    def pop(self, index=0, stamp=None, default=None):
        if(stamp in self.buffer):
            default = self.buffer.pop(stamp)
            stamp_index = self.buffer_list.find(stamp)
            self.buffer_list.pop(stamp_index)
        elif(index in self.buffer):
            default = self.buffer.pop(index)
            stamp_index = self.buffer_list.find(index)
            self.buffer_list.pop(stamp_index)
        elif(isinstance(index, int)):
            if(abs(index)<len(self.buffer_list)):
                stamp = self.buffer_list[index]
                default = self.buffer.pop(stamp)
                self.buffer_list.pop(index)
        return default
            
    def clear(self):
        self.buffer_locked = True
        self.buffer.clear()
        self.buffer_list.clear()
        self.buffer_locked = False
        
    def replace(self, stamp, package, stamps=None, stamp_for_file=False):
        stamp = stamp_process('',stamps,'','','','_',for_file=stamp_for_file) if(isinstance(stamps, list)) else stamp
        stamp = stamp if(isinstance(stamp, str)) else ''
        self.buffer.update({stamp:package})
        
    def cleaning(self):
        start_time = dt.now() if(self.cleaning_waitng_time) else None
        while(not self.stop_flag):
            if(self.cleaning_waitng_time):
                if((dt.now() - start_time).total_seconds() < self.cleaning_waitng_time):
                    continue
                start_time = dt.now()
            self.save(self.exp_fd, self.save_types, rewrite = self.rewrite) if(self.save_types) else None
            self.clear()
            # self.pop(self.first_pop_index)
            
    def export(self):
        return self.buffer
    
    def export_and_clear(self):
        ret =  dcp(self.buffer)
        self.clear()
        return ret
    
    def save(self, exp_fd=None, save_types=None, rewrite=False):
        buffer = self.export()
        if(not buffer):
            return True
        save_types = save_types if(isinstance(save_types, list)) else []
        stamp = stamp_process('',['attr'] + self.stamps + [dt.now().strftime('%Y%m%d')],'','','','-',for_file=1)
        try:
            save(buffer, exp_fd=exp_fd, fn='%s-log'%stamp, save_types=save_types, rewrite=rewrite)
        except Exception as e:
            self.stop()
            exception_process(e, logfile='', stamps=[self.save.__name__]+self.stamps)
            return False
        return True
    
    def collect_data(self, ret=None):
        ret = ret if(isinstance(ret, dict)) else {}
        ret['data'] = self.export()
        return True
    
    def stop(self):
        self.stop_flag = True
        self.c.join()
        
    def start(self, **kwags):
        cleaning_waitng_time = kwags.get('cleaning_waitng_time', getattr(self, 'cleaning_waitng_time', None))
        if(not isinstance(astype(cleaning_waitng_time), type(None))):
            self.stop_flag = False
            self.cleaning_waitng_time = astype(cleaning_waitng_time)
            self.cleaning_waitng_time = max(self.cleaning_waitng_time, 10)
            self.c = threading.Thread(target=self.cleaning)
            self.c.start()
            return True
        else:
            return False

class myThreadAgent:
    def __init__(self, target=None, target_core=None, stamps=None, live_buffer=None, 
                 time_waiting=1, feedback_break=type(None), time_retry=None, retry_ubd=1,
                 live_ret=None, immediate_start=False, log_counter=None, **kwags):
        self.stamps = stamps if(isinstance(stamps, list)) else []
        self.target = target
        self.target_core = target_core
        self.log_counter = log_counter if(isinstance(log_counter, dict)) else {}
        self.live_buffer = live_buffer if(isinstance(live_buffer, dict)) else {}
        self.live_buffer.update({'log_counter':self.log_counter})
        time_waiting = astype(time_waiting, default=None)
        self.time_waiting = time_waiting if(isinstance(time_waiting, float)) else None
        time_retry = astype(time_retry, default=None)
        self.time_retry = time_retry if(isinstance(time_retry, float)) else 1
        retry_ubd = astype(retry_ubd, d_type=int, default=None)
        self.retry_ubd = retry_ubd if(isinstance(retry_ubd, int)) else None
        self.feedback_break = feedback_break
        self.event = threading.Event()
        self.name = kwags.get('name', None)
        self.args = kwags.get('args', [])
        self.kwargs = kwags.get('kwargs', {})
        self.daemon = kwags.get('daemon', True)
        self.start() if(immediate_start) else None
    
    def target_(self, *args, **kwargs):
        if(self.target_core!=None):
            retry = 0
            start_time = dt.min if(self.time_waiting) else None
            while(not self.event.is_set()):
                if(self.time_waiting):
                    if((dt.now() - start_time).total_seconds() < self.time_waiting):
                        continue
                try:
                    feedback = self.target_core(**self.live_buffer)
                    if(self.time_waiting):
                        start_time = dt.now()
                    if(feedback==self.feedback_break):
                        break
                except Exception as e:
                    exception_process(e, logfile=getattr(self, 'logfile', ''), stamps=self.stamps)
                    if(isinstance(self.retry_ubd, int)):
                        retry += 1
                        if(retry > self.retry_ubd):
                            break
                    time.sleep(self.time_retry)
                    continue
                    
        elif(self.target!=None):
            return self.target(*args, event=self.event, **kwargs)
        else:
            pass
    
    def stop(self):
        self.event.set()
        self.t.join() if(isinstance(getattr(self, 't', None), threading.Thread)) else None
        
    def start(self, **kwags):
        self.event.clear()
        self.t = threading.Thread(target=self.target_, name=self.name, daemon=self.daemon, args=self.args, kwargs=self.kwargs)
        self.t.start()
        
    def restart(self):
        self.stop()
        self.start()

class myFileRemover:
    def __init__(self, target, period_seconds=24*60*60, sleep_period_seconds=None, 
                 is_target_selfdelete=False, target_extfiletype=None,
                 stamps=None, **kwags):
        self.target = target
        self.period_seconds = astype(period_seconds)
        self.period_seconds = max(self.period_seconds, 60)
        self.sleep_period_seconds = sleep_period_seconds if(astype(sleep_period_seconds)!=None) else dcp(self.period_seconds)
        self.is_target_selfdelete = is_target_selfdelete
        self.target = target
        self.target_extfiletype = target_extfiletype
        self.addlog = kwags.get('addlog', addloger(logfile=kwags.get('logfile','')))
        self.event = threading.Event()
        self.start(period_seconds=period_seconds)
            
    def execute(self):
        removefile_in_region(self.target, period_seconds=self.period_seconds,
                             is_target_selfdelete=self.is_target_selfdelete, target_extfiletype=self.target_extfiletype)
        
    def execute_periodly(self):
        while(not self.event.is_set()):
            self.execute()
            self.event.wait(self.sleep_period_seconds)
            
    def stop(self):
        self.event.set()
        
    def start(self, **kwags):
        period_seconds = kwags.get('period_seconds', getattr(self, 'period_seconds', None))
        if(not isinstance(astype(period_seconds), type(None))):
            self.event.clear()
            self.period_seconds = astype(period_seconds)
            self.period_seconds = max(self.period_seconds, 60)
            self.ec = threading.Thread(target=self.execute_periodly)
            self.ec.start()
            return True
        else:
            return False
    
    def restart(self, **kwags):
        self.stop()
        self.start(**kwags)
        
class Messenger:
    def __init__(self, sender, password, SMTP_SERVER = 'smtp-mail.outlook.com', SMTP_PORT = 587, delivered_logfile='LOGger_messenger.json', 
                 **kwags):
        self.SMTP_SERVER = SMTP_SERVER
        self.SMTP_PORT = SMTP_PORT
        self.sender = sender
        self.password = password
        self.delivered_logfile = delivered_logfile
        
    def send_email(self, recipient, subject='', body='', delivered_missions_ubd=1, **kwags):
        buffer = load_json(self.delivered_logfile)
        delivered_missions = buffer.get('delivered_missions', [])
        addlog_ = kwags.get('addlog', addloger(logfile=kwags.get('logfile','')))
        if(len(delivered_missions)>=delivered_missions_ubd):
            addlog_('delivered_missions is full:%d'%delivered_missions_ubd)
            return
        
        addlog_(stamp_process('',[recipient, subject],'','','',' * '), stamps=['send e-mail'])
        sender = kwags.get('sender', self.sender)
        password = kwags.get('password', self.password)
        SMTP_SERVER = kwags.get('SMTP_SERVER', self.SMTP_SERVER)
        SMTP_PORT = kwags.get('SMTP_PORT', self.SMTP_PORT)
        
        msg = MIMEText(body)
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject
        
        smtp_server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        smtp_server.starttls()
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipient, msg.as_string())
        smtp_server.quit()
        
        delivered_missions.append('||'.join([recipient, subject, dt.now().strftime('%Y%m%d %H:%M:%S')]))
        buffer.update({'delivered_missions':delivered_missions})
        CreateFile(self.delivered_logfile, lambda f:save_json(buffer, file=f))
        addlog_(stamp_process('',[recipient, subject],'','','',' * '), stamps=['send e-mail complete'])

m_sender = load_json('LOGger_messenger.json').get('sender')
m_password = load_json(load_json('LOGger_messenger.json').get('password_file','')).get('e')
m_messenger = None
if(isinstance_not_empty(m_sender, str) and isinstance_not_empty(m_password, str)):
    m_messenger = Messenger(m_sender, m_password)
    print("type(m_messenger)",type(m_messenger))
    
class myDebuger(mydict):
    def __init__(self, *args, stamps=None, fn=None, file=None, exp_fd='.', maxlen_str=500, **kwags):
        super().__init__(*args, **kwags)
        self.stamps = (stamps if(isinstance(stamps, list)) else [])+['debug']
        self.exp_fd = exp_fd
        self.fn = fn if(isinstance(fn, str)) else '%s.pkl'%stamp_process('',self.stamps,'','','','_',for_file=True)
        self.file = file if(isinstance(file, str)) else self.fn
        self.maxlen_str = maxlen_str
        self.messeges = {}
        
    def __str__(self):
        temp = {}
        for k,v in self.items():
            if(isinstance(v, dict)):
                temp[parse(k)] = '\n'+str(myDebuger(v))[:self.maxlen_str]
                continue
            if(isinstance(v,(list,tuple))):
                typeClass = type(v)
                temp[parse(k)] = '\n'+parse(typeClass([parse(x) for x in v]))
                continue
            temp[parse(k)] = parse(v)[:self.maxlen_str]
        return stamp_process('',temp,':','[',']','\n',digit=4)
        
    def listen(self, msg, stamps=None, **kwags):
        stamps = stamps if(isinstance(stamps, list)) else []
        stamp = stamp_process('',stamps,'','','','_')
        stamp = stamp if(isinstance_not_empty(stamp, str)) else 'core'
        if(not stamp in self.messeges): self.messeges[stamp] = []
        self.messeges[stamp].append(msg)
        return True
    
    def reporting(self, **kwags):
        msgsTemp = {}
        for k,v in self.messeges.items():
            msgTemp = dcp(stamp_process('',v,adjoint_sep='\n'))
            msgsTemp[k] = dcp(msgTemp)
        return msgsTemp
    
    def messege(self, logfile='', **kwags):
        msgs = self.reporting()
        msg = stamp_process('',msgs,adjoint_sep='\n')
        addlog(msg, colora=WARNING, logfile=logfile, **kwags)
        return msg
    
    def report(self, **kwags):
        msgs = self.reporting()
        return pd.DataFrame(msgs)
    
    def save(self, file=None, **kwags):
        print(FAIL+str(self))
        file = file if(isinstance_not_empty(file, str)) else self.file
        addlog('save to:', file, logfile='debugList.txt', colora=FAIL)
        joblib.dump(dict(self), file)
    
    def dump(self, file=None, **kwags):
        self.save(file=file, **kwags)
        sys.exit(1)
        
    def dumpDefault(self, file=None, **kwags):
        if(len(self)==0):
            return 
        self.dump()
        
    def updateDump(self, ofWhat=None, file=None, **kwags):
        self.update(ofWhat) if(isinstance(ofWhat, dict)) else None
        self.dump(file=file, **kwags)