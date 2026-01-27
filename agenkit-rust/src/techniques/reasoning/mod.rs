///! Reasoning techniques for AI agents.
pub mod chain_of_thought;
pub mod least_to_most;
pub mod reasoning_tree;
pub mod self_consistency;
pub mod tree_of_thought;

pub use chain_of_thought::{ChainOfThoughtAgent, ChainOfThoughtConfig};
pub use least_to_most::{DecomposerFn, LeastToMostAgent, LeastToMostConfig, Subproblem};
pub use reasoning_tree::{NodeState, ReasoningNode, ReasoningTree, TreeStatistics};
pub use self_consistency::{
    default_answer_extractor, AnswerExtractor, SelfConsistencyAgent, SelfConsistencyConfig,
    VotingStrategy,
};
pub use tree_of_thought::{
    default_evaluator, EvaluatorFunc, SearchStrategy, TreeOfThoughtAgent, TreeOfThoughtConfig,
};
