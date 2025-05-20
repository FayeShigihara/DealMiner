import os
import requests
import plotly.express as px
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import streamlit as st
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
import io
import base64
from dominate import document
from dominate.tags import *

def generate_pdf(data, query):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Resultados de búsqueda: {query}", styles['Title']))
    elements.append(Spacer(1, 12))

    for item in data:
        elements.append(Paragraph(f"Título: {item['Título']}", styles['Heading4']))
        elements.append(Paragraph(f"Precio: ${item['Precio']:.2f}", styles['Normal']))
        elements.append(Paragraph(f"Tienda: {item['Tienda']}", styles['Normal']))
        elements.append(Paragraph(f"Fecha: {item['Fecha']}", styles['Normal']))
        elements.append(Paragraph(f"URL Producto: {item['URL Producto']}", styles['Normal']))

        if item.get("URL Imagen"):
            try:
                response = requests.get(item["URL Imagen"], stream=True, timeout=5)
                if response.status_code == 200:
                    image_bytes = io.BytesIO(response.content)
                    img = RLImage(image_bytes, width=100, height=100)
                    elements.append(img)
            except Exception as e:
                elements.append(Paragraph(f"[No se pudo cargar la imagen: {e}]", styles['Normal']))

        elements.append(Spacer(1, 20))

    doc.build(elements)
    buffer.seek(0)
    return buffer
def generate_html(data, query):
    doc = document(title=f"Reporte {query}")

    with doc.head:
        style("""
            body {
                font-family: Arial, sans-serif;
                margin: 2rem;
                background-color: #f5f5f5;
                color: #333;
            }
            h1 {
                text-align: center;
                margin-bottom: 2rem;
            }
            .product {
                background-color: #fff;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                padding: 0.8rem;
                margin: 1rem auto;
                display: flex;
                flex-direction: column;
                align-items: center;
                max-width: 500px;
            }
            .product img {
                max-width: 140px;
                height: auto;
                border-radius: 5px;
                margin-bottom: 0.8rem;
            }
            .price {
                color: green;
                font-weight: bold;
                margin: 0.3rem 0;
            }
            .store, .date {
                font-size: 0.85rem;
                color: #666;
            }
            a {
                display: inline-block;
                margin-top: 0.5rem;
                text-decoration: none;
                color: #fff;
                background-color: #007BFF;
                padding: 0.3rem 0.8rem;
                border-radius: 5px;
                font-size: 0.85rem;
                transition: background-color 0.3s ease;
            }
            a:hover {
                background-color: #0056b3;
            }
            @media (min-width: 768px) {
                .product {
                    flex-direction: row;
                    gap: 1rem;
                    max-width: 600px;
                }
                .product img {
                    max-width: 120px;
                }
                .product-details {
                    flex: 1;
                }
            }
        """)

    with doc:
        h1(f"Resultados para: {query}")
        for item in data:
            with div(cls="product"):
                if item.get("URL Imagen"):
                    try:
                        response = requests.get(item["URL Imagen"], timeout=5)
                        if response.status_code == 200:
                            b64_img = base64.b64encode(response.content).decode()
                            img(src=f"data:image/jpeg;base64,{b64_img}")
                    except Exception as e:
                        p(f"[Error cargando imagen: {str(e)}]")

                with div(cls="product-details"):
                    h2(item['Título'])
                    p(f"Tienda: {item['Tienda']}", cls="store")
                    p(f"Fecha: {item['Fecha']}", cls="date")
                    p(f"Precio: ${item['Precio']:.2f} {'USD' if item['Tienda'] == 'Amazon' else 'MXN'}", cls="price")
                    a("Ver producto", href=item['URL Producto'], target="_blank")

    return doc.render()


def save_to_excel(data, query):
    df = pd.DataFrame(data)
    file_name = f"{query.replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
    df.to_excel(file_name, index=False)
    return file_name


st.set_page_config(
    page_title="DealMiner",
    page_icon="🛒"
)

def get_product_info_amazon(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, features='lxml')

    try:
        title = soup.find(id='productTitle').get_text(strip=True)
    except AttributeError:
        title = 'No title found'

    try:
        image_url = soup.find(id='landingImage')['src']
    except (AttributeError, TypeError):
        image_url = None

    try:
        price_text = soup.find('span', {'class': 'a-offscreen'}).get_text(strip=True)
        price = float(price_text.replace('$', '').replace(',', ''))
    except:
        price = None

    return title, image_url, price

def get_search_results_amazon(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept-Language': 'en-US,en;q=0.9'
    }

    url = f"https://www.amazon.com/s?k={query.replace(' ', '+')}"
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, features='lxml')

    product_links = []
    for link in soup.find_all('a', {'class': 'a-link-normal s-no-outline'}, href=True):
        product_links.append("https://www.amazon.com" + link['href'])
    return product_links

def obtener_titulo_desde_pagina(url, headers):
    try:
        respuesta = requests.get(url, headers=headers)
        sopa = BeautifulSoup(respuesta.text, "html.parser")
        titulo_tag = sopa.find("h1", class_="ui-pdp-title")
        return titulo_tag.text.strip() if titulo_tag else "Sin título"
    except:
        return "Sin título"

