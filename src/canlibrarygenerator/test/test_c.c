#include <math.h>
#include <stdio.h>
#include <stdbool.h>
#include <string.h>

#include "cangen_interface.h"
#include "cangen_db.h"

// --- Simple testing framework ---
int tests_run = 0;
int tests_passed = 0;

#define TEST_ASSERT(cond, msg) \
    do { \
        tests_run++; \
        if (!(cond)) { \
            printf("  [FAIL] %s:%d - %s\n", __func__, __LINE__, msg); \
        } else { \
            printf("  [PASS] %s\n", msg); \
            tests_passed++; \
        } \
    } while(0)

#define TEST_ASSERT_FLOAT_EQ(expected, actual, epsilon, msg) \
    do { \
        tests_run++; \
        if (fabs((expected) - (actual)) > (epsilon)) { \
            printf("  [FAIL] %s:%d - %s (Expected: %f, Got: %f)\n", __func__, __LINE__, msg, (double)(expected), (double)(actual)); \
        } else { \
            printf("  [PASS] %s\n", msg); \
            tests_passed++; \
        } \
    } while(0)

bool compare_data(const uint8_t* a, const uint8_t* b, size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (a[i] != b[i]) return false;
    }
    return true;
}

// --- Standard CAN message test ---
void test_standard_can_message(void) {
    printf("\n--- Testing CAN Message (ID 0x121) ---\n");

    const uint32_t can_id = 289;
    const uint8_t raw_data[8] = { 0x0C, 0xB5, 0x01, 0x6E, 0xC4, 0xD0, 0xB6, 0x01 };
    const uint8_t msg_length = sizeof(raw_data);

    // Unpack test
    int unpack_res = cangen_unpackage_message(can_id, raw_data, msg_length);
    TEST_ASSERT(unpack_res == 0, "Message decoded successfully");

    if (unpack_res == 0) {
        TEST_ASSERT_FLOAT_EQ(12.0, cangen_msgMotor_01.base.signals[0].phys_value, 1e-3, "sigMO_CRC decoded correctly");
        TEST_ASSERT_FLOAT_EQ(5.0,  cangen_msgMotor_01.base.signals[1].phys_value, 1e-3, "sigMO_CTR decoded correctly");
        TEST_ASSERT_FLOAT_EQ(1.0,  cangen_msgMotor_01.base.signals[2].phys_value, 1e-3, "sigMO_MotorRunningStatus decoded correctly");
        TEST_ASSERT_FLOAT_EQ(5.2,  cangen_msgMotor_01.base.signals[3].phys_value, 1e-3, "sigMO_PedalPosition decoded correctly");
        TEST_ASSERT_FLOAT_EQ(880.0, cangen_msgMotor_01.base.signals[4].phys_value, 1e-3, "sigMO_EngineSpeed decoded correctly");
        TEST_ASSERT_FLOAT_EQ(49.0, cangen_msgMotor_01.base.signals[5].phys_value, 1e-3, "sigMO_EngineTorque decoded correctly");
        TEST_ASSERT_FLOAT_EQ(87.0, cangen_msgMotor_01.base.signals[6].phys_value, 1e-3, "sigMO_Oil_Temperature decoded correctly");
        TEST_ASSERT_FLOAT_EQ(1.0,  cangen_msgMotor_01.base.signals[7].phys_value, 1e-3, "sigMO_Oil_pressure decoded correctly");
    }

    // Pack test
    int pack_res = cangen_package_message(can_id);
    TEST_ASSERT(pack_res == 0, "Message packaged successfully");

    if (pack_res == 0) {
        TEST_ASSERT(compare_data(raw_data, cangen_msgMotor_01.base.data, cangen_msgMotor_01.base.dlc), "Data integrity matches after packaging");
    }
}

// --- CAN FD message test ---
void test_canfd_message(void) {
    printf("\n--- Testing CAN FD Message (ID 0xD001) ---\n");

    const uint32_t canfd_id = 0xD001;
    const uint8_t canfd_data[16] = { 0x10, 0x37, 0xBB, 0x1D, 0x64, 0x49, 0xE5, 0x0A, 0xE7, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    const uint8_t msg_length = sizeof(canfd_data);

    // Unpack test
    int unpack_res = cangen_unpackage_message(canfd_id, canfd_data, msg_length);
    TEST_ASSERT(unpack_res == 0, "CAN FD message decoded successfully");

    if (unpack_res == 0) {
        TEST_ASSERT(cangen_msgVD_GNSS_precision_position.base.is_fd == 1, "is_fd flag set correctly");
        TEST_ASSERT_FLOAT_EQ(110.491736, cangen_msgVD_GNSS_precision_position.base.signals[0].phys_value, 1E-6, "sigVD_GNSS_LatitudeDegree decoded correctly");
        TEST_ASSERT_FLOAT_EQ(189.047311, cangen_msgVD_GNSS_precision_position.base.signals[1].phys_value, 1E-6, "sigVD_GNSS_LongitudeDegree decoded correctly");
        TEST_ASSERT_FLOAT_EQ(7.8, cangen_msgVD_GNSS_precision_position.base.signals[2].phys_value, 1E-6, "sigVD_GNSS_heading decoded correctly");
    }

    // Pack test
    int pack_res = cangen_package_message(canfd_id);
    TEST_ASSERT(pack_res == 0, "CAN FD message packaged successfully");

    if (pack_res == 0) {
        TEST_ASSERT(compare_data(canfd_data, cangen_msgVD_GNSS_precision_position.base.data, cangen_msgVD_GNSS_precision_position.base.length), "CAN FD data integrity matches after packaging");
    }
}

// --- Registry test ---
void test_registry_size(void) {
    printf("\n--- Testing C Registry ---\n");

    // Using the generated variable for message count
    size_t actual_size = cangen_all_messages_count;
    printf("  Registry size: %zu messages\n", actual_size);
    TEST_ASSERT(actual_size > 0, "Registry is not empty");
}

int main(void) {
    printf("Running C tests...\n");

    test_standard_can_message();
    test_canfd_message();
    test_registry_size();

    printf("\n======================================\n");
    printf("RESULT: %d / %d tests passed.\n", tests_passed, tests_run);
    printf("======================================\n");

    return (tests_passed == tests_run) ? 0 : 1;
}