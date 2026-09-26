(function () {
  "use strict";

  var publishableKey = document.body.getAttribute("data-clerk-publishable-key");
  if (!publishableKey) return;

  function loadScript(src, attributes) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.crossOrigin = "anonymous";
      if (attributes) {
        Object.keys(attributes).forEach(function (name) {
          script.setAttribute("data-clerk-" + name.replace(/[A-Z]/g, function (letter) {
            return "-" + letter.toLowerCase();
          }), attributes[name]);
        });
      }
      script.onload = resolve;
      script.onerror = function () {
        reject(new Error("Unable to load Clerk."));
      };
      document.head.appendChild(script);
    });
  }

  function clerkDomainFromPublishableKey(key) {
    var encoded = key.split("_")[2];
    if (!encoded) throw new Error("Invalid Clerk publishable key.");
    return atob(encoded).slice(0, -1);
  }

  async function loadClerk() {
    if (window.Clerk && window.Clerk.loaded) return window.Clerk;

    var domain = clerkDomainFromPublishableKey(publishableKey);

    if (!window.__ssaiClerkUiLoading) {
      window.__ssaiClerkUiLoading = loadScript(
        "https://" + domain + "/npm/@clerk/ui@1/dist/ui.browser.js"
      );
    }
    await window.__ssaiClerkUiLoading;

    if (!window.__ssaiClerkJsLoading) {
      window.__ssaiClerkJsLoading = loadScript(
        "https://" + domain + "/npm/@clerk/clerk-js@6/dist/clerk.browser.js",
        { publishableKey: publishableKey }
      );
    }
    await window.__ssaiClerkJsLoading;

    if (!window.Clerk || typeof window.Clerk.load !== "function") {
      throw new Error("ClerkJS failed to initialize.");
    }

    if (!window.Clerk.loaded) {
      await window.Clerk.load({
        ui: { ClerkUI: window.__internal_ClerkUICtor },
        signInUrl: "/login",
        signUpUrl: "/register",
        appearance: {
          options: {
            socialButtonsPlacement: "top",
          },
        },
      });
    }

    return window.Clerk;
  }

  var googleButton = document.getElementById("clerk-google-button");
  if (googleButton) {
    googleButton.addEventListener("click", async function () {
      googleButton.disabled = true;
      var originalText = googleButton.innerHTML;
      googleButton.innerHTML = "Opening Google sign-in…";

      try {
        var clerk = await loadClerk();
        var next = googleButton.getAttribute("data-next") || "/dashboard";
        var callbackUrl = "/clerk-sync?next=" + encodeURIComponent(next);

        clerk.openSignIn({
          withSignUp: true,
          oauthFlow: "redirect",
          forceRedirectUrl: callbackUrl,
        });
      } catch (error) {
        console.error("Clerk sign-in failed:", error);
        googleButton.disabled = false;
        googleButton.innerHTML = originalText;
        if (typeof showToast === "function") {
          showToast("Google sign-in is temporarily unavailable. You can still use email and password.", "warning");
        }
      }
    });
  }

  var syncPage = document.getElementById("clerk-sync-page");
  if (syncPage) {
    (async function () {
      var status = document.getElementById("clerk-sync-status");
      var next = syncPage.getAttribute("data-next") || "/dashboard";
      var csrf = syncPage.getAttribute("data-csrf-token");

      try {
        status.textContent = "Finishing sign-in…";
        var clerk = await loadClerk();

        if (!clerk.isSignedIn || !clerk.session) {
          throw new Error("No active Clerk session.");
        }

        var token = await clerk.session.getToken();
        if (!token) {
          throw new Error("Unable to obtain a Clerk session token.");
        }

        var response = await fetch("/auth/clerk/sync", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + token,
            "X-CSRF-Token": csrf || "",
            "Accept": "application/json",
          },
        });

        var data = await response.json().catch(function () { return {}; });
        if (!response.ok || !data.ok) {
          throw new Error(data.error || "Unable to create the SSAI session.");
        }

        window.location.replace(next);
      } catch (error) {
        console.error("Clerk session sync failed:", error);
        status.textContent = "We couldn't finish Google sign-in.";
        var retry = document.getElementById("clerk-sync-retry");
        if (retry) retry.hidden = false;
      }
    })();
  }
})();
