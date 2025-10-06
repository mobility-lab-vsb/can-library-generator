#include <math.h>
#include <stdio.h>
#include <stdbool.h>
#include "../temp/cangen/cangen_interface.h"
#include "../temp/cangen/cangen_db.h"

int compare_data(const uint8_t* a, const uint8_t* b, const size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (a[i] != b[i]) {
            printf("DEBUG: Data mismatch at index %zu: 0x%X != 0x%X\n", i, a[i], b[i]);
            return 0;
        } /*else {
            printf("DEBUG: Data match at index %zu: 0x%X == 0x%X\n", i, a[i], b[i]);
        }*/
    }

    return 1;
}

int are_equal(const double d1, const double d2, const double epsilon) {
    if (fabs(d1 - d2) < epsilon)
        return 1;
    return 0;
}

void run_can_test() {
    printf("--- Testing CAN Message (ID 0x121) ---\n");

    const uint32_t can_message_id = 289;
    const uint8_t can_message_data[8] = { 0x0C, 0xB5, 0x01, 0x6E, 0xC4, 0xD0, 0xB6, 0x01 };
    const double expected_values[8] = { 12, 5, 1, 5.2, 880, 49, 87, 1 };
    const uint8_t message_length = sizeof(can_message_data);

    printf("Attempting to decode message with ID 0x%X...\n", can_message_id);
    if (cangen_unpackage_message(can_message_id, can_message_data, message_length) == 0) {
        printf("Decoding successfull.\n");

        printf("Verifying decoded signal values...\n");
        bool all_signals_ok = true;

        if (cangen_msgMotor_01.base.signals[0].phys_value != expected_values[0]) {
            printf("  - ERROR: sigMO_CRC mismatch. Expected %u, got %u\n", (uint8_t)expected_values[0], (uint8_t)cangen_msgMotor_01.base.signals[0].phys_value);
            all_signals_ok = false;
        }
        if (cangen_msgMotor_01.base.signals[1].phys_value != expected_values[1]) {
            printf("  - ERROR: sigMO_CTR mismatch. Expected %u, got %u\n", (uint8_t)expected_values[1], (uint8_t)cangen_msgMotor_01.base.signals[1].phys_value);
            all_signals_ok = false;
        }
        if (cangen_msgMotor_01.base.signals[2].phys_value != expected_values[2]) {
            printf("  - ERROR: sigMO_MotorRunningStatus mismatch. Expected %u, got %u\n", (bool)expected_values[2], (bool)cangen_msgMotor_01.base.signals[2].phys_value);
            all_signals_ok = false;
        }
        if (cangen_msgMotor_01.base.signals[3].phys_value != expected_values[3]) {
            printf("  - ERROR: sigMO_PedalPosition mismatch. Expected %f, got %f\n", expected_values[3], cangen_msgMotor_01.base.signals[3].phys_value);
            all_signals_ok = false;
        }
        if (cangen_msgMotor_01.base.signals[4].phys_value != expected_values[4]) {
            printf("  - ERROR: sigMO_EngineSpeed mismatch. Expected %u, got %u\n", (uint16_t)expected_values[4], (uint16_t)cangen_msgMotor_01.base.signals[4].phys_value);
            all_signals_ok = false;
        }
        if (cangen_msgMotor_01.base.signals[5].phys_value != expected_values[5]) {
            printf("  - ERROR: sigMO_EngineTorque mismatch. Expected %d, got %d\n", (int)expected_values[5], (int)cangen_msgMotor_01.base.signals[5].phys_value);
            all_signals_ok = false;
        }
        if (cangen_msgMotor_01.base.signals[6].phys_value != expected_values[6]) {
            printf("  - ERROR: sigMO_Oil_Temperature mismatch. Expected %d, got %d\n", (int)expected_values[6], (int)cangen_msgMotor_01.base.signals[6].phys_value);
            all_signals_ok = false;
        }
        if (cangen_msgMotor_01.base.signals[7].phys_value != expected_values[7]) {
            printf("  - ERROR: sigMO_Oil_pressure mismatch. Expected %f, got %f\n", expected_values[7], cangen_msgMotor_01.base.signals[7].phys_value);
            all_signals_ok = false;
        }

        if (all_signals_ok) {
            printf("  All signals decoded correctly.\n");
        }
        else {
            printf("  Some signals failed to decode correctly.\n");
        }

        // Test packaging process
        printf("\nVerifying packaging process...\n");
        if (cangen_package_message(can_message_id) == 0) {
            printf("Packaging successful. Checking data integrity...\n");
            if (compare_data(can_message_data,cangen_msgMotor_01.base.data, cangen_msgMotor_01.base.dlc)) {
                printf("Data integrity test passed!\n");
            }
            else {
                printf("ERROR: Encoded data does not match original data.\n");
            }
        }
        else {
            printf("ERROR: Packaging failed for message with ID 0x%x", can_message_id);
        }
    }
    else {
        printf("ERROR: Decoding failed for message with ID 0x%X.\n", can_message_id);
    }
}

