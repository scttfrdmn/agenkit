///! Reasoning techniques for AI agents.
pub mod chain_of_thought;
pub mod graph_of_thought;
pub mod least_to_most;
pub mod plan_and_solve;
pub mod reasoning_graph;
pub mod reasoning_tree;
pub mod self_consistency;
pub mod tree_of_thought;

pub use chain_of_thought::{ChainOfThoughtAgent, ChainOfThoughtConfig};
pub use graph_of_thought::{AggregatorType, GraphOfThoughtAgent, GraphOfThoughtConfig};
pub use least_to_most::{DecomposerFn, LeastToMostAgent, LeastToMostConfig, Subproblem};
pub use plan_and_solve::{Plan, PlanAndSolveAgent, PlanAndSolveConfig, PlanStep, PlannerFn, SolverFn};
pub use reasoning_graph::{
    EdgeType, GraphStatistics, LogicalEdge, NodeType, ReasoningGraph, ThoughtNode,
};
pub use reasoning_tree::{NodeState, ReasoningNode, ReasoningTree, TreeStatistics};
pub use self_consistency::{
    default_answer_extractor, AnswerExtractor, SelfConsistencyAgent, SelfConsistencyConfig,
    VotingStrategy,
};
pub use tree_of_thought::{
    default_evaluator, EvaluatorFunc, SearchStrategy, TreeOfThoughtAgent, TreeOfThoughtConfig,
};
