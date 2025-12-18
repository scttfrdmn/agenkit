///! Reasoning techniques for AI agents.

pub mod chain_of_thought;
pub mod reasoning_tree;
pub mod self_consistency;
pub mod tree_of_thought;

pub use chain_of_thought::{ChainOfThoughtAgent, ChainOfThoughtConfig};
pub use reasoning_tree::{NodeState, ReasoningNode, ReasoningTree, TreeStatistics};
pub use self_consistency::{
    SelfConsistencyAgent,
    SelfConsistencyConfig,
    VotingStrategy,
    AnswerExtractor,
    default_answer_extractor,
};
pub use tree_of_thought::{
    TreeOfThoughtAgent,
    TreeOfThoughtConfig,
    SearchStrategy,
    EvaluatorFunc,
    default_evaluator,
};
