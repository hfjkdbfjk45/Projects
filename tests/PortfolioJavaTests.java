import java.nio.file.*;
import java.util.*;

public final class PortfolioJavaTests {
    static int checks=0;
    static void check(boolean ok,String message) {checks++;if(!ok)throw new AssertionError(message);}
    static Map<String,Object> copy(Map<String,Object> m){return Json.object(Json.parse(Json.write(m)));}
    static void rejects(Runnable fn,String label) {try{fn.run();throw new AssertionError("Expected rejection: "+label);}catch(IllegalArgumentException expected){checks++;}}
    public static void main(String[] args) throws Exception {
        Path root=Path.of(args.length>0?args[0]:".");
        var r=TradeEngine.Rules.load(root.resolve("projects/nba-trade-machine/config/rules.xml"));
        var sample=Json.object(Json.parse(Files.readString(root.resolve("projects/nba-trade-machine/data/sample-trade.json"))));
        var result=TradeEngine.validate(sample,r);
        check(Boolean.TRUE.equals(result.get("validUnderImplementedRules")),"Sample salary-matching trade passes");
        var cle=Json.object(Json.array(result.get("teams")).get(0));
        check(cle.get("effectiveHardCap").equals(r.firstApron()),"Expanded exception triggers first-apron hard cap");
        check(cle.get("matchingLimit").equals(25_751_817L),"Indexed matching allowance uses cap ratio and integer dollars");
        var invalid=copy(sample);var team=Json.object(Json.array(invalid.get("teams")).get(0));
        team.put("payroll",180_000_000L);team.put("apronPayroll",180_000_000L);
        check(Boolean.FALSE.equals(TradeEngine.validate(invalid,r).get("validUnderImplementedRules")),"Cannot use expanded matching above first apron");
        invalid=copy(sample);team=Json.object(Json.array(invalid.get("teams")).get(0));team.put("hardCap",164_000_000L);
        check(Boolean.FALSE.equals(TradeEngine.validate(invalid,r).get("validUnderImplementedRules")),"Existing hard cap checked against projected apron payroll");
        invalid=copy(sample);team=Json.object(Json.array(invalid.get("teams")).get(1));team.put("rosterSize",15);
        Json.array(invalid.get("moves")).remove(1);
        check(Boolean.FALSE.equals(TradeEngine.validate(invalid,r).get("validUnderImplementedRules")),"Roster cannot exceed 15");
        invalid=copy(sample);team=Json.object(Json.array(invalid.get("teams")).get(0));
        Json.object(Json.array(team.get("players")).get(0)).put("tradeEligible",false);
        check(Boolean.FALSE.equals(TradeEngine.validate(invalid,r).get("validUnderImplementedRules")),"Eligibility flag enforced");
        final var duplicate=copy(sample);Json.array(duplicate.get("moves")).add(Json.array(duplicate.get("moves")).get(0));
        rejects(()->TradeEngine.validate(duplicate,r),"Repeated player");
        final var negative=copy(sample);Json.object(Json.array(negative.get("teams")).get(0)).put("payroll",-1L);
        rejects(()->TradeEngine.validate(negative,r),"Negative payroll");
        final var fractional=copy(sample);Json.object(Json.array(fractional.get("teams")).get(0)).put("payroll",140000000.5);
        rejects(()->TradeEngine.validate(fractional,r),"Fractional dollars rejected");
        rejects(()->Json.parse("{\"x\":1,\"x\":2}"),"Duplicate JSON keys");
        rejects(()->Json.parse("[1,]"),"Malformed JSON");
        check(Json.parse(Json.write(Map.of("quote","line\n\"value\"","number",42L))).equals(Map.of("quote","line\n\"value\"","number",42L)),"JSON escaping round trip");
        var aggregate=copy(sample);team=Json.object(Json.array(aggregate.get("teams")).get(0));
        team.put("payroll",200_000_000L);team.put("apronPayroll",200_000_000L);
        Json.array(aggregate.get("moves")).add(Map.of("playerId","cle-2","fromTeam","CLE","toTeam","NYC"));
        check(Boolean.FALSE.equals(TradeEngine.validate(aggregate,r).get("validUnderImplementedRules")),"Aggregated standard exception prohibited above second apron");
        var request=new LinkedHashMap<String,Object>(Map.of("laps",57L,"runs",300L,"seed",42L,"rainProbability",0.25,"pitLoss",22.0));
        var a=RaceSimulator.simulate(request);var b=RaceSimulator.simulate(request);
        check(a.equals(b),"Seeded Monte Carlo reproducible");
        double winSum=0;
        for(Object raw:Json.array(a.get("results"))) {
            var row=Json.object(raw);double p10=((Number)row.get("p10Seconds")).doubleValue(),mean=((Number)row.get("meanSeconds")).doubleValue(),p90=((Number)row.get("p90Seconds")).doubleValue();
            check(p10>0&&p10<=p90&&Double.isFinite(mean),"Finite ordered race-time distribution");
            winSum+=((Number)row.get("winProbability")).doubleValue();
        }
        check(Math.abs(winSum-1)<1e-10,"Lowest-time shares sum to one over paired scenarios");
        check(Json.array(a.get("lapTrace")).size()==4*57,"Every strategy has a complete dry-race trace");
        final var badRain=new LinkedHashMap<>(request);badRain.put("rainProbability",1.1);
        rejects(()->RaceSimulator.simulate(badRain),"Invalid rain probability");
        request.put("rainProbability",0.0);var dry=RaceSimulator.simulate(request);request.put("pitLoss",32.0);var slower=RaceSimulator.simulate(request);
        Map<String,Double> oldMeans=new HashMap<>();for(Object raw:Json.array(dry.get("results"))){var row=Json.object(raw);oldMeans.put((String)row.get("strategy"),((Number)row.get("meanSeconds")).doubleValue());}
        for(Object raw:Json.array(slower.get("results"))) {
            var row=Json.object(raw);int stops=Json.array(row.get("pitLaps")).size();
            check(Math.abs(((Number)row.get("meanSeconds")).doubleValue()-oldMeans.get(row.get("strategy"))-10*stops)<.01,"Added pit loss changes race time by the number of scheduled stops");
        }
        System.out.println("Java checks passed: "+checks);
    }
}
