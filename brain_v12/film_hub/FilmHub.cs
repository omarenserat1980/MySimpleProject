using System.Text.Json;

namespace Brain.FilmHub;

public sealed record Film(
    string Id,
    string Title,
    string VideoPath,
    string ManifestPath,
    string Status,
    DateTime CreatedUtc
);

public sealed class FilmHub
{
    private readonly Dictionary<string, Film> _films = new();

    public Film RegisterVerifiedFilm(string title, string videoPath, string manifestPath)
    {
        var id = Guid.NewGuid().ToString("N");
        var film = new Film(id, title, videoPath, manifestPath, "VERIFIED_COMPLETED", DateTime.UtcNow);
        _films[id] = film;
        return film;
    }

    public IReadOnlyCollection<Film> List() => _films.Values;

    public Film? Get(string id) => _films.TryGetValue(id, out var film) ? film : null;

    public string ToJson() => JsonSerializer.Serialize(_films.Values);
}
