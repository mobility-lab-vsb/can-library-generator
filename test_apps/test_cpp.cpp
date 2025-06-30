#include <iostream>
#include "../temp/dbc_library_test.hpp"  

int main() {
     uint8_t can_data[8] = { 0x0C, 0xB5, 0x01, 0x6E, 0xC4, 0xD0, 0xB6, 0x01 };
    uint8_t packaged_data[8] = { 0, 0, 0, 0, 0, 0, 0, 0 };
    double can_data_real[8] = { 12, 5, 1, 5.2, 880, 49, 87, 1 };
    uint32_t can_id = 0x121;
    uint8_t dlc = 8;
    int status = 0;

    std::cout << "Unpackaging message..." << std::endl;

    if (dbc_unpackage_message(can_id, dlc, can_data) == false) {
        std::cout << "Unpackage failed or message not found!" << std::endl;
        
        return 1;
    }
    
    else {
        for (int i = 0; i < msgMotor_01.base.signals.size(); i++) {
            if (can_data_real[i] != msgMotor_01.base.signals[i]->value) {
                std::cout << "Signal" << msgMotor_01.base.signals[i]->name << "has wrong real value!" << std::endl;
                std::cout << "Original value: " << can_data_real[i] << " ::Unpackaged value : " << msgMotor_01.base.signals[i]->value << std::endl;
                std::cout << "Unpackaged raw value: " << msgMotor_01.base.signals[i]->raw_value << std::endl;

                status = 1;
            }
        }

        if (status == 0) {
            std::cout << "Signals has been unpackaged successfully!" << std::endl;
        }
    }

    std::cout << "\nPackaging message..." << std::endl;
    status = 0;

    if (dbc_package_message(can_id, dlc, packaged_data) == false) {
        std::cout << "Package message failed or message not Found!" << std::endl;

        return 1;
    }

    else {
        for (int j = 0; j < msgMotor_01.base.signals.size(); j++) {
            if (packaged_data[j] != can_data[j]) {
                std::cout << "Original data does not match with packaged data!" << std::endl;
                std::cout << "Original: " << can_data[j] << " :: Packaged: " << packaged_data[j] << std::endl;

                status = 1;
            }
        }

        if (status == 0) {
            std::cout << "Signals has been packaged successfully!" << std::endl;
        }
    }

    return 0;
}