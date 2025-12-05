import requests
import pytz
from datetime import datetime
import re
import concurrent.futures

# =======================================================
# 核心时间验证模块
# =======================================================
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 定义多个不同来源的 API (国内源优先)
API_SOURCES = {
    # 淘宝 (返回时间戳，极快，国内首选)
    'Taobao': "http://api.m.taobao.com/rest/api3.do?api=mtop.common.getTimestamp",
    # 苏宁 (返回标准时间字符串，稳定)
    'Suning': "http://quan.suning.com/getSysTime.do",
    # 腾讯 (返回 JSON/Text，备用)
    'Tencent': "http://vv.video.qq.com/checktime?otype=json",
    # 原有接口 (作为最后的备用，国外源)
    'WorldTime': "http://worldtimeapi.org/api/timezone/Asia/Shanghai"
}

def fetch_time_worker(api_url, timeout=3):
    """
    工作函数：针对不同的 API URL 使用不同的解析逻辑，返回带时区的北京时间对象。
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(api_url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        dt_beijing = None

        # --- 1. 淘宝 API 解析 ---
        if "taobao" in api_url:
            data = response.json()
            # 淘宝返回的是毫秒级时间戳字符串
            timestamp = float(data['data']['t']) / 1000.0
            dt_utc = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
            dt_beijing = dt_utc.astimezone(BEIJING_TZ)

        # --- 2. 苏宁 API 解析 ---
        elif "suning" in api_url:
            data = response.json()
            # 苏宁返回 "yyyy-MM-dd HH:mm:ss"
            time_str = data['sysTime2']
            dt_raw = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            dt_beijing = BEIJING_TZ.localize(dt_raw)

        # --- 3. 腾讯 API 解析 ---
        elif "qq.com" in api_url:
            content = response.text
            # 腾讯可能返回 QZOutputJson={"s":"...","t":176...};
            match = re.search(r'"t":(\d+)', content) 
            if match:
                timestamp = float(match.group(1))
                dt_utc = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.utc)
                dt_beijing = dt_utc.astimezone(BEIJING_TZ)
            else:
                # 备用匹配日期格式
                match_date = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', content)
                if match_date:
                    dt_raw = datetime.strptime(match_date.group(0), '%Y-%m-%d %H:%M:%S')
                    dt_beijing = BEIJING_TZ.localize(dt_raw)

        # --- 4. 原 WorldTimeAPI 解析 ---
        elif "worldtimeapi" in api_url:
            data = response.json()
            time_str = data['datetime'].split('.')[0].replace('T', ' ')
            dt_raw = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            if "UTC" in api_url:
                dt_utc = pytz.utc.localize(dt_raw)
                dt_beijing = dt_utc.astimezone(BEIJING_TZ)
            else:
                dt_beijing = BEIJING_TZ.localize(dt_raw)

        return dt_beijing

    except Exception as e:
        # print(f"API {api_url} 失败: {e}") # 调试用，实际运行可静默
        return None

def get_network_time():
    """
    并发获取网络时间，返回最快响应的 datetime 对象（带时区）。
    如果所有 API 都失败，返回 None。
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(API_SOURCES)) as executor:
        future_to_url = {executor.submit(fetch_time_worker, url): name for name, url in API_SOURCES.items()}
        
        # as_completed 返回的是迭代器，一旦有任务完成就立即返回
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                dt = future.result()
                if dt:
                    return dt
            except Exception:
                continue
    return None

def is_within_date_range(start_date_str, end_date_str):
    """
    检查当前网络时间是否在指定范围内。
    支持格式: 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM'
    返回: (bool, str) -> (是否在范围内, 提示信息)
    """
    current_time = get_network_time()
    if not current_time:
        # 强制使用网络时间，如果获取失败直接返回错误
        return False, "NETWORK_ERROR"
    
    try:
        # 尝试解析带时间的格式，如果失败则回退到仅日期格式
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M')
        except ValueError:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            
        start_date = BEIJING_TZ.localize(start_date)
        
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M')
            end_date = BEIJING_TZ.localize(end_date)
        except ValueError:
            # 如果只有日期，默认截止到当天的 23:59:59
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            end_date = BEIJING_TZ.localize(end_date).replace(hour=23, minute=59, second=59)

        if current_time < start_date:
            return False, "NOT_STARTED"
        
        if current_time > end_date:
            return False, "EXPIRED"
            
        return True, "VALID"
        
    except ValueError:
        return False, "日期格式配置错误。"

if __name__ == "__main__":
    # 测试
    print("正在获取时间...")
    now = get_network_time()
    print(f"当前网络时间: {now}")
    valid, msg = is_within_date_range("2023-01-01", "2030-12-31")
    print(f"检查结果: {valid}, {msg}")
