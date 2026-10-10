"""baojia 报价机器人 - 文案与排版模块

所有面向用户的中文文本与消息排版集中在此，按钮文案均为纯文字（无 emoji）。
"""

import baojia_config
import baojia_utils

BAOJIA_TEXT_WELCOME = (
    "欢迎使用 baojia 报价机器人。\n"
    "私聊我可录入/更新报价；在内部群内发送国家名称即可查询该国最新报价。"
)

BAOJIA_TEXT_DENIED = (
    "抱歉，你暂时没有使用权限。\n"
    "你的 Telegram ID 是：{baojia_user_id}\n"
    "请把该 ID 发给管理员，由管理员在「操作员管理」中添加。"
)

BAOJIA_TEXT_NEED_ADMIN = "该操作仅管理员可执行。"

BAOJIA_TEXT_CANCELLED = "已取消当前操作。"

BAOJIA_TEXT_INPUT_INVALID = "输入格式不正确，请重新输入。"


def baojia_text_main_menu(baojia_admin_flag):
    """主菜单文案。"""
    baojia_lines = [
        BAOJIA_TEXT_WELCOME,
        "",
        "当前身份：" + ("管理员" if baojia_admin_flag else "操作员"),
        "",
        "功能说明：",
        "1. 录入报价：私聊逐步录入，同维度重复录入即更新",
        "2. 群组查询：直接发送群组 ID，查看群链接、业务员与该群全部报价",
        "3. 群内查价：在内部群直接发送国家名称",
        "4. 删除报价：按国家或群组找到报价后删除（记入历史）",
    ]
    return "\n".join(baojia_lines)


# ==================== 录入相关 ====================

def baojia_text_entry_confirm(baojia_draft):
    """录入确认页。"""
    baojia_type_label = baojia_config.BAOJIA_TYPE_LABELS[baojia_draft["baojia_type"]]
    baojia_lines = [
        "请确认录入信息：",
        "————————————",
        f"类型：{baojia_utils.baojia_esc(baojia_type_label)}",
        f"国家：{baojia_utils.baojia_esc(baojia_draft['baojia_country'])}"
        f" | 料性：{baojia_utils.baojia_esc(baojia_draft['baojia_material'])}",
        f"账户类别：{baojia_utils.baojia_esc(baojia_draft['baojia_account_type'])}"
        f" | 结算方式：{baojia_utils.baojia_esc(baojia_draft['baojia_settle_method'])}",
        f"手续费：{baojia_utils.baojia_fmt_plain(baojia_draft['baojia_fee_rate'])}%"
        f" | 汇率：{baojia_utils.baojia_fmt_plain(baojia_draft['baojia_rate'])}",
    ]
    if baojia_draft["baojia_type"] == baojia_config.BAOJIA_TYPE_PAY:
        baojia_lines.append(
            f"单笔费用：{baojia_utils.baojia_fmt_plain(baojia_draft.get('baojia_single_fee', 0))}"
        )
    baojia_lines.extend([
        f"群名：{baojia_utils.baojia_esc(baojia_draft['baojia_group_name'])}",
        f"群组ID：{baojia_draft['baojia_group_id']}",
        f"所属公群：{baojia_utils.baojia_esc(baojia_draft.get('baojia_parent_group', ''))}",
        f"业务员：{baojia_utils.baojia_esc(baojia_draft['baojia_sales'])}",
        f"备注：{baojia_utils.baojia_esc(baojia_draft.get('baojia_remark', '')) or '无'}",
        "————————————",
    ])
    return "\n".join(baojia_lines)


def baojia_text_entry_conflict(baojia_existing):
    """归属冲突提示。"""
    return (
        "提示：该群组【"
        f"{baojia_utils.baojia_esc(baojia_existing['baojia_country'])}-"
        f"{baojia_utils.baojia_esc(baojia_existing['baojia_material'])}-"
        f"{baojia_utils.baojia_esc(baojia_existing['baojia_account_type'])}-"
        f"{baojia_utils.baojia_esc(baojia_existing['baojia_settle_method'])}-"
        f"{baojia_utils.baojia_esc(baojia_config.BAOJIA_TYPE_LABELS[baojia_existing['baojia_type']])}】已有报价\n"
        f"归属业务员：{baojia_utils.baojia_esc(baojia_existing['baojia_sales'])}"
        f"（更新于 {baojia_utils.baojia_display_time(baojia_existing['baojia_updated_at'])}）\n"
        "如价格有变动，请直接覆盖更新为最新报价。"
    )


