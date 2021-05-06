"""
Schedule tasks to run at a given time.
"""
import threading
import time
import datetime as dt

class TaskNode:
    def __init__(self, value):
        self.next = None
        self.value = value
        pass

class Scheduler:
    def __init__(self):
        self.head = None
        self.active = False
        self.timer = None
        pass

    def add_task(self, time, action):
        '''Add a task to the task-chain.

        Args:
            time (datetime): When the task occurs.
            action (function): Function to run when `time` is reached.
        '''
        self._handle_terminated()
        task = TaskNode({"time": time, "action": action})
        head = self.head
        if head is None: # First task is being added
            self.head =  task
        else:
            node = self.head
            while node:
                isHead = node == self.head
                notTail = node.next != None

                afterNode = time > node.value["time"]
                if notTail:
                    beforeNextNode = time < node.next.value["time"]
                else:
                    beforeNextNode = True # allow all times at the tail

                if afterNode and beforeNextNode: # Add task after current node
                    task.next = node.next
                    node.next = task
                    break
                elif isHead and not afterNode: # Add task before current node (head)
                    task.next = node
                    self.head = task
                node = node.next
        
        if task == self.head:
            # Timer needs to be changed
            if self.timer and self.active:
                self.timer.cancel()
                self._wait_for_head()

    def _wrap_action(self, action):
        def wrapped():
            action()
            # Forget completed task
            self.head = self.head.next
            if self.active:
                self._wait_for_head()
        return wrapped

    def _wait_for_head(self):
        task = self.head
        if task:
            interval = (task.value["time"] - dt.datetime.now()).total_seconds()
            # NOTE: Negative intervals execute instantly and are allowed in threading.Timer()
            self.timer = threading.Timer(interval, self._wrap_action(task.value["action"]))
            self.timer.start()

    def start(self, auto_stop=False):
        '''Start the scheduler.

        Args:
            auto_stop(bool): Whether the scheduler should stop when no tasks are scheduled.
        '''
        self._handle_terminated()
        self.resume()
        if auto_stop is False:
            # Add daemon to keep scheduler alive
            self.add_task(dt.date.now() + dt.timedelta(days=1), lambda: print("Exiting"))

    def terminate(self):
        '''Stop the scheduler.

        Detaches the head and marks scheduler as terminated.
        '''
        self._handle_terminated()
        self.pause()
        self.head = None
        self.active = "TERMINATED"

    def _handle_terminated(self):
        if self.active == "TERMINATED":
            raise Exception("Can not use terminated scheduler.")

    def pause(self, timeToLast=-1):
        '''Pause the scheduler.

        Args:
            timeToLast(float, optional): Number of seconds to pause the scheduler for.

            Note that the scheduler's activity is reverted, not toggled.
        '''
        self._handle_terminated()
        self.active = False
        if timeToLast>=0:
            if self.timer:
                self.timer.cancel()
            threading.Timer(timeToLast, lambda: self.resume())
    
    def resume(self, timeToLast=-1):
        '''Resume the scheduler.

        Args:
            timeToLast(float, optional): Number of seconds to resume the scheduler for.
        
            Note that the scheduler's activity is reverted, not toggled.
        '''
        self._handle_terminated()
        self.active = True
        self._wait_for_head()
        if timeToLast>=0:
            threading.Timer(timeToLast, lambda: self.pause())