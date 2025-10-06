import os

from src.canlibrarygenerator.generate_functions.generate_c_library import generate_c_code
from src.canlibrarygenerator.generate_functions.generate_cpp_library import generate_cpp_code
from src.canlibrarygenerator.scripts.codegen_utils import generate_all_code


# Configuration
dbc_file = os.path.join(os.path.dirname(__file__), '..', 'dbc', 'CAN_example.dbc')
generate_all_code(dbc_file, "cangen", generate_c_code, generate_cpp_code)