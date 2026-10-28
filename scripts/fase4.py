#!/usr/bin/env python3
import os
import sys
import random
import math
from collections import deque
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib import cm

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
else:
    sys.exit("Por favor, declara la variable de entorno 'SUMO_HOME'")
import traci

random.seed(42)

# --- CONFIGURACIÓN DE HOSPITALES ---
HOSPITALES = {
    "VCM":         {"nombre": "Vicente Corral M.", "lon": -78.992923, "lat": -2.911098, "tipo": "público"},
    "IESS_JCA":    {"nombre": "José Carrasco A.",  "lon": -78.970118, "lat": -2.898698, "tipo": "público"},
    "MILITAR":     {"nombre": "Hospital Militar",  "lon": -79.003968, "lat": -2.903146, "tipo": "público"},
    "MUNI_PAT":    {"nombre": "Muni. Patamarca",   "lon": -78.982263, "lat": -2.866103, "tipo": "público"},
    "MUNI_VALLE":  {"nombre": "Muni. El Valle",    "lon": -78.961959, "lat": -2.919522, "tipo": "público"},
    "MONTE_SINAI": {"nombre": "Monte Sinaí",       "lon": -79.007373, "lat": -2.908606, "tipo": "privado"},
    "DEL_RIO":     {"nombre": "Univ. del Río",     "lon": -78.960796, "lat": -2.892939, "tipo": "privado"}
}

def dibujar_circulo(cx, cy, radio, puntos=30):
    return [(cx + radio * math.cos(2 * math.pi * i / puntos), cy + radio * math.sin(2 * math.pi * i / puntos)) for i in range(puntos)]


# --- ESTILO GLOBAL DE GRÁFICAS ---
def estilo_limpio(ax):
    ax.set_facecolor('#FAFBFC')
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color('#B0B7C3')
    ax.tick_params(colors='#37474F', labelsize=10)
    ax.yaxis.grid(True, linestyle='--', linewidth=0.7, color='#D5DAE1', alpha=0.9)
    ax.set_axisbelow(True)


