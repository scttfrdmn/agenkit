/**
 * Load balancing for distributing requests across multiple agents with:
 * - Multiple strategies (round-robin, least-connections, weighted, random)
 * - Automatic health checking
 * - Failover support
 * - Real-time backend statistics
 * - Thread-safe for concurrent requests
 */

import type { Agent, Message } from '../core/interfaces';

/**
 * Load balancing algorithm strategy.
 */
export enum LoadBalancingStrategy {
  ROUND_ROBIN = 'round_robin',
  LEAST_CONNECTIONS = 'least_connections',
  WEIGHTED_ROUND_ROBIN = 'weighted_round_robin',
  RANDOM = 'random',
}

/**
 * Backend agent with metadata.
 */
export interface AgentBackend {
  agent: Agent;
  weight: number;
  healthy: boolean;
  activeConnections: number;
  totalRequests: number;
  totalFailures: number;
  lastHealthCheck: Date;
  consecutiveFailures: number;
}

/**
 * Load balancer configuration.
 */
export interface LoadBalancerConfig {
  strategy: LoadBalancingStrategy;
  healthCheckInterval: number; // milliseconds
  healthCheckTimeout: number; // milliseconds
  failureThreshold: number;
  successThreshold: number;
  enableFailover: boolean;
}

/**
 * Default load balancer configuration.
 */
export function defaultLoadBalancerConfig(): LoadBalancerConfig {
  return {
    strategy: LoadBalancingStrategy.ROUND_ROBIN,
    healthCheckInterval: 30000,
    healthCheckTimeout: 5000,
    failureThreshold: 3,
    successThreshold: 2,
    enableFailover: true,
  };
}

/**
 * Load balancer performance metrics.
 */
export interface LoadBalancerMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  failoverAttempts: number;
  backendHealthChanges: Record<string, number>;
}

/**
 * Backend statistics.
 */
export interface BackendStats {
  name: string;
  healthy: boolean;
  weight: number;
  activeConnections: number;
  totalRequests: number;
  totalFailures: number;
  lastHealthCheck: Date;
}

/**
 * Load balancer distributes requests across multiple agents.
 */
export class LoadBalancer implements Agent {
  private backends: AgentBackend[];
  private config: LoadBalancerConfig;
  private metrics: LoadBalancerMetrics;
  private currentIndex: number;
  private healthCheckInterval?: NodeJS.Timeout;

  constructor(agents: Agent[], config?: LoadBalancerConfig, weights?: number[]) {
    if (agents.length === 0) {
      throw new Error('At least one agent required');
    }

    this.config = config || defaultLoadBalancerConfig();

    // Default weights to 1 if not provided
    const finalWeights = weights || agents.map(() => 1);

    if (finalWeights.length !== agents.length) {
      throw new Error(
        `Weights length (${finalWeights.length}) must match agents length (${agents.length})`
      );
    }

    // Create backends
    this.backends = agents.map((agent, i) => ({
      agent,
      weight: finalWeights[i],
      healthy: true,
      activeConnections: 0,
      totalRequests: 0,
      totalFailures: 0,
      lastHealthCheck: new Date(),
      consecutiveFailures: 0,
    }));

    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      failoverAttempts: 0,
      backendHealthChanges: {},
    };

