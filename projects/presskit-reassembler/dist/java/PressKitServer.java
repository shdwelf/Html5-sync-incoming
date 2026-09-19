import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;

/**
 * PressKitServer - a dependency-free local server for the Press Kit Reassembler.
 *
 * The reassembler is a fully client-side HTML5+WebAssembly app (its WASM engine
 * and DOS code skeleton are embedded in the HTML), so this server only has to
 * host the static bundle. It is the runnable, build-a-.jar counterpart of the
 * WAR in dist/war/ (drop that in Tomcat/Jetty for servlet-container deployment).
 *
 *   static/index.html   the app (copied there by build.sh)
 *   static/icon.png     app icon
 *
 * JDK-only (uses com.sun.net.httpserver). Build with build.sh, run:
 *   java -jar presskit-reassembler.jar 8080
 */
public class PressKitServer {

    public static void main(String[] args) throws IOException {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 8080;
        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);
        server.createContext("/", new StaticHandler());
        server.setExecutor(null);
        server.start();
        System.out.println("[PressKitServer] listening on http://0.0.0.0:" + port + "/");
    }

    /** Serves files bundled under /static on the classpath. */
    static class StaticHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange ex) throws IOException {
            String path = ex.getRequestURI().getPath();
            if (path.equals("/") || path.equals("/index.html")) path = "/index.html";
            String resource = "/static" + path;
            InputStream in = PressKitServer.class.getResourceAsStream(resource);
            if (in == null) {
                byte[] notFound = "404 - resource not found".getBytes(StandardCharsets.UTF_8);
                ex.sendResponseHeaders(404, notFound.length);
                try (OutputStream os = ex.getResponseBody()) { os.write(notFound); }
                return;
            }
            byte[] body = in.readAllBytes();
            ex.getResponseHeaders().set("Content-Type", mime(path));
            ex.sendResponseHeaders(200, body.length);
            try (OutputStream os = ex.getResponseBody()) { os.write(body); }
            in.close();
        }

        private static String mime(String path) {
            if (path.endsWith(".html")) return "text/html; charset=utf-8";
            if (path.endsWith(".png")) return "image/png";
            if (path.endsWith(".gif")) return "image/gif";
            if (path.endsWith(".js")) return "application/javascript";
            if (path.endsWith(".css")) return "text/css";
            if (path.endsWith(".wasm")) return "application/wasm";
            return "application/octet-stream";
        }
    }
}
