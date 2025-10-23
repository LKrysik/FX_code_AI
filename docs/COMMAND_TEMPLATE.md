# Command Template v2.0 - AI Agent Execution Framework

This enhanced template addresses critical gaps in AI agent autonomous execution. It provides concrete guidance, implementation examples, and failure recovery procedures that AI agents need for reliable task completion.

## Core Philosophy
**Problem Solved**: Original template described WHAT to do but not HOW to do it, leading to inconsistent AI agent decisions and quality issues.

**Solution**: Add implementation templates, concrete success criteria, failure recovery procedures, and context analysis guidelines.

## Enhanced Structure

### Header
```yaml
---
description: "[Brief description of the command's purpose]"
ai_execution_complexity: "[LOW|MEDIUM|HIGH]"
requires_human_review: "[true|false]"
estimated_duration: "[minutes]"
dependencies: ["command1", "command2"]
---
```

### Title and Purpose
```markdown
# /[command_name] - [Short Title]

**Purpose**: [Detailed explanation of what the command does and why it exists]
**AI Agent Suitability**: [Explanation of why this task is suitable/challenging for autonomous execution]
**Human Oversight Level**: [None|Minimal|Moderate|High] - [Reasoning]
```

### Usage
```markdown
**Usage**: /[command_name] "[param1]" "[param2]" [optional flags]
**Example**: /[command_name] "user_requirement_01" --validate --dry-run
```

### Inputs and Validation
- **Required Inputs**: 
  - `param1` (string): [Description] - Must match pattern `[regex]`
  - `param2` (string): [Description] - Must be one of: [value1, value2, value3]
- **Optional Inputs**:
  - `--flag` (boolean): [Description] - Default: false
- **Pre-execution Validation**:
  - Check file existence requirements
  - Validate input format and constraints
  - Verify system state prerequisites

### Implementation Templates

#### **Code Structure Templates**
```markdown
**For Frontend Components:**
```typescript
// Template: src/components/[FeatureName]/[ComponentName].tsx
interface [ComponentName]Props {
  // Required props
}

export const [ComponentName]: React.FC<[ComponentName]Props> = () => {
  // Implementation pattern
};
```

**For Backend Services:**
```typescript
// Template: src/services/[ServiceName].ts
export class [ServiceName] {
  constructor(private dependencies: Dependencies) {}
  
  async [mainMethod](): Promise<Result> {
    // Implementation pattern with error handling
  }
}
```

**For Configuration Files:**
```json
// Template: config/[type]/[name].json
{
  "id": "[uuid]",
  "type": "[type]",
  "version": "1.0.0",
  // Standard structure
}
```

#### **File Organization Patterns**
- New features: `src/features/[feature-name]/`
- Shared components: `src/components/shared/`
- Services: `src/services/[domain]/`
- Types: `src/types/[domain]/`
- Tests: Follow same structure with `.test.ts` suffix

### Steps with Concrete Actions

1. **Context Analysis** (MANDATORY)
   - Read and analyze: `[list of required files]`
   - Identify existing patterns: `[specific patterns to look for]`
   - Check dependencies: `[dependency validation commands]`

2. **Implementation Planning**
   - Create file structure: `[specific directory creation commands]`
   - Define interfaces: `[required interface definitions]`
   - Plan integration points: `[specific integration requirements]`

3. **Core Implementation**
   - [Specific implementation steps with code examples]
   - [Error handling requirements]
   - [Performance considerations]

4. **Testing Implementation**
   - Unit tests: `[specific test file patterns]`
   - Integration tests: `[required test scenarios]`
   - Performance tests: `[benchmark requirements]`

5. **Validation and Integration**
   - Run verification commands: `[specific commands to execute]`
   - Check integration points: `[validation procedures]`
   - Performance validation: `[measurement commands]`

### Concrete Success Criteria

#### **Functional Requirements**
- [ ] All specified user interactions work correctly
- [ ] Edge cases handled: `[list specific edge cases]`
- [ ] Error conditions handled gracefully: `[list error scenarios]`
- [ ] Performance meets requirements: `[specific metrics]`

#### **Quality Gates**
- [ ] Test coverage ≥ [X]% with meaningful assertions
- [ ] No critical code quality issues (ESLint, TypeScript)
- [ ] All integration points validated
- [ ] Documentation updated and accurate

#### **Verification Commands**
```bash
# Run these commands to verify success:
npm test -- --coverage
npm run lint
npm run type-check
npm run e2e-test
```

### Failure Recovery Procedures

#### **Common Failure Scenarios**

**Scenario 1: Test Failures**
```markdown
**Symptoms**: Test suite fails during implementation
**Diagnosis**: Run `npm test -- --verbose` to identify specific failures
**Resolution Steps**:
1. Analyze failing test output
2. Check if business logic is correctly implemented
3. Verify test assertions are appropriate
4. Fix implementation or update tests (justify choice)
**Escalation**: If >50% of tests fail, stop and request human review
```

**Scenario 2: Integration Conflicts**
```markdown
**Symptoms**: New code breaks existing functionality
**Diagnosis**: Run full test suite and check error logs
**Resolution Steps**:
1. Identify conflicting dependencies
2. Analyze impact scope
3. Choose: refactor approach OR update integration points
4. Re-run integration tests
**Escalation**: If core architecture changes needed, request review
```

**Scenario 3: Performance Issues**
```markdown
**Symptoms**: Implementation doesn't meet performance requirements
**Diagnosis**: Profile critical code paths
**Resolution Steps**:
1. Identify bottlenecks using profiling tools
2. Apply optimization patterns: [list specific patterns]
3. Re-measure performance
4. Document trade-offs made
**Escalation**: If fundamental algorithm changes needed, request review
```

### Context Integration Guidelines

#### **Required File Analysis**
Before implementation, MUST analyze:
- `docs/MVP.md` - Understand user requirements
- `src/types/` - Check existing type definitions
- `config/` - Understand configuration patterns
- `tests/` - Study existing test patterns
- Related feature files - Understand architecture patterns

#### **Architecture Consistency Checks**
- Follow existing naming conventions: `[document patterns found]`
- Use established error handling patterns: `[reference examples]`
- Maintain dependency injection patterns: `[show usage]`
- Follow data flow patterns: `[document current approach]`

#### **Impact Assessment**
- Identify all files that import modified modules
- Check for breaking changes in public APIs
- Verify configuration changes don't break existing features
- Test integration with related features

### Reasoning and Decision Framework

#### **Decision Points Template**
For each major decision, document:
1. **Options Considered**: [List alternatives]
2. **Evaluation Criteria**: [Performance, maintainability, complexity]
3. **Choice Made**: [Selected option]
4. **Justification**: [Why this option was best]
5. **Trade-offs**: [What was sacrificed]
6. **Risk Assessment**: [Potential issues and mitigation]

### Output (Enhanced Receipt)

#### **Files Modified**
```markdown
**Created**:
- `path/to/file.ts` - [Purpose and key functionality]
- `path/to/test.ts` - [Test coverage scope]

