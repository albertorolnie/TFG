# route_finder.py

import networkx as nx
from cost_calculator import coste_total_solo


def encontrar_rutas(g, origen_nodo, destino_nodo):
    """
    Calcula la ruta más corta (distancia pura) y la ruta más segura (coste total).

    Argumentos:
        G (nx.Graph): El grafo de la red.
        origen_nodo (int): ID del nodo de origen.
        destino_nodo (int): ID del nodo de destino.

    Devuelve:
        tuple: (ruta_corta, ruta_segura), donde cada ruta es una lista de IDs de nodos.
    """

    # 1. Ruta más corta (peso = distancia)
    ruta_corta = nx.shortest_path(
        g,
        source=origen_nodo,
        target=destino_nodo,
        weight='length'
    )

    # 2. Ruta más segura (peso = coste total)
    # Usa la función de coste definida en cost_calculator.py
    ruta_segura = nx.shortest_path(
        g,
        source=origen_nodo,
        target=destino_nodo,
        weight=coste_total_solo
    )

    return ruta_corta, ruta_segura