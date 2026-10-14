"""baojia 报价机器人 - 通用工具

权限判定、管理员装饰器、数值解析、报价折算计算、群组链接生成、报价存取等。
所有自定义变量与函数均带 baojia 前缀。
"""

import contextlib
import functools
import hashlib
import hmac
import html
import re
import secrets
from datetime import datetime, timedelta

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


# ==================== Web 后台账号密码 ====================

BAOJIA_PBKDF2_ITERATIONS = 200_000


def baojia_hash_password(baojia_password):
    """用 pbkdf2_sha256 哈希密码，返回 'pbkdf2_sha256$迭代次数$盐$哈希' 字符串。"""
    baojia_salt = secrets.token_bytes(16)
    baojia_hash = hashlib.pbkdf2_hmac(
        "sha256", baojia_password.encode("utf-8"), baojia_salt, BAOJIA_PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${BAOJIA_PBKDF2_ITERATIONS}${baojia_salt.hex()}${baojia_hash.hex()}"


def baojia_verify_password(baojia_password, baojia_stored):
    """校验密码是否匹配存储的哈希。"""
    if not baojia_stored or not baojia_password:
        return False
    try:
        baojia_algo, baojia_iters, baojia_salt_hex, baojia_hash_hex = baojia_stored.split("$")
        if baojia_algo != "pbkdf2_sha256":
            return False
        baojia_salt = bytes.fromhex(baojia_salt_hex)
        baojia_expected = bytes.fromhex(baojia_hash_hex)
        baojia_actual = hashlib.pbkdf2_hmac(
            "sha256", baojia_password.encode("utf-8"), baojia_salt, int(baojia_iters)
        )
        return hmac.compare_digest(baojia_actual, baojia_expected)
    except (ValueError, TypeError):
        return False


def baojia_user_by_username(baojia_username):
    """按用户名查询用户，不存在返回 None。"""
    if not baojia_username:
        return None
    return baojia_database.baojia_query_one(
        "SELECT * FROM baojia_users WHERE baojia_username = ?",
        (baojia_username,),
    )


def baojia_ensure_web_admin():
    """确保存在一个 Web 后台管理员账号。

    按 baojia_config.baojia_ADMIN_USERNAME 查询：
    - 不存在则创建（baojia_user_id=0，role=admin，is_active=1）；
    - 已存在则跳过（不覆盖密码，便于管理员自行改密）。
    """
    baojia_username = baojia_config.baojia_ADMIN_USERNAME
    if not baojia_username:
        return
    baojia_existing = baojia_user_by_username(baojia_username)
    if baojia_existing:
        return
    baojia_database.baojia_execute(
        """
        INSERT INTO baojia_users(
            baojia_user_id, baojia_full_name, baojia_role, baojia_is_active,
            baojia_created_at, baojia_username, baojia_password_hash)
        VALUES (0, ?, 'admin', 1, ?, ?, ?)
        """,
        (
            "Web 管理员", baojia_now(), baojia_username,
            baojia_hash_password(baojia_config.baojia_ADMIN_PASSWORD),
        ),
    )


# ==================== 用户管理（Web 后台用） ====================

# 受保护账号：Web 初始管理员 user_id=0，禁止删除/禁用
BAOJIA_PROTECTED_USER_IDS = {0}


def baojia_list_users():
    """返回所有用户（不含密码哈希），按 user_id 排序。"""
    return baojia_database.baojia_query(
        "SELECT baojia_user_id, baojia_full_name, baojia_role, baojia_is_active, "
        "baojia_username, baojia_created_at FROM baojia_users ORDER BY baojia_user_id"
    )


def baojia_user_by_id(baojia_user_id):
    """按 ID 查询用户，不存在返回 None。"""
    return baojia_database.baojia_query_one(
        "SELECT baojia_user_id, baojia_full_name, baojia_role, baojia_is_active, "
        "baojia_username, baojia_created_at FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )


def baojia_create_user(baojia_full_name, baojia_role, baojia_is_active,
                       baojia_username=None, baojia_password=None, baojia_telegram_id=None):
    """新建用户。

    - baojia_telegram_id 提供则用它作为 user_id（Telegram 操作员）；
      否则分配一个负数 user_id（纯 Web 用户，避开 Telegram 正数 ID）。
    - baojia_username 若提供则必须唯一，否则报错。
    返回新 user_id。
    """
    if baojia_username:
        if baojia_user_by_username(baojia_username):
            raise ValueError(f"用户名 {baojia_username} 已存在")
    if baojia_telegram_id is not None:
        baojia_user_id = int(baojia_telegram_id)
        if baojia_user_by_id(baojia_user_id):
            raise ValueError(f"用户 ID {baojia_user_id} 已存在")
    else:
        baojia_min_row = baojia_database.baojia_query_one(
            "SELECT MIN(baojia_user_id) AS m FROM baojia_users"
        )
        baojia_user_id = min((baojia_min_row["m"] or 0) - 1, -1)
    baojia_database.baojia_execute(
        """
        INSERT INTO baojia_users(
            baojia_user_id, baojia_full_name, baojia_role, baojia_is_active,
            baojia_created_at, baojia_username, baojia_password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            baojia_user_id, baojia_full_name, baojia_role, int(bool(baojia_is_active)),
            baojia_now(), baojia_username or "",
            baojia_hash_password(baojia_password) if baojia_password else "",
        ),
    )
    return baojia_user_id


def baojia_update_user(baojia_user_id, baojia_full_name=None, baojia_role=None,
                       baojia_is_active=None, baojia_username=None):
    """更新用户非密码字段。返回更新后的行，不存在返回 None。"""
    baojia_existing = baojia_user_by_id(baojia_user_id)
    if not baojia_existing:
        return None
    baojia_set, baojia_params = [], []
    if baojia_full_name is not None:
        baojia_set.append("baojia_full_name = ?"); baojia_params.append(baojia_full_name)
    if baojia_role is not None:
        baojia_set.append("baojia_role = ?"); baojia_params.append(baojia_role)
    if baojia_is_active is not None:
        # 受保护账号不允许禁用
        if baojia_user_id in BAOJIA_PROTECTED_USER_IDS and not baojia_is_active:
            raise ValueError("初始管理员账号禁止禁用")
        baojia_set.append("baojia_is_active = ?"); baojia_params.append(int(bool(baojia_is_active)))
    if baojia_username is not None:
        baojia_dup = baojia_user_by_username(baojia_username)
        if baojia_dup and baojia_dup["baojia_user_id"] != baojia_user_id:
            raise ValueError(f"用户名 {baojia_username} 已存在")
        baojia_set.append("baojia_username = ?"); baojia_params.append(baojia_username)
    if not baojia_set:
        return baojia_existing
    baojia_params.append(baojia_user_id)
    baojia_database.baojia_execute(
        f"UPDATE baojia_users SET {', '.join(baojia_set)} WHERE baojia_user_id = ?",
        tuple(baojia_params),
    )
    return baojia_user_by_id(baojia_user_id)


def baojia_set_password(baojia_user_id, baojia_password):
    """直接设置用户密码（管理员重置用）。返回是否成功。"""
    if not baojia_password:
        raise ValueError("密码不能为空")
    if not baojia_user_by_id(baojia_user_id):
        return False
    baojia_database.baojia_execute(
        "UPDATE baojia_users SET baojia_password_hash = ? WHERE baojia_user_id = ?",
        (baojia_hash_password(baojia_password), baojia_user_id),
    )
    return True


def baojia_change_own_password(baojia_user_id, baojia_old_password, baojia_new_password):
    """用户自助改密：校验旧密码后设置新密码。"""
    if not baojia_new_password:
        raise ValueError("新密码不能为空")
    baojia_row = baojia_database.baojia_query_one(
        "SELECT baojia_password_hash FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    if not baojia_row:
        raise ValueError("用户不存在")
    if not baojia_verify_password(baojia_old_password, baojia_row["baojia_password_hash"]):
        raise ValueError("旧密码不正确")
    baojia_database.baojia_execute(
        "UPDATE baojia_users SET baojia_password_hash = ? WHERE baojia_user_id = ?",
        (baojia_hash_password(baojia_new_password), baojia_user_id),
    )
    return True


def baojia_delete_user(baojia_user_id):
    """删除用户。受保护账号禁止删除。返回被删的行，不存在返回 None。"""
    if baojia_user_id in BAOJIA_PROTECTED_USER_IDS:
        raise ValueError("初始管理员账号禁止删除")
    baojia_row = baojia_user_by_id(baojia_user_id)
    if not baojia_row:
        return None
    baojia_database.baojia_execute(
        "DELETE FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    return baojia_row


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
                        baojia_remark = ?, baojia_user_id = ?, baojia_updated_at = ?
                    WHERE baojia_quote_id = ?
                    """,
                    (
                        baojia_draft["baojia_fee_rate"], baojia_draft["baojia_rate"],
                        baojia_draft.get("baojia_single_fee", 0),
                        baojia_draft["baojia_group_name"], baojia_draft.get("baojia_parent_group", ""),
                        baojia_draft["baojia_sales"], baojia_draft.get("baojia_remark", ""),
                        baojia_user_id, baojia_now_text, baojia_quote_id,
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
                        baojia_remark, baojia_user_id, baojia_created_at, baojia_updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        baojia_draft["baojia_type"], baojia_draft["baojia_country"],
                        baojia_draft["baojia_material"], baojia_draft["baojia_account_type"],
                        baojia_draft["baojia_settle_method"], baojia_draft["baojia_fee_rate"],
                        baojia_draft["baojia_rate"], baojia_draft.get("baojia_single_fee", 0),
                        baojia_draft["baojia_group_id"], baojia_draft["baojia_group_name"],
                        baojia_draft.get("baojia_parent_group", ""), baojia_draft["baojia_sales"],
                        baojia_draft.get("baojia_remark", ""), baojia_user_id,
                        baojia_now_text, baojia_now_text,
                    ),
                )
                baojia_quote_id = baojia_cur.lastrowid
            baojia_conn.execute(
                """
                INSERT INTO baojia_quote_history(
                    baojia_quote_id, baojia_action, baojia_type, baojia_country, baojia_material,
                    baojia_account_type, baojia_settle_method, baojia_fee_rate, baojia_rate,
                    baojia_single_fee, baojia_group_id, baojia_group_name, baojia_parent_group,
                    baojia_sales, baojia_remark, baojia_changed_by, baojia_changed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baojia_quote_id, baojia_action, baojia_draft["baojia_type"],
                    baojia_draft["baojia_country"], baojia_draft["baojia_material"],
                    baojia_draft["baojia_account_type"], baojia_draft["baojia_settle_method"],
                    baojia_draft["baojia_fee_rate"], baojia_draft["baojia_rate"],
                    baojia_draft.get("baojia_single_fee", 0), baojia_draft["baojia_group_id"],
                    baojia_draft["baojia_group_name"], baojia_draft.get("baojia_parent_group", ""),
                    baojia_draft["baojia_sales"], baojia_draft.get("baojia_remark", ""),
                    baojia_user_id, baojia_now_text,
                ),
            )
    return baojia_quote_id, baojia_action


def baojia_quote_by_id(baojia_quote_id):
    """按报价 ID 查询单条报价，不存在返回 None。"""
    return baojia_database.baojia_query_one(
        "SELECT * FROM baojia_quotes WHERE baojia_quote_id = ?",
        (baojia_quote_id,),
    )


def baojia_quotes_list(baojia_country=None, baojia_type=None, baojia_material=None,
                       baojia_group_id=None, baojia_parent_group=None, baojia_group_name=None):
    """按条件查询报价列表（Web 后台用）。

    参数均为可选；不传则返回全部。
    - baojia_group_id：群 ID 精确匹配；
    - baojia_parent_group：所属公群模糊匹配（包含子串即命中）；
    - baojia_group_name：群名模糊匹配（包含子串即命中）。
    按国家、类型、更新时间排序。
    """
    baojia_sql = "SELECT * FROM baojia_quotes WHERE 1=1"
    baojia_params = []
    if baojia_country:
        baojia_sql += " AND baojia_country = ?"
        baojia_params.append(baojia_country)
    if baojia_type:
        baojia_sql += " AND baojia_type = ?"
        baojia_params.append(baojia_type)
    if baojia_material:
        baojia_sql += " AND baojia_material = ?"
        baojia_params.append(baojia_material)
    if baojia_group_id:
        baojia_sql += " AND baojia_group_id = ?"
        baojia_params.append(int(baojia_group_id))
    if baojia_parent_group:
        baojia_sql += " AND baojia_parent_group LIKE ?"
        baojia_params.append(f"%{baojia_parent_group}%")
    if baojia_group_name:
        baojia_sql += " AND baojia_group_name LIKE ?"
        baojia_params.append(f"%{baojia_group_name}%")
    baojia_sql += " ORDER BY baojia_country, baojia_type, baojia_updated_at DESC"
    baojia_rows = baojia_database.baojia_query(baojia_sql, tuple(baojia_params))
    # 按价格优势排序：国家 → 类型（代收在前）→ 组内按折算 USDT（代收降序、代付升序）
    def baojia_sort_key(baojia_row):
        baojia_usdt = baojia_quote_usdt(baojia_row)
        baojia_type_order = 0 if baojia_row["baojia_type"] == baojia_config.BAOJIA_TYPE_COLLECT else 1
        baojia_adv = -baojia_usdt if baojia_row["baojia_type"] == baojia_config.BAOJIA_TYPE_COLLECT else baojia_usdt
        return (baojia_row["baojia_country"], baojia_type_order, baojia_adv)
    return sorted(baojia_rows, key=baojia_sort_key)


def baojia_update_quote_by_id(baojia_quote_id, baojia_draft, baojia_user_id):
    """按报价 ID 直接更新（Web 后台编辑用），并写入历史表。

    与 baojia_save_quote 不同：不按维度查重，直接更新指定行，
    避免修改维度时产生重复记录。返回更新后的行，不存在返回 None。
    """
    baojia_existing = baojia_quote_by_id(baojia_quote_id)
    if not baojia_existing:
        return None
    baojia_now_text = baojia_now()
    with contextlib.closing(baojia_database.baojia_get_connection()) as baojia_conn:
        with baojia_conn:
            baojia_conn.execute(
                """
                UPDATE baojia_quotes SET
                    baojia_type = ?, baojia_country = ?, baojia_material = ?,
                    baojia_account_type = ?, baojia_settle_method = ?,
                    baojia_fee_rate = ?, baojia_rate = ?, baojia_single_fee = ?,
                    baojia_group_id = ?, baojia_group_name = ?, baojia_parent_group = ?,
                    baojia_sales = ?, baojia_remark = ?, baojia_user_id = ?, baojia_updated_at = ?
                WHERE baojia_quote_id = ?
                """,
                (
                    baojia_draft["baojia_type"], baojia_draft["baojia_country"],
                    baojia_draft.get("baojia_material", ""),
                    baojia_draft.get("baojia_account_type", ""),
                    baojia_draft.get("baojia_settle_method", ""),
                    baojia_draft["baojia_fee_rate"], baojia_draft["baojia_rate"],
                    baojia_draft.get("baojia_single_fee", 0),
                    baojia_draft["baojia_group_id"], baojia_draft["baojia_group_name"],
                    baojia_draft.get("baojia_parent_group", ""),
                    baojia_draft["baojia_sales"], baojia_draft.get("baojia_remark", ""),
                    baojia_user_id, baojia_now_text, baojia_quote_id,
                ),
            )
            baojia_conn.execute(
                """
                INSERT INTO baojia_quote_history(
                    baojia_quote_id, baojia_action, baojia_type, baojia_country, baojia_material,
                    baojia_account_type, baojia_settle_method, baojia_fee_rate, baojia_rate,
                    baojia_single_fee, baojia_group_id, baojia_group_name, baojia_parent_group,
                    baojia_sales, baojia_remark, baojia_changed_by, baojia_changed_at)
                VALUES (?, 'update', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baojia_quote_id, baojia_draft["baojia_type"], baojia_draft["baojia_country"],
                    baojia_draft.get("baojia_material", ""),
                    baojia_draft.get("baojia_account_type", ""),
                    baojia_draft.get("baojia_settle_method", ""),
                    baojia_draft["baojia_fee_rate"], baojia_draft["baojia_rate"],
                    baojia_draft.get("baojia_single_fee", 0), baojia_draft["baojia_group_id"],
                    baojia_draft["baojia_group_name"], baojia_draft.get("baojia_parent_group", ""),
                    baojia_draft["baojia_sales"], baojia_draft.get("baojia_remark", ""),
                    baojia_user_id, baojia_now_text,
                ),
            )
    return baojia_quote_by_id(baojia_quote_id)


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
                    baojia_sales, baojia_remark, baojia_changed_by, baojia_changed_at)
                VALUES (?, 'delete', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    baojia_row["baojia_quote_id"], baojia_row["baojia_type"],
                    baojia_row["baojia_country"], baojia_row["baojia_material"],
                    baojia_row["baojia_account_type"], baojia_row["baojia_settle_method"],
                    baojia_row["baojia_fee_rate"], baojia_row["baojia_rate"],
                    baojia_row.get("baojia_single_fee", 0), baojia_row["baojia_group_id"],
                    baojia_row["baojia_group_name"], baojia_row.get("baojia_parent_group", ""),
                    baojia_row["baojia_sales"], baojia_row.get("baojia_remark", ""),
                    baojia_user_id, baojia_now(),
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


def baojia_overview_stats():
    """后台顶部数据汇总：国家总数、报价总条数、今日/本周/本月记录条数。

    以 baojia_created_at（录入时间）为准统计。
    """
    baojia_now = datetime.now()
    baojia_today = baojia_now.replace(hour=0, minute=0, second=0, microsecond=0)
    baojia_week = baojia_today - timedelta(days=baojia_today.weekday())
    baojia_month = baojia_today.replace(day=1)
    baojia_fmt = lambda dt: dt.strftime(BAOJIA_DATETIME_FORMAT)
    baojia_row = baojia_database.baojia_query_one(
        """
        SELECT
            COUNT(DISTINCT baojia_country) AS baojia_countries,
            COUNT(*) AS baojia_total,
            SUM(CASE WHEN baojia_created_at >= ? THEN 1 ELSE 0 END) AS baojia_today,
            SUM(CASE WHEN baojia_created_at >= ? THEN 1 ELSE 0 END) AS baojia_week,
            SUM(CASE WHEN baojia_created_at >= ? THEN 1 ELSE 0 END) AS baojia_month
        FROM baojia_quotes
        """,
        (baojia_fmt(baojia_today), baojia_fmt(baojia_week), baojia_fmt(baojia_month)),
    )
    return {
        "countries": baojia_row["baojia_countries"] or 0,
        "total": baojia_row["baojia_total"] or 0,
        "today": baojia_row["baojia_today"] or 0,
        "week": baojia_row["baojia_week"] or 0,
        "month": baojia_row["baojia_month"] or 0,
    }


def baojia_quotes_by_country(baojia_country):
    """按国家取出全部报价行。"""
    return baojia_database.baojia_query(
        "SELECT * FROM baojia_quotes WHERE baojia_country = ?",
        (baojia_country,),
    )


def baojia_material_stats():
    """统计每个国家已记录的料性与条数。

    返回行字段：baojia_country, baojia_type, baojia_material, baojia_count。
    代收在前、代付在后（代付料性为空字符串）。
    """
    return baojia_database.baojia_query(
        """
        SELECT baojia_country, baojia_type, baojia_material,
               COUNT(*) AS baojia_count
        FROM baojia_quotes
        GROUP BY baojia_country, baojia_type, baojia_material
        ORDER BY baojia_country,
                 CASE baojia_type WHEN 'collect' THEN 0 ELSE 1 END,
                 baojia_material
        """
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
