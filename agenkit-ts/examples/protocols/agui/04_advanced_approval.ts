/**
 * Advanced AG-UI HITL Approval Patterns
 *
 * Demonstrates advanced Human-in-the-Loop patterns with custom approval logic,
 * multi-stage approval, approval with modifications, and complex decision workflows.
 *
 * Key concepts:
 * - Multi-level approval thresholds
 * - Approval with content modifications
 * - Contextual approval decisions
 * - Custom approval UI patterns
 * - Approval audit trails
 *
 * This example shows:
 * - Dynamic approval thresholds
 * - Approval with modifications
 * - Multi-stage approval workflow
 * - Approval context and metadata
 * - Custom approval UI integration
 *
 * Run:
 *   npx ts-node examples/protocols/agui/04_advanced_approval.ts
 */

import { Agent, Message } from '../../../src/core/interfaces.js';
import { HumanInLoopAgent, ApprovalRequest, ApprovalResponse } from '../../../src/patterns/human-in-loop.js';
import { AGUIHumanInLoopAdapter, Interrupt } from '../../../src/protocols/agui/index.js';

/**
 * Approval log entry for audit trail
 */
interface ApprovalLogEntry {
  timestamp: Date;
  amount: number;
  confidence: number;
  riskLevel: string;
  decision: string;
  tier: number;
  approver: string;
  feedback: string;
  modified: boolean;
}

// Global approval audit log
const approvalLog: ApprovalLogEntry[] = [];

/**
 * Financial agent that processes transactions
 */
class FinancialAgent implements Agent {
  readonly name = 'FinancialAgent';

  async process(message: Message): Promise<Message> {
    const content = String(message.content).toLowerCase();

    // Extract amount
    const amount = this.extractAmount(content);

    // Calculate confidence based on amount
    const confidence = this.calculateConfidence(amount);

    // Determine transaction type
    let txType = 'transaction';
    let adjustedConfidence = confidence;

    if (content.includes('wire') || content.includes('international')) {
      adjustedConfidence *= 0.8; // Lower confidence for wire transfers
      txType = 'wire_transfer';
    } else if (content.includes('payment')) {
      txType = 'payment';
    }

    // Determine risk level
    let riskLevel = 'low';
    if (amount > 25000) {
      riskLevel = 'high';
    } else if (amount > 5000) {
      riskLevel = 'medium';
    }

    return {
      role: 'assistant',
      content: `Processing ${txType} for $${this.formatAmount(amount)}`,
      metadata: {
        confidence: adjustedConfidence,
        amount,
        transaction_type: txType,
        risk_level: riskLevel,
      },
      timestamp: new Date().toISOString(),
    };
  }

  readonly capabilities = ['finance', 'transactions', 'risk-assessment'];

  private extractAmount(text: string): number {
    const match = text.match(/\$([0-9,]+)/);
    if (match) {
      const amountStr = match[1].replace(/,/g, '');
      return parseInt(amountStr, 10);
    }
    return 1000; // Default
  }

  private calculateConfidence(amount: number): number {
    if (amount < 1000) return 0.95;
    if (amount < 10000) return 0.85;
    if (amount < 50000) return 0.7;
    return 0.4;
  }

  private formatAmount(amount: number): string {
    return amount.toLocaleString('en-US');
  }
}

/**
 * Tiered approval function
 *
 * Approval tiers:
 * - < $1,000: Auto-approve
 * - $1,000 - $10,000: Manager approval
 * - $10,000 - $50,000: Director approval
 * - > $50,000: Executive approval + modifications
 */
