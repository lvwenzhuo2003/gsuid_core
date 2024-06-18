from typing import Dict, Union, Optional, Literal

from gsuid_core.logger import logger
from gsuid_core.utils.plugins_config.gs_config import core_plugins_config
from . import resolve_captcha
from .base_request import BaseMysApi
from .tools import get_ds_token

ssl_verify = core_plugins_config.get_config('MhySSLVerify').data


def pass_func(gt: str, ch: str, api_secret: str):
    import anticaptchaofficial.geetestproxyless as geetest
    solver = geetest.geetestProxyless()
    solver.set_verbose(1)
    solver.set_key(api_secret)
    solver.set_website_url("https://webstatic.mihoyo.com/bbs/event/signin-ys/index.html")
    solver.set_gt_key(gt)
    solver.set_challenge_key(ch)
    result = solver.solve_and_return_solution()
    if solver.err_string != '':
        raise ConnectionError(f"An error occurred while resolving the captcha: {solver.err_string}")
    return result


class PassMysApi(BaseMysApi):
    async def get_user_device_id(self, uid: str) -> Optional[str]:
        return None

    async def get_user_fp(self, uid: str) -> Optional[str]:
        return None

    async def get_stoken(self, uid: str) -> Optional[str]:
        return None

    async def get_ck(self, uid: str, mode: Literal['OWNER', 'RANDOM'] = 'RANDOM') -> Optional[str]:
        return None

    async def _pass(self, gt: str, ch: str, header: Dict) -> Dict:
        _pass_api_secret = core_plugins_config.get_config('_pass_API_secret').data
        if _pass_api_secret:
            return await resolve_captcha.solve_captcha(gt, ch, _pass_api_secret, "https://webstatic.mihoyo.com/bbs/event/signin-ys/index.html")


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

        result = await self._pass(gt, ch, header)
        vl = result['solution']['validate']
        ch = result['solution']['challenge']

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
