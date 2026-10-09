"""baojia 报价机器人 - 启动与主菜单处理器

包含 /start 命令、主菜单回调、/cancel 命令、全局错误处理。
"""

import traceback

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import baojia_keyboards
import baojia_texts
import baojia_utils


async def baojia_cmd_start(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """/start 命令：登记用户并展示主菜单。"""
    baojia_user = baojia_update.effective_user
    if not baojia_user:
        return ConversationHandler.END
    baojia_utils.baojia_register_user(baojia_user)
    if not baojia_utils.baojia_can_use(baojia_user.id):
        await baojia_update.effective_message.reply_text(
            baojia_texts.BAOJIA_TEXT_DENIED.format(baojia_user_id=baojia_user.id),
        )
        return ConversationHandler.END
    baojia_is_admin = baojia_utils.baojia_is_admin(baojia_user.id)
    await baojia_update.effective_message.reply_text(
        baojia_texts.baojia_text_main_menu(baojia_is_admin),
        reply_markup=baojia_keyboards.baojia_keyboard_main(baojia_is_admin),
    )
    return ConversationHandler.END


async def baojia_cmd_cancel(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """/cancel 命令：结束任何对话并返回主菜单。"""
    baojia_user = baojia_update.effective_user
    if baojia_user:
        baojia_utils.baojia_register_user(baojia_user)
    if baojia_context.user_data:
        baojia_context.user_data.clear()
    await baojia_update.effective_message.reply_text(
        baojia_texts.BAOJIA_TEXT_CANCELLED,
        reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
    )
    return ConversationHandler.END


@baojia_utils.baojia_operator_only
async def baojia_on_menu_home(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """主菜单回调：返回主菜单。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_user = baojia_update.effective_user
    baojia_utils.baojia_register_user(baojia_user)
    if baojia_context.user_data:
        baojia_context.user_data.clear()
    baojia_is_admin = baojia_utils.baojia_is_admin(baojia_user.id)
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_main_menu(baojia_is_admin),
        reply_markup=baojia_keyboards.baojia_keyboard_main(baojia_is_admin),
    )
    return ConversationHandler.END


async def baojia_on_error(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """全局错误处理器：记录日志并回复用户。"""
    print("[baojia error]", traceback.format_exc())
    try:
        if baojia_update and baojia_update.effective_message:
            await baojia_update.effective_message.reply_text(
                "操作出错，已记录日志。可发送 /cancel 后重试，或联系管理员。",
                reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
            )
    except Exception:
        pass
