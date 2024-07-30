import json
import time
from typing import Dict, Tuple, Union, Optional

import requests
import urllib3
from aiohttp import TCPConnector, ClientSession, ContentTypeError

from gsuid_core.logger import logger
from gsuid_core.utils.plugins_config.gs_config import core_plugins_config

from .tools import get_ds_token
from .base_request import BaseMysApi

session = requests.session()

ssl_verify = core_plugins_config.get_config('MhySSLVerify').data


class PassMysApi(BaseMysApi):
    async def __make_pass_request(self, method, data):
        logger.info("[upass]发送请求...")
        logger.debug(f"[upass]请求方法：{method}，请求数据：{data}")
        try:
            response = session.post("https://api.anti-captcha.com/" + method, data=json.dumps(data))
            logger.trace(f"[upass]请求返回：{response.text}")
        # 错误返回说明：
        # 255: 遭遇HTTP错误
        # 254: 连接超时
        # 253: 读取超时
        # 252：超出最大重试次数
        # 251：远程主机强制关闭了一个现有的连接
        # 250：等待过程中超时
        except requests.exceptions.HTTPError as err:
            logger.error(
                f"[upass]遭遇HTTP错误，错误标号{err.errno}，错误说明{err.strerror}，请求{err.args}，{err.filename}")
            return 255
        except requests.exceptions.ConnectTimeout:
            logger.error(f"[upass]连接超时")
            return 254
        except urllib3.exceptions.ConnectTimeoutError:
            logger.error(f"[upass]连接超时")
            return 254
        except requests.exceptions.ReadTimeout:
            logger.error(f"[upass]读取超时")
            return 253
        except urllib3.exceptions.MaxRetryError as err:
            logger.error(f"[upass]连接重试错误：{err.reason}")
            return 252
        except requests.exceptions.ConnectionError:
            logger.error(f"[upass]远程主机强制关闭了一个现有的连接")
            return 251
        return response.json()

    async def __create_pass_task(self, post_data):
        new_task = await self.__make_pass_request(method="createTask", data=post_data)
        if isinstance(new_task, int):
            return new_task
        else:
            # 返回说明：
            # 3：任务创建成功，任务ID已经设置，请执行后续操作
            # 2：任务创建失败，错误ID与错误信息已经设置
            # 1：任务创建成功，但是无法解决任务
            if new_task["errorId"] == 0:
                self.task_id = new_task["taskId"]
                logger.trace(f"[upass]返回：任务ID{self.task_id}")
                return 3
            else:
                self.error_code = new_task["errorCode"]
                self.err_string = new_task["errorDescription"]
                logger.error(f"[upass]任务创建失败，错误ID{self.error_code}，错误信息{self.err_string}")
                return 2

    async def __wait_pass_result(self, api_key, timeout=30, current_time=0):
        if current_time >= timeout:
            logger.error(f'[upass]超出指定的最大等待时间{timeout}，任务已设置为过期并放弃等待')
            return 250
        time.sleep(1)
        task_check = await self.__make_pass_request(method="getTaskResult", data={
            "clientKey": api_key,
            "taskId": self.task_id
        })
        if isinstance(task_check, int):
            return task_check
        else:
            if task_check["errorId"] == 0:
                if task_check["status"] == "processing":
                    logger.info(f'[upass]等待任务{self.task_id}处理')
                    return await self.__wait_pass_result(timeout=timeout, current_time=current_time + 1,
                                                         api_key=api_key)
                if task_check["status"] == "ready":
                    logger.info(f'[upass]任务{self.task_id}已完成，返回{task_check}')
                    return task_check
            else:
                self.error_code = task_check["errorCode"]
                self.err_string = task_check["errorDescription"]
                logger.error(f'[upass]API返回了一个错误{self.error_code}：{self.err_string}')
                return 1

    async def __pass_func(self, gt: str, ch: str, api_key: str, website_url: str, geetest_api_domain: str):
        if await self.__create_pass_task({
            "clientKey": api_key,
            "task": {
                "type": "GeeTestTaskProxyless",
                "websiteURL": website_url,
                "gt": gt,
                "challenge": ch,
                "geetestApiServerSubdomain": geetest_api_domain,
                "version": 3,
            },
            "softId": 0
        }) == 3:
            logger.info(f"[upass]创建任务成功，任务ID{self.task_id}")
        else:
            logger.error(f"[upass]创建任务失败，错误信息{self.err_string}")
            return 1
        # checking result
        time.sleep(3)
        task_result = await self.__wait_pass_result(api_key=api_key)
        if isinstance(task_result, int):
            return 1
        else:
            return task_result["solution"]["validate"]

    async def get_pass_api_balance(self, api_key: str):
        balance = await self.__make_pass_request(method="getBalance", data={"clientKey": api_key})
        return balance["balance"]

    async def _pass(
        self, gt: str, ch: str, header: Dict
    ) -> Tuple[Optional[str], Optional[str]]:
        # 警告：使用该服务（例如某RR等）需要注意风险问题
        # 本项目不以任何形式提供相关接口
        # 代码来源：GITHUB项目MIT开源
        _pass_api_key = core_plugins_config.get_config('_pass_API_key').data
        if _pass_api_key:
            validate = await self.__pass_func(gt=gt,
                                              ch=ch,
                                              api_key=_pass_api_key,
                                              geetest_api_domain="api.geevisit.com",
                                              website_url="https://api-takumi.mihoyo.com/event/luna/sign")
            if validate == 1:
                validate = None
        else:
            validate = None
        return validate, ch

    async def _upass(self, header: Dict, is_bbs: bool = False) -> str | tuple[str, str]:
        logger.info('[upass] 进入处理...')
        if is_bbs:
            raw_data = await self.get_bbs_upass_link(header)
        else:
            raw_data = await self.get_upass_link(header)
        if isinstance(raw_data, int):
            return ''
        gt = raw_data['data']['gt']
        ch = raw_data['data']['challenge']

        vl, ch = await self._pass(gt, ch, header)

        if vl:
            await self.get_header_and_vl(header, ch, vl, is_bbs)
            if ch:
                logger.info(f'[upass] 获取ch -> {ch}')
                return vl, ch
            else:
                return '', ch
        else:
            return '', ch

    async def get_upass_link(self, header: Dict) -> Union[int, Dict]:
        header['DS'] = get_ds_token('is_high=false')
        return await self._mys_request(
            url=self.MAPI['VERIFICATION_URL'],
            method='GET',
            header=header,
        )

    async def get_bbs_upass_link(self, header: Dict) -> Union[int, Dict]:
        header['DS'] = get_ds_token('is_high=true')
        return await self._mys_request(
            url=self.MAPI['BBS_VERIFICATION_URL'],
            method='GET',
            header=header,
        )

    async def get_header_and_vl(
        self, header: Dict, ch, vl, is_bbs: bool = False
    ):
        header['DS'] = get_ds_token(
            '',
            {
                'geetest_challenge': ch,
                'geetest_validate': vl,
                'geetest_seccode': f'{vl}|jordan',
            },
        )
        _ = await self._mys_request(
            url=(
                self.MAPI['VERIFY_URL']
                if not is_bbs
                else self.MAPI['BBS_VERIFY_URL']
            ),
            method='POST',
            header=header,
            data={
                'geetest_challenge': ch,
                'geetest_validate': vl,
                'geetest_seccode': f'{vl}|jordan',
            },
        )
