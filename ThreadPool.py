from queue import Queue


class ThreadPool:
    """ Pool of threads consuming tasks from a queue """

    def __init__(self, num_threads, cls_worker):
        self.tasks = Queue(num_threads)
        for _ in range(num_threads):
            cls_worker.from_queue(tasks=self.tasks)

    def add_task(self, task):
        """ Add a task to the queue """
        self.tasks.put(task)

    def wait_completion(self):
        """ Wait for completion of all the tasks in the queue """
        self.tasks.join()
