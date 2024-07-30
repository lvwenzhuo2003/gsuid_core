from typing import List, Type, Optional

from sqlalchemy import or_
from sqlmodel import Field, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .base_models import (
    Bind,
    Push,
    User,
    Cache,
    BaseIDModel,
    BaseBotIDModel,
    with_session,
)


class CoreTag(BaseIDModel, table=True):
    tag_type: str = Field(default='DIRECT', title='类型')  # GROUP
    tag_id: str = Field(default='1', title='群或用户ID')
    tag_name: str = Field(default='默认用户', title='标记名称')

    @classmethod
    @with_session
    async def insert_tag(
        cls,
        session: AsyncSession,
        tag_type: str,
        uid: str,
        tag_name: Optional[str] = None,
    ) -> int:
        if not tag_name:
            tag_name = '默认用户'
        await cls.full_insert_data(
            tag_type=tag_type,
            tag_id=uid,
            tag_name=tag_name,
        )
        return 1

    @classmethod
    @with_session
    async def delete_tag(
        cls,
        session: AsyncSession,
        tag_type: str,
        uid: str,
        tag_name: Optional[str],
    ) -> int:
        await cls.delete_row(tag_type=tag_type, uid=uid, tag_name=tag_name)
        return 1


class CoreUser(BaseBotIDModel, table=True):
    __table_args__ = {'extend_existing': True}

    user_id: str = Field(default='1', title='账号')
    group_id: Optional[str] = Field(default='1', title='群号')
    user_name: str = Field(default='1', title='用户名')
    user_icon: str = Field(default='1', title='用户头像')

    @classmethod
    @with_session
    async def get_all_user(
        cls,
        session: AsyncSession,
    ):
        result: Optional[List[Type["CoreUser"]]] = await cls.select_rows(True)
        return result

    @classmethod
    @with_session
    async def get_all_user_list(
        cls,
        session: AsyncSession,
    ):
        data: List[str] = []
        result = await cls.get_all_user()
        if result:
            data = [i.user_id for i in result]
            data = list(set(data))
        return data

    @classmethod
    @with_session
    async def get_group_all_user(
        cls,
        session: AsyncSession,
        group_id: str,
    ):
        result: Optional[List[Type["CoreUser"]]] = await cls.select_rows(
            group_id=group_id
        )
        return result

    @classmethod
    @with_session
    async def get_group_all_user_count(
        cls,
        session: AsyncSession,
        group_id: str,
    ):
        result = await cls.get_group_all_user(group_id)
        return len(result) if result else 0

    @classmethod
    @with_session
    async def insert_user(
        cls,
        session: AsyncSession,
        bot_id: str,
        user_id: str,
        group_id: Optional[str],
    ) -> int:
        data: Optional[Type["CoreUser"]] = await cls.base_select_data(
            bot_id=bot_id, user_id=user_id, group_id=group_id
        )
        if not data:
            await cls.full_insert_data(
                bot_id=bot_id,
                user_id=user_id,
                group_id=group_id,
            )

        '''
        if not await CoreTag.data_exist(
            tag_type='DIRECT', tag_id=user_id, tag_name='默认用户'
        ):
            await CoreTag.insert_tag(tag_type='DIRECT', uid=user_id)
        '''

        return 1


class CoreGroup(BaseBotIDModel, table=True):
    __table_args__ = {'extend_existing': True}

    group_id: str = Field(default='1', title='群号')
    group_count: int = Field(default=0, title='群活跃人数(每天更新)')
    group_name: str = Field(default='1', title='群名')
    group_icon: str = Field(default='1', title='群头像')

    @classmethod
    @with_session
    async def get_all_group(
        cls,
        session: AsyncSession,
    ):
        result: Optional[List[Type["CoreGroup"]]] = await cls.select_rows(True)
        return result

    @classmethod
    @with_session
    async def get_all_group_list(
        cls,
        session: AsyncSession,
    ):
        data: List[str] = []
        result = await cls.get_all_group()
        if result:
            data = [i.group_id for i in result]
            data = list(set(data))
        return data

    @classmethod
    @with_session
    async def insert_group(
        cls,
        session: AsyncSession,
        bot_id: str,
        group_id: str,
    ) -> int:
        data: Optional[Type["CoreGroup"]] = await cls.base_select_data(
            bot_id=bot_id, group_id=group_id
        )
        if not data:
            await cls.full_insert_data(
                bot_id=bot_id,
                group_id=group_id,
            )
        return 1


