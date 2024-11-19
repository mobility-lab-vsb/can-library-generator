#include <iostream>
#include <fstream>
#include <string>

// Funkce pro otevření souboru .dbc a následné vypsání do konzole pro kontrolu
void openDBCFile(const std::string& path) {
    std::ifstream dbcFile(path);

    if (!dbcFile.is_open()) {
        std::cerr << "Error: Failed to open " << path << std::endl;
        return;
    }

    std::cout << "File " << path << " open success." << std::endl;

    std::string line;

    while (std::getline(dbcFile, line)) {
        std::cout << line << std::endl;
    }

    dbcFile.close();
}

int main() {
    std::string path = "../../dbc/CAN_example.dbc";
    
    openDBCFile(path);

    return 0;
}
