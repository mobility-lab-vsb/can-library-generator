#include <iostream>
#include <fstream>
#include <string>
#include <vector>

// Struktura pro signál
struct DBCSignal {
    std::string name;
    int startBit;
    int length;
    std::string byteOrder;
    char valueType;
    double factor;
    double offset;
    double min;
    double max;
    std::string unit;
    std::string receiver;
};

// Struktura pro zprávu
struct DBCMessage {
    int id;
    std::string name;
    int dlc;
    std::string sender;
    std::vector<DBCSignal> signals;
};

// Funkce pro otevření souboru .dbc a následné vypsání do konzole pro kontrolu
void openDBCFile(const std::string& path) {
    std::ifstream dbcFile(path); // Otevření souboru

    if (!dbcFile.is_open()) {
        std::cerr << "Error: Failed to open " << path << std::endl;
        return;
    }

    std::cout << "File " << path << " open success." << std::endl;

    std::string line;

    // Výpis souboru .dbc na konzoli
    while (std::getline(dbcFile, line)) {
        std::cout << line << std::endl;
    }

    dbcFile.close(); // Zavření souboru
}

int main() {
    std::string path = "../../dbc/CAN_example.dbc";
    
    openDBCFile(path);

    return 0;
}
