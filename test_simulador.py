import unittest

from simulador import Memory, Partition

MEMORY_START = 100
MEMORY_SIZE = 450
MEMORY_LIMIT = MEMORY_START + MEMORY_SIZE


def place(memory: Memory, layout: list[tuple[int, int]]) -> None:
    """Coloca particiones en posiciones fijas (base, tamaño), saltandose la asignación."""
    memory.partitions = [
        Partition(number, base, size)
        for number, (base, size) in enumerate(layout, start=1)
    ]


def assert_invariant(memory: Memory) -> None:
    previous_end = MEMORY_START
    for part in memory.partitions:
        assert part.base >= previous_end, "Solapamiento o particiones desordenadas"
        previous_end = part.base + part.size

    assert previous_end <= MEMORY_LIMIT, "Última partición excede el límite de memoria"


class TestAllocation(unittest.TestCase):
    def set_memory(self):
        self.memory = Memory(start=MEMORY_START, size=MEMORY_SIZE)

    # Pedir en memoria un espacio mayor que su tamaño no debería devolver
    # ninguna partición, ni tampoco asignarla.
    def test_request_larger_than_memory_fails(self):
        self.set_memory()
        result = self.memory._allocate(MEMORY_SIZE + 1)
        self.assertIsNone(result)
        self.assertEqual(self.memory.partitions, [])

    # Si existe un hueco de tamaño exacto para una partición deberia
    # asignarselo
    def test_exact_fit_in_middle_gap(self):
        self.set_memory()
        # Espacio de 100 exacto entre 300 y 400
        place(self.memory, [(100, 200), (400, 150)])
        new = self.memory._allocate(100)

        self.assertIsNotNone(new)
        self.assertEqual(new.base, 300)
        self.assertIs(self.memory.partitions[1], new)
        assert_invariant(self.memory)

    # Se puede asignar un hueco entre el comienzo de la memoria y la primera
    # partición
    def test_fits_in_leading_gap(self):
        self.set_memory()
        place(self.memory, [(200, 350)])
        new = self.memory._allocate(100)

        self.assertIsNotNone(new)
        self.assertEqual(new.base, 100)
        self.assertIs(self.memory.partitions[0], new)
        assert_invariant(self.memory)

    # Se puede asignar un hueco entre la última partición y el límite de la
    # memoria
    def test_fits_in_trailing_gap(self):
        self.set_memory()
        place(self.memory, [(100, 300)])
        new = self.memory._allocate(150)

        self.assertIsNotNone(new)
        self.assertEqual(new.base, 400)
        self.assertIs(self.memory.partitions[-1], new)
        assert_invariant(self.memory)

    def test_best_fit(self):
        self.set_memory()
        # Huecos 100..200 y 300..330
        # first-fit eligiría el primero y best-fit el segundo
        place(self.memory, [(200, 100), (330, 220)])
        new = self.memory._allocate(30)

        self.assertIsNotNone(new)
        self.assertEqual(new.base, 300)
        self.assertIs(self.memory.partitions[1], new)
        assert_invariant(self.memory)


if __name__ == "__main__":
    unittest.main()
