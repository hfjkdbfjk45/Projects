import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Paired Monte Carlo race-time comparison with synthetic, explicitly configurable pace assumptions. */
public final class RaceSimulator {
    record Tyre(String name, double offset, double degradation, int life) {}
    record Strategy(String name, List<Tyre> tyres, List<Integer> stops) {}
    static final Tyre SOFT=new Tyre("SOFT",-1.0,0.055,18), MEDIUM=new Tyre("MEDIUM",0,0.035,28), HARD=new Tyre("HARD",0.65,0.021,40), INTER=new Tyre("INTERMEDIATE",5.0,0.025,35);
    public static Map<String,Object> simulate(Map<String,Object> input) {
        int laps=(int)Json.integer(input,"laps",20,80), runs=(int)Json.integer(input,"runs",100,20000);
        long seed=Json.integer(input,"seed",0,2147483647);
        double rain=number(input,"rainProbability",0,1), pitLoss=number(input,"pitLoss",10,45);
        List<Strategy> strategies=List.of(
            new Strategy("Medium / Hard - early",List.of(MEDIUM,HARD),List.of((int)Math.round(laps*.34))),
            new Strategy("Medium / Hard - balanced",List.of(MEDIUM,HARD),List.of((int)Math.round(laps*.44))),
            new Strategy("Medium / Hard - late",List.of(MEDIUM,HARD),List.of((int)Math.round(laps*.54))),
            new Strategy("Soft / Medium / Hard",List.of(SOFT,MEDIUM,HARD),List.of((int)Math.round(laps*.25),(int)Math.round(laps*.60)))
        );
        double[][] times=new double[strategies.size()][runs]; double[] wins=new double[strategies.size()];
        Random rng=new Random(seed);
        for(int run=0;run<runs;run++) {
            int rainLap=rng.nextDouble()<rain?5+rng.nextInt(laps-9):laps+1;
            double[] noise=new double[laps]; for(int i=0;i<laps;i++) noise[i]=rng.nextGaussian()*.35;
            double pitNoise=rng.nextGaussian()*.75, paceNoise=rng.nextGaussian()*.2;
            int best=0;
            for(int s=0;s<strategies.size();s++) {
                times[s][run]=race(strategies.get(s),laps,rainLap,noise,pitLoss+pitNoise,paceNoise,null);
                if(times[s][run]<times[best][run]) best=s;
            }
            int tied=0;for(int s=0;s<strategies.size();s++) if(Math.abs(times[s][run]-times[best][run])<1e-9)tied++;
            for(int s=0;s<strategies.size();s++) if(Math.abs(times[s][run]-times[best][run])<1e-9)wins[s]+=1.0/tied;
        }
        List<Object> result=new ArrayList<>();
        for(int s=0;s<strategies.size();s++) {
            double[] sorted=times[s].clone(); Arrays.sort(sorted); double mean=Arrays.stream(sorted).average().orElseThrow();
            double sum=0; for(double x:sorted) sum+=(x-mean)*(x-mean); double sd=Math.sqrt(sum/(runs-1));
            Map<String,Object> row=new LinkedHashMap<>(); row.put("strategy",strategies.get(s).name); row.put("meanSeconds",round(mean));
            row.put("p10Seconds",round(quantile(sorted,.1))); row.put("p90Seconds",round(quantile(sorted,.9))); row.put("standardDeviation",round(sd));
            row.put("meanStandardError",round(sd/Math.sqrt(runs))); row.put("winProbability",wins[s]/(double)runs);
            row.put("pitLaps",strategies.get(s).stops); result.add(row);
        }
        result.sort(Comparator.comparingDouble(o->((Number)Json.object(o).get("meanSeconds")).doubleValue()));
        List<Object> trace=new ArrayList<>();
        for(Strategy s:strategies) race(s,laps,laps+1,new double[laps],pitLoss,0,trace);
        return Map.of("runsPerStrategy",runs,"laps",laps,"seed",seed,"rainProbability",rain,"pitLoss",pitLoss,"results",result,
            "lapTrace",trace,"dataSource","synthetic pace and tyre assumptions; no real-race calibration",
            "modelNotes","Common random scenarios compare race time, not finishing position. Rain persists; every strategy adapts to intermediates.");
    }
    private static double race(Strategy s,int laps,int rainLap,double[] noise,double pitLoss,double paceNoise,List<Object> trace) {
        int stint=0,age=0,stops=0; double total=0; Tyre tyre=s.tyres.get(0);
        for(int lap=1;lap<=laps;lap++) {
            boolean pit=false;
            // Scheduled stops occur before this lap. Once rain begins, dry stops are cancelled.
            if(lap==rainLap) {tyre=INTER;age=0;pit=true;stops++;}
            else if(lap<rainLap && s.stops.contains(lap)) {stint++;tyre=s.tyres.get(stint);age=0;pit=true;stops++;}
            double fuel=Math.max(0,110.0*(1-(lap-1)/(double)laps));
            double wear=tyre.degradation*age+Math.max(0,age-tyre.life)*.25;
            double duration=90+tyre.offset+wear+.03*fuel+noise[lap-1]+paceNoise+(pit?pitLoss:0);
            total+=duration;
            if(trace!=null) trace.add(Map.of("strategy",s.name,"lap",lap,"compound",tyre.name,"tyreAge",age,"fuelKg",round(fuel),"lapSeconds",round(duration),"pit",pit,"cumulativeSeconds",round(total)));
            age++;
        }
        return total;
    }
    private static double number(Map<String,Object> m,String k,double min,double max) {
        if(!(m.get(k) instanceof Number n)||!Double.isFinite(n.doubleValue())||n.doubleValue()<min||n.doubleValue()>max) throw new IllegalArgumentException("Invalid "+k);
        return n.doubleValue();
    }
    private static double round(double x) {return Math.round(x*1000)/1000.0;}
    private static double quantile(double[] a,double p) {double n=p*(a.length-1);int i=(int)n;return a[i]+(a[Math.min(i+1,a.length-1)]-a[i])*(n-i);}
    static void export(Map<String,Object> result,Path dir) throws IOException {
        Files.createDirectories(dir);
        try(var w=Files.newBufferedWriter(dir.resolve("strategy_results.csv"))) {
            w.write("strategy,mean_seconds,p10_seconds,p90_seconds,win_probability\n");
            for(Object raw:Json.array(result.get("results"))) {var r=Json.object(raw);w.write(r.get("strategy")+","+r.get("meanSeconds")+","+r.get("p10Seconds")+","+r.get("p90Seconds")+","+r.get("winProbability")+"\n");}
        }
        try(var w=Files.newBufferedWriter(dir.resolve("lap_trace.csv"))) {
            w.write("strategy,lap,compound,tyre_age,fuel_kg,lap_seconds,pit,cumulative_seconds\n");
            for(Object raw:Json.array(result.get("lapTrace"))) {var r=Json.object(raw);w.write(r.get("strategy")+","+r.get("lap")+","+r.get("compound")+","+r.get("tyreAge")+","+r.get("fuelKg")+","+r.get("lapSeconds")+","+r.get("pit")+","+r.get("cumulativeSeconds")+"\n");}
        }
        Files.writeString(dir.resolve("simulation.json"),Json.write(result));
    }
    public static void main(String[] args) throws Exception {
        try {
            String text=new String(System.in.readNBytes(8193),StandardCharsets.UTF_8);
            if(text.length()>8192) throw new IllegalArgumentException("Request too large");
            Map<String,Object> request=text.isBlank()?Map.of("laps",57,"runs",1000,"seed",42,"rainProbability",.25,"pitLoss",22):Json.object(Json.parse(text));
            var result=simulate(request); if(args.length==2&&args[0].equals("--export")) export(result,Path.of(args[1]));
            System.out.println(Json.write(result));
        } catch(IllegalArgumentException e) {System.err.println(e.getMessage());System.exit(2);}
    }
}
