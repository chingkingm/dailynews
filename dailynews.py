import asyncio
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional


from hoshino import Service, aiorequests, get_bot
from hoshino.typing import CQEvent, CQHttpError, HoshinoBot, MessageSegment

sv = Service(
    "dailynews",
    enable_on_default=False,
    help_="""每日早报
启用后会在每天早上发送一份早报
[@bot 今日早报] （测试用）手动发送一份早报""",
)

subs_path = os.path.join(os.path.dirname(__file__), "subscription.json")


def load_subs() -> Dict:
    with open(subs_path, "r", encoding="utf8") as f:
        return json.load(f)


def update_subs(data):
    with open(subs_path, "w", encoding="utf8") as f:
        json.dump(data, f, sort_keys=True,indent=4)


async def get_image():
    class dnError(BaseException):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
    info = await aiorequests.get("http://dwz.2xb.cn/zaob")
    try:
        info = await info.json()
    except:
        print(await info.text)
        raise
    if info["msg"] == "Success":
        return MessageSegment.image(info["imageUrl"],cache=True)
    else:
        sv.logger.error(f'daily news error {info["msg"]}')
        raise dnError(f'daily news error {info["msg"]}')

@sv.scheduled_job("cron", hour="8", minute="40", jitter=50)
async def autonews():
    try:
        info = await aiorequests.get("http://dwz.2xb.cn/zaob")
        try:
            info = await info.json()
        except:
            print(await info.text)
            raise
        if info["msg"] == "Success":
            await sv.broadcast(
                MessageSegment.image(info["imageUrl"], cache=True), "dailynews"
            )
        else:
            sv.logger.error(f'daily news error {info["msg"]}')
    except CQHttpError as e:
        sv.logger.error(f"daily news error {e}")
        raise


@sv.on_fullmatch("今日早报", only_to_me=True)
async def handnews(bot: HoshinoBot, ev: CQEvent):
    # info = await aiorequests.get("http://dwz.2xb.cn/zaob")
    # info = await info.json()
    # if info["msg"] == "Success":
    #     await bot.send(ev, MessageSegment.image(info["imageUrl"], cache=True))
    # else:
    #     sv.logger.error(f'daily news error {info["msg"]}')
    im = await get_image()
    await bot.send(ev,im)

@sv.on_fullmatch("订阅每日早报")
async def subscribe(bot: HoshinoBot, ev: CQEvent):
    qid = ev.user_id
    subscribers = load_subs()
    if str(qid) in subscribers.keys():
        await bot.send(ev, f"不可以重复订阅！", at_sender=True)
        return
    friend_list = await bot.get_friend_list()
    if qid in [friend.get("user_id") for friend in friend_list]:
        today = datetime.today().day
        subscribers.update({str(qid):{"today":today,"pushed":True}})
        update_subs(subscribers)
        im = await get_image()
        await bot.send_private_msg(
            user_id=qid, message=im
        )
        await bot.send(ev, f"已订阅每日早报，发送'TDMRZB/退订每日早报/取消订阅每日早报'以退订。", at_sender=True)
        return
    else:
        await bot.send(ev, f"请先添加bot为好友")
        return


@sv.on_fullmatch(("TDMRZB", "退订每日早报", "取消订阅每日早报"))
async def unsubscribe(bot: HoshinoBot, ev: CQEvent):
    subscribers = load_subs()
    qid = ev.user_id
    if str(qid) not in subscribers.keys():
        await bot.send(ev, f"尚未订阅每日早报！", at_sender=True)
        return
    subscribers.pop(str(qid))
    update_subs(subscribers)
    await bot.send(ev, f"取消订阅成功！", at_sender=True)

@sv.scheduled_job("cron",hour="7",minute="40-50",jitter=50)
# @sv.scheduled_job("cron",hour="2",minute="0/1",jitter=50)
async def push():
    bot = get_bot()
    today = datetime.today().day
    subs = load_subs()
    im = await get_image()
    for qid in subs:
        if subs[qid].get("today") != today or not subs[qid].get("pushed"):
            try:
                await bot.send_private_msg(user_id=int(qid),message=im)
            except:
                continue
            subs.update({str(qid):{"today":today,"pushed":True}})
            update_subs(subs)
            await asyncio.sleep(random.randint(1,5))