async function tieredApprovalFunc(request: ApprovalRequest): Promise<ApprovalResponse> {
  const amount = (request.message.metadata?.amount as number) || 0;
  const confidence = request.confidence || 0;
  const riskLevel = (request.message.metadata?.risk_level as string) || 'unknown';

  console.log('\n' + '='.repeat(60));
  console.log('Tiered Approval Request');
  console.log('='.repeat(60));
  console.log(`Amount:      $${amount.toLocaleString('en-US')}`);
  console.log(`Confidence:  ${confidence.toFixed(2)}`);
  console.log(`Risk Level:  ${riskLevel}`);

  // Create log entry
  const logEntry: ApprovalLogEntry = {
    timestamp: new Date(),
    amount,
    confidence,
    riskLevel,
    decision: '',
    tier: 0,
    approver: '',
    feedback: '',
    modified: false,
  };

  // Simulate review time
  await new Promise((resolve) => setTimeout(resolve, 200));

  if (amount < 1000) {
    console.log('✓ Auto-approved (Tier 0: < $1,000)');
    logEntry.decision = 'auto_approved';
    logEntry.tier = 0;
    logEntry.approver = 'System';
    logEntry.feedback = 'Auto-approved';
    approvalLog.push(logEntry);

    return {
      approved: true,
      feedback: 'Auto-approved',
    };
  } else if (amount < 10000) {
    console.log('✓ Manager approved (Tier 1: $1K-$10K)');
    logEntry.decision = 'manager_approved';
    logEntry.tier = 1;
    logEntry.approver = 'Manager';
    logEntry.feedback = 'Approved by Manager';
    approvalLog.push(logEntry);

    return {
      approved: true,
      feedback: 'Approved by Manager',
    };
  } else if (amount < 50000) {
    console.log('✓ Director approved (Tier 2: $10K-$50K)');
    logEntry.decision = 'director_approved';
    logEntry.tier = 2;
    logEntry.approver = 'Director';
    logEntry.feedback = 'Approved by Director';
    approvalLog.push(logEntry);

    return {
      approved: true,
      feedback: 'Approved by Director',
    };
  } else {
    // High-value transaction: Executive approval with modifications
    console.log('⚠️  Executive review required (Tier 3: > $50K)');
    console.log('   → Adding compliance review requirement');

    logEntry.decision = 'executive_approved_modified';
    logEntry.tier = 3;
    logEntry.approver = 'Executive';
    logEntry.feedback = 'Executive approval with compliance review';
    logEntry.modified = true;
    approvalLog.push(logEntry);

    // Modify the message to add compliance requirement
    const modifiedContent = `${request.message.content} [REQUIRES COMPLIANCE REVIEW]`;
    const modifiedMessage: Message = {
      role: request.message.role,
      content: modifiedContent,
      metadata: {
        ...request.message.metadata,
        compliance_review_required: true,
        executive_approved: true,
      },
      timestamp: new Date().toISOString(),
    };

    return {
      approved: true,
      feedback: 'Executive approval granted with compliance review requirement',
      modifiedMessage,
    };
  }
}

/**
 * Contextual approval function based on risk and timing
 */
async function contextualApprovalFunc(request: ApprovalRequest): Promise<ApprovalResponse> {
  const amount = (request.message.metadata?.amount as number) || 0;
  const confidence = request.confidence || 0;
  const riskLevel = (request.message.metadata?.risk_level as string) || 'unknown';
  const txType = (request.message.metadata?.transaction_type as string) || 'unknown';

  console.log('\n' + '='.repeat(60));
  console.log('Contextual Approval Request');
  console.log('='.repeat(60));
  console.log(`Amount:       $${amount.toLocaleString('en-US')}`);
  console.log(`Type:         ${txType}`);
  console.log(`Risk Level:   ${riskLevel}`);
  console.log(`Confidence:   ${confidence.toFixed(2)}`);
  console.log(`Time:         ${new Date().toLocaleTimeString('en-US')}`);

  // Check if it's business hours (9 AM - 5 PM)
  const hour = new Date().getHours();
  const businessHours = hour >= 9 && hour < 17;

  // Simulate review time
  await new Promise((resolve) => setTimeout(resolve, 200));

  // Wire transfers require extra scrutiny
  if (txType === 'wire_transfer') {
    if (!businessHours) {
      console.log('❌ REJECTED: Wire transfers not allowed outside business hours');
      return {
        approved: false,
        feedback: 'Wire transfers must be processed during business hours (9 AM - 5 PM)',
      };
    }
    if (riskLevel === 'high') {
      console.log('⚠️  APPROVED WITH CONDITIONS: High-risk wire transfer');
      return {
        approved: true,
        feedback: 'Approved with enhanced monitoring and dual authorization required',
      };
    }
  }

  // High-risk transactions
  if (riskLevel === 'high') {
    if (confidence < 0.5) {
      console.log('❌ REJECTED: High risk + low confidence');
      return {
        approved: false,
        feedback: 'Insufficient confidence for high-risk transaction',
      };
    }
    console.log('✓ APPROVED: High-risk transaction with acceptable confidence');
    return {
      approved: true,
      feedback: `Approved high-risk transaction (confidence: ${confidence.toFixed(2)})`,
    };
  }

  // Default approval
  console.log('✓ APPROVED: Standard approval');
  return {
    approved: true,
    feedback: 'Standard approval granted',
  };
}

/**
 * Example 1: Tiered approval workflow
 */
