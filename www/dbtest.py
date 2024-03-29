#/usr/bin/env python3

import asyncio
import orm
from models import User, Blog, Comment


async def test(loop):
    await  orm.create_pool(loop, user='awesome', password='awe@s0me', db='awesome')
    u = User(name='test', email='test@example', passwd='122345', image='about:blank')

    await  u.save()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test(loop))
    print('test finished')
    loop.close()