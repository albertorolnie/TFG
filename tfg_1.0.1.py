# ! Hay que instalar scikit con py -m pip install scikit-learn

import osmnx as ox
import networkx as nx
import folium
import random

# Descarga la red peatonal de la dirección dada y la convierte en grafo
direccion = "Plaza de Lavapiés, Madrid, España"
G = ox.graph_from_address(direccion, dist=4000, network_type="walk")
G = nx.Graph(G)

# Asigna valores aleatorios de seguridad en un array de cinco valores
for u, v, datos in G.edges(data=True):
    datos["seguridad"] = [
        random.randint(1, 5),  # luminosidad
        random.randint(1, 5),  # camaras
        random.randint(1, 5),  # contenedores
        random.randint(1, 5),  # robos
        random.randint(1, 5)   # peatones
    ]

# Usamos la seguridad aleatoria para ponderarla junto al coste distancia de las aristas del grafo
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

# Encuentra el nodo mas cercano
def obtener_nodo(G, entrada):
    """
    Entrada puede ser:
    - str: dirección (geocodificada)
    - tuple: (lat, lon) coordenadas
    """
    if isinstance(entrada, str):
        lat, lon = ox.geocode(entrada)
    else:
        lat, lon = entrada
    return ox.distance.nearest_nodes(G, X=lon, Y=lat)

# Asignamos las coordenadas de nuestro origen y destino (ver si se puede hacer con el nombre de la calle)
origen_input = (40.41023231741949, -3.7047604321897616)
destino_input = (40.40139553653678, -3.6908766039851235)

# Obtenemos los nodos origen y destino de las coordenadas anteriores
origen_nodo = obtener_nodo(G, origen_input)
destino_nodo = obtener_nodo(G, destino_input)

# Calculamos la ruta segura (la mas corta ya habiendo ponderado la seguridad como coste junto a distancia)
ruta = nx.shortest_path(
    G,
    source=origen_nodo,
    target=destino_nodo,
    weight=lambda u, v, datos: calcular_coste(u, v, datos)
)

# 8. Extraer coordenadas de la ruta
coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]

# Creamos un nuevo mapa (Folium)
m = folium.Map(location=coords[0], zoom_start=15, tiles="cartodbpositron")

# Dibujamos el origen y destino de la ruta en el mapa
folium.Marker(coords[0], tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
folium.Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)

# Dibujamos la ruta en el mapa
folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)

# Guardamos un html con el mapa con la ruta resaltada
m.save("ruta_segura.html")
print("Mapa guardado en ruta_segura.html — ábrelo en tu navegador")
