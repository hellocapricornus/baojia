"""baojia 报价机器人 - 报价删除处理器

流程：
- 主菜单「删除报价」-> 选择方式（按国家/按群组）
- 按国家：选择国家 -> 列出该国报价 -> 选条目 -> 确认删除
- 按群组：输入群组 ID -> 列出该群报价 -> 选条目 -> 确认删除
- 群组查询结果页「删除该群报价」按钮可直接进入该群的删除列表
删除会写入历史表（action=delete），可在群更新历史中追溯。
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import baojia_keyboards
import baojia_states
import baojia_texts
import baojia_utils

BAOJIA_DEL_CTX_KEY = "baojia_del_ctx"


# ==================== 入口 ====================

@baojia_utils.baojia_operator_only
async def baojia_on_del_menu(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """主菜单 -> 删除报价。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_context.user_data[BAOJIA_DEL_CTX_KEY] = {}
    await baojia_query.edit_message_text(
        baojia_texts.BAOJIA_TEXT_DEL_MENU,
        reply_markup=baojia_keyboards.baojia_keyboard_del_mode(),
    )
    return baojia_states.BAOJIA_STATE_DEL_MODE


@baojia_utils.baojia_operator_only
async def baojia_on_del_from_group(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """群查询结果页 -> 删除该群报价（直接进入该群的删除列表）。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_group_id = int(baojia_query.data.replace("baojia_grp_del_", ""))
    baojia_rows = baojia_utils.baojia_quotes_by_group(baojia_group_id)
    if not baojia_rows:
        await baojia_query.edit_message_text(
            "该群组暂无报价，无需删除。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_context.user_data[BAOJIA_DEL_CTX_KEY] = {
        "mode": "group",
        "group_id": baojia_group_id,
    }
    baojia_title = f"群【{baojia_rows[0]['baojia_group_name']}】"
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_del_list(baojia_title, baojia_rows),
        reply_markup=baojia_keyboards.baojia_keyboard_del_quotes(
            baojia_rows, baojia_show_country=True
        ),
    )
    return baojia_states.BAOJIA_STATE_DEL_SELECT


# ==================== 选择删除方式 ====================

async def baojia_on_del_mode_country(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """按国家删除：列出全部国家。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_countries = baojia_utils.baojia_list_countries()
    if not baojia_countries:
        await baojia_query.edit_message_text(
            "暂无任何报价，无需删除。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_context.user_data[BAOJIA_DEL_CTX_KEY] = {
        "mode": "country",
        "countries": baojia_countries,
    }
    await baojia_query.edit_message_text(
        "请选择要删除报价的国家：",
        reply_markup=baojia_keyboards.baojia_keyboard_del_countries(baojia_countries),
    )
    return baojia_states.BAOJIA_STATE_DEL_COUNTRY


async def baojia_on_del_mode_group(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """按群组删除：引导输入群组 ID。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_context.user_data[BAOJIA_DEL_CTX_KEY] = {"mode": "group"}
    await baojia_query.edit_message_text(
        "请发送要删除报价的群组 ID（如 -1001234567890 或 1234567890）：",
        reply_markup=baojia_keyboards.baojia_keyboard_del_cancel(),
    )
    return baojia_states.BAOJIA_STATE_DEL_GROUP_ID


# ==================== 国家 / 群组 -> 报价列表 ====================

async def baojia_on_del_country(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """选择国家，列出该国全部报价。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_ctx = baojia_context.user_data.get(BAOJIA_DEL_CTX_KEY) or {}
    baojia_countries = baojia_ctx.get("countries") or []
    baojia_idx = int(baojia_query.data.replace("baojia_del_c_", ""))
    if baojia_idx >= len(baojia_countries):
        await baojia_query.edit_message_text(
            baojia_texts.BAOJIA_TEXT_DEL_EXPIRED,
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_country = baojia_countries[baojia_idx]
    baojia_rows = baojia_utils.baojia_quotes_by_country(baojia_country)
    if not baojia_rows:
        await baojia_query.edit_message_text(
            "该国家下已无报价。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_ctx["country"] = baojia_country
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_del_list(f"【{baojia_country}】", baojia_rows),
        reply_markup=baojia_keyboards.baojia_keyboard_del_quotes(
            baojia_rows, baojia_show_parent=True
        ),
    )
    return baojia_states.BAOJIA_STATE_DEL_SELECT


async def baojia_on_del_group_id(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """按群组删除：解析群 ID 并列出该群全部报价。"""
    baojia_group_id = baojia_utils.baojia_parse_group_id(baojia_update.message.text)
    if baojia_group_id is None:
        await baojia_update.message.reply_text(
            "群组 ID 格式不正确，请输入 -100 开头的完整 ID 或 10 位以上纯数字：",
            reply_markup=baojia_keyboards.baojia_keyboard_del_cancel(),
        )
        return baojia_states.BAOJIA_STATE_DEL_GROUP_ID
    baojia_rows = baojia_utils.baojia_quotes_by_group(baojia_group_id)
    if not baojia_rows:
        await baojia_update.message.reply_text(
            f"群组 {baojia_group_id} 暂无报价，无需删除。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_context.user_data[BAOJIA_DEL_CTX_KEY] = {
        "mode": "group",
        "group_id": baojia_group_id,
    }
    baojia_title = f"群【{baojia_rows[0]['baojia_group_name']}】"
    await baojia_update.message.reply_text(
        baojia_texts.baojia_text_del_list(baojia_title, baojia_rows),
        reply_markup=baojia_keyboards.baojia_keyboard_del_quotes(
            baojia_rows, baojia_show_country=True
        ),
    )
    return baojia_states.BAOJIA_STATE_DEL_SELECT


# ==================== 选择报价 -> 确认 -> 删除 ====================

async def baojia_on_del_select(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """选择要删除的报价，进入确认页。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_quote_id = int(baojia_query.data.replace("baojia_del_q_", ""))
    baojia_row = baojia_utils.baojia_quote_by_id(baojia_quote_id)
    if not baojia_row:
        await baojia_query.edit_message_text(
            "该报价已被删除或不存在。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_del_confirm(baojia_row),
        reply_markup=baojia_keyboards.baojia_keyboard_del_confirm(baojia_quote_id),
        disable_web_page_preview=True,
    )
    return baojia_states.BAOJIA_STATE_DEL_CONFIRM


async def baojia_on_del_back(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """确认页返回报价列表（按当前删除方式重新拉取）。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_ctx = baojia_context.user_data.get(BAOJIA_DEL_CTX_KEY) or {}
    baojia_rows = []
    baojia_title = ""
    baojia_show_country = False
    baojia_show_parent = False
    if baojia_ctx.get("mode") == "country" and baojia_ctx.get("country"):
        baojia_rows = baojia_utils.baojia_quotes_by_country(baojia_ctx["country"])
        baojia_title = f"【{baojia_ctx['country']}】"
        baojia_show_parent = True
    elif baojia_ctx.get("mode") == "group" and baojia_ctx.get("group_id"):
        baojia_rows = baojia_utils.baojia_quotes_by_group(baojia_ctx["group_id"])
        if baojia_rows:
            baojia_title = f"群【{baojia_rows[0]['baojia_group_name']}】"
        baojia_show_country = True
    if not baojia_rows:
        await baojia_query.edit_message_text(
            "该范围下已无报价。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_del_list(baojia_title, baojia_rows),
        reply_markup=baojia_keyboards.baojia_keyboard_del_quotes(
            baojia_rows, baojia_show_country=baojia_show_country,
            baojia_show_parent=baojia_show_parent,
        ),
    )
    return baojia_states.BAOJIA_STATE_DEL_SELECT


async def baojia_on_del_ok(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """确认删除。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_quote_id = int(baojia_query.data.replace("baojia_del_ok_", ""))
    baojia_user = baojia_update.effective_user
    baojia_row = baojia_utils.baojia_delete_quote(baojia_quote_id, baojia_user.id)
    if not baojia_row:
        await baojia_query.edit_message_text(
            "该报价已被删除或不存在。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_context.user_data.pop(BAOJIA_DEL_CTX_KEY, None)
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_del_done(baojia_row),
        reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        disable_web_page_preview=True,
    )
    return ConversationHandler.END


async def baojia_on_del_cancel(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """取消删除，返回主菜单。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_context.user_data.pop(BAOJIA_DEL_CTX_KEY, None)
    baojia_is_admin = baojia_utils.baojia_is_admin(baojia_update.effective_user.id)
    await baojia_query.edit_message_text(
        baojia_texts.BAOJIA_TEXT_CANCELLED,
        reply_markup=baojia_keyboards.baojia_keyboard_main(baojia_is_admin),
    )
    return ConversationHandler.END
