# WebAssembly Language Support

## v0.44.0: Current WASM Languages

Agenkit v0.44.0 implements WebAssembly support for three compiled systems languages:

### ✅ Rust
- **Runtime**: wasm-bindgen-futures (replaced tokio)
- **Target**: wasm32-unknown-unknown
- **Output**: Optimized WASM modules (KB range)
- **Status**: 18/18 patterns implemented
- **Use Case**: Browser and edge computing with excellent performance

### ✅ C++
- **Runtime**: Emscripten toolchain
- **Target**: wasm32-emscripten
- **Output**: 46MB static library (libagenkit.a)
- **Status**: 18/18 patterns + Self-Consistency technique
- **Use Case**: Existing C++ codebases, high-performance computing

### ✅ Zig
- **Runtime**: Native Zig WASM compilation
- **Target**: wasm32-wasi
- **Output**: 27 WASM files (4.5K-89K each)
- **Status**: 18/18 patterns + examples
- **Use Case**: Lightweight, portable binaries with WASI support

## Languages Not Included (Yet)

### Go - Future Consideration

**Why not in v0.44.0:**
- **Runtime Size**: Go's WASM runtime is several MB (vs KB for Rust/C++/Zig)
- **Browser-First Design**: Go's WASM is primarily for `GOOS=js` browser environments
- **WASI Maturity**: Go's WASI support is still experimental (as of Go 1.21+)
- **Use Case Mismatch**: Go excels at server-side concurrent systems, not edge/browser deployment

**Why reconsider later:**
- Go 1.21+ added WASI support (`GOOS=wasip1`)
- TinyGo provides significantly smaller WASM binaries
- Growing WASI ecosystem may improve Go's WASM story
- Server-side WASM (wasmCloud, Spin) could benefit from Go's concurrency

**Future Issue**: Track at #290 (if created)

### TypeScript - Not Applicable

TypeScript doesn't compile to WASM - it compiles to JavaScript, which already runs natively in browsers and Node.js environments. TypeScript doesn't need WASM support.

## Decision Rationale

### Primary Goals for v0.44.0 WASM Support

1. **Browser Deployment**: Run AI agents directly in web browsers
2. **Edge Computing**: Deploy to Cloudflare Workers, Fastly Compute@Edge, etc.
3. **Sandboxed Execution**: Run untrusted code safely with WASM sandboxing
4. **Minimal Overhead**: Keep runtime sizes small for fast loading

### Why These Three Languages

**Rust**:
- Best-in-class WASM tooling (wasm-bindgen, wasm-pack)
- Zero-cost abstractions compile to efficient WASM
- Active WASM ecosystem and community

**C++**:
- Emscripten is the original C/C++ to WASM compiler
- Massive existing C++ codebases can be ported
- Strong performance characteristics

**Zig**:
- Native WASM support without external toolchains
- Ultra-small binary sizes
- Growing systems programming community
- WASI-first approach aligns with WASM standards

### Comparison Table

| Language   | Runtime Size | Toolchain Maturity | WASI Support | Browser Support | v0.44.0 Status |
|------------|--------------|-------------------|--------------|-----------------|----------------|
| Rust       | KB range     | Excellent         | Yes          | Excellent       | ✅ Implemented |
| C++        | MB range     | Excellent         | Yes          | Excellent       | ✅ Implemented |
| Zig        | KB range     | Good              | Yes          | Good            | ✅ Implemented |
| Go         | MB range     | Experimental      | Experimental | Good            | ⏳ Future      |
| TypeScript | N/A          | N/A               | N/A          | Native (JS)     | ❌ Not Needed  |

## Future Roadmap

### Short-Term (v0.44.0 - Q1 2025)
- Complete @agenkit/wasm NPM package
- Browser integration examples (React, Vue, Svelte)
- Automated WASM testing and CI/CD

### Medium-Term (v0.45.0+ - Q2 2025)
- Evaluate TinyGo for smaller Go WASM binaries
- Monitor Go WASI maturity (Go 1.22+)
- Assess real-world demand for Go WASM support

### Long-Term (2026+)
- Server-side WASM runtimes (wasmCloud, Spin)
- WASM Component Model adoption
- Multi-language WASM composition

## References

- [Go WASM Proposal](https://github.com/golang/go/issues/31105)
- [TinyGo WASM Support](https://tinygo.org/docs/guides/webassembly/)
- [Rust WASM Book](https://rustwasm.github.io/docs/book/)
- [Emscripten Documentation](https://emscripten.org/docs/)
- [Zig WASM Support](https://ziglang.org/documentation/master/#WebAssembly)

## See Also

- WASM tracking: see GitHub issues labeled `wasm` (the authoritative source for status/plan)
- Cross-language parity: regenerated via `scripts/test-parity.sh` and the Parity Validation CI workflow
