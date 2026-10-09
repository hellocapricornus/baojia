"""baojia 报价机器人 - 配置模块

所有配置项均以 baojia 前缀命名，从项目根目录的 baojia.env 文件加载，
未提供 baojia.env 时直接读取系统环境变量。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BAOJIA_BASE_DIR = Path(__file__).resolve().parent

# 加载 baojia.env（若存在）
load_dotenv(BAOJIA_BASE_DIR / "baojia.env")


def baojia_parse_int_list(baojia_raw):
    """把逗号/分号分隔的数字字符串解析为整数集合。"""
    baojia_result = set()
    for baojia_part in str(baojia_raw or "").replace(";", ",").split(","):
        baojia_part = baojia_part.strip()
        if baojia_part.isdigit():
            baojia_result.add(int(baojia_part))
    return baojia_result


# Telegram 机器人 Token
baojia_BOT_TOKEN = os.getenv("baojia_BOT_TOKEN", "").strip()

# 超级管理员 Telegram ID 集合
baojia_ADMIN_IDS = baojia_parse_int_list(os.getenv("baojia_ADMIN_IDS", ""))

# SQLite 数据库路径
baojia_DB_PATH = os.getenv("baojia_DB_PATH", "").strip() or str(
    BAOJIA_BASE_DIR / "baojia_data" / "baojia_bot.db"
)

# 日志级别
baojia_LOG_LEVEL = os.getenv("baojia_LOG_LEVEL", "INFO").strip().upper()

# 报价类型
BAOJIA_TYPE_COLLECT = "collect"  # 代收
BAOJIA_TYPE_PAY = "pay"          # 代付
BAOJIA_TYPE_LABELS = {
    BAOJIA_TYPE_COLLECT: "代收",
    BAOJIA_TYPE_PAY: "代付",
}

# 预设选项（录入时以按钮形式提供，也支持手动输入）
BAOJIA_PRESET_MATERIALS = ["大区", "换汇杀", "拦截", "刷单", "精料", "滲透", "盗刷"]  # 料性
BAOJIA_PRESET_ACCOUNTS = ["公户", "私户", "卡", "钱包"]   # 账户类别
BAOJIA_PRESET_SETTLES = ["拖算", "进算"]                 # 结算方式

# 比价基准：统一以 100 万当地货币折算 USDT
BAOJIA_BASE_AMOUNT = 1_000_000

# 群内展开分页：每页报价条数
BAOJIA_PAGE_SIZE = 6
