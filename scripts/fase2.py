#!/usr/bin/env python3
import os
import sys
import math
import random
from collections import deque

# Configurar TraCI
SUMO_HOME = os.environ.get("SUMO_HOME", "/usr/share/sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))
import traci

# Semilla exigida para reproducibilidad
random.seed(42)

HOSPITALES = {
    "VCM":         {"nombre": "Vicente Corral M.", "lon": -78.992923, "lat": -2.911098, "tipo": "público"},
    "IESS_JCA":    {"nombre": "José Carrasco A.",  "lon": -78.970118, "lat": -2.898698, "tipo": "público"},
    "MILITAR":     {"nombre": "Hospital Militar",  "lon": -79.003968, "lat": -2.903146, "tipo": "público"},
    "MUNI_PAT":    {"nombre": "Muni. Patamarca",   "lon": -78.982263, "lat": -2.866103, "tipo": "público"},
    "MUNI_VALLE":  {"nombre": "Muni. El Valle",    "lon": -78.961959, "lat": -2.919522, "tipo": "público"},
    "MONTE_SINAI": {"nombre": "Monte Sinaí",       "lon": -79.007373, "lat": -2.908606, "tipo": "privado"},
    "DEL_RIO":     {"nombre": "Univ. del Río",     "lon": -78.960796, "lat": -2.892939, "tipo": "privado"}
}

def circulo(cx, cy, radio=120, n=24):
    """ Genera puntos para un polígono circular gigante """
    return [(cx + radio * math.cos(2 * math.pi * i / n), cy + radio * math.sin(2 * math.pi * i / n)) for i in range(n)]

P_SIN = 0.25 
flota = {}

def main():
    print("🚀 Iniciando Fase 2 con Marcadores Gigantes e Interfaz GUI...")
    
    # Iniciar directamente con GUI y pausar al inicio (--start abre directo)
    traci.start(["sumo-gui", "-c", "reto.sumocfg", "--start"]) 
    
    print("\n--- TAREA 2.1 y 2.2: UBICAR HOSPITALES Y FLOTA ---")
    print(f"{'Hospital':<20} | {'Stock':<5} | {'Dist.':<7} | {'Arista Asignada':<20} | {'Calle'}")
    print("-" * 80)
    
    for h_id, datos in HOSPITALES.items():
        arista, pos, carril = traci.simulation.convertRoad(datos["lon"], datos["lat"], isGeo=True, vClass="emergency")
        px, py = traci.simulation.convertGeo(datos["lon"], datos["lat"], fromGeo=True)
        dist = traci.simulation.getDistance2D(px, py, traci.simulation.convert2D(arista, pos)[0], traci.simulation.convert2D(arista, pos)[1])
        
        HOSPITALES[h_id]["edge"] = arista
        HOSPITALES[h_id]["pos"] = pos
        
        # COLOR Y DIBUJO DE CÍRCULOS GIGANTES Y ETIQUETAS
        # Rojo translúcido para públicos, Naranja para privados
        rgba = (255, 0, 0, 160) if datos["tipo"] == "público" else (255, 140, 0, 160)
        try: 
            # 1. Círculo gigante (Polígono de radio 120m)
            traci.polygon.add(f"circ_{h_id}", circulo(px, py, 120), rgba, fill=True, layer=50)
            # 2. Etiqueta con el ID/Nombre sobre el mapa
            traci.poi.add(h_id, px, py, (255, 255, 255, 255), poiType=datos["nombre"], layer=200)
        except Exception as e:
            pass
        
        # Cola FIFO de ambulancias (Stock aleatorio según tipo de hospital)
        st = random.randint(1, 3) if datos["tipo"] == "público" else random.randint(0, 1)
        flota[h_id] = deque([f"amb_{h_id}_{i+1}" for i in range(st)])
        calle = traci.edge.getStreetName(arista)
        
        print(f"{datos['nombre']:<20} | {st:<5} | {dist:>5.1f} m | {arista:<20} | {calle}")

    # Dar un paso de simulación para forzar el dibujado en GUI
    traci.simulationStep()
    
    print("\n" + "📸 " * 15)
    print("👉 ¡LA VISTA ESTÁ LISTA EN SUMO-GUI!")
    print("👉 Toma la captura de pantalla de la red con los círculos de los hospitales ahora.")
    input("👉 Presiona ENTER en esta consola para continuar con el despacho de prueba...")
    print("📸 " * 15 + "\n")

    print("\n--- TAREA 2.3: AMBULANCIA DE PRUEBA EN T=120s ---")
    paso = 0
    t_despacho = 0
    t_estimado = 0
    llegada_confirmada = False

    try:
        while traci.simulation.getMinExpectedNumber() > 0 and paso < 1000:
            traci.simulationStep()
            paso += 1
            
            # Despachar ambulancia de prueba en t=120s
            if paso == 120:
                origen = HOSPITALES["VCM"]["edge"]
                destino = HOSPITALES["IESS_JCA"]["edge"]
                
                ruta = traci.simulation.findRoute(origen, destino, vType="ambulance")
                if ruta.edges:
                    t_estimado = int(ruta.travelTime)
                    traci.route.add("ruta_prueba", ruta.edges)
                    traci.vehicle.add("amb_prueba", "ruta_prueba", typeID="ambulance", departPos=HOSPITALES["VCM"]["pos"])
                    t_despacho = paso
                    print(f"[120 s] DESPACHO VCM -> IESS_JCA | ETA (travelTime ideal): {t_estimado} s")
                else:
                    print("[120 s] Error: No se encontró ruta viable.")
                    
            if "amb_prueba" in traci.simulation.getArrivedIDList():
                t_real = paso - t_despacho
                print(f"[{paso} s] LLEGADA amb_prueba | Tiempo Real: {t_real} s | ETA original: {t_estimado} s")
                llegada_confirmada = True
                break

    except traci.exceptions.FatalTraCIError: pass
    finally:
        traci.close()
        if llegada_confirmada:
            print("✅ Prueba de Fase 2 (Validación A3 y A4) superada exitosamente.\n")

if __name__ == "__main__":
    main()