def baojia_text_entry_saved(baojia_draft, baojia_action):
    """保存成功回执。"""
    baojia_word = "报价已更新（覆盖旧报价，旧值已存入历史）。" if baojia_action == "update" else "报价录入成功。"
    baojia_type_label = baojia_config.BAOJIA_TYPE_LABELS[baojia_draft["baojia_type"]]
    baojia_link = baojia_utils.baojia_group_link(baojia_draft["baojia_group_id"])
    baojia_group_name = baojia_utils.baojia_esc(baojia_draft["baojia_group_name"])
    baojia_lines = [
        f"{baojia_word}\n\n"
        f"{baojia_utils.baojia_esc(baojia_draft['baojia_country'])}"
        f" | {baojia_utils.baojia_esc(baojia_type_label)}"
        f" | {baojia_utils.baojia_esc(baojia_draft['baojia_material'])}\n"
        f"手续费 {baojia_utils.baojia_fmt_plain(baojia_draft['baojia_fee_rate'])}%"
        f" | 汇率 {baojia_utils.baojia_fmt_plain(baojia_draft['baojia_rate'])}\n"
        f'群：<a href="{baojia_link}">{baojia_group_name}</a>\n'
        f"所属公群：{baojia_utils.baojia_esc(baojia_draft.get('baojia_parent_group', ''))}\n"
        f"业务员：{baojia_utils.baojia_esc(baojia_draft['baojia_sales'])}\n"
    ]
    baojia_remark = baojia_draft.get("baojia_remark", "")
    if baojia_remark:
        baojia_lines.append(f"备注：{baojia_utils.baojia_esc(baojia_remark)}\n")
    baojia_lines.append(f"时间：{baojia_utils.baojia_display_time(baojia_utils.baojia_now())}")
    return "".join(baojia_lines)


# ==================== 群内查询展示 ====================

def baojia_quote_line(baojia_row, baojia_rank=None):
    """单条报价展示（HTML），格式：
    第N名
    手续费xx%｜汇率xxxx
    公户　　｜拖算
    群组：群名（超链接，点击在 Telegram 内跳转）
    业务员：@xxxxx ｜ 更新：xxxx-xx-xx xx:xx
    """
    baojia_lines = []
    if baojia_rank is not None:
        baojia_lines.append(f"第{baojia_rank}名")
    baojia_lines.append(
        f"手续费{baojia_utils.baojia_fmt_plain(baojia_row['baojia_fee_rate'])}%"
        f"｜汇率{baojia_utils.baojia_fmt_plain(baojia_row['baojia_rate'])}"
    )
    if not baojia_row["baojia_type"] == baojia_config.BAOJIA_TYPE_COLLECT:
        baojia_lines.append(
            f"单笔费用{baojia_utils.baojia_fmt_plain(baojia_row.get('baojia_single_fee', 0))}"
        )
    baojia_account = baojia_utils.baojia_esc(baojia_row["baojia_account_type"])
    baojia_settle = baojia_utils.baojia_esc(baojia_row["baojia_settle_method"])
    # 对齐：账户类别占 4 个中文字符宽度
    baojia_pad = "\u3000" * max(0, 4 - len(baojia_row["baojia_account_type"]))
    baojia_lines.append(f"{baojia_account}{baojia_pad}｜{baojia_settle}")
    baojia_link = baojia_utils.baojia_group_link(baojia_row["baojia_group_id"])
    baojia_group_name = baojia_utils.baojia_esc(baojia_row["baojia_group_name"])
    baojia_lines.append(f'群组：<a href="{baojia_link}">{baojia_group_name}</a>')
    baojia_parent = baojia_utils.baojia_esc(baojia_row.get("baojia_parent_group", ""))
    baojia_lines.append(f"所属公群：{baojia_parent or '无'}")
    baojia_lines.append(
        f"业务员：{baojia_utils.baojia_esc(baojia_row['baojia_sales'])}"
        f" ｜ 更新：{baojia_utils.baojia_display_time(baojia_row['baojia_updated_at'])}"
    )
    baojia_remark = baojia_row.get("baojia_remark", "")
    if baojia_remark:
        baojia_lines.append(f"备注：{baojia_utils.baojia_esc(baojia_remark)}")
    return "\n".join(baojia_lines)


