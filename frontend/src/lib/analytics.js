// Caricamento di Google Analytics e PostHog SOLO dopo consenso esplicito
// (vedi CookieConsentContext) — prima di questo file, entrambi gli script
// partivano incondizionatamente da public/index.html, senza attendere
// alcuna scelta dell'utente.
//
// La registrazione di sessione di PostHog parte comunque SEMPRE disattivata
// all'init: viene riattivata solo sulle pagine pubbliche (AnalyticsRouteGuard
// in App.js), mai dentro /app dove passano dati clienti reali (nomi,
// importi, contenuto documenti, conversazioni con l'assistente AI). Anche
// l'autocapture (che registrerebbe testo/interazioni cliccate ovunque) resta
// disattivato ovunque, non solo in /app: il valore che aggiungerebbe non
// giustifica il rischio di catturare per sbaglio un dato sensibile.

const GA_MEASUREMENT_ID = "G-19R9YNHMSP";
const POSTHOG_KEY = "phc_xAvL2Iq4tFmANRE7kzbKwaSqp1HJjN7x48s3vr0CMjs";
const POSTHOG_HOST = "https://us.i.posthog.com";

let googleAnalyticsLoaded = false;
let postHogLoaded = false;

export function loadGoogleAnalytics() {
  if (googleAnalyticsLoaded || typeof window === "undefined") return;
  googleAnalyticsLoaded = true;

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() {
    window.dataLayer.push(arguments);
  };
  window.gtag("js", new Date());
  window.gtag("config", GA_MEASUREMENT_ID);
}

export function loadPostHog() {
  if (postHogLoaded || typeof window === "undefined") return;
  postHogLoaded = true;

  // Snippet ufficiale PostHog (invariato rispetto a quello prima incollato
  // in public/index.html), solo spostato in una funzione richiamabile a
  // consenso dato invece che eseguito subito al caricamento della pagina.
  /* eslint-disable */
  !(function (t, e) {
    var o, n, p, r;
    e.__SV ||
      ((window.posthog = e),
      (e._i = []),
      (e.init = function (i, s, a) {
        function g(t, e) {
          var o = e.split(".");
          2 == o.length && ((t = t[o[0]]), (e = o[1])),
            (t[e] = function () {
              t.push([e].concat(Array.prototype.slice.call(arguments, 0)));
            });
        }
        ((p = t.createElement("script")).type = "text/javascript"),
          (p.crossOrigin = "anonymous"),
          (p.async = !0),
          (p.src = s.api_host.replace(".i.posthog.com", "-assets.i.posthog.com") + "/static/array.js"),
          (r = t.getElementsByTagName("script")[0]).parentNode.insertBefore(p, r);
        var u = e;
        for (
          void 0 !== a ? (u = e[a] = []) : (a = "posthog"),
            u.people = u.people || [],
            u.toString = function (t) {
              var e = "posthog";
              return "posthog" !== a && (e += "." + a), t || (e += " (stub)"), e;
            },
            u.people.toString = function () {
              return u.toString(1) + ".people (stub)";
            },
            o =
              "init me ws ys ps bs capture je Di ks register register_once register_for_session unregister unregister_for_session Ps getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveysLoaded onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey canRenderSurveyAsync identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty Es $s createPersonProfile Is opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing Ss debug xs getPageViewId captureTraceFeedback captureTraceMetric".split(
                " ",
              ),
            n = 0;
          n < o.length;
          n++
        )
          g(u, o[n]);
        e._i.push([i, s, a]);
      }),
      (e.__SV = 1));
  })(document, window.posthog || []);
  /* eslint-enable */

  window.posthog.init(POSTHOG_KEY, {
    api_host: POSTHOG_HOST,
    person_profiles: "identified_only",
    autocapture: false,
    session_recording: {
      recordCrossOriginIframes: false,
      capturePerformance: false,
      // Maschera il contenuto di ogni <input>/<textarea> nelle registrazioni
      // (nome/email/telefono/messaggio nei form pubblici): la registrazione
      // stessa gira comunque solo sulle pagine pubbliche, mai in /app, ma
      // resta comunque un dato digitato dall'utente da non catturare in chiaro.
      maskAllInputs: true,
    },
  });
  // Stato iniziale coerente con la pagina su cui ci si trova AL MOMENTO in
  // cui il consenso viene dato (non sempre "/": si può accettare da
  // qualunque pagina pubblica). Impostato qui direttamente — non solo
  // affidandosi ad AnalyticsRouteGuard, il cui effect potrebbe eseguire
  // prima che window.posthog esista ancora, a seconda dell'ordine di
  // commit degli effect React — che resta comunque responsabile di
  // mantenerlo corretto sui cambi di rotta successivi.
  setSessionRecordingEnabled(!window.location.pathname.startsWith("/app"));
}

export function setSessionRecordingEnabled(enabled) {
  if (typeof window === "undefined" || !window.posthog) return;
  if (enabled) window.posthog.startSessionRecording();
  else window.posthog.stopSessionRecording();
}

export function optOutPostHog() {
  if (typeof window !== "undefined" && window.posthog) {
    window.posthog.opt_out_capturing();
  }
}
