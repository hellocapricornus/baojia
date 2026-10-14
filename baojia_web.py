"""baojia 报价机器人 - Web 后台管理

与 Telegram 机器人同进程运行（aiohttp + PTB 共享 event loop），
复用同一套 SQLite 数据库与 baojia_utils 存取函数，保证两边行为一致。

认证说明：
    当前 baojia_web_get_user() 为占位实现，返回固定管理员身份，
    便于先把页面功能跑通。选定方案后替换该函数即可：
    - 方案 A（Telegram 登录小部件）：校验 Telegram 回调签名，
      用 user_id 查 baojia_users 表，is_active=1 才放行；
    - 方案 B（账号密码）：给 baojia_users 加 password_hash 列，
      登录后签发 session/token。

接口契约（字段均以 baojia_ 前缀，与数据库一致）：
    GET  /api/countries          -> {"countries": [str, ...]}
    GET  /api/quotes?country=&type=&material=
                                 -> [quote_row, ...]
    POST /api/quotes             -> {"ok": true, "id": int, "action": "create"}
    PUT  /api/quotes/{id}        -> {"ok": true}
    DELETE /api/quotes/{id}      -> {"ok": true}
"""

import json
import secrets
import time
from pathlib import Path

from aiohttp import web

import baojia_config
import baojia_utils

BAOJIA_ADMIN_HTML = baojia_config.BAOJIA_BASE_DIR / "baojia_admin.html"

# 内存会话存储：{token: {"user_id", "expires_at"}}
# 单进程部署，重启后会话失效（需重新登录）。
BAOJIA_SESSIONS = {}
BAOJIA_SESSION_TTL = 7 * 24 * 3600  # 7 天


# ==================== 认证（账号密码） ====================

def baojia_web_make_session(baojia_user_row):
    """为已登录用户创建会话，返回 token。"""
    baojia_token = secrets.token_hex(32)
    BAOJIA_SESSIONS[baojia_token] = {
        "user_id": baojia_user_row["baojia_user_id"],
        "expires_at": time.time() + BAOJIA_SESSION_TTL,
    }
    return baojia_token


def baojia_web_clean_sessions():
    """清理过期会话。"""
    baojia_now = time.time()
    baojia_expired = [t for t, s in BAOJIA_SESSIONS.items() if s["expires_at"] < baojia_now]
    for t in baojia_expired:
        BAOJIA_SESSIONS.pop(t, None)


def baojia_web_get_user(request):
    """从 Authorization: Bearer <token> 取出当前登录用户，未登录/过期返回 None。"""
    baojia_auth = request.headers.get("Authorization", "")
    if not baojia_auth.startswith("Bearer "):
        return None
    baojia_token = baojia_auth[7:].strip()
    baojia_session = BAOJIA_SESSIONS.get(baojia_token)
    if not baojia_session:
        return None
    if baojia_session["expires_at"] < time.time():
        BAOJIA_SESSIONS.pop(baojia_token, None)
        return None
    baojia_user = baojia_utils.baojia_database.baojia_query_one(
        "SELECT baojia_user_id, baojia_full_name, baojia_role, baojia_is_active "
        "FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_session["user_id"],),
    )
    if not baojia_user or baojia_user["baojia_is_active"] != 1:
        return None
    return {
        "baojia_user_id": baojia_user["baojia_user_id"],
        "baojia_full_name": baojia_user["baojia_full_name"],
        "baojia_is_admin": baojia_user["baojia_role"] == "admin",
    }


def baojia_web_require_auth(baojia_handler):
    """Web 接口鉴权装饰器，未登录返回 401。"""
    async def baojia_wrapper(baojia_request):
        baojia_user = baojia_web_get_user(baojia_request)
        if not baojia_user:
            return web.json_response({"ok": False, "error": "未登录或登录已过期"}, status=401)
        baojia_request["baojia_user"] = baojia_user
        return await baojia_handler(baojia_request)
    return baojia_wrapper