def baojia_group_rows(baojia_rows):
    """把报价行整理为有序结构：
    [(类型, [(料性, 排序后的行列表), ...]), ...]，代收在前、代付在后；
    料性组按组内最优值排序，组内按优劣排序。
    """
    baojia_result = []
    for baojia_type in (baojia_config.BAOJIA_TYPE_COLLECT, baojia_config.BAOJIA_TYPE_PAY):
        baojia_typed = [baojia_row for baojia_row in baojia_rows if baojia_row["baojia_type"] == baojia_type]
        if not baojia_typed:
            continue
        baojia_materials = {}
        for baojia_row in baojia_typed:
            baojia_materials.setdefault(baojia_row["baojia_material"], []).append(baojia_row)
        baojia_groups = []
        for baojia_material, baojia_group_rows_list in baojia_materials.items():
            baojia_sorted = sorted(
                baojia_group_rows_list,
                key=baojia_utils.baojia_quote_usdt,
                reverse=(baojia_type == baojia_config.BAOJIA_TYPE_COLLECT),
            )
            baojia_groups.append((baojia_material, baojia_sorted))
        baojia_groups.sort(
            key=lambda baojia_item: baojia_utils.baojia_quote_usdt(baojia_item[1][0]),
            reverse=(baojia_type == baojia_config.BAOJIA_TYPE_COLLECT),
        )
        baojia_result.append((baojia_type, baojia_groups))
    return baojia_result


def baojia_material_block(baojia_material, baojia_sorted, baojia_expanded, baojia_idx):
    """渲染单个料性区块，整体用 Telegram 原生引用（blockquote）包裹。

    未展开：只显示第 1 名；已展开：显示全部排名。
    """
    baojia_is_expanded = baojia_idx in baojia_expanded
    baojia_count = len(baojia_sorted)
    if baojia_is_expanded:
        baojia_title = f"▎{baojia_utils.baojia_esc(baojia_material)}（{baojia_count} 条）"
        baojia_body_parts = [
            baojia_quote_line(baojia_row, baojia_rank=baojia_rank)
            for baojia_rank, baojia_row in enumerate(baojia_sorted, start=1)
        ]
    else:
        baojia_title = f"▎{baojia_utils.baojia_esc(baojia_material)}（共 {baojia_count} 条）"
        baojia_body_parts = [baojia_quote_line(baojia_sorted[0], baojia_rank=1)]
    baojia_block = baojia_title + "\n" + "\n\n".join(baojia_body_parts)
    return f"<blockquote>{baojia_block}</blockquote>"


def baojia_text_summary(baojia_country, baojia_rows, baojia_expanded=None):
    """群内折叠摘要：每个（类型×料性）默认只显示第一名，
    展开的料性显示全部排名。料性用 Telegram 原生引用（blockquote）标记。
    baojia_expanded 为已展开料性的索引集合（与按钮回调的索引一致）。
    """
    if baojia_expanded is None:
        baojia_expanded = set()
    baojia_latest = max(baojia_row["baojia_updated_at"] for baojia_row in baojia_rows)
    baojia_lines = [
        f"【{baojia_utils.baojia_esc(baojia_country)} 最新报价】共 {len(baojia_rows)} 条"
        f" | 更新至 {baojia_utils.baojia_display_time(baojia_latest)}",
        "",
    ]
    baojia_idx = 0
    for baojia_type, baojia_groups in baojia_group_rows(baojia_rows):
        baojia_type_label = baojia_config.BAOJIA_TYPE_LABELS[baojia_type]
        baojia_lines.append(f"—— {baojia_utils.baojia_esc(baojia_type_label)} ——")
        baojia_lines.append("")
        for baojia_material, baojia_sorted in baojia_groups:
            baojia_lines.append(
                baojia_material_block(
                    baojia_material, baojia_sorted, baojia_expanded, baojia_idx
                )
            )
            baojia_lines.append("")
            baojia_idx += 1
    return "\n".join(baojia_lines).strip()


