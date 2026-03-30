def classFactory(iface):
    """
    QGIS plugin entry point.

    Keep imports inside the factory so unit tests that import protocol-only modules
    do not require a full QGIS/PyQt environment.
    """

    from .qgis_server_plugin import QgisServerPlugin

    return QgisServerPlugin(iface)

