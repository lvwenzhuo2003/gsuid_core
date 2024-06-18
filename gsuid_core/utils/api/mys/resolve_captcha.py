import json
import time
import requests
import urllib3.exceptions

from gsuid_core.logger import logger

_session = requests.Session()
_session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})


async def __make_request(method: str, data: str):
    logger.info(f'[upass]正在使用以下数据执行验证码绕过任务：请求方法{method}，请求数据{data}')

    try:
        response = _session.post("https://api.anti-captcha.com/" + method, data=data)
    except requests.exceptions.HTTPError as err:
        logger.error(f'[upass]验证码绕过任务创建失败，HTTPError: {err.strerror}')
        for err_arg in err.args:
            if "Network is unreachable" in str(err_arg):
                logger.error('[upass]网络不可达')
            if "Connection refused" in str(err_arg):
                logger.error('[upass]连接被拒绝')
        return 255
    except requests.exceptions.ConnectTimeout:
        logger.error('[upass]验证码绕过任务创建失败，连接超时')
        return 254
    except urllib3.exceptions.ConnectTimeoutError:
        logger.error('[upass]验证码绕过任务创建失败，连接超时')
        return 254
    except requests.exceptions.ReadTimeout:
        logger.error('[upass]验证码绕过任务创建失败，连接超时')
        return 253
    except urllib3.exceptions.MaxRetryError as err:
        logger.error(f'[upass]验证码绕过任务创建失败，超出最大重试次数: {err.reason}')
        return 252
    except requests.exceptions.ConnectionError:
        logger.error('[upass]验证码绕过任务创建失败，连接被拒绝')
        return 251
    return json.loads(response.text)


async def __create_task(data: str):
    new_task = await __make_request('createTask', data)
    if isinstance(new_task, int):
        return new_task, "noerror"
    else:
        if new_task["errorId"] == 0:
            return new_task["taskId"], "noerror"
        else:
            return new_task["errorCode"], new_task["errorDescription"]


async def _wait_task_result(api_secret: str, task_id: str, max_retry: int = 300, current_retry: int = 0):
    if current_retry >= max_retry:
        logger.error(f'[upass]验证码绕过任务创建失败，超出最大重试次数:')
        return 252

    time.sleep(1)

    task_check_data = {
        "clientKey": api_secret,
        "taskId": task_id
    }
    task_check = await __make_request('getTaskResult', json.dumps(task_check_data))
    if isinstance(task_check, int):
        return task_check
    else:
        if task_check["errorId"] == 0:
            if task_check["status"] == "processing":
                logger.info(f'[upass]验证码绕过任务正在处理中 ({current_retry}/{max_retry})...')
                return await _wait_task_result(api_secret, task_id, max_retry, current_retry + 1)
            elif task_check["status"] == "ready":
                logger.info(f'[upass]验证码问题已解决 ({current_retry}/{max_retry})')
                logger.info(f'[upass]验证码结果：{task_check["solution"]["validate"]}')
                return task_check
        else:
            logger.error(
                f'[upass]验证码绕过任务无法完成，错误代码: {task_check["errorId"]}，错误描述: {task_check["errorCode"]}')
            return task_check


async def get_balance(api_secret: str):
    result = await __make_request("getBalance", json.dumps({"clientKey": api_secret}))
    if isinstance(result, int):
        return result
    else:
        return result["balance"]


async def solve_captcha(gt: str, ch: str, api_secret: str, website_url: str):
    create_task_data = {
        "clientKey": api_secret,
        "task": {
            "type": "GeeTestTaskProxyless",
            "websiteURL": website_url,
            "gt": gt,
            "challenge": ch,
            "geetestApiServerSubdomain": "",
            "geetestGetLib": "",
            "version": 3,
            "initParameters": {}
        },
        "softId": 0
    }
    task_id, error = await __create_task(json.dumps(create_task_data))
    if error != "noerror":
        logger.error(f"[upass]验证码绕过任务 {task_id} 创建失败: {error}")
        return error
    else:
        logger.info(f"[upass]验证码绕过任务 {task_id} 创建成功")

    time.sleep(3)
    result = await _wait_task_result(api_secret=api_secret, task_id=task_id, max_retry=600, current_retry=0)
    if result['errorId'] == 0:
        logger.info(f"[upass]验证码绕过任务 {task_id} 完成，花费 US${result['cost']}")

    else:
        logger.error(f"[upass]验证码绕过任务 {task_id} 无法完成: {result['errorCode']}")
    return result
