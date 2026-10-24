import QtQuick
import QtQuick.Window

Window {
    id: window
    width: 1440
    height: 960
    minimumWidth: 800
    minimumHeight: 600
    title: "AI Product Toolkit"
    visible: true
    color: "#f3f6fa"
    property bool shutdownAllowed: false
    signal closeRequested()
    signal saveUnavailable()
    signal readyChecked(bool ready)
    signal sectionChecked(bool ready)

    onClosing: function(event) {
        if (!shutdownAllowed) {
            event.accepted = false;
            closeRequested();
        }
    }

    Loader {
        id: browser
        anchors.fill: parent
        source: rendererFile
        onLoaded: item.url = initialUrl
    }

    function requestSave() {
        if (!browser.item) { saveUnavailable(); return; }
        browser.item.evaluate(saveScript, function(found) {
            if (!found) window.saveUnavailable();
        });
    }

    function checkReady() {
        if (!browser.item) return;
        const script = "(() => { const page = document.getElementById('page-project-setup'); return !!page && page.getBoundingClientRect().width > 0; })()";
        browser.item.evaluate(script, function(ready) { window.readyChecked(!!ready); });
    }

    function checkSection(name, pageId, needsGraph) {
        if (!browser.item) { sectionChecked(false); return; }
        const script = "(() => { const name = " + JSON.stringify(name) +
            "; const radio = [...document.querySelectorAll('#toolkit-desktop-section input[type=radio]')].find(input => input.value === name);" +
            "if (!radio) return false; if (!radio.checked) { radio.click(); return false; }" +
            "const page = document.getElementById(" + JSON.stringify(pageId) + ");" +
            "return !!page && page.getBoundingClientRect().width > 0 && (!" +
            JSON.stringify(needsGraph) + " || !!page.querySelector('.js-plotly-plot svg')); })()";
        browser.item.evaluate(script, function(ready) { window.sectionChecked(!!ready); });
    }
}
