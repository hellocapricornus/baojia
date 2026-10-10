"""baojia 报价机器人 - 操作员管理处理器（仅管理员）

支持：添加操作员、查看列表、启用/禁用、删除操作员。
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import baojia_database
import baojia_keyboards
import baojia_states
import baojia_utils

BAOJIA_DRAFT_KEY = "baojia_admin_draft"


# ==================== 菜单 ====================

@baojia_utils.baojia_admin_only
async def baojia_on_admin_menu(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """操作员管理主菜单。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    await baojia_query.edit_message_text(
        "操作员管理：",
        reply_markup=baojia_keyboards.baojia_keyboard_admin_menu(),
    )
    return ConversationHandler.END


# ==================== 添加操作员 ====================

@baojia_utils.baojia_admin_only
async def baojia_on_emp_add(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """引导输入操作员 Telegram ID。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    await baojia_query.edit_message_text(
        "请输入操作员的 Telegram 数字 ID（用户可通过 @userinfobot 查询）：",
        reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
    )
    return baojia_states.BAOJIA_STATE_ADMIN_EMP_ADD


async def baojia_on_emp_add_done(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """保存新操作员。"""
    baojia_user_id = baojia_utils.baojia_parse_int(baojia_update.message.text)
    if baojia_user_id is None:
        await baojia_update.message.reply_text(
            "请输入纯数字的 Telegram ID。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return baojia_states.BAOJIA_STATE_ADMIN_EMP_ADD
    baojia_existing = baojia_database.baojia_query_one(
        "SELECT baojia_role, baojia_is_active FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    if baojia_existing:
        baojia_status = "启用" if baojia_existing["baojia_is_active"] == 1 else "禁用"
        await baojia_update.message.reply_text(
            f"该用户已存在，角色：{baojia_existing['baojia_role']}，状态：{baojia_status}。",
            reply_markup=baojia_keyboards.baojia_keyboard_admin_menu(),
        )
        return ConversationHandler.END
    baojia_database.baojia_execute(
        "INSERT INTO baojia_users(baojia_user_id, baojia_full_name, baojia_role, baojia_is_active, baojia_created_at) "
        "VALUES (?, ?, 'operator', 1, ?)",
        (baojia_user_id, f"操作员{baojia_user_id}", baojia_utils.baojia_now()),
    )
    await baojia_update.message.reply_text(
        f"操作员 {baojia_user_id} 已添加。",
        reply_markup=baojia_keyboards.baojia_keyboard_admin_menu(),
    )
    return ConversationHandler.END


# ==================== 列表与详情 ====================

@baojia_utils.baojia_admin_only
async def baojia_on_emp_list(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """操作员列表。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_users = baojia_database.baojia_query(
        "SELECT baojia_user_id, baojia_full_name, baojia_role, baojia_is_active "
        "FROM baojia_users ORDER BY baojia_user_id"
    )
    if not baojia_users:
        await baojia_query.edit_message_text(
            "暂无操作员。",
            reply_markup=baojia_keyboards.baojia_keyboard_admin_menu(),
        )
        return ConversationHandler.END
    await baojia_query.edit_message_text(
        "操作员列表（点击查看/编辑）：",
        reply_markup=baojia_keyboards.baojia_keyboard_emp_list(baojia_users),
    )
    return ConversationHandler.END


@baojia_utils.baojia_admin_only
async def baojia_on_emp_view(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """查看操作员详情。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_user_id = baojia_utils.baojia_parse_int(baojia_query.data.split("_")[-1])
    baojia_user = baojia_database.baojia_query_one(
        "SELECT baojia_user_id, baojia_full_name, baojia_role, baojia_is_active "
        "FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    if not baojia_user:
        await baojia_query.edit_message_text(
            "操作员不存在。",
            reply_markup=baojia_keyboards.baojia_keyboard_admin_menu(),
        )
        return ConversationHandler.END
    baojia_status = "启用" if baojia_user["baojia_is_active"] == 1 else "禁用"
    await baojia_query.edit_message_text(
        f"操作员详情：\n\n"
        f"Telegram ID：{baojia_user['baojia_user_id']}\n"
        f"姓名：{baojia_utils.baojia_esc(baojia_user['baojia_full_name'])}\n"
        f"角色：{baojia_utils.baojia_esc(baojia_user['baojia_role'])}\n"
        f"状态：{baojia_status}",
        reply_markup=baojia_keyboards.baojia_keyboard_emp_actions(
            baojia_user_id, baojia_user["baojia_is_active"]
        ),
    )
    return ConversationHandler.END


# ==================== 启停 / 删除 ====================

@baojia_utils.baojia_admin_only
async def baojia_on_emp_active(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """启用/禁用操作员。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_parts = baojia_query.data.split("_")
    baojia_user_id = baojia_utils.baojia_parse_int(baojia_parts[-2])
    baojia_new_active = int(baojia_parts[-1])
    baojia_database.baojia_execute(
        "UPDATE baojia_users SET baojia_is_active = ? WHERE baojia_user_id = ?",
        (baojia_new_active, baojia_user_id),
    )
    baojia_label = "启用" if baojia_new_active == 1 else "禁用"
    await baojia_query.edit_message_text(
        f"操作员已{baojia_label}。",
        reply_markup=baojia_keyboards.baojia_keyboard_admin_menu(),
    )
    return ConversationHandler.END


@baojia_utils.baojia_admin_only
async def baojia_on_emp_del(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """删除操作员二次确认。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_user_id = baojia_utils.baojia_parse_int(baojia_query.data.split("_")[-1])
    baojia_user = baojia_database.baojia_query_one(
        "SELECT baojia_full_name FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    baojia_name = baojia_user["baojia_full_name"] if baojia_user else str(baojia_user_id)
    await baojia_query.edit_message_text(
        f"确定要删除操作员「{baojia_utils.baojia_esc(baojia_name)}」吗？",
        reply_markup=baojia_keyboards.baojia_keyboard_emp_del_confirm(baojia_user_id),
    )
    return ConversationHandler.END


@baojia_utils.baojia_admin_only
async def baojia_on_emp_delok(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """确认删除操作员。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_user_id = baojia_utils.baojia_parse_int(baojia_query.data.split("_")[-1])
    baojia_database.baojia_execute(
        "DELETE FROM baojia_users WHERE baojia_user_id = ?",
        (baojia_user_id,),
    )
    await baojia_query.edit_message_text(
        "操作员已删除。",
        reply_markup=baojia_keyboards.baojia_keyboard_admin_menu(),
    )
    return ConversationHandler.END
