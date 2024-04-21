import multiprocessing as mp
import multiprocessing.connection as conn
import os
import time

from .task import Task

TASK_RUNNING_PLACEHOLDER_VALUE = -487329475

def decrease_tasks(workers_tasks: list[list[int]]) -> None:
    for k in range(len(workers_tasks)):
        for i in range(workers_tasks[k]):
            if workers_tasks[k][i] != -1:
                workers_tasks[k][i] -= 1

def get_free_device(workers_tasks: list[list[int]], max_workers_across_devices: int) -> tuple[int, int]:
    for task in range(max_workers_across_devices):
        for device in range(len(workers_tasks)):
            if task < len(workers_tasks[device]) and workers_tasks[device][task] == -1:
                return device, task
    return -1, -1

def scheduler_func(connection: conn.Connection,
                   devices: list[int],
                   max_workers_per_device: list[int]):
    num_procs = 0
    ended = False
    max_workers_across_devices = max(max_workers_per_device)
    workers_tasks = [[-1] * max_workers_per_device[k] for k in range(len(devices))]
    worker_processes = [[None] * max_workers_per_device[k] for k in range(len(devices))]
    messages = []
    output_messages = []

    print("Scheduler process started.")
    while True:
        # store all incoming messages in a list
        # stop storing when exit signal is received
        while connection.poll():
            msg = connection.recv()
            if isinstance(msg, str) and msg == "<EXIT>":
                ended = True
                print("Received exit signal (scheduler).")
            elif not ended:
                messages.append(msg)
        
        # if no messages and exit signal received, exit
        if ended and len(messages) == 0 and len(output_messages) == 0:
            break
        
        # process messages
        while len(messages) > 0:
            msg = messages[0]
            device, task = get_free_device(workers_tasks, max_workers_across_devices)

            if device == -1:
                # no free devices, wait for tasks to finish
                break

            # now we have a free device and task slot. run it.
            messages.pop(0)
            workers_tasks[device][task] = len(output_messages)
            output_messages.append(TASK_RUNNING_PLACEHOLDER_VALUE) # placeholder for the result

            working_dir = msg["working_dir"]
            module_name = msg["module_name"]
            function_name = msg["function_name"]
            args = msg["args"]
            kwargs = msg["kwargs"]
            worker_processes[device][task] = Task(device, working_dir, num_procs,
                                                  module_name, function_name, args, kwargs)
            worker_processes[device][task].start()
            num_procs += 1
        
        time.sleep(0.01)
        
        # get results from the tasks
        for device in range(len(devices)):
            for task in range(max_workers_per_device[device]):
                if workers_tasks[device][task] == -1:
                    continue # no task running on this slot
                if worker_processes[device][task].is_alive():
                    continue # task is still running
                output_messages[workers_tasks[device][task]] = worker_processes[device][task].get_result()
                workers_tasks[device][task] = -1
        
        # send the cached results back to the main process
        while (len(output_messages) > 0) and not (isinstance(output_messages[0], int) and output_messages[0] == TASK_RUNNING_PLACEHOLDER_VALUE):
            connection.send(output_messages[0])
            output_messages.pop(0)
            decrease_tasks(workers_tasks)
        
        time.sleep(0.01)

    print("Scheduler process exiting. Processes run: ", num_procs)

class Scheduler:
    devices: list[int]
    max_workers_per_device: list[int]
    started: bool
    killed: bool

    def __init__(self, devices: list[int], max_workers_per_device: list[int]):
        assert isinstance(devices, list), "Devices should be a list"
        assert isinstance(max_workers_per_device, list), "Max workers per device should be a list"
        assert len(devices) == len(max_workers_per_device), "Number of devices and max workers per device should be equal"
        for k in range(len(devices)):
            assert isinstance(devices[k], int), "Devices should be a list of integers"
            assert isinstance(max_workers_per_device[k], int), "Max workers per device should be a list of integers"
            assert devices[k] >= 0, "Device should be a non-negative integer"
            assert max_workers_per_device[k] > 0, "Max workers per device should be a positive integer"

        self.devices = devices
        self.max_workers_per_device = max_workers_per_device
        self.started = False
        self.killed = False

        self.connection, child_connection = mp.Pipe()
        self.process = mp.Process(target=scheduler_func, name="SchedulerProcess",
                                  args=(child_connection, devices, max_workers_per_device))
    
    def start(self):
        assert not self.started, "Scheduler already started"
        assert not self.killed, "Scheduler was killed"
        self.process.start()
        self.started = True
    
    def stop_process(self):
        if self.started:
            self.connection.send("<EXIT>")
            print("Sent exit signal to scheduler process. Waiting for process to join...")
            self.process.join()
            self.started = False
            self.killed = True
            print("Scheduler process stopped.")
    
    def schedule_function(self, working_dir: str, func: callable, args: tuple, kwargs: dict):
        assert self.started, "Scheduler not started"
        assert not self.killed, "Scheduler was killed"
        module_name = func.__module__
        function_name = func.__name__
        self.connection.send({
            "working_dir": working_dir,
            "module_name": module_name,
            "function_name": function_name,
            "args": args,
            "kwargs": kwargs
        })
    
    def get_result(self):
        assert self.started, "Scheduler not started"
        assert not self.killed, "Scheduler was killed"
        return self.connection.recv()