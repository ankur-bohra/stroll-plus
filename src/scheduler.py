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
        task = TaskNode({"time": time, "action": action})
        head = self.head
        if head is None: # First task is being added
            self.head =  task
        else:
            node = self.head
            while node:
                if node.next and node.value["time"] < time < node.next.value["time"]:
                    # Insert task in between
                    node.next = task
                    task.next = node.next
                    break
                node = node.next
        
        if head != self.head:
            # Timer needs to be changed
            if self.timer and self.active:
                self.timer.cancel()
                self._wait_for_head()

    def _wrap_action(self, action):
        def wrapped():
            action()
            if self.active:
                self._wait_for_head()
        return wrapped

    def _wait_for_head(self):
        task = self.head
        interval = task.value["time"] - dt.datetime.now()
        self.timer = threading.Timer(interval, self._wrap_action(task.value["action"]))

    def start(self):
        '''Start the scheduler.
        '''
        self.active = True
        self._wait_for_head()

    def pause(self, delay=None):
        '''Pause the scheduler.

        Args:
            delay(int, optional): Number of seconds to pause the scheduler for.
        '''
        self.active = False
        if delay:
            self.timer.cancel()
            time.sleep(delay)
            self.resume()
    
    def resume(self):
        '''Resume the scheduler.
        '''
        self.active = True
        self._wait_for_head()