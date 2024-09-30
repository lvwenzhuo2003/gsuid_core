import sys
import random
import asyncio
from typing import Union

import httpx
import websockets.client
from msgspec import to_builtins
from msgspec import json as msgjson
from models import Message, MessageSend, MessageReceive
from websockets.exceptions import ConnectionClosedError

sys.path.append('..')
from segment import MessageSegment  # noqa: E402


class GsClient:
    @classmethod
    async def async_connect(
        cls, IP: str = 'localhost', PORT: Union[str, int] = '8765'
    ):
        self = GsClient()
        cls.ws_url = f'ws://{IP}:{PORT}/ws/Nonebot'
        print(f'连接至WS链接{self.ws_url}...')
        cls.ws = await websockets.client.connect(
            cls.ws_url, max_size=2**25, open_timeout=30
        )
        print('已成功链接！')
        return self

    async def recv_msg(self):
        try:
            async for message in self.ws:
                print(msgjson.decode(message, type=MessageSend))
        except ConnectionClosedError:
            print('断开连接...等待5秒，尝试重连中...')
            await asyncio.sleep(5)
            client = await self.async_connect()
            await client.start()

    async def _input(self):
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: input("请输入消息\n")
        )

    async def send_msg(self):
        while True:
            intent = await self._input()
            content = Message(type='text', data=intent)
            group_id = random.choice(['8888', '88888'])
            user_id = random.choice(['99999'])
            msg = MessageReceive(
                bot_id='console',
                # bot_id='qqgroup',
                bot_self_id='511love51',
                user_type='group',
                user_pm=0,
                group_id=group_id,
                user_id=user_id,
                content=[content],
            )
            msg_send = msgjson.encode(msg)
            await self.ws.send(msg_send)

    async def start(self):
        recv_task = asyncio.create_task(self.recv_msg())
        send_task = asyncio.create_task(self.send_msg())
        _, pending = await asyncio.wait(
            [recv_task, send_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()


async def http_test():
    msg = to_builtins(
        MessageReceive(
            content=[
                MessageSegment.text('强制刷新'),
            ]
        )
    )

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            'http://127.0.0.1:8765/api/send_msg',
            json=msg,
        )
        print(response.text)
        print(response.status_code)


async def main():
    await http_test()
    client = await GsClient().async_connect()
    await client.start()


asyncio.run(main())
