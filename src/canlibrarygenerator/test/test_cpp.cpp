#include <iostream>
#include <cmath>
#include <vector>
#include <iomanip>
#include "../temp/cangen.hpp"

bool compare_data(const std::vector<uint8_t>& a, const std::vector<uint8_t>& b) {
    if (a.size() != b.size()) {
        std::cout << "DEBUG: Data size mismatch. a.size() = " << a.size() << ", b.size() = " << b.size() << std::endl;
        return false;
    }

    for (size_t i = 0; i < a.size(); i++) {
        if (a[i] != b[i]) {
            std::cout << "DEBUG: Data mismatch at index " << i << ": 0x" << std::hex << a[i] << " != 0x" << b[i] << std::dec << std::endl;
            return false;
        }
    }

    return true;
}

bool are_equal(const double d1, const double d2, const double epsilon) {
    return std::fabs(d1 - d2) < epsilon;
}

//--- run_can_test ---
void run_can_test() {
    std::cout << "--- Testing CAN Message (ID 0x121) ---" << std::endl;

    const uint32_t can_message_id = 289;
    const std::vector<uint8_t> can_message_data = { 0x0C, 0xB5, 0x01, 0x6E, 0xC4, 0xD0, 0xB6, 0x01 };
    const std::vector<double> expected_values = { 12, 5, 1, 5.2, 880, 49, 87, 1 };
    const uint8_t dlc = can_message_data.size();

    std::cout << "Attempting to decode message with ID 0x" << std::hex << can_message_id << std::dec << "..." << std::endl;
    if (dbc_unpackage_message(can_message_id, can_message_data.data(), dlc)) {
        std::cout << "Decoding successful." << std::endl;

        std::cout << "Verifying decoded signal values..." << std::endl;
        bool all_signals_ok = true;

        if (msgMotor_01.base.signals[0]->value != expected_values[0]) {
            std::cout << "  - ERROR: sigMO_CRC mismatch. Expected " << expected_values[0] << ", got " << msgMotor_01.base.signals[0]->value << std::endl;
            all_signals_ok = false;
        }
        if (msgMotor_01.base.signals[1]->value != expected_values[1]) {
            std::cout << "  - ERROR: sigMO_CTR mismatch. Expected " << expected_values[1] << ", got " << msgMotor_01.base.signals[1]->value << std::endl;
            all_signals_ok = false;
        }
        if (msgMotor_01.base.signals[2]->value != expected_values[2]) {
            std::cout << "  - ERROR: sigMO_MotorRunningStatus mismatch. Expected " << expected_values[2] << ", got " << msgMotor_01.base.signals[2]->value << std::endl;
            all_signals_ok = false;
        }
        if (msgMotor_01.base.signals[3]->value != expected_values[3]) {
            std::cout << "  - ERROR: sigMO_PedalPosition mismatch. Expected " << expected_values[3] << ", got " << msgMotor_01.base.signals[3]->value << std::endl;
            all_signals_ok = false;
        }
        if (msgMotor_01.base.signals[4]->value != expected_values[4]) {
            std::cout << "  - ERROR: sigMO_EngineSpeed mismatch. Expected " << expected_values[4] << ", got " << msgMotor_01.base.signals[4]->value << std::endl;
            all_signals_ok = false;
        }
        if (msgMotor_01.base.signals[5]->value != expected_values[5]) {
            std::cout << "  - ERROR: sigMO_EngineTorque mismatch. Expected " << expected_values[5] << ", got " << msgMotor_01.base.signals[5]->value << std::endl;
            all_signals_ok = false;
        }
        if (msgMotor_01.base.signals[6]->value != expected_values[6]) {
            std::cout << "  - ERROR: sigMO_Oil_Temperature mismatch. Expected " << expected_values[6] << ", got " << msgMotor_01.base.signals[6]->value << std::endl;
            all_signals_ok = false;
        }
        if (msgMotor_01.base.signals[7]->value != expected_values[7]) {
            std::cout << "  - ERROR: sigMO_Oil_pressure mismatch. Expected " << expected_values[7] << ", got " << msgMotor_01.base.signals[7]->value << std::endl;
            all_signals_ok = false;
        }

        if (all_signals_ok) {
            std::cout << "  All signals decoded correctly." << std::endl;
        } else {
            std::cout << "  Some signals failed to decode correctly." << std::endl;
        }

        // Test packaging process
        std::cout << "\nVerifying packaging process..." << std::endl;
        if (dbc_package_message(can_message_id)) {
            std::cout << "Packaging successful. Checking data integrity..." << std::endl;
            std::vector<uint8_t> packaged_data(msgMotor_01.base.data, msgMotor_01.base.data + msgMotor_01.base.dlc);
            if (compare_data(can_message_data, packaged_data)) {
                std::cout << "Data integrity test passed!" << std::endl;
            } else {
                std::cout << "ERROR: Encoded data does not match original data." << std::endl;
            }
        } else {
            std::cout << "ERROR: Packaging failed for message with ID 0x" << std::hex << can_message_id << std::dec << std::endl;
        }
    } else {
        std::cout << "ERROR: Decoding failed for message with ID 0x" << std::hex << can_message_id << std::dec << "." << std::endl;
    }
}

