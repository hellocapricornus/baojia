"""baojia 报价机器人 - 内联键盘模块

所有按钮为纯文字（无 emoji），回调数据统一 baojia 前缀。
回调前缀约定：
- baojia_menu_*    主菜单
- baojia_entry_*   报价录入
- baojia_del_*     报价删除
- baojia_gq_*      群内报价展开/分页/收起
- baojia_grp_*     群 ID 查询（私聊）
- baojia_admin_*   操作员管理
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import baojia_config
import baojia_utils


def baojia_btn(baojia_text, baojia_callback):
    """快捷创建按钮。"""
    return InlineKeyboardButton(baojia_text, callback_data=baojia_callback)


def baojia_keyboard_main(baojia_admin_flag):
    """主菜单键盘。"""
    baojia_rows = [
        [baojia_btn("录入报价", "baojia_menu_add")],
        [baojia_btn("群组查询", "baojia_menu_group")],
        [baojia_btn("删除报价", "baojia_menu_del")],
    ]
    if baojia_admin_flag:
        baojia_rows.append([baojia_btn("操作员管理", "baojia_menu_admin")])
    return InlineKeyboardMarkup(baojia_rows)


def baojia_keyboard_back_main():
    """返回主菜单。"""
    return InlineKeyboardMarkup([[baojia_btn("返回主菜单", "baojia_menu_home")]])


# ==================== 录入流程 ====================

def baojia_keyboard_cancel_entry():
    """录入流程中的取消按钮。"""
    return InlineKeyboardMarkup([[baojia_btn("取消", "baojia_entry_cancel")]])


def baojia_keyboard_entry_type():
    """选择代收/代付。"""
    return InlineKeyboardMarkup([
        [baojia_btn("代收", "baojia_entry_type_collect"),
         baojia_btn("代付", "baojia_entry_type_pay")],
        [baojia_btn("取消", "baojia_entry_cancel")],
    ])


def baojia_keyboard_preset(baojia_presets, baojia_prefix):
    """预设选项键盘 + 手动输入。"""
    baojia_rows = []
    for baojia_index in range(0, len(baojia_presets), 2):
        baojia_row = [
            baojia_btn(baojia_value, f"{baojia_prefix}{baojia_value}")
            for baojia_value in baojia_presets[baojia_index:baojia_index + 2]
        ]
        baojia_rows.append(baojia_row)
    baojia_rows.append([baojia_btn("手动输入", f"{baojia_prefix}__manual__")])
    baojia_rows.append([baojia_btn("取消", "baojia_entry_cancel")])
    return InlineKeyboardMarkup(baojia_rows)


def baojia_keyboard_entry_confirm():
    """录入确认。"""
    return InlineKeyboardMarkup([
        [baojia_btn("确认保存", "baojia_entry_save"),
         baojia_btn("取消", "baojia_entry_cancel")],
    ])


def baojia_keyboard_entry_conflict():
    """归属冲突确认。"""
    return InlineKeyboardMarkup([
        [baojia_btn("覆盖更新", "baojia_entry_overwrite"),
         baojia_btn("取消", "baojia_entry_cancel")],
    ])


# ==================== 群内报价展示 ====================

def baojia_keyboard_summary(baojia_country, baojia_indices):
    """折叠摘要的键盘：每个料性一个展开/收起按钮。
    baojia_indices: [(type, material), ...] 顺序与展示一致。
    """
    baojia_rows = []
    for baojia_idx, (_, baojia_material) in enumerate(baojia_indices):
        baojia_rows.append([
            baojia_btn(
                f"展开 {baojia_material}",
                f"baojia_gq_exp_{baojia_idx}",
            )
        ])
    return InlineKeyboardMarkup(baojia_rows)


def baojia_keyboard_expanded(baojia_country, baojia_idx, baojia_material):
    """展开状态下的收起按钮（单条）。"""
    return InlineKeyboardMarkup([
        [baojia_btn(f"收起 {baojia_material}", f"baojia_gq_col_{baojia_idx}")],
    ])


# ==================== 群 ID 查询 ====================

def baojia_keyboard_group_info(baojia_group_id):
    """群查询结果操作。"""
    return InlineKeyboardMarkup([
        [baojia_btn("查看该群更新历史", f"baojia_grp_hist_{baojia_group_id}")],
        [baojia_btn("删除该群报价", f"baojia_grp_del_{baojia_group_id}")],
        [baojia_btn("返回主菜单", "baojia_menu_home")],
    ])


# ==================== 操作员管理 ====================

def baojia_keyboard_admin_menu():
    """操作员管理菜单。"""
    return InlineKeyboardMarkup([
        [baojia_btn("添加操作员", "baojia_admin_emp_add")],
        [baojia_btn("操作员列表", "baojia_admin_emp_list")],
        [baojia_btn("返回主菜单", "baojia_menu_home")],
    ])


def baojia_keyboard_emp_list(baojia_users):
    """操作员列表。"""
    baojia_rows = []
    for baojia_user in baojia_users:
        baojia_status = "" if baojia_user["baojia_is_active"] == 1 else "（已禁用）"
        baojia_rows.append([
            baojia_btn(
                f"{baojia_user['baojia_full_name']} {baojia_status}",
                f"baojia_admin_emp_view_{baojia_user['baojia_user_id']}",
            )
        ])
    baojia_rows.append([baojia_btn("返回操作员管理", "baojia_menu_admin")])
    return InlineKeyboardMarkup(baojia_rows)


def baojia_keyboard_emp_actions(baojia_user_id, baojia_is_active):
    """操作员详情操作。"""
    baojia_rows = []
    if baojia_is_active:
        baojia_rows.append([baojia_btn("禁用该操作员", f"baojia_admin_emp_active_{baojia_user_id}_0")])
    else:
        baojia_rows.append([baojia_btn("启用该操作员", f"baojia_admin_emp_active_{baojia_user_id}_1")])
    baojia_rows.append([baojia_btn("删除该操作员", f"baojia_admin_emp_del_{baojia_user_id}")])
    baojia_rows.append([baojia_btn("返回操作员列表", "baojia_admin_emp_list")])
    return InlineKeyboardMarkup(baojia_rows)


def baojia_keyboard_emp_del_confirm(baojia_user_id):
    """删除操作员二次确认。"""
    return InlineKeyboardMarkup([
        [baojia_btn("确认删除", f"baojia_admin_emp_delok_{baojia_user_id}"),
         baojia_btn("取消", f"baojia_admin_emp_view_{baojia_user_id}")],
    ])


# ==================== 报价删除 ====================

def baojia_keyboard_del_cancel():
    """删除流程中的取消按钮。"""
    return InlineKeyboardMarkup([[baojia_btn("取消", "baojia_del_cancel")]])


def baojia_keyboard_del_mode():
    """删除方式选择。"""
    return InlineKeyboardMarkup([
        [baojia_btn("按国家查找", "baojia_del_mode_country")],
        [baojia_btn("按群组查找", "baojia_del_mode_group")],
        [baojia_btn("取消", "baojia_del_cancel")],
    ])


def baojia_keyboard_del_countries(baojia_countries):
    """国家选择键盘（两列），回调携带列表下标。"""
    baojia_rows = []
    baojia_base = 0
    for baojia_i in range(0, len(baojia_countries), 2):
        baojia_chunk = baojia_countries[baojia_i:baojia_i + 2]
        baojia_rows.append([
            baojia_btn(baojia_c, f"baojia_del_c_{baojia_base + baojia_j}")
            for baojia_j, baojia_c in enumerate(baojia_chunk)
        ])
        baojia_base += len(baojia_chunk)
    baojia_rows.append([baojia_btn("取消", "baojia_del_cancel")])
    return InlineKeyboardMarkup(baojia_rows)


def baojia_quote_button_label(baojia_row, baojia_show_country=False, baojia_show_parent=False):
    """删除列表中的报价按钮文案（按钮文字为纯文本，不做 HTML 转义）。

    baojia_show_country：追加国家（按群组查找时用，方便区分国家）；
    baojia_show_parent：追加所属公群（按国家查找时用，方便区分公群）。
    """
    baojia_label = (
        f"{baojia_config.BAOJIA_TYPE_LABELS[baojia_row['baojia_type']]}"
        f"｜{baojia_row['baojia_material']}"
        f"｜{baojia_row['baojia_account_type']}"
        f"｜{baojia_row['baojia_settle_method']}"
        f"｜{baojia_utils.baojia_fmt_plain(baojia_row['baojia_fee_rate'])}%"
        f"｜汇率{baojia_utils.baojia_fmt_plain(baojia_row['baojia_rate'])}"
    )
    if baojia_show_country:
        baojia_label += f"｜国家：{baojia_row['baojia_country']}"
    if baojia_show_parent:
        baojia_label += f"｜公群：{baojia_row.get('baojia_parent_group') or '无'}"
    return baojia_label


def baojia_keyboard_del_quotes(baojia_rows, baojia_show_country=False, baojia_show_parent=False):
    """报价选择键盘，每条报价一个按钮，回调携带报价 ID。"""
    baojia_kb = []
    for baojia_row in baojia_rows:
        baojia_kb.append([
            baojia_btn(
                baojia_quote_button_label(baojia_row, baojia_show_country, baojia_show_parent),
                f"baojia_del_q_{baojia_row['baojia_quote_id']}",
            )
        ])
    baojia_kb.append([baojia_btn("取消", "baojia_del_cancel")])
    return InlineKeyboardMarkup(baojia_kb)


def baojia_keyboard_del_confirm(baojia_quote_id):
    """报价删除二次确认。"""
    return InlineKeyboardMarkup([
        [baojia_btn("确认删除", f"baojia_del_ok_{baojia_quote_id}"),
         baojia_btn("返回列表", "baojia_del_back")],
        [baojia_btn("取消", "baojia_del_cancel")],
    ])
