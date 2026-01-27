//! Tests for Least-to-Most reasoning technique

use agenkit::core::{Agent, AgentError, Message};
use agenkit::techniques::reasoning::{LeastToMostAgent, LeastToMostConfig};
use async_trait::async_trait;
use std::sync::Arc;

/// Mock agent that returns predefined responses
struct MockAgent {
    responses: Vec<String>,
    call_count: std::sync::Mutex<usize>,
}

impl MockAgent {
    fn new(responses: Vec<String>) -> Self {
        Self {
            responses,
            call_count: std::sync::Mutex::new(0),
        }
    }
}

#[async_trait]
impl Agent for MockAgent {
    fn name(&self) -> &str {
        "mock_agent"
    }

    fn capabilities(&self) -> Vec<String> {
        vec!["mock".to_string(), "testing".to_string()]
    }

    async fn process(&self, _message: Message) -> Result<Message, AgentError> {
        let mut count = self.call_count.lock().unwrap();
        let idx = *count % self.responses.len();
        *count += 1;

        Ok(Message::with_text("assistant", self.responses[idx].clone()))
    }
}

#[tokio::test]
async fn test_basic_functionality() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Calculate 3*4\n2. Calculate 2*5\n3. Add the results".to_string(),
        "12".to_string(),
        "10".to_string(),
        "22".to_string(),
    ]));

    let config = LeastToMostConfig::default();
    let ltm = LeastToMostAgent::new(mock, config);

    let message = Message::with_text("user", "Calculate 3*4 + 2*5");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    // Check final solution
    assert_eq!(
        response.content_as_str().unwrap(),
        "22"
    );

    // Check technique metadata
    assert_eq!(
        response.metadata.get("technique").unwrap().as_str().unwrap(),
        "least_to_most"
    );

    // Check num_subproblems
    assert_eq!(
        response.metadata.get("num_subproblems").unwrap().as_u64().unwrap(),
        3
    );

    // Check subproblems array
    let subproblems = response.metadata.get("subproblems").unwrap();
    assert!(subproblems.is_array());
    assert_eq!(subproblems.as_array().unwrap().len(), 3);

    // Check solutions array
    let solutions = response.metadata.get("subproblem_solutions").unwrap();
    assert!(solutions.is_array());
    assert_eq!(solutions.as_array().unwrap().len(), 3);
}

#[tokio::test]
async fn test_name_and_capabilities() {
    let mock = Arc::new(MockAgent::new(vec!["test".to_string()]));
    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    assert_eq!(ltm.name(), "least_to_most");

    let caps = ltm.capabilities();
    assert_eq!(caps.len(), 5);
    assert!(caps.contains(&"reasoning".to_string()));
    assert!(caps.contains(&"decomposition".to_string()));
    assert!(caps.contains(&"compositional_reasoning".to_string()));
    assert!(caps.contains(&"least_to_most".to_string()));
    assert!(caps.contains(&"sequential_solving".to_string()));
}

#[tokio::test]
async fn test_decomposition_with_periods() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. First subproblem\n2. Second subproblem\n3. Third subproblem".to_string(),
        "Solution 1".to_string(),
        "Solution 2".to_string(),
        "Solution 3".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Complex problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    let subproblems = response.metadata.get("subproblems").unwrap();
    let subproblems_array = subproblems.as_array().unwrap();

    assert_eq!(subproblems_array[0].as_str().unwrap(), "First subproblem");
    assert_eq!(subproblems_array[1].as_str().unwrap(), "Second subproblem");
    assert_eq!(subproblems_array[2].as_str().unwrap(), "Third subproblem");
}

