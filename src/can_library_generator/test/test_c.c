#include <stdio.h>
#include <stdint.h>
#include "../temp/dbc_library_test.h"

int main() {
    uint8_t can_data[8] = { 0x0C, 0xB5, 0x01, 0x6E, 0xC4, 0xD0, 0xB6, 0x01 };
    uint8_t packaged_data[8] = { 0, 0, 0, 0, 0, 0, 0, 0 };
    double can_data_real[8] = { 12, 5, 1, 5.2, 880, 49, 87, 1 };
    uint32_t can_id = 0x121;
    uint8_t dlc = 8;
    int status = 0;

    printf("Unpackaging message...\n");

    if (dbc_unpackage_message(can_id, dlc, can_data) != 0) {
        printf("Unpackage failed or message not found!\n");
        
        return 1;
    }
    
    else {
        for (int i = 0; i < msgMotor_01.base.num_signals; i++) {
            if (can_data_real[i] != msgMotor_01.base.signals[i].value) {
                printf("Signal %s has wrong real value!\n", msgMotor_01.base.signals[i].name);
                printf("Original value: %.2f :: Unpackaged value: %.2f\n", can_data_real[i], msgMotor_01.base.signals[i].value);
                printf("Unpackaged raw value: %02x\n", msgMotor_01.base.signals[i].raw_value);

                status = 1;
            }
        }

        if (status == 0) {
            printf("Signals has been unpackaged successfully!\n");
        }
    }

    printf("\nPackaging message...\n");
    status = 0;

    if (dbc_package_message(can_id, dlc, packaged_data) != 0) {
        printf("Package message failed or message not Found!\n");

        return 1;
    }

    else {
        for (int j = 0; j < msgMotor_01.base.num_signals; j++) {
            if (packaged_data[j] != can_data[j]) {
                printf("Original data does not match with packaged data!\n");
                printf("Original: %02x :: Packaged: %02x\n", can_data[j], packaged_data[j]);

                status = 1;
            }
        }

        if (status == 0) {
            printf("Signals has been packaged successfully!\n");
        }
    }

    return 0;
}