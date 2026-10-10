"""baojia 报价机器人 - 通用工具

权限判定、管理员装饰器、数值解析、报价折算计算、群组链接生成、报价存取等。
所有自定义变量与函数均带 baojia 前缀。
"""

import contextlib
import functools
import html
import re
from datetime import datetime

import baojia_config
import baojia_database

BAOJIA_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
BAOJIA_DISPLAY_FORMAT = "%Y-%m-%d %H:%M"


def baojia_esc(baojia_text):
    """HTML 转义：所有用户输入文本在拼进 HTML 消息前必须经过此函数，
    防止 < > & 等字符破坏排版或注入标签。"""
    return html.escape(str(baojia_text if baojia_text is not None else ""))


def baojia_now():
    """当前时间字符串（存储用，精确到秒）。"""
    return datetime.now().strftime(BAOJIA_DATETIME_FORMAT)


def baojia_display_time(baojia_text):
    """存储时间转展示时间（年月日时分）。"""
    try:
        return datetime.strptime(str(baojia_text), BAOJIA_DATETIME_FORMAT).strftime(BAOJIA_DISPLAY_FORMAT)
    except (TypeError, ValueError):
        return str(baojia_text or "")


def baojia_parse_number(baojia_text):
    """解析正数（>0），非法返回 None。"""
    if baojia_text is None:
        return None
    baojia_clean = str(baojia_text).strip().replace(",", "").replace("，", "")
    if not baojia_clean:
        return None
    try:
        baojia_value = float(baojia_clean)
    except (TypeError, ValueError):
        return None
    if baojia_value != baojia_value or baojia_value <= 0:
        return None
    return baojia_value


def baojia_parse_nonneg(baojia_text):
    """解析非负数（>=0），非法返回 None。手续费、单笔费用允许为 0。"""
    if baojia_text is None:
        return None
    baojia_clean = str(baojia_text).strip().replace(",", "").replace("，", "")
    if not baojia_clean:
        return None
    try:
        baojia_value = float(baojia_clean)
    except (TypeError, ValueError):
        return None
    if baojia_value != baojia_value or baojia_value < 0:
        return None
    return baojia_value


def baojia_parse_int(baojia_text):
    """解析正整数，非法返回 None。"""
    if baojia_text is None:
        return None
    baojia_clean = str(baojia_text).strip()
    if not baojia_clean.isdigit():
        return None
    baojia_value = int(baojia_clean)
    return baojia_value if baojia_value > 0 else None


def baojia_parse_group_id(baojia_text):
    """解析群组 ID。

    支持：
    - -1001234567890（超级群完整 ID）
    - 1234567890（10 位以上纯数字，自动补 -100 前缀）
    - -987654321（普通群负数 ID）
    非法返回 None。
    """
    if baojia_text is None:
        return None
    baojia_clean = str(baojia_text).strip()
    if re.fullmatch(r"-100\d{10,}", baojia_clean):
        return int(baojia_clean)
    if re.fullmatch(r"\d{10,}", baojia_clean):
        return int("-100" + baojia_clean)
    if re.fullmatch(r"-\d{4,}", baojia_clean):
        return int(baojia_clean)
    return None


def baojia_group_link(baojia_group_id):
    """由群组 ID 生成 t.me/c 可点击跳转链接（机器人无需入群/当管理员）。

    -1001234567890 -> https://t.me/c/1234567890
    """
    baojia_text = str(baojia_group_id)
    if baojia_text.startswith("-100"):
        return f"https://t.me/c/{baojia_text[4:]}"
    if baojia_text.startswith("-"):
        return f"https://t.me/c/{baojia_text[1:]}"
    return f"https://t.me/c/{baojia_text}"


def baojia_fmt_number(baojia_value, baojia_digits=2):
    """数值千分位格式化。"""
    try:
        return f"{float(baojia_value):,.{baojia_digits}f}"
    except (TypeError, ValueError):
        return "0." + "0" * baojia_digits


def baojia_fmt_plain(baojia_value):
    """费用/汇率原样展示：整数不带小数点。"""
    try:
        baojia_float = float(baojia_value)
    except (TypeError, ValueError):
        return str(baojia_value)
    return f"{baojia_float:g}"


# ==================== 回调安全回答 ====================

async def baojia_safe_answer(baojia_query, *baojia_args, **baojia_kwargs):
    """安全地回答回调查询：query 过期/无效时静默忽略，不中断后续处理。"""
    try:
        await baojia_query.answer(*baojia_args, **baojia_kwargs)
    except Exception:
        pass


# ==================== 权限 ====================

