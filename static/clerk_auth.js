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

    // OAuth can finish before this Clerk instance has refreshed its client.
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
      credentials: "same-origin",
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

        // Use Clerk's full-page OAuth redirect instead of a popup. This makes
        // the OAuth callback and the __session cookie land in the same browser
        // context that will perform the SSAI sync, avoiding popup/session races.
        if (authMode === "register") {
          clerk.openSignUp({
            oauthFlow: "redirect",
            transferable: false,
            signInUrl: window.location.origin + "/login",
            forceRedirectUrl: window.location.origin + "/clerk-sync?next=" + encodeURIComponent(next),
          });
        } else {
          clerk.openSignIn({
            withSignUp: true,
            transferable: false,
            oauthFlow: "redirect",
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
      var csrfToken = syncPage.getAttribute("data-csrf-token") || "";

      async function syncUsingCookie() {
        // On the same origin Clerk sends the __session cookie automatically.
        // Prefer this path on the callback page: it removes the dependency on
        // ClerkJS having already exposed the new session to JavaScript.
        var response = await fetch("/auth/clerk/sync", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRF-Token": csrfToken,
            "Accept": "application/json",
          },
        });
        var data = await response.json().catch(function () { return {}; });
        return { response: response, data: data };
      }

      async function syncUsingBearer(clerk) {
        var token = await getSessionTokenWithRetry(clerk);
        if (!token) return null;

        var response = await fetch("/auth/clerk/sync", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Authorization": "Bearer " + token,
            "X-CSRF-Token": csrfToken,
            "Accept": "application/json",
          },
        });
        var data = await response.json().catch(function () { return {}; });
        return { response: response, data: data };
      }

      try {
        status.textContent = "Checking your Clerk session…";

        // First allow the browser/Clerk handshake a short window to establish
        // the same-origin __session cookie, then authenticate server-side.
        for (var attempt = 0; attempt < 8; attempt += 1) {
          var cookieResult = await syncUsingCookie();
          if (cookieResult.response.ok && cookieResult.data.ok) {
            window.location.replace(cookieResult.data.has_transactions ? next : "/get-started");
            return;
          }

          if (cookieResult.response.status !== 401) {
            throw new Error(cookieResult.data.error || "Unable to create the SSAI session.");
          }

          if (attempt < 7) await wait(500);
        }

        // Fallback for browsers where Clerk's callback cookie is not yet
        // visible to the backend: obtain the session token from ClerkJS and
        // send it explicitly.
        var clerk = await loadClerk();
        var bearerResult = await syncUsingBearer(clerk);
        if (bearerResult && bearerResult.response.ok && bearerResult.data.ok) {
          window.location.replace(bearerResult.data.has_transactions ? next : "/get-started");
          return;
        }

        throw new Error(
          (bearerResult && bearerResult.data && bearerResult.data.error) ||
          "Clerk session is not signed in."
        );
      } catch (error) {
        console.error("Clerk session sync failed:", error);
        status.textContent = "We couldn't finish Google sign-in.";
        var retry = document.getElementById("clerk-sync-retry");
        if (retry) retry.hidden = false;
      }
    })();
  }
})();
