# config.py

# Datos para generar el grafo
DIRECCION = "Plaza de Lavapiés, Madrid, España"
DISTANCIA_RADIO_M = 4000
NETWORK_TYPE = "walk"

# Coordenadas de origen y destino para la ruta (Lat, Lon)
ORIGEN_INPUT = (40.41023231741949, -3.7047604321897616)
DESTINO_INPUT = (40.40139553653678, -3.6908766039851235)

# Pesos de importancia de cada item de seguridad
PESOS_SEGURIDAD = (
    0.20,  # Luminosidad
    0.25,  # Cámaras
    0.10,  # Contenedores
    0.35,  # Robos
    0.10   # Peatones
)

# Factor de penalización (k) para el score de seguridad en la fórmula de coste
K_PENALIZACION = 100