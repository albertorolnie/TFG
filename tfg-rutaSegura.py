import osmnx as ox
import networkx as nx
import folium
import random
from shapely.geometry import LineString, Point


# Descarga red peatonal (walk) de un barrio/ciudad de radio dist en metros y la convierte en un multiDiGraph
direccion = "Plaza de Lavapiés, Madrid, España"
G = ox.graph_from_address(direccion, dist=4000, network_type="walk")


def insertar_nodo_en_calle(G, punto_latlon):
    """
    Inserta un nuevo nodo en la arista (calle) más cercano a las coordenadas de entrada.
    Esto permite usar un punto de origen/destino que no es un cruce existente en la red.
    Divide la arista original en dos nuevas aristas.

    Recibe 2 argumentos, el grafo de la red callejera (un multiDiGraph) y un punto (tuple) que contiene
    las coordenadas (latitud, longitud) del punto a insertar. Devuelve el ID del nuevo nodo insertado.
    """


    # 1. PREPARACIÓN E IDENTIFICACIÓN DE LA CALLE MÁS CERCANA

    lat, lon = punto_latlon
    # Crea un objeto Shapely Point (Longitud, Latitud) para el punto de entrada.
    punto = Point(lon, lat)

    # Encuentra la arista (calle) más cercana al punto.
    # Devuelve los IDs de los nodos que la forman (u, v) y su clave (key).
    u, v, key = ox.distance.nearest_edges(G, X=lon, Y=lat, return_dist=False)


    # 2. PROYECCIÓN DEL PUNTO SOBRE LA CALLE

    # Obtiene los datos de la arista (u, v, key).
    datos = G[u][v][key]

    # Recupera la geometría de la calle (LineString). Si no está presente (calle recta),
    # crea una LineString simple usando las coordenadas de los nodos u y v.
    geom = datos.get("geometry", LineString([
        (G.nodes[u]["x"], G.nodes[u]["y"]),
        (G.nodes[v]["x"], G.nodes[v]["y"])
    ]))

    # Calcula el punto sobre 'geom' que está más cerca de 'punto'.
    # geom.project(punto) -> calcula la distancia a lo largo de la línea.
    # geom.interpolate(...) -> devuelve el punto en esa distancia proyectada.
    punto_proj = geom.interpolate(geom.project(punto))
    lon_proj, lat_proj = punto_proj.x, punto_proj.y


    # 3. INSERCIÓN DEL NUEVO NODO

    # Asigna un ID único al nuevo nodo, usando el máximo ID de nodo + 1.
    nuevo_nodo = max(G.nodes) + 1
    # Añade el nuevo nodo al grafo con sus coordenadas proyectadas.
    G.add_node(nuevo_nodo, x=lon_proj, y=lat_proj)


    # 4. CÁLCULO DE LAS NUEVAS LONGITUDES

    # Obtiene las coordenadas de los nodos existentes y el nuevo nodo para el cálculo de distancia.
    lat_u, lon_u = G.nodes[u]["y"], G.nodes[u]["x"]
    lat_v, lon_v = G.nodes[v]["y"], G.nodes[v]["x"]
    lat_n, lon_n = lat_proj, lon_proj

    # Calcula la distancia geodésica (círculo máximo) en metros del nuevo tramo u -> n.
    distancia_u_n = ox.distance.great_circle(lat1=lat_u, lon1=lon_u, lat2=lat_n, lon2=lon_n)
    # Calcula la distancia geodésica (círculo máximo) en metros del nuevo tramo n -> v.
    distancia_n_v = ox.distance.great_circle(lat1=lat_n, lon1=lon_n, lat2=lat_v, lon2=lon_v)

    # Recupera el atributo de seguridad original de la calle que se va a dividir.
    seguridad_original = datos.get("seguridad")


    # 5. DIVISIÓN DE LA ARISTA ORIGINAL

    # Crea la geometría LineString para el tramo u -> n.
    line1 = LineString([geom.coords[0], (lon_proj, lat_proj)])
    # Crea la geometría LineString para el tramo n -> v.
    line2 = LineString([(lon_proj, lat_proj), geom.coords[-1]])

    # Elimina la arista original (u, v, key) que ha sido reemplazada.
    G.remove_edge(u, v, key)

    # Añade la primera nueva arista: del nodo 'u' al nuevo nodo.
    G.add_edge(u, nuevo_nodo,
               length=distancia_u_n,  # Asigna la nueva longitud calculada
               geometry=line1,  # Asigna la nueva geometría
               seguridad=seguridad_original,  # Mantiene el atributo de seguridad original
               key=0)  # Asigna una clave (necesario si G era MultiDiGraph)

    # Añade la segunda nueva arista: del nuevo nodo al nodo 'v'.
    G.add_edge(nuevo_nodo, v,
               length=distancia_n_v,  # Asigna la nueva longitud calculada
               geometry=line2,  # Asigna la nueva geometría
               seguridad=seguridad_original,  # Mantiene el atributo de seguridad original
               key=0)

    # Devuelve el ID del nodo recién insertado, que será usado como origen o destino de la ruta.
    return nuevo_nodo


