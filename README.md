# homeassistant-meteogalicia_tides
[![HACS Supported](https://img.shields.io/badge/HACS-Supported-green.svg)](https://github.com/custom-components/hacs)
![GitHub Activity](https://img.shields.io/github/commit-activity/m/danieldiazi/homeassistant-meteogalicia_tides?label=commits)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=Danieldiazi_homeassistant-meteogalicia_tides&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=Danieldiazi_homeassistant-meteogalicia_tides)

MeteoGalicia Tides - Home Assistant Integration 

Esta integración para [Home Assistant](https://www.home-assistant.io/) te permite obtener información de mareas de aquellos puertos de Galicia que sean de tu interés. La información se obtiene de los servicios webs proporcionados por [MeteoGalicia](https://www.meteogalicia.gal/), organismo oficial que tiene entre otros objetivos la predicción meteorológica de Galicia.


## Características

Por cada puerto crea estas entidades:

| Entidad | Contenido | Activación inicial |
| --- | --- | --- |
| Forecast Tides | Estado histórico con la próxima pleamar o bajamar y sus atributos | Activada |
| Próxima marea | Fecha y hora de la próxima marea | Desactivada |
| Tipo de la próxima marea | Pleamar o bajamar en formato estructurado | Desactivada |
| Altura de la próxima marea | Altura prevista en metros | Desactivada |
| Próxima pleamar | Fecha y hora de la siguiente pleamar disponible | Desactivada |
| Próxima bajamar | Fecha y hora de la siguiente bajamar disponible | Desactivada |
| Marea siguiente | Fecha y hora de la marea posterior a la próxima | Desactivada |
| Número de mareas de hoy | Cantidad de mareas incluidas en la previsión de hoy | Desactivada |

La entidad histórica conserva su nombre, estado e identificador único para no romper automatizaciones existentes.

## Requisitos

Para instalar esta integración en Home Assistant necesitarás:

* una instalación de Home Assistant (ver <https://www.home-assistant.io/>)
* tener HACS en tu entorno de Home Assistant (ver <https://hacs.xyz/>)


## Instalación
Una vez cumplidos los objetivos anteriores, los pasos a seguir para la instalación de esta integración son los siguientes:

1. Pulsa en [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=danieldiazi&repository=homeassistant-meteogalicia_tides&category=integration),

2. Instalar la integración mediante HACS. [Más info](docs/HACS_add_integration.md)

3. Reiniciar Home Assistant.

4. Añadir la integración desde **Ajustes → Dispositivos y servicios → Añadir integración**, buscar **MeteoGalicia Tides** y seleccionar el puerto por su nombre.

Antes de guardar la entrada se comprueba que MeteoGalicia responde y que los datos del puerto tienen un formato válido.

El intervalo predeterminado de las nuevas entradas es de 30 segundos. Puedes modificarlo desde **Ajustes → Dispositivos y servicios → MeteoGalicia Tides → Configurar**, entre 30 segundos y 24 horas.

La configuración mediante `configuration.yaml` sigue siendo compatible para las instalaciones existentes. Al iniciar Home Assistant, cada puerto configurado en YAML se importará automáticamente a **Dispositivos y servicios**, conservando el mismo identificador único de la entidad. Home Assistant mostrará una reparación para recordar que ya puedes retirar ese bloque YAML.

Si quieres añadir la información para un puerto dado:
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
- Con el parámetro opcional `scan_interval` indicas cada cuánto tiempo se conecta a MeteoGalicia. El valor se expresa en segundos; por ejemplo, 1200 equivale a 20 minutos. Al importar YAML, el intervalo se conserva exactamente y posteriormente puede modificarse desde la interfaz.

  
5. Si utilizas YAML, reinicia para que se recargue la configuración y espera unos minutos a que aparezca la entidad.

La integración ofrece además **Descargar diagnósticos** desde el menú de la entrada. El archivo incluye los últimos intentos y aciertos, duración de la petición, motivo del último fallo, backoff efectivo, versión del cliente y un resumen de la respuesta, pero no las coordenadas devueltas por la API.

No configures el mismo puerto simultáneamente mediante la interfaz y YAML.


## FAQ

###### La integración aparece como no disponible
El coordinador marca las entidades como no disponibles cuando MeteoGalicia no responde, devuelve contenido vacío o proporciona una respuesta inválida. Tras fallos consecutivos reduce progresivamente la frecuencia de consulta, hasta un máximo de 24 horas, y recupera el intervalo configurado en cuanto obtiene una respuesta válida.

###### TimeoutError
Si aparece el mensaje *MeteoGalicia request timed out*, el servicio no respondió antes de 60 segundos. Revisa la conexión y espera al siguiente intento.

###### Respuesta vacía o inválida
Los mensajes *returned no data* e *invalid response* diferencian una respuesta vacía de una respuesta que no contiene ninguna marea utilizable.
