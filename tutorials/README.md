# Agenkit Tutorials

Complete learning path from beginner to production deployment.

## 🎯 Learning Path

Follow these tutorials in order for the best learning experience:

```
📚 Beginner        → 🏭 Production    → 🧠 Advanced       → 🚀 Deployment    → 🧪 Testing
Tutorial 01          Tutorial 02        Tutorial 03         Tutorial 04        Tutorial 05
Getting Started      Production         Advanced            Production         Testing
                     Patterns           Reasoning           Deployment         Patterns

15-20 min           20-30 min          25-35 min           30-40 min          20-25 min
```

**Total Time**: ~2 hours to master Agenkit fundamentals

---

## 📖 Tutorials

### 01. Getting Started
**Start here!** Learn the fundamentals of building AI agents.

- **Format**: Jupyter Notebook + Marimo (reactive)
- **Time**: 15-20 minutes
- **Level**: Beginner

**What You'll Learn**:
- Installation and setup
- Your first agent (echo agent)
- Agent composition and pipelines
- Working with LLMs (OpenAI, Claude)
- Running and testing agents

**Files**:
- [Jupyter Notebook](01-getting-started.ipynb) - Traditional format
- [Marimo Notebook](01-getting-started.py) - Interactive with sliders

**Key Concepts**: `Agent`, `Message`, `SequentialAgent`, LLM adapters

---

### 02. Production Patterns
**Level up!** Build production-ready agents with middleware and observability.

- **Format**: Jupyter Notebook + Marimo (reactive)
- **Time**: 20-30 minutes
- **Level**: Intermediate

**What You'll Learn**:
- Middleware (Retry, Circuit Breaker, Timeout)
- Observability (Tracing, Metrics)
- Error handling and fallbacks
- Performance optimization (Caching)
- Testing patterns

**Files**:
- [Jupyter Notebook](02-production-patterns.ipynb) - Traditional format
- [Marimo Notebook](02-production-patterns.py) - Interactive with controls

**Key Concepts**: `RetryMiddleware`, `CircuitBreakerMiddleware`, `MetricsMiddleware`, `CachingMiddleware`

**Marimo Features**:
- Interactive sliders for retry configuration
- Dropdowns for failure scenarios
- Real-time metrics collection toggle
- Button-triggered cache performance tests

---

### 03. Advanced Reasoning
**Get smart!** Unlock powerful reasoning techniques for complex problems.

- **Format**: Jupyter Notebook + Marimo (reactive)
- **Time**: 25-35 minutes
- **Level**: Advanced

**What You'll Learn**:
- Chain-of-Thought (CoT) - Step-by-step reasoning
- Tree-of-Thought (ToT) - Explore multiple paths
- Self-Consistency - Voting for reliability
- When to use each technique
- Combining techniques for maximum power

**Files**:
- [Jupyter Notebook](03-advanced-reasoning.ipynb) - Traditional format
- [Marimo Notebook](03-advanced-reasoning.py) - Interactive exploration

**Key Concepts**: `ChainOfThought`, `TreeOfThought`, `SelfConsistency`

**Marimo Features**:
- Sliders for branching factor and depth (ToT)
- Dropdowns for search and voting strategies
- Real-time technique comparison
- Interactive cost-quality trade-off explorer

---

### 04. Production Deployment
**Ship it!** Deploy agents to production with Docker, Kubernetes, and CI/CD.

- **Format**: Comprehensive Guide + Working Templates
- **Time**: 30-40 minutes
- **Level**: Advanced

**What You'll Learn**:
- Docker containerization (multi-stage builds)
- Docker Compose orchestration
- Kubernetes production deployment
- CI/CD with GitHub Actions
- Monitoring with Prometheus + Grafana
- Security, scaling, and reliability best practices

