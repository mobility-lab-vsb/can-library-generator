from src.canlibrarygenerator.ir.builder import build_library_ir
from src.canlibrarygenerator.renderers.c_renderer import CRenderer


def generate_c_code(selected_items, library_name, dbs, tree, __version__, message_modes=None):
    """Generate C library output files"""

    ir = build_library_ir(
        selected_items=selected_items,
        library_name=library_name,
        dbs=dbs,
        tree=tree,
        version=__version__,
        message_modes=message_modes or {}
    )

    renderer = CRenderer()
    return renderer.render_all(ir)