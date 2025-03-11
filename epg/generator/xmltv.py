from lxml import etree
from epg.model import Channel
from datetime import datetime, timezone, timedelta

def fix_datetime(dt):
    """确保时间统一为 UTC+8"""
    if dt is None:
        return datetime.now(timezone(timedelta(hours=8)))  # 默认返回当前 UTC+8 时间
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone(timedelta(hours=8)))  # 如果没有时区信息，则设置为 UTC+8
    return dt.astimezone(timezone(timedelta(hours=8)))  # 转换为 UTC+8 时区

def write(filepath: str, channels: list[Channel], info: str = "") -> bool:
    root = etree.Element("tv")
    tree = etree.ElementTree(root)
    tree.docinfo.system_url = "xmltv.dtd"
    root.set("generator-info-name", info)

    # 计算最新的更新时间
    last_update_time_list = [
        fix_datetime(channel.metadata.get("last_update"))
        for channel in channels if "last_update" in channel.metadata
    ]
    if last_update_time_list:
        last_update_time = max(last_update_time_list)
        root.set("date", last_update_time.strftime("%Y%m%d%H%M%S %z"))

    # 生成频道信息
    for channel in channels:
        channel_element = etree.SubElement(root, "channel", id=channel.id)
        for name in channel.metadata.get("name", []):
            display_name = etree.SubElement(channel_element, "display-name")
            display_name.text = name

    # 处理节目单
    for channel in channels:
        # **这里修正**: 先转换时间，然后再排序，但保持原始的 program 对象
        for program in channel.programs:
            program.start_time = fix_datetime(program.start_time)
            program.end_time = fix_datetime(program.end_time)

        channel.programs.sort(key=lambda p: p.start_time)

        for program in channel.programs:
            program_element = etree.SubElement(root, "programme",
                                              start=program.start_time.strftime("%Y%m%d%H%M%S %z"),
                                              stop=program.end_time.strftime("%Y%m%d%H%M%S %z"),
                                              channel=channel.id)
            title = etree.SubElement(program_element, "title")
            title.text = program.title
            if program.sub_title:
                sub_title = etree.SubElement(program_element, "sub-title")
                sub_title.text = program.sub_title
            if program.desc:
                desc = etree.SubElement(program_element, "desc")
                desc.text = program.desc

    tree.write(filepath, pretty_print=True, xml_declaration=True, encoding="utf-8")
    return True
