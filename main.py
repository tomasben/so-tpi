from pathlib import Path

import cli
import loader
from loader import ProcessSpec
from simulador import MAX_LOADED_PROCESSES, USER_SPACE_SIZE, Simulator
from style import GRAY, ORANGE, PADDING, RESET, YELLOW

options = [
    "Cargar desde archivo .csv",
    "Usar archivo de ejemplo",
    "Salir del simulador",
]

# Ruta para poder incluir archivo de prueba en los binarios
test_file_route = Path(__file__).resolve().parent / "prueba" / "procesos.csv"


def print_options() -> None:
    for i, opt in enumerate(options, start=1):
        print(f"{PADDING}[{i}] {opt}")


def get_selection() -> int:
    value_range = f"1..{len(options)}"

    while True:
        option = input(f"\n{PADDING}{YELLOW}Opción 🞂 {RESET}")

        try:
            selection = int(option)
        except ValueError:
            error = "Ingresá un valor numérico"
        else:
            if 1 <= selection <= len(options):
                return selection
            error = f"Ingresá un número válido ({value_range})"

        print(f"{PADDING}{ORANGE}ERROR: {error}{RESET}")


def get_path() -> Path | None:
    while True:
        print(f"\n{PADDING}Ingresá la ruta del archivo .csv")
        print(f"{PADDING}[3] Volver al menú principal")
        print(f"{PADDING}[4] Salir del simulador")

        option = input(
            f"\n{PADDING}{YELLOW}Ruta u Opción 🞂 {RESET}"
        ).strip()

        if option == "3":
            return None

        if option == "4":
            print(f"\n{PADDING}{GRAY}Saliendo del simulador...{RESET}")
            raise SystemExit(0)

        if not option:
            print(f"{PADDING}{ORANGE}ERROR: La ruta no puede estar vacía.{RESET}")
            continue

        route = Path(option)

        if route.is_file():
            return route

        print(f"{PADDING}{ORANGE}ERROR: Ingresá una ruta válida.{RESET}")


def load_specs() -> list[ProcessSpec]:
    while True:
        cli.clear()
        cli.draw_banner()
        print()
        print_options()

        selection = get_selection()

        if selection == 3:
            print(f"\n{PADDING}{GRAY}Saliendo del simulador...{RESET}")
            raise SystemExit(0)

        if selection == 1:
            path = get_path()

            if path is None:
                continue
        else:
            path = test_file_route

        return loader.read_specs_from_file(
            path, amount=MAX_LOADED_PROCESSES
        )


def run_simulation(simulator: Simulator) -> None:
    while True:
        cli.clear()
        cli.draw_state(simulator.get_report())
        if simulator.is_finished:
            return

        choice = cli.await_user_input(
            {
                "": f"{YELLOW}ENTER{RESET}: avanzar una unidad",
                "s": f"{YELLOW}S + ENTER{RESET}: próxima admisión o finalización",
            }
        )
        if choice == "":
            simulator.step()
        else:
            simulator.skip_to_important_step()


def main() -> None:
    specs = load_specs()
    if not loader.validate_specs(specs, size_limit=USER_SPACE_SIZE):
        return

    cli.print_loaded_specs(specs)
    print()
    cli.await_user_input({"": f"Presioná {YELLOW}ENTER{RESET} para continuar"})

    simulator = Simulator(specs)
    run_simulation(simulator)

    cli.await_user_input(
        {"": f"Presioná {YELLOW}ENTER{RESET} para mostrar resumen final"}
    )
    cli.clear()
    cli.draw_summary(simulator.get_report())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{PADDING}{GRAY}Simulación interrumpida")
