/**
 * Checkpoint storage implementations.
 *
 * Provides in-memory and file-based storage for checkpoints.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  Checkpoint,
  CheckpointStorage,
  checkpointFromJson,
  checkpointToJson,
} from './checkpoint';

/**
 * In-memory checkpoint storage.
 *
 * Good for:
 * - Testing
 * - Development
 * - Short-lived sessions
 *
 * Not suitable for:
 * - Production (no persistence)
 * - Long-running agents (lost on restart)
 *
 * Example:
 *   const storage = new InMemoryCheckpointStorage();
 *   await storage.save(checkpoint);
 *   const loaded = await storage.load(checkpoint.checkpointId);
 */
export class InMemoryCheckpointStorage implements CheckpointStorage {
  // checkpoint_id -> Checkpoint
  private checkpoints: Map<string, Checkpoint> = new Map();

  // session_id -> list of checkpoint_ids (ordered by timestamp)
  private sessionCheckpoints: Map<string, string[]> = new Map();

  /**
   * Save checkpoint to memory.
   */
  async save(checkpoint: Checkpoint): Promise<void> {
    this.checkpoints.set(checkpoint.checkpointId, checkpoint);

    // Add to session index
    if (!this.sessionCheckpoints.has(checkpoint.sessionId)) {
      this.sessionCheckpoints.set(checkpoint.sessionId, []);
    }

    const sessionCpts = this.sessionCheckpoints.get(checkpoint.sessionId)!;
    if (!sessionCpts.includes(checkpoint.checkpointId)) {
      sessionCpts.push(checkpoint.checkpointId);

      // Sort by timestamp (most recent first)
      sessionCpts.sort((a, b) => {
        const cptA = this.checkpoints.get(a)!;
        const cptB = this.checkpoints.get(b)!;
        return cptB.timestamp.getTime() - cptA.timestamp.getTime();
      });
    }
  }

  /**
   * Load checkpoint from memory.
   */
  async load(checkpointId: string): Promise<Checkpoint | undefined> {
    return this.checkpoints.get(checkpointId);
  }

  /**
   * List checkpoints for session.
   */
  async listCheckpoints(sessionId: string, limit?: number): Promise<Checkpoint[]> {
    const checkpointIds = this.sessionCheckpoints.get(sessionId) || [];

    const idsToLoad = limit ? checkpointIds.slice(0, limit) : checkpointIds;

    return idsToLoad
      .map((id) => this.checkpoints.get(id))
      .filter((cpt): cpt is Checkpoint => cpt !== undefined);
  }

  /**
   * Get latest checkpoint for session.
   */
  async getLatest(sessionId: string): Promise<Checkpoint | undefined> {
    const checkpoints = await this.listCheckpoints(sessionId, 1);
    return checkpoints[0];
  }

  /**
   * Delete checkpoint.
   */
  async delete(checkpointId: string): Promise<boolean> {
    const checkpoint = this.checkpoints.get(checkpointId);
    if (!checkpoint) {
      return false;
    }

    this.checkpoints.delete(checkpointId);

    // Remove from session index
    const sessionCpts = this.sessionCheckpoints.get(checkpoint.sessionId);
    if (sessionCpts) {
      const index = sessionCpts.indexOf(checkpointId);
      if (index !== -1) {
        sessionCpts.splice(index, 1);
      }
    }

    return true;
  }

  /**
   * Delete all checkpoints for session.
   */
  async deleteSession(sessionId: string): Promise<number> {
    const checkpointIds = this.sessionCheckpoints.get(sessionId) || [];
    const count = checkpointIds.length;

    for (const checkpointId of checkpointIds) {
      this.checkpoints.delete(checkpointId);
    }

    this.sessionCheckpoints.delete(sessionId);

    return count;
  }

