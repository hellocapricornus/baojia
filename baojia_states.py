"""baojia 报价机器人 - 对话状态常量

所有 ConversationHandler 使用的状态全部集中在此，统一 baojia 前缀。
"""

# 报价录入流程 baojia_handler_entry
BAOJIA_STATE_ENTRY_TYPE = 101          # 选择代收/代付
BAOJIA_STATE_ENTRY_COUNTRY = 102       # 输入国家
BAOJIA_STATE_ENTRY_MATERIAL = 103      # 选择料性
BAOJIA_STATE_ENTRY_MATERIAL_INPUT = 104    # 手动输入料性
BAOJIA_STATE_ENTRY_ACCOUNT = 105       # 选择账户类别
BAOJIA_STATE_ENTRY_ACCOUNT_INPUT = 106     # 手动输入账户类别
BAOJIA_STATE_ENTRY_SETTLE = 107        # 选择结算方式
BAOJIA_STATE_ENTRY_SETTLE_INPUT = 108      # 手动输入结算方式
BAOJIA_STATE_ENTRY_FEE = 109           # 输入手续费百分比
BAOJIA_STATE_ENTRY_RATE = 110          # 输入汇率
BAOJIA_STATE_ENTRY_SINGLE_FEE = 111    # 代付单笔费用
BAOJIA_STATE_ENTRY_GROUP_ID = 112      # 输入群组ID
BAOJIA_STATE_ENTRY_GROUP_NAME = 113    # 输入群名称
BAOJIA_STATE_ENTRY_PARENT_GROUP = 117  # 输入所属公群
BAOJIA_STATE_ENTRY_SALES = 114         # 输入业务员
BAOJIA_STATE_ENTRY_CONFIRM = 115       # 确认保存
BAOJIA_STATE_ENTRY_CONFLICT = 116      # 归属冲突确认覆盖

# 操作员管理 baojia_handler_admin
BAOJIA_STATE_ADMIN_EMP_ADD = 401       # 添加操作员（输入 Telegram ID）

# 报价删除 baojia_handler_del
BAOJIA_STATE_DEL_MODE = 201            # 选择删除方式（按国家/按群组）
BAOJIA_STATE_DEL_COUNTRY = 202         # 选择国家
BAOJIA_STATE_DEL_GROUP_ID = 203        # 输入群组 ID
BAOJIA_STATE_DEL_SELECT = 204          # 选择要删除的报价
BAOJIA_STATE_DEL_CONFIRM = 205         # 确认删除
