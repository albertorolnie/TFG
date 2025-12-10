# network_loader.py

import osmnx as ox
import networkx as nx
import random
from shapely.geometry import LineString, Point

def cargar_y_preparar_grafo(direccion, dist, network_type):
    """
    Descarga la red peatonal de OSMnx y la devuelve como un MultiDiGraph.
    """
    # Se usa 'g' para representar el objeto grafo
    return ox.graph_from_address(direccion, dist=dist, network_type=network_type)


def insertar_nodo_en_calle(g, punto_latlon):
    """
    Inserta un nuevo nodo en la arista (calle) más cercana a las coordenadas de entrada.
    Esto permite usar un punto de origen/destino que no es un cruce existente en la red.
    Divide la arista original en dos nuevas aristas.
    Devuelve el ID del nuevo nodo insertado.
    """
    lat, lon = punto_latlon
    # Crea un punto Shapely para la proyección (Lon, Lat)
    punto = Point(lon, lat)

    # Encuentra la arista más cercana (u, v, key)
    # Si 'g' es MultiDiGraph, ox.distance.nearest_edges devuelve key.
    u, v, key = ox.distance.nearest_edges(g, X=lon, Y=lat, return_dist=False)

    # Obtener los datos del borde (necesario para manejar MultiDiGraph)
    datos = g[u][v][key]

    # Obtener la geometría de la arista o crearla si no existe
    geom = datos.get("geometry", LineString([
        (g.nodes[u]["x"], g.nodes[u]["y"]),
        (g.nodes[v]["x"], g.nodes[v]["y"])
    ]))

    # Proyectar el punto de entrada sobre la línea de la calle
    punto_proj = geom.interpolate(geom.project(punto))
    lon_proj, lat_proj = punto_proj.x, punto_proj.y

    # Crear un nuevo ID de nodo, asegurándose de que es único
    nuevo_nodo = max(g.nodes) + 1
    g.add_node(nuevo_nodo, x=lon_proj, y=lat_proj)

    # Calcular distancias y datos para las nuevas aristas
    lat_u, lon_u = g.nodes[u]["y"], g.nodes[u]["x"]
    lat_v, lon_v = g.nodes[v]["y"], g.nodes[v]["x"]
    lat_n, lon_n = lat_proj, lon_proj

    # Usar la función de distancia de OSMnx
    distancia_u_n = ox.distance.great_circle(lat1=lat_u, lon1=lon_u, lat2=lat_n, lon2=lon_n)
    distancia_n_v = ox.distance.great_circle(lat1=lat_n, lon1=lon_n, lat2=lat_v, lon2=lon_v)

    # Mantenemos el atributo de seguridad de la arista original
    seguridad_original = datos.get("seguridad")

    # Crear las geometrías de las nuevas aristas
    line1 = LineString([geom.coords[0], (lon_proj, lat_proj)])
    line2 = LineString([(lon_proj, lat_proj), geom.coords[-1]])

    # Eliminar la arista original y añadir las dos nuevas
    g.remove_edge(u, v, key)

    # Usamos key=0 en las nuevas aristas (ya que el MultiDiGraph original las tiene)
    # aunque luego se convertirá a Graph simple.
    g.add_edge(u, nuevo_nodo,
               length=distancia_u_n,
               geometry=line1,
               seguridad=seguridad_original,
               key=0)

    g.add_edge(nuevo_nodo, v,
               length=distancia_n_v,
               geometry=line2,
               seguridad=seguridad_original,
               key=0)

    return nuevo_nodo