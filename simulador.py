import getpass
import os
from bisect import insort, insort_left
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from itertools import count
from typing import ClassVar

from loader import ProcessSpec

MEMORY_START = 100
MEMORY_SIZE = 450
MEMORY_LIMIT = MEMORY_START + MEMORY_SIZE
MAX_MULTIPROGRAMMING = 5


# Función para obtener el nombre de usuario para la creación de procesos
# https://docs.python.org/3/library/getpass.html#getpass.getuser
def get_username() -> str:
    try:
        return getpass.getuser()
    # Puede arrojar diferentes errores dependiendo de la plataforma y versión
    # de python (3.13, 3.12, 3.11)
    except (OSError, KeyError, ImportError):
        return "usuario"


class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    SUSPENDED = "ready/suspended"
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
    def __init__(self, remaining: int) -> None:
        self.state: ProcessState = ProcessState.NEW
        self.remaining: int = remaining
        self.base: int | None = None
        self.limit: int | None = None


class Metrics:
    def __init__(self, arrival: int, burst: int) -> None:
        self.arrival_time: int = arrival
        self.burst_time: int = burst
        self.admit_time: int | None = None
        self.dispatch_time: int | None = None
        self.finish_time: int | None = None
        self.preemptions: int = 0


class PCB:
    def __init__(self, spec: ProcessSpec) -> None:
        self.spec = spec
        self.identity = Identity(spec.pid, spec.name)
        self.control = ControlInfo(spec.burst_time)
        self.metrics = Metrics(spec.arrival_time, spec.burst_time)

    @property
    def is_finished(self) -> bool:
        return self.control.remaining == 0

    def advance(self) -> None:
        if self.control.remaining > 0:
            self.control.remaining -= 1


class Scheduler:
    def __init__(self):
        self.new_queue: list[Process] = []
        self.ready_queue: list[Process] = []
        self.suspended_queue: list[Process] = []
        self.executing: Process | None = None

    @property
    def mult_degree(self) -> int:
        """Devuelve la cantidad de procesos en cola de listos, suspendidos y en ejecución."""
        executing: int = 1 if self.executing is not None else 0
        return executing + len(self.ready_queue) + len(self.suspended_queue)

    def execute(self) -> None:
        time: int = 0

        if not self.ready_queue:
            return
        else:
            self.executing = self.ready_queue.pop(0)
            print(f"Process {self.executing.id} is now executing")

            while True:
                if not self.executing.is_finished:
                    self.executing.advance()
                    time += 1

                elif self.ready_queue:
                    print(f"Process {self.executing.id} finished at t: {time}")
                    self.executing = self.ready_queue.pop(0)
                    print(f"Process {self.executing.id} is now executing")

                else:
                    print(f"Process {self.executing.id} finished at t: {time}")
                    print("All process finished. Exiting CPU Scheduler")
                    break

    def advance(self) -> None:
        if self.executing is not None:
            self.executing.advance()

    def submit(self, proc_list: list[Process]) -> None:
        """Registra los procesos creados en la cola de nuevos."""
        # La cola de nuevos se organiza de manera FIFO
        self.new_queue.extend(proc_list)
        for proc in proc_list:
            proc.state = ProcessState.NEW

    def admit(self, proc: Process) -> None:
        """Admite nuevos procesos a la cola de listos.
        Es responsabilidad de quien la llama asegurarse que haya cupos en el procesador."""
        insort(self.ready_queue, proc, key=lambda x: x.remaining_time)
        self.new_queue.remove(proc)
        proc.state = ProcessState.READY

    def dispatch(self) -> None:
        """Ejecuta el proceso en la cabeza de la cola de listos.
        Es responsabilidad de quien la llama asegurarse de que no haya otro proceso en ejecución."""
        if len(self.ready_queue) > 0:
            next = self.ready_queue.pop(0)
            self.executing = next
            next.state = ProcessState.RUNNING

    def preempt(self) -> None:
        if self.executing is not None and len(self.ready_queue) > 0:
            old = self.executing
            self.executing = self.ready_queue.pop(0)
            self.executing.state = ProcessState.RUNNING
            insort_left(self.ready_queue, old, key=lambda x: x.remaining_time)
            old.state = ProcessState.READY

    def suspend(self) -> None:
        """Mueve el proceso en ejecución a la lista de suspendidos."""
        if self.executing is not None:
            self.executing.state = ProcessState.SUSPENDED
            self.suspended_queue.insert(0, self.executing)
            self.executing = None

    def suspend(self, proc: Process) -> None:
        """Mueve el proceso a la lista de suspendidos."""
        self.suspended_queue.append(proc)
        proc.state = ProcessState.SUSPENDED

    def activate(self, proc: Process) -> None:
        """Mueve un proceso de la cola de suspendidos a la cabeza de listos."""
        insort_left(self.ready_queue, proc, key=lambda x: x.remaining_time)
        self.suspended_queue.remove(proc)
        proc.state = ProcessState.READY

    def release(self) -> None:
        """Libera el proceso actualmente en ejecución.
        Es responsabilidad de quien la llama asegurarse de que haya finalizado."""
        if self.executing is not None:
            self.executing.state = ProcessState.FINISHED
            self.executing = None


