/**
 * Safety and security module for agent operations.
 *
 * Provides comprehensive security features:
 * - Audit logging with structured events
 * - Anomaly detection for suspicious behavior
 * - Input validation and prompt injection defense
 * - Output validation and sensitive data redaction
 * - Permission-based access control (RBAC)
 * - Sandboxing for agent execution
 */

// Audit logging
export {
  AuditEventType,
  AuditSeverity,
  AuditEvent,
  SecurityAuditLoggerConfig,
  SecurityAuditLogger,
  getAuditLogger,
  configureAuditLogger,
} from './audit';

// Anomaly detection
export {
  SecurityEvent,
  AnomalyDetector,
  AnomalyDetectionMiddleware,
  anomalyDetection,
} from './anomaly-detection';

// Input validation
export {
  ValidationError,
  PromptInjectionDetector,
  ContentFilter,
  InputValidationMiddleware,
  inputValidation,
} from './input-validation';

// Output validation
export {
  OutputValidationError,
  SchemaValidator,
  SensitiveDataRedactor,
  OutputValidationMiddleware,
  outputValidation,
} from './output-validation';

// Permissions and sandboxing
export {
  Permission,
  Role,
  ROLE_PERMISSIONS,
  PermissionDeniedError,
  Sandbox,
  PermissionMiddleware,
  permissions,
} from './permissions';
