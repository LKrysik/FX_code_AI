/**
 * Validation Channel - Throttling and Delta Serialization
 * ======================================================
 *
 * Provides efficient validation updates with throttling and delta serialization
 * to reduce server load and improve performance for large graphs.
 */

import { Node, Edge } from 'reactflow';

export interface GraphDelta {
  nodes: {
    added: Node[];
    updated: Node[];
    removed: string[];
  };
  edges: {
    added: Edge[];
    updated: Edge[];
    removed: string[];
  };
  timestamp: number;
}

export interface ValidationRequest {
  graphId: string;
  delta: GraphDelta;
  fullGraph?: {
    nodes: Node[];
    edges: Edge[];
  };
}

export interface ValidationResponse {
  graphId: string;
  isValid: boolean;
  errors: Array<{
    type: string;
    message: string;
    nodeId?: string;
    edgeId?: string;
  }>;
  warnings: Array<{
    type: string;
    message: string;
    nodeId?: string;
    edgeId?: string;
  }>;
  timestamp: number;
}

class ValidationChannel {
  private pendingRequests = new Map<string, ValidationRequest>();
  private activeRequests = new Map<string, Promise<ValidationResponse>>();
  private requestTimeouts = new Map<string, NodeJS.Timeout>();
  private lastFullValidation = new Map<string, number>();
  private deltaBuffer = new Map<string, GraphDelta>();

  // Configuration
  private readonly THROTTLE_MS = 300;
  private readonly FULL_VALIDATION_INTERVAL_MS = 5000; // Force full validation every 5 seconds
  private readonly MAX_BUFFER_SIZE = 10;