void run_canfd_test() {
    std::cout << std::endl;
    std::cout << "--- Testing CAN FD Message (ID 0xD001) ---" << std::endl;

    const uint32_t canfd_canid = 0xD001;
    const std::vector<uint8_t> canfd_data = { 0x10, 0x37, 0xBB, 0x1D, 0x64, 0x49, 0xE5, 0x0A, 0xE7, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    const uint8_t canfd_dlen = canfd_data.size();
    const std::vector<double> expected_canfd_values = { 110.491736, 189.047311, 7.8 };

    std::cout << "Attempting to decode message with ID 0x" << std::hex << canfd_canid << std::dec << "..." << std::endl;
    if (dbc_unpackage_message(canfd_canid, canfd_data.data(), canfd_dlen)) {
        std::cout << "Decoding successful." << std::endl;

        if (msgVD_GNSS_precision_position.base.is_fd) {
            std::cout << "Message correctly identified as CAN FD." << std::endl;
        } else {
            std::cout << "ERROR: Message not identified as CAN FD." << std::endl;
        }

        std::cout << "\nVerifying decoded signal values..." << std::endl;
        bool all_signals_ok = true;

        if (!are_equal(expected_canfd_values[0], msgVD_GNSS_precision_position.base.signals[0]->value, 1E-6)) {
            std::cout << "  - ERROR: " << msgVD_GNSS_precision_position.base.signals[0]->name << " mismatch. Expected " << std::fixed << std::setprecision(6) << expected_canfd_values[0] << ", got " << msgVD_GNSS_precision_position.base.signals[0]->value << std::endl;
            all_signals_ok = false;
        }
        if (!are_equal(expected_canfd_values[1], msgVD_GNSS_precision_position.base.signals[1]->value, 1E-6)) {
            std::cout << "  - ERROR: " << msgVD_GNSS_precision_position.base.signals[1]->name << " mismatch. Expected " << expected_canfd_values[1] << ", got " << msgVD_GNSS_precision_position.base.signals[1]->value << std::endl;
            all_signals_ok = false;
        }
        if (!are_equal(expected_canfd_values[2], msgVD_GNSS_precision_position.base.signals[2]->value, 1E-6)) {
            std::cout << "  - ERROR: " << msgVD_GNSS_precision_position.base.signals[2]->name << " mismatch. Expected " << expected_canfd_values[2] << ", got " << msgVD_GNSS_precision_position.base.signals[2]->value << std::endl;
            all_signals_ok = false;
        }

        if (all_signals_ok) {
            std::cout << "  All signals decoded correctly." << std::endl;
        } else {
            std::cout << "  Some signals failed to decode correctly." << std::endl;
        }

        // Test packaging process
        std::cout << "\nVerifying packaging process..." << std::endl;
        if (dbc_package_message(canfd_canid)) {
            std::cout << "Packaging successful. Checking data integrity..." << std::endl;
            std::vector<uint8_t> packaged_data(msgVD_GNSS_precision_position.base.data, msgVD_GNSS_precision_position.base.data + msgVD_GNSS_precision_position.base.dlc);
            if (compare_data(canfd_data, packaged_data)) {
                std::cout << "Data integrity test passed!" << std::endl;
            } else {
                std::cout << "ERROR: Decoded data does not match original data." << std::endl;
            }
        } else {
            std::cout << "ERROR: Packaging failed for message with ID 0x" << std::hex << canfd_canid << std::dec << std::endl;
        }
    } else {
        std::cout << "ERROR: Decoding failed for message with ID 0x" << std::hex << canfd_canid << std::dec << std::endl;
    }
}

int main() {
    run_can_test();
    run_canfd_test();

    return 0;
}