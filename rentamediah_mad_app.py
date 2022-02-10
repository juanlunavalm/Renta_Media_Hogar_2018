# CARGA DE LIBRERIAS

import pandas as pd
import geopandas as gpd
import pygeos

import streamlit as st
import numpy as np
import pydeck as pdk

# CARGA DEL FICHEROS
# Fichero con los poligonos censales del INE
ine_polig_censal = pd.read_csv('/Users/juanluis/Documents/RMH/Madrid/ine-censal-polygon-boundaries-2011-Madrid.csv',
                               sep=';')

geometry_ine = gpd.GeoSeries.from_wkt(ine_polig_censal['WKT'], crs='EPSG:4326')
geo_ine = gpd.GeoDataFrame(ine_polig_censal, geometry=geometry_ine, crs='EPSG:4326')

# Fichero con los barrios
df_barrios = pd.read_csv('/Users/juanluis/Documents/RMH/Madrid/Madrid_polygons.csv',
                         sep=';')

geometry_barrios = gpd.GeoSeries.from_wkt(df_barrios['WKT'], crs='EPSG:4326')
geo_barrios = gpd.GeoDataFrame(df_barrios, geometry=geometry_barrios, crs='EPSG:4326')

# Fichero del INE con los datos de la Renta Media del Hogar para la Comunidad de Madrid en 2018

df_rmh_comunidad = pd.read_csv('/Users/juanluis/Documents/RMH/Madrid/31097bsc.csv', thousands='.', sep=';',
                               encoding='latin-1')

# ASIGNACIÓN DEL BARRIO AL POLIGONO CENSAL DEL INE

# Tenemos que tener en cuenta que un polígono ha de pertenecer a un único barrio, pero los límites del polígono censal
# pueden no estár circunscrito al polígono del barrio, por lo que en principio pertenecería a más de un barrio. En estos
# casos el área del polígono estará en más de un 90% incluida en el barrio, y el resto del área no circunscrita se con-
# siderará residual.

# Para asignar el barrio, realizamos:
# 1.- Con el método overlay() de GeoPandas y los dos GeoFDataFrames hallamos el polígono intersección resultante de
# sobreponer cada polígono censal (CUSEC) con el polígono de cada barrio y calcular el área de este polígono.
# 2.- Para cada CUSEC calculamos el área máxima de este polígono intersección y calculamos la diferencia entre el área
# máxima y y el área del polígono intersección con cada barrio.
# 3.- Asignamos el barrio que tenga el área máxima, es decir, el que tenga la diferencia del punto 2 igual a 0

res_interseccion = geo_ine.overlay(geo_barrios, how='intersection')

res_interseccion['area'] = res_interseccion['geometry'].apply(lambda x: x.area)
res_intersec_area_max = res_interseccion.join(res_interseccion.groupby(by=['CUSEC'])['area'].max(),
                                              on='CUSEC',
                                              how='left',
                                              lsuffix='_left',
                                              rsuffix='_right'
                                              )

res_intersec_area_max.rename({'area_left': 'area', 'area_right': 'area_max'}, axis=1, inplace=True)

res_intersec_area_max['flag_barrio'] = res_intersec_area_max.apply(lambda x:
                                                                   1 if round(x['area_max']-x['area'], ndigits=6) == 0
                                                                   else 0,
                                                                   axis=1
                                                                   )

Filtro_barrio = res_intersec_area_max['flag_barrio'] == 1
geo_ine_barrio = res_intersec_area_max[Filtro_barrio]

# PREPARACIóN DEL FICHERO DE RENTA MEDIA DEL HOGAR
# Generamos el campo CUSEC a partir del dato "Unidades territoriales

df_rmh_comunidad['CUSEC'] = df_rmh_comunidad['Unidades territoriales'].str.split(n=1, expand=True).iloc[:, [0]]
df_rmh_comunidad['Literal'] = df_rmh_comunidad['Unidades territoriales'].str.split(n=1, expand=True).iloc[:, [1]]

# Creamos una columna con el código de población para para luego filtrar por el de Madrid capital "28079", y otra para
# la longitud del CUSEC para coger los de longitud 10 que son las filas con la información a nivel de sección censal

