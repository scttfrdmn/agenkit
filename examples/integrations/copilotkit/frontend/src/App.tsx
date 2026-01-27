import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import "./App.css";

function App() {
  return (
    <CopilotKit
      runtimeUrl="/agui"
      agent="ResearchAssistant"
      showDevConsole={true}
    >
      <CopilotSidebar
        defaultOpen={true}
        clickOutsideToClose={false}
        labels={{
          title: "Research Assistant",
          initial: "Hi! I'm your research assistant. I can help you:\n\n🔍 Search the web for information\n🧮 Perform calculations\n🌤️ Check weather forecasts\n\nWhat would you like to know?",
        }}
      >
        <div className="app-container">
          <header className="app-header">
            <h1>🤖 Agenkit + CopilotKit</h1>
            <p className="subtitle">Research Assistant with AG-UI Standard Protocol</p>
          </header>

          <main className="app-main">
            <section className="info-card">
              <h2>✨ Features</h2>
              <ul>
                <li>
                  <strong>Web Search:</strong> Ask me to search for any topic or current events
                </li>
                <li>
                  <strong>Calculator:</strong> Perform mathematical calculations with natural language
                </li>
                <li>
                  <strong>Weather:</strong> Get current weather and forecasts for any location
                </li>
              </ul>
            </section>

            <section className="info-card">
              <h2>🔧 Technology Stack</h2>
              <div className="tech-grid">
                <div className="tech-item">
                  <h3>Backend</h3>
                  <ul>
                    <li>Agenkit (Python)</li>
                    <li>FastAPI</li>
                    <li>AG-UI Standard Protocol</li>
                    <li>SSE Transport</li>
                  </ul>
                </div>
                <div className="tech-item">
                  <h3>Frontend</h3>
                  <ul>
                    <li>React + TypeScript</li>
                    <li>CopilotKit</li>
                    <li>Vite</li>
                  </ul>
                </div>
              </div>
            </section>

            <section className="info-card">
              <h2>💡 Try These Examples</h2>
              <div className="examples">
                <button className="example-button">
                  "Search for the latest AI developments"
                </button>
                <button className="example-button">
                  "Calculate the area of a circle with radius 5"
                </button>
                <button className="example-button">
                  "What's the weather in San Francisco?"
                </button>
                <button className="example-button">
                  "Search for Python async patterns and calculate 2^10"
                </button>
              </div>
            </section>

            <section className="info-card protocol-info">
              <h2>📡 AG-UI Standard Protocol</h2>
              <p>
                This example demonstrates the full AG-UI Standard protocol with:
              </p>
              <ul>
                <li><strong>15+ Event Types:</strong> Lifecycle, text messages, tool calls, state management</li>
                <li><strong>SSE Transport:</strong> Efficient server-sent events streaming</li>
                <li><strong>Tool Call Tracking:</strong> Real-time visibility into tool execution</li>
                <li><strong>State Management:</strong> JSON Patch for efficient state updates</li>
                <li><strong>Production Ready:</strong> CORS, health checks, error handling</li>
              </ul>
            </section>
          </main>

          <footer className="app-footer">
            <p>
              <a href="https://github.com/agentic-ai/agenkit" target="_blank" rel="noopener noreferrer">
                View on GitHub
              </a>
              {" · "}
              <a href="/metadata" target="_blank" rel="noopener noreferrer">
                Agent Metadata
              </a>
              {" · "}
              <a href="/health" target="_blank" rel="noopener noreferrer">
                Health Check
              </a>
            </p>
          </footer>
        </div>
      </CopilotSidebar>
    </CopilotKit>
  );
}

export default App;
