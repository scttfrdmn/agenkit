/**
 * Structured logging with trace correlation for Agenkit.
 *
 * Provides JSON structured logging with automatic trace context injection.
 */

import { trace } from '@opentelemetry/api';

/**
 * Log levels.
 */
export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

/**
 * Logging configuration.
 */
export interface LoggingConfig {
  /** Minimum log level */
  level: LogLevel;
  /** Use structured JSON format */
  structured: boolean;
  /** Include trace context (trace_id, span_id) */
  includeTraceContext: boolean;
}

/**
 * Structured log entry.
 */
export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  trace_id?: string;
  span_id?: string;
  [key: string]: any;
}

let currentConfig: LoggingConfig = {
  level: LogLevel.INFO,
  structured: false,
  includeTraceContext: false,
};

const LOG_LEVEL_VALUES: Record<LogLevel, number> = {
  [LogLevel.DEBUG]: 0,
  [LogLevel.INFO]: 1,
  [LogLevel.WARN]: 2,
  [LogLevel.ERROR]: 3,
};

/**
 * Configure structured logging.
 *
 * @param config - Logging configuration
 *
 * @example
 * ```typescript
 * import { configureLogging, LogLevel } from '@agenkit/core/observability';
 *
 * configureLogging({
 *   level: LogLevel.INFO,
 *   structured: true,
 *   includeTraceContext: true
 * });
 * ```
 */
export function configureLogging(config: Partial<LoggingConfig>): void {
  currentConfig = {
    ...currentConfig,
    ...config,
  };
}

/**
 * Get current logging configuration.
 *
 * @returns Current configuration
 */
export function getLoggingConfig(): LoggingConfig {
  return { ...currentConfig };
}

/**
 * Check if a log level should be logged.
 *
 * @param level - Level to check
 * @returns True if should log
 */
function shouldLog(level: LogLevel): boolean {
  return LOG_LEVEL_VALUES[level] >= LOG_LEVEL_VALUES[currentConfig.level];
}

/**
 * Get current trace context.
 *
 * @returns Trace context or undefined
 */
function getTraceContext(): { trace_id: string; span_id: string } | undefined {
  if (!currentConfig.includeTraceContext) {
    return undefined;
  }

  const span = trace.getActiveSpan();
  if (!span) {
    return undefined;
  }

  const spanContext = span.spanContext();
  if (!spanContext) {
    return undefined;
  }

  return {
    trace_id: spanContext.traceId,
    span_id: spanContext.spanId,
  };
}

/**
 * Format log entry.
 *
 * @param level - Log level
 * @param message - Log message
 * @param metadata - Additional metadata
 * @returns Formatted log entry
 */
function formatLogEntry(level: LogLevel, message: string, metadata?: Record<string, any>): LogEntry {
  const entry: LogEntry = {
    timestamp: new Date().toISOString(),
    level,
    message,
  };

  // Add trace context if available
  const traceContext = getTraceContext();
  if (traceContext) {
    entry.trace_id = traceContext.trace_id;
    entry.span_id = traceContext.span_id;
  }

  // Add metadata
  if (metadata) {
    Object.assign(entry, metadata);
  }

  return entry;
}

/**
 * Write log entry to output.
 *
 * @param entry - Log entry
 */
function writeLog(entry: LogEntry): void {
  if (currentConfig.structured) {
    // Structured JSON output
    console.log(JSON.stringify(entry));
  } else {
    // Human-readable output
    const traceInfo = entry.trace_id ? ` [trace_id=${entry.trace_id} span_id=${entry.span_id}]` : '';
    console.log(`[${entry.timestamp}] ${entry.level}${traceInfo}: ${entry.message}`);

    // Log metadata if present
    const metadata: Record<string, any> = { ...entry };
    delete metadata['timestamp'];
    delete metadata['level'];
    delete metadata['message'];
    delete metadata['trace_id'];
    delete metadata['span_id'];

    if (Object.keys(metadata).length > 0) {
      console.log('  Metadata:', metadata);
    }
  }
}

/**
 * Logger class with trace context support.
 */
export class Logger {
  private readonly name: string;

  /**
   * Create a new logger.
   *
   * @param name - Logger name (usually module or component name)
   */
  constructor(name: string) {
    this.name = name;
  }

  /**
   * Log a debug message.
   *
   * @param message - Log message
   * @param metadata - Additional metadata
   */
  debug(message: string, metadata?: Record<string, any>): void {
    if (!shouldLog(LogLevel.DEBUG)) {
      return;
    }

    const entry = formatLogEntry(LogLevel.DEBUG, message, {
      logger: this.name,
      ...metadata,
    });

    writeLog(entry);
  }

  /**
   * Log an info message.
   *
   * @param message - Log message
   * @param metadata - Additional metadata
   */
  info(message: string, metadata?: Record<string, any>): void {
    if (!shouldLog(LogLevel.INFO)) {
      return;
    }

    const entry = formatLogEntry(LogLevel.INFO, message, {
      logger: this.name,
      ...metadata,
    });

    writeLog(entry);
  }

  /**
   * Log a warning message.
   *
   * @param message - Log message
   * @param metadata - Additional metadata
   */
  warn(message: string, metadata?: Record<string, any>): void {
    if (!shouldLog(LogLevel.WARN)) {
      return;
    }

    const entry = formatLogEntry(LogLevel.WARN, message, {
      logger: this.name,
      ...metadata,
    });

    writeLog(entry);
  }

  /**
   * Log an error message.
   *
   * @param message - Log message
   * @param error - Error object (optional)
   * @param metadata - Additional metadata
   */
  error(message: string, error?: Error, metadata?: Record<string, any>): void {
    if (!shouldLog(LogLevel.ERROR)) {
      return;
    }

    const entry = formatLogEntry(LogLevel.ERROR, message, {
      logger: this.name,
      ...(error && {
        error: {
          name: error.name,
          message: error.message,
          stack: error.stack,
        },
      }),
      ...metadata,
    });

    writeLog(entry);
  }
}

/**
 * Get a logger with trace context support.
 *
 * @param name - Logger name
 * @returns Logger instance
 *
 * @example
 * ```typescript
 * import { getLoggerWithTrace } from '@agenkit/core/observability';
 *
 * const logger = getLoggerWithTrace('MyAgent');
 * logger.info('Processing message', { user_id: '123' });
 * ```
 */
export function getLoggerWithTrace(name: string): Logger {
  return new Logger(name);
}
