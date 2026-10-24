import QtQuick
import QtWebView

WebView {
    function evaluate(script, callback) {
        runJavaScript(script, function(value) {
            // Native WebView2 may return a JSON-encoded result.
            if (typeof value === 'string') {
                try { value = JSON.parse(value); } catch (_) {}
            }
            callback(value);
        });
    }
}
