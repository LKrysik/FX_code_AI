/**
 * Graph Store
 * ===========
 * Manages strategy graph state for the visual strategy builder.
 * Handles optimistic updates, server sync, and graph validation.
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Node, Edge } from 'reactflow';

export interface GraphNodeData {
  id: string;
  node_type: string;
  label: string;
  [key: string]: any;
}

export interface GraphEdgeData {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

export interface StrategyBlueprint {
  id?: string;
  name: string;
  version: string;
  description?: string;
  graph: {
    name: string;
    version: string;
    description?: string;
    nodes: GraphNodeData[];
    edges: GraphEdgeData[];
  };
  tags?: string[];
  is_template?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

interface GraphState {
  // Current graph state
  nodes: Node[];
  edges: Edge[];
  blueprint: StrategyBlueprint | null;

  // UI state
  selectedNodeId: string | null;
  isDirty: boolean;
  lastSaved: string | null;

  // Loading states
  saving: boolean;
  loading: boolean;
  validating: boolean;

  // Error states
  saveError: string | null;
  loadError: string | null;
  validationError: string | null;

  // Validation state
  validationResult: ValidationResult;

  // Draft management
  hasUnsavedChanges: boolean;
  draftName: string;
}

interface GraphActions {
  // Node/Edge management
  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  addNode: (node: Node) => void;
  updateNode: (nodeId: string, updates: Partial<Node>) => void;
  removeNode: (nodeId: string) => void;
  addEdge: (edge: Edge) => void;
  removeEdge: (edgeId: string) => void;

  // Blueprint management
  setBlueprint: (blueprint: StrategyBlueprint | null) => void;
  updateBlueprint: (updates: Partial<StrategyBlueprint>) => void;

  // UI state management
  setSelectedNodeId: (nodeId: string | null) => void;
  setDirty: (dirty: boolean) => void;

  // Async actions
  saveBlueprint: (name?: string) => Promise<void>;
  loadBlueprint: (blueprintId: string) => Promise<void>;
  createBlueprint: (name: string) => Promise<void>;
  validateGraph: () => Promise<ValidationResult>;

  // Draft management
  saveDraft: () => void;
  loadDraft: () => void;
  clearDraft: () => void;

  // Utility actions
  reset: () => void;
  exportGraph: () => StrategyBlueprint;
  importGraph: (blueprint: StrategyBlueprint) => void;
}

const initialState: GraphState = {
  nodes: [],
  edges: [],
  blueprint: null,

  selectedNodeId: null,
  isDirty: false,
  lastSaved: null,

  saving: false,
  loading: false,
  validating: false,

  saveError: null,
  loadError: null,
  validationError: null,

  validationResult: {
    isValid: true,
    errors: [],
    warnings: []
  },

  hasUnsavedChanges: false,
  draftName: 'Untitled Strategy'
};

export const useGraphStore = create<GraphState & GraphActions>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Node/Edge management
      setNodes: (nodes: Node[]) => {
        set({ nodes, isDirty: true, hasUnsavedChanges: true });
      },

      setEdges: (edges: Edge[]) => {
        set({ edges, isDirty: true, hasUnsavedChanges: true });
      },

      addNode: (node: Node) => {
        const { nodes } = get();
        set({
          nodes: [...nodes, node],
          isDirty: true,
          hasUnsavedChanges: true
        });
      },

      updateNode: (nodeId: string, updates: Partial<Node>) => {
        const { nodes } = get();
        const updatedNodes = nodes.map(node =>
          node.id === nodeId ? { ...node, ...updates } : node
        );
        set({
          nodes: updatedNodes,
          isDirty: true,
          hasUnsavedChanges: true
        });
      },

      removeNode: (nodeId: string) => {
        const { nodes, edges } = get();
        const filteredNodes = nodes.filter(node => node.id !== nodeId);
        const filteredEdges = edges.filter(edge =>
          edge.source !== nodeId && edge.target !== nodeId
        );
        set({
          nodes: filteredNodes,
          edges: filteredEdges,
          isDirty: true,
          hasUnsavedChanges: true,
          selectedNodeId: get().selectedNodeId === nodeId ? null : get().selectedNodeId
        });
      },

      addEdge: (edge: Edge) => {
        const { edges } = get();
        set({
          edges: [...edges, edge],
          isDirty: true,
          hasUnsavedChanges: true
        });
      },

      removeEdge: (edgeId: string) => {
        const { edges } = get();
        const filteredEdges = edges.filter(edge => edge.id !== edgeId);
        set({
          edges: filteredEdges,
          isDirty: true,
          hasUnsavedChanges: true
        });
      },

      // Blueprint management
      setBlueprint: (blueprint: StrategyBlueprint | null) => {
        if (blueprint) {
          // Convert blueprint graph to ReactFlow format
          const nodes: Node[] = blueprint.graph.nodes.map(nodeData => ({
            id: nodeData.id,
            type: nodeData.node_type.split('_')[0], // Extract base type (data_source, indicator, etc.)
            position: nodeData.position || { x: 100, y: 100 },
            data: nodeData
          }));

          const edges: Edge[] = blueprint.graph.edges.map(edgeData => ({
            id: edgeData.id,
            source: edgeData.source,
            target: edgeData.target,
            sourceHandle: edgeData.sourceHandle,
            targetHandle: edgeData.targetHandle
          }));

          set({
            blueprint,
            nodes,
            edges,
            isDirty: false,
            hasUnsavedChanges: false,
            lastSaved: blueprint.updated_at || new Date().toISOString(),
            draftName: blueprint.name
          });
        } else {
          set({
            blueprint: null,
            nodes: [],
            edges: [],
            isDirty: false,
            hasUnsavedChanges: false,
            lastSaved: null,
            draftName: 'Untitled Strategy'
          });
        }
      },

      updateBlueprint: (updates: Partial<StrategyBlueprint>) => {
        const { blueprint } = get();
        if (blueprint) {
          set({
            blueprint: { ...blueprint, ...updates },
            isDirty: true,
            hasUnsavedChanges: true
          });
        }
      },

      // UI state management
      setSelectedNodeId: (nodeId: string | null) => {
        set({ selectedNodeId: nodeId });
      },

      setDirty: (dirty: boolean) => {
        set({ isDirty: dirty });
      },

      // Async actions
      saveBlueprint: async (name?: string) => {
        const { blueprint, nodes, edges, draftName } = get();

        set({ saving: true, saveError: null });

        try {
          const blueprintName = name || draftName;
          const graphData = {
            name: blueprintName,
            version: "1.0.0",
            description: `Strategy blueprint created in Strategy Builder`,
            nodes: nodes.map(node => ({
              id: node.id,
              node_type: node.data.node_type,
              position: node.position,
              ...node.data
            })),
            edges: edges.map(edge => ({
              id: edge.id,
              source: edge.source,
              target: edge.target,
              sourceHandle: edge.sourceHandle,
              targetHandle: edge.targetHandle
            }))
          };

          // Call the strategy blueprints API
          const response = await fetch('/api/strategy-blueprints/', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              name: blueprintName,
              graph: graphData
            })
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to save blueprint');
          }

          const result = await response.json();
          const savedBlueprint: StrategyBlueprint = {
            id: result.blueprint.id,
            name: result.blueprint.name,
            version: result.blueprint.version,
            description: result.blueprint.description,
            graph: graphData,
            created_at: result.blueprint.created_at,
            updated_at: result.blueprint.updated_at
          };

          set({
            blueprint: savedBlueprint,
            saving: false,
            isDirty: false,
            hasUnsavedChanges: false,
            lastSaved: new Date().toISOString(),
            draftName: blueprintName
          });

        } catch (error: any) {
          set({
            saving: false,
            saveError: error.message || 'Failed to save blueprint'
          });
          throw error;
        }
      },

      loadBlueprint: async (blueprintId: string) => {
        set({ loading: true, loadError: null });

        try {
          const response = await fetch(`/api/strategy-blueprints/${blueprintId}`);

          if (!response.ok) {
            throw new Error('Failed to load blueprint');
          }

          const result = await response.json();
          const blueprint = result.blueprint;

          get().setBlueprint(blueprint);
          set({ loading: false });

        } catch (error: any) {
          set({
            loading: false,
            loadError: error.message || 'Failed to load blueprint'
          });
          throw error;
        }
      },

      createBlueprint: async (name: string) => {
        // Reset to empty state with new name
        set({
          ...initialState,
          draftName: name,
          blueprint: {
            name,
            version: "1.0.0",
            graph: {
              name,
              version: "1.0.0",
              nodes: [],
              edges: []
            }
          }
        });
      },

      validateGraph: async () => {
        const { nodes, edges } = get();

        set({ validating: true, validationError: null });

        try {
          // Convert to graph format for validation
          const graphData = {
            name: "validation",
            nodes: nodes.map(node => ({
              id: node.id,
              node_type: node.data.node_type,
              position: node.position,
              ...node.data
            })),
            edges: edges.map(edge => ({
              id: edge.id,
              source: edge.source,
              target: edge.target,
              sourceHandle: edge.sourceHandle,
              targetHandle: edge.targetHandle
            }))
          };

          // Call validation endpoint
          const response = await fetch('/api/strategy-blueprints/validate', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ graph: graphData })
          });

          const result = await response.json();
          const validationResult: ValidationResult = {
            isValid: result.validation.valid,
            errors: result.validation.errors.map((e: any) => e.message),
            warnings: result.validation.warnings.map((w: any) => w.message)
          };

          set({
            validationResult,
            validating: false
          });

          return validationResult;

        } catch (error: any) {
          const validationResult: ValidationResult = {
            isValid: false,
            errors: [error.message || 'Validation failed'],
            warnings: []
          };

          set({
            validationResult,
            validating: false,
            validationError: error.message || 'Validation failed'
          });

          return validationResult;
        }
      },

      // Draft management
      saveDraft: () => {
        const { nodes, edges, blueprint, draftName } = get();
        const draft = {
          nodes,
          edges,
          blueprint,
          draftName,
          timestamp: new Date().toISOString()
        };

        try {
          localStorage.setItem('strategy-builder-draft', JSON.stringify(draft));
        } catch (error) {
          console.warn('Failed to save draft to localStorage:', error);
        }
      },

      loadDraft: () => {
        try {
          const draftJson = localStorage.getItem('strategy-builder-draft');
          if (draftJson) {
            const draft = JSON.parse(draftJson);
            set({
              nodes: draft.nodes || [],
              edges: draft.edges || [],
              blueprint: draft.blueprint || null,
              draftName: draft.draftName || 'Untitled Strategy',
              hasUnsavedChanges: true
            });
          }
        } catch (error) {
          console.warn('Failed to load draft from localStorage:', error);
        }
      },

      clearDraft: () => {
        try {
          localStorage.removeItem('strategy-builder-draft');
        } catch (error) {
          console.warn('Failed to clear draft from localStorage:', error);
        }
      },

      // Utility actions
      reset: () => {
        set(initialState);
      },

      exportGraph: () => {
        const { nodes, edges, blueprint, draftName } = get();
        return {
          name: draftName,
          version: "1.0.0",
          graph: {
            name: draftName,
            version: "1.0.0",
            nodes: nodes.map(node => ({
              id: node.id,
              node_type: node.data.node_type,
              position: node.position,
              ...node.data
            })),
            edges: edges.map(edge => ({
              id: edge.id,
              source: edge.source,
              target: edge.target,
              sourceHandle: edge.sourceHandle,
              targetHandle: edge.targetHandle
            }))
          },
          ...blueprint
        };
      },

      importGraph: (blueprint: StrategyBlueprint) => {
        get().setBlueprint(blueprint);
      }
    }),
    {
      name: 'graph-store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

// Selectors for optimized re-renders
export const useGraphNodes = () => useGraphStore(state => state.nodes);
export const useGraphEdges = () => useGraphStore(state => state.edges);
export const useBlueprint = () => useGraphStore(state => state.blueprint);
export const useSelectedNodeId = () => useGraphStore(state => state.selectedNodeId);
export const useGraphDirty = () => useGraphStore(state => state.isDirty);
export const useValidationResult = () => useGraphStore(state => state.validationResult);

// Loading states
export const useGraphLoadingStates = () => useGraphStore(state => ({
  saving: state.saving,
  loading: state.loading,
  validating: state.validating,
}));

// Error states
export const useGraphErrors = () => useGraphStore(state => ({
  saveError: state.saveError,
  loadError: state.loadError,
  validationError: state.validationError,
}));

// Actions
export const useGraphActions = () => useGraphStore(state => ({
  // Node/Edge actions
  setNodes: state.setNodes,
  setEdges: state.setEdges,
  addNode: state.addNode,
  updateNode: state.updateNode,
  removeNode: state.removeNode,
  addEdge: state.addEdge,
  removeEdge: state.removeEdge,

  // Blueprint actions
  setBlueprint: state.setBlueprint,
  updateBlueprint: state.updateBlueprint,

  // UI actions
  setSelectedNodeId: state.setSelectedNodeId,
  setDirty: state.setDirty,

  // Async actions
  saveBlueprint: state.saveBlueprint,
  loadBlueprint: state.loadBlueprint,
  createBlueprint: state.createBlueprint,
  validateGraph: state.validateGraph,

  // Draft actions
  saveDraft: state.saveDraft,
  loadDraft: state.loadDraft,
  clearDraft: state.clearDraft,

  // Utility actions
  reset: state.reset,
  exportGraph: state.exportGraph,
  importGraph: state.importGraph,
}));

// Computed selectors
export const useNodeCount = () => useGraphStore(state => state.nodes.length);
export const useEdgeCount = () => useGraphStore(state => state.edges.length);
export const useIsValid = () => useGraphStore(state => state.validationResult.isValid);
export const useHasErrors = () => useGraphStore(state => state.validationResult.errors.length > 0);
export const useHasWarnings = () => useGraphStore(state => state.validationResult.warnings.length > 0);