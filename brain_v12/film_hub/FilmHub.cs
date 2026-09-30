using System.Text.Json;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.FileProviders;

namespace Brain.FilmHub;

public sealed record Film(string Id,string Title,string VideoPath,string ManifestPath,string Status,DateTime CreatedUtc);

public sealed class FilmHub {
    private readonly Dictionary<string,Film> _films = new();

    public Film RegisterVerifiedFilm(string title,string videoPath,string manifestPath) {
        if (!File.Exists(videoPath)) throw new FileNotFoundException("MP4_NOT_FOUND",videoPath);
        if (!File.Exists(manifestPath)) throw new FileNotFoundException("MANIFEST_NOT_FOUND",manifestPath);
        var manifest=File.ReadAllText(manifestPath);
        if (!manifest.Contains("VERIFIED_COMPLETED",StringComparison.Ordinal))
            throw new InvalidOperationException("FILM_NOT_VERIFIED");
        var id=Guid.NewGuid().ToString("N");
        var film=new Film(id,title,videoPath,manifestPath,"VERIFIED_COMPLETED",DateTime.UtcNow);
        _films[id]=film; return film;
    }
    public IReadOnlyCollection<Film> List()=>_films.Values;
    public Film? Get(string id)=>_films.TryGetValue(id,out var film)?film:null;
}

public static class FilmHubWeb {
    public static void MapFilmHub(WebApplication app,string mediaRoot) {
        Directory.CreateDirectory(mediaRoot);
        app.MapGet("/api/films",(FilmHub hub)=>Results.Ok(hub.List()));
        app.MapGet("/api/films/{id}",(string id,FilmHub hub)=>{
            var f=hub.Get(id); return f is null ? Results.NotFound() : Results.Ok(f);
        });
        app.MapGet("/api/films/{id}/stream",(string id,FilmHub hub)=>{
            var f=hub.Get(id);
            if(f is null || !File.Exists(f.VideoPath)) return Results.NotFound();
            return Results.File(f.VideoPath,"video/mp4",enableRangeProcessing:true);
        });
        app.MapGet("/films/{id}",async (string id,FilmHub hub, HttpContext ctx)=>{
            var f=hub.Get(id); if(f is null) return Results.NotFound();
            ctx.Response.ContentType="text/html; charset=utf-8";
            await ctx.Response.WriteAsync($"""
<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{System.Net.WebUtility.HtmlEncode(f.Title)} — Brain Film Hub</title>
<style>
body{{margin:0;background:#0b1017;color:#edf2f7;font-family:system-ui}}
main{{max-width:1100px;margin:auto;padding:24px}}.player{{background:#000;border-radius:16px;overflow:hidden}}
video{{width:100%;display:block;max-height:75vh}}.meta{{padding:20px 0}}.badge{{display:inline-block;padding:6px 10px;border-radius:999px;background:#183b2a;color:#8ff0b0}}
a{{color:#8fc7ff}}
</style></head><body><main>
<p><a href="/film-hub/">← Brain Film Hub</a></p>
<h1>{System.Net.WebUtility.HtmlEncode(f.Title)}</h1>
<div class="player"><video controls preload="metadata" playsinline src="/api/films/{f.Id}/stream"></video></div>
<div class="meta"><span class="badge">{f.Status}</span><p>Brain verified film · {f.CreatedUtc:u}</p></div>
</main></body></html>
""");
            return Results.Empty;
        });
        app.UseStaticFiles(new StaticFileOptions {
            FileProvider=new PhysicalFileProvider(Path.GetFullPath(Path.Combine(mediaRoot,"..","web"))),
            RequestPath="/film-hub"
        });
    }
}