class GsBind(Bind, table=True):
    __table_args__ = {'extend_existing': True}

    uid: Optional[str] = Field(default=None, title='原神UID')
    sr_uid: Optional[str] = Field(default=None, title='星铁UID')
    bb_uid: Optional[str] = Field(default=None, title='崩坏二UID')
    bbb_uid: Optional[str] = Field(default=None, title='崩坏三UID')
    zzz_uid: Optional[str] = Field(default=None, title='绝区零UID')
    wd_uid: Optional[str] = Field(default=None, title='未定UID')
    mys_id: Optional[str] = Field(default=None, title='米游社通行证')


class GsUser(User, table=True):
    __table_args__ = {'extend_existing': True}
    cookie: str = Field(
        default=None,
        title='Cookie',
        schema_extra={'json_schema_extra': {'hint': '发送扫码登陆'}},
    )
    stoken: Optional[str] = Field(
        default=None,
        title='Stoken',
        schema_extra={'json_schema_extra': {'hint': '发送扫码登陆'}},
    )
    push_switch: str = Field(
        default='off',
        title='全局推送开关',
        schema_extra={'json_schema_extra': {'hint': 'gs开启推送'}},
    )
    sign_switch: str = Field(
        default='off',
        title='自动签到',
        schema_extra={'json_schema_extra': {'hint': 'gs开启自动签到'}},
    )
    sr_sign_switch: str = Field(
        default='off',
        title='崩铁自动签到',
        schema_extra={'json_schema_extra': {'hint': 'sr开启自动签到'}},
    )
    zzz_sign_switch: str = Field(
        default='off',
        title='绝区零自动签到',
        schema_extra={'json_schema_extra': {'hint': 'zzz开启自动签到'}},
    )
    uid: Optional[str] = Field(default=None, title='原神UID')
    sr_uid: Optional[str] = Field(default=None, title='星铁UID')
    bb_uid: Optional[str] = Field(default=None, title='崩坏二UID')
    bbb_uid: Optional[str] = Field(default=None, title='崩坏三UID')
    zzz_uid: Optional[str] = Field(default=None, title='绝区零UID')
    wd_uid: Optional[str] = Field(default=None, title='未定UID')
    mys_id: Optional[str] = Field(default=None, title='米游社通行证')
    region: Optional[str] = Field(default=None, title='原神地区')
    sr_region: Optional[str] = Field(default=None, title='星铁地区')
    zzz_region: Optional[str] = Field(default=None, title='绝区零地区')
    bb_region: Optional[str] = Field(default=None, title='崩坏二地区')
    bbb_region: Optional[str] = Field(default=None, title='崩坏三地区')
    wd_region: Optional[str] = Field(default=None, title='未定地区')
    bbs_switch: str = Field(
        default='off',
        title='自动米游币',
        schema_extra={'json_schema_extra': {'hint': 'gs开启自动米游币'}},
    )
    draw_switch: str = Field(
        default='off',
        title='自动留影叙佳期',
        schema_extra={'json_schema_extra': {'hint': 'gs开启自动留影叙佳期'}},
    )
    sr_push_switch: str = Field(default='off', title='星铁全局推送开关')
    zzz_push_switch: str = Field(default='off', title='星铁全局推送开关')
    fp: Optional[str] = Field(default=None, title='Fingerprint')
    device_id: Optional[str] = Field(default=None, title='设备ID')
    device_info: Optional[str] = Field(
        default=None,
        title='设备fp',
        schema_extra={'json_schema_extra': {'hint': 'mys设备登陆'}},
    )