def baojia_web_require_admin(baojia_handler):
    """管理员权限装饰器，非管理员返回 403。"""
    async def baojia_wrapper(baojia_request):
        baojia_user = baojia_web_get_user(baojia_request)
        if not baojia_user:
            return web.json_response({"ok": False, "error": "未登录或登录已过期"}, status=401)
        if not baojia_user["baojia_is_admin"]:
            return web.json_response({"ok": False, "error": "该操作仅管理员可执行"}, status=403)
        baojia_request["baojia_user"] = baojia_user
        return await baojia_handler(baojia_request)
    return baojia_wrapper


# ==================== 数据转换 ====================

def baojia_row_to_dict(baojia_row):
    """sqlite3.Row / dict 转普通 dict，供 JSON 序列化。"""
    if baojia_row is None:
        return None
    if isinstance(baojia_row, dict):
        return dict(baojia_row)
    return {baojia_key: baojia_row[baojia_key] for baojia_key in baojia_row.keys()}


async def baojia_read_json(baojia_request):
    """读取并解析 JSON body，失败返回 None。"""
    try:
        return await baojia_request.json()
    except (json.JSONDecodeError, Exception):
        return None


def baojia_build_draft(baojia_data):
    """把前端 JSON 转为 baojia_save_quote / update_quote_by_id 所需的 draft。"""
    baojia_type = str(baojia_data.get("baojia_type", "")).strip()
    baojia_is_pay = baojia_type == baojia_config.BAOJIA_TYPE_PAY
    baojia_draft = {
        "baojia_type": baojia_type,
        "baojia_country": str(baojia_data.get("baojia_country", "")).strip(),
        "baojia_material": "" if baojia_is_pay else str(baojia_data.get("baojia_material", "")).strip(),
        "baojia_account_type": "" if baojia_is_pay else str(baojia_data.get("baojia_account_type", "")).strip(),
        "baojia_settle_method": "" if baojia_is_pay else str(baojia_data.get("baojia_settle_method", "")).strip(),
        "baojia_fee_rate": float(baojia_data.get("baojia_fee_rate", 0)),
        "baojia_rate": float(baojia_data.get("baojia_rate", 0)),
        "baojia_single_fee": float(baojia_data.get("baojia_single_fee", 0)) if baojia_is_pay else 0,
        "baojia_group_id": int(baojia_data.get("baojia_group_id", 0)),
        "baojia_group_name": str(baojia_data.get("baojia_group_name", "")).strip(),
        "baojia_parent_group": str(baojia_data.get("baojia_parent_group", "")).strip(),
        "baojia_sales": str(baojia_data.get("baojia_sales", "")).strip(),
        "baojia_remark": str(baojia_data.get("baojia_remark", "")).strip(),
    }
    return baojia_draft


# ==================== 认证接口 ====================

async def baojia_web_login(baojia_request):
    """账号密码登录，成功返回 token 与用户信息。"""
    baojia_data = await baojia_read_json(baojia_request)
    if not baojia_data:
        return web.json_response({"ok": False, "error": "请求体不是合法 JSON"}, status=400)
    baojia_username = str(baojia_data.get("username", "")).strip()
    baojia_password = str(baojia_data.get("password", ""))
    if not baojia_username or not baojia_password:
        return web.json_response({"ok": False, "error": "用户名和密码不能为空"}, status=400)
    baojia_user_row = baojia_utils.baojia_user_by_username(baojia_username)
    if (not baojia_user_row
            or baojia_user_row["baojia_is_active"] != 1
            or not baojia_utils.baojia_verify_password(
                baojia_password, baojia_user_row["baojia_password_hash"])):
        return web.json_response({"ok": False, "error": "用户名或密码错误"}, status=401)
    baojia_web_clean_sessions()
    baojia_token = baojia_web_make_session(baojia_user_row)
    return web.json_response({
        "ok": True,
        "token": baojia_token,
        "user": {
            "baojia_user_id": baojia_user_row["baojia_user_id"],
            "baojia_full_name": baojia_user_row["baojia_full_name"],
            "baojia_is_admin": baojia_user_row["baojia_role"] == "admin",
        },
    })


