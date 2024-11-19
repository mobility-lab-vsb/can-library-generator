#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <regex>

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

// Funkce pro parsování zprávy (BO_)
DBCMessage parseMessage(const std::string& line) {
    DBCMessage message;
    std::istringstream iss(line);
    std::string prefix;

    iss >> prefix >> message.id >> message.name >> message.dlc >> message.sender;
   
    // Kontrola jestli název zprávy obsahuje ':' nebo je prázdný
    if (!message.name.empty() && message.name.back() == ':') {
        message.name.pop_back(); // Slouží k odtranění ':' na konci jména zprávy
    }

    return message;
}

// Funkce pro parsování signálu (SG_)
DBCSignal parseSignal(const std::string& line) {
    DBCSignal signal;
    //std::regex signalRegex(R"(SG_\s+(\w+)\s*:\s*(\d+)\|(\d+)@(\d)([\+\-])\s+\(([\d\.]+),([\d\.]+)\)\s+\[([\d\.]+)\|([\d\.]+)\]\s+\"([^\"]*)\"\s+(\w+))");
    // Slouží pro správný parsing signálů
    std::regex signalRegex(R"(SG_\s+(\w+)\s*:\s*(\d+)\|(\d+)@(\d)([\+\-])\s+\(([\d\.]+),([\d\.]+)\)\s+\[([-+]?\d*\.?\d+)\|([-+]?\d*\.?\d+)\]\s*\"([^\"]*)\"\s*(\w+))");

    std::smatch match;

    for (int i = 0; i < match.size(); i++) {
        std::cout << match[i] << std::endl;
    }

    if (std::regex_search(line, match, signalRegex)) {
        signal.name = match[1];
        signal.startBit = std::stoi(match[2]);
        signal.length = std::stoi(match[3]);
        signal.byteOrder = match[4];
        signal.valueType = match[5].str()[0];
        signal.factor = std::stod(match[6]);
        signal.offset = std::stod(match[7]);
        signal.min = std::stod(match[8]);
        signal.max = std::stod(match[9]);
        signal.unit = match[10];
        signal.receiver = match[11];

        std::cout << "Parsed signal: " << signal.name << std::endl; // Výpis pro debug
    }
    else {
        std::cout << "No match for line: " << line << std::endl; // Výpis pro debug
    }

    return signal;
}

/*// Funkce pro otevření souboru .dbc a následné vypsání do konzole pro kontrolu
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
}*/

std::vector<DBCMessage> loadDBCFile(const std::string& path) {
    std::ifstream dbcFile(path); // Otevření souboru

    if (!dbcFile.is_open()) {
        std::cerr << "Error: Failed to open " << path << std::endl;
        return {};
    }

    std::cout << "File " << path << " open success." << std::endl;

    std::vector<DBCMessage> messages;
    DBCMessage currentMessage;
    std::string line;

    currentMessage = {};

    while (std::getline(dbcFile, line)) {
        if (line.rfind("BO_", 0) == 0) {
            if (!currentMessage.name.empty()) {
                messages.push_back(currentMessage);
                currentMessage = {};
            }

            currentMessage = parseMessage(line);
        }

        else if (line.rfind(" SG_", 0) == 0) {
            DBCSignal signal = parseSignal(line);
            currentMessage.signals.push_back(signal);
        }
    }

    if (!currentMessage.name.empty()) {
        messages.push_back(currentMessage);
    }

    dbcFile.close(); // Zavření souboru

    return messages;
}

int main() {
    std::string path = "../../dbc/CAN_example.dbc";
    std::vector<DBCMessage> messages = loadDBCFile(path);

    //openDBCFile(path);

    // Výpis zpráv a signálů do konzole pro debug
    for (const auto& message : messages) {
        std::cout << "Message ID: " << message.id << ", Name: " << message.name << ", DLC: " << message.dlc << ", Sender: " << message.sender << std::endl;

        for (const auto& signal : message.signals) {
            std::cout << "  Signal: " << signal.name << std::endl;
            std::cout << "      Start Bit: " << signal.startBit << std::endl;
            std::cout << "      Length: " << signal.length << std::endl;
            std::cout << "      Byte Order: " << signal.byteOrder << std::endl;
            std::cout << "      Value Type: " << signal.valueType << std::endl;
            std::cout << "      Factor: " << signal.factor << std::endl;
            std::cout << "      Offset " << signal.offset << std::endl;
            std::cout << "      Min: " << signal.min << std::endl;
            std::cout << "      Max: " << signal.max << std::endl;
            std::cout << "      Unit: " << signal.unit << std::endl;
            std::cout << "      Receiver: " << signal.receiver << std::endl;
        }
    }

    return 0;
}
