#!/usr/bin/env python3
# Trinity OS - Core System Implementation
# Core system that integrates process, memory, and resource management
from __future__ import annotations
import os
import sys
import json
import time
import uuid
import signal
import logging
import threading
import multiprocessing
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Set, Tuple, Union, Callable

VERSION = "0.2.0"

# ======================================================================
# PROCESS MANAGEMENT
# ======================================================================

class ProcessState(Enum):
    """Process states"""
    CREATED = auto()      # Process created but not started
    READY = auto()        # Ready to be scheduled
    RUNNING = auto()      # Currently running
    BLOCKED = auto()      # Blocked on I/O or other resource
    SUSPENDED = auto()    # Suspended by user or system
    TERMINATED = auto()   # Process has terminated
    ZOMBIE = auto()       # Process terminated but not reaped

class ProcessPriority(Enum):
    """Process priority levels"""
    IDLE = 0              # Background, only run when no other process is ready
    LOW = 10              # Low priority, non-interactive
    NORMAL = 20           # Normal priority for regular processes
    HIGH = 30             # High priority for important processes
    REAL_TIME = 40        # Real-time priority, time-critical processes
    SYSTEM = 50           # System-level priority, kernel processes

class SchedulingPolicy(Enum):
    """Process scheduling policies"""
    ROUND_ROBIN = auto()  # Round-robin scheduling
    FIFO = auto()         # First-in, first-out scheduling
    PRIORITY = auto()     # Priority-based scheduling
    DEADLINE = auto()     # Deadline-based scheduling
    FAIR = auto()         # Fair scheduling with time slices

@dataclass
class ProcessInfo:
    """Information about a process"""
    process_id: int
    parent_id: int
    name: str
    state: ProcessState
    priority: ProcessPriority
    policy: SchedulingPolicy
    cpu_affinity: List[int] = field(default_factory=list)
    creation_time: float = field(default_factory=time.time)
    start_time: float = 0
    runtime: float = 0
    deadline: Optional[float] = None
    time_slice: float = 0.01  # Default time slice in seconds
    weight: float = 1.0       # Weight for fair scheduling
    quantum_used: float = 0   # Time used in current quantum
    last_run: float = 0       # Last time the process ran
    context_switches: int = 0 # Number of context switches
    memory_usage: int = 0     # Memory used by the process
    file_descriptors: Set[int] = field(default_factory=set)  # Open file descriptors
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ProcessContext:
    """Process execution context"""
    registers: Dict[str, int] = field(default_factory=dict)
    stack_pointer: int = 0
    program_counter: int = 0
    stack: List[int] = field(default_factory=list)
    memory_segments: Dict[str, Tuple[int, int]] = field(default_factory=dict)

# ======================================================================
# MEMORY MANAGEMENT
# ======================================================================

class MemoryPermission(Enum):
    """Memory access permissions"""
    NONE = 0              # No access
    READ = 1              # Read-only
    WRITE = 2             # Write-only (rare)
    READ_WRITE = 3        # Read and write
    EXECUTE = 4           # Execute-only (rare)
    READ_EXECUTE = 5      # Read and execute
    WRITE_EXECUTE = 6     # Write and execute (rare)
    READ_WRITE_EXECUTE = 7 # All permissions

class MemoryType(Enum):
    """Types of memory for allocation"""
    NORMAL = auto()       # General purpose memory
    SHARED = auto()       # Shared between processes
    LOCKED = auto()       # Locked in physical memory (non-swappable)
    HUGE = auto()         # Large pages (if supported)
    DEVICE = auto()       # Device memory (if applicable)

@dataclass
class MemoryRegion:
    """Represents a region of memory"""
    id: str
    start: int
    size: int
    owner_pid: int
    memory_type: MemoryType
    permissions: MemoryPermission
    name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_mapped: bool = True
    created_at: float = field(default_factory=time.time)
    last_accessed: float = 0

@dataclass
class MemorySegment:
    """Memory segment for a process"""
    start: int
    size: int
    permissions: MemoryPermission
    segment_type: str  # "code", "data", "stack", "heap", etc.
    content: bytearray = field(default_factory=bytearray)

