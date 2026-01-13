//! String interning for common values
//!
//! Reduces allocations for frequently used strings like message roles,
//! metadata keys, and other common identifiers.

use std::borrow::Cow;
use std::sync::Arc;
use parking_lot::RwLock;
use std::collections::HashMap;

lazy_static::lazy_static! {
    /// Global string pool for interned strings
    static ref STRING_POOL: StringPool = StringPool::new();
}

/// Common message roles as static strings
pub mod roles {
    pub const USER: &str = "user";
    pub const ASSISTANT: &str = "assistant";
    pub const SYSTEM: &str = "system";
    pub const TOOL: &str = "tool";
}

/// Common metadata keys as static strings
pub mod metadata_keys {
    pub const SESSION_ID: &str = "session_id";
    pub const TIMESTAMP: &str = "timestamp";
    pub const MODEL: &str = "model";
    pub const TEMPERATURE: &str = "temperature";
    pub const MAX_TOKENS: &str = "max_tokens";
    pub const STOP_SEQUENCES: &str = "stop_sequences";
}

/// String pool for interning strings to reduce allocations
pub struct StringPool {
    pool: RwLock<HashMap<String, Arc<str>>>,
}

impl StringPool {
    /// Create a new string pool
    fn new() -> Self {
        let mut pool = HashMap::new();

        // Pre-populate with common values
        Self::populate_common_roles(&mut pool);
        Self::populate_common_metadata_keys(&mut pool);

        Self {
            pool: RwLock::new(pool),
        }
    }

    /// Pre-populate common role strings
    fn populate_common_roles(pool: &mut HashMap<String, Arc<str>>) {
        for role in &[roles::USER, roles::ASSISTANT, roles::SYSTEM, roles::TOOL] {
            pool.insert(role.to_string(), Arc::from(*role));
        }
    }

    /// Pre-populate common metadata key strings
    fn populate_common_metadata_keys(pool: &mut HashMap<String, Arc<str>>) {
        for key in &[
            metadata_keys::SESSION_ID,
            metadata_keys::TIMESTAMP,
            metadata_keys::MODEL,
            metadata_keys::TEMPERATURE,
            metadata_keys::MAX_TOKENS,
            metadata_keys::STOP_SEQUENCES,
        ] {
            pool.insert(key.to_string(), Arc::from(*key));
        }
    }

    /// Intern a string, returning a reference-counted pointer
    ///
    /// If the string is already in the pool, returns the existing Arc.
    /// Otherwise, adds it to the pool and returns a new Arc.
    pub fn intern(&self, s: impl AsRef<str>) -> Arc<str> {
        let s_ref = s.as_ref();

        // Fast path: check if already in pool (read lock)
        {
            let pool = self.pool.read();
            if let Some(interned) = pool.get(s_ref) {
                return Arc::clone(interned);
            }
        }

        // Slow path: add to pool (write lock)
        let mut pool = self.pool.write();

        // Double-check after acquiring write lock (another thread might have added it)
        if let Some(interned) = pool.get(s_ref) {
            return Arc::clone(interned);
        }

        let interned: Arc<str> = Arc::from(s_ref);
        pool.insert(s_ref.to_string(), Arc::clone(&interned));
        interned
    }

    /// Get an interned string without adding it if not present
    pub fn get(&self, s: &str) -> Option<Arc<str>> {
        let pool = self.pool.read();
        pool.get(s).map(Arc::clone)
    }

    /// Check if a string is interned
    pub fn contains(&self, s: &str) -> bool {
        let pool = self.pool.read();
        pool.contains_key(s)
    }

    /// Get the size of the string pool
    pub fn size(&self) -> usize {
        let pool = self.pool.read();
        pool.len()
    }

    /// Clear the string pool (except pre-populated values)
    pub fn clear(&self) {
        let mut pool = self.pool.write();
        pool.clear();
        Self::populate_common_roles(&mut pool);
        Self::populate_common_metadata_keys(&mut pool);
    }
}

/// Get a reference to the global string pool
pub fn global_pool() -> &'static StringPool {
    &STRING_POOL
}

/// Intern a string using the global pool
pub fn intern(s: impl AsRef<str>) -> Arc<str> {
    STRING_POOL.intern(s)
}

/// Get a role string, preferring static strings for common roles
pub fn role(role: &str) -> Cow<'static, str> {
    match role {
        roles::USER => Cow::Borrowed(roles::USER),
        roles::ASSISTANT => Cow::Borrowed(roles::ASSISTANT),
        roles::SYSTEM => Cow::Borrowed(roles::SYSTEM),
        roles::TOOL => Cow::Borrowed(roles::TOOL),
        _ => Cow::Owned(role.to_string()),
    }
}

/// Check if a role is one of the common roles
pub fn is_common_role(role: &str) -> bool {
    matches!(role, roles::USER | roles::ASSISTANT | roles::SYSTEM | roles::TOOL)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_string_pool_intern() {
        let pool = StringPool::new();

        let s1 = pool.intern("test");
        let s2 = pool.intern("test");

        // Same Arc (pointer equality)
        assert!(Arc::ptr_eq(&s1, &s2));
    }

    #[test]
    fn test_string_pool_contains() {
        let pool = StringPool::new();

        assert!(pool.contains(roles::USER));
        assert!(pool.contains(roles::ASSISTANT));
        assert!(!pool.contains("custom_role"));

        pool.intern("custom_role");
        assert!(pool.contains("custom_role"));
    }

    #[test]
    fn test_string_pool_size() {
        let pool = StringPool::new();

        // Should have pre-populated values
        let initial_size = pool.size();
        assert!(initial_size >= 4); // At least 4 roles

        pool.intern("new_value");
        assert_eq!(pool.size(), initial_size + 1);
    }

    #[test]
    fn test_string_pool_clear() {
        let pool = StringPool::new();

        pool.intern("custom1");
        pool.intern("custom2");

        let size_before = pool.size();
        pool.clear();
        let size_after = pool.size();

        // Should clear custom values but keep pre-populated
        assert!(size_after < size_before);
        assert!(pool.contains(roles::USER));
        assert!(!pool.contains("custom1"));
    }

    #[test]
    fn test_role_cow_borrowed() {
        let r = role(roles::USER);
        assert!(matches!(r, Cow::Borrowed(_)));

        let r = role(roles::ASSISTANT);
        assert!(matches!(r, Cow::Borrowed(_)));
    }

    #[test]
    fn test_role_cow_owned() {
        let r = role("custom_role");
        assert!(matches!(r, Cow::Owned(_)));
    }

    #[test]
    fn test_is_common_role() {
        assert!(is_common_role(roles::USER));
        assert!(is_common_role(roles::ASSISTANT));
        assert!(is_common_role(roles::SYSTEM));
        assert!(is_common_role(roles::TOOL));
        assert!(!is_common_role("custom"));
    }

    #[test]
    fn test_global_pool() {
        let s1 = intern("global_test");
        let s2 = intern("global_test");

        assert!(Arc::ptr_eq(&s1, &s2));
    }

    #[test]
    fn test_metadata_keys_interned() {
        let pool = global_pool();

        assert!(pool.contains(metadata_keys::SESSION_ID));
        assert!(pool.contains(metadata_keys::MODEL));
        assert!(pool.contains(metadata_keys::TEMPERATURE));
    }
}