def buscar_en_mercado_libre(producto: str, limite=10):
    query = producto.replace(" ", "+")
    url = f"https://listado.mercadolibre.com.mx/{query}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    respuesta = requests.get(url, headers=headers)
    sopa = BeautifulSoup(respuesta.text, "html.parser")

    items = sopa.find_all("li", class_="ui-search-layout__item")
    resultados = []

    for item in items[:limite]:
        try:
            enlace_tag = item.find("a", href=True)
            enlace = enlace_tag["href"] if enlace_tag else None
            if not enlace:
                continue

            titulo = obtener_titulo_desde_pagina(enlace, headers)

            precio_entero = item.find("span", class_="andes-money-amount__fraction")
            precio_decimal = item.find("span", class_="andes-money-amount__cents")
            if not precio_entero:
                continue

            precio = precio_entero.text.replace(",", "")
            precio_completo = f"{precio}.{precio_decimal.text if precio_decimal else '00'}"

            imagen_tag = item.find("img")
            imagen = None
            if imagen_tag:
                imagen = (
                    imagen_tag.get("data-src") or
                    imagen_tag.get("data-srcset") or
                    imagen_tag.get("src")
                )

            resultados.append({
                "Fecha": datetime.now().strftime('%Y-%m-%d'),
                "Título": titulo,
                "Precio": float(precio_completo),
                "URL Imagen": imagen,
                "URL Producto": enlace,
                "Tienda": "Mercado Libre"
            })
        except:
            continue

    return resultados

st.title("🛒 Comparador de precios: Amazon + Mercado Libre")

search_query = st.text_input("Introduce tu búsqueda:")
tiendas = st.multiselect("Selecciona las tiendas que quieres comparar:", ["Amazon", "Mercado Libre"], default=["Amazon", "Mercado Libre"])

if search_query and tiendas:
    st.write(f"### Resultados para: '{search_query}'")
    resultados = []

    with st.spinner("🔎 Buscando productos..."):
        if "Amazon" in tiendas:
            urls_amazon = get_search_results_amazon(search_query)
            for url in urls_amazon[:10]:
                titulo, imagen, precio = get_product_info_amazon(url)
                if titulo != 'No title found' and precio is not None:
                    resultados.append({
                        "Fecha": datetime.now().strftime('%Y-%m-%d'),
                        "Título": titulo,
                        "Precio": precio,
                        "URL Imagen": imagen,
                        "URL Producto": url,
                        "Tienda": "Amazon"
                    })

        if "Mercado Libre" in tiendas:
            resultados.extend(buscar_en_mercado_libre(search_query, limite=10))

    if resultados:
        resultados_ordenados = sorted(resultados, key=lambda x: x["Precio"])
        for item in resultados_ordenados:
            try:
                st.markdown("___")
                cols = st.columns([1, 3])
                with cols[0]:
                    if item["URL Imagen"]:
                        st.image(item["URL Imagen"], use_container_width=True)
                with cols[1]:
                    st.markdown(f"**[{item['Título']}]({item['URL Producto']})**")
                    moneda = "USD" if item["Tienda"] == "Amazon" else "MXN"
                    st.markdown(f"💲 **Precio:** {moneda} ${item['Precio']:.2f}")
                    st.markdown(f"🏬 **Tienda:** {item['Tienda']}")
                    st.markdown(f"📅 **Fecha:** {item['Fecha']}")
            except Exception as e:
                st.error(f"Error al mostrar un resultado: {e}")
        
                # Histograma de precios por tienda
        st.markdown("---")
        st.subheader("Distribución de Precios")

        # Crear DataFrame desde resultados ordenados
        df = pd.DataFrame(resultados_ordenados)

        # Crear histograma con Plotly
        fig = px.histogram(
            df,
            x="Precio",
            nbins=20,
            color="Tienda",
            marginal="rug",
            title="Distribución de Precios por Tienda",
            labels={"Precio": "Precio (USD/MXN)"},
            hover_data=df.columns
        )

        # Personalización del diseño del gráfico
        fig.update_layout(
            bargap=0.1,
            xaxis_title="Precio",
            yaxis_title="Cantidad de Productos",
            hovermode="x unified"
        )

        # Mostrar el gráfico en Streamlit
        st.plotly_chart(fig, use_container_width=True)


        file_name = save_to_excel(resultados_ordenados, search_query)
        with open(file_name, "rb") as f:
            st.download_button(
                label="📅 Descargar Excel con todos los productos",
                data=f,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        pdf_buffer = generate_pdf(resultados_ordenados, search_query)
        st.download_button(
            label="📄 Descargar PDF con los resultados",
            data=pdf_buffer,
            file_name=f"{search_query.replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d')}.pdf",
            mime="application/pdf"
        )

        # Generar y descargar HTML
        html_report = generate_html(resultados_ordenados, search_query)
        st.download_button(
            label="🌐 Descargar HTML offline",
            data=html_report,
            file_name=f"{search_query.replace(' ', '_')}_reporte.html",
            mime="text/html"
        )
    else:
        st.warning("No se encontraron resultados para tu búsqueda.")
elif search_query and not tiendas:
    st.info("Por favor selecciona al menos una tienda.")
