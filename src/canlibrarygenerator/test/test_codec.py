"""Compare signed, Motorola and wide signal codecs against cantools."""
import unittest

from src.canlibrarygenerator.test.support import database, compile_and_run


class CodecTests(unittest.TestCase):
    def test_roundtrips(self):
        cases = [
            (' SG_ Value : 0|8@1- (1,0) [-128|127] "" ECU', -1),
            (' SG_ Value : 7|16@0+ (1,0) [0|65535] "" ECU', 4660),
            (' SG_ Value : 11|12@0- (0.25,-10) [-522|501.75] "" ECU', -20),
            (' SG_ Value : 0|40@1+ (1,0) [0|1099511627775] "" ECU', 78187493530),
        ]
        for signals, value in cases:
            db = database(signals)
            expected = db.messages[0].encode({'Value': value})
            payload = ','.join(str(byte) for byte in expected)
            body = f'''
                uint8_t expected[8] = {{{payload}}};
                assert(test_unpackage_message(256, expected, 8) == 0);
                assert(test_Sample.Value->phys_value == {value});
                assert(test_package_message(256) == 0);
                assert(memcmp(expected, test_Sample.base.data, 8) == 0);
                assert(test_parse_signal(expected, 1, 500, 64, false) == 0);
                uint8_t unchanged[8]; memcpy(unchanged, expected, 8);
                test_insert_signal(expected, 1, UINT64_MAX, 7, 64, true);
                assert(memcmp(expected, unchanged, 8) == 0);
                test_Sample.base.cb_fnc = callback;
                test_init(&test_Sample.base); assert(callbacks == 1);
                can_db_msg_t rx = {{0}};
                rx.id = 999; rx.length = 8;
                test_Sample_input_processing(&rx); assert(callbacks == 1);
            '''
            for language in ('c', 'cpp'):
                for embedded in (False, True):
                    with self.subTest(value=value, language=language, embedded=embedded):
                        # C++ cannot use {0} on a structure with std::string.
                        fixture = body.replace('rx = {0}', 'rx = {}') if language == 'cpp' else body
                        compile_and_run(self, db, fixture, language, embedded)

    def test_raw_64_bits_and_rejected_physical_values(self):
        db = database(' SG_ Value : 0|64@1+ (1,0) [0|18446744073709551615] "" ECU')
        body = '''
            test_Sample.Value->raw_value = UINT64_MAX;
            assert(test_package_message_raw(256) == 0);
            for (int i = 0; i < 8; ++i) assert(test_Sample.base.data[i] == 255);
            assert(test_unpackage_message(256, test_Sample.base.data, 8) == 0);
            assert(test_Sample.Value->raw_value == UINT64_MAX);
            test_Sample.Value->phys_value = -1;
            assert(test_package_message(256) == -1);
            assert(test_Sample.Value->raw_value == UINT64_MAX);
            assert(test_unpackage_message(256, NULL, 8) == -1);
        '''
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                compile_and_run(self, db, body, language)

    def test_counter_wrap_and_crc(self):
        db = database(' SG_ CRC : 0|8@1+ (1,0) [0|255] "" ECU\n'
                      ' SG_ Count : 8|4@1+ (1,0) [0|15] "" ECU',
                      'BA_DEF_ SG_ "GenSigFuncType" INT 0 2;\n'
                      'BA_ "GenSigFuncType" SG_ 256 Count 1;\n'
                      'BA_ "GenSigFuncType" SG_ 256 CRC 2;')
        hooks = 'uint8_t calculate_crc(const uint8_t* data, uint8_t length, uint8_t initial) { assert(length == 8); assert(initial == 0); assert((data[1] & 15) == 0); return 0xA5; }'
        body = '''test_Sample.Count->phys_value = 15;
                  test_Sample_output_processing();
                  assert(test_Sample.Count->phys_value == 0);
                  assert(test_Sample.base.data[0] == 0xA5); assert(sends == 1);'''
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                compile_and_run(self, db, body, language, hooks=hooks)


if __name__ == '__main__':
    unittest.main()
