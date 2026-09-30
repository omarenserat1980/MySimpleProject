using Brain.FilmHub;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<FilmHub>();
var app = builder.Build();

var mediaRoot = Environment.GetEnvironmentVariable("BRAIN_FILM_MEDIA_ROOT")
    ?? Path.Combine(AppContext.BaseDirectory, "media");

FilmHubWeb.MapFilmHub(app, mediaRoot);

app.MapGet("/health", () => Results.Ok(new { ok = true, service = "Brain Film Hub" }));

app.Run();
