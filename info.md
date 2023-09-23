[![HACS Supported](https://img.shields.io/badge/HACS-Supported-green.svg)](https://github.com/custom-components/hacs)
![GitHub Activity](https://img.shields.io/github/commit-activity/m/danieldiazi/homeassistant-meteogalicia_tides?label=commits)
![GitHub Release](https://img.shields.io/github/v/release/danieldiazi/homeassistant-meteogalicia_tides)

**configuration.yaml:**

```yaml
sensor:
  platform: meteogalicia_tides
  id_port: 1
  scan_interval: 1800
```

Many sensors:

``` yaml
sensor:
  - platform: meteogalicia_tides
    id_port: 1
    scan_interval: 1200
  - platform: meteogalicia_tides
    id_port: 2
    scan_interval: 1800
```


**Configuration variables:**  
  
key | description  
:--- | :---  
**platform (Required)** | The platform name: "meteogalicia_tides".  
**id_port (Required)** | The ID port by MeteoGalicia.  List available at: https://www.meteogalicia.gal/datosred/infoweb/meteo/docs/rss/RSS_Mareas_gl.pdf
**scan_interval (Optional)** | Interval in seconds to poll new data from meteogalicia webservice.  Recommended.
  
   


