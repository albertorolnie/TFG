import osmnx as ox
import networkx as nx
import folium
import random
from shapely.geometry import LineString, Point

# Descarga red peatonal (walk) de un barrio/ciudad de radio dist en metros y la convierte en un multiDiGraph
direccion = "Plaza de Lavapiés, Madrid, España"
# G es un MultiDiGraph
G = ox.graph_from_address(direccion, dist=4000, network_type="walk")


# Inserta un nuevo nodo en unas coordenadas concretas y calcula la longitud en metros
def insertar_nodo_en_calle(G, punto_latlon):
    # Crea un punto en las coordenadas que recibe
    lat, lon = punto_latlon
    punto = Point(lon, lat)

    # Buscar la arista más cercana al punto (u, v, key)
    u, v, key = ox.distance.nearest_edges(G, X=lon, Y=lat, return_dist=False)

    # Obtiene la geometría y los datos de la arista original
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


    # Coordenadas de los nodos u y v (extremos de la arista original)
    lat_u, lon_u = G.nodes[u]["y"], G.nodes[u]["x"]
    lat_v, lon_v = G.nodes[v]["y"], G.nodes[v]["x"]
    # Coordenadas del nuevo nodo (proyectado)
    lat_n, lon_n = lat_proj, lon_proj

    distancia_u_n = ox.distance.great_circle(lat1=lat_u, lon1=lon_u, lat2=lat_n, lon2=lon_n)
    distancia_n_v = ox.distance.great_circle(lat1=lat_n, lon1=lon_n, lat2=lat_v, lon2=lon_v)

    # La seguridad será asignada en el bloque principal, pero la transferimos
    seguridad_original = datos.get("seguridad")

    # Partir y Añadir aristas
    line1 = LineString([geom.coords[0], (lon_proj, lat_proj)])
    line2 = LineString([(lon_proj, lat_proj), geom.coords[-1]])

    # Elimina la arista original
    G.remove_edge(u, v, key)

    # Añade la primera nueva arista con la longitud y seguridad corregidas
    G.add_edge(u, nuevo_nodo,
               length=distancia_u_n,
               geometry=line1,
               seguridad=seguridad_original,  # Mantenemos el atributo, si existe
               key=0)  # Asignar una key para que OSMnx lo maneje bien

    # Añade la segunda nueva arista con la longitud y seguridad corregidas
    G.add_edge(nuevo_nodo, v,
               length=distancia_n_v,
               geometry=line2,
               seguridad=seguridad_original,  # Mantenemos el atributo, si existe
               key=0)

    return nuevo_nodo


# Definimos las coordenadas para el origen y el destino de nuestra ruta
origen_input = (40.41023231741949, -3.7047604321897616)
destino_input = (40.40139553653678, -3.6908766039851235)

# Insertamos nuevos nodos en nuestro origen y destino
origen_nodo = insertar_nodo_en_calle(G, origen_input)
destino_nodo = insertar_nodo_en_calle(G, destino_input)

# Convertimos a grafo simple (ya no necesitamos keys y simplifica la búsqueda)
# Esto debe hacerse DESPUÉS de insertar los nodos
G = nx.Graph(G)

# Asignamos valores aleatorios de seguridad a TODAS las calles (aristas), 0 significa desconocido
# Esto garantiza que las aristas nuevas y las originales tengan el atributo "seguridad".
for u, v, datos in G.edges(data=True):
    # Solo asignamos seguridad si aún no existe (es decir, a las aristas que no fueron cortadas)
    if "seguridad" not in datos or datos["seguridad"] is None:
        datos["seguridad"] = [
            random.randint(0, 5),  # luminosidad
            random.randint(0, 5),  # cámaras
            random.randint(0, 5),  # contenedores
            random.randint(0, 5),  # robos
            random.randint(0, 5)   # peatones
        ]


# --- FUNCIÓN DE COSTE V2 ---

def calcular_coste(u, v, datos, pesos=(0.20, 0.25, 0.10, 0.35, 0.10), k=100):
    """
    Calcula el coste total de una arista (distancia + penalización de seguridad)
    utilizando penalización no proporcional (cuadrática).
    """
    distancia = datos.get("length", 1)
    seguridad = datos.get("seguridad", [3, 3, 3, 3, 3])

    score_seguridad = 0

    for valor, peso in zip(seguridad, pesos):
        if valor == 0:
            # Ignorar si el valor es desconocido (0)
            continue

        # Penalización No Proporcional (Cuadrática)
        # Penalización normalizada (0 a 1, peor caso en 1) = (5 - valor) / 4
        penalizacion_normalizada = (5 - valor) / 4

        # Aplicamos la función cuadrática: Penalización ** 2
        penalizacion_cuadratica = penalizacion_normalizada ** 2

        # Sumamos al score, multiplicando por el peso del atributo
        score_seguridad += peso * penalizacion_cuadratica

    # Coste Total = Distancia + k * Score de Seguridad
    return distancia + k * score_seguridad



# --- CÁLCULO DE RUTA Y VISUALIZACIÓN ---

# Calculamos la ruta de menor coste (distancia + seguridad) usando la función corregida
ruta = nx.shortest_path(
    G,
    source=origen_nodo,
    target=destino_nodo,
    weight=lambda u, v, datos: calcular_coste(u, v, datos)
)

# Extraemos las coordenadas de la ruta para graficar en Folium
coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]

# Creamos un mapa con Folium
m = folium.Map(location=coords[0], zoom_start=15, tiles="cartodbpositron")
folium.Marker(coords[0], tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
folium.Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)

# Dibujamos la ruta tramo a tramo con tooltip
for i in range(len(ruta) - 1):
    u, v = ruta[i], ruta[i + 1]

    # Recuperamos coordenadas de los nodos
    punto1 = (G.nodes[u]["y"], G.nodes[u]["x"])
    punto2 = (G.nodes[v]["y"], G.nodes[v]["x"])
    coords_tramo = [punto1, punto2]


    # En un grafo simple (nx.Graph), get_edge_data(u, v) devuelve el diccionario de atributos
    # o None si no hay arista. También puedes usar datos = G[u][v]
    datos = G.get_edge_data(u, v)

    # Manejar el caso de que la arista no exista (aunque no debería ocurrir en una ruta válida)
    if datos is None:
        continue


    # Recuperamos datos de seguridad y distancia
    seguridad = datos.get("seguridad", [0, 0, 0, 0, 0])
    distancia = datos.get("length", 0)

    # Creamos texto del tooltip
    tooltip_text = f"""
    <b>Distancia:</b> {distancia:.1f} m<br>
    <b>Luminosidad:</b> {seguridad[0]}<br>
    <b>Cámaras:</b> {seguridad[1]}<br>
    <b>Contenedores:</b> {seguridad[2]}<br>
    <b>Robos:</b> {seguridad[3]}<br>
    <b>Peatones:</b> {seguridad[4]}
    """

    # Añadimos PolyLine con tooltip
    folium.PolyLine(
        coords_tramo,
        color="blue",
        weight=5,
        opacity=0.8,
        tooltip=folium.Tooltip(tooltip_text, sticky=True)
    ).add_to(m)

# Guardamos el mapa
m.save("ruta_segura.html")
print("Mapa guardado en ruta_segura.html — Ábrelo en tu navegador")