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
    lat, lon = punto_latlon
    punto = Point(lon, lat)

    u, v, key = ox.distance.nearest_edges(G, X=lon, Y=lat, return_dist=False)

    datos = G[u][v][key]
    geom = datos.get("geometry", LineString([
        (G.nodes[u]["x"], G.nodes[u]["y"]),
        (G.nodes[v]["x"], G.nodes[v]["y"])
    ]))

    punto_proj = geom.interpolate(geom.project(punto))
    lon_proj, lat_proj = punto_proj.x, punto_proj.y

    nuevo_nodo = max(G.nodes) + 1
    G.add_node(nuevo_nodo, x=lon_proj, y=lat_proj)

    lat_u, lon_u = G.nodes[u]["y"], G.nodes[u]["x"]
    lat_v, lon_v = G.nodes[v]["y"], G.nodes[v]["x"]
    lat_n, lon_n = lat_proj, lon_proj

    distancia_u_n = ox.distance.great_circle(lat1=lat_u, lon1=lon_u, lat2=lat_n, lon2=lon_n)
    distancia_n_v = ox.distance.great_circle(lat1=lat_n, lon1=lon_n, lat2=lat_v, lon2=lon_v)

    seguridad_original = datos.get("seguridad")

    line1 = LineString([geom.coords[0], (lon_proj, lat_proj)])
    line2 = LineString([(lon_proj, lat_proj), geom.coords[-1]])

    G.remove_edge(u, v, key)

    G.add_edge(u, nuevo_nodo,
               length=distancia_u_n,
               geometry=line1,
               seguridad=seguridad_original,
               key=0)

    G.add_edge(nuevo_nodo, v,
               length=distancia_n_v,
               geometry=line2,
               seguridad=seguridad_original,
               key=0)

    return nuevo_nodo


# Definimos las coordenadas para el origen y el destino de nuestra ruta
origen_input = (40.41023231741949, -3.7047604321897616)
destino_input = (40.40139553653678, -3.6908766039851235)

# Insertamos nuevos nodos en nuestro origen y destino
origen_nodo = insertar_nodo_en_calle(G, origen_input)
destino_nodo = insertar_nodo_en_calle(G, destino_input)

# Convertimos a grafo simple (ya no necesitamos keys y simplifica la búsqueda)
G = nx.Graph(G)

# Asignamos valores aleatorios de seguridad a TODAS las calles (aristas), 0 significa desconocido
for u, v, datos in G.edges(data=True):
    if "seguridad" not in datos or datos["seguridad"] is None:
        datos["seguridad"] = [
            random.randint(0, 5),  # luminosidad
            random.randint(0, 5),  # cámaras
            random.randint(0, 5),  # contenedores
            random.randint(0, 5),  # robos
            random.randint(0, 5)   # peatones
        ]


# --- FUNCIÓN DE COSTE V2 (k=100) ---

def calcular_coste(u, v, datos, pesos=(0.20, 0.25, 0.10, 0.35, 0.10), k=100):
    distancia = datos.get("length", 1)
    seguridad = datos.get("seguridad", [3, 3, 3, 3, 3])

    score_seguridad = 0

    for valor, peso in zip(seguridad, pesos):
        if valor == 0:
            continue

        penalizacion_normalizada = (5 - valor) / 4
        penalizacion_cuadratica = penalizacion_normalizada ** 2

        score_seguridad += peso * penalizacion_cuadratica

    return distancia + k * score_seguridad, score_seguridad


# --- FUNCIÓN AUXILIAR PARA EL TOOLTIP ---

def formato_seguridad(valor):
    """Formatea el valor de seguridad a estrellas o '?'"""
    if valor == 0:
        return "<b style='color: gray;'>? (Desc.)</b>"
    else:
        return "⭐" * valor


# --- CÁLCULO DE RUTAS Y COMPARATIVA ---

def coste_total_solo(u, v, datos):
    coste, _ = calcular_coste(u, v, datos)
    return coste

ruta_segura = nx.shortest_path(
    G,
    source=origen_nodo,
    target=destino_nodo,
    weight=coste_total_solo
)

ruta_corta = nx.shortest_path(
    G,
    source=origen_nodo,
    target=destino_nodo,
    weight='length'
)

coords_segura = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta_segura]


# --- VISUALIZACIÓN EN FOLIUM Y CONTROL DE CAPAS ---

m = folium.Map(location=coords_segura[0], zoom_start=15, tiles="cartodbpositron")
folium.Marker(coords_segura[0], tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
folium.Marker(coords_segura[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)

# 1. Crear la capa para la RUTA MÁS CORTA
ruta_corta_group = folium.FeatureGroup(name="Ruta Más Corta (Distancia Pura)").add_to(m)
if ruta_segura != ruta_corta:
    coords_corta = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta_corta]
    folium.PolyLine(
        coords_corta,
        color="orange",
        weight=4,
        opacity=0.6,
        tooltip=folium.Tooltip("Ruta más Corta (por Distancia)", sticky=True)
    ).add_to(ruta_corta_group) # Añadir a la capa de la ruta corta


# 2. Crear la capa para la RUTA MÁS SEGURA
ruta_segura_group = folium.FeatureGroup(name="Ruta Más Segura (Coste Total)").add_to(m)
for i in range(len(ruta_segura) - 1):
    u, v = ruta_segura[i], ruta_segura[i + 1]

    punto1 = (G.nodes[u]["y"], G.nodes[u]["x"])
    punto2 = (G.nodes[v]["y"], G.nodes[v]["x"])
    coords_tramo = [punto1, punto2]

    datos = G.get_edge_data(u, v)
    if datos is None: continue

    coste_total, score_seguridad = calcular_coste(u, v, datos)

    seguridad = datos.get("seguridad", [0, 0, 0, 0, 0])
    distancia = datos.get("length", 0)

    lum_f = formato_seguridad(seguridad[0])
    cam_f = formato_seguridad(seguridad[1])
    cont_f = formato_seguridad(seguridad[2])
    rob_f = formato_seguridad(seguridad[3])
    peat_f = formato_seguridad(seguridad[4])

    tooltip_text = f"""
    <b>--- TRAMO SEGURO ---</b><br>
    <b>Distancia:</b> {distancia:.1f} m<br>
    <b>Score Penalización (k={100}):</b> {score_seguridad:.4f}<br>
    <b>Coste Total (Distancia + Penalización):</b> {coste_total:.1f}<br>
    ---<br>
    <b>Luminosidad:</b> {lum_f}<br>
    <b>Cámaras:</b> {cam_f}<br>
    <b>Contenedores:</b> {cont_f}<br>
    <b>Robos:</b> {rob_f}<br>
    <b>Peatones:</b> {peat_f}
    """

    folium.PolyLine(
        coords_tramo,
        color="blue",
        weight=6,
        opacity=0.8,
        tooltip=folium.Tooltip(tooltip_text, sticky=True)
    ).add_to(ruta_segura_group) # Añadir a la capa de la ruta segura


# 3. Añadir el control de capas al mapa
folium.LayerControl().add_to(m)


# Guardamos el mapa
m.save("ruta_segura.html")
print("Mapa guardado en ruta_segura.html — Abre el archivo para comparar rutas y costes")