def baojia_register_user(baojia_user):
    """用户 /start 时登记到 baojia_users。

    新用户默认 is_active=0（待管理员启用），不会自动获得使用权限；
    已存在用户只更新姓名与环境变量管理员角色，不改变其启用状态。
    """
    baojia_is_env_admin = baojia_user.id in baojia_config.baojia_ADMIN_IDS
    baojia_role = "admin" if baojia_is_env_admin else "operator"
    baojia_full_name = f"{baojia_user.first_name or ''} {baojia_user.last_name or ''}".strip()
    baojia_database.baojia_execute(
        """
        INSERT INTO baojia_users(baojia_user_id, baojia_full_name, baojia_role, baojia_is_active, baojia_created_at)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(baojia_user_id) DO UPDATE SET
            baojia_full_name = excluded.baojia_full_name,
            baojia_role = CASE WHEN excluded.baojia_role = 'admin'
                              THEN 'admin' ELSE baojia_users.baojia_role END
        """,
        (baojia_user.id, baojia_full_name or baojia_user.username or str(baojia_user.id),
         baojia_role, baojia_now()),
    )


def baojia_is_admin(baojia_user_id):
    """环境变量管理员或数据库中角色为 admin 均算管理员。"""
    if baojia_user_id in baojia_config.baojia_ADMIN_IDS:
        return True
    baojia_row = baojia_database.baojia_query_one(
        "SELECT baojia_role FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    return bool(baojia_row and baojia_row["baojia_role"] == "admin")


def baojia_can_use(baojia_user_id):
    """管理员或启用状态的操作员可使用机器人私聊功能。"""
    if baojia_user_id in baojia_config.baojia_ADMIN_IDS:
        return True
    baojia_row = baojia_database.baojia_query_one(
        "SELECT baojia_role, baojia_is_active FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    return bool(
        baojia_row
        and baojia_row["baojia_is_active"] == 1
        and baojia_row["baojia_role"] in ("admin", "operator")
    )


def baojia_admin_only(baojia_func):
    """管理员权限装饰器，同时兼容消息处理器与回调查询处理器。"""

    @functools.wraps(baojia_func)
    async def baojia_wrapper(baojia_update, baojia_context):
        baojia_user = baojia_update.effective_user
        if not baojia_user or not baojia_is_admin(baojia_user.id):
            if baojia_update.callback_query:
                await baojia_safe_answer(
                    baojia_update.callback_query, "仅管理员可执行此操作", show_alert=True
                )
            else:
                import baojia_texts

                await baojia_update.effective_message.reply_text(
                    baojia_texts.BAOJIA_TEXT_NEED_ADMIN
                )
            return None
        return await baojia_func(baojia_update, baojia_context)

    return baojia_wrapper


def baojia_operator_only(baojia_func):
    """使用权限装饰器：仅管理员或启用状态的操作员可使用机器人功能。

    未授权时的响应方式：
    - 回调查询：弹窗提示（仅点击者可见）；
    - 群消息：静默忽略，避免在群内刷屏；
    - 私聊消息：回复拒绝文案并展示其 Telegram ID。
    """

    @functools.wraps(baojia_func)
    async def baojia_wrapper(baojia_update, baojia_context):
        baojia_user = baojia_update.effective_user
        if not baojia_user or not baojia_can_use(baojia_user.id):
            if baojia_update.callback_query:
                await baojia_safe_answer(
                    baojia_update.callback_query,
                    "你没有使用权限，请联系管理员添加",
                    show_alert=True,
                )
                return None
            baojia_chat = baojia_update.effective_chat
            if baojia_chat and baojia_chat.type in ("group", "supergroup"):
                return None
            import baojia_texts

            baojia_user_id = baojia_user.id if baojia_user else 0
            await baojia_update.effective_message.reply_text(
                baojia_texts.BAOJIA_TEXT_DENIED.format(baojia_user_id=baojia_user_id)
            )
            return None
        return await baojia_func(baojia_update, baojia_context)

    return baojia_wrapper


# ==================== 报价计算 ====================

def baojia_calc_usdt(baojia_type, baojia_fee_rate, baojia_rate, baojia_single_fee=0):
    """以 100 万当地货币为基准折算 USDT。

    代收：1,000,000 ÷ 汇率 × (1 - 手续费%)   → 到手越多越好
    代付：1,000,000 ÷ 汇率 × (1 + 手续费%) + 单笔费用 ÷ 汇率 → 付出越少越好
    """
    if not baojia_rate or baojia_rate <= 0:
        return 0.0
    baojia_base = baojia_config.BAOJIA_BASE_AMOUNT
    if baojia_type == baojia_config.BAOJIA_TYPE_COLLECT:
        return baojia_base / baojia_rate * (1 - baojia_fee_rate / 100.0)
    return baojia_base / baojia_rate * (1 + baojia_fee_rate / 100.0) + (baojia_single_fee or 0) / baojia_rate


def baojia_quote_usdt(baojia_row):
    """对数据库行直接计算折算 USDT。"""
    return baojia_calc_usdt(
        baojia_row["baojia_type"],
        baojia_row["baojia_fee_rate"],
        baojia_row["baojia_rate"],
        baojia_row.get("baojia_single_fee", 0),
    )


def baojia_is_better(baojia_type, baojia_new_usdt, baojia_old_usdt):
    """判断新折算值是否优于旧值。代收越高越好，代付越低越好。"""
    if baojia_type == baojia_config.BAOJIA_TYPE_COLLECT:
        return baojia_new_usdt > baojia_old_usdt
    return baojia_new_usdt < baojia_old_usdt


# ==================== 报价存取 ====================

def baojia_find_quote(baojia_type, baojia_country, baojia_material, baojia_account_type,
                      baojia_settle_method, baojia_group_id):
    """按唯一维度查找已有报价，不存在返回 None。"""
    return baojia_database.baojia_query_one(
        """
        SELECT * FROM baojia_quotes
        WHERE baojia_type = ? AND baojia_country = ? AND baojia_material = ?
          AND baojia_account_type = ? AND baojia_settle_method = ? AND baojia_group_id = ?
        """,
        (baojia_type, baojia_country, baojia_material, baojia_account_type,
         baojia_settle_method, baojia_group_id),
    )


def baojia_save_quote(baojia_draft, baojia_user_id):
    """保存报价：同维度存在则覆盖更新，否则新建；全程记录历史表。

    返回 (baojia_quote_id, baojia_action)。action 为 'create' 或 'update'。
    """
    baojia_now_text = baojia_now()
    baojia_existing = baojia_find_quote(
        baojia_draft["baojia_type"], baojia_draft["baojia_country"],
        baojia_draft["baojia_material"], baojia_draft["baojia_account_type"],
        baojia_draft["baojia_settle_method"], baojia_draft["baojia_group_id"],
    )
    with contextlib.closing(baojia_database.baojia_get_connection()) as baojia_conn:
        with baojia_conn:
            if baojia_existing:
                baojia_quote_id = baojia_existing["baojia_quote_id"]
                baojia_action = "update"
                baojia_conn.execute(
                    """
                    UPDATE baojia_quotes SET
                        baojia_fee_rate = ?, baojia_rate = ?, baojia_single_fee = ?,
                        baojia_group_name = ?, baojia_parent_group = ?, baojia_sales = ?,
                        baojia_user_id = ?, baojia_updated_at = ?
                    WHERE baojia_quote_id = ?
                    """,
                    (
                        baojia_draft["baojia_fee_rate"], baojia_draft["baojia_rate"],
                        baojia_draft.get("baojia_single_fee", 0),
                        baojia_draft["baojia_group_name"], baojia_draft.get("baojia_parent_group", ""),
                        baojia_draft["baojia_sales"], baojia_user_id,
                        baojia_now_text, baojia_quote_id,
                    ),
                )
            else:
                baojia_action = "create"
                baojia_cur = baojia_conn.execute(
                    """
                    INSERT INTO baojia_quotes(
                        baojia_type, baojia_country, baojia_material, baojia_account_type,
                        baojia_settle_method, baojia_fee_rate, baojia_rate, baojia_single_fee,
                        baojia_group_id, baojia_group_name, baojia_parent_group, baojia_sales,
                        baojia_user_id, baojia_created_at, baojia_updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        baojia_draft["baojia_type"], baojia_draft["baojia_country"],
                        baojia_draft["baojia_material"], baojia_draft["baojia_account_type"],
                        baojia_draft["baojia_settle_method"], baojia_draft["baojia_fee_rate"],
                        baojia_draft["baojia_rate"], baojia_draft.get("baojia_single_fee", 0),
                        baojia_draft["baojia_group_id"], baojia_draft["baojia_group_name"],
                        baojia_draft.get("baojia_parent_group", ""), baojia_draft["baojia_sales"],
                        baojia_user_id, baojia_now_text, baojia_now_text,
                    ),
                )
                baojia_quote_id = baojia_cur.lastrowid
            baojia_conn.execute(
                """
                INSERT INTO baojia_quote_history(
                    baojia_quote_id, baojia_action, baojia_type, baojia_country, baojia_material,
                    baojia_account_type, baojia_settle_method, baojia_fee_rate, baojia_rate,
                    baojia_single_fee, baojia_group_id, baojia_group_name, baojia_parent_group,
                    baojia_sales, baojia_changed_by, baojia_changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baojia_quote_id, baojia_action, baojia_draft["baojia_type"],
                    baojia_draft["baojia_country"], baojia_draft["baojia_material"],
                    baojia_draft["baojia_account_type"], baojia_draft["baojia_settle_method"],
                    baojia_draft["baojia_fee_rate"], baojia_draft["baojia_rate"],
                    baojia_draft.get("baojia_single_fee", 0), baojia_draft["baojia_group_id"],
                    baojia_draft["baojia_group_name"], baojia_draft.get("baojia_parent_group", ""),
                    baojia_draft["baojia_sales"], baojia_user_id, baojia_now_text,
                ),
            )
    return baojia_quote_id, baojia_action


def baojia_quote_by_id(baojia_quote_id):
    """按报价 ID 查询单条报价，不存在返回 None。"""
    return baojia_database.baojia_query_one(
        "SELECT * FROM baojia_quotes WHERE baojia_quote_id = ?",
        (baojia_quote_id,),
    )


def baojia_delete_quote(baojia_quote_id, baojia_user_id):
    """删除报价并写入历史表（action='delete'），可追溯。

    返回被删除的报价行；报价不存在或已删除返回 None。
    """
    baojia_row = baojia_quote_by_id(baojia_quote_id)
    if not baojia_row:
        return None
    with contextlib.closing(baojia_database.baojia_get_connection()) as baojia_conn:
        with baojia_conn:
            baojia_conn.execute(
                """
                INSERT INTO baojia_quote_history(
                    baojia_quote_id, baojia_action, baojia_type, baojia_country, baojia_material,
                    baojia_account_type, baojia_settle_method, baojia_fee_rate, baojia_rate,
                    baojia_single_fee, baojia_group_id, baojia_group_name, baojia_parent_group,
                    baojia_sales, baojia_changed_by, baojia_changed_at)
                VALUES (?, 'delete', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baojia_row["baojia_quote_id"], baojia_row["baojia_type"],
                    baojia_row["baojia_country"], baojia_row["baojia_material"],
                    baojia_row["baojia_account_type"], baojia_row["baojia_settle_method"],
                    baojia_row["baojia_fee_rate"], baojia_row["baojia_rate"],
                    baojia_row.get("baojia_single_fee", 0), baojia_row["baojia_group_id"],
                    baojia_row["baojia_group_name"], baojia_row.get("baojia_parent_group", ""),
                    baojia_row["baojia_sales"], baojia_user_id, baojia_now(),
                ),
            )
            baojia_conn.execute(
                "DELETE FROM baojia_quotes WHERE baojia_quote_id = ?",
                (baojia_quote_id,),
            )
    return baojia_row


def baojia_list_countries():
    """返回所有已有报价的国家名称列表。"""
    baojia_rows = baojia_database.baojia_query(
        "SELECT DISTINCT baojia_country FROM baojia_quotes ORDER BY baojia_country"
    )
    return [baojia_row["baojia_country"] for baojia_row in baojia_rows]


def baojia_quotes_by_country(baojia_country):
    """按国家取出全部报价行。"""
    return baojia_database.baojia_query(
        "SELECT * FROM baojia_quotes WHERE baojia_country = ?",
        (baojia_country,),
    )


def baojia_quotes_by_group(baojia_group_id):
    """按群组 ID 取出全部报价行。"""
    return baojia_database.baojia_query(
        "SELECT * FROM baojia_quotes WHERE baojia_group_id = ?",
        (baojia_group_id,),
    )


def baojia_history_by_group(baojia_group_id, baojia_limit=10):
    """按群组 ID 取最近的变更历史。"""
    return baojia_database.baojia_query(
        "SELECT * FROM baojia_quote_history WHERE baojia_group_id = ? "
        "ORDER BY baojia_history_id DESC LIMIT ?",
        (baojia_group_id, baojia_limit),
    )


def baojia_match_country(baojia_text):
    """群消息国家名匹配：消息全文（去空格）与已有国家名完全一致才命中。"""
    baojia_clean = str(baojia_text or "").strip()
    if not baojia_clean or len(baojia_clean) > 30:
        return None
    baojia_countries = baojia_list_countries()
    if baojia_clean in baojia_countries:
        return baojia_clean
    return None
