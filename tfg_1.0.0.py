import osmnx as ox
import networkx as nx
import folium
import random

# 1. Descargar la red peatonal alrededor de la Plaza de Lavapiés
direccion = "Plaza de Lavapiés, Madrid, España"
G = ox.graph_from_address(direccion, dist=800, network_type="walk")

# 2. Convertimos el grafo a no dirigido (por compatibilidad con networkx)
G = nx.Graph(G)

# 3. Añadimos factores de seguridad simulados a cada arista
for u, v, datos in G.edges(data=True):
    datos["seguridad"] = [
        random.randint(1, 5),  # luminosidad
        random.randint(1, 5),  # camaras
        random.randint(1, 5),  # contenedores
        random.randint(1, 5),  # robos
        random.randint(1, 5)  # peatones
    ]


# 4. Función de coste personalizada
def calcular_coste(u, v, datos, pesos=(1, 2, 1, 3, 2), k=100):
    distancia = datos.get("length", 1)
    lum, cam, cont, rob, peat = datos["seguridad"]
    a, b, c, d, e = pesos

    score = (
            a * (1 - lum / 5) +
            b * (1 - cam / 5) +
            c * (cont / 5) +
            d * (rob / 5) +
            e * (1 - peat / 5)
    )
    return distancia + k * score


# 5. Escogemos nodos de origen y destino
nodos = list(G.nodes())
nodo_origen = nodos[0]
nodo_destino = nodos[100]  # cambiar si da error porque hay pocos nodos

# 6. Calculamos la ruta segura
ruta = nx.shortest_path(
    G,
    source=nodo_origen,
    target=nodo_destino,
    weight=lambda u, v, datos: calcular_coste(u, v, datos)
)

# 7. Extraemos coordenadas de la ruta
coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]

# 8. Creamos un mapa interactivo con Folium
m = folium.Map(location=coords[0], zoom_start=16, tiles="cartodbpositron")

# Marcamos origen y destino
folium.Marker(coords[0], tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
folium.Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)

# Dibujamos la ruta
folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)

# Guardamos el mapa
m.save("ruta_segura.html")
print("Ruta guardada correctamente")