# ======================================================================
# SYSTEM CALL INTERFACE
# ======================================================================

class SyscallCategory(Enum):
    """Categories of system calls"""
    PROCESS = auto()      # Process management
    FILE = auto()         # File operations
    MEMORY = auto()       # Memory management
    NETWORK = auto()      # Network operations
    IPC = auto()          # Inter-process communication
    DEVICE = auto()       # Device access
    SYSTEM = auto()       # System information
    TIME = auto()         # Time and date
    SECURITY = auto()     # Security and permissions
    USER = auto()         # User management
    DEBUG = auto()        # Debugging and monitoring

class SyscallError(Exception):
    """System call related errors"""
    pass

class PermissionError(SyscallError):
    """Permission denied error"""
    pass

class NotImplementedError(SyscallError):
    """System call not implemented"""
    pass

@dataclass
class SyscallResult:
    """Result of a system call"""
    success: bool
    value: Any = None
    error: Optional[str] = None

# ======================================================================
# INTER-PROCESS COMMUNICATION
# ======================================================================

class IPCMessageType(Enum):
    """IPC message types"""
    SIGNAL = auto()       # Signal message
    DATA = auto()         # Data message
    REQUEST = auto()      # Request message
    RESPONSE = auto()     # Response message
    EVENT = auto()        # Event message
    CONTROL = auto()      # Control message

@dataclass
class IPCMessage:
    """Inter-process communication message"""
    message_id: str
    message_type: IPCMessageType
    sender_id: int
    target_id: int
    subject: str
    payload: Any
    timestamp: float = field(default_factory=time.time)
    timeout: float = 0.0  # 0 = no timeout
    headers: Dict[str, Any] = field(default_factory=dict)

# ======================================================================
# CORE SYSTEM IMPLEMENTATION
# ======================================================================

