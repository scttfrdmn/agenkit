"use strict";
/**
 * Structured logging with trace correlation for Agenkit.
 *
 * Provides JSON structured logging with automatic trace context injection.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.Logger = exports.LogLevel = void 0;
exports.configureLogging = configureLogging;
exports.getLoggingConfig = getLoggingConfig;
exports.getLoggerWithTrace = getLoggerWithTrace;
const api_1 = require("@opentelemetry/api");
/**
 * Log levels.
 */
var LogLevel;
(function (LogLevel) {
    LogLevel["DEBUG"] = "DEBUG";
    LogLevel["INFO"] = "INFO";
    LogLevel["WARN"] = "WARN";
    LogLevel["ERROR"] = "ERROR";
})(LogLevel || (exports.LogLevel = LogLevel = {}));
let currentConfig = {
    level: LogLevel.INFO,
    structured: false,
    includeTraceContext: false,
};
const LOG_LEVEL_VALUES = {
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
function configureLogging(config) {
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
function getLoggingConfig() {
    return { ...currentConfig };
}
/**
 * Check if a log level should be logged.
 *
 * @param level - Level to check
 * @returns True if should log
 */
function shouldLog(level) {
    return LOG_LEVEL_VALUES[level] >= LOG_LEVEL_VALUES[currentConfig.level];
}
/**
 * Get current trace context.
 *
 * @returns Trace context or undefined
 */
function getTraceContext() {
    if (!currentConfig.includeTraceContext) {
        return undefined;
    }
    const span = api_1.trace.getActiveSpan();
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
function formatLogEntry(level, message, metadata) {
    const entry = {
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
function writeLog(entry) {
    if (currentConfig.structured) {
        // Structured JSON output
        console.log(JSON.stringify(entry));
    }
    else {
        // Human-readable output
        const traceInfo = entry.trace_id ? ` [trace_id=${entry.trace_id} span_id=${entry.span_id}]` : '';
        console.log(`[${entry.timestamp}] ${entry.level}${traceInfo}: ${entry.message}`);
        // Log metadata if present
        const metadata = { ...entry };
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
class Logger {
    /**
     * Create a new logger.
     *
     * @param name - Logger name (usually module or component name)
     */
    constructor(name) {
        this.name = name;
    }
    /**
     * Log a debug message.
     *
     * @param message - Log message
     * @param metadata - Additional metadata
     */
    debug(message, metadata) {
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
    info(message, metadata) {
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
    warn(message, metadata) {
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
    error(message, error, metadata) {
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
exports.Logger = Logger;
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
function getLoggerWithTrace(name) {
    return new Logger(name);
}
