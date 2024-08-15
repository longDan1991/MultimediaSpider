# -*- coding: utf-8 -*-
import asyncio
import os
from typing import Dict, List, Optional

import pandas as pd

import config
import constant
from constant import EXCEL_ACCOUNT_SAVE, MYSQL_ACCOUNT_SAVE
from pkg.account_pool.field import (AccountInfoModel, AccountStatusEnum,
                                    AccountWithIpModel)
from pkg.proxy import IpInfoModel
from pkg.proxy.proxy_ip_pool import ProxyIpPool
from pkg.tools import utils
from repo.accounts_cookies import cookies_manage_sql


class AccountPoolManager:
    def __init__(self, platform_name: str, account_save_type: str):
        """
        account pool manager class constructor
        Args:
            platform_name:
            account_save_type:
        """
        self._platform_name = platform_name
        self._account_save_type = account_save_type
        self._account_list: List[AccountInfoModel] = []

    async def async_initialize(self):
        """
        async init
        Returns:

        """
        if self._account_save_type == EXCEL_ACCOUNT_SAVE:
            self.load_accounts_from_xlsx()
        elif self._account_save_type == MYSQL_ACCOUNT_SAVE:
            await self.load_accounts_from_mysql()

    def load_accounts_from_xlsx(self):
        """
        load account from xlsx
        Returns:

        """
        utils.logger.info(
            f"[AccountPoolManager.load_accounts_from_xlsx] load account from {self._platform_name} accounts_cookies.xlsx")
        account_cookies_file_name = "../../config/accounts_cookies.xlsx"
        account_cookies_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), account_cookies_file_name)
        df = pd.read_excel(account_cookies_file_path, sheet_name=self._platform_name, engine='openpyxl')
        account_id = 1
        for _, row in df.iterrows():
            account = AccountInfoModel(
                id=row.get("id", account_id),
                account_name=row.get("account_name", ""),
                cookies=row.get("cookies", ""),
                status=AccountStatusEnum.NORMAL.value,
                platform_name=self._platform_name
            )
            self.add_account(account)
            account_id += 1
            utils.logger.info(f"[AccountPoolManager.load_accounts_from_xlsx] load account {account}")
        utils.logger.info(f"[AccountPoolManager.load_accounts_from_xlsx] all account load success")

    async def load_accounts_from_mysql(self):
        """
        load account from mysql
        Returns:

        """
        account_list: List[Dict] = await cookies_manage_sql.query_platform_accounts_cookies(self._platform_name)
        for account_item in account_list:
            account = AccountInfoModel(
                id=account_item.get("id"),
                account_name=account_item.get("account_name"),
                cookies=account_item.get("cookies"),
                status=account_item.get("status"),
                platform_name=account_item.get("platform_name")
            )
            self.add_account(account)
            utils.logger.info(f"[AccountPoolManager.load_accounts_from_mysql] load account {account}")
        utils.logger.info(f"[AccountPoolManager.load_accounts_from_mysql] all account load success")

    def get_active_account(self) -> AccountInfoModel:
        """
        get active account
        Returns:
            AccountInfoModel: account info model
        """
        while len(self._account_list) > 0:
            account = self._account_list.pop(0)
            if account.status.value == AccountStatusEnum.NORMAL.value:
                utils.logger.info(f"[AccountPoolManager.get_active_account] get active account {account}")
                return account

        raise Exception("[AccountPoolManager.get_active_account] no active account available")

    def add_account(self, account: AccountInfoModel):
        """
        add account
        Args:
            account: account info model
        """
        self._account_list.append(account)

    def update_account_status(self, account: AccountInfoModel, status: AccountStatusEnum):
        """
        update account status
        Args:
            account: account info model
            status: account status enum
        """
        for account_item in self._account_list:
            if account_item.id == account.id:
                account_item.status = status
                account_item.invalid_timestamp = utils.get_current_timestamp()
                # todo update account status in mysql
                return


class AccountWithIpPoolManager(AccountPoolManager):
    def __init__(self, platform_name: str, account_save_type: str,
                 proxy_ip_pool: Optional[ProxyIpPool] = None):
        """
        account with ip pool manager class constructor
        if proxy_ip_pool is None, then the account pool manager will not use proxy ip
        It will only use account pool
        Args:
            platform_name: platform name, defined in constant/base_constant.py
            account_save_type: account save type, defined in constant/base_constant.py
            proxy_ip_pool: proxy ip pool, defined in proxy/proxy_ip_pool.py
        """
        super().__init__(platform_name, account_save_type)
        self.proxy_ip_pool = proxy_ip_pool

    async def async_initialize(self):
        """
        async init
        Returns:

        """
        await super().async_initialize()

    async def get_account_with_ip_info(self) -> AccountWithIpModel:
        """
        get account with ip, if proxy_ip_pool is None, then return account only
        Returns:

        """
        ip_info: Optional[IpInfoModel] = None
        account: AccountInfoModel = self.get_active_account()
        if self.proxy_ip_pool:
            ip_info = await self.proxy_ip_pool.get_proxy()
            utils.logger.info(
                f"[AccountWithIpPoolManager.get_account_with_ip] enable proxy ip pool, get proxy ip: {ip_info}")
        return AccountWithIpModel(account=account, ip_info=ip_info)

    async def mark_account_invalid(self, account: AccountInfoModel):
        """
        mark account invalid
        Args:
            account:

        Returns:

        """
        self.update_account_status(account, AccountStatusEnum.INVALID)

    async def mark_ip_invalid(self, ip_info: Optional[IpInfoModel]):
        """
        mark ip invalid
        Args:
            ip_info:

        Returns:

        """
        if not ip_info:
            return
        await self.proxy_ip_pool.mark_ip_invalid(ip_info)


async def test_get_account_with_ip():
    import db
    await db.init_db()
    account_pool_manager = AccountWithIpPoolManager(constant.XHS_PLATFORM_NAME,
                                                    account_save_type=config.ACCOUNT_POOL_SAVE_TYPE)
    await account_pool_manager.async_initialize()
    account_with_ip = await account_pool_manager.get_account_with_ip_info()
    print(account_with_ip)
    return account_with_ip


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(test_get_account_with_ip())