@baojia_web_require_auth
async def baojia_web_logout(baojia_request):
    """登出：销毁当前 token。"""
    baojia_auth = baojia_request.headers.get("Authorization", "")
    baojia_token = baojia_auth[7:].strip() if baojia_auth.startswith("Bearer ") else ""
    BAOJIA_SESSIONS.pop(baojia_token, None)
    return web.json_response({"ok": True})


@baojia_web_require_auth
async def baojia_web_me(baojia_request):
    """返回当前登录用户信息。"""
    return web.json_response({"ok": True, "user": baojia_request["baojia_user"]})


@baojia_web_require_auth
async def baojia_web_change_own_password(baojia_request):
    """自助修改密码：需提供旧密码。"""
    baojia_data = await baojia_read_json(baojia_request)
    if not baojia_data:
        return web.json_response({"ok": False, "error": "请求体不是合法 JSON"}, status=400)
    baojia_old = str(baojia_data.get("old_password", ""))
    baojia_new = str(baojia_data.get("new_password", ""))
    if not baojia_new:
        return web.json_response({"ok": False, "error": "新密码不能为空"}, status=400)
    try:
        baojia_utils.baojia_change_own_password(
            baojia_request["baojia_user"]["baojia_user_id"], baojia_old, baojia_new
        )
    except ValueError as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    return web.json_response({"ok": True})


# ==================== 操作员管理（管理员） ====================

@baojia_web_require_admin
async def baojia_web_users_list(baojia_request):  # noqa: ARG001
    """用户列表。"""
    baojia_rows = baojia_utils.baojia_list_users()
    return web.json_response({"ok": True, "users": [dict(r) for r in baojia_rows]})


@baojia_web_require_admin
async def baojia_web_users_create(baojia_request):
    """新建用户。"""
    baojia_data = await baojia_read_json(baojia_request)
    if not baojia_data:
        return web.json_response({"ok": False, "error": "请求体不是合法 JSON"}, status=400)
    baojia_full_name = str(baojia_data.get("full_name", "")).strip()
    baojia_role = str(baojia_data.get("role", "operator")).strip()
    baojia_is_active = int(bool(baojia_data.get("is_active", 1)))
    baojia_username = str(baojia_data.get("username", "")).strip() or None
    baojia_password = str(baojia_data.get("password", "")) or None
    baojia_telegram_id = baojia_data.get("telegram_id")
    if not baojia_full_name:
        return web.json_response({"ok": False, "error": "姓名不能为空"}, status=400)
    if baojia_role not in ("admin", "operator"):
        return web.json_response({"ok": False, "error": "角色必须为 admin 或 operator"}, status=400)
    if baojia_telegram_id is not None:
        try:
            baojia_telegram_id = int(baojia_telegram_id)
        except (TypeError, ValueError):
            return web.json_response({"ok": False, "error": "Telegram ID 必须为数字"}, status=400)
    try:
        baojia_user_id = baojia_utils.baojia_create_user(
            baojia_full_name, baojia_role, baojia_is_active,
            baojia_username=baojia_username, baojia_password=baojia_password,
            baojia_telegram_id=baojia_telegram_id,
        )
    except ValueError as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    return web.json_response({"ok": True, "user_id": baojia_user_id})


@baojia_web_require_admin
async def baojia_web_users_update(baojia_request):
    """更新用户字段（不含密码）。"""
    try:
        baojia_user_id = int(baojia_request.match_info["baojia_user_id"])
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "无效的用户 ID"}, status=400)
    baojia_data = await baojia_read_json(baojia_request)
    if not baojia_data:
        return web.json_response({"ok": False, "error": "请求体不是合法 JSON"}, status=400)
    baojia_kwargs = {}
    if "full_name" in baojia_data:
        baojia_kwargs["baojia_full_name"] = str(baojia_data["full_name"]).strip()
    if "role" in baojia_data:
        baojia_role = str(baojia_data["role"]).strip()
        if baojia_role not in ("admin", "operator"):
            return web.json_response({"ok": False, "error": "角色必须为 admin 或 operator"}, status=400)
        baojia_kwargs["baojia_role"] = baojia_role
    if "is_active" in baojia_data:
        baojia_kwargs["baojia_is_active"] = int(bool(baojia_data["is_active"]))
    if "username" in baojia_data:
        baojia_kwargs["baojia_username"] = str(baojia_data["username"]).strip()
    try:
        baojia_row = baojia_utils.baojia_update_user(baojia_user_id, **baojia_kwargs)
    except ValueError as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    if not baojia_row:
        return web.json_response({"ok": False, "error": "用户不存在"}, status=404)
    return web.json_response({"ok": True, "user": dict(baojia_row)})


