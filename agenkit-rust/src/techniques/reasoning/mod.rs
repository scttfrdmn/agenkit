///! Reasoning techniques for AI agents.

pub mod self_consistency;

pub use self_consistency::{
    SelfConsistencyAgent,
    SelfConsistencyConfig,
    VotingStrategy,
    AnswerExtractor,
    default_answer_extractor,
};