**Modified**:
- `path/to/existing.ts` - [Changes made and justification]

**Configuration**:
- `config/file.json` - [New settings and impact]
```

#### **Architecture Impact**
- **New Dependencies**: [List with justification]
- **API Changes**: [Breaking/non-breaking changes]
- **Performance Impact**: [Measured changes]
- **Security Considerations**: [New attack vectors or protections]

#### **Quality Metrics Achieved**
- Test coverage: [X]% (target: [Y]%)
- Performance: [specific measurements]
- Code quality: [static analysis results]
- Documentation: [completeness assessment]

#### **Validation Evidence**
- **Functional Tests**: [Pass/fail summary with key scenarios]
- **Integration Tests**: [Cross-system validation results]
- **Manual Testing**: [UI/UX validation if applicable]
- **Performance Tests**: [Benchmark results]

#### **Next Steps and Dependencies**
- **Immediate Follow-ups**: [Required actions for completion]
- **Future Enhancements**: [Identified improvement opportunities]
- **Monitoring Requirements**: [What to watch for in production]
- **Related Work**: [Other features/commands that should be updated]

### When to Use This Command
- [Specific scenarios with examples]
- [Preconditions that must be met]
- [Signs that this command is NOT appropriate]

### Integration with Other Commands
- **Triggers**: Commands that should invoke this one
- **Triggered By**: What this command calls next
- **Parallel Execution**: Commands that can run simultaneously
- **Conflicts**: Commands that should not run at the same time

## Template Advantages (Enhanced)

### **Eliminated Original Weaknesses**
✅ **Concrete Implementation Guidance**: Code templates, file organization patterns, and specific examples
✅ **Clear Success Criteria**: Measurable outcomes with verification commands
✅ **Failure Recovery**: Detailed troubleshooting procedures for common scenarios
✅ **Context Integration**: Required file analysis and architecture consistency checks
✅ **Quality Standards**: Specific metrics with implementation guidance

### **New Strengths**
- **AI Agent Autonomy**: Sufficient detail for reliable autonomous execution
- **Consistent Quality**: Templates ensure architectural consistency
- **Rapid Problem Resolution**: Failure scenarios with proven solutions
- **Evidence-Based Validation**: Concrete verification procedures
- **Scalable Process**: Framework grows with project complexity

## Template Disadvantages (Acknowledged)

### **Complexity Overhead**
❌ **Initial Setup Cost**: More complex template requires more time per command
❌ **Maintenance Burden**: Templates need updates when patterns change
❌ **Learning Curve**: Team needs training on enhanced structure

### **Mitigation Strategies**
- **Graduated Complexity**: Use simple version for trivial commands
- **Template Tools**: Provide code generators for common patterns
- **Living Documentation**: Update templates based on real usage patterns
- **Training Materials**: Create examples and best practices guides

## Usage Guidelines

### **For Simple Commands** (LOW complexity)
Use minimal template with basic templates and success criteria

### **For Complex Commands** (HIGH complexity)
Use full template with comprehensive failure recovery and detailed examples

### **For Critical Commands** (Production impact)
Mandatory human review gates with enhanced validation procedures