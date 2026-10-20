import unittest

from src.canlibrarygenerator.selection import DatabaseSelection
from src.canlibrarygenerator.ir.builder import build_library_ir
from src.canlibrarygenerator.test.support import database


def build(dbs, selected=None, prefix='test'):
    tree = DatabaseSelection(dbs)
    return build_library_ir(selected if selected is not None else tree.selected_items,
                            prefix, dbs, tree, 'test', tree.message_modes)


class ValidationTests(unittest.TestCase):
    def test_duplicate_database_names_are_selected_by_identity(self):
        dbs = [database(' SG_ Value : 0|8@1+ (1,0) [0|255] "" ECU', frame=i)
               for i in (256, 257)]
        tree = DatabaseSelection(dbs)
        ir = build(dbs, [tree.selected_items[0]])
        self.assertEqual([msg.frame_id for msg in ir.messages], [256])
        with self.assertRaisesRegex(ValueError, 'generated name'):
            build(dbs)

    def test_invalid_prefix_and_signal_collisions(self):
        db = database(' SG_ Value : 0|8@1+ (1,0) [0|255] "" ECU')
        for prefix in ('bad-name', '../outside', 'class', 'const_cast', '_Atomic', '123'):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                build([db], prefix=prefix)
        db = database(' SG_ A__B : 0|8@1+ (1,0) [0|255] "" ECU\n'
                      ' SG_ A_B : 8|8@1+ (1,0) [0|255] "" ECU')
        with self.assertRaisesRegex(ValueError, 'colliding'):
            build([db])

    def test_message_names_cannot_shadow_generated_api(self):
        signal = ' SG_ Value : 0|8@1+ (1,0) [0|255] "" ECU'
        for name in ('all_messages', 'package_message'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'colliding'):
                build([database(signal, name=name)])
        with self.assertRaisesRegex(ValueError, 'macro'):
            build([database(signal, name='Sample', frame=256),
                   database(signal, name='sample', frame=257)])

    def test_unsupported_wire_types_and_lengths(self):
        mux = database(' SG_ Mode M : 0|8@1+ (1,0) [0|1] "" ECU\n'
                       ' SG_ A m0 : 8|8@1+ (1,0) [0|255] "" ECU\n'
                       ' SG_ B m1 : 8|8@1+ (1,0) [0|255] "" ECU')
        with self.assertRaisesRegex(ValueError, 'multiplexing'):
            build([mux])
        floating = database(' SG_ Value : 0|32@1+ (1,0) [0|1] "" ECU', 'SIG_VALTYPE_ 256 Value : 1;')
        with self.assertRaisesRegex(ValueError, 'floating-point'):
            build([floating])
        oversized = database(' SG_ Value : 0|8@1+ (1,0) [0|255] "" ECU', length=9)
        with self.assertRaisesRegex(ValueError, 'payload length'):
            build([oversized])


if __name__ == '__main__':
    unittest.main()
