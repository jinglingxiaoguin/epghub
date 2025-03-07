from datetime import datetime, date, timedelta
import requests
from bs4 import BeautifulSoup
from epg.model import Channel, Program  # 假设你已经定义了 Channel 和 Program 类
import re

# 基础 URL
baseurl = "https://sports8.cc/program/"

# 请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def grab_programs(channel_id: str, need_weekday: int) -> tuple:
    """
    从 sports8.cc 抓取节目表。
    返回: (节目内容, 日期) 的元组
    参数:
        channel_id (str): 频道 ID。
        need_weekday (int): 星期几（1 表示周一，7 表示周日）。
    """
    channel_baseurl = baseurl + channel_id + "/" + str(need_weekday) + ".htm"
    try:
        res = requests.get(channel_baseurl, headers=headers, timeout=5)
        if res.status_code != 200:
            return False
    except requests.RequestException:
        return False

    if res.status_code == 200:
        soup = BeautifulSoup(res.text, "html.parser")
        try:
            # 抓取节目列表
            content = soup.find("div", id="Weepgprogram_epgInfo").find_all("p")
            # 抓取日期（假设页面中有日期信息）
            try:
                date_str = soup.find("div", class_="date_info").text.strip()
                date = datetime.strptime(date_str, "%Y年%m月%d日").date()
            except AttributeError:
                # 如果页面中没有日期信息，根据当前日期推算
                now_date = datetime.now().date()
                delta = timedelta(days=need_weekday - now_date.weekday() - 1)
                date = now_date + delta
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
        time_element = line.find("em", class_="time")
        title_element = line

        if time_element and title_element:
            time_str = time_element.text.strip()
            title = title_element.text.strip()

            # 清理节目名称中的时间前缀
            if time_str in title:
                title = title.replace(time_str, "").strip()

            # 清理节目名称中的【直播中】字样
            if "【直播中】" in title:
                title = title.replace("【直播中】", "").strip()

            # 检查时间格式是否为 HH:MM
            if re.match(r"^\d{2}:\d{2}$", time_str):
                try:
                    # 解析时间
                    start_time = datetime.strptime(time_str, "%H:%M").time()
                    start = datetime.combine(date, start_time)

                    # 添加到节目列表
                    programs.append({"title": title, "start": start})
                except ValueError:
                    continue  # 跳过无效时间格式
            else:
                continue  # 跳过无效时间格式

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
    now_weekday = now_date.weekday() + 1  # 转换为 1-7 的星期格式
    need_weekday = now_weekday + delta.days

    # 确保 need_weekday 在 1 到 7 之间
    if need_weekday < 1:
        need_weekday += 7
    elif need_weekday > 7:
        need_weekday -= 7

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
        temp_program = Program(title, starttime, None, channel.id + "@sports8.cc")

    # 设置最后一个节目的结束时间
    if temp_program is not None:
        temp_program.end_time = temp_program.start_time.replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
        channel.programs.append(temp_program)

    return True
