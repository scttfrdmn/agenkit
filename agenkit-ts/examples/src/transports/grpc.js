"use strict";
/**
 * gRPC Transport - Efficient RPC-based agent communication
 *
 * Provides high-performance communication using gRPC with Protocol Buffers.
 * Supports unary RPC, server streaming, and bidirectional streaming.
 *
 * @packageDocumentation
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.GrpcServer = exports.GrpcAgent = exports.GrpcTransportError = void 0;
const grpc = __importStar(require("@grpc/grpc-js"));
const protoLoader = __importStar(require("@grpc/proto-loader"));
const path = __importStar(require("path"));
/**
 * gRPC transport error
 */
class GrpcTransportError extends Error {
    constructor(message, code, details) {
        super(message);
        this.code = code;
        this.details = details;
        this.name = 'GrpcTransportError';
    }
}
exports.GrpcTransportError = GrpcTransportError;
/**
 * GrpcAgent - Client for communicating with remote agents via gRPC
 *
 * @example
 * ```typescript
 * const agent = new GrpcAgent('my-agent', {
 *   address: 'localhost:50051'
 * });
 *
 * const response = await agent.process({
 *   role: 'user',
 *   content: 'Hello'
 * });
 * ```
 */
class GrpcAgent {
    constructor(_name, config) {
        this._name = _name;
        this.config = config;
        this.connected = false;
        // Load proto file
        const PROTO_PATH = path.join(__dirname, '../../proto/agent.proto');
        this.packageDefinition = protoLoader.loadSync(PROTO_PATH, {
            keepCase: true,
            longs: String,
            enums: String,
            defaults: true,
            oneofs: true,
        });
        // Load gRPC package
        this.proto = grpc.loadPackageDefinition(this.packageDefinition).agenkit;
    }
    get name() {
        return this._name;
    }
    /**
     * Connect to the gRPC server
     */
    async connect() {
        if (this.connected) {
            return;
        }
        const credentials = this.config.useTLS
            ? this.config.credentials || grpc.credentials.createSsl()
            : grpc.credentials.createInsecure();
        this.client = new this.proto.AgentService(this.config.address, credentials);
        this.connected = true;
    }
    /**
     * Disconnect from the gRPC server
     */
    async close() {
        if (this.client) {
            this.client.close();
            this.connected = false;
        }
    }
    /**
     * Process a message using unary RPC
     */
    async process(message) {
        if (!this.connected) {
            await this.connect();
        }
        const request = {
            version: '1.0',
            id: this.generateId(),
            timestamp: new Date().toISOString(),
            method: 'process',
            agent_name: this.config.agentName || this._name,
            messages: [this.messageToProto(message)],
            metadata: message.metadata || {},
        };
        return new Promise((resolve, reject) => {
            const deadline = this.config.timeout
                ? Date.now() + this.config.timeout
                : undefined;
            this.client.Process(request, { deadline }, (error, response) => {
                if (error) {
                    reject(new GrpcTransportError(error.message, error.code, error.details));
                    return;
                }
                if (response.type === 'RESPONSE_TYPE_ERROR' || response.error) {
                    reject(new GrpcTransportError(response.error?.message || 'Unknown error', grpc.status.UNKNOWN, response.error?.details));
                    return;
                }
                resolve(this.protoToMessage(response.message));
            });
        });
    }
    /**
     * Process a message with streaming response
     */
    async *processStream(message) {
        if (!this.connected) {
            await this.connect();
        }
        const request = {
            version: '1.0',
            id: this.generateId(),
            timestamp: new Date().toISOString(),
            method: 'stream',
            agent_name: this.config.agentName || this._name,
            messages: [this.messageToProto(message)],
            metadata: message.metadata || {},
        };
        const call = this.client.ProcessStream(request);
        try {
            for await (const chunk of this.streamToAsyncIterator(call)) {
                if (chunk.type === 'CHUNK_TYPE_ERROR' || chunk.error) {
                    throw new GrpcTransportError(chunk.error?.message || 'Stream error', grpc.status.UNKNOWN, chunk.error?.details);
                }
                if (chunk.type === 'CHUNK_TYPE_END') {
                    break;
                }
                if (chunk.message) {
                    yield this.protoToMessage(chunk.message);
                }
            }
        }
        finally {
            call.cancel();
        }
    }
    /**
     * Convert gRPC stream to async iterator
     */
    async *streamToAsyncIterator(call) {
        const queue = [];
        let error = null;
        let done = false;
        call.on('data', (chunk) => {
            queue.push(chunk);
        });
        call.on('error', (err) => {
            error = err;
        });
        call.on('end', () => {
            done = true;
        });
        while (!done || queue.length > 0) {
            if (error) {
                throw error;
            }
            if (queue.length > 0) {
                yield queue.shift();
            }
            else {
                // Wait a bit before checking again
                await new Promise((resolve) => setTimeout(resolve, 10));
            }
        }
    }
    /**
     * Convert Message to proto format
     */
    messageToProto(message) {
        return {
            role: message.role,
            content: message.content,
            metadata: message.metadata || {},
            timestamp: new Date().toISOString(),
        };
    }
    /**
     * Convert proto message to Message
     */
    protoToMessage(proto) {
        return {
            role: proto.role,
            content: proto.content,
            metadata: proto.metadata || {},
        };
    }
    /**
     * Generate unique request ID
     */
    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
}
exports.GrpcAgent = GrpcAgent;
/**
 * GrpcServer - Server for hosting agents via gRPC
 *
 * @example
 * ```typescript
 * const server = new GrpcServer(myAgent, {
 *   address: '0.0.0.0:50051'
 * });
 *
 * await server.start();
 * ```
 */
