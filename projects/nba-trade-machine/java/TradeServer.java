import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import com.sun.net.httpserver.*;

public final class TradeServer {
    public static void main(String[] args) throws Exception {
        Path root=Path.of(args.length>1?args[1]:".").toAbsolutePath();
        var rules=TradeEngine.Rules.load(root.resolve("projects/nba-trade-machine/config/rules.xml"));
        if(args.length>0 && args[0].equals("validate")) {
            try { System.out.println(Json.write(TradeEngine.validate(Json.object(Json.parse(new String(System.in.readNBytes(65537),StandardCharsets.UTF_8))),rules))); }
            catch(IllegalArgumentException e) { System.err.println(e.getMessage()); System.exit(2); }
            return;
        }
        int port=args.length>2?Integer.parseInt(args[2]):8081;
        String bind=System.getenv().getOrDefault("JAVA_BIND","127.0.0.1");
        HttpServer server=HttpServer.create(new InetSocketAddress(bind,port),0);
        server.createContext("/health",x->respond(x,200,Map.of("status","ok","engine","java","season",rules.season())));
        server.createContext("/api/sample",x->{try {respond(x,200,Json.parse(Files.readString(root.resolve("projects/nba-trade-machine/data/sample-trade.json"))));} catch(Exception e){respond(x,500,Map.of("error","Unable to load fixture"));}});
        server.createContext("/api/validate",x->{
            if(!x.getRequestMethod().equals("POST")) {respond(x,405,Map.of("error","POST required"));return;}
            try {
                byte[] body=x.getRequestBody().readNBytes(65537);
                if(body.length>65536){respond(x,413,Map.of("error","Request too large"));return;}
                respond(x,200,TradeEngine.validate(Json.object(Json.parse(new String(body,StandardCharsets.UTF_8))),rules));
            } catch(IllegalArgumentException e){respond(x,400,Map.of("error",e.getMessage()));}
            catch(Exception e){respond(x,500,Map.of("error","Validation failed"));}
        });
        server.setExecutor(Executors.newFixedThreadPool(4)); server.start();
        System.err.println("NBA Java engine listening at http://127.0.0.1:"+port);
    }
    private static void respond(HttpExchange x,int status,Object body) throws IOException {
        byte[] bytes=Json.write(body).getBytes(StandardCharsets.UTF_8);
        x.getResponseHeaders().set("Content-Type","application/json; charset=utf-8");
        x.sendResponseHeaders(status,bytes.length); try(var stream=x.getResponseBody()){stream.write(bytes);}
    }
}
