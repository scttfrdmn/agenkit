package io.agenkit.safety;

import io.agenkit.core.Message;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Checks user permissions before allowing agent operations.
 */
public final class PermissionChecker {

    private final Map<String, Set<String>> userPermissions = new ConcurrentHashMap<>();
    private final Set<String> defaultPermissions;

    public PermissionChecker(Set<String> defaultPermissions) {
        this.defaultPermissions = Set.copyOf(defaultPermissions);
    }

    public PermissionChecker() {
        this(Set.of("read", "write"));
    }

    public void grantPermission(String userId, String permission) {
        userPermissions.computeIfAbsent(userId, k -> ConcurrentHashMap.newKeySet())
                .add(permission);
    }

    public void revokePermission(String userId, String permission) {
        Set<String> perms = userPermissions.get(userId);
        if (perms != null) {
            perms.remove(permission);
        }
    }

    public boolean hasPermission(Message message, String requiredPermission) {
        String userId = (String) message.getMetadata().getOrDefault("user_id", "anonymous");
        Set<String> userPerms = userPermissions.getOrDefault(userId, Set.of());

        return defaultPermissions.contains(requiredPermission)
                || userPerms.contains(requiredPermission)
                || userPerms.contains("admin");
    }

    public boolean check(Message message, String permission) {
        return hasPermission(message, permission);
    }
}
