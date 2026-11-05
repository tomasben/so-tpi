import getpass
import os
from bisect import insort, insort_left
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from itertools import count
from typing import Any, ClassVar

from loader import ProcessSpec

MEMORY_START = 100
MEMORY_SIZE = 450
MAX_MULTIPROGRAMMING = 5


# Función para obtener el nombre de usuario para la creación de procesos
# https://docs.python.org/3/library/getpass.html#getpass.getuser
def get_username() -> str:
    try:
        return getpass.getuser()
    # Puede arrojar diferentes errores dependiendo de la plataforma
    # y versión de python (3.13, 3.12, 3.11)
    except (OSError, KeyError, ImportError):
        return "usuario"


class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    READY_SUSPENDED = "ready/suspended"
    RUNNING = "running"
    FINISHED = "finished"


@dataclass(frozen=True)
class Identity:
    pid: int
    name: str
    # El proceso del simulador es el padre de los procesos creados
    ppid: int = os.getpid()
    # Primer programa de usuario en Linux
    uid: int = 1000
    username: str = get_username()


class ControlInfo:
    def __init__(self, remaining_time: int) -> None:
        self.state: ProcessState = ProcessState.NEW
        self.remaining_time: int = remaining_time
        self.base: int | None = None
        self.limit: int | None = None


class Metrics:
    def __init__(self) -> None:
        self.admit_time: int | None = None
        self.finish_time: int | None = None
        self.preemptions: int = 0


class PCB:
    def __init__(self, spec: ProcessSpec) -> None:
        self.spec = spec
        self.identity = Identity(spec.pid, spec.name)
        self.control = ControlInfo(spec.burst_time)
        self.metrics = Metrics()

    @property
    def is_finished(self) -> bool:
        return self.control.remaining_time == 0

    @property
    def turnaround_time(self) -> int | None:
        if self.metrics.finish_time is None:
            return None
        return self.metrics.finish_time - self.spec.arrival_time

    @property
    def waiting_time(self) -> int | None:
        turnaround = self.turnaround_time
        if turnaround is None:
            return None
        return turnaround - self.spec.burst_time

    def advance(self) -> None:
        if self.control.remaining_time > 0:
            self.control.remaining_time -= 1

    def mark_ready(self, time: int | None = None) -> None:
        if self.control.state == ProcessState.NEW and time is not None:
            self.metrics.admit_time = time
        self.control.state = ProcessState.READY

    def mark_ready_suspended(self) -> None:
        self.control.state = ProcessState.READY_SUSPENDED

    def mark_running(self) -> None:
        self.control.state = ProcessState.RUNNING

    def mark_finished(self, time: int) -> None:
        if self.metrics.finish_time is None:
            self.metrics.finish_time = time
        self.control.state = ProcessState.FINISHED


class Clock:
    def __init__(self) -> None:
        self._time: int = 0

    @property
    def now(self) -> int:
        return self._time

    def tick(self) -> None:
        self._time += 1


class Scheduler:
    def __init__(self, clock: Clock):
        self.new_queue: list[PCB] = []
        self.ready_queue: list[PCB] = []
        self.ready_suspended_queue: list[PCB] = []
        self.running: PCB | None = None
        self.clock: Clock = clock

    @property
    def multiprogramming_degree(self) -> int:
        """Devuelve la cantidad de procesos en cola de listos, suspendidos y en ejecución."""
        running: int = 1 if self.running is not None else 0
        return running + len(self.ready_queue) + len(self.ready_suspended_queue)

    def step(self) -> None:
        if self.running is not None:
            self.running.advance()

    def schedule(self) -> None:
        if self.running is None:
            self.dispatch()
        else:
            if len(self.ready_queue) > 0:
                upcoming = self.ready_queue[0]
                if (
                    upcoming.control.remaining_time
                    < self.running.control.remaining_time
                ):
                    self.preempt()

    def submit(self, arrivals: list[PCB]) -> None:
        """Registra los procesos creados en la cola de nuevos."""
        # La cola de nuevos se organiza de manera FIFO
        self.new_queue.extend(arrivals)

    def admit(self, pcb: PCB) -> None:
        """Admite nuevos procesos a la cola de listos, una vez cargados en memoria.
        Es responsabilidad de quien la llama asegurarse de que no se supere el grado de multiprogramación."""
        insort(self.ready_queue, pcb, key=lambda x: x.control.remaining_time)
        self.new_queue.remove(pcb)
        pcb.mark_ready(self.clock.now)

    def dispatch(self) -> None:
        """Ejecuta el proceso en la cabeza de la cola de listos.
        Es responsabilidad de quien la llama asegurarse de que no haya otro proceso en ejecución."""
        if len(self.ready_queue) > 0:
            self.running = self.ready_queue.pop(0)
            self.running.mark_running()

    def preempt(self) -> None:
        """Intercambia el proceso actualmente en ejecución por el siguiente en la cola de listos."""
        if self.running is not None and len(self.ready_queue) > 0:
            preempted = self.running

            self.running = self.ready_queue.pop(0)
            self.running.mark_running()
            insort_left(
                self.ready_queue, preempted, key=lambda x: x.control.remaining_time
            )

            preempted.mark_ready()
            preempted.metrics.preemptions += 1

    def suspend(self, pcb: PCB) -> None:
        """Mueve un proceso a la cola de listos/suspendidos.
        Es responsabilidad de quien la llama asegurarse de liberar la partición de la memoria."""
        self.ready_suspended_queue.append(pcb)
        self.new_queue.remove(pcb)
        pcb.mark_ready_suspended()

    def activate(self, pcb: PCB) -> None:
        """Mueve un proceso de la cola de listos/suspendidos a la cola de listos.
        Es responsabilidad de quien la llama asegurarse de se le haya asignado una partición en memoria."""
        insort_left(self.ready_queue, pcb, key=lambda x: x.control.remaining_time)
        self.ready_suspended_queue.remove(pcb)
        pcb.mark_ready()

    def release(self) -> None:
        """Libera el proceso actualmente en ejecución.
        Es responsabilidad de quien la llama asegurarse de que haya finalizado."""
        if self.running is not None:
            self.running.mark_finished(self.clock.now)
            self.running = None


