#include <stdio.h>
#include <stdint.h>
#include "../temp/dbc_library_test.h"

int main() {
    uint8_t can_data[8] = { 0x0C, 0xB5, 0x01, 0x6E, 0xC4, 0xD0, 0xB6, 0x01 };
    uint32_t can_id = 0x121;
    uint8_t dlc = 8;

    if(dbc_unpackage_message(can_id, dlc, can_data) != 0) {
        printf("Decode failed or message not found!\n");
        
        return 1;
    }

    printf("Decoded signals from msgMotor_01:\n");
    printf("    sigMO_CRC: %.2f\n", msgMotor_01.sigMO_CRC->value);
    printf("    sigMO_CTR: %.2f\n", msgMotor_01.sigMO_CTR->value);
    printf("    sigMO_MotorRunningStatus: %.2f\n", msgMotor_01.sigMO_MotorRunningStatus->value);
    printf("    sigMO_PedalPosition: %.2f\n", msgMotor_01.sigMO_PedalPosition->value);
    printf("    sigMO_EngineSpeed: %.2f\n", msgMotor_01.sigMO_EngineSpeed->value);
    printf("    sigMO_EngineTorque: %.2f\n", msgMotor_01.sigMO_EngineTorque->value);
    printf("    sigMO_Oil_Temperature: %.2f\n", msgMotor_01.sigMO_Oil_Temperature->value);
    printf("    sigMO_Oil_pressure: %.2f\n", msgMotor_01.sigMO_Oil_pressure->value);

    return 0;
}