from typing import Dict, Tuple, Union, Optional

from aiohttp import TCPConnector, ClientSession, ContentTypeError

from gsuid_core.logger import logger
from gsuid_core.utils.plugins_config.gs_config import core_plugins_config

from .tools import get_ds_token
from .base_request import BaseMysApi

ssl_verify = core_plugins_config.get_config('MhySSLVerify').data


class PassMysApi(BaseMysApi):
    async def _pass(
        self, gt: str, ch: str, header: Dict
    ) -> Tuple[Optional[str], Optional[str]]:
        # 警告：使用该服务（例如某RR等）需要注意风险问题
        # 本项目不以任何形式提供相关接口
        # 代码来源：GITHUB项目MIT开源
        _pass_api_secret = core_plugins_config.get_config('_pass_API_secret').data
        if _pass_api_secret:
            import anticaptchaofficial.geetestproxyless as geetest
            solver = geetest.geetestProxyless()
            solver.set_verbose(1)
            solver.set_key(_pass_api_secret)
            solver.set_website_url("https://webstatic.mihoyo.com/bbs/event/signin-ys/index.html")
            solver.set_gt_key(gt)
            solver.set_challenge_key(ch)
            result = solver.solve_and_return_solution()
            if solver.err_string != '':
                raise ConnectionError(f"An error occurred while resolving the captcha: {solver.err_string}")
            validate = result['validate']
        else:
            validate = None

        return validate, ch

    async def _upass(self, header: Dict, is_bbs: bool = False) -> str:
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
                return ch
            else:
                return ''
        else:
            return ''

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
