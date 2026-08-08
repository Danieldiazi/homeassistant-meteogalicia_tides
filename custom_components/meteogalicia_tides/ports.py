"""Ports supported by the MeteoGalicia tide service."""

PORTS: dict[str, str] = {
    "1": "A Coruña",
    "2": "Xixón",
    "3": "Vigo",
    "4": "Vilagarcía",
    "6": "Ría de Foz",
    "7": "Corcubión",
    "8": "Ría de Camariñas",
    "9": "Ría de Corme",
    "10": "A Guarda",
    "11": "Ribeira",
    "12": "Muros",
    "13": "Pontevedra",
    "14": "Ferrol Porto exterior",
    "15": "Marín",
    "16": "Ferrol",
}


def port_name(id_port: str) -> str:
    """Return the official name or a stable fallback for a port ID."""
    return PORTS.get(id_port, f"Port {id_port}")
