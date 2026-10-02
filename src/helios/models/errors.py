"""Fallo de un adaptador local. La mesa sigue con el resto de etapas."""


class ModelUnavailable(RuntimeError):
    """El modelo no está instalado, no responde o falta la librería."""
