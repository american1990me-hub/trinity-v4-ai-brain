#!/usr/bin/env python3
"""Simple test run simulation for the Trinity CoreSystem.

This script initializes and starts the core system, creates a test
process, allocates memory, sends an IPC message and immediately
retrieves it, then prints system information before shutting down.
"""

from core_system import CoreSystem, SchedulingPolicy


def run_simulation():
    core = CoreSystem()
    if not core.initialize():
        print("Initialization failed")
        return
    if not core.start():
        print("Start failed")
        return

    # Create a test process
    proc_result = core.invoke_syscall(0, 1, {
        "name": "sim_process",
        "policy": SchedulingPolicy.ROUND_ROBIN.value,
    })
    if not proc_result.success:
        print("Process creation failed:", proc_result.error)
        core.stop()
        return
    pid = proc_result.value["pid"]
    print(f"Created process with PID {pid}")

    # Allocate some memory for the process
    mem_result = core.invoke_syscall(pid, 10, {"size": 4096})  # 4KB
    if mem_result.success:
        print("Allocated memory region:", mem_result.value)
    else:
        print("Memory allocation failed:", mem_result.error)

    # Send an IPC message from kernel (PID 0) to the test process
    send_result = core.invoke_syscall(0, 20, {
        "target_id": pid,
        "subject": "test",
        "payload": "Hello from kernel!",
    })
    if send_result.success:
        print("Sent IPC message:", send_result.value)
    else:
        print("IPC send failed:", send_result.error)

    # Receive the IPC message as the test process
    recv_result = core.invoke_syscall(pid, 21, {"wait": False})
    if recv_result.success:
        print("Received IPC message:", recv_result.value)
    else:
        print("IPC receive failed:", recv_result.error)

    # Display a snapshot of system information
    info = core.get_system_info()
    print("System Info:")
    for key, value in info.items():
        print(f"  {key}: {value}")

    # Shut down the core system
    core.stop()


if __name__ == "__main__":
    run_simulation()
