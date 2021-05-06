from threading import Timer

from scheduler import Scheduler

# SCHEDULER LINKS

scheduler = Scheduler()
scheduler.start()

def changeSchedulerActivity(action, timeToLast=-1, callback=None):
    '''Change the scheduler's activity

    Args:
        newAction(string): The action to perform on the scheduler. "Pause" or "Resume".
        timeToLast(float, optional): No. of seconds to change to newAcitivty for before reverting.
    '''
    action = action.lower()
    if hasattr(scheduler, action):
        getattr(scheduler, action)(timeToLast)
        if callback:
            Timer(timeToLast, callback)
    else:
        raise AttributeError("No such action: %s" % action)