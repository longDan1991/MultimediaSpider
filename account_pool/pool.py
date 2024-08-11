# -*- coding: utf-8 -*-
import asyncio
import os
from typing import List, Optional

import pandas as pd

import constant
from account_pool.field import (AccountInfoModel, AccountStatusEnum,
                                AccountWithIpModel)
from constant import EXCEL_ACCOUNT_SAVE
from proxy import IpInfoModel
from proxy.proxy_ip_pool import ProxyIpPool
from tools import utils


class AccountPoolManager:
    def __init__(self, platform_name: str, account_save_type: str = EXCEL_ACCOUNT_SAVE):
        """
        account pool manager class constructor
        Args:
            platform_name:
            account_save_type:
        """
        self._platform_name = platform_name
        self._account_save_type = account_save_type
        self._account_list: List[AccountInfoModel] = []
        self.load_accounts_from_xlsx()

    def load_accounts_from_xlsx(self):
        """
        load account from xlsx
        Returns:
            List[AccountInfoModel]: list of account info models
        """
        utils.logger.info(
            f"[AccountPoolManager.load_accounts_from_xlsx] load account from {self._platform_name} accounts_cookies.xlsx")
        account_cookies_file_name = "accounts_cookies.xlsx"
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

        raise Exception("No active account available")

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
                return

    async def async_init(self):
        """
        async init
        Returns:

        """
        raise NotImplementedError

    async def load_accounts_from_mysql(self):
        """
        load account from mysql
        Returns:

        """
        raise NotImplementedError


class AccountWithIpPoolManager(AccountPoolManager):
    def __init__(self, platform_name: str, account_save_type: str = EXCEL_ACCOUNT_SAVE,
                 proxy_ip_pool: ProxyIpPool = None):
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

    def set_proxy_ip_pool(self, proxy_ip_pool: ProxyIpPool):
        """
        set proxy ip pool
        Args:
            proxy_ip_pool:
        """
        self.proxy_ip_pool = proxy_ip_pool

    async def get_account_with_ip(self) -> AccountWithIpModel:
        """
        get account with ip, if proxy_ip_pool is None, then return account only
        Returns:

        """
        account: AccountInfoModel = self.get_active_account()
        ip: Optional[IpInfoModel] = None
        if self.proxy_ip_pool is not None:
            ip = await self.proxy_ip_pool.get_proxy()
            utils.logger.info(
                f"[AccountWithIpPoolManager.get_account_with_ip] enable proxy ip pool, get proxy ip: {ip}")
        return AccountWithIpModel(account=account, ip=ip)

    async def mark_account_invalid(self, account: AccountInfoModel):
        """
        mark account invalid
        Args:
            account:

        Returns:

        """
        self.update_account_status(account, AccountStatusEnum.INVALID)

    async def mark_ip_invalid(self, ip: IpInfoModel):
        """
        mark ip invalid
        Args:
            ip:

        Returns:

        """
        if not ip:
            return
        await self.proxy_ip_pool.mark_ip_invalid(ip)


async def test_get_account_with_ip():
    account_pool_manager = AccountWithIpPoolManager(constant.XHS_PLATFORM_NAME)
    account_with_ip = await account_pool_manager.get_account_with_ip()
    print(account_with_ip)
    return account_with_ip


if __name__ == '__main__':
    asyncio.run(test_get_account_with_ip())
