import asyncio
from typing import Dict, Union

import httpx

from gsuid_core.logger import logger
from gsuid_core.utils.plugins_config.gs_config import core_plugins_config
from .base_request import BaseMysApi
from .tools import get_ds_token



ssl_verify = core_plugins_config.get_config('MhySSLVerify').data


class PassMysApi(BaseMysApi):
    async def __make_pass_request(self, method, data):
        url = "https://api.anti-captcha.com/" + method
        logger.info("[upass]发送请求...")
        logger.debug(f"[upass]请求方法：{method}，请求数据：{data}")
        try:
            client = httpx.AsyncClient()
            response = await client.post(url=url, json=data, timeout=30)
            response.raise_for_status()
            logger.trace(f"[upass]请求返回：{response.text}")
            await client.aclose()
            return response.json()
        except httpx.HTTPStatusError as err:
            logger.error(f"[upass]遭遇HTTP错误，状态码：{str(err.response.status_code)}，错误内容：{str(err.response.text)}")
            return 255
        except httpx.ConnectTimeout as err:
            logger.error(f"[upass]连接超时，错误内容{str(err)}")
            return 254
        except httpx.ReadTimeout as err:
            logger.error(f"[upass]读取超时，错误内容{str(err)}")
            return 253
        except httpx.NetworkError as err:
            logger.error(f"[upass]网络错误：{str(err)}")
            return 251
        except Exception as e:
            logger.error(f"[upass]未知错误：{str(e)}")
            return 250

    async def __create_pass_task(self, post_data):
        new_task = await self.__make_pass_request(method="createTask", data=post_data)
        if isinstance(new_task, int):
            return new_task
        else:
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
        await asyncio.sleep(1)
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
                    return await self.__wait_pass_result(api_key=api_key, timeout=timeout, current_time=current_time + 1)
                if task_check["status"] == "ready":
                    logger.info(f'[upass]任务{self.task_id}已完成，返回{task_check}')
                    return task_check
            else:
                self.error_code = task_check["errorCode"]
                self.err_string = task_check["errorDescription"]
                logger.error(f'[upass]API返回了一个错误{self.error_code}：{self.err_string}')
                return 1

    async def __pass_func(self, gt, ch, api_key, website_url, geetest_api_domain):
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
        await asyncio.sleep(3)
        task_result = await self.__wait_pass_result(api_key=api_key)
        if isinstance(task_result, int):
            return 1
        else:
            return task_result["solution"]["validate"]

    async def get_pass_api_balance(self, api_key):
        balance = await self.__make_pass_request(method="getBalance", data={"clientKey": api_key})
        return balance["balance"]

    async def _pass(self, gt, ch, header):
        _pass_api_key = core_plugins_config.get_config('_pass_API_key').data
        if _pass_api_key:
            validate = await self.__pass_func(gt=gt, ch=ch, api_key=_pass_api_key, geetest_api_domain="api.geevisit.com",
                                              website_url="https://api-takumi.mihoyo.com/event/luna/sign")
            if validate == 1:
                validate = None
                ch = self.err_string
        else:
            validate = None
            ch = self.err_string
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
