# map_visualizer.py

import folium
from branca.element import Element
from cost_calculator import calcular_coste, formato_seguridad
from config import K_PENALIZACION


# --- Funciones de Cálculo de Resumen para ser usadas por main.py ---

def calcular_resumen_ruta(g, ruta):
    """
    Calcula la distancia total y el score de seguridad total (ponderado por distancia) de una ruta.

    Devuelve: (distancia_total, score_seguridad_total_ponderado)
    """
    distancia_total = 0
    score_seguridad_total_ponderado = 0

    for i in range(len(ruta) - 1):
        u, v = ruta[i], ruta[i + 1]
        datos = g.get_edge_data(u, v)
        if datos is None: continue

        # Recalcula el coste para obtener los scores y la distancia
        distancia_tramo = datos.get("length", 0)
        # Solo necesitamos el segundo valor (score_seguridad)
        _, score_seguridad_tramo = calcular_coste(u, v, datos)

        distancia_total += distancia_tramo
        # Ponderar el score por la distancia del tramo
        score_seguridad_total_ponderado += score_seguridad_tramo * distancia_tramo

    return distancia_total, score_seguridad_total_ponderado


def crear_popup_resumen(dist_corta, score_por_100m_corta,
                        dist_segura, score_por_100m_segura, k_penalizacion):
    """Genera el HTML con el resumen estadístico de las rutas."""

    if dist_corta > 0:
        porcentaje_mas_larga = ((dist_segura - dist_corta) / dist_corta) * 100
    else:
        porcentaje_mas_larga = 0

    # 4. Generar HTML
    html_resumen = f"""
    <div style='font-family: Arial, sans-serif; max-width: 350px;'>
        <h3 style='color: #2c3e50;'>📊 Comparativa de Rutas</h3>
        <hr style='border: 1px solid #bdc3c7;'>

        <h4>Ruta Más Corta (Naranja)</h4>
        <ul>
            <li>📏 Distancia Total = <b style='color: orange;'>{dist_corta:.1f} m</b></li>
            <li>⚖️ Score Seguridad por 100m = <b style='color: orange;'>{score_por_100m_corta:.3f}</b></li>
        </ul>

        <h4>Ruta Más Segura (Morado)</h4>
        <ul>
            <li>📏 Distancia Total = <b style='color: #6600d3;'>{dist_segura:.1f} m</b></li>
            <li>⚖️ Score Seguridad por 100m = <b style='color: #6600d3;'>{score_por_100m_segura:.3f}</b></li>
        </ul>

        <hr style='border: 1px solid #bdc3c7;'>

        <h4>Comparativa de Distancia</h4>
        <p>
            La Ruta Segura es <b style='color: {'red' if porcentaje_mas_larga > 5 else 'green'};'>
            {porcentaje_mas_larga:.2f}%</b> más larga que la Ruta Corta.
        </p>
        <p style='font-size: 0.8em; color: #7f8c8d;'>
            * Score Seguridad por 100m: Cuanto menor sea el valor, más segura es la ruta.
            (Penalización k={k_penalizacion})
        </p>
    </div>
    """
    return html_resumen


# --- Funciones de Tooltip y Dibujo del Mapa ---

def generar_tooltip_y_datos(g, u, v, tipo_ruta):
    """
    Calcula el coste y la seguridad de un tramo (u, v) y genera el HTML del tooltip.
    """
    datos = g.get_edge_data(u, v)
    if datos is None:
        return None

    coste_total, score_seguridad = calcular_coste(u, v, datos)
    seguridad = datos.get("seguridad", [0, 0, 0, 0, 0])
    distancia = datos.get("length", 0)

    # Formateo de los valores de seguridad
    lum_f = formato_seguridad(seguridad[0])
    cam_f = formato_seguridad(seguridad[1])
    cont_f = formato_seguridad(seguridad[2])
    rob_f = formato_seguridad(seguridad[3])
    peat_f = formato_seguridad(seguridad[4])

    tooltip_text = f"""
    <b>--- TRAMO {tipo_ruta} ---</b><br>
    <b>Distancia:</b> {distancia:.1f} m<br>
    <b>Score Penalización (k={K_PENALIZACION}):</b> {score_seguridad:.4f}<br>
    <b>Coste Total (Distancia + Penalización):</b> {coste_total:.1f}<br>
    ---<br>
    <b>Luminosidad:</b> {lum_f}<br>
    <b>Cámaras:</b> {cam_f}<br>
    <b>Contenedores:</b> {cont_f}<br>
    <b>Robos:</b> {rob_f}<br>
    <b>Peatones:</b> {peat_f}
    """

    return {
        "tooltip_text": tooltip_text,
        "coste_total": coste_total,
        "score_seguridad": score_seguridad,
        "distancia": distancia
    }


