# Practica4_SUMO_Ambulancias

# Simulación Logística de Ambulancias en Cuenca (SUMO y TraCI)

Este repositorio contiene el entorno de simulación microscópica desarrollado para evaluar la logística de respuesta prehospitalaria en la red vial de Cuenca, Ecuador, utilizando Eclipse SUMO y la interfaz de control TraCI.

## Estructura del Proyecto

El repositorio está organizado en los siguientes directorios para facilitar su revisión y ejecución:

* **scripts/**: Contiene los scripts de Python (fase2.py, fase3.py, fase4.py) que gestionan el bucle de simulación a través de TraCI. Incluye la lógica de inyección de tráfico, generación de siniestros y el algoritmo de enrutamiento dinámico de la flota de ambulancias.
* **red_sumo/**: Almacena los archivos de infraestructura del simulador. Incluye el archivo de configuración principal (reto.sumocfg), la topología de la red (cuenca_ciudad.net.xml), los archivos de rutas para el tráfico civil (autos, buses, motos) y las definiciones macroscópicas.
* **Graficas/**: Reúne las visualizaciones generadas tras la ejecución de las pruebas, incluyendo el análisis estadístico de los tiempos de respuesta y el balance logístico por centro hospitalario.
* **salida/**: Contiene los reportes nativos en formato XML generados por SUMO al finalizar la corrida de simulación (estadísticas globales, información de viajes completos y registro detallado de colisiones).

## Notas de Ejecución

Debido a la organización del proyecto en subdirectorios, para ejecutar la simulación desde la carpeta `scripts/`, las rutas en el código Python apuntan al directorio de configuración de la siguiente manera:
`sumoCmd = [sumoBinary, "-c", "../red_sumo/reto.sumocfg"]`