void run_canfd_test() {
    printf("--- Testing CAN FD Message (ID 0xD001) ---\n");

    const uint32_t canfd_canid = 0xD001;
    const uint8_t canfd_data[16] = { 0x10, 0x37, 0xBB, 0x1D, 0x64, 0x49, 0xE5, 0x0A, 0xE7, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    const uint8_t canfd_dlen = sizeof(canfd_data);
    const double expected_canfd_values[3] = { 110.491736, 189.047311, 7.8 };

    printf("Attempting to decode message with ID 0x%x...\n", canfd_canid);
    if (cangen_unpackage_message(canfd_canid, canfd_data, canfd_dlen) == 0) {
        printf("Decoding successful.\n");

        if (cangen_msgVD_GNSS_precision_position.base.is_fd) {
            printf("Message correctly identified as CAN FD.\n");
        }
        else {
            printf("ERROR: Message not identified as CAN FD.\n");
        }

        printf("\nVerifying decoded signal values...\n");
        bool all_signals_ok = true;

        if (are_equal(expected_canfd_values[0], cangen_msgVD_GNSS_precision_position.base.signals[0].phys_value, 1E-6) == 0) {
            printf("  - ERROR: %s mismatch. Expected %f, got %f\n", cangen_msgVD_GNSS_precision_position.base.signals[0].name, expected_canfd_values[0], cangen_msgVD_GNSS_precision_position.base.signals[0].phys_value);
            all_signals_ok = false;
        }
        if (are_equal(expected_canfd_values[1], cangen_msgVD_GNSS_precision_position.base.signals[1].phys_value, 1E-6) == 0) {
            printf("  - ERROR: %s mismatch. Expected %f, got %f\n", cangen_msgVD_GNSS_precision_position.base.signals[1].name, expected_canfd_values[1], cangen_msgVD_GNSS_precision_position.base.signals[1].phys_value);
            all_signals_ok = false;
        }
        if (are_equal(expected_canfd_values[2], cangen_msgVD_GNSS_precision_position.base.signals[2].phys_value, 1E-6) == 0) {
            printf("  - ERROR: %s mismatch. Expected %f, got %f\n", cangen_msgVD_GNSS_precision_position.base.signals[2].name, expected_canfd_values[2], cangen_msgVD_GNSS_precision_position.base.signals[2].phys_value);
            all_signals_ok = false;
        }

        if (all_signals_ok) {
            printf("  All signals decoded correctly.\n");
        }
        else {
            printf("  Some signals failed to decode correctly.\n");
        }

        // Test packaging process
        printf("\nVerifying packaging process...\n");
        if (cangen_package_message(canfd_canid) == 0) {
            printf("Packaging successful. Checking data integrity...\n");
            if (compare_data(canfd_data, cangen_msgVD_GNSS_precision_position.base.data, cangen_msgVD_GNSS_precision_position.base.dlc)) {
                printf("Data integrity test passed!\n");
            }
            else {
                printf("ERROR: Decoded data does not match original data.\n");
            }
        }
        else {
            printf("ERROR: Packaging failed for message with ID 0x%x", canfd_canid);
        }
    }
    else {
        printf("ERROR: Decoding failed for message with ID 0x%X", canfd_canid);
    }
}

int main(void) {
    run_can_test();
    run_canfd_test();

    return 0;
}