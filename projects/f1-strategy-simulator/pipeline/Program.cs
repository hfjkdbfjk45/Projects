using System.Globalization;
using System.Text.Json;

// Public historical OpenF1 data. Offline fixtures exercise the same normalization path.
var options = new Dictionary<string, string>();
for (var i=0;i<args.Length;i+=2) {
    if (i+1>=args.Length || !new[]{"--fixture","--session","--output"}.Contains(args[i])) throw new ArgumentException("Use --fixture PATH or --session INTEGER and --output PATH");
    options.Add(args[i],args[i+1]);
}
var output=options.GetValueOrDefault("--output","output/f1-telemetry");
var endpoints=new[]{"laps","stints","pit","weather"};
var data=new Dictionary<string, JsonElement[]>();
if(options.TryGetValue("--fixture",out var fixture)) {
    using var doc=JsonDocument.Parse(await File.ReadAllTextAsync(fixture));
    foreach(var endpoint in endpoints) data[endpoint]=doc.RootElement.GetProperty(endpoint).EnumerateArray().Select(x=>x.Clone()).ToArray();
} else {
    if(!options.TryGetValue("--session",out var session)||!int.TryParse(session,out var key)||key<=0) throw new ArgumentException("A positive historical --session key is required");
    using var client=new HttpClient{Timeout=TimeSpan.FromSeconds(45)};
    client.DefaultRequestHeaders.UserAgent.ParseAdd("SportsAnalyticsPortfolio/1.0");
    foreach(var endpoint in endpoints) {
        JsonElement[]? rows=null;
        for(var retry=0;retry<4;retry++) {
            using var response=await client.GetAsync($"https://api.openf1.org/v1/{endpoint}?session_key={key}");
            if((int)response.StatusCode==429 || (int)response.StatusCode>=500) {await Task.Delay(1000*(retry+1));continue;}
            response.EnsureSuccessStatusCode();
            using var doc=JsonDocument.Parse(await response.Content.ReadAsStringAsync());
            rows=doc.RootElement.EnumerateArray().Select(x=>x.Clone()).ToArray();break;
        }
        data[endpoint]=rows ?? throw new IOException($"OpenF1 {endpoint} failed after retries");
        await Task.Delay(400);
    }
}
double? Number(JsonElement e,string k) => e.TryGetProperty(k,out var v)&&v.ValueKind==JsonValueKind.Number&&v.TryGetDouble(out var n)?n:null;
string Text(JsonElement e,string k) => e.TryGetProperty(k,out var v)&&v.ValueKind==JsonValueKind.String?v.GetString()??"":"";
string Csv(object? v) {
    var s=v is IFormattable f?f.ToString(null,CultureInfo.InvariantCulture):v?.ToString()??"";
    return "\""+s.Replace("\"","\"\"")+"\"";
}
var stints=data["stints"].Where(x=>Number(x,"driver_number")!=null&&Number(x,"lap_start")!=null)
    .GroupBy(x=>(int)Number(x,"driver_number")!).ToDictionary(g=>g.Key,g=>g.OrderBy(x=>Number(x,"lap_start")).ToArray());
var pits=data["pit"].Where(x=>Number(x,"driver_number")!=null&&Number(x,"lap_number")!=null)
    .GroupBy(x=>((int)Number(x,"driver_number")!, (int)Number(x,"lap_number")!)).ToDictionary(g=>g.Key,g=>g.Last());
Directory.CreateDirectory(output);
await using var writer=new StreamWriter(Path.Combine(output,"laps_normalized.csv"));
await writer.WriteLineAsync("session_key,driver_number,lap_number,lap_duration,compound,tyre_age,is_pit_out_lap,pit_lane_seconds,stationary_stop_seconds");
var kept=0;var dropped=0;
foreach(var lap in data["laps"].OrderBy(x=>Number(x,"driver_number")).ThenBy(x=>Number(x,"lap_number"))) {
    var duration=Number(lap,"lap_duration"); var driverValue=Number(lap,"driver_number"); var lapValue=Number(lap,"lap_number");
    if(duration is null or <=0 ||driverValue is null||lapValue is null) {dropped++;continue;}
    var driver=(int)driverValue;var n=(int)lapValue;JsonElement? stint=null;
    if(stints.TryGetValue(driver,out var list)) {
        // Binary search for the most recent stint that started at or before this lap.
        var lo=0;var hi=list.Length-1;var found=-1;
        while(lo<=hi){var mid=(lo+hi)/2;if(Number(list[mid],"lap_start")<=n){found=mid;lo=mid+1;}else hi=mid-1;}
        if(found>=0 && (Number(list[found],"lap_end") is null ||Number(list[found],"lap_end")>=n)) stint=list[found];
    }
    var compound=stint.HasValue?Text(stint.Value,"compound"):"UNKNOWN";
    double? age=stint.HasValue?n-Number(stint.Value,"lap_start")+(Number(stint.Value,"tyre_age_at_start")??0):null;
    var pit=pits.GetValueOrDefault((driver,n));
    var outLap=lap.TryGetProperty("is_pit_out_lap",out var ol)&&ol.ValueKind==JsonValueKind.True;
    var lane=pit.ValueKind==JsonValueKind.Undefined?null:Number(pit,"lane_duration")??Number(pit,"pit_duration");
    var stationary=pit.ValueKind==JsonValueKind.Undefined?null:Number(pit,"stop_duration");
    await writer.WriteLineAsync(string.Join(",",new object?[]{Number(lap,"session_key"),driver,n,duration,compound,age,outLap,lane,stationary}.Select(Csv)));kept++;
}
var summary=new{source=options.ContainsKey("--fixture")?"fixture; see its data_source":"OpenF1 historical API",rawCounts=data.ToDictionary(x=>x.Key,x=>x.Value.Length),normalizedLapCount=kept,droppedInvalidLaps=dropped,createdUtc=DateTimeOffset.UtcNow};
await File.WriteAllTextAsync(Path.Combine(output,"summary.json"),JsonSerializer.Serialize(summary,new JsonSerializerOptions{WriteIndented=true}));
foreach(var endpoint in endpoints) await File.WriteAllTextAsync(Path.Combine(output,endpoint+".json"),JsonSerializer.Serialize(data[endpoint]));
Console.WriteLine(JsonSerializer.Serialize(summary));