# Definimos las coordenadas para el origen y el destino de nuestra ruta
origen_input = (40.41023231741949, -3.7047604321897616)
destino_input = (40.40139553653678, -3.6908766039851235)

# Insertamos nuevos nodos en nuestro origen y destino
origen_nodo = insertar_nodo_en_calle(G, origen_input)
destino_nodo = insertar_nodo_en_calle(G, destino_input)

# Convertimos a grafo simple (ya no necesitamos keys y simplifica la búsqueda)
G = nx.Graph(G)

# Asignamos valores aleatorios de seguridad a TODAS las calles (aristas). 0 significa desconocido
for u, v, datos in G.edges(data=True):
    if "seguridad" not in datos or datos["seguridad"] is None:
        datos["seguridad"] = [
            random.randint(0, 5),  # luminosidad
            random.randint(0, 5),  # cámaras
            random.randint(0, 5),  # contenedores
            random.randint(0, 5),  # robos
            random.randint(0, 5)   # peatones
        ]


# --- FUNCIÓN DE COSTE V3 (k=100) ---

def calcular_coste(u, v, datos, pesos=(0.20, 0.25, 0.10, 0.35, 0.10), k=100):
    distancia = datos.get("length", 1)
    # Lista de 5 valores de seguridad (por si hubo algún error a la hora de asignar seguridad a las aristas)
    seguridad = datos.get("seguridad", [3, 3, 3, 3, 3])

    score_penalizacion_no_normalizado = 0
    suma_pesos_conocidos = 0  # Variable para rastrear la suma de pesos de los items conocidos

    # Itera sobre los valores de seguridad y sus pesos asociados
    for valor, peso in zip(seguridad, pesos):

        # Ignora los valores desconocidos (valor == 0)
        if valor == 0:
            continue

        # Suma el peso del ítem si su valor es CONOCIDO (valor > 0)
        suma_pesos_conocidos += peso

        # Cálculo de la Penalización (0=Malo, 1=Bueno)
        # Se normaliza la escala (1 a 5) a una escala de penalización (0 a 1)
        # (5 - valor) -> Invierte la escala: 5-seguro -> 0-penalización; 1-inseguro -> 4-penalización
        penalizacion_normalizada = (5 - valor) / 4

        # Penalización Cuadrática: Acentúa la penalización de los valores más inseguros (cercanos a 1)
        penalizacion_cuadratica = penalizacion_normalizada ** 2

        # Acumula la penalización pesada
        score_penalizacion_no_normalizado += peso * penalizacion_cuadratica

    # 1. NORMALIZACIÓN DEL SCORE DE PENALIZACIÓN

    # Si todos los valores eran desconocidos, la penalización se deja en 0 (asumiendo neutralidad o el valor por defecto)
    if suma_pesos_conocidos > 0:
        # Divide el score acumulado por la suma de los pesos de los ítems que contribuyeron.
        # Esto normaliza el score para que siempre esté entre 0.0 y 1.0.
        score_seguridad_normalizado = score_penalizacion_no_normalizado / suma_pesos_conocidos
    else:
        # En caso de no conocer ningún dato, no hay penalización por seguridad.
        score_seguridad_normalizado = 0.0

    # 2. CÁLCULO DEL COSTE TOTAL

    # El coste es la distancia (coste base) más la penalización de seguridad escalada por 'k'.
    # Cuanto mayor sea score_seguridad_normalizado (cercano a 1.0), mayor es el coste.
    return distancia + k * score_seguridad_normalizado, score_seguridad_normalizado


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
m.save("ruta_segura2.html")
print("Mapa guardado en ruta_segura2.html — Abre el archivo para comparar rutas y costes")