def baojia_material_indices(baojia_rows):
    """返回料性列表，供键盘索引使用。"""
    baojia_groups = baojia_group_rows(baojia_rows)
    baojia_list = []
    for baojia_type, baojia_groups_list in baojia_groups:
        for baojia_material, _ in baojia_groups_list:
            baojia_list.append((baojia_type, baojia_material))
    return baojia_list


# ==================== 群组查询（私聊） ====================

def baojia_country_groups(baojia_rows):
    """把报价行按国家分组，返回 [(国家, 该国的类型/料性有序结构), ...]。

    国家按其组内最新更新时间倒序排列（最近有变动的国家排前面）；
    国家内部复用 baojia_group_rows 的排序（代收在前、料性按优劣）。
    """
    baojia_by_country = {}
    for baojia_row in baojia_rows:
        baojia_by_country.setdefault(baojia_row["baojia_country"], []).append(baojia_row)
    baojia_result = []
    for baojia_country, baojia_country_rows in baojia_by_country.items():
        baojia_result.append((baojia_country, baojia_group_rows(baojia_country_rows)))
    baojia_result.sort(
        key=lambda baojia_item: max(
            baojia_row["baojia_updated_at"]
            for _, baojia_groups in baojia_item[1]
            for _, baojia_sorted in baojia_groups
            for baojia_row in baojia_sorted
        ),
        reverse=True,
    )
    return baojia_result


def baojia_text_group_info(baojia_group_id, baojia_rows):
    """群 ID 查询结果：按国家分类展示该群在各国家的全部报价。"""
    baojia_group_name = baojia_utils.baojia_esc(baojia_rows[0]["baojia_group_name"])
    baojia_link = baojia_utils.baojia_group_link(baojia_group_id)
    baojia_sales_list = sorted({baojia_row["baojia_sales"] for baojia_row in baojia_rows if baojia_row["baojia_sales"]})
    baojia_sales_text = "、".join(baojia_utils.baojia_esc(baojia_s) for baojia_s in baojia_sales_list) if baojia_sales_list else "未填写"
    # 所属公群：汇总该群全部报价中出现过的非空公群名称
    baojia_parent_list = sorted({
        baojia_row["baojia_parent_group"]
        for baojia_row in baojia_rows
        if baojia_row.get("baojia_parent_group")
    })
    baojia_parent_text = "、".join(baojia_utils.baojia_esc(baojia_p) for baojia_p in baojia_parent_list) if baojia_parent_list else "无"
    baojia_country_data = baojia_country_groups(baojia_rows)
    baojia_lines = [
        "【群组查询】",
        f"群名：{baojia_group_name}",
        f'链接：<a href="{baojia_link}">点击跳转群组</a>',
        f"所属公群：{baojia_parent_text}",
        f"所属业务员：{baojia_sales_text}",
        "",
        f"该群全部报价（{len(baojia_rows)} 条），覆盖 {len(baojia_country_data)} 个国家：",
        "",
    ]
    for baojia_country, baojia_type_groups in baojia_country_data:
        baojia_country_count = sum(
            len(baojia_sorted)
            for _, baojia_groups in baojia_type_groups
            for _, baojia_sorted in baojia_groups
        )
        baojia_lines.append(f"—— 国家：{baojia_utils.baojia_esc(baojia_country)}（{baojia_country_count} 条）——")
        baojia_idx = 0
        for baojia_type, baojia_groups in baojia_type_groups:
            baojia_type_label = baojia_config.BAOJIA_TYPE_LABELS[baojia_type]
            baojia_lines.append(f"—— {baojia_utils.baojia_esc(baojia_type_label)} ——")
            for baojia_material, baojia_sorted in baojia_groups:
                # 群详情中所有料性默认全部展开
                baojia_lines.append(
                    baojia_material_block(
                        baojia_material, baojia_sorted, {baojia_idx}, baojia_idx
                    )
                )
                baojia_lines.append("")
                baojia_idx += 1
    return "\n".join(baojia_lines).strip()