async function exampleTieredApproval() {
  console.log('='.repeat(60));
  console.log('Example 1: Tiered Approval Workflow');
  console.log('='.repeat(60));
  console.log();

  const agent = new FinancialAgent();

  const hilAgent = new HumanInLoopAgent({
    agent,
    approvalFunc: tieredApprovalFunc,
    approvalThreshold: 0.8,
  });

  const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
    agentName: 'TieredApproval',
    emitInterrupts: true,
  });

  // Test different amounts
  const testCases = [
    { description: 'Small transaction', message: 'Process payment of $500', expectedTier: 0 },
    { description: 'Medium transaction', message: 'Process payment of $5,000', expectedTier: 1 },
    { description: 'Large transaction', message: 'Process payment of $25,000', expectedTier: 2 },
    { description: 'Very large transaction', message: 'Process wire transfer of $75,000', expectedTier: 3 },
  ];

  for (const tc of testCases) {
    console.log(`\n📝 Test: ${tc.description}`);
    console.log(`   Message: ${tc.message}`);

    const message: Message = {
      role: 'user',
      content: tc.message,
      timestamp: new Date().toISOString(),
    };

    let interruptFound = false;
    for await (const event of adapter.streamEvents(message)) {
      if (event instanceof Interrupt) {
        interruptFound = true;
        console.log('\n   🚨 Interrupt Event:');
        console.log(`      Status: ${event.context?.approval_status}`);
        console.log(`      Confidence: ${(event.context?.confidence as number)?.toFixed(2)}`);
      }
    }

    if (!interruptFound) {
      console.log('   ✓ No approval needed (high confidence)');
    }
  }
}

/**
 * Example 2: Contextual approval
 */
async function exampleContextualApproval() {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 2: Contextual Approval (Risk & Timing)');
  console.log('='.repeat(60));
  console.log();

  const agent = new FinancialAgent();

  const hilAgent = new HumanInLoopAgent({
    agent,
    approvalFunc: contextualApprovalFunc,
    approvalThreshold: 0.8,
  });

  const adapter = new AGUIHumanInLoopAdapter(hilAgent, {
    agentName: 'ContextualApproval',
    emitInterrupts: true,
  });

  const testCases = [
    'Process wire transfer of $30,000',
    'Process payment of $50,000',
    'Process international wire of $100,000',
  ];

  for (const tc of testCases) {
    console.log(`\n📝 Test: ${tc}`);

    const message: Message = {
      role: 'user',
      content: tc,
      timestamp: new Date().toISOString(),
    };

    for await (const event of adapter.streamEvents(message)) {
      if (event instanceof Interrupt) {
        console.log(`   🚨 Decision: ${event.context?.approval_status}`);
      }
    }
  }
}

/**
 * Example 3: Approval audit trail
 */
function exampleAuditTrail() {
  console.log('\n\n' + '='.repeat(60));
  console.log('Example 3: Approval Audit Trail');
  console.log('='.repeat(60));
  console.log();

  if (approvalLog.length === 0) {
    console.log('No approvals logged yet');
    return;
  }

  console.log('Approval History:');
  console.log('─'.repeat(60));

  approvalLog.forEach((entry, i) => {
    console.log(`\n${i + 1}. ${entry.timestamp.toLocaleString('en-US')}`);
    console.log(`   Amount:      $${entry.amount.toLocaleString('en-US')}`);
    console.log(`   Risk Level:  ${entry.riskLevel}`);
    console.log(`   Confidence:  ${entry.confidence.toFixed(2)}`);
    console.log(`   Tier:        ${entry.tier} (${entry.approver})`);
    console.log(`   Decision:    ${entry.decision}`);
    console.log(`   Modified:    ${entry.modified}`);
    if (entry.feedback) {
      console.log(`   Feedback:    ${entry.feedback}`);
    }
  });

  // Summary statistics
  console.log('\n' + '─'.repeat(60));
  console.log('Summary Statistics:');
  console.log(`   Total Approvals: ${approvalLog.length}`);

  const tierCounts: Record<number, number> = {};
  let totalAmount = 0;
  let modifiedCount = 0;

  approvalLog.forEach((entry) => {
    tierCounts[entry.tier] = (tierCounts[entry.tier] || 0) + 1;
    totalAmount += entry.amount;
    if (entry.modified) modifiedCount++;
  });

  console.log(`   Total Amount:    $${totalAmount.toLocaleString('en-US')}`);
  console.log(`   Modified:        ${modifiedCount}`);
  console.log('\n   Approvals by Tier:');
  for (let tier = 0; tier <= 3; tier++) {
    if (tierCounts[tier]) {
      console.log(`      Tier ${tier}: ${tierCounts[tier]}`);
    }
  }
}

/**
 * Main function
 */
async function main() {
  console.log('AG-UI Advanced Approval Patterns Examples');
  console.log();

  // Run examples
  await exampleTieredApproval();
  await exampleContextualApproval();
  exampleAuditTrail();

  console.log('\n\n' + '='.repeat(60));
  console.log('✅ All examples completed successfully!');
  console.log('='.repeat(60));
}

// Run examples
main().catch((error) => {
  console.error('Error:', error);
  process.exit(1);
});
