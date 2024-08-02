from pathlib import Path
from copy import deepcopy
from typing import Dict, Union, Optional

from PIL import Image, ImageDraw

from gsuid_core.handler import command_start
from gsuid_core.utils.fonts.fonts import core_font
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.plugins_config.gs_config import send_security_config
from gsuid_core.utils.image.image_tools import (
    get_color_bg,
    draw_center_text_by_line,
)

if command_start and command_start[0]:
    _start = command_start[0]
else:
    _start = ''

UID_HINT = f'你还没有绑定过uid哦!\n请使用[{_start}绑定uid123456789]命令绑定!'

MYS_HINT = f'你还没有绑定过mysid哦!\n请使用[{_start}绑定mys123456789]命令绑定!'

CK_HINT = f"""你还没有绑定过Cookie哦!\n发送[{_start}ck帮助]获取帮助!\n发送[{_start}扫码登陆]绑定CK&SK!
警告：使用此机器人是违反《米游社用户协议》的行为，继续绑定即代表您同意承担一切风险，包括但不限于封禁等处罚！"""

_CHAR_HINT = f'请先使用[{_start}强制刷新]命令来缓存数据! \n或者使用[{_start}查询展柜角色]命令查看已缓存角色！'

CHAR_HINT = '你还没有{}的缓存噢！\n' + _CHAR_HINT

VERIFY_HINT = f'''请求校验失败：无效请求！\n请执行[{_start}刷新ck]以刷新ck信息\n如反复出现此提示，请进行[{_start}绑定设备]以解除风险'''

SK_HINT = (
    '你还没有绑定过Stoken或者Stoken已失效~\n'
    f'请加好友私聊Bot\n [{_start}扫码登陆] 或 [{_start}添加]后跟SK格式 以绑定SK'
)

UPDATE_HINT = f'''更新失败!更多错误信息请查看日志...
>> 可以尝试使用
>> [{_start}gs强制更新](危险)
>> [{_start}gs强行强制更新](超级危险)!'''


ERROR_CODE = {
    -51: CK_HINT,
    -100: f'您的cookie已经失效，请刷新CK或重新绑定CK！',
    -503: CK_HINT,
    10001: f'您的cookie已经失效，请刷新CK或重新绑定CK！',
    10101: '请求过于频繁，请等待24小时后重试！',
    10102: '当前查询UID为强隐私UID，查询失败！',
    1034: VERIFY_HINT,
    -10001: '指定的请求非法，请联系管理员...',
    -201: '当前账号状态异常，请联系米游社客服...',
    1008: f'该API需要CK却未提供，请绑定CK...',
    10104: 'CK与用户信息不符，请重新绑定！\n若反复出现此错误，请联系管理员...',
    -999: VERIFY_HINT,
    -501002: f'当前查询UID为强隐私UID, 请绑定CK！',
    10110: '米游社未查询到你的游戏角色, 请先前往米游社进行绑定游戏角色！',
    -199: '指定的活动不存在！',
}

error_dict = deepcopy(ERROR_CODE)
error_dict.update(
    {
        -512009: '[留影叙佳期]内容已被获取！',
        -501101: '游戏内冒险等阶未达到10级，不满足活动最低要求！',
        400: '[MINIGG]找不到此内容！',
        -400: '匹配项过多，请限制查询范围！',
        125: '充值方式暂不可用！',
        126: '充值方式错误！',
    }
)

TEXT_PATH = Path(__file__).parent / 'image' / 'texture2d'
is_pic_error = send_security_config.get_config('ChangeErrorToPic').data


def get_error(
    retcode: Union[int, str], message: Union[str, Dict, None] = None
) -> str:
    if isinstance(message, str):
        _msg = message
    elif isinstance(message, Dict):
        if 'message' in message:
            _msg = message['message']
        elif 'msg' in message:
            _msg = message['msg']
        else:
            _msg = '无可用信息。'
    else:
        _msg = '无可用信息。'
    return error_dict.get(
        int(retcode), f'未知错误，错误码为{retcode}：{_msg}'
    )


def get_error_type(retcode: Union[int, str]) -> str:
    retcode = int(retcode)
    if retcode in [-51, 10104]:
        return '绑定信息错误'
    elif retcode in [-400, 400]:
        return 'MGGApi错误'
    else:
        return 'Api错误'


async def get_error_img(
    retcode: Union[int, str],
    force_image: bool = False,
    message: Union[str, Dict, None] = None,
) -> Union[bytes, str]:
    error_message = get_error(retcode, message)
    if is_pic_error or force_image:
        error_type = get_error_type(retcode)
        return await draw_error_img(retcode, error_message, error_type)
    else:
        return error_message


async def draw_error_img(
    retcode: Union[int, str] = 51233,
    error_message: Optional[str] = None,
    error_type: Optional[str] = None,
) -> bytes:
    if error_type is None:
        error_type = 'API报错'
    if error_message is None:
        error_message = '未知错误, 请检查日志...'

    error_img = Image.open(TEXT_PATH / 'error_img.png')
    img = await get_color_bg(
        *error_img.size, is_full=True, color=(228, 222, 210)
    )
    img.paste(error_img, (0, 0), error_img)
    img_draw = ImageDraw.Draw(img)
    img_draw.text((350, 646), error_type, 'white', core_font(26), 'mm')
    img_draw.text(
        (350, 695), f'错误码 {retcode}', 'white', core_font(36), 'mm'
    )
    draw_center_text_by_line(
        img_draw, (350, 750), error_message, core_font(30), 'black', 440
    )
    return await convert_img(img)