def generar_mapa_folium(g, ruta_corta, ruta_segura, origen_nodo, destino_nodo, html_resumen):
    """
    Crea y pobla el mapa Folium con las rutas y el popup de resumen.
    """
    coords_segura = [(g.nodes[n]["y"], g.nodes[n]["x"]) for n in ruta_segura]

    # Inicialización del mapa en la coordenada de origen
    m = folium.Map(location=coords_segura[0], zoom_start=15, tiles="cartodbpositron")

    # Marcadores de Origen y Destino
    # Origen: Punto morado pequeño
    folium.CircleMarker(
        location=coords_segura[0],
        radius=6,
        color="#6600d3",
        fill=True,
        fill_color="#6600d3",
        fill_opacity=1.0,
        tooltip="Origen"
    ).add_to(m)
    
    # Destino: Bandera de meta (tipo Waze)
    folium.Marker(
        location=coords_segura[-1],
        tooltip="Destino",
        icon=folium.Icon(icon="flag-checkered", prefix="fa", color="black", icon_color="white")
    ).add_to(m)

    # 1. Capa para la RUTA MÁS CORTA (AMARILLA/NARANJA)
    ruta_corta_group = folium.FeatureGroup(name="Ruta Más Corta (Distancia Pura)").add_to(m)
    if ruta_segura != ruta_corta:
        for i in range(len(ruta_corta) - 1):
            u, v = ruta_corta[i], ruta_corta[i + 1]

            datos_tramo = generar_tooltip_y_datos(g, u, v, "CORTO (DISTANCIA)")
            if datos_tramo is None: continue

            punto1 = (g.nodes[u]["y"], g.nodes[u]["x"])
            punto2 = (g.nodes[v]["y"], g.nodes[v]["x"])
            coords_tramo = [punto1, punto2]

            folium.PolyLine(
                coords_tramo,
                color="orange",
                weight=4,
                opacity=0.6,
                tooltip=folium.Tooltip(datos_tramo["tooltip_text"], sticky=True)
            ).add_to(ruta_corta_group)

    # 2. Capa para la RUTA MÁS SEGURA (AZUL)
    ruta_segura_group = folium.FeatureGroup(name="Ruta Más Segura (Coste Total)").add_to(m)
    for i in range(len(ruta_segura) - 1):
        u, v = ruta_segura[i], ruta_segura[i + 1]

        datos_tramo = generar_tooltip_y_datos(g, u, v, "SEGURO")
        if datos_tramo is None: continue

        punto1 = (g.nodes[u]["y"], g.nodes[u]["x"])
        punto2 = (g.nodes[v]["y"], g.nodes[v]["x"])
        coords_tramo = [punto1, punto2]

        folium.PolyLine(
            coords_tramo,
            color="#6600d3",
            weight=6,
            opacity=0.8,
            tooltip=folium.Tooltip(datos_tramo["tooltip_text"], sticky=True)
        ).add_to(ruta_segura_group)

    # 3. Botón Flotante de Resumen (Sustituye al marcador)
    
    # CSS y HTML para el botón y el panel
    custom_ui = f"""
    <div id="info-container" style="position: fixed; bottom: 20px; left: 20px; z-index: 9999; font-family: Arial, sans-serif;">
        <!-- Panel de Información (Oculto por defecto) -->
        <div id="info-panel" style="display: none; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.2); margin-bottom: 15px; max-width: 350px; border: 1px solid #ddd;">
            {html_resumen}
        </div>
        
        <!-- Botón de Imagen -->
        <img id="info-btn" src="assets/button_icon.png" 
             style="width: 150px; height: auto; cursor: pointer; transition: transform 0.2s; display: block;" 
             onclick="toggleInfo()"
             onmouseover="this.style.transform='scale(1.1)'"
             onmouseout="this.style.transform='scale(1.0)'"
             title="Ver Resumen de Rutas">
    </div>

    <script>
        function toggleInfo() {{
            var panel = document.getElementById('info-panel');
            if (panel.style.display === 'none' || panel.style.display === '') {{
                panel.style.display = 'block';
            }} else {{
                panel.style.display = 'none';
            }}
        }}
    </script>
    """
    
    m.get_root().html.add_child(Element(custom_ui))

    # 4. Control de Capas
    folium.LayerControl().add_to(m)

    return m