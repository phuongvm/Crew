(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;
  var React = SDK.React;
  var h = React.createElement;

  function CrewPage() {
    var iframeRef = React.useRef(null);

    React.useEffect(function () {
      function syncTheme() {
        var el = iframeRef.current;
        if (!el) return;
        try {
          var doc = el.contentDocument || (el.contentWindow && el.contentWindow.document);
          if (!doc) return;
          var style = window.getComputedStyle(document.documentElement);
          var bg = style.getPropertyValue("--background-base").trim() || style.getPropertyValue("--background").trim() || "#041c1c";
          var fg = style.getPropertyValue("--foreground-base").trim() || style.getPropertyValue("--foreground").trim() || "#ffffff";
          var existing = doc.getElementById("hermes-theme-sync");
          if (!existing) {
            var s = doc.createElement("style");
            s.id = "hermes-theme-sync";
            doc.head.appendChild(s);
            existing = s;
          }
          existing.textContent = ":root { --crew-bg: " + bg + " !important; --color-background: " + bg + " !important; --crew-fg: " + fg + " !important; } html, body, main#board { background-color: " + bg + " !important; }";
        } catch (err) {}
      }

      var el = iframeRef.current;
      if (el) {
        el.addEventListener("load", syncTheme);
      }
      return function () {
        if (el) {
          el.removeEventListener("load", syncTheme);
        }
      };
    }, []);

    return h("div", {
      style: {
        width: "100%",
        height: "calc(100vh - 3.5rem)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--background, #041c1c)"
      }
    },
      h("iframe", {
        ref: iframeRef,
        src: "/api/plugins/crew/board",
        style: {
          width: "100%",
          height: "100%",
          border: "none",
          flex: 1,
          backgroundColor: "var(--background, #041c1c)"
        },
        title: "Crew Board"
      })
    );
  }

  if (window.__HERMES_PLUGINS__ && window.__HERMES_PLUGINS__.register) {
    window.__HERMES_PLUGINS__.register("crew", CrewPage);
  }
})();