class GrpcServer {
    constructor(agent, config) {
        this.agent = agent;
        this.config = config;
        // Load proto file
        const PROTO_PATH = path.join(__dirname, '../../proto/agent.proto');
        this.packageDefinition = protoLoader.loadSync(PROTO_PATH, {
            keepCase: true,
            longs: String,
            enums: String,
            defaults: true,
            oneofs: true,
        });
        // Load gRPC package
        this.proto = grpc.loadPackageDefinition(this.packageDefinition).agenkit;
        // Create server
        this.server = new grpc.Server();
        // Add service
        this.server.addService(this.proto.AgentService.service, {
            Process: this.handleProcess.bind(this),
            ProcessStream: this.handleProcessStream.bind(this),
            BidirectionalStream: this.handleBidirectionalStream.bind(this),
        });
    }
    /**
     * Start the gRPC server
     */
    async start() {
        const credentials = this.config.useTLS
            ? this.config.credentials || grpc.ServerCredentials.createSsl(null, [])
            : grpc.ServerCredentials.createInsecure();
        return new Promise((resolve, reject) => {
            this.server.bindAsync(this.config.address, credentials, (error, port) => {
                if (error) {
                    reject(error);
                    return;
                }
                this.server.start();
                resolve();
            });
        });
    }
    /**
     * Stop the gRPC server
     */
    async stop() {
        return new Promise((resolve) => {
            this.server.tryShutdown(() => {
                resolve();
            });
        });
    }
    /**
     * Handle unary Process RPC
     */
    async handleProcess(call, callback) {
        try {
            const request = call.request;
            const message = this.protoToMessage(request.messages[0]);
            const response = await this.agent.process(message);
            callback(null, {
                version: '1.0',
                id: request.id,
                timestamp: new Date().toISOString(),
                type: 'RESPONSE_TYPE_MESSAGE',
                message: this.messageToProto(response),
                metadata: response.metadata || {},
            });
        }
        catch (error) {
            callback(null, {
                version: '1.0',
                id: call.request.id,
                timestamp: new Date().toISOString(),
                type: 'RESPONSE_TYPE_ERROR',
                error: {
                    code: 'INTERNAL_ERROR',
                    message: error.message,
                    details: {},
                },
            });
        }
    }
    /**
     * Handle streaming ProcessStream RPC
     */
    async handleProcessStream(call) {
        try {
            const request = call.request;
            const message = this.protoToMessage(request.messages[0]);
            // Check if agent supports streaming
            if ('processStream' in this.agent && typeof this.agent.processStream === 'function') {
                const stream = this.agent.processStream(message);
                for await (const chunk of stream) {
                    call.write({
                        version: '1.0',
                        id: request.id,
                        timestamp: new Date().toISOString(),
                        type: 'CHUNK_TYPE_MESSAGE',
                        message: this.messageToProto(chunk),
                    });
                }
            }
            else {
                // Fallback to regular process
                const response = await this.agent.process(message);
                call.write({
                    version: '1.0',
                    id: request.id,
                    timestamp: new Date().toISOString(),
                    type: 'CHUNK_TYPE_MESSAGE',
                    message: this.messageToProto(response),
                });
            }
            // Send end marker
            call.write({
                version: '1.0',
                id: request.id,
                timestamp: new Date().toISOString(),
                type: 'CHUNK_TYPE_END',
            });
            call.end();
        }
        catch (error) {
            call.write({
                version: '1.0',
                id: call.request.id,
                timestamp: new Date().toISOString(),
                type: 'CHUNK_TYPE_ERROR',
                error: {
                    code: 'INTERNAL_ERROR',
                    message: error.message,
                    details: {},
                },
            });
            call.end();
        }
    }
    /**
     * Handle bidirectional BidirectionalStream RPC
     */
    async handleBidirectionalStream(call) {
        call.on('data', async (request) => {
            try {
                const message = this.protoToMessage(request.messages[0]);
                const response = await this.agent.process(message);
                call.write({
                    version: '1.0',
                    id: request.id,
                    timestamp: new Date().toISOString(),
                    type: 'RESPONSE_TYPE_MESSAGE',
                    message: this.messageToProto(response),
                    metadata: response.metadata || {},
                });
            }
            catch (error) {
                call.write({
                    version: '1.0',
                    id: request.id,
                    timestamp: new Date().toISOString(),
                    type: 'RESPONSE_TYPE_ERROR',
                    error: {
                        code: 'INTERNAL_ERROR',
                        message: error.message,
                        details: {},
                    },
                });
            }
        });
        call.on('end', () => {
            call.end();
        });
        call.on('error', (error) => {
            console.error('Bidirectional stream error:', error);
            call.end();
        });
    }
    /**
     * Convert proto message to Message
     */
    protoToMessage(proto) {
        return {
            role: proto.role,
            content: proto.content,
            metadata: proto.metadata || {},
        };
    }
    /**
     * Convert Message to proto format
     */
    messageToProto(message) {
        return {
            role: message.role,
            content: message.content,
            metadata: message.metadata || {},
            timestamp: new Date().toISOString(),
        };
    }
}
exports.GrpcServer = GrpcServer;
