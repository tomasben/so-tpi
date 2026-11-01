import pprint
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from itertools import count
from random import randint
from typing import ClassVar, Self

MEMORY_START = 100
MEMORY_SIZE = 450
MEMORY_LIMIT = MEMORY_START + MEMORY_SIZE
MAX_MULTIPROGRAMMING = 5


class ProcessState(Enum):
    NEW = "new"
    READY = "ready"
    SUSPENDED = "ready/suspended"
    RUNNING = "running"
    FINISHED = "finished"


class Process:
    # Usamos un iterador para el PID autoincremental
    _id: ClassVar[Iterator[int]] = count(start=1)

    def __init__(self, burst_time: int, arrival_time: int, size: int) -> None:
        self.id: int = next(self._id)
        self.state: ProcessState = ProcessState.NEW
        self.size: int = size
        self.arrival_time: int = arrival_time
        self.burst_time: int = burst_time
        self.remaining_time: int = burst_time

    @classmethod
    def random(cls, count: int) -> list[Self]:
        instances: list[Self] = [
            cls(burst_time=randint(1, 15), size=150) for i in range(count)
        ]

        return instances

    @property
    def is_finished(self) -> bool:
        return self.remaining_time == 0

    def advance(self) -> None:
        if self.remaining_time >= 1:
            self.remaining_time -= 1

    def __repr__(self) -> str:
        return f"Proceso {self.id}, TI de {self.burst_time}"


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
        self.new_queue.extend(proc_list)
        for proc in proc_list:
            proc.state = ProcessState.NEW

    def admit(self, proc_list: list[Process]) -> None:
        """Admite nuevos procesos a la cola de listos."""
        self.ready_queue.extend(proc_list)
        self.ready_queue.sort(key=lambda x: x.remaining_time)
        for proc in proc_list:
            proc.state = ProcessState.READY

    def dispatch(self, proc: Process) -> None:
        """Ejecuta el proceso pasado por parámetro.
        Es trabajo de quien la llama asegurarse de que no haya otro proceso en ejecución."""
        self.executing = proc
        proc.state = ProcessState.RUNNING

    def timeout(self) -> None:
        """Mueve el proceso actualmente en ejecución a la cabeza de la cola de listos."""
        if self.executing is not None:
            self.ready_queue.insert(0, self.executing)
            self.executing.state = ProcessState.READY
            self.executing = None

    def suspend(self, proc: Process) -> None:
        """Mueve el proceso a la lista de suspendidos."""
        self.suspended_queue.append(proc)
        proc.state = ProcessState.SUSPENDED

    def activate(self, proc: Process) -> None:
        """Mueve un proceso de la cola de suspendidos a listos."""
        self.ready_queue.append(proc)
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

    def free(self, proc_id: int) -> Partition | None:
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

        if candidates:
            best_gap = min(candidates, key=lambda gap: gap.size)
            new_part = Partition(next(self._number), best_gap.base, required_size)
            self.partitions.insert(best_gap.index, new_part)
            return new_part

        return None


def main():
    planner = Scheduler()

    mock_data = Process.random(10)
    pprint.pp(mock_data)


if __name__ == "__main__":
    main()
