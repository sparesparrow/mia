"""
UDS Service Job - MsgJob Extension for UDS Service Execution

This module provides UDS service job management with ResponsePending handling,
timeout management, and job prioritization for automotive diagnostic services.
"""

import time
import asyncio
import threading
import logging
from typing import Dict, List, Optional, Set, Tuple, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import heapq

from .uds_router import UDSResponse, UDSNRC, UDSSessionState

logger = logging.getLogger(__name__)


class JobPriority(Enum):
    """Job priority levels for UDS service execution"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    SAFETY = 5


class JobState(Enum):
    """UDS job execution states"""
    PENDING = "pending"
    RUNNING = "running"
    RESPONSE_PENDING = "response_pending"
    COMPLETED = "completed"
    ABORTED = "aborted"
    TIMEOUT = "timeout"
    FAILED = "failed"


class JobType(Enum):
    """Types of UDS service jobs"""
    DIAGNOSTIC = "diagnostic"
    ROUTINE = "routine"
    DOWNLOAD = "download"
    UPLOAD = "upload"
    SECURITY = "security"
    MAINTENANCE = "maintenance"


@dataclass(order=True)
class UDSJob:
    """UDS service job with priority queue support"""
    priority: int  # For heapq ordering (lower number = higher priority)
    job_id: int = field(compare=False)
    service_id: int = field(compare=False)
    job_type: JobType = field(compare=False, default=JobType.DIAGNOSTIC)
    state: JobState = field(compare=False, default=JobState.PENDING)
    created_time: int = field(compare=False, default_factory=lambda: int(time.time() * 1000))
    started_time: Optional[int] = field(compare=False, default=None)
    completed_time: Optional[int] = field(compare=False, default=None)

    # Job execution parameters
    request_data: bytes = field(compare=False, default_factory=bytes)
    response_data: Optional[bytes] = field(compare=False, default=None)
    nrc_code: Optional[UDSNRC] = field(compare=False, default=None)

    # Timeout management
    p2_timeout_ms: int = field(compare=False, default=5000)  # Default P2
    p2_star_timeout_ms: int = field(compare=False, default=5000)  # Default P2*
    execution_deadline: Optional[int] = field(compare=False, default=None)

    # Response pending management
    response_pending_sent: bool = field(compare=False, default=False)
    last_response_pending_time: Optional[int] = field(compare=False, default=None)
    response_pending_interval_ms: int = field(compare=False, default=1000)  # Send 0x78 every 1s

    # Execution context
    session_state: Optional[UDSSessionState] = field(compare=False, default=None)
    source_address: Optional[int] = field(compare=False, default=None)
    is_functional: bool = field(compare=False, default=False)

    # Callbacks
    execution_callback: Optional[Callable[['UDSJob'], Awaitable[UDSResponse]]] = field(compare=False, default=None)
    completion_callback: Optional[Callable[['UDSJob'], None]] = field(compare=False, default=None)
    timeout_callback: Optional[Callable[['UDSJob'], None]] = field(compare=False, default=None)

    def __post_init__(self):
        # Set execution deadline based on P2 timeout
        if self.execution_deadline is None:
            self.execution_deadline = self.created_time + self.p2_timeout_ms

    def get_priority_enum(self) -> JobPriority:
        """Get priority as enum for external use"""
        for prio in JobPriority:
            if prio.value == (6 - self.priority):  # Convert heapq priority to enum
                return prio
        return JobPriority.NORMAL

    def set_priority(self, priority: JobPriority) -> None:
        """Set job priority"""
        self.priority = 6 - priority.value  # Convert enum to heapq priority

    def is_expired(self) -> bool:
        """Check if job has expired"""
        current_time = int(time.time() * 1000)
        return current_time > self.execution_deadline

    def needs_response_pending(self) -> bool:
        """Check if ResponsePending (0x78) should be sent"""
        if self.state != JobState.RUNNING:
            return False

        current_time = int(time.time() * 1000)

        if not self.response_pending_sent:
            # Send first 0x78 after half of P2 timeout
            return current_time > (self.started_time + (self.p2_timeout_ms // 2))
        else:
            # Send subsequent 0x78 at regular intervals
            if self.last_response_pending_time:
                return current_time > (self.last_response_pending_time + self.response_pending_interval_ms)

        return False

    def mark_response_pending_sent(self) -> None:
        """Mark that ResponsePending was sent"""
        self.response_pending_sent = True
        self.last_response_pending_time = int(time.time() * 1000)

    def complete_success(self, response_data: bytes) -> None:
        """Mark job as completed successfully"""
        self.state = JobState.COMPLETED
        self.response_data = response_data
        self.completed_time = int(time.time() * 1000)

    def complete_failure(self, nrc: UDSNRC) -> None:
        """Mark job as completed with failure"""
        self.state = JobState.FAILED
        self.nrc_code = nrc
        self.completed_time = int(time.time() * 1000)

    def abort(self) -> None:
        """Abort the job"""
        self.state = JobState.ABORTED
        self.completed_time = int(time.time() * 1000)

    def timeout(self) -> None:
        """Mark job as timed out"""
        self.state = JobState.TIMEOUT
        self.completed_time = int(time.time() * 1000)

    def get_duration(self) -> Optional[int]:
        """Get job execution duration in milliseconds"""
        if self.completed_time and self.started_time:
            return self.completed_time - self.started_time
        elif self.started_time:
            return int(time.time() * 1000) - self.started_time
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization"""
        return {
            'job_id': self.job_id,
            'service_id': self.service_id,
            'job_type': self.job_type.value,
            'state': self.state.value,
            'priority': self.get_priority_enum().value,
            'created_time': self.created_time,
            'started_time': self.started_time,
            'completed_time': self.completed_time,
            'p2_timeout_ms': self.p2_timeout_ms,
            'p2_star_timeout_ms': self.p2_star_timeout_ms,
            'execution_deadline': self.execution_deadline,
            'request_data': self.request_data.hex() if self.request_data else None,
            'response_data': self.response_data.hex() if self.response_data else None,
            'nrc_code': self.nrc_code.value if self.nrc_code else None,
            'source_address': self.source_address,
            'is_functional': self.is_functional
        }


