using Agenkit.Core;

namespace Agenkit.Safety;

/// <summary>
/// Role-based permission checker for agent operations.
/// </summary>
public class PermissionChecker
{
    private readonly Dictionary<string, HashSet<string>> _rolePermissions = new();

    /// <summary>Grants a set of permissions to a role.</summary>
    public PermissionChecker Grant(string role, params string[] permissions)
    {
        if (!_rolePermissions.TryGetValue(role, out var set))
        {
            set = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            _rolePermissions[role] = set;
        }
        foreach (var p in permissions) set.Add(p);
        return this;
    }

    /// <summary>Checks whether a message from the given role has the required permission.</summary>
    public bool HasPermission(string role, string permission)
    {
        if (_rolePermissions.TryGetValue(role, out var perms))
            return perms.Contains(permission) || perms.Contains("*");
        return false;
    }

    /// <summary>Throws UnauthorizedAccessException if the message role lacks the permission.</summary>
    public void Require(Message message, string permission)
    {
        if (!HasPermission(message.Role, permission))
            throw new UnauthorizedAccessException(
                $"role '{message.Role}' does not have permission '{permission}'");
    }
}
