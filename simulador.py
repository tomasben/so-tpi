import pprint
import random
from collections.abc import Iterator
from itertools import count
from typing import ClassVar, Self


class Process:
    _id: ClassVar[Iterator[int]] = count(start=1)

    def __init__(self, burst_time: int) -> None:
        self.id: int = next(self._id)
        self.burst_time: int = burst_time
        self.remaining_time: int = burst_time


    @classmethod
    def random(cls, count: int) -> list[Self]:
        instances: list[Self] = [
            cls(burst_time=random.randint(1, 15))
            for i in range(count)
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
        self.ready_queue: list[Process] = []
        self.executing: Process | None = None


    def asign(self, asignee: list[Process]) -> None:
        self.ready_queue.extend(asignee)


    def execute(self) -> None:
        start_time: int = 0
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



def main():
    planner = Scheduler()

    mock_data = Process.random(10)
    pprint.pp(mock_data)

    planner.asign(mock_data)
    planner.execute()


if __name__ == "__main__":
    main()
