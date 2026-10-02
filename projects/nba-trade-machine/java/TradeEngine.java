import java.math.*;
import java.nio.file.*;
import java.util.*;
import javax.xml.parsers.*;
import org.w3c.dom.*;

/** Salary/roster checks for a documented subset of the NBA's 2023 CBA. */
public final class TradeEngine {
    public record Rules(String season, long cap, long baseCap, long firstApron, long secondApron,
                        long allowance, long expandedAllowance, int maxRoster) {
        public static Rules load(Path file) throws Exception {
            DocumentBuilderFactory f = DocumentBuilderFactory.newInstance();
            f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            f.setFeature("http://xml.org/sax/features/external-general-entities", false);
            f.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            f.setXIncludeAware(false); f.setExpandEntityReferences(false);
            Element root = f.newDocumentBuilder().parse(file.toFile()).getDocumentElement();
            Rules r = new Rules(root.getAttribute("season"), tag(root,"salaryCap"), tag(root,"baseSalaryCap"),
                tag(root,"firstApron"),tag(root,"secondApron"),tag(root,"standardAllowance"),tag(root,"expandedBaseAllowance"),(int)tag(root,"maxRoster"));
            if (r.cap<=0 || r.baseCap<=0 || r.firstApron<=r.cap || r.secondApron<=r.firstApron || r.allowance<0 || r.maxRoster<1) throw new IllegalArgumentException("Invalid rule configuration");
            return r;
        }
        private static long tag(Element e,String k) { return Long.parseLong(e.getElementsByTagName(k).item(0).getTextContent().trim()); }
    }
    public static long expandedLimit(long outgoing, Rules r) {
        long indexedAllowance = BigDecimal.valueOf(r.expandedAllowance).multiply(BigDecimal.valueOf(r.cap))
            .divide(BigDecimal.valueOf(r.baseCap),0,RoundingMode.DOWN).longValueExact();
        return Math.max(Math.min(2*outgoing+r.allowance,outgoing+indexedAllowance),outgoing*5/4+r.allowance);
    }
    public static Map<String,Object> validate(Map<String,Object> request, Rules r) {
        List<Object> rawTeams = Json.array(request.get("teams")), rawMoves = Json.array(request.get("moves"));
        if (rawTeams.size()<2 || rawTeams.size()>4 || rawMoves.isEmpty() || rawMoves.size()>30) throw new IllegalArgumentException("Use 2-4 teams and 1-30 player moves");
        Map<String,Map<String,Object>> teams = new LinkedHashMap<>(), players = new HashMap<>();
        Map<String,String> owners = new HashMap<>();
        for (Object raw : rawTeams) {
            Map<String,Object> t=Json.object(raw); String id=Json.text(t,"id");
            if (teams.putIfAbsent(id,t)!=null) throw new IllegalArgumentException("Duplicate team " + id);
            Json.text(t,"name"); Json.integer(t,"payroll",0,600_000_000); Json.integer(t,"apronPayroll",0,600_000_000);
            long roster=Json.integer(t,"rosterSize",0,30);
            if (t.get("hardCap")!=null) Json.integer(t,"hardCap",1,600_000_000);
            List<Object> rosterPlayers=Json.array(t.get("players")); long listedSalary=0;
            if (rosterPlayers.size()>roster) throw new IllegalArgumentException("Listed players exceed roster size");
            for (Object x:rosterPlayers) {
                Map<String,Object> p=Json.object(x); String pid=Json.text(p,"id");
                if(players.putIfAbsent(pid,p)!=null) throw new IllegalArgumentException("Duplicate player " + pid);
                listedSalary+=Json.integer(p,"salary",0,100_000_000); owners.put(pid,id);
                if (!(p.get("tradeEligible") instanceof Boolean)) throw new IllegalArgumentException("Missing trade eligibility flag");
            }
            if(listedSalary>Json.integer(t,"payroll",0,600_000_000)) throw new IllegalArgumentException("Listed salaries exceed payroll");
        }
        Map<String,Long> out=new HashMap<>(), in=new HashMap<>(); Map<String,Integer> sent=new HashMap<>(), received=new HashMap<>();
        Set<String> traded=new HashSet<>(); List<String> violations=new ArrayList<>();
        for(Object raw:rawMoves) {
            Map<String,Object> m=Json.object(raw); String pid=Json.text(m,"playerId"), from=Json.text(m,"fromTeam"), to=Json.text(m,"toTeam");
            if(!teams.containsKey(from)||!teams.containsKey(to)||from.equals(to)) throw new IllegalArgumentException("Invalid trade destination");
            if(!from.equals(owners.get(pid))) throw new IllegalArgumentException("Player does not belong to sending team");
            if(!traded.add(pid)) throw new IllegalArgumentException("A player cannot be traded twice");
            Map<String,Object> p=players.get(pid); long salary=Json.integer(p,"salary",0,100_000_000);
            if(!Boolean.TRUE.equals(p.get("tradeEligible"))) violations.add(pid+": contract marked ineligible to trade");
            out.merge(from,salary,Long::sum); in.merge(to,salary,Long::sum); sent.merge(from,1,Integer::sum); received.merge(to,1,Integer::sum);
        }
        List<Object> results=new ArrayList<>();
        for(var entry:teams.entrySet()) {
            String id=entry.getKey(); Map<String,Object> t=entry.getValue();
            long outgoing=out.getOrDefault(id,0L), incoming=in.getOrDefault(id,0L);
            long salary=Json.integer(t,"payroll",0,600_000_000)-outgoing+incoming;
            long apron=Json.integer(t,"apronPayroll",0,600_000_000)-outgoing+incoming;
            int count=sent.getOrDefault(id,0), roster=(int)Json.integer(t,"rosterSize",0,30)-count+received.getOrDefault(id,0);
            long padding=apron>r.firstApron?0:r.allowance;
            long standard=outgoing+padding, room=r.cap+padding;
            long expanded=outgoing>0?expandedLimit(outgoing,r):0;
            List<String> errors=new ArrayList<>(), notes=new ArrayList<>();
            String route="none"; Long triggered=null; long limit;
            if(salary<=room) { route="cap room"; limit=Math.max(0,r.cap-Json.integer(t,"payroll",0,600_000_000)+outgoing+padding); }
            else if(outgoing>0 && incoming<=standard) {
                route=count>1?"aggregated standard exception":"standard exception"; limit=standard;
                if(count>1) { triggered=r.secondApron; if(apron>r.secondApron) errors.add("Aggregated standard exception exceeds second apron"); }
            } else if(outgoing>0 && incoming<=expanded && apron<=r.firstApron) {
                route="expanded exception"; limit=expanded; triggered=r.firstApron;
            } else { limit=apron>r.firstApron?standard:Math.max(standard,expanded); errors.add("Incoming salary exceeds available matching exception or apron constraint"); }
            if(t.get("hardCap")!=null && apron>Json.integer(t,"hardCap",1,600_000_000)) errors.add("Existing hard cap exceeded");
            if(roster>r.maxRoster) errors.add("Projected standard roster exceeds " + r.maxRoster);
            if(roster<14) notes.add("Roster below 14: timing and temporary roster exceptions need separate review");
            if(salary<0 || apron<0 || roster<0) errors.add("Inconsistent payroll or roster input");
            if(count==0 && received.getOrDefault(id,0)==0) notes.add("Team has no player movement");
            Long effective=t.get("hardCap")==null?triggered:Long.valueOf(Json.integer(t,"hardCap",1,600_000_000));
            if(triggered!=null && effective!=null) effective=Math.min(effective,triggered);
            for(String error:errors) violations.add(id+": "+error);
            Map<String,Object> result=new LinkedHashMap<>();
            result.put("teamId",id); result.put("name",t.get("name")); result.put("outgoing",outgoing); result.put("incoming",incoming);
            result.put("projectedPayroll",salary); result.put("projectedApronPayroll",apron); result.put("projectedRosterSize",roster);
            result.put("matchingLimit",limit); result.put("route",route); result.put("effectiveHardCap",effective);
            result.put("errors",errors); result.put("notes",notes); results.add(result);
        }
        return Map.of("validUnderImplementedRules",violations.isEmpty(),"season",r.season,"teams",results,"violations",violations,
            "scope","Salary matching, supplied apron salary, supplied eligibility and roster maximum only; not full CBA certification.");
    }
}
