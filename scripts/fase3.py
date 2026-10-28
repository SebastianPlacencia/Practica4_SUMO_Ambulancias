#!/usr/bin/env python3
import os
import sys
import random

# Configurar TraCI
if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
else:
    sys.exit("Por favor, declara la variable de entorno 'SUMO_HOME'")
import traci

random.seed(42)

def main():
    print("🚀 Iniciando Fase 3: Siniestralidad Bus-Moto (Normativa Docente)...")
    
    traci.start([
        "sumo", 
        "-c", "reto.sumocfg",
        "--no-warnings", "true",
        "--no-step-log", "true"
    ]) 
    
    # 1. Agenda de 15 instantes (5 por hora)
    agenda_accidentes = []
    for hora in range(3):
        instantes = [random.randint(hora * 3600 + 300, (hora + 1) * 3600 - 120) for _ in range(5)]
        agenda_accidentes.extend(instantes)
    agenda_accidentes.sort()
    
    paso = 0
    motos_imprudentes = {}  # {moto_id: (bus_id, t_inicio)}
    colisiones_registradas = 0
    pares_vistos = set()

    print(f"{'PASO (s)':<10} | {'MOTO ATACANTE':<15} | {'BUS VÍCTIMA':<15} | {'ESTADO'}")
    print("═" * 70)

    try:
        while traci.simulation.getMinExpectedNumber() > 0 and paso <= 10800:
            traci.simulationStep()
            paso += 1
            
            # 2. Provocar colisión según la agenda (Tarea 3.2 del Taller)
            if agenda_accidentes and paso >= agenda_accidentes[0]:
                # Buscar un bus apto en marcha
                buses_aptos = []
                for v in traci.vehicle.getIDList():
                    if traci.vehicle.getTypeID(v) == "bus":
                        road = traci.vehicle.getRoadID(v)
                        speed = traci.vehicle.getSpeed(v)
                        pos_lane = traci.vehicle.getLanePosition(v)
                        # No estar en cruce (:), v > 4 m/s y avance > 60m
                        if not road.startswith(":") and speed >= 4.0 and pos_lane > 60.0:
                            buses_aptos.append(v)
                
                if buses_aptos:
                    agenda_accidentes.pop(0)
                    bus_target = random.choice(buses_aptos)
                    
                    # Verificar si ya tiene una moto detrás
                    follower = traci.vehicle.getFollower(bus_target, 80.0)
                    moto_target = None
                    
                    if follower and follower[0] != "" and traci.vehicle.getTypeID(follower[0]) == "moto":
                        moto_target = follower[0]
                    else:
                        # Si no hay moto, insertar una 45m detrás con la misma ruta del bus
                        moto_id = f"moto_imp_{paso}"
                        route_bus = traci.vehicle.getRoute(bus_target)
                        route_idx = traci.vehicle.getRouteIndex(bus_target)
                        sub_route = route_bus[route_idx:]
                        
                        if len(sub_route) > 0:
                            route_id = f"route_{moto_id}"
                            traci.route.add(route_id, sub_route)
                            bus_pos = traci.vehicle.getLanePosition(bus_target)
                            moto_pos = max(0.0, bus_pos - 45.0)
                            
                            try:
                                traci.vehicle.add(moto_id, route_id, typeID="moto", departPos=str(moto_pos))
                                moto_target = moto_id
                            except:
                                pass
                    
                    if moto_target and moto_target in traci.vehicle.getIDList():
                        # Modificar submodelo longitudinal (C04)
                        traci.vehicle.setSpeedMode(moto_target, 0)
                        traci.vehicle.setLaneChangeMode(moto_target, 0)
                        traci.vehicle.setSpeed(moto_target, 22.0)
                        motos_imprudentes[moto_target] = (bus_target, paso)
                        print(f"[{paso:>5} s]  | {moto_target:<15} | {bus_target:<15} | ⚡ IMPRUDENTE (Krauss OFF)")
                    else:
                        # Si falló la inserción, posponer 10s
                        agenda_accidentes.insert(0, paso + 10)
                else:
                    agenda_accidentes[0] += 5

            # Control de tiempo: Si la moto lleva > 90s sin chocar, devolverle el control y reprogramar
            motos_a_retirar = []
            for m_id, (b_id, t_ini) in motos_imprudentes.items():
                if paso - t_ini > 90:
                    motos_a_retirar.append(m_id)
                    if m_id in traci.vehicle.getIDList():
                        traci.vehicle.setSpeedMode(m_id, 31)
                        traci.vehicle.setSpeed(m_id, -1)
                        traci.vehicle.setLaneChangeMode(m_id, 1621)
                    # Reprogramar accidente en 60 segundos
                    agenda_accidentes.append(paso + 60)
                    agenda_accidentes.sort()
            for m_id in motos_a_retirar:
                del motos_imprudentes[m_id]

            # 3. Detección e Inmovilización en dos pasos (Tarea 3.3 y 3.4 del Taller)
            for col in traci.simulation.getCollisions():
                pair = tuple(sorted([col.collider, col.victim]))
                if pair not in pares_vistos:
                    # Comprobar si al menos uno es de los registrados
                    if col.collider in motos_imprudentes or col.victim in motos_imprudentes:
                        pares_vistos.add(pair)
                        colisiones_registradas += 1
                        
                        moto_found = col.collider if col.collider in motos_imprudentes else col.victim
                        if moto_found in motos_imprudentes:
                            del motos_imprudentes[moto_found]
                        
                        # Inmovilizar en dos pasos según la guía (Evita Emergency Stop warnings)
                        for v_id in [col.collider, col.victim]:
                            try:
                                traci.vehicle.setSpeedMode(v_id, 0)
                                traci.vehicle.setSpeed(v_id, 0.0)
                                traci.vehicle.setSpeedMode(v_id, 31)
                            except:
                                pass
                        
                        print(f"[{paso:>5} s]  | {col.collider:<15} | {col.victim:<15} | 💥 ACCIDENTE CONFIRMADO ({colisiones_registradas}/15)")

    except traci.exceptions.FatalTraCIError:
        pass
    finally:
        traci.close()
        print("═" * 70)
        print(f"✅ Fase 3 Finalizada. Total de accidentes confirmados: {colisiones_registradas}\n")

if __name__ == "__main__":
    main()