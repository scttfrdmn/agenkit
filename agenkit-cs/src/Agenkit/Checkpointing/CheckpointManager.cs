using System.Text.Json;

namespace Agenkit.Checkpointing;

/// <summary>
/// Saves and loads agent state checkpoints to/from JSON.
/// </summary>
public class CheckpointManager
{
    private readonly string _directory;

    private static readonly JsonSerializerOptions JsonOpts = new()
    {
        WriteIndented = true
    };

    /// <summary>Creates a CheckpointManager that persists to the given directory.</summary>
    public CheckpointManager(string directory = "checkpoints")
    {
        _directory = directory;
    }

    /// <summary>Saves a state object as a checkpoint.</summary>
    public async Task SaveAsync(string name, object state, CancellationToken ct = default)
    {
        Directory.CreateDirectory(_directory);
        var path = Path.Combine(_directory, $"{name}.json");
        var json = JsonSerializer.Serialize(state, JsonOpts);
        await File.WriteAllTextAsync(path, json, ct).ConfigureAwait(false);
    }

    /// <summary>Loads a checkpoint and deserializes it to the given type.</summary>
    public async Task<T?> LoadAsync<T>(string name, CancellationToken ct = default)
    {
        var path = Path.Combine(_directory, $"{name}.json");
        if (!File.Exists(path)) return default;
        var json = await File.ReadAllTextAsync(path, ct).ConfigureAwait(false);
        return JsonSerializer.Deserialize<T>(json, JsonOpts);
    }

    /// <summary>Returns true if a checkpoint with the given name exists.</summary>
    public bool Exists(string name)
    {
        var path = Path.Combine(_directory, $"{name}.json");
        return File.Exists(path);
    }

    /// <summary>Deletes a checkpoint.</summary>
    public void Delete(string name)
    {
        var path = Path.Combine(_directory, $"{name}.json");
        if (File.Exists(path)) File.Delete(path);
    }

    /// <summary>Returns the names of all stored checkpoints.</summary>
    public IReadOnlyList<string> ListCheckpoints()
    {
        if (!Directory.Exists(_directory)) return Array.Empty<string>();
        return Directory.GetFiles(_directory, "*.json")
            .Select(Path.GetFileNameWithoutExtension)
            .OfType<string>()
            .ToList();
    }
}
