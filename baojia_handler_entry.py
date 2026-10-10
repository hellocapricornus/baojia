"""baojia 报价机器人 - 报价录入处理器

对话流程：
类型 -> 国家 -> 料性（按钮/手动）-> 账户类别（按钮/手动）
-> 结算方式（按钮/手动）-> 手续费 -> 汇率 -> 代付单笔费用（仅代付）
-> 群组ID -> 群名称 -> 业务员 -> 备注（可跳过）-> 确认/冲突覆盖 -> 保存
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import baojia_config
import baojia_keyboards
import baojia_states
import baojia_texts
import baojia_utils

BAOJIA_DRAFT_KEY = "baojia_entry_draft"
BAOJIA_PENDING_KEY = "baojia_entry_pending_conflict"


# ==================== 入口 ====================

@baojia_utils.baojia_operator_only
async def baojia_on_entry_menu(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """主菜单 -> 录入报价。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_context.user_data[BAOJIA_DRAFT_KEY] = {}
    baojia_context.user_data[BAOJIA_PENDING_KEY] = None
    await baojia_query.edit_message_text(
        "请选择报价类型：",
        reply_markup=baojia_keyboards.baojia_keyboard_entry_type(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_TYPE


async def baojia_on_entry_type(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """选择类型（代收/代付）。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_type = "collect" if "_collect" in baojia_query.data else "pay"
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_type"] = baojia_type
    await baojia_query.edit_message_text(
        f"类型：{baojia_config.BAOJIA_TYPE_LABELS[baojia_type]}\n\n请输入国家名称（如：坦桑尼亚）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_COUNTRY


# ==================== 国家 ====================

async def baojia_on_entry_country(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入国家。"""
    baojia_country = baojia_update.message.text.strip()
    if not baojia_country:
        await baojia_update.message.reply_text(
            "国家名称不能为空，请重新输入：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_COUNTRY
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_country"] = baojia_country
    await baojia_update.message.reply_text(
        f"国家：{baojia_utils.baojia_esc(baojia_country)}\n\n请选择料性：",
        reply_markup=baojia_keyboards.baojia_keyboard_preset(
            baojia_config.BAOJIA_PRESET_MATERIALS, "baojia_entry_mat_"
        ),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_MATERIAL


# ==================== 料性 ====================

async def baojia_on_entry_material(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """选择预设料性。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_material = baojia_query.data.replace("baojia_entry_mat_", "")
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_material"] = baojia_material
    return await baojia_step_account(baojia_query)


async def baojia_on_entry_material_input(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """手动输入料性。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    await baojia_query.edit_message_text(
        "请输入料性名称：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_MATERIAL_INPUT


async def baojia_on_entry_material_text(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """接收手动料性文本。"""
    baojia_text = baojia_update.message.text.strip()
    if not baojia_text:
        await baojia_update.message.reply_text(
            "料性不能为空，请重新输入：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_MATERIAL_INPUT
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_material"] = baojia_text
    return await baojia_step_account(baojia_update)


# ==================== 账户类别 ====================

async def baojia_step_account(baojia_target):
    """引导选择账户类别。兼容 callback_query 和 message 两种场景。"""
    if hasattr(baojia_target, "edit_message_text"):
        await baojia_target.edit_message_text(
            "请选择账户类别：",
            reply_markup=baojia_keyboards.baojia_keyboard_preset(
                baojia_config.BAOJIA_PRESET_ACCOUNTS, "baojia_entry_acc_"
            ),
        )
    else:
        await baojia_target.effective_message.reply_text(
            "请选择账户类别：",
            reply_markup=baojia_keyboards.baojia_keyboard_preset(
                baojia_config.BAOJIA_PRESET_ACCOUNTS, "baojia_entry_acc_"
            ),
        )
    return baojia_states.BAOJIA_STATE_ENTRY_ACCOUNT


async def baojia_on_entry_account(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """选择预设账户类别。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_account = baojia_query.data.replace("baojia_entry_acc_", "")
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_account_type"] = baojia_account
    return await baojia_step_settle(baojia_query)


async def baojia_on_entry_account_input(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """手动输入账户类别。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    await baojia_query.edit_message_text(
        "请输入账户类别：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_ACCOUNT_INPUT


async def baojia_on_entry_account_text(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """接收手动账户类别文本。"""
    baojia_text = baojia_update.message.text.strip()
    if not baojia_text:
        await baojia_update.message.reply_text(
            "账户类别不能为空，请重新输入：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_ACCOUNT_INPUT
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_account_type"] = baojia_text
    return await baojia_step_settle(baojia_update)


# ==================== 结算方式 ====================

async def baojia_step_settle(baojia_target):
    """引导选择结算方式。"""
    if hasattr(baojia_target, "edit_message_text"):
        await baojia_target.edit_message_text(
            "请选择结算方式：",
            reply_markup=baojia_keyboards.baojia_keyboard_preset(
                baojia_config.BAOJIA_PRESET_SETTLES, "baojia_entry_set_"
            ),
        )
    else:
        await baojia_target.effective_message.reply_text(
            "请选择结算方式：",
            reply_markup=baojia_keyboards.baojia_keyboard_preset(
                baojia_config.BAOJIA_PRESET_SETTLES, "baojia_entry_set_"
            ),
        )
    return baojia_states.BAOJIA_STATE_ENTRY_SETTLE


async def baojia_on_entry_settle(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """选择预设结算方式。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_settle = baojia_query.data.replace("baojia_entry_set_", "")
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_settle_method"] = baojia_settle
    await baojia_query.edit_message_text(
        "请输入手续费百分比（如：8 表示 8%）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_FEE


async def baojia_on_entry_settle_input(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):  # noqa: ARG001
    """手动输入结算方式。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    await baojia_query.edit_message_text(
        "请输入结算方式：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_SETTLE_INPUT


async def baojia_on_entry_settle_text(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """接收手动结算方式文本。"""
    baojia_text = baojia_update.message.text.strip()
    if not baojia_text:
        await baojia_update.message.reply_text(
            "结算方式不能为空，请重新输入：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_SETTLE_INPUT
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_settle_method"] = baojia_text
    await baojia_update.effective_message.reply_text(
        "请输入手续费百分比（如：8 表示 8%）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_FEE


# ==================== 手续费 + 汇率 + 单笔费用 ====================

async def baojia_on_entry_fee(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入手续费。"""
    baojia_value = baojia_utils.baojia_parse_nonneg(baojia_update.message.text)
    if baojia_value is None:
        await baojia_update.message.reply_text(
            baojia_texts.BAOJIA_TEXT_INPUT_INVALID + "\n\n手续费请输入 >=0 的数字（如 8 表示 8%）：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_FEE
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_fee_rate"] = baojia_value
    await baojia_update.message.reply_text(
        "请输入汇率（如：2820）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_RATE


async def baojia_on_entry_rate(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入汇率。"""
    baojia_value = baojia_utils.baojia_parse_number(baojia_update.message.text)
    if baojia_value is None:
        await baojia_update.message.reply_text(
            baojia_texts.BAOJIA_TEXT_INPUT_INVALID + "\n\n汇率请输入大于 0 的数字：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_RATE
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_rate"] = baojia_value
    if baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_type"] == baojia_config.BAOJIA_TYPE_PAY:
        await baojia_update.message.reply_text(
            "请输入单笔费用（如：1500），没有则输入 0：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_SINGLE_FEE
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_single_fee"] = 0
    await baojia_update.message.reply_text(
        "请输入群组 ID（如 -1001234567890 或 1234567890）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_GROUP_ID


async def baojia_on_entry_single_fee(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入代付单笔费用。"""
    baojia_value = baojia_utils.baojia_parse_nonneg(baojia_update.message.text)
    if baojia_value is None:
        await baojia_update.message.reply_text(
            baojia_texts.BAOJIA_TEXT_INPUT_INVALID + "\n\n单笔费用请输入 >=0 的数字，没有则输入 0：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_SINGLE_FEE
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_single_fee"] = baojia_value
    await baojia_update.message.reply_text(
        "请输入群组 ID（如 -1001234567890 或 1234567890）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_GROUP_ID


# ==================== 群组 ID + 群名 + 业务员 ====================

async def baojia_on_entry_group_id(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入群组 ID。"""
    baojia_group_id = baojia_utils.baojia_parse_group_id(baojia_update.message.text)
    if baojia_group_id is None:
        await baojia_update.message.reply_text(
            "群组 ID 格式不正确。\n"
            "请提供完整群 ID（如 -1001234567890），或输入纯数字（10 位以上，自动补全）：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_GROUP_ID
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_group_id"] = baojia_group_id
    await baojia_update.message.reply_text(
        f"群组 ID：{baojia_group_id}\n\n请输入群名称：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_GROUP_NAME


async def baojia_on_entry_group_name(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入群名称。"""
    baojia_name = baojia_update.message.text.strip()
    if not baojia_name:
        await baojia_update.message.reply_text(
            "群名称不能为空，请重新输入：",
            reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_GROUP_NAME
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_group_name"] = baojia_name
    await baojia_update.message.reply_text(
        f"群名称：{baojia_utils.baojia_esc(baojia_name)}\n\n请输入所属公群（如没有可输入 0 跳过）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_PARENT_GROUP


async def baojia_on_entry_parent_group(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入所属公群。"""
    baojia_parent = baojia_update.message.text.strip()
    if baojia_parent == "0":
        baojia_parent = ""
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_parent_group"] = baojia_parent
    await baojia_update.message.reply_text(
        f"所属公群：{baojia_utils.baojia_esc(baojia_parent) if baojia_parent else '无'}\n\n请输入业务员（如 @zhangsan）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_SALES


async def baojia_on_entry_sales(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入业务员，引导输入备注。"""
    baojia_sales = baojia_update.message.text.strip()
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_sales"] = baojia_sales
    await baojia_update.message.reply_text(
        f"业务员：{baojia_utils.baojia_esc(baojia_sales) if baojia_sales else '未填写'}\n\n"
        "请输入备注（如没有可输入 0 跳过）：",
        reply_markup=baojia_keyboards.baojia_keyboard_cancel_entry(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_REMARK


async def baojia_on_entry_remark(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """输入备注（可跳过），进入冲突检查。"""
    baojia_remark = baojia_update.message.text.strip()
    if baojia_remark == "0":
        baojia_remark = ""
    baojia_context.user_data[BAOJIA_DRAFT_KEY]["baojia_remark"] = baojia_remark
    baojia_draft = baojia_context.user_data[BAOJIA_DRAFT_KEY]
    baojia_existing = baojia_utils.baojia_find_quote(
        baojia_draft["baojia_type"], baojia_draft["baojia_country"],
        baojia_draft["baojia_material"], baojia_draft["baojia_account_type"],
        baojia_draft["baojia_settle_method"], baojia_draft["baojia_group_id"],
    )
    if baojia_existing:
        baojia_context.user_data[BAOJIA_PENDING_KEY] = baojia_existing
        await baojia_update.message.reply_text(
            baojia_texts.baojia_text_entry_conflict(baojia_existing),
            reply_markup=baojia_keyboards.baojia_keyboard_entry_conflict(),
        )
        return baojia_states.BAOJIA_STATE_ENTRY_CONFLICT
    return await baojia_step_confirm(baojia_update, baojia_context)


# ==================== 确认与保存 ====================

async def baojia_step_confirm(baojia_update, baojia_context):
    """展示确认信息。"""
    baojia_draft = baojia_context.user_data[BAOJIA_DRAFT_KEY]
    baojia_text = baojia_texts.baojia_text_entry_confirm(baojia_draft)
    await baojia_update.effective_message.reply_text(
        baojia_text,
        reply_markup=baojia_keyboards.baojia_keyboard_entry_confirm(),
    )
    return baojia_states.BAOJIA_STATE_ENTRY_CONFIRM


async def baojia_on_entry_save(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """确认保存（新建或覆盖更新）。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_draft = baojia_context.user_data.pop(BAOJIA_DRAFT_KEY, None)
    baojia_context.user_data.pop(BAOJIA_PENDING_KEY, None)
    if not baojia_draft:
        await baojia_query.edit_message_text(
            "报价信息已过期，请重新开始。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_user = baojia_update.effective_user
    _, baojia_action = baojia_utils.baojia_save_quote(baojia_draft, baojia_user.id)
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_entry_saved(baojia_draft, baojia_action),
        reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
    )
    return ConversationHandler.END


async def baojia_on_entry_overwrite(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """冲突时点击覆盖更新。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_draft = baojia_context.user_data.pop(BAOJIA_DRAFT_KEY, None)
    baojia_context.user_data.pop(BAOJIA_PENDING_KEY, None)
    if not baojia_draft:
        await baojia_query.edit_message_text(
            "报价信息已过期，请重新开始。",
            reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
        )
        return ConversationHandler.END
    baojia_user = baojia_update.effective_user
    _, baojia_action = baojia_utils.baojia_save_quote(baojia_draft, baojia_user.id)
    await baojia_query.edit_message_text(
        baojia_texts.baojia_text_entry_saved(baojia_draft, baojia_action),
        reply_markup=baojia_keyboards.baojia_keyboard_back_main(),
    )
    return ConversationHandler.END


async def baojia_on_entry_cancel(baojia_update: Update, baojia_context: ContextTypes.DEFAULT_TYPE):
    """取消录入。"""
    baojia_query = baojia_update.callback_query
    await baojia_utils.baojia_safe_answer(baojia_query)
    baojia_context.user_data.pop(BAOJIA_DRAFT_KEY, None)
    baojia_context.user_data.pop(BAOJIA_PENDING_KEY, None)
    baojia_is_admin = baojia_utils.baojia_is_admin(baojia_update.effective_user.id)
    await baojia_query.edit_message_text(
        baojia_texts.BAOJIA_TEXT_CANCELLED,
        reply_markup=baojia_keyboards.baojia_keyboard_main(baojia_is_admin),
    )
    return ConversationHandler.END
