<div align="center">

# Simulador de Planificador de Procesos

<img src="imágenes/ejecución.png" alt="Simulador ejecutándose en la terminal" width="85%">

</div>

<br>

> [!NOTE]  
> Toda la interfaz de la terminal, contenida dentro del archivo cli.py, fue creada con inteligencia artificial.

## Funcionamiento

Para no organizar todo dentro del planificador y que este sea el encargado de manejar a la memoria y toda la lógica, se pensó a `Simulator` como la clase que contiene a ambas y las coordina. Para esto, utiliza las funciones que ambas clases exponen. `Memory` permite que se pueda asignar un nuevo espacio para un proceso o que se libere una partición.

<img src="imágenes/clases_simulador.png" alt="Relación entre clases de Simulator, Memory y Scheduler" width="100%">

`Scheduler` mantiene las colas de procesos nuevos, listos y listo/suspendidos, además del proceso que está en ejecución. Expone operaciones para registrar llegadas (`submit`), admitir procesos (`admit`), suspenderlos (`suspend`), ejecutar el siguiente en la cola de listos (`dispatch`), y también liberar el proceso en ejecución (`release`). Además, tiene una operación para intercambiar al proceso que está ejecutándose y el primero en la cola de listos (`preempt`).

<img src="imágenes/estados.svg" alt="Diagrama de estados de procesos" width="100%">
    
La simulación permite avanzar una sola unidad de tiempo o avanzar hasta el siguiente evento donde haya ocurrido una admisión o finalización de un proceso en ejecución, para lo cuál existen las clases `Event` y `EventTy` que registran esto. En cada paso, `Simulator` libera el proceso en ejecución en caso de que haya agotado su tiempo, registra las nuevas llegadas, intenta cargar en memoria a los procesos suspendidos, intenta asignar a los procesos nuevos, luego delega al planificador la decisión de qué proceso ejecutar, y por último avanza el reloj. 

[Ver el diagrama de flujo del simulador](imágenes/diagrama_flujo.png)

Cada proceso se carga a partir de una especificación de proceso (`ProcessSpec`), que es leida de un archivo .csv, y con la cuál se genera su `PCB` dentro del simulador en el instante que arriban. Cada PCB tiene asociadas las clases `Identity` y `ControlInfo`, las cuáles reflejan los apartados del PCB vistos en la teoria para la identificación e información de control del proceso, respectivamente. Si bien estas clases no son de gran importancia en la implementación del simulador, fue la manera en que decidimos diseñar y distribuir la información relacionada a los procesos, en vez de tenerlo todo dentro de una gran clase 'Proceso'.

Además, los PCB también contienen una referencia a la especificación a partir de la cuál fueron generados, y una clase `Metrics` para guardar información estadística relacionada a la ejecución del proceso. Cada uno de estos PCB son almacenados dentro de la tabla de procesos, un diccionario que relaciona los pid con sus respectivos bloques de control, y que vive dentro del simulador.

<img src="imágenes/clases_procesos.png" alt="Diagrama de clase de PCB y sus componentes" width="100%">

El resto de estadísticas son derivadas a partir de estas clases.

## Acuse de uso de inteligencia artificial (IA)

Se hizo uso de modelos de lenguaje para el diseño preliminar del Simulador, durante la etapa del diagrama de flujo, y posteriormente para facilitar la implementación de la interfaz de la terminal (dentro del archivo cli.py) y algunos tests para asegurar el correcto funcionamiento del simulador. El código correspondiente a la lógica del simulador (simulador.py), la carga de procesos (loader.py) y el flujo de ejecución del programa (main.py) fue escrito en su totalidad por los integrantes del grupo.

## Estructura

```
so-tpi
├── main.py              # Punto de entrada
├── cli.py               # Interfaz en la terminal
├── loader.py            # Carga y validación de los procesos
├── simulador.py         # Lógica del simulador
├── style.py             # Secuencias ANSI comunes a todos los archivos
└── tests/
    └── test_memory.py  
```