df_rmh_comunidad['Poblacion'] = df_rmh_comunidad['CUSEC'].map(lambda x: x[0:5])
df_rmh_comunidad['Long_Seccion'] = df_rmh_comunidad['CUSEC'].map(lambda x: len(x))
df_rmh_comunidad['CUSEC'] = df_rmh_comunidad['CUSEC'].astype('int64')

Filtro_capital = (df_rmh_comunidad['Poblacion'] == '28079') & (df_rmh_comunidad['Long_Seccion'] == 10)
df_rmh_capital = df_rmh_comunidad[Filtro_capital]

# Vamos a pasar a numérica la columna "Total". Para evitar los problemas en la conversión a este tipo de dato en los
# registros en los que "Total" tenga el valor "." usamos un replace() para eliminar los caracteres "." y rellenamos los
# posibles nulos con el valor 0.

df_rmh_capital['Total'] = df_rmh_capital['Total'].str.replace('.', '')
df_rmh_capital['Total'].fillna('0', inplace=True)

df_rmh_capital['Total'] = df_rmh_capital['Total'].astype('int64')

# ENRIQUECER EL FICHERO DE POLIGONOS CENSALES Y BARRIOS CON LA RENTA MEDIA DEL HOGAR EN CADA POLIGONO CENSAL

geo_ine_barrio_rmh = geo_ine_barrio.join(df_rmh_capital.set_index('CUSEC'),
                                         on='CUSEC',
                                         how='left',
                                         lsuffix='_left',
                                         rsuffix='_right'
                                         )

# CREAR EL FICHERO CON LOS DATOS QUE USARA LA APLICACION

cols = ['LOCATIONNAME', 'CUSEC', 'MUNICIPIO', 'Total', 'WKT_1']
df_ine_barrios_rmh = geo_ine_barrio_rmh[cols]

df_ine_barrios_rmh = df_ine_barrios_rmh.fillna(0, axis=1)
df_ine_barrios_rmh['Total'] = df_ine_barrios_rmh['Total'].astype('int64')
df_ine_barrios_rmh.rename({'LOCATIONNAME': 'BARRIO', 'WKT_1': 'WKT'}, axis=1, inplace=True)

print('')
print('df_ine_barrio_rmh-info')
print('----------------------')
df_ine_barrios_rmh.info()

# Transformamos el fichero en un GeoPandasDataFrame

geometry_data = gpd.GeoSeries.from_wkt(df_ine_barrios_rmh['WKT'])
geo_data = gpd.GeoDataFrame(df_ine_barrios_rmh, geometry=geometry_data, crs='EPSG:4326')

# WEB DE LA APLICACION
# Montamos la web donde correrá la app

st.title('**RENTA MEDIA DEL HOGAR 2018**')
st.header('MADRID CAPITAL')

# Construcción de filtros

etiqueta_buscar = {
    0: 'Buscar por barrio',
    1: 'Buscar por importe'}

tipo_consulta = st.sidebar.radio('Seleccionar el tipo de consulta', (0, 1),
                                 format_func=lambda x: etiqueta_buscar.get(x))

if tipo_consulta == 0:
    st.write('Has elegido barrio')
else:
    st.write('Has elegido importe')

min_rmh = geo_data['Total'].min()
max_rmh = geo_data['Total'].max()

st.sidebar.write('Renta media del hogar (en €)')
rmh_desde = st.sidebar.number_input('Desde:', min_rmh, max_rmh, min_rmh)
rmh_hasta = st.sidebar.number_input('Hasta:', min_rmh, max_rmh, max_rmh)

if rmh_desde > rmh_hasta:
    rmh_desde = rmh_hasta
    st.sidebar.write('El importe "Desde" no puede ser mayor al importe "Hasta"')

cols_data = ['MUNICIPIO', 'BARRIO', 'CUSEC', 'Total']
data = geo_data[(geo_data['Total'] >= rmh_desde) & (geo_data['Total'] <= rmh_hasta)][cols_data]

hide_dataframe_row_index = """
                           <style>
                           .row_heading.level0 {display:none}
                           .blank {display:none}
                           </style>
                           """

st.markdown(hide_dataframe_row_index, unsafe_allow_html=True)
st.dataframe(data.style.highlight_max(subset=['Total'], color='yellow', axis=0))
