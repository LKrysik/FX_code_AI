export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  infos: string[];
}

export function validateStrategy(nodes: any[], edges: any[]): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  const infos: string[] = [];

  // Basic validation
  if (nodes.length === 0) {
    errors.push('Strategy must have at least one node');
  }

  // Check for disconnected nodes
  const connectedNodeIds = new Set();
  edges.forEach(edge => {
    connectedNodeIds.add(edge.source);
    connectedNodeIds.add(edge.target);
  });

  const disconnectedNodes = nodes.filter(node => !connectedNodeIds.has(node.id));
  if (disconnectedNodes.length > 0) {
    warnings.push(`${disconnectedNodes.length} disconnected node(s) found`);
  }

  // Check for action nodes
  const actionNodes = nodes.filter(node => node.type === 'action');
  if (actionNodes.length === 0) {
    warnings.push('Strategy has no action nodes - no trades will be executed');
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    infos
  };
}

export function updateNodesWithValidationErrors(nodes: any[], validationResult: ValidationResult): any[] {
  return nodes.map(node => ({
    ...node,
    data: {
      ...node.data,
      validation_errors: validationResult.errors.length > 0 ? ['Validation failed'] : undefined
    }
  }));
}