**Directory Structure**:
```
04-deployment/
├── README.md                      # Complete guide
├── Dockerfile                     # Multi-stage build
├── docker-compose.yml             # Local dev stack
├── app.py                        # Production agent
├── requirements.txt               # Dependencies
├── prometheus.yml                 # Metrics config
├── grafana-dashboard.json        # Pre-built dashboard
├── .github/workflows/deploy.yml  # CI/CD pipeline
└── k8s/                          # Kubernetes manifests
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── hpa.yaml                  # Autoscaling
    └── pdb.yaml                  # Disruption budget
```

**Key Features**:
- Complete Docker setup (ready to build)
- Kubernetes manifests (ready to deploy)
- CI/CD pipeline (test → build → deploy)
- Full observability stack
- Production-grade configurations

**Quick Start**:
```bash
cd 04-deployment
docker-compose up  # Start entire stack
```

---

### 05. Testing Patterns
**Test it!** Write comprehensive tests for reliable agents.

- **Format**: Markdown Guide
- **Time**: 20-25 minutes
- **Level**: Intermediate

**What You'll Learn**:
- Unit testing agents with pytest
- Integration testing pipelines
- Mock agents for cost-free testing
- Property-based testing with Hypothesis
- Cross-language testing (Python ↔ Go)
- Performance and load testing
- Best practices and patterns

**File**: [Testing Patterns Guide](05-testing-patterns.md)

**Key Concepts**: pytest, fixtures, mocks, parametrization, coverage

**Testing Stack**:
- pytest + pytest-asyncio
- pytest-cov (coverage)
- pytest-benchmark (performance)
- hypothesis (property-based)

---

## 🎓 Learning Paths by Role

### For Beginners
Start here if you're new to AI agents:
1. **Tutorial 01** - Getting Started
2. **Tutorial 02** - Production Patterns (basics only)
3. Build a simple agent project
4. Return to **Tutorial 05** - Testing Patterns

### For Experienced Developers
Skip ahead if you're comfortable with agents:
1. **Tutorial 01** - Skim for Agenkit-specific patterns
2. **Tutorial 03** - Advanced Reasoning (your sweet spot)
3. **Tutorial 04** - Production Deployment
4. **Tutorial 05** - Testing Patterns

### For DevOps/SRE
Focus on deployment and reliability:
1. **Tutorial 01** - Quick intro to understand agents
2. **Tutorial 02** - Production Patterns (observability focus)
3. **Tutorial 04** - Production Deployment (your focus)
4. **Tutorial 05** - Testing Patterns

### For Researchers/Data Scientists
Focus on reasoning and experimentation:
1. **Tutorial 01** - Getting Started
2. **Tutorial 03** - Advanced Reasoning (your focus)
3. **Tutorial 02** - Production Patterns (caching for experiments)
4. **Tutorial 05** - Testing Patterns (for reproducibility)

---

## 🆚 Jupyter vs. Marimo

### Jupyter Notebooks (`.ipynb`)
**Best for**:
- Traditional notebook workflow
- Linear, step-by-step execution
- JupyterLab or VS Code users
- Familiar environment

**Run**:
```bash
jupyter notebook 01-getting-started.ipynb
```

### Marimo Notebooks (`.py`)
**Best for**:
- Interactive parameter exploration
- Reactive execution (cells update automatically)
- Modern, reactive UI widgets
- No hidden state

**Run**:
```bash
marimo edit 01-getting-started.py
```

**Unique Marimo Features**:
- Sliders, dropdowns, buttons, text inputs
- Cells update when dependencies change
- Real-time feedback
- No execution order confusion

Both formats teach the same concepts - choose based on your preference!

---

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.9+
python --version

# Install Agenkit
pip install agenkit

# For Jupyter notebooks
pip install jupyter

# For Marimo notebooks
pip install marimo

# For LLM examples (optional)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### Run Your First Tutorial

```bash
# Clone repository
git clone https://github.com/scttfrdmn/agenkit.git
cd agenkit/tutorials

# Option 1: Jupyter
jupyter notebook 01-getting-started.ipynb

# Option 2: Marimo (interactive!)
marimo edit 01-getting-started.py

# Option 3: Read guides
cat 04-deployment/README.md
cat 05-testing-patterns.md
```