class GsCache(Cache, table=True):
    __table_args__ = {'extend_existing': True}
    cookie: str = Field(default=None, title='Cookie')
    uid: Optional[str] = Field(default=None, title='原神UID')
    sr_uid: Optional[str] = Field(default=None, title='星铁UID')
    mys_id: Optional[str] = Field(default=None, title='米游社通行证')


class GsPush(Push, table=True):
    __table_args__ = {'extend_existing': True}
    bot_id: str = Field(title='平台')
    uid: str = Field(default=None, title='原神UID')
    coin_push: Optional[str] = Field(
        title='洞天宝钱推送',
        default='off',
        schema_extra={'json_schema_extra': {'hint': 'gs开启宝钱'}},
    )
    coin_value: Optional[int] = Field(title='洞天宝钱阈值', default=2100)
    coin_is_push: Optional[str] = Field(
        title='洞天宝钱是否已推送', default='off'
    )
    resin_push: Optional[str] = Field(
        title='体力推送',
        default='off',
        schema_extra={'json_schema_extra': {'hint': 'gs开启体力'}},
    )
    resin_value: Optional[int] = Field(title='体力阈值', default=140)
    resin_is_push: Optional[str] = Field(title='体力是否已推送', default='off')
    go_push: Optional[str] = Field(
        title='派遣推送',
        default='off',
        schema_extra={'json_schema_extra': {'hint': 'gs开启派遣'}},
    )
    go_value: Optional[int] = Field(title='派遣阈值', default=300)
    go_is_push: Optional[str] = Field(title='派遣是否已推送', default='off')
    transform_push: Optional[str] = Field(
        title='质变仪推送',
        default='off',
        schema_extra={'json_schema_extra': {'hint': 'gs开启质变仪'}},
    )
    transform_value: Optional[int] = Field(title='质变仪阈值', default=1000)
    transform_is_push: Optional[str] = Field(
        title='质变仪是否已推送', default='off'
    )


class GsUID(BaseIDModel, table=True):
    main_uid: str = Field(title='主UID')
    game_name: Optional[str] = Field(title='游戏名称', default=None)
    uid_1: Optional[str] = Field(title='UID1', default=None)
    uid_2: Optional[str] = Field(title='UID2', default=None)
    uid_3: Optional[str] = Field(title='UID3', default=None)
    uid_4: Optional[str] = Field(title='UID4', default=None)

    @classmethod
    @with_session
    async def _get_main_uid(
        cls,
        session: AsyncSession,
        uid: str,
        game_name: Optional[str] = None,
    ) -> Optional["GsUID"]:
        stmt = (
            select(cls)
            .where(
                or_(
                    cls.main_uid == uid,
                    cls.uid_1 == uid,
                    cls.uid_2 == uid,
                    cls.uid_3 == uid,
                    cls.uid_4 == uid,
                )
            )
            .where(cls.game_name == game_name)
        )
        results = await session.execute(stmt)
        data = results.scalars().all()
        if data:
            return data[0]
        else:
            return None

    @classmethod
    @with_session
    async def get_main_uid(
        cls,
        session: AsyncSession,
        uid: str,
        game_name: Optional[str] = None,
    ) -> str:
        data = await cls._get_main_uid(uid, game_name)
        if data:
            return data.main_uid
        else:
            return uid

    @classmethod
    @with_session
    async def uid_exist(
        cls,
        session: AsyncSession,
        uid: str,
        game_name: Optional[str] = None,
    ) -> Optional[str]:
        data = await cls._get_main_uid(uid, game_name)
        if data:
            return data.main_uid
        else:
            return None

    @classmethod
    @with_session
    async def update_data(
        cls,
        session: AsyncSession,
        uid: str,
        game_name: Optional[str] = None,
        **data,
    ):
        sql = (
            update(cls)
            .where(cls.main_uid == uid)
            .where(cls.game_name == game_name)
        )
        if data is not None:
            query = sql.values(**data)
            query.execution_options(synchronize_session='fetch')
            await session.execute(query)
            return 0
        return -1
