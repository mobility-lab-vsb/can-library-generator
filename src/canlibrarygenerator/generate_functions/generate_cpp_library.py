from ..ir.builder import build_library_ir
from ..renderers.cpp_renderer import CPPRenderer

def generate_cpp_code(selected_items, library_name, dbs, tree, __version__="dev", message_modes=None, embedded=False, with_units=False,
                      generate_counter=True, generate_crc=True, generate_callback=None):
    """Generate C++ library output files"""

    ir = build_library_ir(
        selected_items=selected_items,
        library_name=library_name,
        dbs=dbs,
        tree=tree,
        version=__version__,
        message_modes=message_modes or {},
        embedded=embedded,
        with_units=with_units,
        generate_counter=generate_counter,
        generate_crc=generate_crc,
        generate_callback=generate_callback
    )

    renderer = CPPRenderer()
    return renderer.render_all(ir)