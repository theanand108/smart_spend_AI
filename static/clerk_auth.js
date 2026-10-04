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

  function wait(milliseconds) {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, milliseconds);
    });
  }

  async function getSessionTokenWithRetry(clerk) {
    var attempts = 8;

    for (var attempt = 0; attempt < attempts; attempt += 1) {
      if (clerk.isSignedIn && clerk.session) {
        try {
          var token = await clerk.session.getToken({ skipCache: attempt > 0 });
          if (token) return token;
        } catch (error) {
          console.warn("Clerk session token attempt failed:", error);
        }
      }

      if (attempt < attempts - 1) {
        await wait(400);
      }
    }

    return null;
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
        signInUrl: window.location.origin + "/login",
        signUpUrl: window.location.origin + "/register",
        appearance: {
          options: {
            socialButtonsPlacement: "top",
          },
        },
      });
    }

    return window.Clerk;
  }

  async function syncCurrentClerkSession(clerk, next) {
    var token = await getSessionTokenWithRetry(clerk);
    if (!token) {
      throw new Error("Unable to obtain the Clerk session token.");
    }

    var response = await fetch("/auth/clerk/sync", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + token,
        "X-CSRF-Token": (document.querySelector('input[name="_csrf_token"]') || {}).value || "",
        "Accept": "application/json",
      },
    });

    var data = await response.json().catch(function () { return {}; });
    if (!response.ok || !data.ok) {
      throw new Error(data.error || "Unable to create the SSAI session.");
    }

    var destination = data.has_transactions ? next : "/get-started";
    window.location.replace(destination);
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
        var authMode = googleButton.getAttribute("data-auth-mode") || "login";
        var syncing = false;
        var unsubscribe = null;

        async function finishWithSession() {
          if (syncing || !clerk.isSignedIn || !clerk.session) return;
          syncing = true;
          if (unsubscribe) unsubscribe();
          googleButton.innerHTML = "Finishing sign-in…";

          try {
            await syncCurrentClerkSession(clerk, next);
          } catch (error) {
            console.error("Clerk session sync failed:", error);
            syncing = false;
            googleButton.disabled = false;
            googleButton.innerHTML = originalText;
            if (typeof showToast === "function") {
              showToast(error.message || "Unable to finish sign-in.", "warning");
            }
          }
        }

        // Do not redirect to /clerk-sync after OAuth. Keeping the OAuth flow
        // in the originating page lets Clerk establish the session in the
        // same browser context before we exchange its token with our backend.
        unsubscribe = clerk.addListener(function (emission) {
          if (emission && emission.session) {
            finishWithSession();
          }
        }, { skipInitialEmit: true });

        // This also handles a user who is already signed into Clerk but not
        // yet signed into the SSAI application.
        if (clerk.isSignedIn && clerk.session) {
          await finishWithSession();
          return;
        }

        if (authMode === "register") {
          clerk.openSignUp({
            oauthFlow: "popup",
            transferable: false,
          });
        } else {
          clerk.openSignIn({
            withSignUp: true,
            transferable: false,
            oauthFlow: "popup",
          });
        }
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

      // Backward-compatible handler for any old redirect links. New Google
      // flows no longer depend on this page for the OAuth session handoff.
      try {
        status.textContent = "Checking your Clerk session…";
        var clerk = await loadClerk();
        if (!clerk.isSignedIn || !clerk.session) {
          throw new Error("Clerk session is not signed in.");
        }

        await syncCurrentClerkSession(clerk, next);
      } catch (error) {
        console.error("Clerk session sync failed:", error);
        status.textContent = "We couldn't finish Google sign-in.";
        var retry = document.getElementById("clerk-sync-retry");
        if (retry) retry.hidden = false;
      }
    })();
  }
})();