@baojia_web_require_admin
async def baojia_web_users_reset_password(baojia_request):
    """管理员重置用户密码。"""
    try:
        baojia_user_id = int(baojia_request.match_info["baojia_user_id"])
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "无效的用户 ID"}, status=400)
    baojia_data = await baojia_read_json(baojia_request)
    if not baojia_data:
        return web.json_response({"ok": False, "error": "请求体不是合法 JSON"}, status=400)
    baojia_new = str(baojia_data.get("new_password", ""))
    try:
        baojia_ok = baojia_utils.baojia_set_password(baojia_user_id, baojia_new)
    except ValueError as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    if not baojia_ok:
        return web.json_response({"ok": False, "error": "用户不存在"}, status=404)
    return web.json_response({"ok": True})


@baojia_web_require_admin
async def baojia_web_users_delete(baojia_request):
    """删除用户。"""
    try:
        baojia_user_id = int(baojia_request.match_info["baojia_user_id"])
    except (TypeError, ValueError):
        return web.json_response({"ok": False, "error": "无效的用户 ID"}, status=400)
    try:
        baojia_row = baojia_utils.baojia_delete_user(baojia_user_id)
    except ValueError as e:
        return web.json_response({"ok": False, "error": str(e)}, status=400)
    if not baojia_row:
        return web.json_response({"ok": False, "error": "用户不存在"}, status=404)
    return web.json_response({"ok": True})


# ==================== 接口处理 ====================

async def baojia_web_index(baojia_request):  # noqa: ARG001
    """返回后台管理单页。"""
    if not BAOJIA_ADMIN_HTML.exists():
        return web.Response(text="后台页面未找到", status=404)
    return web.Response(
        body=BAOJIA_ADMIN_HTML.read_bytes(),
        content_type="text/html",
    )


@baojia_web_require_auth
async def baojia_web_countries(baojia_request):  # noqa: ARG001
    """返回已有报价的国家列表。"""
    return web.json_response({"countries": baojia_utils.baojia_list_countries()})


@baojia_web_require_auth
async def baojia_web_stats(baojia_request):  # noqa: ARG001
    """顶部数据汇总：国家总数、报价总条数、今日/本周/本月记录条数。"""
    return web.json_response(baojia_utils.baojia_overview_stats())


@baojia_web_require_auth
async def baojia_web_quotes_list(baojia_request):
    """报价列表，支持国家/类型/料性筛选。"""
    baojia_country = baojia_request.query.get("country")
    baojia_type = baojia_request.query.get("type")
    baojia_material = baojia_request.query.get("material")
    baojia_group_id = baojia_request.query.get("group_id")
    baojia_parent_group = baojia_request.query.get("parent_group")
    baojia_group_name = baojia_request.query.get("group_name")
    baojia_rows = baojia_utils.baojia_quotes_list(
        baojia_country=baojia_country,
        baojia_type=baojia_type,
        baojia_material=baojia_material,
        baojia_group_id=baojia_group_id,
        baojia_parent_group=baojia_parent_group,
        baojia_group_name=baojia_group_name,
    )
    return web.json_response([baojia_row_to_dict(r) for r in baojia_rows])


