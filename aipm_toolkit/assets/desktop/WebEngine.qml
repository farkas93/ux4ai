import QtQuick
import QtWebEngine

WebEngineView {
    WebEngineProfilePrototype {
        id: localProfile
        storageName: "AIProductToolkit"
        cachePath: profileCachePath
        persistentStoragePath: profileStoragePath
        persistentCookiesPolicy: WebEngineProfile.NoPersistentCookies
    }
    profile: localProfile.instance()
    function evaluate(script, callback) { runJavaScript(script, callback); }
}