---

## 📚 Additional Resources

### Documentation
- [Main Documentation](https://agenkit.dev)
- [API Reference](https://agenkit.dev/api/)
- [Pattern Library](../docs/patterns/)

### Examples
- [Basic Examples](../examples/basics/) - Simple, focused examples
- [Pattern Examples](../examples/patterns/) - All 18 agent patterns
- [Production Apps](../examples/apps/) - Complete applications
- [150+ examples](../examples/) across all patterns and languages

### Migration Guides
- [LangChain → Agenkit](../docs/migrations/langchain-to-agenkit.md)
- [CrewAI → Agenkit](../docs/migrations/crewai-to-agenkit.md)
- [AutoGen → Agenkit](../docs/migrations/autogen-to-agenkit.md)
- [AWS Strands → Agenkit](../docs/migrations/strands-to-agenkit.md)
- [smolagents → Agenkit](../docs/migrations/smolagents-to-agenkit.md)

### Multi-Language Support
- [Python](https://github.com/scttfrdmn/agenkit/tree/main/agenkit) - Primary implementation
- [Go](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-go) - High performance
- [TypeScript](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-ts) - Browser + Node.js
- [Rust](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-rust) - Systems programming
- [C++](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-cpp) - Native performance
- [Zig](https://github.com/scttfrdmn/agenkit/tree/main/agenkit-zig) - Modern systems language

---

## 🤝 Community

### Get Help
- [GitHub Discussions](https://github.com/scttfrdmn/agenkit/discussions) - Ask questions
- [GitHub Issues](https://github.com/scttfrdmn/agenkit/issues) - Report bugs
- [Examples](../examples/) - See working code

### Contribute
- Found a bug? [Open an issue](https://github.com/scttfrdmn/agenkit/issues/new)
- Have a tutorial idea? [Start a discussion](https://github.com/scttfrdmn/agenkit/discussions/new)
- Want to contribute? [See CONTRIBUTING.md](../CONTRIBUTING.md)

---

## ✅ Tutorial Completion Checklist

Track your progress through the tutorials:

- [ ] **Tutorial 01**: Created your first agent
- [ ] **Tutorial 01**: Built an agent pipeline
- [ ] **Tutorial 01**: Connected to an LLM
- [ ] **Tutorial 02**: Added retry middleware
- [ ] **Tutorial 02**: Implemented caching
- [ ] **Tutorial 02**: Exposed metrics
- [ ] **Tutorial 03**: Used Chain-of-Thought
- [ ] **Tutorial 03**: Explored Tree-of-Thought
- [ ] **Tutorial 03**: Applied Self-Consistency
- [ ] **Tutorial 04**: Built Docker image
- [ ] **Tutorial 04**: Deployed to Kubernetes
- [ ] **Tutorial 04**: Set up monitoring
- [ ] **Tutorial 05**: Wrote unit tests
- [ ] **Tutorial 05**: Created mock agents
- [ ] **Tutorial 05**: Ran benchmarks

### 🎉 Completed All Tutorials?

**Congratulations!** You're now ready to:
- Build production AI agents
- Deploy to Kubernetes with confidence
- Test thoroughly and reliably
- Use advanced reasoning techniques
- Scale to handle production load

**Next Steps**:
1. Build your own agent project
2. Explore [advanced examples](../examples/)
3. Join the [community discussions](https://github.com/scttfrdmn/agenkit/discussions)
4. Share what you've built!

---

## 📝 Feedback

We'd love to hear from you!

- **Was this helpful?** ⭐ [Star the repo](https://github.com/scttfrdmn/agenkit)
- **Found a bug?** 🐛 [Open an issue](https://github.com/scttfrdmn/agenkit/issues)
- **Have suggestions?** 💡 [Start a discussion](https://github.com/scttfrdmn/agenkit/discussions)
- **Want to contribute?** 🤝 [See CONTRIBUTING.md](../CONTRIBUTING.md)

---

**Happy Building!** 🚀

Made with ❤️ by the Agenkit community