#[tokio::test]
async fn test_decomposition_with_parentheses() {
    let mock = Arc::new(MockAgent::new(vec![
        "1) First\n2) Second\n3) Third".to_string(),
        "S1".to_string(),
        "S2".to_string(),
        "S3".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    let subproblems = response.metadata.get("subproblems").unwrap();
    let subproblems_array = subproblems.as_array().unwrap();

    assert_eq!(subproblems_array[0].as_str().unwrap(), "First");
    assert_eq!(subproblems_array[1].as_str().unwrap(), "Second");
    assert_eq!(subproblems_array[2].as_str().unwrap(), "Third");
}

#[tokio::test]
async fn test_sequential_solving() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Step A\n2. Step B".to_string(),
        "Answer A".to_string(),
        "Answer B".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    let solutions = response.metadata.get("subproblem_solutions").unwrap();
    let solutions_array = solutions.as_array().unwrap();

    assert_eq!(solutions_array[0].as_str().unwrap(), "Answer A");
    assert_eq!(solutions_array[1].as_str().unwrap(), "Answer B");
}

#[tokio::test]
async fn test_final_solution_is_last() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Subproblem 1\n2. Subproblem 2".to_string(),
        "Intermediate".to_string(),
        "Final answer".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(response.content_as_str().unwrap(), "Final answer");
    assert_eq!(response.role, "assistant");
}

#[tokio::test]
async fn test_max_subproblems_limit() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Sub 1\n2. Sub 2\n3. Sub 3\n4. Sub 4\n5. Sub 5\n6. Sub 6".to_string(),
        "S1".to_string(),
        "S2".to_string(),
        "S3".to_string(),
    ]));

    let config = LeastToMostConfig {
        decomposer: None,
        max_subproblems: 3,
        compose_solutions: true,
    };
    let ltm = LeastToMostAgent::new(mock, config);

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.metadata.get("num_subproblems").unwrap().as_u64().unwrap(),
        3
    );

    let subproblems = response.metadata.get("subproblems").unwrap();
    assert_eq!(subproblems.as_array().unwrap().len(), 3);
}

#[tokio::test]
async fn test_custom_decomposer() {
    let custom_decomposer = Arc::new(|_problem: &str| -> Result<Vec<String>, AgentError> {
        Ok(vec![
            "Custom step 1".to_string(),
            "Custom step 2".to_string(),
            "Custom step 3".to_string(),
        ])
    });

    let mock = Arc::new(MockAgent::new(vec![
        "Sol 1".to_string(),
        "Sol 2".to_string(),
        "Sol 3".to_string(),
    ]));

    let config = LeastToMostConfig {
        decomposer: Some(custom_decomposer),
        max_subproblems: 5,
        compose_solutions: true,
    };
    let ltm = LeastToMostAgent::new(mock, config);

    let message = Message::with_text("user", "Any problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    let subproblems = response.metadata.get("subproblems").unwrap();
    let subproblems_array = subproblems.as_array().unwrap();

    assert_eq!(subproblems_array[0].as_str().unwrap(), "Custom step 1");
    assert_eq!(subproblems_array[1].as_str().unwrap(), "Custom step 2");
    assert_eq!(subproblems_array[2].as_str().unwrap(), "Custom step 3");
}

#[tokio::test]
async fn test_compose_solutions_enabled() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Sub 1\n2. Sub 2".to_string(),
        "Solution 1".to_string(),
        "Solution 2".to_string(),
    ]));

    let config = LeastToMostConfig {
        decomposer: None,
        max_subproblems: 5,
        compose_solutions: true,
    };
    let ltm = LeastToMostAgent::new(mock, config);

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.metadata.get("compose_solutions").unwrap().as_bool().unwrap(),
        true
    );
}

#[tokio::test]
async fn test_compose_solutions_disabled() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Sub 1\n2. Sub 2".to_string(),
        "Solution 1".to_string(),
        "Solution 2".to_string(),
    ]));

    let config = LeastToMostConfig {
        decomposer: None,
        max_subproblems: 5,
        compose_solutions: false,
    };
    let ltm = LeastToMostAgent::new(mock, config);

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.metadata.get("compose_solutions").unwrap().as_bool().unwrap(),
        false
    );
}

#[tokio::test]
async fn test_skip_empty_lines() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. First\n\n2. Second\n\n\n3. Third".to_string(),
        "S1".to_string(),
        "S2".to_string(),
        "S3".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.metadata.get("num_subproblems").unwrap().as_u64().unwrap(),
        3
    );
}