  /**
   * Get checkpoint history by following parent links.
   */
  async getCheckpointHistory(
    checkpointId: string,
    maxDepth: number = 10,
  ): Promise<Checkpoint[]> {
    const history: Checkpoint[] = [];
    let currentId: string | undefined = checkpointId;

    for (let i = 0; i < maxDepth; i++) {
      if (!currentId) break;

      const checkpoint = await this.load(currentId);
      if (!checkpoint) break;

      history.push(checkpoint);

      if (!checkpoint.parentCheckpointId) break;

      currentId = checkpoint.parentCheckpointId;
    }

    return history;
  }

  /**
   * Get storage statistics.
   */
  getStats(): {
    totalCheckpoints: number;
    totalSessions: number;
    checkpointsPerSession: Record<string, number>;
  } {
    const checkpointsPerSession: Record<string, number> = {};

    for (const [sessionId, checkpointIds] of this.sessionCheckpoints.entries()) {
      checkpointsPerSession[sessionId] = checkpointIds.length;
    }

    return {
      totalCheckpoints: this.checkpoints.size,
      totalSessions: this.sessionCheckpoints.size,
      checkpointsPerSession,
    };
  }
}

/**
 * File-based checkpoint storage.
 *
 * Stores each checkpoint as a JSON file on disk for persistence.
 *
 * Directory structure:
 *   checkpoint_dir/
 *     {session_id}/
 *       {checkpoint_id}.json
 *       {checkpoint_id}.json
 *       ...
 *
 * Good for:
 * - Production (persistent)
 * - Single-machine deployments
 * - Development with persistence
 *
 * Example:
 *   const storage = new FileCheckpointStorage('./checkpoints');
 *   await storage.save(checkpoint);
 *   const loaded = await storage.load(checkpoint.checkpointId);
 */
export class FileCheckpointStorage implements CheckpointStorage {
  private checkpointDir: string;

  constructor(checkpointDir: string = './checkpoints') {
    this.checkpointDir = checkpointDir;

    // Create checkpoint directory if it doesn't exist
    if (!fs.existsSync(this.checkpointDir)) {
      fs.mkdirSync(this.checkpointDir, { recursive: true });
    }
  }

  /**
   * Get directory for session checkpoints.
   */
  private getSessionDir(sessionId: string): string {
    const sessionDir = path.join(this.checkpointDir, sessionId);
    if (!fs.existsSync(sessionDir)) {
      fs.mkdirSync(sessionDir, { recursive: true });
    }
    return sessionDir;
  }

  /**
   * Get file path for checkpoint.
   */
  private getCheckpointPath(sessionId: string, checkpointId: string): string {
    return path.join(this.getSessionDir(sessionId), `${checkpointId}.json`);
  }

  /**
   * Save checkpoint to file.
   */
  async save(checkpoint: Checkpoint): Promise<void> {
    const checkpointPath = this.getCheckpointPath(checkpoint.sessionId, checkpoint.checkpointId);
    const jsonStr = checkpointToJson(checkpoint);
    fs.writeFileSync(checkpointPath, jsonStr, 'utf-8');
  }

  /**
   * Load checkpoint from file.
   */
  async load(checkpointId: string): Promise<Checkpoint | undefined> {
    // Need to search through session directories
    if (!fs.existsSync(this.checkpointDir)) {
      return undefined;
    }

    const sessionDirs = fs.readdirSync(this.checkpointDir);

    for (const sessionDir of sessionDirs) {
      const sessionPath = path.join(this.checkpointDir, sessionDir);
      if (!fs.statSync(sessionPath).isDirectory()) {
        continue;
      }

      const checkpointPath = path.join(sessionPath, `${checkpointId}.json`);
      if (fs.existsSync(checkpointPath)) {
        const jsonStr = fs.readFileSync(checkpointPath, 'utf-8');
        return checkpointFromJson(jsonStr);
      }
    }

    return undefined;
  }

