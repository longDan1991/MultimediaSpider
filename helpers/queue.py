import asyncio
from collections import defaultdict
from typing import Callable, Any, Dict, List, Optional


class AsyncMessageQueue:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
        self.tasks: Dict[str, List[asyncio.Task]] = defaultdict(list)

    async def add_task(
        self,
        queue_name: str,
        func: Callable,
        *args,
        wait_for_result: bool = True,
        **kwargs,
    ) -> Optional[Any]:
        if wait_for_result:
            future = asyncio.Future()
            await self.queues[queue_name].put((func, args, kwargs, future))
        else:
            await self.queues[queue_name].put((func, args, kwargs, None))

        if not self.tasks[queue_name]:
            self.tasks[queue_name].append(
                asyncio.create_task(self._process_queue(queue_name))
            )

        if wait_for_result:
            return await future
        return None

    async def _process_queue(self, queue_name: str):
        while True:
            if self.queues[queue_name].empty():
                del self.queues[queue_name]
                del self.tasks[queue_name]
                break

            func, args, kwargs, future = await self.queues[queue_name].get()
            try:
                result = await func(*args, **kwargs)
                if future:
                    future.set_result(result)
            except Exception as e:
                if future:
                    future.set_exception(e)
            finally:
                self.queues[queue_name].task_done()


_async_queue = AsyncMessageQueue()


def enqueue_task(
    func: Callable,
    queue_name: Optional[str] = None,
    wait_for_result: bool = True
) -> Callable:
    """
    返回一个函数，该函数将任务添加到指定队列中并异步执行。

    示例:
    async def example_task(x, y):
        return x + y

    enqueued_task = enqueue_task(example_task)

    # 等待结果
    result = await enqueued_task(3, 4)
    # result 将会是 7

    # 不等待结果
    await enqueued_task(3, 4, wait_for_result=False)
    # 立即返回 None，任务在后台执行

    :param func: 要执行的异步函数
    :param queue_name: 队列名称，如果不指定，默认使用函数名
    :param wait_for_result: 是否等待函数执行结果，默认为 True
    :return: 一个可以接受参数并执行任务的函数
    """
    if queue_name is None:
        queue_name = func.__name__

    async def wrapper(*args, **kwargs):
        return await _async_queue.add_task(
            queue_name, func, *args, wait_for_result=wait_for_result, **kwargs
        )

    return wrapper
