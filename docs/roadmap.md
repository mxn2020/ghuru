# Roadmap

## v0.2 — AI Adapter Interface

- [ ] Define `AIRunner` abstract class extending the Runner interface
- [ ] Add configuration for AI provider settings (API keys, model selection)
- [ ] Implement OpenAI-compatible adapter as reference implementation
- [ ] Add `--runner ai` option to `ghfun agent run`
- [ ] Configurable workflow templates (user-defined task handlers)
- [ ] Mission templates library (pre-built mission definitions)
- [ ] Improved error recovery and retry logic for runners

## v0.3 — Multi-Agent & Comparison

- [ ] Parallel agent runs for the same task (multiple runners simultaneously)
- [ ] Comparison dashboard: side-by-side diff of results from different runners
- [ ] Agent leaderboard: track success rates and timing per runner type
- [ ] Web UI prototype (FastAPI + HTMX or similar lightweight approach)
- [ ] Webhook receiver for real-time GitHub event processing
- [ ] Mission dependency graph (tasks can depend on other tasks)
- [ ] Export/import missions between repositories

## v1.0 — Stable Release

- [ ] Stable public API for runner plugins
- [ ] Plugin system for custom runners and task types
- [ ] Full web UI with authentication and multi-user support
- [ ] GitHub Marketplace integration (installable GitHub App)
- [ ] GitHub Enterprise Server support
- [ ] Comprehensive API documentation
- [ ] Performance benchmarks and optimization
- [ ] Telemetry and usage analytics (opt-in)
- [ ] Pre-built runner marketplace

## Future Ideas

- VS Code extension for mission management
- Team collaboration features (shared missions, reviews)
- Cost tracking for AI-powered runners
- Integration with other CI/CD systems (GitLab, Bitbucket)
- Natural language mission creation ("set up a React app with tests")
