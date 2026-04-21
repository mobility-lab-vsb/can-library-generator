from jinja2 import Environment, FileSystemLoader
import os

class CPPRenderer:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates", "cpp")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=False,
            lstrip_blocks=False
            )

    def render_can_db_def(self, ir):
        return self.env.get_template("can_db_def.hpp.j2").render(ir=ir)

    def render_db_h(self, ir):
        return self.env.get_template("db_hpp.j2").render(ir=ir)

    def render_db_c(self, ir):
        return self.env.get_template("db_cpp.j2").render(ir=ir)

    def render_interface_h(self, ir):
        return self.env.get_template("interface_hpp.j2").render(ir=ir)

    def render_interface_c(self, ir):
        return self.env.get_template("interface_cpp.j2").render(ir=ir)

    def render_all(self, ir):
        return (
            self.render_can_db_def(ir),
            self.render_db_h(ir),
            self.render_db_c(ir),
            self.render_interface_h(ir),
            self.render_interface_c(ir)
        )