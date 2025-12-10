# tfg_main.py

import networkx as nx
import random  # Necesario para la asignación de seguridad

from config import (
    DIRECCION, DISTANCIA_RADIO_M, NETWORK_TYPE,
    ORIGEN_INPUT, DESTINO_INPUT, K_PENALIZACION
)

from network_loader import cargar_y_preparar_grafo, insertar_nodo_en_calle
from route_finder import encontrar_rutas
from map_visualizer import (
    generar_mapa_folium,
    calcular_resumen_ruta,
    crear_popup_resumen
)


def run_application():
    """Ejecuta el flujo completo de la aplicación."""

    # --- 1. Carga y Preparación del Grafo ---
    print("1. Cargando y preparando el grafo...")
    # El grafo G se descarga como MultiDiGraph (dirigido y múltiples aristas)
    G_multi = cargar_y_preparar_grafo(DIRECCION, DISTANCIA_RADIO_M, NETWORK_TYPE)

    # Insertar nodos de origen y destino en las aristas más cercanas
    origen_nodo = insertar_nodo_en_calle(G_multi, ORIGEN_INPUT)
    destino_nodo = insertar_nodo_en_calle(G_multi, DESTINO_INPUT)

    # Convertir a grafo simple (ya no necesitamos MultiGraph para nx.shortest_path con peso)
    G = nx.Graph(G_multi)

    # Asignar valores aleatorios de seguridad a TODAS las calles (aristas).
    for u, v, datos in G.edges(data=True):
        if "seguridad" not in datos or datos["seguridad"] is None:
            # Asigna [luminosidad, cámaras, contenedores, robos, peatones]
            datos["seguridad"] = [random.randint(0, 5) for _ in range(5)]

    print(f"   -> Grafo listo con {G.number_of_nodes()} nodos y {G.number_of_edges()} aristas.")

    # --- 2. Cálculo de Rutas ---
    print("2. Calculando rutas (Corta y Segura)...")
    ruta_corta, ruta_segura = encontrar_rutas(G, origen_nodo, destino_nodo)
    print("   -> Rutas calculadas.")

    # --- 3. Generación de Resumen y Métricas ---
    print("3. Generando resumen estadístico...")

    # Calcular métricas de la ruta corta
    dist_corta, score_pond_corta = calcular_resumen_ruta(G, ruta_corta)
    score_por_100m_corta = (score_pond_corta / dist_corta) * 100 if dist_corta > 0 else 0

    # Calcular métricas de la ruta segura
    dist_segura, score_pond_segura = calcular_resumen_ruta(G, ruta_segura)
    score_por_100m_segura = (score_pond_segura / dist_segura) * 100 if dist_segura > 0 else 0

    # Generar el HTML del popup de resumen
    html_resumen = crear_popup_resumen(
        dist_corta, score_por_100m_corta,
        dist_segura, score_por_100m_segura,
        K_PENALIZACION
    )
    print("   -> Resumen generado.")

    # --- 4. Visualización en Folium ---
    print("4. Generando mapa interactivo...")
    m = generar_mapa_folium(
        G, ruta_corta, ruta_segura,
        origen_nodo, destino_nodo,
        html_resumen
    )
    print("   -> Mapa generado.")

    # --- 5. Guardar Resultado ---
    nombre_archivo = "ruta_segura.html"
    m.save(nombre_archivo)
    print(
        f"\n✅ Mapa guardado en {nombre_archivo} — Abre el archivo y haz clic en el marcador morado para ver el resumen")


if __name__ == "__main__":
    run_application()