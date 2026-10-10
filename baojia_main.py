"""baojia 报价机器人 - 程序入口

启动流程：初始化数据库 -> 构建 Application -> 注册各模块处理器 -> 开始轮询。
"""

import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Defaults,
    MessageHandler,
    filters,
)

import baojia_config
import baojia_database
import baojia_keyboards
import baojia_states
import baojia_utils
import baojia_handler_start
import baojia_handler_entry
import baojia_handler_del
import baojia_handler_group
import baojia_handler_admin


def baojia_setup_logging():
    """配置日志格式与级别。"""
    baojia_level = getattr(logging, baojia_config.baojia_LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=baojia_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def baojia_register_handlers(baojia_app):
    """注册全部处理器。"""

    # ---------- 主菜单回调 ----------
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_start.baojia_on_menu_home,
            pattern=r"^baojia_menu_home$",
        )
    )

    # ---------- /start /cancel ----------
    baojia_app.add_handler(CommandHandler("start", baojia_handler_start.baojia_cmd_start))
    baojia_app.add_handler(CommandHandler("cancel", baojia_handler_start.baojia_cmd_cancel))

    # ---------- 报价录入对话 ----------
    baojia_entry_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                baojia_handler_entry.baojia_on_entry_menu,
                pattern=r"^baojia_menu_add$",
            )
        ],
        states={
            baojia_states.BAOJIA_STATE_ENTRY_TYPE: [
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_type,
                    pattern=r"^baojia_entry_type_(collect|pay)$",
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_COUNTRY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_country,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_MATERIAL: [
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_material,
                    pattern=r"^baojia_entry_mat_(?!__manual__$).+$",
                ),
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_material_input,
                    pattern=r"^baojia_entry_mat___manual__$",
                ),
            ],
            baojia_states.BAOJIA_STATE_ENTRY_MATERIAL_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_material_text,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_ACCOUNT: [
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_account,
                    pattern=r"^baojia_entry_acc_(?!__manual__$).+$",
                ),
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_account_input,
                    pattern=r"^baojia_entry_acc___manual__$",
                ),
            ],
            baojia_states.BAOJIA_STATE_ENTRY_ACCOUNT_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_account_text,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_SETTLE: [
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_settle,
                    pattern=r"^baojia_entry_set_(?!__manual__$).+$",
                ),
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_settle_input,
                    pattern=r"^baojia_entry_set___manual__$",
                ),
            ],
            baojia_states.BAOJIA_STATE_ENTRY_SETTLE_INPUT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_settle_text,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_FEE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_fee,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_RATE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_rate,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_SINGLE_FEE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_single_fee,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_GROUP_ID: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_group_id,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_GROUP_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_group_name,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_PARENT_GROUP: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_parent_group,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_SALES: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_entry.baojia_on_entry_sales,
                )
            ],
            baojia_states.BAOJIA_STATE_ENTRY_CONFIRM: [
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_save,
                    pattern=r"^baojia_entry_save$",
                ),
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_cancel,
                    pattern=r"^baojia_entry_cancel$",
                ),
            ],
            baojia_states.BAOJIA_STATE_ENTRY_CONFLICT: [
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_overwrite,
                    pattern=r"^baojia_entry_overwrite$",
                ),
                CallbackQueryHandler(
                    baojia_handler_entry.baojia_on_entry_cancel,
                    pattern=r"^baojia_entry_cancel$",
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", baojia_handler_start.baojia_cmd_cancel),
            CallbackQueryHandler(
                baojia_handler_entry.baojia_on_entry_cancel,
                pattern=r"^baojia_entry_cancel$",
            ),
        ],
        allow_reentry=True,
        name="baojia_entry_conversation",
    )
    baojia_app.add_handler(baojia_entry_conv)

    # ---------- 报价删除对话 ----------
    baojia_del_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                baojia_handler_del.baojia_on_del_menu,
                pattern=r"^baojia_menu_del$",
            ),
            CallbackQueryHandler(
                baojia_handler_del.baojia_on_del_from_group,
                pattern=r"^baojia_grp_del_-?\d+$",
            ),
        ],
        states={
            baojia_states.BAOJIA_STATE_DEL_MODE: [
                CallbackQueryHandler(
                    baojia_handler_del.baojia_on_del_mode_country,
                    pattern=r"^baojia_del_mode_country$",
                ),
                CallbackQueryHandler(
                    baojia_handler_del.baojia_on_del_mode_group,
                    pattern=r"^baojia_del_mode_group$",
                ),
            ],
            baojia_states.BAOJIA_STATE_DEL_COUNTRY: [
                CallbackQueryHandler(
                    baojia_handler_del.baojia_on_del_country,
                    pattern=r"^baojia_del_c_\d+$",
                ),
            ],
            baojia_states.BAOJIA_STATE_DEL_GROUP_ID: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_del.baojia_on_del_group_id,
                ),
            ],
            baojia_states.BAOJIA_STATE_DEL_SELECT: [
                CallbackQueryHandler(
                    baojia_handler_del.baojia_on_del_select,
                    pattern=r"^baojia_del_q_\d+$",
                ),
            ],
            baojia_states.BAOJIA_STATE_DEL_CONFIRM: [
                CallbackQueryHandler(
                    baojia_handler_del.baojia_on_del_ok,
                    pattern=r"^baojia_del_ok_\d+$",
                ),
                CallbackQueryHandler(
                    baojia_handler_del.baojia_on_del_back,
                    pattern=r"^baojia_del_back$",
                ),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", baojia_handler_start.baojia_cmd_cancel),
            CallbackQueryHandler(
                baojia_handler_del.baojia_on_del_cancel,
                pattern=r"^baojia_del_cancel$",
            ),
        ],
        allow_reentry=True,
        name="baojia_del_conversation",
    )
    baojia_app.add_handler(baojia_del_conv)

    # ---------- 操作员管理对话 ----------
    baojia_emp_add_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                baojia_handler_admin.baojia_on_emp_add,
                pattern=r"^baojia_admin_emp_add$",
            )
        ],
        states={
            baojia_states.BAOJIA_STATE_ADMIN_EMP_ADD: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    baojia_handler_admin.baojia_on_emp_add_done,
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", baojia_handler_start.baojia_cmd_cancel)],
        allow_reentry=True,
        name="baojia_emp_add_conversation",
    )
    baojia_app.add_handler(baojia_emp_add_conv)

    # ---------- 群内查询 ----------

    # 群消息国家名匹配（只处理群消息，不过滤命令）
    baojia_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            baojia_handler_group.baojia_on_group_country,
        )
    )

    # 展开/收起（每个料性独立）
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_group.baojia_on_gq_expand,
            pattern=r"^baojia_gq_exp_\d+$",
        )
    )
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_group.baojia_on_gq_collapse,
            pattern=r"^baojia_gq_col_\d+$",
        )
    )

    # 私聊群 ID 查询（只处理纯文本私聊消息）
    baojia_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            baojia_handler_group.baojia_on_group_query,
        )
    )
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_group.baojia_on_group_history,
            pattern=r"^baojia_grp_hist_.+$",
        )
    )

    # ---------- 操作员管理（单步） ----------

    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_admin.baojia_on_admin_menu,
            pattern=r"^baojia_menu_admin$",
        )
    )
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_admin.baojia_on_emp_list,
            pattern=r"^baojia_admin_emp_list$",
        )
    )
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_admin.baojia_on_emp_view,
            pattern=r"^baojia_admin_emp_view_\d+$",
        )
    )
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_admin.baojia_on_emp_active,
            pattern=r"^baojia_admin_emp_active_\d+_[01]$",
        )
    )
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_admin.baojia_on_emp_del,
            pattern=r"^baojia_admin_emp_del_\d+$",
        )
    )
    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_handler_admin.baojia_on_emp_delok,
            pattern=r"^baojia_admin_emp_delok_\d+$",
        )
    )

    # ---------- 群组查询入口（菜单） ----------

    async def baojia_on_menu_group(baojia_update, baojia_context):  # noqa: ARG001
        baojia_query = baojia_update.callback_query
        await baojia_utils.baojia_safe_answer(baojia_query)
        await baojia_query.edit_message_text(
            "请直接发送群组 ID（如 -1001234567890 或 1234567890）：",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END

    baojia_on_menu_group = baojia_utils.baojia_operator_only(baojia_on_menu_group)

    baojia_app.add_handler(
        CallbackQueryHandler(
            baojia_on_menu_group,
            pattern=r"^baojia_menu_group$",
        )
    )

    # ---------- 全局错误 ----------
    baojia_app.add_error_handler(baojia_handler_start.baojia_on_error)


def baojia_run():
    """主函数。"""
    baojia_setup_logging()
    baojia_logger = logging.getLogger("baojia_main")

    baojia_token = baojia_config.baojia_BOT_TOKEN
    if not baojia_token:
        baojia_logger.error("未配置 baojia_BOT_TOKEN，请检查 baojia.env 文件。")
        raise SystemExit(1)

    baojia_logger.info("初始化数据库...")
    baojia_database.baojia_init_db()

    baojia_logger.info("启动机器人...")
    # 全局默认 HTML 解析：支持 <blockquote> 引用块与 <a> 超链接
    baojia_app = (
        Application.builder()
        .token(baojia_token)
        .defaults(Defaults(parse_mode=ParseMode.HTML))
        .build()
    )
    baojia_register_handlers(baojia_app)
    baojia_app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    baojia_run()