class UdsServiceJobManager:
    """
    UDS Service Job Manager - MsgJob extension for UDS service execution

    Provides job queuing, ResponsePending handling, timeout management,
    and prioritization for automotive diagnostic services.
    """

    def __init__(self, max_concurrent_jobs: int = 4, job_queue_size: int = 16):
        """
        Initialize UDS Service Job Manager

        Args:
            max_concurrent_jobs: Maximum number of jobs that can execute concurrently
            job_queue_size: Maximum number of jobs in queue
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.job_queue_size = job_queue_size

        # Job management
        self._job_queue: List[UDSJob] = []  # Priority queue (heapq)
        self._running_jobs: Dict[int, UDSJob] = {}
        self._completed_jobs: Dict[int, UDSJob] = {}
        self._job_id_counter = 0

        # Threading and synchronization
        self._queue_lock = threading.RLock()
        self._job_lock = threading.RLock()

        # Background task management
        self._executor_task: Optional[asyncio.Task] = None
        self._timeout_monitor_task: Optional[asyncio.Task] = None
        self._running = False

        # Transport abstraction
        self._response_sender: Optional[Callable[[UDSResponse, Optional[int]], Awaitable[None]]] = None

        # Job factory for creating jobs from requests
        self._job_factory: Optional[Callable[[int, bytes, UDSSessionState, Optional[int], bool], UDSJob]] = None

        # Statistics
        self._total_jobs_created = 0
        self._total_jobs_completed = 0
        self._total_jobs_failed = 0
        self._total_jobs_timed_out = 0
        self._total_response_pending_sent = 0

    def set_response_sender(self, sender: Callable[[UDSResponse, Optional[int]], Awaitable[None]]) -> None:
        """Set the response sender function"""
        self._response_sender = sender

    def set_job_factory(self, factory: Callable[[int, bytes, UDSSessionState, Optional[int], bool], UDSJob]) -> None:
        """Set job factory function"""
        self._job_factory = factory

    async def start(self) -> None:
        """Start the job manager"""
        if self._running:
            return

        self._running = True
        self._executor_task = asyncio.create_task(self._job_executor_loop())
        self._timeout_monitor_task = asyncio.create_task(self._timeout_monitor_loop())

        logger.info("UDS Service Job Manager started")

    async def stop(self) -> None:
        """Stop the job manager"""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        if self._executor_task and not self._executor_task.done():
            self._executor_task.cancel()
            try:
                await self._executor_task
            except asyncio.CancelledError:
                pass

        if self._timeout_monitor_task and not self._timeout_monitor_task.done():
            self._timeout_monitor_task.cancel()
            try:
                await self._timeout_monitor_task
            except asyncio.CancelledError:
                pass

        # Abort all running jobs
        with self._job_lock:
            for job in self._running_jobs.values():
                job.abort()
            self._running_jobs.clear()

        logger.info("UDS Service Job Manager stopped")

    def create_job(self, service_id: int, request_data: bytes,
                   session_state: UDSSessionState,
                   source_address: Optional[int] = None,
                   is_functional: bool = False,
                   priority: JobPriority = JobPriority.NORMAL) -> Optional[UDSJob]:
        """
        Create a new UDS service job

        Args:
            service_id: UDS service ID
            request_data: Request data bytes
            session_state: Current session state
            source_address: Source ECU address
            is_functional: Whether this is functional addressing
            priority: Job priority level

        Returns:
            Created job or None if queue full
        """
        with self._queue_lock:
            if len(self._job_queue) >= self.job_queue_size:
                logger.warning("Job queue full, cannot create new job")
                return None

            # Generate job ID
            self._job_id_counter += 1
            job_id = self._job_id_counter

            # Create job using factory or default
            if self._job_factory:
                job = self._job_factory(service_id, request_data, session_state, source_address, is_functional)
                job.job_id = job_id
                job.set_priority(priority)
            else:
                # Default job creation
                job = UDSJob(
                    priority=6 - priority.value,  # Convert to heapq priority
                    job_id=job_id,
                    service_id=service_id,
                    request_data=request_data,
                    session_state=session_state,
                    source_address=source_address,
                    is_functional=is_functional,
                    p2_timeout_ms=session_state.p2_timeout_ms,
                    p2_star_timeout_ms=session_state.p2_star_timeout_ms
                )

            # Add to priority queue
            heapq.heappush(self._job_queue, job)
            self._total_jobs_created += 1

            logger.debug(f"Created job {job_id} for service 0x{service_id:02X}")
            return job

    async def _job_executor_loop(self) -> None:
        """Background task to execute queued jobs"""
        logger.info("Job executor loop started")

        while self._running:
            try:
                # Get next job from queue
                job = None
                with self._queue_lock:
                    if self._job_queue and len(self._running_jobs) < self.max_concurrent_jobs:
                        job = heapq.heappop(self._job_queue)

                if job:
                    # Start job execution
                    asyncio.create_task(self._execute_job(job))

                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)

            except Exception as e:
                logger.error(f"Error in job executor loop: {e}")
                await asyncio.sleep(0.1)

        logger.info("Job executor loop stopped")

    async def _execute_job(self, job: UDSJob) -> None:
        """Execute a single job"""
        # Mark job as running
        job.state = JobState.RUNNING
        job.started_time = int(time.time() * 1000)

        with self._job_lock:
            self._running_jobs[job.job_id] = job

        logger.debug(f"Started execution of job {job.job_id}")

        try:
            # Execute job using callback
            if job.execution_callback:
                response = await job.execution_callback(job)

                # Handle response
                if response.response_code == 0x00:  # Positive response
                    job.complete_success(response.data)
                    self._total_jobs_completed += 1

                    # Send final response
                    if self._response_sender:
                        await self._response_sender(response, job.source_address)

                else:  # Negative response
                    job.complete_failure(UDSNRC(response.response_code))
                    self._total_jobs_failed += 1

                    # Send NRC response
                    if self._response_sender:
                        await self._response_sender(response, job.source_address)

            else:
                # No execution callback - fail job
                job.complete_failure(UDSNRC.CONDITIONS_NOT_CORRECT)
                self._total_jobs_failed += 1

        except Exception as e:
            logger.error(f"Job execution error for job {job.job_id}: {e}")
            job.complete_failure(UDSNRC.FAILED)
            self._total_jobs_failed += 1

        finally:
            # Clean up running job
            with self._job_lock:
                self._running_jobs.pop(job.job_id, None)

            # Move to completed jobs (keep last N for debugging)
            with self._queue_lock:
                self._completed_jobs[job.job_id] = job
                if len(self._completed_jobs) > 100:  # Keep last 100 jobs
                    oldest_id = min(self._completed_jobs.keys())
                    del self._completed_jobs[oldest_id]

            # Call completion callback
            if job.completion_callback:
                try:
                    job.completion_callback(job)
                except Exception as e:
                    logger.error(f"Completion callback error for job {job.job_id}: {e}")

    async def _timeout_monitor_loop(self) -> None:
        """Background task to monitor job timeouts and send ResponsePending"""
        logger.info("Timeout monitor loop started")

        while self._running:
            try:
                current_time = int(time.time() * 1000)
                expired_jobs = []
                response_pending_jobs = []

                # Check running jobs
                with self._job_lock:
                    for job in self._running_jobs.values():
                        if job.is_expired():
                            expired_jobs.append(job)
                        elif job.needs_response_pending():
                            response_pending_jobs.append(job)

                # Handle expired jobs
                for job in expired_jobs:
                    logger.warning(f"Job {job.job_id} timed out")
                    job.timeout()
                    self._total_jobs_timed_out += 1

                    # Send timeout response
                    timeout_response = UDSResponse.negative_response(
                        job.service_id, UDSNRC.FAILED
                    )
                    if self._response_sender:
                        await self._response_sender(timeout_response, job.source_address)

                    # Call timeout callback
                    if job.timeout_callback:
                        try:
                            job.timeout_callback(job)
                        except Exception as e:
                            logger.error(f"Timeout callback error for job {job.job_id}: {e}")

                # Send ResponsePending for long-running jobs
                for job in response_pending_jobs:
                    response_pending = UDSResponse.response_pending(job.service_id)
                    if self._response_sender:
                        await self._response_sender(response_pending, job.source_address)

                    job.mark_response_pending_sent()
                    self._total_response_pending_sent += 1

                    logger.debug(f"Sent ResponsePending for job {job.job_id}")

                # Check every 100ms
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in timeout monitor loop: {e}")
                await asyncio.sleep(0.1)

        logger.info("Timeout monitor loop stopped")

    def abort_job(self, job_id: int) -> bool:
        """
        Abort a running job

        Args:
            job_id: Job ID to abort

        Returns:
            True if job was aborted
        """
        with self._job_lock:
            job = self._running_jobs.get(job_id)
            if job:
                job.abort()

                # Send abort response
                abort_response = UDSResponse.negative_response(
                    job.service_id, UDSNRC.FAILED
                )
                if self._response_sender:
                    asyncio.create_task(self._response_sender(abort_response, job.source_address))

                logger.info(f"Aborted job {job_id}")
                return True

        return False

    def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get status of a job"""
        with self._job_lock:
            job = self._running_jobs.get(job_id)
            if job:
                return job.to_dict()

        with self._queue_lock:
            for queued_job in self._job_queue:
                if queued_job.job_id == job_id:
                    return queued_job.to_dict()

            job = self._completed_jobs.get(job_id)
            if job:
                return job.to_dict()

        return None

    def get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get all running jobs"""
        with self._job_lock:
            return [job.to_dict() for job in self._running_jobs.values()]

    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information"""
        with self._queue_lock:
            return {
                'queued_jobs': len(self._job_queue),
                'max_queue_size': self.job_queue_size,
                'running_jobs': len(self._running_jobs),
                'max_concurrent_jobs': self.max_concurrent_jobs,
                'completed_jobs': len(self._completed_jobs)
            }

    def get_statistics(self) -> Dict[str, Any]:
        """Get job manager statistics"""
        return {
            'total_jobs_created': self._total_jobs_created,
            'total_jobs_completed': self._total_jobs_completed,
            'total_jobs_failed': self._total_jobs_failed,
            'total_jobs_timed_out': self._total_jobs_timed_out,
            'total_response_pending_sent': self._total_response_pending_sent,
            'current_running_jobs': len(self._running_jobs),
            'current_queued_jobs': len(self._job_queue)
        }

    def clear_completed_jobs(self) -> None:
        """Clear completed jobs history"""
        with self._queue_lock:
            self._completed_jobs.clear()