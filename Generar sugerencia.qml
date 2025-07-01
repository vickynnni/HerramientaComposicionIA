import QtQuick 2.0
import MuseScore 3.0

MuseScore {
    menuPath: "Plugins/TFG/Ejecutar Script Python"

    onRun: {
        var request = new XMLHttpRequest();
        request.open("PUT", "file:///tmp/tfg_trigger.json");
        request.send(JSON.stringify({ timestamp: Date.now() }));

        Qt.quit();
    }
}
