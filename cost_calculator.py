# cost_calculator.py

from config import PESOS_SEGURIDAD, K_PENALIZACION


def calcular_coste(u, v, datos, pesos=PESOS_SEGURIDAD, k=K_PENALIZACION):
    """
    Calcula el coste total (distancia + penalización de seguridad) de una arista.
    Devuelve (coste_total, score_seguridad_normalizado).
    """
    # Usamos 1 como valor por defecto si la distancia no existe (evita división por cero)
    distancia = datos.get("length", 1)
    # Valores por defecto de seguridad (3=neutro) si no existe o es None
    seguridad = datos.get("seguridad", [3, 3, 3, 3, 3])

    score_penalizacion_no_normalizado = 0
    suma_pesos_conocidos = 0

    for valor, peso in zip(seguridad, pesos):
        if valor == 0:
            # Si el valor es 0, significa "desconocido" y se ignora su peso
            continue

        suma_pesos_conocidos += peso

        # Normalización: (5 - valor) / 4. Rango [0, 1].
        # valor=5 (muy seguro) -> penalización=0
        # valor=1 (muy inseguro) -> penalización=1
        penalizacion_normalizada = (5 - valor) / 4

        # Penalización cuadrática enfatiza los tramos más inseguros
        penalizacion_cuadratica = penalizacion_normalizada ** 2

        score_penalizacion_no_normalizado += peso * penalizacion_cuadratica

    if suma_pesos_conocidos > 0:
        # Se normaliza dividiendo entre la suma de pesos que sí eran conocidos
        score_seguridad_normalizado = score_penalizacion_no_normalizado / suma_pesos_conocidos
    else:
        # Si todos los datos son 0 (desconocido), la penalización es 0
        score_seguridad_normalizado = 0.0

    # Coste Total = Distancia + k * Score_Seguridad
    coste_total = distancia + k * score_seguridad_normalizado
    return coste_total, score_seguridad_normalizado


def coste_total_solo(u, v, datos):
    """
    Función envoltorio para ser usada como `weight` en nx.shortest_path para la ruta segura.
    Solo devuelve el coste total.
    """
    coste, _ = calcular_coste(u, v, datos)
    return coste


def formato_seguridad(valor):
    """Formatea el valor de seguridad (0-5) a estrellas o '?'."""
    if valor == 0:
        return "<b style='color: gray;'>? (Desc.)</b>"
    else:
        return "⭐" * valor