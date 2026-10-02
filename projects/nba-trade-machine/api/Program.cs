using System.Net;
using System.Text;
using System.Text.Json;

var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxRequestBodySize = 65536);
builder.Services.AddHttpClient("engine", c => {
    c.BaseAddress = new Uri(Environment.GetEnvironmentVariable("NBA_ENGINE_URL") ?? "http://127.0.0.1:8081");
    c.Timeout = TimeSpan.FromSeconds(10);
});
var app = builder.Build();

async Task<IResult> Forward(IHttpClientFactory factory, string path, JsonElement? body = null) {
    try {
        var client = factory.CreateClient("engine");
        using var response = body is null ? await client.GetAsync(path) :
            await client.PostAsync(path, new StringContent(body.Value.GetRawText(), Encoding.UTF8, "application/json"));
        return Results.Content(await response.Content.ReadAsStringAsync(), "application/json", statusCode: (int)response.StatusCode);
    } catch (HttpRequestException) {
        return Results.Json(new { error = "Java trade engine unavailable" }, statusCode: (int)HttpStatusCode.BadGateway);
    } catch (TaskCanceledException) {
        return Results.Json(new { error = "Java trade engine timed out" }, statusCode: (int)HttpStatusCode.GatewayTimeout);
    }
}
app.MapGet("/health", (IHttpClientFactory f) => Forward(f, "/health"));
app.MapGet("/api/sample", (IHttpClientFactory f) => Forward(f, "/api/sample"));
app.MapPost("/api/validate", (JsonElement request, IHttpClientFactory f) => {
    if (request.ValueKind != JsonValueKind.Object || !request.TryGetProperty("teams", out var t) || t.ValueKind != JsonValueKind.Array ||
        !request.TryGetProperty("moves", out var m) || m.ValueKind != JsonValueKind.Array)
        return Task.FromResult<IResult>(Results.BadRequest(new { error = "teams and moves arrays are required" }));
    return Forward(f, "/api/validate", request);
});
app.Run();
