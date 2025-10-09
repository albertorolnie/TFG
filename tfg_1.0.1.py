# ! Hay que instalar scikit con py -m pip install scikit-learn

import osmnx as ox
import networkx as nx
import folium
import random
from shapely.geometry import LineString, Point


# Descarga red peatonal (walk) de un barrio/ciudad de radio dist en metros y la convierte en un multiDiGraph
direccion = "Plaza de Lavapiés, Madrid, España"
G = ox.graph_from_address(direccion, dist=4000, network_type="walk")


# Inserta un nuevo nodo en unas coordenadas concretas
def insertar_nodo_en_calle(G, punto_latlon):

    # Crea un punto en las coordenadas que recibe
    lat, lon = punto_latlon
    punto = Point(lon, lat)

    # Buscar la arista más cercana al punto
    u, v, key = ox.distance.nearest_edges(G, X=lon, Y=lat, return_dist=False)

    # Obtiene la geometría de la arista
    datos = G[u][v][key]
    geom = datos.get("geometry", LineString([
        (G.nodes[u]["x"], G.nodes[u]["y"]),
        (G.nodes[v]["x"], G.nodes[v]["y"])
    ]))

    # Calcula el punto proyectado sobre la línea
    punto_proj = geom.interpolate(geom.project(punto))
    lon_proj, lat_proj = punto_proj.x, punto_proj.y

    # Crea un nuevo nodo
    nuevo_nodo = max(G.nodes) + 1
    G.add_node(nuevo_nodo, x=lon_proj, y=lat_proj)

    # Parte la arista en dos
    line1 = LineString([geom.coords[0], (lon_proj, lat_proj)])
    line2 = LineString([(lon_proj, lat_proj), geom.coords[-1]])

    # Elimina la arista original
    G.remove_edge(u, v, key)

    # Añade las nuevas aristas sin seguridad (se añadirán después)
    G.add_edge(u, nuevo_nodo, length=line1.length, geometry=line1)
    G.add_edge(nuevo_nodo, v, length=line2.length, geometry=line2)

    return nuevo_nodo


# Definimos las coordenadas para el origen y el destino de nuestra ruta (mas adelante recibira Strings de direcciones)
origen_input = (40.41023231741949, -3.7047604321897616)
destino_input = (40.40139553653678, -3.6908766039851235)

# Insertamos nuevos nodos en nuestro origen y destino
origen_nodo = insertar_nodo_en_calle(G, origen_input)
destino_nodo = insertar_nodo_en_calle(G, destino_input)


# Convertimos a grafo simple (ya no necesitamos keys y simplifica la busqueda)
G = nx.Graph(G)


# Asignamos valores aleatorios de seguridad a nuestras calles (aristas)
for u, v, datos in G.edges(data=True):
    datos["seguridad"] = [
        random.randint(1, 5),  # luminosidad
        random.randint(1, 5),  # camaras
        random.randint(1, 5),  # contenedores
        random.randint(1, 5),  # robos
        random.randint(1, 5)   # peatones
    ]


# Calculamos el coste total por calle (distancia + seguridad)
def calcular_coste(u, v, datos, pesos=(1, 2, 1, 3, 2), k=100):
    distancia = datos.get("length", 1)
    seguridad = datos.get("seguridad", [3, 3, 3, 3, 3])

    lum, cam, cont, rob, peat = seguridad
    a, b, c, d, e = pesos

    score = (
        a * (1 - lum / 5) +
        b * (1 - cam / 5) +
        c * (cont / 5) +
        d * (rob / 5) +
        e * (1 - peat / 5)
    )
    return distancia + k * score


# Calculamos la ruta de menor coste (distancia + seguridad)
ruta = nx.shortest_path(
    G,
    source=origen_nodo,
    target=destino_nodo,
    weight=lambda u, v, datos: calcular_coste(u, v, datos)
)


# Extraemos las coordenadas de la ruta para graficar en Folium
coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]


# Creamos un mapa con Folium y añadimos los puntos de origen y destino y la ruta segura
m = folium.Map(location=coords[0], zoom_start=15, tiles="cartodbpositron")
folium.Marker(coords[0], tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
folium.Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)
folium.PolyLine(coords, color="blue", weight=5, opacity=0.8).add_to(m)


# Guardamos el mapa como html
m.save("ruta_segura.html")
print("Mapa guardado en ruta_segura.html — Ábrelo en tu navegador")
