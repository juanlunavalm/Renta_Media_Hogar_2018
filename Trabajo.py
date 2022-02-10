# CARGA DE LIBRERIAS

import pandas as pd
import geopandas as gpd
import pygeos
# import streamlit as st
# import numpy as np
# import pydeck as pdk

# CARGA DEL FICHEROS

"""
Fichero del INE con los datos de la Renta Media de lo Hogares de la Comunidad de Madrid en 2018
"""

df_rmh_comunidad = pd.read_csv('/Users/juanluis/Documents/RMH/Madrid/31097bsc.csv', thousands='.', sep=';',
                               encoding='latin-1')

"""
Fichero de polígonos censales del INE
"""
ine_polig_censal = pd.read_csv('/Users/juanluis/Documents/RMH/Madrid/ine-censal-polygon-boundaries-2011-Madrid.csv',
                               sep=';')
"""
print('FICHERO ine_polig_censal')
ine_polig_censal.info()
"""
geometry_ine = gpd.GeoSeries.from_wkt(ine_polig_censal['WKT'], crs='EPSG:4326')
geo_ine_madrid = gpd.GeoDataFrame(ine_polig_censal, geometry=geometry_ine, crs='EPSG:4326')

geo_ine_madrid.info()
print(geo_ine_madrid.columns)
print(geo_ine_madrid['WKT'][0])
print(geo_ine_madrid['CUSEC'][0])

"""
Fichero de barrios
"""
df_barrios = pd.read_csv('/Users/juanluis/Documents/RMH/Madrid/Madrid_polygons.csv', sep=';')
geometry_barrios = gpd.GeoSeries.from_wkt(df_barrios['WKT'], crs='EPSG:4326')
geo_barrios = gpd.GeoDataFrame(df_barrios, geometry=geometry_barrios, crs='EPSG:4326')

print('FICHERO geo_barrios')
geo_barrios.info()
print(df_barrios.head())

# PREPARACION DEL FICHERO DE RENTA MEDIA DEL HOGAR

df_rmh_comunidad_2 = df_rmh_comunidad.copy()

"""
El campo Total está definido como string, antes de pasarlo a float (que nos da un problema al mostrar el dataframe con
streamlit al poner un 0 tras su última posición) eliminamos el punto '.' con un replace
"""
df_rmh_comunidad_2['Total'] = df_rmh_comunidad_2['Total'].str.replace('.', '')


""" Rellenanmos los nulos en Total con 0 """
df_rmh_comunidad_2['Total'].fillna(0, inplace=True)


df_rmh_comunidad_2['CUSEC'] = df_rmh_comunidad_2['Unidades territoriales'].str.split(n=1, expand=True).iloc[:, [0]]
df_rmh_comunidad_2['Literal'] = df_rmh_comunidad_2['Unidades territoriales'].str.split(n=1, expand=True).iloc[:, [1]]

"""
Creamos una columna con el código de población para para luego filtrar por el de Madrid capital "28079", y otra para
la longitud del CUSEC para coger los de longitud 10 que son las filas con la información a nivel de sección censal
"""

df_rmh_comunidad_2['Poblacion'] = df_rmh_comunidad_2['CUSEC'].map(lambda x: x[0:5])
df_rmh_comunidad_2['Long_Seccion'] = df_rmh_comunidad_2['CUSEC'].map(lambda x: len(x))
print(df_rmh_comunidad_2.iloc[0:10, 6:8])

filtro_capital = (df_rmh_comunidad_2['Poblacion'] == '28079') & (df_rmh_comunidad_2['Long_Seccion'] == 10)
df_rmh_cap = df_rmh_comunidad_2[filtro_capital]
print(df_rmh_cap.iloc[0:10, 6:8])

df_rmh_cap['Total'] = df_rmh_cap['Total'].astype('int64')

# TRATAMIENTO FICHERO DE BARRIOS
""" Construimos el campo CUSEC, para cruzarlo con el fichero del INE, a partir del campo LOCATIONID"""

df_barrios = pd.concat([df_barrios, df_barrios.LOCATIONID.str.split('-', expand=True)], axis=1)

df_barrios['CUSEC'] = df_barrios[3] + df_barrios[6] + df_barrios[7] + df_barrios[8]
df_barrios['CUSEC'] = df_barrios['CUSEC'].astype('int64')

df_barrios.drop([0, 1, 2, 3, 4, 5, 6, 7, 8], axis=1, inplace=True)


print('FICHERO df_barrios con CUSEC')
df_barrios.info()

# ENRIQUECIMIENTO DEL FICHERO DEL INE
""" Añadimos el nombre del barrio al que pertenece el polígono censal del INE"""

"""
ine_polig_censal = ine_polig_censal.join(df_barrios[['CUSEC','LOCATIONNAME']].set_index('CUSEC'), on='CUSEC',
                                         lsuffix='_p', rsuffix='_b')
print('FICHERO ine_polig_censal con nombre barrio')
ine_polig_censal.info()
"""

""" Enriquecemos con el nombre del barrio"""
geo_ine_madrid = gpd.sjoin(geo_ine_madrid,
                           geo_barrios[['geometry', 'LOCATIONNAME']],
                           how='right',
                           predicate='intersects')
geo_ine_madrid.info()