  /**
   * Queue a validation request with delta serialization
   */
  async queueValidation(
    graphId: string,
    currentNodes: Node[],
    currentEdges: Edge[],
    previousNodes: Node[],
    previousEdges: Edge[]
  ): Promise<ValidationResponse> {
    // Calculate delta
    const delta = this.calculateDelta(currentNodes, currentEdges, previousNodes, previousEdges);

    // Check if we need full validation
    const lastFull = this.lastFullValidation.get(graphId) || 0;
    const needsFullValidation = Date.now() - lastFull > this.FULL_VALIDATION_INTERVAL_MS;

    const request: ValidationRequest = {
      graphId,
      delta,
      fullGraph: needsFullValidation ? { nodes: currentNodes, edges: currentEdges } : undefined
    };

    // Cancel any pending request for this graph
    this.cancelPendingRequest(graphId);

    // Buffer the delta
    this.bufferDelta(graphId, delta);

    // Set up throttled request
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(async () => {
        try {
          // Combine buffered deltas
          const combinedDelta = this.getCombinedDelta(graphId);

          const finalRequest: ValidationRequest = {
            graphId,
            delta: combinedDelta,
            fullGraph: needsFullValidation ? { nodes: currentNodes, edges: currentEdges } : undefined
          };

          const response = await this.sendValidationRequest(finalRequest);

          if (needsFullValidation) {
            this.lastFullValidation.set(graphId, Date.now());
          }

          // Clear buffer
          this.clearDeltaBuffer(graphId);

          resolve(response);
        } catch (error) {
          reject(error);
        }
      }, this.THROTTLE_MS);

      this.requestTimeouts.set(graphId, timeout);
      this.pendingRequests.set(graphId, request);
    });
  }

  /**
   * Send validation request to server
   */
  private async sendValidationRequest(request: ValidationRequest): Promise<ValidationResponse> {
    // Check if there's already an active request for this graph
    const activeRequest = this.activeRequests.get(request.graphId);
    if (activeRequest) {
      return activeRequest;
    }

    // Create new request
    const promise = this.doSendValidationRequest(request);
    this.activeRequests.set(request.graphId, promise);

    try {
      return await promise;
    } finally {
      this.activeRequests.delete(request.graphId);
    }
  }

  /**
   * Actually send the HTTP request
   */
  private async doSendValidationRequest(request: ValidationRequest): Promise<ValidationResponse> {
    const endpoint = request.fullGraph
      ? '/api/strategy-blueprints/validate'
      : '/api/strategy-blueprints/validate-delta';

    const payload = request.fullGraph ? {
      graph: request.fullGraph
    } : {
      graphId: request.graphId,
      delta: request.delta
    };

    // Reuse localStorage access token when available; cookies cover primary auth
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error(`Validation request failed: ${response.status}`);
      }

      const result = await response.json();

      return {
        graphId: request.graphId,
        isValid: result.validation?.valid ?? false,
        errors: result.validation?.errors ?? [],
        warnings: result.validation?.warnings ?? [],
        timestamp: Date.now()
      };
    } catch (error) {
      console.error('Validation request failed:', error);
      throw error;
    }
  }

  /**
   * Calculate delta between current and previous graph state
   */
  private calculateDelta(
    currentNodes: Node[],
    currentEdges: Edge[],
    previousNodes: Node[],
    previousEdges: Edge[]
  ): GraphDelta {
    const currentNodeMap = new Map(currentNodes.map(n => [n.id, n]));
    const previousNodeMap = new Map(previousNodes.map(n => [n.id, n]));
    const currentEdgeMap = new Map(currentEdges.map(e => [e.id, e]));
    const previousEdgeMap = new Map(previousEdges.map(e => [e.id, e]));

    // Calculate node changes
    const addedNodes = currentNodes.filter(n => !previousNodeMap.has(n.id));
    const updatedNodes = currentNodes.filter(n => {
      const prev = previousNodeMap.get(n.id);
      return prev && !this.nodesEqual(n, prev);
    });
    const removedNodeIds = previousNodes
      .filter(n => !currentNodeMap.has(n.id))
      .map(n => n.id);

    // Calculate edge changes
    const addedEdges = currentEdges.filter(e => !previousEdgeMap.has(e.id));
    const updatedEdges = currentEdges.filter(e => {
      const prev = previousEdgeMap.get(e.id);
      return prev && !this.edgesEqual(e, prev);
    });
    const removedEdgeIds = previousEdges
      .filter(e => !currentEdgeMap.has(e.id))
      .map(e => e.id);

    return {
      nodes: {
        added: addedNodes,
        updated: updatedNodes,
        removed: removedNodeIds
      },
      edges: {
        added: addedEdges,
        updated: updatedEdges,
        removed: removedEdgeIds
      },
      timestamp: Date.now()
    };
  }

  /**
   * Check if two nodes are equal (for delta calculation)
   */
  private nodesEqual(node1: Node, node2: Node): boolean {
    return (
      node1.type === node2.type &&
      node1.position.x === node2.position.x &&
      node1.position.y === node2.position.y &&
      JSON.stringify(node1.data) === JSON.stringify(node2.data)
    );
  }

  /**
   * Check if two edges are equal (for delta calculation)
   */
  private edgesEqual(edge1: Edge, edge2: Edge): boolean {
    return (
      edge1.source === edge2.source &&
      edge1.target === edge2.target &&
      edge1.sourceHandle === edge2.sourceHandle &&
      edge1.targetHandle === edge2.targetHandle
    );
  }

  /**
   * Buffer delta changes
   */
  private bufferDelta(graphId: string, delta: GraphDelta): void {
    const existing = this.deltaBuffer.get(graphId);
    if (existing) {
      // Merge deltas
      const merged: GraphDelta = {
        nodes: {
          added: [...existing.nodes.added, ...delta.nodes.added],
          updated: [...existing.nodes.updated, ...delta.nodes.updated],
          removed: [...existing.nodes.removed, ...delta.nodes.removed]
        },
        edges: {
          added: [...existing.edges.added, ...delta.edges.added],
          updated: [...existing.edges.updated, ...delta.edges.updated],
          removed: [...existing.edges.removed, ...delta.edges.removed]
        },
        timestamp: delta.timestamp
      };

      // Remove duplicates and limit buffer size
      merged.nodes.added = this.deduplicateNodes(merged.nodes.added);
      merged.edges.added = this.deduplicateEdges(merged.edges.added);

      if (merged.nodes.added.length + merged.edges.added.length > this.MAX_BUFFER_SIZE) {
        // If buffer gets too large, we'll send a full validation
        this.deltaBuffer.set(graphId, delta);
      } else {
        this.deltaBuffer.set(graphId, merged);
      }
    } else {
      this.deltaBuffer.set(graphId, delta);
    }
  }

  /**
   * Get combined delta from buffer
   */
  private getCombinedDelta(graphId: string): GraphDelta {
    return this.deltaBuffer.get(graphId) || {
      nodes: { added: [], updated: [], removed: [] },
      edges: { added: [], updated: [], removed: [] },
      timestamp: Date.now()
    };
  }

  /**
   * Clear delta buffer for a graph
   */
  private clearDeltaBuffer(graphId: string): void {
    this.deltaBuffer.delete(graphId);
  }

  /**
   * Remove duplicates from node arrays
   */
  private deduplicateNodes(nodes: Node[]): Node[] {
    const seen = new Set<string>();
    return nodes.filter(node => {
      if (seen.has(node.id)) {
        return false;
      }
      seen.add(node.id);
      return true;
    });
  }

  /**
   * Remove duplicates from edge arrays
   */
  private deduplicateEdges(edges: Edge[]): Edge[] {
    const seen = new Set<string>();
    return edges.filter(edge => {
      if (seen.has(edge.id)) {
        return false;
      }
      seen.add(edge.id);
      return true;
    });
  }

  /**
   * Cancel pending request for a graph
   */
  private cancelPendingRequest(graphId: string): void {
    const timeout = this.requestTimeouts.get(graphId);
    if (timeout) {
      clearTimeout(timeout);
      this.requestTimeouts.delete(graphId);
    }
    this.pendingRequests.delete(graphId);
  }

  /**
   * Clean up resources
   */
  cleanup(): void {
    // Clear all timeouts
    this.requestTimeouts.forEach(timeout => {
      clearTimeout(timeout);
    });

    // Clear all maps
    this.pendingRequests.clear();
    this.activeRequests.clear();
    this.requestTimeouts.clear();
    this.lastFullValidation.clear();
    this.deltaBuffer.clear();
  }

  /**
   * Get channel statistics
   */
  getStats(): {
    pendingRequests: number;
    activeRequests: number;
    bufferedGraphs: number;
  } {
    return {
      pendingRequests: this.pendingRequests.size,
      activeRequests: this.activeRequests.size,
      bufferedGraphs: this.deltaBuffer.size
    };
  }
}

// Global validation channel instance
export const validationChannel = new ValidationChannel();

// Cleanup on page unload
if (typeof window !== 'undefined') {
  window.addEventListener('beforeunload', () => {
    validationChannel.cleanup();
  });
}

// Export types
export type { ValidationChannel };
