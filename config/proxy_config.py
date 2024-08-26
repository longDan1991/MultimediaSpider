# -*- coding: utf-8 -*-
import os

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2 # 一般情况下设置成2个就够了，程序会自动维护IP可用性

# 代理IP提供商名称
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# 快代理配置
KDL_SECERT_ID = os.getenv("KDL_SECERT_ID", "你的快代理secert_id")
KDL_SIGNATURE = os.getenv("KDL_SIGNATURE", "你的快代理签名")
KDL_USER_NAME = os.getenv("KDL_USER_NAME", "你的快代理用户名")
KDL_USER_PWD = os.getenv("KDL_USER_PWD", "你的快代理密码")
