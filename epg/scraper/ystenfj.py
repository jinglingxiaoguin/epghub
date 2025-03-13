from epg.model import Channel, Program
from datetime import datetime, date, timezone
import requests
import json
from . import headers, tz_shanghai

def update(
    channel: Channel, scraper_id: str | None = None, dt: date = datetime.today().date()
) -> bool:
    # 根据传入的 scraper_id 或者 channel.id 获取频道的 UUID
    channel_id = channel.id if scraper_id is None else scraper_id
    
    # 格式化日期，准备请求参数
    start_date = dt.strftime("%Y%m%d")
    end_date = dt.strftime("%Y%m%d")
    
    # 构造 API 请求 URL
    url = f"https://wxtv.fja.bcs.ottcn.com/wxlive/cms-lvp-epg/lvps/getAllProgramlist?uuid={channel_id}&startDate={start_date}&endDate={end_date}&cancelId=1714195200000&t=1714195200000&abilityString=%7B%22abilities%22%3A%5B%22Playable-YOUKU%7CPlayable-IQIYI%7CDL-3rd%22%2C%224K-1%7CtimeShift%7CNxM%22%2C%224K-1%7Ccp-TENCENT%22%5D%2C%22businessGroupIds%22%3A%5B%5D%2C%22deviceGroupIds%22%3A%5B%222081%22%5D%2C%22districtCode%22%3A%22350100%22%2C%22labelIds%22%3A%5B%5D%2C%22ucsUserAbilityRefresh%22%3A%221657268699859%22%2C%22userGroupIds%22%3A%5B%22350000%22%5D%2C%22userLabelIds%22%3A%5B%5D%7D"
    
    try:
        # 发送请求
        res = requests.get(url, headers=headers, timeout=5)
    except:
        print("Fail:", url)
        return False
    
    # 如果响应码不是 200，说明请求失败
    if res.status_code != 200:
        return False
    
    # 解析 JSON 数据
    data = json.loads(res.text)
    
    # 判断返回的 resultCode 是否为 "000"，即请求是否成功
    if data["resultCode"] != "000":
        print("API returned an error:", data.get("resultMessage"))
        return False
    
    # 获取内容部分
    content = data["content"]
    
    # 如果没有找到相关内容，返回 False
    if not content:
        return False
    
    # 提取频道节目数据
    programs_data = content[0]["programs"]  # 假设该频道在第一个列表项中
    
    # 清空该频道的旧节目数据
    channel.flush(dt)
    
    # 遍历节目列表并更新节目数据
    for program in programs_data:
        title = program["programName"]
        start_time = datetime.fromtimestamp(program["startTime"], tz=tz_shanghai)
        end_time = datetime.fromtimestamp(program["endTime"], tz=tz_shanghai)
        
        # 选择合适的播放 URL（这里选择 multicastUrl，作为示例）
        url = program["resolution"][0]["multicastUrl"] if program["resolution"] else ""
        
        # 创建并添加 Program 对象
        channel.programs.append(
            Program(title, start_time, end_time, url)
        )
    
    # 更新频道的元数据
    channel.metadata.update({"last_update": datetime.now(timezone.utc).astimezone()})
    
    return True
