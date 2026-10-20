import unittest

from src.canlibrarygenerator.test.support import database, compile_and_run


class J1939ProtectionTests(unittest.TestCase):
    def test_all_combinations_and_partial_selection(self):
        for combination in ('Aa', 'Cd', 'Da', 'Ef'):
            crc, counter = combination
            crc_start, crc_length = (56, 8) if crc in ('A', 'D') else (60, 4)
            counter_start = 52 if counter == 'a' else 56
            db = database(
                ' SG_ Payload : 0|8@1+ (1,0) [0|255] "" ECU\n'
                f' SG_ Counter : {counter_start}|4@1+ (1,0) [0|15] "" ECU\n'
                f' SG_ CRC : {crc_start}|{crc_length}@1+ (1,0) [0|255] "" ECU',
                'BA_DEF_ "ProtocolType" STRING ;\nBA_ "ProtocolType" "J1939";\n'
                f'BA_DEF_ BO_ "FsJ1939UseCrcAndCounter" ENUM "Default","{combination}";\n'
                'BA_ "FsJ1939UseCrcAndCounter" BO_ 256 1;')
            maximum = 7 if counter == 'f' else 15
            hooks = f'''
                uint8_t j1939_increment_ctr_{counter}(uint8_t previous) {{ return (previous + 1) & {maximum}; }}
                uint8_t j1939_calculate_crc_{crc.lower()}(can_db_msg_t* msg, uint8_t count) {{
                    assert(msg->data[0] == 42); assert(msg->data[1] == 255);
                    assert(count == 1); return 0xA5;
                }}
            '''
            body = f'''
                test_Sample.base.cb_fnc = callback;
                test_init(&test_Sample.base); assert(callbacks == 1);
                test_Sample.Payload->phys_value = 42;
                test_Sample_output_processing();
                assert(callbacks == 2);
                assert(test_Sample.Counter->phys_value == 1);
                assert(test_Sample.CRC->raw_value == {165 if crc_length == 8 else 5});
                assert(test_Sample.base.data[7] == {165 if crc_length == 8 else 81});
            '''
            for language in ('c', 'cpp'):
                for embedded in (False, True):
                    with self.subTest(combination=combination, language=language, embedded=embedded):
                        compile_and_run(self, db, body, language, embedded, hooks=hooks, selected=['Payload'])

    def test_disabled_crc_counter_and_callbacks_need_no_hooks(self):
        db = database(' SG_ Payload : 0|8@1+ (1,0) [0|255] "" ECU\n'
                      ' SG_ Counter : 52|4@1+ (1,0) [0|15] "" ECU\n'
                      ' SG_ CRC : 56|8@1+ (1,0) [0|255] "" ECU',
                      'BA_DEF_ BO_ "FsJ1939UseCrcAndCounter" ENUM "Default","Aa";\n'
                      'BA_ "FsJ1939UseCrcAndCounter" BO_ 256 1;')
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                compile_and_run(self, db, 'test_Sample_output_processing();',
                                language, generate_crc=False, generate_counter=False, generate_callback=False)


if __name__ == '__main__':
    unittest.main()