#[tokio::test]
async fn test_atomic_problem_fallback() {
    let mock = Arc::new(MockAgent::new(vec![
        "No valid decomposition".to_string(),
        "Single solution".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Simple problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.metadata.get("num_subproblems").unwrap().as_u64().unwrap(),
        1
    );

    let subproblems = response.metadata.get("subproblems").unwrap();
    let subproblems_array = subproblems.as_array().unwrap();
    assert_eq!(subproblems_array[0].as_str().unwrap(), "Simple problem");

    assert_eq!(response.content_as_str().unwrap(), "Single solution");
}

#[tokio::test]
async fn test_whitespace_handling() {
    let mock = Arc::new(MockAgent::new(vec![
        "  1.   Trimmed   \n  2.   Also trimmed   ".to_string(),
        "S1".to_string(),
        "S2".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    let subproblems = response.metadata.get("subproblems").unwrap();
    let subproblems_array = subproblems.as_array().unwrap();

    assert_eq!(subproblems_array[0].as_str().unwrap(), "Trimmed");
    assert_eq!(subproblems_array[1].as_str().unwrap(), "Also trimmed");
}

#[tokio::test]
async fn test_metadata_includes_all_fields() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Calculate x\n2. Calculate y\n3. Combine results".to_string(),
        "X".to_string(),
        "Y".to_string(),
        "XY".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    // Check all required metadata fields
    assert!(response.metadata.contains_key("technique"));
    assert!(response.metadata.contains_key("num_subproblems"));
    assert!(response.metadata.contains_key("subproblems"));
    assert!(response.metadata.contains_key("subproblem_solutions"));
    assert!(response.metadata.contains_key("compose_solutions"));

    let subproblems = response.metadata.get("subproblems").unwrap();
    let subproblems_array = subproblems.as_array().unwrap();
    assert_eq!(subproblems_array[0].as_str().unwrap(), "Calculate x");
    assert_eq!(subproblems_array[1].as_str().unwrap(), "Calculate y");
    assert_eq!(subproblems_array[2].as_str().unwrap(), "Combine results");
}

#[tokio::test]
async fn test_empty_problem_string() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Sub".to_string(),
        "Sol".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.metadata.get("technique").unwrap().as_str().unwrap(),
        "least_to_most"
    );
}

#[tokio::test]
async fn test_max_subproblems_one() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. A\n2. B\n3. C".to_string(),
        "Only one".to_string(),
    ]));

    let config = LeastToMostConfig {
        decomposer: None,
        max_subproblems: 1,
        compose_solutions: true,
    };
    let ltm = LeastToMostAgent::new(mock, config);

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.metadata.get("num_subproblems").unwrap().as_u64().unwrap(),
        1
    );

    let subproblems = response.metadata.get("subproblems").unwrap();
    assert_eq!(subproblems.as_array().unwrap().len(), 1);
}

#[tokio::test]
async fn test_solution_whitespace_trimming() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. Sub".to_string(),
        "   Solution with whitespace   ".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    assert_eq!(
        response.content_as_str().unwrap(),
        "Solution with whitespace"
    );

    let solutions = response.metadata.get("subproblem_solutions").unwrap();
    let solutions_array = solutions.as_array().unwrap();
    assert_eq!(
        solutions_array[0].as_str().unwrap(),
        "Solution with whitespace"
    );
}

#[tokio::test]
async fn test_multiline_content_parsing() {
    let mock = Arc::new(MockAgent::new(vec![
        "1. First part\n   continued\n2. Second".to_string(),
        "S1".to_string(),
        "S2".to_string(),
    ]));

    let ltm = LeastToMostAgent::new(mock, LeastToMostConfig::default());

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    // Should only parse lines starting with numbers
    assert_eq!(
        response.metadata.get("num_subproblems").unwrap().as_u64().unwrap(),
        2
    );
}

#[tokio::test]
async fn test_custom_decomposer_with_max_limit() {
    let custom_decomposer = Arc::new(|_problem: &str| -> Result<Vec<String>, AgentError> {
        Ok(vec![
            "Step 1".to_string(),
            "Step 2".to_string(),
            "Step 3".to_string(),
            "Step 4".to_string(),
            "Step 5".to_string(),
        ])
    });

    let mock = Arc::new(MockAgent::new(vec![
        "S1".to_string(),
        "S2".to_string(),
        "S3".to_string(),
    ]));

    let config = LeastToMostConfig {
        decomposer: Some(custom_decomposer),
        max_subproblems: 3,
        compose_solutions: true,
    };
    let ltm = LeastToMostAgent::new(mock, config);

    let message = Message::with_text("user", "Problem");
    let result = ltm.process(message).await;

    assert!(result.is_ok());
    let response = result.unwrap();

    // Should be limited to 3 even though custom decomposer returned 5
    assert_eq!(
        response.metadata.get("num_subproblems").unwrap().as_u64().unwrap(),
        3
    );
}
