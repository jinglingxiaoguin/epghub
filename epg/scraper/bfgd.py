from epg.model import Channel, Program
from datetime import datetime, date, timezone, timedelta
import requests
import json
from . import headers, tz_shanghai

def update(
    channel: Channel, scraper_id: str | None = None, dt: date = datetime.today().date()
) -> bool:
    # 根据传入的 scraper_id 或者 channel.id 获取频道的 UUID
    channel_id = channel.id if scraper_id is None else scraper_id
    
    # 格式化日期，准备请求参数
    start_time = datetime.combine(dt, datetime.min.time()).replace(tzinfo=tz_shanghai)  # 00:00:00
    end_time = (start_time + timedelta(days=1))  # 24:00:00
    
    # 将日期转换为时间戳
    start_time_ts = int(start_time.timestamp())
    end_time_ts = int(end_time.timestamp())
    
    # 构造 API 请求 URL
    url = f"http://slave.bfgd.com.cn/media/event/get_list?chnlid={channel_id}&pageidx=1&vcontrol=0&attachdesc=1&repeat=1&accesstoken=R5F2408FEU3198804BK78052214IE73560DFP2BF4M340CE68V0Z339CBW1626D4D261E46FEA&starttime={start_time_ts}&endtime={end_time_ts}&pagenum=100&flagposter=0"
    
    try:
        # 发送请求
        res = requests.get(url, headers=headers, timeout=5)
    except Exception as e:
        print(f"Fail: {e}")
        return False
    
    # 如果响应码不是 200，说明请求失败
    if res.status_code != 200:
        return False
    
    # 解析 JSON 数据
    data = json.loads(res.text)
    
    # 判断返回的 total 是否大于 0，即是否有节目数据
    if data["total"] == 0:
        return False
    
    # 获取 event_list 内容部分
    event_list = data["event_list"]
    
    # 清空该频道的旧节目数据
    channel.flush(dt)
    
    # 遍历节目列表并更新节目数据
    for event in event_list:
        title = event["event_name"]
        start_time = datetime.fromtimestamp(event["start_time"], tz=tz_shanghai)
        end_time = datetime.fromtimestamp(event["end_time"], tz=tz_shanghai)
        
        # 创建并添加 Program 对象
        channel.programs.append(
            Program(title, start_time, end_time, "")
        )
    
    # 更新频道的元数据
    channel.metadata.update({"last_update": datetime.now(timezone.utc).astimezone()})
    
    return True
