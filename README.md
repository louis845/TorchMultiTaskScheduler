# TorchMultiTaskScheduler
Repo for PyTorch multi-task scheduler

## Usage
This package enables multi-task scheduling on multiple threads using multiple GPUs (e.g 2x T4).

The main file to import is `torchtaskscheduler.scheduler`. The class Scheduler takes care of scheduling multiple tasks.

Scheduler(devices: list[int], max_workers_per_device: list[int])

    * devices: List of GPU devices (e.g [0, 1, 2] for cuda:0, cuda:1, cuda:2)
    * max_workers_per_device: How many workers per device

Scheduler.start() - start the scheduler

Scheduler.stop_process() - stops the scheduler, and waits for subprocesses to stop

Scheduler.schedule_function(working_dir: str, func: callable, args: tuple, kwargs: dict) - Runs the callable with associated arguments on the working directory

    * args: tuple of args for the function
    * kwargs: dict of kwargs for the function

Scheduler.get_result() - Gets the return result of the function in order of schedule_function. Returns 0 if function returns None and succeeds. Returns -1 if error happened.