def baojia_text_group_history(baojia_group_name, baojia_rows):
    """群组更新历史。"""
    baojia_action_labels = {"create": "新建", "update": "更新", "delete": "删除"}
    baojia_lines = [f"【群组更新历史】{baojia_utils.baojia_esc(baojia_group_name)}", ""]
    for baojia_row in baojia_rows:
        baojia_action = baojia_action_labels.get(
            baojia_row["baojia_action"], baojia_row["baojia_action"]
        )
        baojia_lines.append(
            f"- {baojia_utils.baojia_display_time(baojia_row['baojia_changed_at'])}"
            f" {baojia_utils.baojia_esc(baojia_row['baojia_sales'])} {baojia_action}："
            f"{baojia_utils.baojia_esc(baojia_row['baojia_country'])}"
            f" {baojia_utils.baojia_esc(baojia_row['baojia_material'])}"
            f" {baojia_utils.baojia_esc(baojia_row['baojia_account_type'])}"
            f" {baojia_utils.baojia_esc(baojia_row['baojia_settle_method'])}"
            f" {baojia_utils.baojia_esc(baojia_config.BAOJIA_TYPE_LABELS[baojia_row['baojia_type']])}"
            f" 手续费{baojia_utils.baojia_fmt_plain(baojia_row['baojia_fee_rate'])}%"
            f" 汇率{baojia_utils.baojia_fmt_plain(baojia_row['baojia_rate'])}"
        )
        if baojia_row.get("baojia_remark"):
            baojia_lines.append(f"  备注：{baojia_utils.baojia_esc(baojia_row['baojia_remark'])}")
    return "\n".join(baojia_lines)


# ==================== 删除相关 ====================

BAOJIA_TEXT_DEL_MENU = (
    "删除报价：请选择查找方式（每次只删除一条报价）。\n"
    "国家/群组仅用于筛选定位，进入列表后点击某条报价单独删除，"
    "删除后立即生效并记入更新历史。"
)

BAOJIA_TEXT_DEL_EXPIRED = "删除会话已过期或数据已变化，请从主菜单重新进入删除报价。"


def baojia_text_del_list(baojia_title, baojia_rows):
    """报价删除列表页头。"""
    return (
        f"{baojia_utils.baojia_esc(baojia_title)}共 {len(baojia_rows)} 条报价，"
        "点击选择要删除的单条（仅删除你点中的这一条）："
    )


def baojia_text_del_confirm(baojia_row):
    """删除确认页，展示报价完整信息。"""
    return (
        "请确认要删除以下报价：\n"
        "————————————\n"
        f"国家：{baojia_utils.baojia_esc(baojia_row['baojia_country'])}\n"
        f"{baojia_quote_line(baojia_row)}\n"
        "————————————\n"
        "删除后立即生效，原报价记入更新历史。"
    )


def baojia_text_del_done(baojia_row):
    """删除成功回执。"""
    baojia_type_label = baojia_config.BAOJIA_TYPE_LABELS[baojia_row["baojia_type"]]
    return (
        "报价已删除。\n\n"
        f"{baojia_utils.baojia_esc(baojia_row['baojia_country'])}"
        f" | {baojia_utils.baojia_esc(baojia_type_label)}"
        f" | {baojia_utils.baojia_esc(baojia_row['baojia_material'])}"
        f" | {baojia_utils.baojia_esc(baojia_row['baojia_account_type'])}"
        f" | {baojia_utils.baojia_esc(baojia_row['baojia_settle_method'])}\n"
        f"群：{baojia_utils.baojia_esc(baojia_row['baojia_group_name'])}\n"
        f"业务员：{baojia_utils.baojia_esc(baojia_row['baojia_sales'])}\n"
        f"时间：{baojia_utils.baojia_display_time(baojia_utils.baojia_now())}"
    )
