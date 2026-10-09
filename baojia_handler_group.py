"""baojia 报价机器人 - 群内查询处理器

包含：
- 群消息国家名匹配 -> 折叠摘要回复（不引用原消息）
- 每个料性独立展开/收起
- 私聊群 ID 查询（群链接 + 业务员 + 该群全部报价详情）
- 群更新历史查询
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import baojia_database
import baojia_keyboards
import baojia_texts
import baojia_utils

BAOJIA_GQ_DATA_KEY = "baojia_gq_data"


def baojia_render_summary(baojia_country, baojia_rows, baojia_expanded):  # noqa: ARG001
    """渲染折叠摘要消息文本与键盘。"""
    baojia_indices = baojia_texts.baojia_material_indices(baojia_rows)
    baojia_text = baojia_texts.baojia_text_summary(baojia_country, baojia_rows, baojia_expanded)
    # 构建键盘：展开的料性显示收起按钮，未展开的显示展开按钮
    baojia_rows_kb = []
    for baojia_idx, (_, baojia_material) in enumerate(baojia_indices):
        if baojia_idx in baojia_expanded:
            baojia_rows_kb.append([baojia_keyboards.baojia_btn(f"收起 {baojia_material}", f"baojia_gq_col_{baojia_idx}")])
        else:
            baojia_rows_kb.append([baojia_keyboards.baojia_btn(f"展开 {baojia_material}", f"baojia_gq_exp_{baojia_idx}")])
    baojia_markup = baojia_keyboards.InlineKeyboardMarkup(baojia_rows_kb) if baojia_rows_kb else None
    return baojia_text, baojia_markup


# ==================== 群消息国家名匹配 ====================

@baojia_utils.baojia_operator_only
async def baojia_on_group_country(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """群消息匹配国家名，回复折叠摘要（不引用原消息）。"""
    baojia_text = baojia_update.message.text
    baojia_country = baojia_utils.baojia_match_country(baojia_text)
    if not baojia_country:
        return
    baojia_rows = baojia_utils.baojia_quotes_by_country(baojia_country)
    if not baojia_rows:
        return
    # 存储查询数据到 chat_data 供按钮回调使用
    baojia_context.chat_data[BAOJIA_GQ_DATA_KEY] = {
        "country": baojia_country,
        "rows": baojia_rows,
        "expanded": set(),
    }
    baojia_text_out, baojia_markup = baojia_render_summary(
        baojia_country, baojia_rows, set()
    )
    await baojia_update.message.chat.send_message(
        baojia_text_out,
        reply_markup=baojia_markup,
        disable_web_page_preview=True,
    )


# ==================== 展开/收起 ====================

@baojia_utils.baojia_operator_only
async def baojia_on_gq_expand(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """展开某个料性。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_idx = int(baojia_query.data.replace("baojia_gq_exp_", ""))
    baojia_data = baojia_context.chat_data.get(BAOJIA_GQ_DATA_KEY)
    if not baojia_data:
        # 数据丢失，重新查询
        await baojia_query.edit_message_text("查询数据已过期，请重新发送国家名称。")
        return
    baojia_data["expanded"].add(baojia_idx)
    baojia_text, baojia_markup = baojia_render_summary(
        baojia_data["country"], baojia_data["rows"], baojia_data["expanded"]
    )
    await baojia_query.edit_message_text(
        baojia_text,
        reply_markup=baojia_markup,
        disable_web_page_preview=True,
    )


@baojia_utils.baojia_operator_only
async def baojia_on_gq_collapse(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """收起某个料性。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_idx = int(baojia_query.data.replace("baojia_gq_col_", ""))
    baojia_data = baojia_context.chat_data.get(BAOJIA_GQ_DATA_KEY)
    if not baojia_data:
        await baojia_query.edit_message_text("查询数据已过期，请重新发送国家名称。")
        return
    baojia_data["expanded"].discard(baojia_idx)
    baojia_text, baojia_markup = baojia_render_summary(
        baojia_data["country"], baojia_data["rows"], baojia_data["expanded"]
    )
    await baojia_query.edit_message_text(
        baojia_text,
        reply_markup=baojia_markup,
        disable_web_page_preview=True,
    )


# ==================== 私聊群 ID 查询 ====================

@baojia_utils.baojia_operator_only
async def baojia_on_group_query(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """私聊收到群组 ID，输出群链接 + 业务员 + 该群全部报价详情。"""
    baojia_group_id = baojia_utils.baojia_parse_group_id(baojia_update.message.text)
    if baojia_group_id is None:
        await baojia_update.message.reply_text(
            "群组 ID 格式不正确，请输入 -100 开头的完整 ID 或 10 位以上纯数字。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return
    baojia_rows = baojia_utils.baojia_quotes_by_group(baojia_group_id)
    if not baojia_rows:
        await baojia_update.message.reply_text(
            f"群组 ID：{baojia_group_id}\n"
            "暂无该群组的报价信息。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return
    baojia_text = baojia_texts.baojia_text_group_info(baojia_group_id, baojia_rows)
    await baojia_update.message.reply_text(
        baojia_text,
        reply_markup=baojia_keyboards.baojia_keyboard_group_info(baojia_group_id),
        disable_web_page_preview=True,
    )


@baojia_utils.baojia_operator_only
async def baojia_on_group_history(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """查看群组更新历史。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_group_id = int(baojia_query.data.replace("baojia_grp_hist_", ""))
    baojia_rows = baojia_utils.baojia_history_by_group(baojia_group_id)
    baojia_group_name = baojia_database.baojia_query_one(
        "SELECT baojia_group_name FROM baojia_quotes WHERE baojia_group_id = ? LIMIT 1",
        (baojia_group_id,),
    )
    baojia_name = baojia_group_name["baojia_group_name"] if baojia_group_name else str(baojia_group_id)
    baojia_text = baojia_texts.baojia_text_group_history(baojia_name, baojia_rows)
    await baojia_query.edit_message_text(
        baojia_text,
        reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        disable_web_page_preview=True,
    )