def main():
    print("🚀 Iniciando Simulación Completa (Fase 3 + Fase 4)...")
    
    # Iniciar con GUI para ver los hospitales y tomar las fotos
    traci.start(["sumo-gui", "-c", "reto.sumocfg", "--no-warnings", "true", "--no-step-log", "true", "--start"]) 
    
    # 1. Inicializar Hospitales en la red
    stock_inicial = {}
    flota = {}
    despachos = {h: 0 for h in HOSPITALES}
    retornos = {h: 0 for h in HOSPITALES}
    
    for h_id, datos in HOSPITALES.items():
        arista, pos, _ = traci.simulation.convertRoad(datos["lon"], datos["lat"], isGeo=True, vClass="emergency")
        HOSPITALES[h_id]["edge"] = arista
        st = random.randint(1, 3) if datos["tipo"] == "público" else random.randint(0, 1)
        stock_inicial[h_id] = st
        flota[h_id] = st
        
        # --- DIBUJO DE HOSPITALES (círculo gigante + etiqueta, igual que Fase 2) ---
        # Rojo translúcido para públicos, naranja para privados
        px, py = traci.simulation.convertGeo(datos["lon"], datos["lat"], fromGeo=True)
        rgba = (255, 0, 0, 160) if datos["tipo"] == "público" else (255, 140, 0, 160)
        try:
            traci.polygon.add(f"circ_{h_id}", dibujar_circulo(px, py, 120, 24), rgba, fill=True, layer=50)
            traci.poi.add(h_id, px, py, (255, 255, 255, 255), poiType=datos["nombre"], layer=200)
        except Exception:
            pass
        
    # 2. Agenda de 15 accidentes
    agenda = []
    for hora in range(3):
        agenda.extend([random.randint(hora * 3600 + 300, (hora + 1) * 3600 - 120) for _ in range(5)])
    agenda.sort()
    
    paso = 0
    motos_imprudentes = {} 
    pares_vistos = set()
    tiempos_respuesta = []
    
    # Control de limpieza de vía
    eventos_activos = {} # {id_accidente: {"t_fin": int, "vehs": [], "poly": str}}

    print(f"\n{'PASO (s)':<8} | {'EVENTO':<28} | {'INFO LOGÍSTICA / ESTADO'}")
    print("═" * 75)

    try:
        while traci.simulation.getMinExpectedNumber() > 0 and paso <= 10800:
            traci.simulationStep()
            paso += 1
            
            # --- A. GENERACIÓN DE ACCIDENTE (Fase 3) ---
            if agenda and paso >= agenda[0]:
                buses_aptos = [v for v in traci.vehicle.getIDList() if traci.vehicle.getTypeID(v) == "bus" and traci.vehicle.getSpeed(v) > 4.0 and not traci.vehicle.getRoadID(v).startswith(":")]
                if buses_aptos:
                    agenda.pop(0)
                    bus_target = random.choice(buses_aptos)
                    
                    moto_id = f"m_imp_{paso}"
                    route_bus = traci.vehicle.getRoute(bus_target)
                    idx = traci.vehicle.getRouteIndex(bus_target)
                    
                    if len(route_bus[idx:]) > 0:
                        traci.route.add(f"r_{moto_id}", route_bus[idx:])
                        moto_pos = max(0.0, traci.vehicle.getLanePosition(bus_target) - 45.0)
                        try:
                            traci.vehicle.add(moto_id, f"r_{moto_id}", typeID="moto", departPos=str(moto_pos))
                            traci.vehicle.setSpeedMode(moto_id, 0)
                            traci.vehicle.setSpeed(moto_id, 22.0)
                            motos_imprudentes[moto_id] = (bus_target, paso)
                        except:
                            agenda.insert(0, paso + 10)
                else:
                    agenda[0] += 5
                    
            # Control de tiempo máximo sin choque (90s)
            motos_a_retirar = [m for m, (b, t) in motos_imprudentes.items() if paso - t > 90]
            for m_id in motos_a_retirar:
                if m_id in traci.vehicle.getIDList():
                    traci.vehicle.setSpeedMode(m_id, 31)
                agenda.append(paso + 60)
                agenda.sort()
                del motos_imprudentes[m_id]

            # --- B. DETECCIÓN Y DESPACHO DE AMBULANCIA (Fase 4) ---
            for col in traci.simulation.getCollisions():
                pair = tuple(sorted([col.collider, col.victim]))
                if pair not in pares_vistos and (col.collider in motos_imprudentes or col.victim in motos_imprudentes):
                    pares_vistos.add(pair)
                    num_acc = len(tiempos_respuesta) + 1
                    
                    moto_found = col.collider if col.collider in motos_imprudentes else col.victim
                    if moto_found in motos_imprudentes: del motos_imprudentes[moto_found]
                    
                    # 1. Inmovilizar vehículos
                    for v_id in [col.collider, col.victim]:
                        try:
                            traci.vehicle.setSpeedMode(v_id, 0)
                            traci.vehicle.setSpeed(v_id, 0.0)
                            traci.vehicle.setSpeedMode(v_id, 31)
                        except: pass
                    
                    crash_edge = traci.vehicle.getRoadID(col.collider)
                    
                    # 2. Efectos Visuales (Círculo Amarillo y Cámara)
                    try:
                        cx, cy = traci.vehicle.getPosition(col.collider)
                        poly_id = f"crash_{paso}"
                        traci.polygon.add(poly_id, dibujar_circulo(cx, cy, 30), (255, 200, 0, 180), fill=True, layer=100)
                        
                        # Centrar cámara en el accidente
                        traci.gui.setOffset("View #0", cx, cy)
                        traci.gui.setZoom("View #0", 1500)
                    except:
                        poly_id = None
                        
                    print(f"[{paso:>5}] | 💥 Choque #{num_acc:<2} en {crash_edge[:10]:<10} | Calculando logística...")

                    # 3. Asignación de Hospital y Ruta
                    hospitales_disp = [h for h in HOSPITALES if flota[h] > 0]
                    if hospitales_disp:
                        h_origen = random.choice(hospitales_disp)
                        flota[h_origen] -= 1
                        despachos[h_origen] += 1
                        
                        h_destino = random.choice(list(HOSPITALES.keys()))
                        flota[h_destino] += 1
                        retornos[h_destino] += 1
                        
                        edge_origen = HOSPITALES[h_origen]["edge"]
                        edge_destino = HOSPITALES[h_destino]["edge"]
                        
                        ruta_ida = traci.simulation.findRoute(edge_origen, crash_edge, vType="ambulance")
                        ruta_vuelta = traci.simulation.findRoute(crash_edge, edge_destino, vType="ambulance")
                        
                        t_respuesta = int(ruta_ida.travelTime) if ruta_ida.edges else random.randint(120, 300)
                        tiempos_respuesta.append(t_respuesta)
                        
                        if ruta_ida.edges:
                            amb_id = f"amb_{paso}"
                            route_id = f"r_amb_{paso}"
                            edges_completos = list(ruta_ida.edges) + list(ruta_vuelta.edges)[1:]
                            traci.route.add(route_id, edges_completos)
                            traci.vehicle.add(amb_id, route_id, typeID="ambulance")
                            traci.vehicle.setStop(amb_id, crash_edge, duration=30.0) # Atendiendo 30s
                        
                        t_despeje = paso + t_respuesta + 35
                        eventos_activos[paso] = {"t_fin": t_despeje, "vehs": [col.collider, col.victim], "poly": poly_id}
                        
                        print(f"         | 🚑 Despacho: {HOSPITALES[h_origen]['nombre'][:15]:<15} | T. Resp: {t_respuesta}s -> Traslado a {HOSPITALES[h_destino]['nombre'][:10]}")
                    else:
                        print(f"         | ❌ SIN AMBULANCIAS         | Accidente #{num_acc} no atendido por colapso")

            # --- C. LIMPIEZA DE LA VÍA POST-ATENCIÓN ---
            terminados = []
            for ev_id, data in eventos_activos.items():
                if paso >= data["t_fin"]:
                    terminados.append(ev_id)
                    for v in data["vehs"]:
                        try: traci.vehicle.remove(v)
                        except: pass
                    if data["poly"]:
                        try: traci.polygon.remove(data["poly"])
                        except: pass
            for ev_id in terminados:
                del eventos_activos[ev_id]
                print(f"[{paso:>5}] | ✅ Vía despejada           | Tráfico restablecido")

    except traci.exceptions.FatalTraCIError:
        pass
    finally:
        traci.close()
        print("═" * 75)
        print(f"🏁 Simulación finalizada. Accidentes atendidos: {len(tiempos_respuesta)}")

    # ======================= GENERACIÓN DE GRÁFICAS =======================
    if not os.path.exists("Graficas"): os.makedirs("Graficas")
    
    # 1. Tiempos de Respuesta
    fig, ax = plt.subplots(figsize=(11, 6), facecolor='white')
    estilo_limpio(ax)
    if tiempos_respuesta:
        n = len(tiempos_respuesta)
        norma = Normalize(vmin=min(tiempos_respuesta), vmax=max(tiempos_respuesta))
        colores = cm.plasma(norma(tiempos_respuesta))
        barras = ax.bar(range(1, n + 1), tiempos_respuesta, color=colores,
                        edgecolor='white', linewidth=1.2, width=0.75, zorder=3)
        
        # Valor sobre cada barra
        for b, v in zip(barras, tiempos_respuesta):
            ax.text(b.get_x() + b.get_width() / 2, v + max(tiempos_respuesta) * 0.015, f"{v}",
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='#263238')
        
        mediana = sorted(tiempos_respuesta)[n // 2]
        ax.axhline(y=mediana, color='#00E5FF', linestyle='--', linewidth=2.2, zorder=4,
                   label=f'Mediana: {mediana} s')
        ax.set_xticks(range(1, n + 1))
        ax.set_ylim(0, max(tiempos_respuesta) * 1.15)
        
        sm = cm.ScalarMappable(cmap='plasma', norm=norma)
        cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.04)
        cbar.set_label('Tiempo (s)', fontsize=10, color='#37474F')
        cbar.outline.set_visible(False)
        ax.legend(loc='upper right', frameon=True, facecolor='white', edgecolor='#D5DAE1', fontsize=10)
    ax.set_title('Tiempo de Respuesta de Ambulancias', fontsize=16, fontweight='bold', color='#0D1B2A', pad=15)
    ax.set_xlabel('Número de Incidente', fontsize=11, color='#37474F', labelpad=8)
    ax.set_ylabel('Tiempo de respuesta (s)', fontsize=11, color='#37474F', labelpad=8)
    fig.tight_layout()
    fig.savefig('Graficas/tiempos_respuesta.png', dpi=300, facecolor='white')
    plt.close(fig)

    # 2. Uso Hospitalario
    h_keys = list(HOSPITALES.keys())
    x = list(range(len(h_keys)))
    ancho = 0.26
    series = [
        ('Stock Inicial', [stock_inicial[h] for h in h_keys], '#00B4D8', -ancho),
        ('Despachos',     [despachos[h] for h in h_keys],     '#FF3D71', 0),
        ('Llegadas',      [retornos[h] for h in h_keys],      '#00C853', ancho),
    ]
    fig, ax = plt.subplots(figsize=(13, 6.5), facecolor='white')
    estilo_limpio(ax)
    max_val = 1
    for etiqueta, datos, color, desplaz in series:
        barras = ax.bar([i + desplaz for i in x], datos, width=ancho, label=etiqueta,
                        color=color, edgecolor='white', linewidth=1.2, zorder=3)
        max_val = max(max_val, max(datos) if datos else 1)
        for b, v in zip(barras, datos):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.05, f"{v}", ha='center', va='bottom',
                    fontsize=9, fontweight='bold', color='#263238')
    ax.set_ylim(0, max_val * 1.2 + 0.5)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.set_xticks(x)
    ax.set_xticklabels([HOSPITALES[h]['nombre'] for h in h_keys], rotation=15, ha='right')
    ax.set_title('Logística Hospitalaria de Ambulancias', fontsize=16, fontweight='bold', color='#0D1B2A', pad=15)
    ax.set_ylabel('Número de ambulancias', fontsize=11, color='#37474F', labelpad=8)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=3, frameon=False, fontsize=11)
    fig.tight_layout()
    fig.savefig('Graficas/logistica_hospitales.png', dpi=300, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    
    print("📊 Gráficas guardadas en la carpeta 'Graficas/'.")

if __name__ == "__main__":
    main()