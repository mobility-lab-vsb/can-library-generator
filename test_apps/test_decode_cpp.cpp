#include <iostream>
#include "../temp/dbc_library_test.hpp"  

int main() {
    uint8_t can_data[8] = { 0x0C, 0xB5, 0x01, 0x6E, 0xC4, 0xD0, 0xB6, 0x01 };
    uint32_t can_id = 0x121;
    uint8_t dlc = 8;

    if (!dbc_decode_message(can_id, dlc, can_data)) {
        std::cerr << "Decode failed or message not found\n";
        return 1;
    }

    std::cout << "Decoded signals from msgMotor_01:\n";
    std::cout << "  sigMO_CRC: " << msgMotor_01.sigMO_CRC->value << "\n";
    std::cout << "  sigMO_CTR: " << msgMotor_01.sigMO_CTR->value << "\n";
    std::cout << "  sigMO_MotorRunningStatus: " << msgMotor_01.sigMO_MotorRunningStatus->value << "\n";
    std::cout << "  sigMO_PedalPosition: " << msgMotor_01.sigMO_PedalPosition->value << "\n";
    std::cout << "  sigMO_EngineSpeed: " << msgMotor_01.sigMO_EngineSpeed->value << "\n";
    std::cout << "  sigMO_EngineTorque: " << msgMotor_01.sigMO_EngineTorque->value << "\n";
    std::cout << "  sigMO_Oil_Temperature: " << msgMotor_01.sigMO_Oil_Temperature->value << "\n";
    std::cout << "  sigMO_Oil_pressure: " << msgMotor_01.sigMO_Oil_pressure->value << "\n";

    return 0;
}