class Partition:
    def __init__(self, number: int, base: int, proc: Process) -> None:
        self.number: int = number
        self.base: int = base
        self.size: int = proc.size
        self.proc_id: int = proc.id


@dataclass(frozen=True)
class Gap:
    base: int
    size: int
    index: int


class Memory:
    _number: ClassVar[Iterator[int]] = count(start=1)

    def __init__(self, size: int, start: int = 0) -> None:
        self.start: int = start
        self.limit: int = self.start + size
        self.size: int = size
        self.partitions: list[Partition] = []

    def allocate(self, proc: Process) -> Partition | None:
        candidates = self._get_candidates(proc.size)

        if candidates:
            best_gap = min(candidates, key=lambda gap: gap.size)
            new_part = Partition(next(self._number), best_gap.base, proc)
            self.partitions.insert(best_gap.index, new_part)
            return new_part

        return None

    def free(self, proc_id: int) -> None:
        for part in self.partitions:
            if part.proc_id == proc_id:
                self.partitions.remove(part)
                return part

        return None

    def _get_candidates(self, required: int) -> list[Gap]:
        candidates: list[Gap] = []

        if not self.partitions:
            if self.size >= required:
                candidates.append(Gap(self.start, self.size, 0))
        else:
            first = self.partitions[0]
            last = self.partitions[-1]

            leading_gap = first.base - self.start
            if leading_gap >= required:
                candidates.append(Gap(self.start, leading_gap, 0))

            for i in range(len(self.partitions) - 1):
                lower_part = self.partitions[i]
                upper_part = self.partitions[i + 1]
                lower_bound = lower_part.base + lower_part.size

                inner_gap = upper_part.base - lower_bound
                if inner_gap >= required:
                    candidates.append(Gap(lower_bound, inner_gap, index=i + 1))

            trailing_gap = self.limit - (last.base + last.size)
            if trailing_gap >= required:
                candidates.append(
                    Gap(last.base + last.size, trailing_gap, len(self.partitions))
                )

        return candidates

    def _allocate(self, required_size: int) -> Partition | None:
        candidates = self._get_candidates(required_size)

class Simulator:
    # TODO: Inicializar procesos dentro de Scheduler, pasados como parámetro a Simulator
    def __init__(self, memory: Memory, scheduler: Scheduler) -> None:
        self.memory: Memory = memory
        self.scheduler: Scheduler = scheduler
        self.time: int = 0

    def advance(self) -> None:
        mock_proc: list[Process] = load_processes("test/procesos.csv")
        pprint.pp(mock_proc)
        arrivals = [p for p in mock_proc if p.arrival_time == self.time]

        while len(mock_proc) > 0:
            self._free_finished()
            self._collect_arrivals(arrivals)
            self._activate_suspended()
            self._load_ready()
            self._assign_cpu()
            self._advance()

    def _advance(self, units: int = 1) -> None:
        self.scheduler.advance()
        self.time += units

    def _free_finished(self) -> None:
        if (
            self.scheduler.executing is not None
            and self.scheduler.executing.is_finished
        ):
            self.memory.free(self.scheduler.executing.id)
            self.scheduler.release()

    def _collect_arrivals(self, arrivals: list[Process]) -> None:
        self.scheduler.submit(arrivals)

    def _activate_suspended(self) -> None:
        for proc in self.scheduler.suspended_queue.copy():
            res = self.memory.allocate(proc)
            if res is not None:
                self.scheduler.activate(proc)

    def _load_ready(self) -> None:
        for proc in self.scheduler.new_queue.copy():
            if self.scheduler.mult_degree < 5:
                alloc_result = self.memory.allocate(proc)
                if alloc_result is not None:
                    self.scheduler.admit(proc)
            else:
                break

    def _assign_cpu(self) -> None:
        if self.scheduler.executing is None:
            self.scheduler.dispatch()
        else:
            if len(self.scheduler.ready_queue) > 0:
                upcoming = self.scheduler.ready_queue[0]
                current = self.scheduler.executing
                if upcoming.remaining_time < current.remaining_time:
                    self.scheduler.preempt()


def load_processes(path: str) -> list[Process]:
    with open(path, newline="", encoding="utf-8") as file:
        return [
            Process(
                size=int(row["size"]),
                arrival_time=int(row["arrival_time"]),
                burst_time=int(row["burst_time"]),
            )
            for row in csv.DictReader(file)
        ]


def main():
    planner = Scheduler()

    mock_data = Process.random(10)
    pprint.pp(mock_data)


if __name__ == "__main__":
    main()
