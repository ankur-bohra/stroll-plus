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

    def start(self, auto_stop):
        '''Start the scheduler.

        Args:
            auto_stop(bool): Whether the scheduler should stop when no tasks are scheduled.
        '''
        self.resume()
        if auto_stop is False:
            # Add daemon to keep scheduler alive
            self.add_task(dt.date.today() + dt.timedelta(days=1), lambda: print("Exiting"))

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