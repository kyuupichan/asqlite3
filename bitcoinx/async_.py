# Copyright (c) 2018-2023, Neil Booth
#
# All right reserved.
#
# Licensed under the the Open BSV License version 3; see LICENCE for details.
#

'''Async framework interface.'''

import asyncio

__all__ = (
    'async_framework', 'Asyncio',
)


class Asyncio:

    sleep = staticmethod(asyncio.sleep)

    @staticmethod
    async def run_in_thread(func, *args):
        '''Run a function in a separate thread, and await its completion.'''
        return await asyncio.get_event_loop().run_in_executor(None, func, *args)


async_framework = Asyncio
