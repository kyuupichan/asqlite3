# Copyright (c) 2018-2023, Neil Booth
#
# All right reserved.
#
# Licensed under the the Open BSV License version 3; see LICENCE for details.
#

'''Async frameworks.'''

import curio


__all__ = ('Curio', )


class Curio:

    sleep = staticmethod(curio.sleep)
    run_in_thread = staticmethod(curio.run_in_thread)