  /**
   * List checkpoints for session.
   */
  async listCheckpoints(sessionId: string, limit?: number): Promise<Checkpoint[]> {
    const sessionDir = this.getSessionDir(sessionId);

    if (!fs.existsSync(sessionDir)) {
      return [];
    }

    // Load all checkpoints
    const checkpoints: Checkpoint[] = [];
    const files = fs.readdirSync(sessionDir);

    for (const file of files) {
      if (!file.endsWith('.json')) continue;

      const checkpointPath = path.join(sessionDir, file);
      const jsonStr = fs.readFileSync(checkpointPath, 'utf-8');
      const checkpoint = checkpointFromJson(jsonStr);
      checkpoints.push(checkpoint);
    }

    // Sort by timestamp (most recent first)
    checkpoints.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

    if (limit) {
      return checkpoints.slice(0, limit);
    }

    return checkpoints;
  }

  /**
   * Get latest checkpoint for session.
   */
  async getLatest(sessionId: string): Promise<Checkpoint | undefined> {
    const checkpoints = await this.listCheckpoints(sessionId, 1);
    return checkpoints[0];
  }

  /**
   * Delete checkpoint file.
   */
  async delete(checkpointId: string): Promise<boolean> {
    // Search through session directories
    if (!fs.existsSync(this.checkpointDir)) {
      return false;
    }

    const sessionDirs = fs.readdirSync(this.checkpointDir);

    for (const sessionDir of sessionDirs) {
      const sessionPath = path.join(this.checkpointDir, sessionDir);
      if (!fs.statSync(sessionPath).isDirectory()) {
        continue;
      }

      const checkpointPath = path.join(sessionPath, `${checkpointId}.json`);
      if (fs.existsSync(checkpointPath)) {
        fs.unlinkSync(checkpointPath);
        return true;
      }
    }

    return false;
  }

  /**
   * Delete all checkpoints for session.
   */
  async deleteSession(sessionId: string): Promise<number> {
    const sessionDir = this.getSessionDir(sessionId);

    if (!fs.existsSync(sessionDir)) {
      return 0;
    }

    // Count and delete checkpoint files
    const files = fs.readdirSync(sessionDir).filter((f) => f.endsWith('.json'));
    const count = files.length;

    for (const file of files) {
      const filePath = path.join(sessionDir, file);
      fs.unlinkSync(filePath);
    }

    // Remove session directory if empty
    try {
      fs.rmdirSync(sessionDir);
    } catch {
      // Directory not empty (might have other files)
    }

    return count;
  }

  /**
   * Get checkpoint history by following parent links.
   */
  async getCheckpointHistory(
    checkpointId: string,
    maxDepth: number = 10,
  ): Promise<Checkpoint[]> {
    const history: Checkpoint[] = [];
    let currentId: string | undefined = checkpointId;

    for (let i = 0; i < maxDepth; i++) {
      if (!currentId) break;

      const checkpoint = await this.load(currentId);
      if (!checkpoint) break;

      history.push(checkpoint);

      if (!checkpoint.parentCheckpointId) break;

      currentId = checkpoint.parentCheckpointId;
    }

    return history;
  }

  /**
   * Get storage statistics.
   */
  getStats(): {
    totalSessions: number;
    totalCheckpoints: number;
    checkpointDir: string;
    diskUsageBytes: number;
  } {
    const stats = {
      totalSessions: 0,
      totalCheckpoints: 0,
      checkpointDir: this.checkpointDir,
      diskUsageBytes: 0,
    };

    if (!fs.existsSync(this.checkpointDir)) {
      return stats;
    }

    const sessionDirs = fs.readdirSync(this.checkpointDir);

    for (const sessionDir of sessionDirs) {
      const sessionPath = path.join(this.checkpointDir, sessionDir);
      if (!fs.statSync(sessionPath).isDirectory()) {
        continue;
      }

      stats.totalSessions++;

      const files = fs.readdirSync(sessionPath);
      for (const file of files) {
        if (!file.endsWith('.json')) continue;

        stats.totalCheckpoints++;
        const filePath = path.join(sessionPath, file);
        stats.diskUsageBytes += fs.statSync(filePath).size;
      }
    }

    return stats;
  }
}