class CoreSystem:
    """Trinity OS Core System implementation"""
    
    def __init__(self, root_dir: str = "trinity_root"):
        self.root_dir = os.path.abspath(root_dir)
        self.core_dir = os.path.join(self.root_dir, "var", "core")
        
        # System state
        self.running = False
        self.initialized = False
        
        # Process management
        self.processes: Dict[int, ProcessInfo] = {}
        self.contexts: Dict[int, ProcessContext] = {}
        self.next_pid = 1000  # Start at 1000, kernel processes below
        self.ready_queue: List[int] = []
        self.blocked_processes: Dict[int, str] = {}  # pid -> reason
        
        # Memory management
        self.memory_regions: Dict[str, MemoryRegion] = {}
        self.process_memory: Dict[int, List[str]] = {}  # pid -> list of region IDs
        self.physical_memory_size = 0
        self.available_memory = 0
        
        # System calls
        self.syscalls: Dict[int, Dict[str, Any]] = {}
        self.syscall_stats: Dict[int, Dict[str, int]] = {}
        
        # IPC
        self.message_queues: Dict[int, List[IPCMessage]] = {}  # pid -> messages
        self.pending_responses: Dict[str, IPCMessage] = {}  # req_id -> response
        
        # Mutexes for thread safety
        self._proc_lock = threading.RLock()
        self._mem_lock = threading.RLock()
        self._syscall_lock = threading.RLock()
        self._ipc_lock = threading.RLock()
        
        # Scheduler thread
        self._scheduler_thread = None
        self._stop_event = threading.Event()
        
        # Create directories
        os.makedirs(self.core_dir, exist_ok=True)
        
        # Register built-in system calls
        self._register_syscalls()
    
    def initialize(self) -> bool:
        """Initialize the core system"""
        if self.initialized:
            return True
            
        try:
            logging.info("Initializing Trinity OS Core System")
            
            # Detect system capabilities
            self._detect_capabilities()
            
            # Initialize process 0 (kernel)
            kernel_proc = ProcessInfo(
                process_id=0,
                parent_id=0,
                name="kernel",
                state=ProcessState.RUNNING,
                priority=ProcessPriority.SYSTEM,
                policy=SchedulingPolicy.FIFO
            )
            self.processes[0] = kernel_proc
            
            # Initialize process 1 (init)
            init_proc = ProcessInfo(
                process_id=1,
                parent_id=0,
                name="init",
                state=ProcessState.READY,
                priority=ProcessPriority.SYSTEM,
                policy=SchedulingPolicy.FIFO
            )
            self.processes[1] = init_proc
            self.ready_queue.append(1)
            
            # Allocate initial memory regions
            self._init_memory()
            
            self.initialized = True
            logging.info("Core System initialized successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to initialize Core System: {e}")
            return False
    
    def start(self) -> bool:
        """Start the core system"""
        if not self.initialized:
            if not self.initialize():
                return False
        
        if self.running:
            return True
            
        try:
            logging.info("Starting Trinity OS Core System")
            
            # Start scheduler thread
            self._stop_event.clear()
            self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self._scheduler_thread.start()
            
            self.running = True
            logging.info("Core System started successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to start Core System: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the core system"""
        if not self.running:
            return True
            
        try:
            logging.info("Stopping Trinity OS Core System")
            
            # Stop scheduler thread
            self._stop_event.set()
            if self._scheduler_thread:
                self._scheduler_thread.join(timeout=3.0)
                self._scheduler_thread = None
            
            self.running = False
            logging.info("Core System stopped successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to stop Core System: {e}")
            return False
    
    def _detect_capabilities(self):
        """Detect system capabilities"""
        # Detect physical memory
        try:
            import psutil
            vm = psutil.virtual_memory()
            self.physical_memory_size = vm.total
            self.available_memory = vm.available
        except ImportError:
            # Fallback: assume 1GB
            self.physical_memory_size = 1024 * 1024 * 1024
            self.available_memory = self.physical_memory_size // 2
    
    def _init_memory(self):
        """Initialize memory subsystem"""
        # Allocate kernel memory region
        kernel_region = MemoryRegion(
            id="kernel_main",
            start=0x1000,  # Start at 4K to avoid NULL pointer
            size=64 * 1024 * 1024,  # 64MB for kernel
            owner_pid=0,
            memory_type=MemoryType.LOCKED,
            permissions=MemoryPermission.READ_WRITE_EXECUTE
        )
        self.memory_regions[kernel_region.id] = kernel_region
        
        if 0 not in self.process_memory:
            self.process_memory[0] = []
        self.process_memory[0].append(kernel_region.id)
        
        # Allocate shared memory region
        shared_region = MemoryRegion(
            id="system_shared",
            start=0x10000000,  # 256MB mark
            size=32 * 1024 * 1024,  # 32MB for shared memory
            owner_pid=0,
            memory_type=MemoryType.SHARED,
            permissions=MemoryPermission.READ_WRITE
        )
        self.memory_regions[shared_region.id] = shared_region
        self.process_memory[0].append(shared_region.id)
    
    def _register_syscalls(self):
        """Register built-in system calls"""
        with self._syscall_lock:
            # Process management syscalls
            self.syscalls[1] = {
                "number": 1,
                "name": "process_create",
                "handler": self._syscall_process_create,
                "category": SyscallCategory.PROCESS
            }
            
            self.syscalls[2] = {
                "number": 2,
                "name": "process_exit",
                "handler": self._syscall_process_exit,
                "category": SyscallCategory.PROCESS
            }
            
            self.syscalls[3] = {
                "number": 3,
                "name": "process_wait",
                "handler": self._syscall_process_wait,
                "category": SyscallCategory.PROCESS
            }
            
            # Memory management syscalls
            self.syscalls[10] = {
                "number": 10,
                "name": "memory_allocate",
                "handler": self._syscall_memory_allocate,
                "category": SyscallCategory.MEMORY
            }
            
            self.syscalls[11] = {
                "number": 11,
                "name": "memory_free",
                "handler": self._syscall_memory_free,
                "category": SyscallCategory.MEMORY
            }
            
            self.syscalls[12] = {
                "number": 12,
                "name": "memory_map",
                "handler": self._syscall_memory_map,
                "category": SyscallCategory.MEMORY
            }
            
            # IPC syscalls
            self.syscalls[20] = {
                "number": 20,
                "name": "ipc_send",
                "handler": self._syscall_ipc_send,
                "category": SyscallCategory.IPC
            }
            
            self.syscalls[21] = {
                "number": 21,
                "name": "ipc_receive",
                "handler": self._syscall_ipc_receive,
                "category": SyscallCategory.IPC
            }
            
            # Initialize stats
            for num in self.syscalls:
                self.syscall_stats[num] = {
                    "calls": 0,
                    "errors": 0,
                    "total_time": 0
                }
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while not self._stop_event.is_set():
            try:
                # Run scheduler
                self._run_scheduler()
                
                # Sleep for a bit
                time.sleep(0.001)  # 1ms
            except Exception as e:
                logging.error(f"Error in scheduler loop: {e}")
                time.sleep(0.01)  # Sleep a bit longer on error
    
    def _run_scheduler(self):
        """Run one pass of the scheduler"""
        with self._proc_lock:
            # Check if we have processes to run
            if not self.ready_queue:
                return
            
            # Get next process
            pid = self.ready_queue.pop(0)
            
            if pid not in self.processes:
                return
                
            process = self.processes[pid]
            
            # Update process state
            old_state = process.state
            process.state = ProcessState.RUNNING
            
            # Execute process for its time slice
            process.last_run = time.time()
            self._execute_process(pid, process.time_slice)
            
            # Check if process is still running
            if pid in self.processes and self.processes[pid].state == ProcessState.RUNNING:
                # Put back in ready queue
                self.processes[pid].state = ProcessState.READY
                self.ready_queue.append(pid)
    
    def _execute_process(self, pid: int, time_slice: float):
        """Execute a process for a given time slice"""
        # This is a simplified simulation
        # In a real OS, this would actually run the process code
        
        # Update runtime
        if pid in self.processes:
            self.processes[pid].runtime += time_slice
            self.processes[pid].context_switches += 1
    
    def invoke_syscall(self, process_id: int, syscall_number: int, args: Dict[str, Any]) -> SyscallResult:
        """Invoke a system call"""
        with self._syscall_lock:
            # Check if syscall exists
            if syscall_number not in self.syscalls:
                return SyscallResult(
                    success=False,
                    error=f"Invalid system call number: {syscall_number}"
                )
            
            # Get syscall info
            syscall = self.syscalls[syscall_number]
            
            # Update stats
            self.syscall_stats[syscall_number]["calls"] += 1
            
            # Call handler
            try:
                start_time = time.time()
                result = syscall["handler"](process_id, **args)
                elapsed = time.time() - start_time
                
                # Update timing stats
                self.syscall_stats[syscall_number]["total_time"] += elapsed
                
                return result
            except Exception as e:
                # Update error stats
                self.syscall_stats[syscall_number]["errors"] += 1
                
                # Return error
                return SyscallResult(
                    success=False,
                    error=str(e)
                )
    
    # System call implementations
    
    def _syscall_process_create(self, process_id: int, name: str, priority: int = 20, 
                              policy: int = 0) -> SyscallResult:
        """Create a new process"""
        with self._proc_lock:
            # Validate parameters
            if not name:
                return SyscallResult(success=False, error="Process name cannot be empty")
            
            # Get next PID
            new_pid = self.next_pid
            self.next_pid += 1
            
            # Create process info
            new_process = ProcessInfo(
                process_id=new_pid,
                parent_id=process_id,
                name=name,
                state=ProcessState.CREATED,
                priority=ProcessPriority(min(max(0, priority), 50)),
                policy=SchedulingPolicy(min(max(0, policy), len(SchedulingPolicy) - 1))
            )
            
            # Add to process table
            self.processes[new_pid] = new_process
            
            # Add to ready queue
            new_process.state = ProcessState.READY
            self.ready_queue.append(new_pid)
            
            # Initialize memory for the process
            self._init_process_memory(new_pid)
            
            # Initialize message queue
            with self._ipc_lock:
                self.message_queues[new_pid] = []
            
            return SyscallResult(
                success=True,
                value={"pid": new_pid}
            )
    
    def _syscall_process_exit(self, process_id: int, exit_code: int = 0) -> SyscallResult:
        """Exit a process"""
        with self._proc_lock:
            # Check if process exists
            if process_id not in self.processes:
                return SyscallResult(success=False, error="Process does not exist")
            
            # Update process state
            self.processes[process_id].state = ProcessState.TERMINATED
            self.processes[process_id].metadata["exit_code"] = exit_code
            
            # Remove from ready queue
            if process_id in self.ready_queue:
                self.ready_queue.remove(process_id)
            
            # Remove from blocked processes
            if process_id in self.blocked_processes:
                del self.blocked_processes[process_id]
            
            # Free memory
            self._free_process_memory(process_id)
            
            # Clean up message queue
            with self._ipc_lock:
                if process_id in self.message_queues:
                    del self.message_queues[process_id]
            
            return SyscallResult(success=True)
    
    def _syscall_process_wait(self, process_id: int, wait_pid: int) -> SyscallResult:
        """Wait for a process to exit"""
        with self._proc_lock:
            # Check if process exists
            if wait_pid not in self.processes:
                return SyscallResult(success=False, error="Target process does not exist")
            
            # Check if process already terminated
            if self.processes[wait_pid].state == ProcessState.TERMINATED:
                exit_code = self.processes[wait_pid].metadata.get("exit_code", 0)
                return SyscallResult(
                    success=True,
                    value={"exit_code": exit_code}
                )
            
            # Block process
            if process_id in self.ready_queue:
                self.ready_queue.remove(process_id)
            
            self.processes[process_id].state = ProcessState.BLOCKED
            self.blocked_processes[process_id] = f"wait:{wait_pid}"
            
            return SyscallResult(
                success=True,
                value={"status": "blocked"}
            )
    
    def _syscall_memory_allocate(self, process_id: int, size: int, 
                               permissions: int = 3) -> SyscallResult:
        """Allocate memory for a process"""
        with self._mem_lock:
            # Check if process exists
            if process_id not in self.processes:
                return SyscallResult(success=False, error="Process does not exist")
            
            # Validate size
            if size <= 0:
                return SyscallResult(success=False, error="Invalid memory size")
            
            # Find free memory region
            region_id = str(uuid.uuid4())
            
            # Find start address (simplified)
            start = 0x20000000  # User space starts at 512MB
            if process_id in self.process_memory:
                # Find highest end address of existing regions
                for rid in self.process_memory[process_id]:
                    region = self.memory_regions[rid]
                    end = region.start + region.size
                    if end > start:
                        start = end
            
            # Create memory region
            region = MemoryRegion(
                id=region_id,
                start=start,
                size=size,
                owner_pid=process_id,
                memory_type=MemoryType.NORMAL,
                permissions=MemoryPermission(permissions)
            )
            
            # Register region
            self.memory_regions[region_id] = region
            
            # Add to process memory
            if process_id not in self.process_memory:
                self.process_memory[process_id] = []
            self.process_memory[process_id].append(region_id)
            
            # Update process memory usage
            if process_id in self.processes:
                self.processes[process_id].memory_usage += size
            
            return SyscallResult(
                success=True,
                value={
                    "region_id": region_id,
                    "address": region.start,
                    "size": region.size
                }
            )
    
    def _syscall_memory_free(self, process_id: int, region_id: str) -> SyscallResult:
        """Free a memory region"""
        with self._mem_lock:
            # Check if region exists
            if region_id not in self.memory_regions:
                return SyscallResult(success=False, error="Memory region does not exist")
            
            region = self.memory_regions[region_id]
            
            # Check if process owns the region
            if region.owner_pid != process_id:
                return SyscallResult(success=False, error="Permission denied")
            
            # Remove from process memory
            if process_id in self.process_memory and region_id in self.process_memory[process_id]:
                self.process_memory[process_id].remove(region_id)
            
            # Update process memory usage
            if process_id in self.processes:
                self.processes[process_id].memory_usage -= region.size
            
            # Delete region
            del self.memory_regions[region_id]
            
            return SyscallResult(success=True)
    
    def _syscall_memory_map(self, process_id: int, target_id: str, 
                          local_address: int, permissions: int = 1) -> SyscallResult:
        """Map a memory region into process address space"""
        with self._mem_lock:
            # Check if region exists
            if target_id not in self.memory_regions:
                return SyscallResult(success=False, error="Target memory region does not exist")
            
            target_region = self.memory_regions[target_id]
            
            # Check if target is shared or owned by process
            if target_region.memory_type != MemoryType.SHARED and target_region.owner_pid != process_id:
                return SyscallResult(success=False, error="Permission denied")
            
            # Create a new mapping region
            region_id = str(uuid.uuid4())
            
            # Use provided address or find free space
            start = local_address if local_address > 0 else 0x30000000  # Mapping space at 768MB
            
            # Create memory region
            region = MemoryRegion(
                id=region_id,
                start=start,
                size=target_region.size,
                owner_pid=process_id,
                memory_type=MemoryType.SHARED,
                permissions=MemoryPermission(permissions),
                metadata={"mapped_from": target_id}
            )
            
            # Register region
            self.memory_regions[region_id] = region
            
            # Add to process memory
            if process_id not in self.process_memory:
                self.process_memory[process_id] = []
            self.process_memory[process_id].append(region_id)
            
            return SyscallResult(
                success=True,
                value={
                    "region_id": region_id,
                    "address": region.start,
                    "size": region.size
                }
            )
    
    def _syscall_ipc_send(self, process_id: int, target_id: int, subject: str, 
                        message_type: int = 1, payload: Any = None, 
                        timeout: float = 0.0) -> SyscallResult:
        """Send an IPC message"""
        with self._ipc_lock:
            # Check if processes exist
            if process_id not in self.processes:
                return SyscallResult(success=False, error="Sender process does not exist")
                
            if target_id not in self.processes:
                return SyscallResult(success=False, error="Target process does not exist")
            
            # Create message
            message_id = str(uuid.uuid4())
            message = IPCMessage(
                message_id=message_id,
                message_type=IPCMessageType(message_type),
                sender_id=process_id,
                target_id=target_id,
                subject=subject,
                payload=payload,
                timeout=timeout
            )
            
            # Add to target's message queue
            if target_id not in self.message_queues:
                self.message_queues[target_id] = []
            
            self.message_queues[target_id].append(message)
            
            # Wake up target if it's blocked waiting for messages
            with self._proc_lock:
                if (target_id in self.blocked_processes and 
                    self.blocked_processes[target_id] == "ipc_receive"):
                    # Unblock process
                    del self.blocked_processes[target_id]
                    
                    # Update state
                    self.processes[target_id].state = ProcessState.READY
                    
                    # Add to ready queue
                    self.ready_queue.append(target_id)
            
            return SyscallResult(
                success=True,
                value={"message_id": message_id}
            )
    
    def _syscall_ipc_receive(self, process_id: int, wait: bool = True) -> SyscallResult:
        """Receive an IPC message"""
        with self._ipc_lock:
            # Check if process exists
            if process_id not in self.processes:
                return SyscallResult(success=False, error="Process does not exist")
            
            # Check if messages available
            if (process_id in self.message_queues and 
                len(self.message_queues[process_id]) > 0):
                # Get oldest message
                message = self.message_queues[process_id].pop(0)
                
                return SyscallResult(
                    success=True,
                    value={
                        "message_id": message.message_id,
                        "message_type": message.message_type.name,
                        "sender_id": message.sender_id,
                        "subject": message.subject,
                        "payload": message.payload,
                        "timestamp": message.timestamp,
                        "headers": message.headers
                    }
                )
            
            # No messages available
            if not wait:
                return SyscallResult(
                    success=True,
                    value=None
                )
            
            # Block process
            with self._proc_lock:
                if process_id in self.ready_queue:
                    self.ready_queue.remove(process_id)
                
                self.processes[process_id].state = ProcessState.BLOCKED
                self.blocked_processes[process_id] = "ipc_receive"
            
            return SyscallResult(
                success=True,
                value={"status": "blocked"}
            )
    
    def _init_process_memory(self, pid: int):
        """Initialize memory for a new process"""
        with self._mem_lock:
            # Allocate code segment
            code_region = MemoryRegion(
                id=f"{pid}_code",
                start=0x20000000,  # User code starts at 512MB
                size=1 * 1024 * 1024,  # 1MB for code
                owner_pid=pid,
                memory_type=MemoryType.NORMAL,
                permissions=MemoryPermission.READ_EXECUTE,
                name="code"
            )
            self.memory_regions[code_region.id] = code_region
            
            # Allocate data segment
            data_region = MemoryRegion(
                id=f"{pid}_data",
                start=0x21000000,  # After code
                size=4 * 1024 * 1024,  # 4MB for data
                owner_pid=pid,
                memory_type=MemoryType.NORMAL,
                permissions=MemoryPermission.READ_WRITE,
                name="data"
            )
            self.memory_regions[data_region.id] = data_region
            
            # Allocate stack segment
            stack_region = MemoryRegion(
                id=f"{pid}_stack",
                start=0x22000000,  # After data
                size=2 * 1024 * 1024,  # 2MB for stack
                owner_pid=pid,
                memory_type=MemoryType.NORMAL,
                permissions=MemoryPermission.READ_WRITE,
                name="stack"
            )
            self.memory_regions[stack_region.id] = stack_region
            
            # Add to process memory
            self.process_memory[pid] = [
                code_region.id,
                data_region.id,
                stack_region.id
            ]
            
            # Update process memory usage
            if pid in self.processes:
                self.processes[pid].memory_usage = (
                    code_region.size + data_region.size + stack_region.size
                )
    
    def _free_process_memory(self, pid: int):
        """Free all memory for a process"""
        with self._mem_lock:
            if pid not in self.process_memory:
                return
            
            # Get all regions for the process
            region_ids = list(self.process_memory[pid])
            
            # Delete regions
            for region_id in region_ids:
                if region_id in self.memory_regions:
                    del self.memory_regions[region_id]
            
            # Clear process memory
            del self.process_memory[pid]
            
            # Update process memory usage
            if pid in self.processes:
                self.processes[pid].memory_usage = 0
    
    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """Get information about a process"""
        with self._proc_lock:
            if pid not in self.processes:
                return None
            
            process = self.processes[pid]
            
            return {
                "pid": process.process_id,
                "parent_pid": process.parent_id,
                "name": process.name,
                "state": process.state.name,
                "priority": process.priority.name,
                "policy": process.policy.name,
                "cpu_affinity": process.cpu_affinity,
                "creation_time": process.creation_time,
                "start_time": process.start_time,
                "runtime": process.runtime,
                "deadline": process.deadline,
                "memory_usage": process.memory_usage,
                "context_switches": process.context_switches,
                "metadata": process.metadata
            }
    
    def get_memory_info(self, region_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a memory region"""
        with self._mem_lock:
            if region_id not in self.memory_regions:
                return None
            
            region = self.memory_regions[region_id]
            
            return {
                "id": region.id,
                "start": region.start,
                "size": region.size,
                "owner_pid": region.owner_pid,
                "type": region.memory_type.name,
                "permissions": region.permissions.name,
                "name": region.name,
                "is_mapped": region.is_mapped,
                "created_at": region.created_at,
                "last_accessed": region.last_accessed,
                "metadata": region.metadata
            }
    
    def get_syscall_stats(self) -> Dict[int, Dict[str, Any]]:
        """Get system call statistics"""
        with self._syscall_lock:
            stats = {}
            
            for num, syscall in self.syscalls.items():
                if num in self.syscall_stats:
                    stats[num] = {
                        "number": num,
                        "name": syscall["name"],
                        "category": syscall["category"].name,
                        "calls": self.syscall_stats[num]["calls"],
                        "errors": self.syscall_stats[num]["errors"],
                        "total_time": self.syscall_stats[num]["total_time"],
                        "avg_time": (
                            self.syscall_stats[num]["total_time"] / max(1, self.syscall_stats[num]["calls"])
                        )
                    }
            
            return stats
    
    def get_process_list(self) -> List[Dict[str, Any]]:
        """Get list of all processes"""
        with self._proc_lock:
            return [self.get_process_info(pid) for pid in self.processes]
    
    def get_memory_map(self, pid: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get memory map, optionally filtered by process"""
        with self._mem_lock:
            result = []
            
            if pid is not None:
                # Get memory map for specific process
                if pid in self.process_memory:
                    for region_id in self.process_memory[pid]:
                        if region_id in self.memory_regions:
                            info = self.get_memory_info(region_id)
                            if info:
                                result.append(info)
            else:
                # Get all memory regions
                for region_id in self.memory_regions:
                    info = self.get_memory_info(region_id)
                    if info:
                        result.append(info)
            
            # Sort by start address
            result.sort(key=lambda r: r["start"])
            
            return result
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        with self._proc_lock, self._mem_lock:
            # Count processes by state
            process_counts = {state.name: 0 for state in ProcessState}
            for process in self.processes.values():
                process_counts[process.state.name] += 1
            
            # Count memory by type
            memory_counts = {mem_type.name: 0 for mem_type in MemoryType}
            for region in self.memory_regions.values():
                memory_counts[region.memory_type.name] += region.size
            
            return {
                "version": VERSION,
                "uptime": time.time() - self.processes[0].creation_time if 0 in self.processes else 0,
                "process_count": len(self.processes),
                "process_states": process_counts,
                "memory_total": self.physical_memory_size,
                "memory_available": self.available_memory,
                "memory_used": sum(region.size for region in self.memory_regions.values()),
                "memory_by_type": memory_counts,
                "syscall_count": sum(stats["calls"] for stats in self.syscall_stats.values())
            }

def main():
    """Test the core system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Trinity OS Core System")
    parser.add_argument("--root-dir", default="trinity_root", help="Root directory")
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    # Create core system
    core = CoreSystem(root_dir=args.root_dir)
    
    # Initialize and start
    if not core.initialize():
        print("Failed to initialize core system")
        return 1
    
    if not core.start():
        print("Failed to start core system")
        return 1
    
    print("Core system started")
    
    # Create a test process
    result = core.invoke_syscall(0, 1, {"name": "test_process"})
    if result.success:
        test_pid = result.value["pid"]
        print(f"Created test process with PID {test_pid}")
        
        # Allocate some memory
        mem_result = core.invoke_syscall(test_pid, 10, {"size": 1024 * 1024})  # 1MB
        if mem_result.success:
            print(f"Allocated memory: {mem_result.value}")
        
        # Send an IPC message
        ipc_result = core.invoke_syscall(0, 20, {
            "target_id": test_pid,
            "subject": "test",
            "payload": "Hello from kernel!"
        })
        if ipc_result.success:
            print(f"Sent IPC message: {ipc_result.value}")
    
    # Print system info
    info = core.get_system_info()
    print("\nSystem Information:")
    print(f"Version: {info['version']}")
    print(f"Uptime: {info['uptime']:.2f} seconds")
    print(f"Processes: {info['process_count']}")
    print(f"Memory Used: {info['memory_used'] / (1024*1024):.2f} MB")
    print(f"Memory Available: {info['memory_available'] / (1024*1024):.2f} MB")
    
    # Print process list
    processes = core.get_process_list()
    print("\nProcesses:")
    for proc in processes:
        print(f"PID {proc['pid']}: {proc['name']} ({proc['state']})")
    
    # Print memory map
    memory_map = core.get_memory_map()
    print("\nMemory Map:")
    for region in memory_map:
        print(f"Region {region['id']}: {region['start']:x}-{region['start']+region['size']:x} "
              f"({region['size'] / 1024:.1f} KB, {region['permissions']})")
    
    try:
        # Keep running until interrupted
        print("\nRunning... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping core system...")
    finally:
        core.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
