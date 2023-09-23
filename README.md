# homeassistant-meteogalicia_tides
[![HACS Supported](https://img.shields.io/badge/HACS-Supported-green.svg)](https://github.com/custom-components/hacs)
![GitHub Activity](https://img.shields.io/github/commit-activity/m/danieldiazi/homeassistant-meteogalicia_tides?label=commits)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Danieldiazi_homeassistant-meteogalicia_tides&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Danieldiazi_homeassistant-meteogalicia_tides)

# homeassistant-meteogalicia_tides
MeteoGalicia Tides - Home Assistant Integration 

Esta integración para [Home Assistant](https://www.home-assistant.io/) te permite obtener información de mareas de aquellos puertos de Galicia que sean de tu interés. La información se obtiene de los servicios webs proporcionados por [MeteoGalicia](https://www.meteogalicia.gal/), organismo oficial que tiene entre otros objetivos la predicción meteorológica de Galicia.


## Características

Proporciona los siguientes sensores:

- Para un puerto dado
  - Pronósticos:
    - Indica cuando será la siguiente marea. (Con información adicional en los atributos del sensor)
      
    

## Requisitos

Para instalar esta integración en Home Assistant necesitarás:

* una instalación de Home Assistant (ver <https://www.home-assistant.io/>)
* tener HACS en tu entorno de Home Assistant (ver <https://hacs.xyz/>)


## Instalación
Una vez cumplidos los objetivos anteriores, los pasos a seguir para la instalación de esta integración son los siguientes:

1. Añadir este repositorio (https://github.com/Danieldiazi/homeassistant-meteogalicia_tides) a los repositorios personalizados de HACS,

2. Instalar la integración mediante HACS. [Más info](docs/HACS_add_integration.md)

3. Reiniciar Home Assistant.

4. Configurarla mediante el fichero de configuración `configuration.yaml` (u otro que uses):

 Si quieres añadir la información para un ayuntamiento dado:
``` yaml
sensor:
  platform: meteogalicia_tides
  id_port: 3
  scan_interval: 1200

```

Puedes poner más de un sensor, por ejemplo:

``` yaml
sensor:
  - platform: meteogalicia_tides
    id_port: 3
    scan_interval: 1200
  - platform: meteogalicia_tides
    id_port: 2
    scan_interval: 1800
```

- El parámetro "id_port" es el indicador del puerto y podrás elegir un valor de entre los disponibles por meteogalicia: https://www.meteogalicia.gal/datosred/infoweb/meteo/docs/rss/RSS_Mareas_gl.pdf
- Con el parámetro opcional "scan_interval" indicas cada cuanto tiempo se conecta a meteogalicia para obtener la información. El valor es en segundos, por tanto, si pones 1200  hará el chequeo cada 20 minutos. Es recomendable usarlo.

  
5. Reiniciar para que recarge la configuración y espera unos minutos a que aparezcan las nuevas entidades, con id: sensor.meteogalicia_tides_XXXX.


## FAQ

###### ClientConnectorError
Aparece el mensaje "[custom_components.meteogalicia_tides.sensor] [ClientConnectorError] Cannot connect to host servizos.meteogalicia.gal:443 ssl:default [Try again]* -> Lo más probable es que en ese momento no tuvieses acceso a internet desde tu Home Assistant.¡

###### TimeoutError
Si aparece el mensaje *Couldn't update sensor (TimeoutError)* o *Still no update available (TimeoutError)* en este caso es un problema con el servicio web de meteogalicia, en ese momento puntual no habrá podido servir la petición.

###### Possible API connection problem. Currently unable to download data from MeteoGalicia. Maybe next time...
En este caso es que ha tratado de conectarse al servicio web de meteogalicia y ha devuelto contenido vacio. 
