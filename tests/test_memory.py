import unittest

from loader import ProcessSpec
from simulador import MEMORY_SIZE, PCB, Memory, Partition


def make_pcb(pid: int, size: int) -> PCB:
    spec = ProcessSpec(
        pid=pid,
        size=size,
        arrival_time=0,
        burst_time=1,
    )
    return PCB(spec)


class TestMemory(unittest.TestCase):
    def setUp(self) -> None:
        self.memory = Memory()

    def place(self, layout: list[tuple[int, int]]) -> list[PCB]:
        processes: list[PCB] = []
        partitions: list[Partition] = []

        for number, (base, size) in enumerate(layout, start=1):
            pcb = make_pcb(number, size)
            pcb.control.base = base
            pcb.control.limit = base + size
            processes.append(pcb)
            partitions.append(Partition(number, base, pcb))

        self.memory.partitions = partitions
        return processes

    def current_layout(self) -> list[tuple[int, int, int]]:
        return [(part.pid, part.base, part.size) for part in self.memory.partitions]

    def test_request_larger_than_memory_fails(self) -> None:
        pcb = make_pcb(1, MEMORY_SIZE + 1)
        partition = self.memory.allocate(pcb)

        self.assertIsNone(partition)
        self.assertEqual(self.memory.partitions, [])
        self.assertIsNone(pcb.control.base)
        self.assertIsNone(pcb.control.limit)

    def test_exact_fit_in_middle_gap(self) -> None:
        # Hueco exacto de 100K entre las direcciones 300 y 400.
        self.place([(100, 200), (400, 150)])
        pcb = make_pcb(3, 100)
        partition = self.memory.allocate(pcb)

        self.assertIsNotNone(partition)
        self.assertEqual(partition.base, 300)
        self.assertEqual(
            self.current_layout(), [(1, 100, 200), (3, 300, 100), (2, 400, 150)]
        )

    def test_fits_in_leading_gap(self) -> None:
        self.place([(200, 350)])
        pcb = make_pcb(2, 100)
        partition = self.memory.allocate(pcb)

        self.assertIsNotNone(partition)
        self.assertEqual(partition.base, 100)
        self.assertEqual(self.current_layout(), [(2, 100, 100), (1, 200, 350)])

    def test_fits_in_trailing_gap(self) -> None:
        self.place([(100, 300)])
        pcb = make_pcb(2, 150)
        partition = self.memory.allocate(pcb)

        self.assertIsNotNone(partition)
        self.assertEqual(partition.base, 400)
        self.assertEqual(self.current_layout(), [(1, 100, 300), (2, 400, 150)])

    def test_best_fit_selects_smallest_gap(self) -> None:
        # Huecos de 100K (100..200) y 30K (300..330).
        # First-Fit elegiría el primero; Best-Fit debe elegir el segundo.
        self.place([(200, 100), (330, 220)])
        pcb = make_pcb(3, 30)
        partition = self.memory.allocate(pcb)

        self.assertIsNotNone(partition)
        self.assertEqual(partition.base, 300)
        self.assertEqual(
            self.current_layout(), [(1, 200, 100), (3, 300, 30), (2, 330, 220)]
        )


if __name__ == "__main__":
    unittest.main()
