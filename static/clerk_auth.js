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

  async function refreshActiveSession(clerk) {
    if (clerk.isSignedIn && clerk.session) return clerk.session;

    // OAuth can finish in another window before this Clerk instance has
    // refreshed its client resource. Reload it before declaring the session
    // missing.
    if (clerk.client && typeof clerk.client.reload === "function") {
      try {
        await clerk.client.reload();
      } catch (error) {
        console.warn("Clerk client reload failed:", error);
      }
    }

    if (clerk.isSignedIn && clerk.session) return clerk.session;

    var client = clerk.client;
    if (!client) return null;

    // If Clerk created a signed-in session but did not select it as active,
    // explicitly select the newest completed session. This is especially
    // important when returning from OAuth in a popup/redirect flow.
    var sessions = client.signedInSessions || [];
    var candidate = null;

    if (client.lastActiveSessionId) {
      candidate = sessions.find(function (session) {
        return session.id === client.lastActiveSessionId;
      }) || null;
    }

    if (!candidate && sessions.length) {
      candidate = sessions[sessions.length - 1];
    }

    if (!candidate) return null;

    try {
      await clerk.setActive({ session: candidate });
      return clerk.session || candidate;
    } catch (error) {
      console.warn("Unable to activate Clerk session:", error);
      return null;
    }
  }

  async function getSessionTokenWithRetry(clerk) {
    var attempts = 12;

    for (var attempt = 0; attempt < attempts; attempt += 1) {
      var session = await refreshActiveSession(clerk);
      if (session) {
        try {
          var token = await session.getToken({ skipCache: attempt > 0 });
          if (token) return token;
        } catch (error) {
          console.warn("Clerk session token attempt failed:", error);
        }
      }

      if (attempt < attempts - 1) {
        await wait(500);
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
        var pollTimer = null;
        var pollStartedAt = Date.now();

        async function finishWithSession() {
          if (syncing) return;
          var session = await refreshActiveSession(clerk);
          if (!session) return;

          syncing = true;
          if (unsubscribe) unsubscribe();
          if (pollTimer) window.clearInterval(pollTimer);
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

        unsubscribe = clerk.addListener(function (emission) {
          if (emission && emission.session) {
            finishWithSession();
          }
        }, { skipInitialEmit: true });

        if (clerk.isSignedIn && clerk.session) {
          await finishWithSession();
          return;
        }

        // Keep checking the Clerk client while the OAuth popup is open. This
        // covers browsers where the popup completes authentication but the
        // parent window receives the client/session update slightly later.
        pollTimer = window.setInterval(function () {
          if (Date.now() - pollStartedAt > 30000) {
            window.clearInterval(pollTimer);
            pollTimer = null;
            return;
          }
          finishWithSession();
        }, 750);

        if (authMode === "register") {
          clerk.openSignUp({
            oauthFlow: "popup",
            transferable: false,
            signInUrl: window.location.origin + "/login",
            forceRedirectUrl: window.location.origin + "/clerk-sync?next=" + encodeURIComponent(next),
          });
        } else {
          clerk.openSignIn({
            withSignUp: true,
            transferable: false,
            oauthFlow: "popup",
            signUpUrl: window.location.origin + "/register",
            forceRedirectUrl: window.location.origin + "/clerk-sync?next=" + encodeURIComponent(next),
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

      try {
        status.textContent = "Checking your Clerk session…";
        var clerk = await loadClerk();
        var token = await getSessionTokenWithRetry(clerk);
        if (!token) {
          throw new Error("Clerk session is not signed in.");
        }

        var response = await fetch("/auth/clerk/sync", {
          method: "POST",
          headers: {
            "Authorization": "Bearer " + token,
            "X-CSRF-Token": syncPage.getAttribute("data-csrf-token") || "",
            "Accept": "application/json",
          },
        });
        var data = await response.json().catch(function () { return {}; });
        if (!response.ok || !data.ok) {
          throw new Error(data.error || "Unable to create the SSAI session.");
        }

        window.location.replace(data.has_transactions ? next : "/get-started");
      } catch (error) {
        console.error("Clerk session sync failed:", error);
        status.textContent = "We couldn't finish Google sign-in.";
        var retry = document.getElementById("clerk-sync-retry");
        if (retry) retry.hidden = false;
      }
    })();
  }
})();
