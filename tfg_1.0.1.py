# Incorpora añadir las direcciones origen y destino manualmente en vez de eligiendo nodos por numero
# ! Hay que instalar scikit con py -m pip install scikit-learn

import osmnx as ox
import networkx as nx
import folium
import random

# 1. Descargar la red peatonal de Lavapiés
direccion = "Plaza de Lavapiés, Madrid, España"
G = ox.graph_from_address(direccion, dist=2000, network_type="walk")
G = nx.Graph(G)

# 2. Añadir factores de seguridad simulados
for u, v, datos in G.edges(data=True):
    datos["seguridad"] = [
        random.randint(1, 5),  # luminosidad
        random.randint(1, 5),  # camaras
        random.randint(1, 5),  # contenedores
        random.randint(1, 5),  # robos
        random.randint(1, 5)  # peatones
    ]


# 3. Función de coste personalizada
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


# 4. Definir direcciones de origen y destino
direccion_origen = "Calle de los Abades 3, Madrid, España"
direccion_destino = "Calle del Hospital 14, Madrid, España"

# 5. Geocodificación → coordenadas
origen_point = ox.geocode(direccion_origen)
destino_point = ox.geocode(direccion_destino)

# 6. Encontrar nodos más cercanos en el grafo
origen_nodo = ox.distance.nearest_nodes(G, X=origen_point[1], Y=origen_point[0])
destino_nodo = ox.distance.nearest_nodes(G, X=destino_point[1], Y=destino_point[0])

# 7. Calcular la ruta segura
ruta = nx.shortest_path(
    G,
    source=origen_nodo,
    target=destino_nodo,
    weight=lambda u, v, datos: calcular_coste(u, v, datos)
)

# 8. Extraer coordenadas de la ruta
coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]

# 9. Crear mapa interactivo con Folium
m = folium.Map(location=coords[0], zoom_start=15, tiles="cartodbpositron")

# Marcadores
folium.Marker(coords[0], tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
folium.Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)

# Dibujar ruta
folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)

# Guardar mapa
m.save("ruta_segura.html")
print("Mapa guardado en ruta_segura.html — ábrelo en tu navegador")

#Veo que el origen es el nodo mas cercano, no crea un nodo donde estoy, por ejemplo, si vivo en mitad de una calle,
# me va a poner el origen en el cruce mas cercano en mi calle, pero no justo en mi casa