    this.currentIndex = 0;
  }

  get name(): string {
    return `LoadBalancer(${this.backends.length} backends)`;
  }

  get capabilities(): string[] {
    const capsMap = new Map<string, boolean>();
    for (const backend of this.backends) {
      for (const cap of backend.agent.capabilities ?? []) {
        capsMap.set(cap, true);
      }
    }
    return Array.from(capsMap.keys());
  }

  /**
   * Get statistics for all backends.
   */
  getBackendStats(): BackendStats[] {
    return this.backends.map((backend) => ({
      name: backend.agent.name,
      healthy: backend.healthy,
      weight: backend.weight,
      activeConnections: backend.activeConnections,
      totalRequests: backend.totalRequests,
      totalFailures: backend.totalFailures,
      lastHealthCheck: backend.lastHealthCheck,
    }));
  }

  /**
   * Start background health check tasks.
   */
  startHealthChecks(): void {
    if (this.healthCheckInterval) {
      return; // Already started
    }

    this.healthCheckInterval = setInterval(() => {
      void this.performHealthChecks();
    }, this.config.healthCheckInterval);
  }

  /**
   * Stop background health check tasks.
   */
  stopHealthChecks(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = undefined;
    }
  }

  private async performHealthChecks(): Promise<void> {
    for (const backend of this.backends) {
      try {
        // Create timeout promise
        const timeoutPromise = new Promise<Message>((_, reject) => {
          setTimeout(() => reject(new Error('Health check timeout')), this.config.healthCheckTimeout);
        });

        // Simple health check: test if agent responds
        const testMsg: Message = {
          role: 'system',
          content: 'health_check',
        };

        const checkPromise = backend.agent.process(testMsg);
        await Promise.race([checkPromise, timeoutPromise]);

        backend.lastHealthCheck = new Date();

        // Success
        backend.consecutiveFailures = 0;
        if (!backend.healthy && backend.consecutiveFailures === 0) {
          backend.healthy = true;
          this.trackHealthChange(backend.agent.name, 'recovered');
        }
      } catch {
        // Failure
        backend.consecutiveFailures++;
        backend.totalFailures++;

        if (backend.healthy && backend.consecutiveFailures >= this.config.failureThreshold) {
          backend.healthy = false;
          this.trackHealthChange(backend.agent.name, 'unhealthy');
        }
      }
    }
  }

  private trackHealthChange(agentName: string, changeType: string): void {
    const key = `${agentName}:${changeType}`;
    this.metrics.backendHealthChanges[key] = (this.metrics.backendHealthChanges[key] || 0) + 1;
  }

  private selectBackend(): AgentBackend | null {
    const healthyBackends = this.backends.filter((b) => b.healthy);

    if (healthyBackends.length === 0) {
      return null;
    }

    switch (this.config.strategy) {
      case LoadBalancingStrategy.ROUND_ROBIN:
        return this.selectRoundRobin();
      case LoadBalancingStrategy.LEAST_CONNECTIONS:
        return this.selectLeastConnections(healthyBackends);
      case LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
        return this.selectWeightedRoundRobin(healthyBackends);
      case LoadBalancingStrategy.RANDOM:
        return healthyBackends[Math.floor(Math.random() * healthyBackends.length)];
      default:
        return healthyBackends[0];
    }
  }

  private selectRoundRobin(): AgentBackend {
    // Find next healthy backend in rotation
    for (let i = 0; i < this.backends.length; i++) {
      this.currentIndex = (this.currentIndex + 1) % this.backends.length;
      if (this.backends[this.currentIndex].healthy) {
        return this.backends[this.currentIndex];
      }
    }

    // Fallback to first healthy
    return this.backends.find((b) => b.healthy)!;
  }

  private selectLeastConnections(backends: AgentBackend[]): AgentBackend {
    let minConnections = backends[0].activeConnections;
    let selected = backends[0];

    for (const backend of backends.slice(1)) {
      if (backend.activeConnections < minConnections) {
        minConnections = backend.activeConnections;
        selected = backend;
      }
    }

    return selected;
  }

  private selectWeightedRoundRobin(backends: AgentBackend[]): AgentBackend {
    // Build weighted list
    const weighted: AgentBackend[] = [];
    for (const backend of backends) {
      for (let i = 0; i < backend.weight; i++) {
        weighted.push(backend);
      }
    }

    if (weighted.length === 0) {
      return backends[0];
    }

    this.currentIndex = (this.currentIndex + 1) % weighted.length;
    return weighted[this.currentIndex];
  }

  /**
   * Process a message using load-balanced backend.
   */
  async process(message: Message): Promise<Message> {
    this.metrics.totalRequests++;

    const attempted = new Set<string>();

    for (;;) {
      const backend = this.selectBackend();
      if (!backend) {
        throw new Error('All backends unhealthy');
      }

      // Avoid retrying same backend
      if (attempted.has(backend.agent.name)) {
        if (!this.config.enableFailover || attempted.size >= this.backends.length) {
          throw new Error('All backends attempted');
        }
        continue;
      }

      attempted.add(backend.agent.name);

      // Track request
      backend.activeConnections++;
      backend.totalRequests++;

      try {
        const response = await backend.agent.process(message);

        backend.activeConnections--;

        // Success
        this.metrics.successfulRequests++;
        return response;
      } catch (error) {
        backend.activeConnections--;

        // Failure
        backend.totalFailures++;
        this.metrics.failedRequests++;

        // Check if should mark unhealthy
        if (backend.totalFailures >= this.config.failureThreshold) {
          backend.healthy = false;
          this.trackHealthChange(backend.agent.name, 'unhealthy');
        }

        // Try failover if enabled
        if (this.config.enableFailover && attempted.size < this.backends.length) {
          this.metrics.failoverAttempts++;
          continue;
        }

        // No more failover
        throw new Error(`Backend ${backend.agent.name} failed: ${error}`);
      }
    }
  }

  /**
   * Get current metrics.
   */
  getMetrics(): LoadBalancerMetrics {
    return this.metrics;
  }
}