class Partition:
    def __init__(self, number: int, base: int, pcb: PCB) -> None:
        self.pid: int = pcb.identity.pid
        self.number: int = number
        self.base: int = base
        self.size: int = pcb.spec.size

    @property
    def limit(self) -> int:
        return self.base + self.size


@dataclass(frozen=True)
class Gap:
    base: int
    size: int


class Memory:
    _number: ClassVar[Iterator[int]] = count(start=1)

    def __init__(self, size: int = MEMORY_SIZE, start: int = MEMORY_START) -> None:
        self.start: int = start
        self.end: int = self.start + size
        self.size: int = size
        self.partitions: list[Partition] = []

    def allocate(self, pcb: PCB) -> Partition | None:
        candidates = self._get_candidates(pcb.spec.size)

        if candidates:
            best_gap = min(candidates, key=lambda gap: gap.size)
            new_partition = Partition(next(self._number), best_gap.base, pcb)
            insort(self.partitions, new_partition, key=lambda part: part.base)
            pcb.control.base = new_partition.base
            pcb.control.limit = new_partition.limit
            return new_partition

        return None

    def free(self, pcb: PCB) -> None:
        """Libera la primer partición en memoria que corresponda a un proceso."""
        # Lógica válida únicamente para organizaciones de memoria contigua.
        for partition in self.partitions:
            if partition.pid == pcb.identity.pid:
                self.partitions.remove(partition)
                pcb.control.base = None
                pcb.control.limit = None

    def get_report(self) -> dict[str, Any]:
        gaps: list[Gap] = self._get_gaps()
        report = {}
        report["gaps"] = gaps
        report["min_gap"] = min(gaps, key=lambda gap: gap.size)
        report["max_gap"] = max(gaps, key=lambda gap: gap.size)
        return report

    def _get_candidates(self, required: int) -> list[Gap]:
        candidates: list[Gap] = []

        if not self.partitions:
            if self.size >= required:
                candidates.append(Gap(self.start, self.size))
        else:
            candidates = self._get_gaps()
            for gap in candidates:
                if gap.size < required:
                    candidates.remove(gap)

        return candidates

    def _get_gaps(self) -> list[Gap]:
        gaps: list[Gap] = []

        if len(self.partitions) > 0:
            first = self.partitions[0]
            leading_gap = self.start - first.base
            if leading_gap > 0:
                gaps.append(Gap(self.start, leading_gap))

            for i in range(len(self.partitions) - 1):
                lower_part = self.partitions[i]
                upper_part = self.partitions[i + 1]
                if lower_part.limit < upper_part.base:
                    gaps.append(
                        Gap(lower_part.limit, lower_part.limit - upper_part.base)
                    )

            last = self.partitions[-1]
            trailing_gap = self.end - last.limit
            if trailing_gap > 0:
                gaps.append(Gap(last.limit, trailing_gap))

        return gaps


class Simulator:
    def __init__(self, specs: list[ProcessSpec]) -> None:
        self.specs: list[ProcessSpec] = specs
        self.process_table: dict[int, PCB] = {}
        self.clock: Clock = Clock()
        self.memory: Memory = Memory()
        self.scheduler: Scheduler = Scheduler(self.clock)

    def get_report(self) -> dict[str, Any]:
        report = {}
        report["time"] = self.clock.now
        report["process_table"] = self.process_table
        report["memory"] = self.memory.get_report()
        return report

    def step(self) -> None:
        self._free_finished()
        self._collect_arrivals()
        self._activate_suspended()
        self._load_new()
        self.scheduler.schedule()
        self.scheduler.step()
        self.clock.tick()

    def _free_finished(self) -> None:
        if self.scheduler.running is not None and self.scheduler.running.is_finished:
            self.memory.free(self.scheduler.running)
            self.scheduler.release()

    def _collect_arrivals(self) -> None:
        arrivals: list[PCB] = [
            PCB(s) for s in self.specs if s.arrival_time == self.clock.now
        ]

        for pcb in arrivals:
            self.process_table[pcb.identity.pid] = pcb

        self.scheduler.submit(arrivals)

    def _activate_suspended(self) -> None:
        for pcb in self.scheduler.ready_suspended_queue.copy():
            partition = self.memory.allocate(pcb)
            if partition is not None:
                self.scheduler.activate(pcb)

    def _load_new(self) -> None:
        # Se asignan los procesos que quepan en memoria, buscando por órden de llegada
        for pcb in self.scheduler.new_queue.copy():
            if self.scheduler.multiprogramming_degree < MAX_MULTIPROGRAMMING:
                alloc_result = self.memory.allocate(pcb)
                if alloc_result is not None:
                    self.scheduler.admit(pcb)
                else:
                    self.scheduler.suspend(pcb)
            else:
                break
