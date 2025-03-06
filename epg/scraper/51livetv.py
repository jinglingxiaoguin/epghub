from datetime import datetime, date, timedelta
import requests
from bs4 import BeautifulSoup
from epg.model import Channel, Program  # 假设你已经定义了 Channel 和 Program 类

# 基础 URL
baseurl = "https://www.51livetv.com/jmb/"

# 请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def grab_programs(channel_id: str, need_weekday: int) -> tuple:
    """
    从 51livetv.com 抓取节目表。
    返回: (节目内容, 日期) 的元组
    参数:
        channel_id (str): 频道 ID。
        need_weekday (int): 星期几（0 表示星期一，6 表示星期日）。
    """
    channel_baseurl = baseurl + channel_id + "_w" + str(need_weekday) + "/"
    try:
        res = requests.get(channel_baseurl, headers=headers, timeout=5)
    except requests.RequestException:
        return False

    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        try:
            # 抓取节目列表
            content = soup.find("ul", class_="program_time_tabs_item_ul").find_all("li")
            # 抓取日期（假设页面中有日期信息）
            date_str = soup.find("div", class_="date_info").text.strip()  # 假设日期在某个 div 中
            date = datetime.strptime(date_str, "%Y年%m月%d日").date()
        except AttributeError:
            return False
    else:
        return False

    return (content, date)


def parse_programs(content: tuple) -> list:
    """
    解析网页内容，提取节目列表。
    返回: 节目列表，每个节目包含 (标题, 开始时间) 的字典。
    参数:
        content (tuple): 网页内容 (节目内容, 日期)。
    """
    date = content[1]
    programs = []
    for line in content[0]:
        time_element = line.find("span", class_="time")
        title_element = line.find("a", class_="name link") if line.find("a", class_="name link") else line

        if time_element and title_element:
            time_str = time_element.text.strip()
            title = title_element.text.strip()

            # 解析时间
            start_time = datetime.strptime(time_str, "%H:%M").time()
            start = datetime.combine(date, start_time)

            # 添加到节目列表
            programs.append({"title": title, "start": start})

    return programs


def update(channel: Channel, scraper_id: str | None = None, dt: date = datetime.today().date()):
    """
    更新频道的节目表。
    返回: 成功返回 True，失败返回 False。
    参数:
        channel (Channel): 要更新的频道对象。
        scraper_id (str): 频道 ID。
        dt (date): 要更新的日期。
    """
    now_date = datetime.now().date()
    request_date = dt
    delta = request_date - now_date
    now_weekday = now_date.weekday()
    need_weekday = now_weekday + delta.days

    if delta.days < 0:
        if abs(delta.days) > now_weekday:
            return False
    if delta.days > 0:
        if delta.days > 6 - now_weekday:
            return False

    # 抓取节目
    bs_programs = grab_programs(scraper_id, need_weekday)
    if not bs_programs:
        return False

    # 解析节目
    programs = parse_programs(bs_programs)
    if len(programs) == 0:
        return False

    # 清空频道当天的节目
    channel.flush(dt)

    # 更新频道节目
    temp_program = None
    for program in programs:
        title = program["title"]
        starttime = program["start"]
        if temp_program is not None:
            temp_program.end_time = starttime
            channel.programs.append(temp_program)
        temp_program = Program(title, starttime, None, channel.id + "@51livetv.com")

    # 设置最后一个节目的结束时间
    if temp_program is not None:
        temp_program.end_time = temp_program.start_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        channel.programs.append(temp_program)

    return True