@baojia_web_require_auth
async def baojia_web_quotes_create(baojia_request):
    """新建报价（复用 baojia_save_quote 的维度查重逻辑）。"""
    baojia_data = await baojia_read_json(baojia_request)
    if not baojia_data:
        return web.json_response({"ok": False, "error": "请求体不是合法 JSON"}, status=400)
    baojia_draft = baojia_build_draft(baojia_data)
    if not baojia_draft["baojia_country"] or not baojia_draft["baojia_group_id"]:
        return web.json_response({"ok": False, "error": "国家和群组 ID 必填"}, status=400)
    baojia_user_id = baojia_request["baojia_user"]["baojia_user_id"]
    baojia_quote_id, baojia_action = baojia_utils.baojia_save_quote(baojia_draft, baojia_user_id)
    return web.json_response({"ok": True, "id": baojia_quote_id, "action": baojia_action})


@baojia_web_require_auth
async def baojia_web_quotes_update(baojia_request):
    """按 ID 更新报价。"""
    baojia_quote_id = int(baojia_request.match_info["baojia_quote_id"])
    baojia_data = await baojia_read_json(baojia_request)
    if not baojia_data:
        return web.json_response({"ok": False, "error": "请求体不是合法 JSON"}, status=400)
    baojia_draft = baojia_build_draft(baojia_data)
    if not baojia_draft["baojia_country"] or not baojia_draft["baojia_group_id"]:
        return web.json_response({"ok": False, "error": "国家和群组 ID 必填"}, status=400)
    baojia_user_id = baojia_request["baojia_user"]["baojia_user_id"]
    baojia_row = baojia_utils.baojia_update_quote_by_id(baojia_quote_id, baojia_draft, baojia_user_id)
    if baojia_row is None:
        return web.json_response({"ok": False, "error": "报价不存在"}, status=404)
    return web.json_response({"ok": True})


@baojia_web_require_auth
async def baojia_web_quotes_delete(baojia_request):
    """按 ID 删除报价（写历史）。"""
    baojia_quote_id = int(baojia_request.match_info["baojia_quote_id"])
    baojia_user_id = baojia_request["baojia_user"]["baojia_user_id"]
    baojia_row = baojia_utils.baojia_delete_quote(baojia_quote_id, baojia_user_id)
    if baojia_row is None:
        return web.json_response({"ok": False, "error": "报价不存在"}, status=404)
    return web.json_response({"ok": True})


# ==================== 应用构建 ====================

async def baojia_web_on_startup(baojia_app):  # noqa: ARG001
    """应用启动时确保存在 Web 管理员账号。"""
    baojia_utils.baojia_ensure_web_admin()


def baojia_create_web_app():
    """构建 aiohttp 应用。"""
    baojia_app = web.Application()
    baojia_app.on_startup.append(baojia_web_on_startup)
    baojia_app.router.add_get("/", baojia_web_index)
    baojia_app.router.add_post("/api/login", baojia_web_login)
    baojia_app.router.add_post("/api/logout", baojia_web_logout)
    baojia_app.router.add_get("/api/me", baojia_web_me)
    baojia_app.router.add_post("/api/me/password", baojia_web_change_own_password)
    baojia_app.router.add_get("/api/users", baojia_web_users_list)
    baojia_app.router.add_post("/api/users", baojia_web_users_create)
    baojia_app.router.add_put("/api/users/{baojia_user_id}", baojia_web_users_update)
    baojia_app.router.add_post("/api/users/{baojia_user_id}/password", baojia_web_users_reset_password)
    baojia_app.router.add_delete("/api/users/{baojia_user_id}", baojia_web_users_delete)
    baojia_app.router.add_get("/api/countries", baojia_web_countries)
    baojia_app.router.add_get("/api/stats", baojia_web_stats)
    baojia_app.router.add_get("/api/quotes", baojia_web_quotes_list)
    baojia_app.router.add_post("/api/quotes", baojia_web_quotes_create)
    baojia_app.router.add_put("/api/quotes/{baojia_quote_id}", baojia_web_quotes_update)
    baojia_app.router.add_delete("/api/quotes/{baojia_quote_id}", baojia_web_quotes_delete)
    return baojia_app
