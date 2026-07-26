import { Buffer } from "node:buffer";
import { timingSafeEqual } from "node:crypto";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

// Hosts that reach the dev server directly on this machine. Everything else
// arrives through the Cloudflare tunnel, i.e. from the public internet.
const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

function safeEqual(a: string, b: string): boolean {
  const left = Buffer.from(a);
  const right = Buffer.from(b);
  // timingSafeEqual throws on length mismatch, so compare lengths first - the
  // length of a credential is not the secret, its content is.
  return left.length === right.length && timingSafeEqual(left, right);
}

/**
 * HTTP Basic Auth for every request that does not come from localhost.
 *
 * The dev server is published to the internet through the Cloudflare tunnel
 * and brings no authentication of its own, so without this gate anyone who
 * knows the URL can read the whole app. Credentials come from the environment
 * (set in start-apps.bat) and are deliberately never stored in the repo.
 *
 * Local requests stay open so a plain `npm run dev` keeps working. A non-local
 * request with no credentials configured is refused rather than allowed, so a
 * forgotten variable cannot silently expose the app.
 */
function basicAuth(): Plugin {
  return {
    name: "basic-auth",
    configureServer(server) {
      // Added inside configureServer, so this runs before Vite's internal
      // middlewares - including the /api proxy, which must not bypass auth.
      server.middlewares.use((req, res, next) => {
        const hostname = (req.headers.host ?? "").replace(/:\d+$/, "");
        if (LOCAL_HOSTS.has(hostname)) return next();

        const user = process.env.BASIC_AUTH_USER;
        const password = process.env.BASIC_AUTH_PASSWORD;
        if (!user || !password) {
          res.statusCode = 503;
          res.end(
            "BASIC_AUTH_USER / BASIC_AUTH_PASSWORD are not set - refusing non-local request.",
          );
          return;
        }

        const [scheme, encoded] = (req.headers.authorization ?? "").split(" ");
        if (scheme === "Basic" && encoded) {
          const decoded = Buffer.from(encoded, "base64").toString("utf8");
          const separator = decoded.indexOf(":");
          if (
            separator !== -1 &&
            safeEqual(decoded.slice(0, separator), user) &&
            safeEqual(decoded.slice(separator + 1), password)
          ) {
            return next();
          }
        }

        res.statusCode = 401;
        res.setHeader(
          "WWW-Authenticate",
          'Basic realm="Defeaturing Review", charset="UTF-8"',
        );
        res.end("Authentication required");
      });
    },
  };
}

// The dev server proxies API calls to the backend so the browser talks to a
// single origin (no CORS in dev) and the same build works behind a reverse
// proxy in production.
export default defineConfig({
  plugins: [react(), basicAuth()],
  server: {
    port: 5173,
    // Bind IPv4 explicitly. Left at the default, Vite/Node can bind only the
    // IPv6 loopback ([::1]) on some Windows setups, which then refuses plain
    // 127.0.0.1 connections (curl, some browsers/extensions, some proxies).
    host: "127.0.0.1",
    // Allow requests coming through the Cloudflare tunnel (Vite blocks
    // unrecognised Host headers by default as a DNS-rebinding guard).
    allowedHosts: ["defeaturing.felixendress.com"],
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
});
