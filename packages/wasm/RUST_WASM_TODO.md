# Rust WASM Implementation - TODO

## Status

Rust WASM compilation is **partially working** but has compilation errors that need to be resolved before it can be included in `@agenkit/wasm`.

## Compilation Errors

### 1. UUID Randomness Source ✅ FIXED

**Error:**
```
error: to use `uuid` on `wasm32-unknown-unknown`, specify a source of randomness
using one of the `js`, `rng-getrandom`, or `rng-rand` features
```

**Fix Applied:**
Updated `Cargo.toml` line 54:
```toml
uuid = { version = "1.6", features = ["v4", "js"] }
```

### 2. Tokio Usage in Self-Consistency ❌ NOT FIXED

**File:** `src/techniques/reasoning/self_consistency.rs:127`

**Error:**
```
error[E0433]: failed to resolve: use of unresolved module or unlinked crate `tokio`
    --> src/techniques/reasoning/self_consistency.rs:127:26
     |
127 |             let handle = tokio::spawn(async move {
     |                          ^^^^^ use of unresolved module or unlinked crate `tokio`
```

**Root Cause:**
- `tokio` is feature-gated for `native` builds only
- WASM builds use `wasm-bindgen-futures` instead
- Self-consistency module directly uses `tokio::spawn` without feature gates

**Fix Needed:**
```rust
// Replace this:
let handle = tokio::spawn(async move {
    // ...
});

// With feature-gated version:
#[cfg(feature = "native")]
let handle = tokio::spawn(async move {
    // ...
});

#[cfg(feature = "wasm")]
let handle = wasm_bindgen_futures::spawn_local(async move {
    // ...
});
```

Or better, use a runtime-agnostic spawn function from `src/runtime.rs`.

### 3. Runtime Type Mismatch ❌ NOT FIXED

**File:** `src/runtime.rs:75`

**Error:**
```
error[E0271]: expected `F` to be a future that resolves to `()`, but it resolves to `<F as Future>::Output`
  --> src/runtime.rs:75:43
   |
75 |         wasm_bindgen_futures::spawn_local(future);
   |         --------------------------------- ^^^^^^ expected `()`, found associated type
```

**Root Cause:**
- `spawn_local` expects `Future<Output = ()>`
- The generic future `F` has an unconstrained output type

**Fix Needed:**
```rust
// Current code (line 75):
pub fn spawn<F>(future: F)
where
    F: Future + 'static,
{
    #[cfg(feature = "wasm")]
    wasm_bindgen_futures::spawn_local(future);  // Error here

    #[cfg(feature = "native")]
    tokio::spawn(future);
}

// Fix: Constrain Future output to ()
pub fn spawn<F>(future: F)
where
    F: Future<Output = ()> + 'static,
{
    #[cfg(feature = "wasm")]
    wasm_bindgen_futures::spawn_local(future);

    #[cfg(feature = "native")]
    {
        tokio::spawn(future);
    }
}
```

## Implementation Plan

### Phase 1: Fix Runtime Abstraction
1. Update `src/runtime.rs`:
   - Add `Future<Output = ()>` constraint to `spawn` function
   - Ensure all runtime functions have proper WASM support
   - Add tests for WASM runtime

### Phase 2: Fix Self-Consistency Module
1. Update `src/techniques/reasoning/self_consistency.rs`:
   - Replace direct `tokio::spawn` calls with `runtime::spawn`
   - Or add feature gates for `tokio` vs `wasm-bindgen-futures`
   - Test with WASM builds

### Phase 3: Build and Test
1. Build WASM:
   ```bash
   cargo build --target wasm32-unknown-unknown \
     --no-default-features --features wasm --release
   ```

2. Or use wasm-pack:
   ```bash
   wasm-pack build --target web \
     --out-dir pkg-web \
     --no-default-features \
     --features wasm \
     --release
   ```

3. Test in browser and Node.js

### Phase 4: Integration
1. Copy `.wasm` and `.js` files to `@agenkit/wasm/wasm/`
2. Update `src/loader.ts` to support Rust WASM
3. Create `src/rust.ts` wrapper similar to `src/zig.ts`
4. Update README with Rust examples
5. Add to package exports in `package.json`

## Estimated Effort

- **Phase 1**: 30 minutes (simple type constraint)
- **Phase 2**: 1 hour (refactor self-consistency module)
- **Phase 3**: 30 minutes (build and test)
- **Phase 4**: 1 hour (integration into NPM package)

**Total**: ~3 hours

## Benefits of Adding Rust

- **wasm-bindgen**: Best-in-class Rust ↔ JavaScript interop
- **Community**: Largest WASM ecosystem in Rust
- **Tooling**: wasm-pack provides excellent developer experience
- **Performance**: Comparable to Zig, slightly larger binaries

## Current Workaround

The `@agenkit/wasm` package currently ships with **Zig WASM only**, which:
- ✅ Works out of the box
- ✅ Ultra-small binaries (4.5K-66K)
- ✅ Native WASM support
- ✅ WASI compatible

Users who need Rust WASM can:
1. Build Rust natively and use HTTP transport
2. Wait for Rust WASM fixes (tracked in #287)
3. Use Zig WASM as a drop-in replacement

## References

- [Issue #287](https://github.com/agenkit/agenkit/issues/287) - NPM Package tracking
- [Issue #284](https://github.com/agenkit/agenkit/issues/284) - Rust WASM patterns (completed)
- [Issue #283](https://github.com/agenkit/agenkit/issues/283) - Rust WASM runtime (completed)
- [wasm-bindgen Guide](https://rustwasm.github.io/docs/wasm-bindgen/)
- [wasm-pack Guide](https://rustwasm.github.io/docs/wasm-pack/)
